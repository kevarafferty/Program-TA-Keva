"""
cocokkan_cuaca.py — Mencari preset cuaca CARLA yang paling mirip dengan rekaman hujan Dika.

Ide: render kamera agen (parameter Dika) di peta train_fix dengan beberapa preset cuaca,
lalu bandingkan statistik citranya dengan frame dari recordings/hujan.mp4 Dika.
Pemilihan preset berdasarkan KEMIRIPAN CITRA, bukan angka penghindaran (hindari fishing).

Tiga langkah (subcommand):

  1. referensi  — ambil sampel frame dari video agen Dika, hitung metrik.        (tanpa CARLA)
  2. ambil      — render kamera agen untuk tiap preset di beberapa titik jalan.  (butuh CARLA)
  3. bandingkan — ranking preset vs referensi + montase visual.                   (tanpa CARLA)

Contoh:
  python cocokkan_cuaca.py referensi --video "<...>\\recordings\\hujan.mp4" --kondisi hujan
  python cocokkan_cuaca.py ambil --label EditorHigh
  python cocokkan_cuaca.py bandingkan --kondisi hujan --label EditorHigh

Catatan teknis:
  - Video Dika: cleanTest.py menulis cvtColor(BGR, RGB2BGR), jadi kanal R/B tertukar -> dibalik.
    Panel kiri (x < 300) digelapkan dan berisi teks overlay -> SEMUA metrik hanya dihitung di x >= 300,
    untuk frame Dika maupun frame kita.
  - Frame kita dilewatkan ke encoder mp4v yang sama (cv2.VideoWriter) sebelum dihitung,
    supaya efek kompresi setara.
  - Kamera: 640x640, FOV 90, x=1.5 z=2.0 pitch=-15 (carla_env.py Dika). Mobil: vehicle.micro.microlino, lajur y=250.5.
"""
import argparse
import glob
import json
import os
import sys
import time

import cv2
import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
X_PANEL = 300           # panel overlay kiri di video Dika
UKURAN = 640

PRESET_DEFAULT = ["ClearNoon", "CloudyNoon", "WetNoon", "WetCloudyNoon",
                  "SoftRainNoon", "MidRainyNoon", "HardRainNoon"]
POSISI_X_DEFAULT = [-280, -245, -210, -175, -140, -105, -70, -45]   # rentang GT lubang Dika
LAJUR_Y = 250.5

METRIK = ["terang", "kontras", "langit", "saturasi", "tepi_jauh", "jalan_terang", "jalan_kontras"]
KET_METRIK = {
    "terang": "rata-rata luminansi",
    "kontras": "simpangan baku luminansi",
    "langit": "luminansi area langit (y < 30%)",
    "saturasi": "rata-rata saturasi HSV",
    "tepi_jauh": "gradien rata-rata di pita jauh (y 30-45%), turun kalau berkabut",
    "jalan_terang": "luminansi jalan (y > 60%), naik kalau basah/memantul",
    "jalan_kontras": "simpangan baku luminansi jalan",
}


# ---------------------------------------------------------------- metrik
def hitung_metrik(bgr):
    """bgr: uint8 HxWx3 (warna benar). Hanya area x >= X_PANEL yang dipakai."""
    roi = bgr[:, X_PANEL:]
    h = roi.shape[0]
    abu = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    gx = cv2.Sobel(abu, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(abu, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx * gx + gy * gy)
    a, b, c = int(0.30 * h), int(0.45 * h), int(0.60 * h)
    return {
        "terang": float(abu.mean()),
        "kontras": float(abu.std()),
        "langit": float(abu[:a].mean()),
        "saturasi": float(hsv[:, :, 1].mean()),
        "tepi_jauh": float(grad[a:b].mean()),
        "jalan_terang": float(abu[c:].mean()),
        "jalan_kontras": float(abu[c:].std()),
    }


def lewat_mp4(daftar_bgr, tmp_path):
    """Encode lalu decode ulang dengan mp4v (sama seperti VideoWriter di cleanTest.py Dika)."""
    if not daftar_bgr:
        return daftar_bgr
    h, w = daftar_bgr[0].shape[:2]
    vw = cv2.VideoWriter(tmp_path, cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (w, h))
    if not vw.isOpened():
        print("   PERINGATAN: encoder mp4v tidak tersedia, metrik dihitung tanpa kompresi.")
        return daftar_bgr
    for f in daftar_bgr:
        vw.write(f)
    vw.release()
    cap = cv2.VideoCapture(tmp_path)
    hasil = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        hasil.append(f)
    cap.release()
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    if len(hasil) != len(daftar_bgr):
        print("   PERINGATAN: jumlah frame setelah mp4 berbeda (%d vs %d), pakai frame asli."
              % (len(hasil), len(daftar_bgr)))
        return daftar_bgr
    return hasil


# ---------------------------------------------------------------- 1. referensi
def cmd_referensi(args):
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        sys.exit("Video tidak bisa dibuka: %s" % args.video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idx = np.linspace(args.lewati_awal, n - 1, args.sampel).astype(int)
    out_dir = os.path.join(DIR, "referensi")
    os.makedirs(out_dir, exist_ok=True)
    baris, contoh = [], []
    for k, i in enumerate(idx):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, f = cap.read()
        if not ok:
            continue
        f = f[:, :, ::-1].copy()          # balik kanal R/B yang tertukar di video Dika
        m = hitung_metrik(f)
        m["frame"] = int(i)
        baris.append(m)
        if k % max(1, len(idx) // 4) == 0 and len(contoh) < 4:
            p = os.path.join(out_dir, "%s_frame%05d.png" % (args.kondisi, i))
            cv2.imwrite(p, f)
            contoh.append(os.path.basename(p))
    cap.release()
    ref = {"kondisi": args.kondisi, "video": args.video, "n_frame_video": n,
           "frame": baris, "contoh": contoh}
    p = os.path.join(out_dir, "referensi_%s.json" % args.kondisi)
    with open(p, "w") as fh:
        json.dump(ref, fh, indent=1)
    print("Referensi %s: %d frame dari %d -> %s" % (args.kondisi, len(baris), n, p))
    for nama in METRIK:
        v = np.array([b[nama] for b in baris])
        print("  %-14s median %7.2f  IQR %6.2f" % (nama, np.median(v), iqr(v)))


def iqr(v):
    q1, q3 = np.percentile(v, [25, 75])
    return float(q3 - q1)


# ---------------------------------------------------------------- 2. ambil (CARLA)
def cmd_ambil(args):
    import queue
    import carla  # pyright: ignore[reportMissingImports]

    client = carla.Client(args.host, args.port)
    client.set_timeout(60.0)
    world = client.get_world()
    nama_peta = world.get_map().name
    if args.peta not in nama_peta:
        print("Memuat peta %s (sekarang %s) ..." % (args.peta, nama_peta))
        world = client.load_world(args.peta)
        time.sleep(5)
    print("Peta:", world.get_map().name, "| server", client.get_server_version())

    presets = args.preset.split(",") if args.preset else PRESET_DEFAULT
    posisi = [float(x) for x in args.posisi.split(",")] if args.posisi else POSISI_X_DEFAULT

    # simpan parameter preset supaya bisa dilaporkan
    out_dir = os.path.join(DIR, "data_%s" % args.label)
    os.makedirs(out_dir, exist_ok=True)
    param = {}
    for p in presets:
        w = getattr(carla.WeatherParameters, p)
        param[p] = {k: float(getattr(w, k)) for k in dir(w)
                    if not k.startswith("_") and isinstance(getattr(w, k), (int, float))}
    with open(os.path.join(out_dir, "parameter_preset.json"), "w") as fh:
        json.dump(param, fh, indent=1)

    asli = world.get_settings()
    s = world.get_settings()
    s.synchronous_mode = True
    s.fixed_delta_seconds = 0.05
    world.apply_settings(s)

    aktor = []
    try:
        bpl = world.get_blueprint_library()
        car_bp = bpl.find("vehicle.micro.microlino")
        peta = world.get_map()

        def tf_di(x):
            wp = peta.get_waypoint(carla.Location(x=x, y=LAJUR_Y, z=0.0), project_to_road=True)
            z = wp.transform.location.z + 0.5
            return carla.Transform(carla.Location(x=x, y=LAJUR_Y, z=z), carla.Rotation(yaw=0))

        mobil = world.try_spawn_actor(car_bp, tf_di(posisi[0]))
        if mobil is None:
            sys.exit("Gagal spawn Microlino. Hapus kendaraan lain (mis. dari run sebelumnya) lalu ulangi.")
        aktor.append(mobil)

        cam_bp = bpl.find("sensor.camera.rgb")
        cam_bp.set_attribute("image_size_x", str(UKURAN))
        cam_bp.set_attribute("image_size_y", str(UKURAN))
        cam_bp.set_attribute("fov", "90")
        kamera = world.spawn_actor(cam_bp, carla.Transform(carla.Location(x=1.5, z=2.0),
                                                           carla.Rotation(pitch=-15)),
                                   attach_to=mobil)
        aktor.append(kamera)
        q = queue.Queue()
        kamera.listen(q.put)

        def tick_dan_ambil(n_tick):
            img = None
            for _ in range(n_tick):
                fr = world.tick()
                while True:
                    im = q.get(timeout=10.0)
                    if im.frame >= fr:
                        img = im
                        break
            a = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(img.height, img.width, 4)
            return a[:, :, :3].copy()     # BGRA -> BGR (sama dengan current_image Dika)

        rem = carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True)
        total = len(presets) * len(posisi)
        k = 0
        t0 = time.time()
        for p in presets:
            world.set_weather(getattr(carla.WeatherParameters, p))
            os.makedirs(os.path.join(out_dir, p), exist_ok=True)
            tick_dan_ambil(args.tick_cuaca)          # biar hujan/genangan stabil
            for x in posisi:
                mobil.set_transform(tf_di(x))
                mobil.apply_control(rem)
                f = tick_dan_ambil(args.tick_posisi)
                cv2.imwrite(os.path.join(out_dir, p, "x%+04d.png" % int(x)), f)
                k += 1
            print("  [%d/%d] %-14s selesai (%.0f s)" % (k, total, p, time.time() - t0))
        print("Selesai. Citra di", out_dir)
    finally:
        for a in aktor:
            try:
                if a.type_id.startswith("sensor"):
                    a.stop()
                a.destroy()
            except Exception:
                pass
        world.apply_settings(asli)      # kembalikan mode asinkron (penting di Editor)


# ---------------------------------------------------------------- 3. bandingkan
def cmd_bandingkan(args):
    p_ref = os.path.join(DIR, "referensi", "referensi_%s.json" % args.kondisi)
    if not os.path.exists(p_ref):
        sys.exit("Belum ada %s. Jalankan 'referensi' dulu." % p_ref)
    with open(p_ref) as fh:
        ref = json.load(fh)
    data_dir = os.path.join(DIR, "data_%s" % args.label)
    presets = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))],
                     key=lambda d: PRESET_DEFAULT.index(d) if d in PRESET_DEFAULT else 99)
    if not presets:
        sys.exit("Tidak ada folder preset di %s." % data_dir)

    med_ref = {m: float(np.median([b[m] for b in ref["frame"]])) for m in METRIK}
    sk_ref = {m: max(iqr(np.array([b[m] for b in ref["frame"]])), 1e-3) for m in METRIK}

    hasil, gambar = {}, {}
    for p in presets:
        file = sorted(glob.glob(os.path.join(data_dir, p, "*.png")))
        frames = [cv2.imread(f) for f in file]
        frames = lewat_mp4(frames, os.path.join(data_dir, "_tmp_%s.mp4" % p))
        ms = [hitung_metrik(f) for f in frames]
        med = {m: float(np.median([x[m] for x in ms])) for m in METRIK}
        jarak = {m: abs(med[m] - med_ref[m]) / sk_ref[m] for m in METRIK}
        hasil[p] = {"median": med, "jarak": jarak, "skor": float(np.mean(list(jarak.values()))),
                    "n": len(frames)}
        gambar[p] = frames

    urut = sorted(hasil, key=lambda p: hasil[p]["skor"])
    out_dir = os.path.join(DIR, "hasil_%s" % args.label)
    os.makedirs(out_dir, exist_ok=True)

    # tabel
    lebar = 9
    kepala = "%-14s" % "preset" + "".join("%*s" % (lebar + 2, m[:lebar + 1]) for m in METRIK) + "   SKOR"
    print("\nKondisi referensi: %s (%d frame Dika) | label render: %s" % (args.kondisi, len(ref["frame"]), args.label))
    print("Angka = median metrik. SKOR = rata-rata |selisih| / IQR Dika (makin kecil makin mirip).\n")
    print(kepala)
    print("%-14s" % "DIKA" + "".join("%*.1f" % (lebar + 2, med_ref[m]) for m in METRIK))
    for p in urut:
        print("%-14s" % p + "".join("%*.1f" % (lebar + 2, hasil[p]["median"][m]) for m in METRIK)
              + "   %5.2f" % hasil[p]["skor"])
    print("\nPaling mirip: %s (skor %.2f). Kedua: %s (skor %.2f)."
          % (urut[0], hasil[urut[0]]["skor"], urut[1], hasil[urut[1]]["skor"]))
    if hasil[urut[1]]["skor"] - hasil[urut[0]]["skor"] < 0.3:
        print("PERHATIAN: dua teratas hampir seri (selisih < 0,3). Putuskan dari montase, bukan dari skor saja.")

    ringkas = {"kondisi": args.kondisi, "label": args.label, "median_dika": med_ref,
               "iqr_dika": sk_ref, "preset": hasil, "urutan": urut, "keterangan_metrik": KET_METRIK}
    with open(os.path.join(out_dir, "ringkasan_%s.json" % args.kondisi), "w") as fh:
        json.dump(ringkas, fh, indent=1)

    # montase: baris = Dika + preset (urut skor), kolom = 4 contoh, hanya area x >= 300
    def potong(f):
        return cv2.resize(f[:, X_PANEL:], (170, 320))

    contoh_dika = [cv2.imread(os.path.join(DIR, "referensi", c)) for c in ref["contoh"]][:4]
    baris_img = []
    def satu_baris(label, frames):
        sel = [potong(f) for f in frames[:4]]
        while len(sel) < 4:
            sel.append(np.zeros((320, 170, 3), np.uint8))
        lab = np.full((320, 190, 3), 255, np.uint8)
        y = 150
        for bagian in label.split("\n"):
            cv2.putText(lab, bagian, (6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
            y += 24
        return np.hstack([lab] + sel)
    baris_img.append(satu_baris("DIKA (%s)" % args.kondisi, contoh_dika))
    for p in urut:
        fr = gambar[p]
        pilih = [fr[i] for i in np.linspace(0, len(fr) - 1, 4).astype(int)]
        baris_img.append(satu_baris("%s\nskor %.2f" % (p, hasil[p]["skor"]), pilih))
    mont = np.vstack(baris_img)
    p_mont = os.path.join(out_dir, "montase_%s.jpg" % args.kondisi)
    cv2.imwrite(p_mont, mont, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print("Montase:", p_mont)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    a = sub.add_parser("referensi")
    a.add_argument("--video", required=True, help="recordings/<kondisi>.mp4 Dika (640x640, kamera agen)")
    a.add_argument("--kondisi", required=True)
    a.add_argument("--sampel", type=int, default=60)
    a.add_argument("--lewati_awal", type=int, default=40, help="lewati frame awal (mobil baru jatuh)")

    b = sub.add_parser("ambil")
    b.add_argument("--host", default="127.0.0.1")
    b.add_argument("--port", type=int, default=2000)
    b.add_argument("--peta", default="train_fix")
    b.add_argument("--label", required=True, help="nama kualitas render, mis. EditorHigh atau PaketEpic")
    b.add_argument("--preset", default="", help="daftar dipisah koma (default 7 preset siang)")
    b.add_argument("--posisi", default="", help="daftar x dipisah koma (default 8 titik)")
    b.add_argument("--tick_cuaca", type=int, default=60)
    b.add_argument("--tick_posisi", type=int, default=20)

    c = sub.add_parser("bandingkan")
    c.add_argument("--kondisi", required=True)
    c.add_argument("--label", required=True)

    args = ap.parse_args()
    if args.cmd == "referensi":
        cmd_referensi(args)
    elif args.cmd == "ambil":
        cmd_ambil(args)
    elif args.cmd == "bandingkan":
        cmd_bandingkan(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
