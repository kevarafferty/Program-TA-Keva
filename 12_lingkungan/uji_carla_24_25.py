"""
uji_carla_24_25.py — Pemeriksaan di CARLA yang WAJIB dijalankan sekali sebelum memakai generator/runner.
Claude tidak punya simulator, jadi bagian ini belum pernah dijalankan.

Subperintah (CarlaUE4.exe sudah terbuka, env carla_env):
  python uji_carla_24_25.py slot       40 slot GT v2 -> objek lingkungan (pencocokan posisi)
  python uji_carla_24_25.py toggle     render kamera dengan lubang nyala / mati / separuh -> PNG + selisih piksel
  python uji_carla_24_25.py spawn [--mesh /Game/...]   cek blueprint static.prop.mesh, munculkan 1 lubang,
                                       lalu Microlino lewat di atasnya: ada tabrakan / guncangan?
  python uji_carla_24_25.py kecepatan  tabel throttle -> kecepatan tunak Microlino (untuk C2)
  python uji_carla_24_25.py kecepatan --kendaraan vehicle.nissan.micra vehicle.citroen.c3 vehicle.tesla.model3   (C4)
  python uji_carla_24_25.py azimut     sapuan sun_azimuth_angle pada altitude 10° (untuk A4)
  python uji_carla_24_25.py semua      slot + toggle + kecepatan + azimut (spawn terpisah karena butuh aset)

Hasil: folder uji_carla/ dan kalibrasi_lingkungan.json (dipakai jalankan_skenario.py).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
from generator_tata_letak import BackendGrid, muat_slot_grid   # noqa: E402

OUT = os.path.join(DIR, "uji_carla")
KAL = os.path.join(DIR, "kalibrasi_lingkungan.json")


def koneksi(a):
    import carla
    c = carla.Client(a.host, a.port)
    c.set_timeout(180.0)
    w = c.get_world()
    if "train_fix" not in w.get_map().name:
        w = c.load_world("train_fix")
    s = w.get_settings()
    s.synchronous_mode, s.fixed_delta_seconds = True, 0.05
    w.apply_settings(s)
    c.set_timeout(30.0)
    return carla, c, w


def lepas(w):
    s = w.get_settings()
    s.synchronous_mode = False
    w.apply_settings(s)


def kamera_dika(carla, w, tf, parent=None):
    bp = w.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", "640")
    bp.set_attribute("image_size_y", "640")
    bp.set_attribute("fov", "90")
    cam = w.spawn_actor(bp, tf, attach_to=parent) if parent else w.spawn_actor(bp, tf)
    buf = {}
    cam.listen(lambda im: buf.__setitem__(im.frame, np.frombuffer(im.raw_data, np.uint8).reshape(im.height, im.width, 4)[:, :, :3].copy()))
    return cam, buf


def ambil(w, buf, n_tick=8):
    f = None
    for _ in range(n_tick):
        f = w.tick()
    t0 = time.time()
    while f not in buf and time.time() - t0 < 5:
        time.sleep(0.01)
    return buf.get(f)


def simpan_kal(perbarui: dict):
    d = {}
    if os.path.exists(KAL):
        with open(KAL, encoding="utf-8") as fh:
            d = json.load(fh)
    d.update(perbarui)
    d["diperbarui"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(KAL, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
    print("kalibrasi ->", KAL)


# ------------------------------------------------------------------------------------------------
def uji_slot(a, carla, c, w):
    g = BackendGrid(w, carla, muat_slot_grid(a.gt))
    r = g.ringkas()
    r["contoh_nama"] = {k: v for k, v in list(g.nama.items())[:6]}
    json.dump(dict(ringkas=r, peta=g.peta, nama=g.nama), open(os.path.join(OUT, "slot.json"), "w"), indent=1)
    print(json.dumps(r, indent=1, ensure_ascii=False))
    print("LULUS" if not r["tidak_ketemu"] else "GAGAL: ada slot tanpa objek lingkungan")
    return g


def uji_toggle(a, carla, c, w):
    import cv2
    g = BackendGrid(w, carla, muat_slot_grid(a.gt))
    # kamera seperti kamera Dika, 8 m di belakang ph_0004..ph_0005 di lajur kanan
    tf = carla.Transform(carla.Location(x=-240.0 + 1.5, y=250.5, z=2.0), carla.Rotation(pitch=-15.0))
    cam, buf = kamera_dika(carla, w, tf)
    hasil = {}
    try:
        g.nyalakan_semua(); im_on = ambil(w, buf)
        g.matikan_semua(); im_off = ambil(w, buf)
        sebagian = [s for s in g.peta if s in ("ph_0004", "ph_0006")]
        g.matikan_semua(); g._toggle(sebagian, True); im_half = ambil(w, buf)
        g.nyalakan_semua(); im_on2 = ambil(w, buf)
        for n, im in (("nyala", im_on), ("mati", im_off), ("sebagian_ph0004_ph0006", im_half), ("nyala_lagi", im_on2)):
            cv2.imwrite(os.path.join(OUT, "toggle_%s.png" % n), im)
        d = lambda p, q: float(np.abs(p.astype(int) - q.astype(int)).mean())
        hasil = dict(selisih_nyala_vs_mati=d(im_on, im_off), selisih_nyala_vs_nyala_lagi=d(im_on, im_on2),
                     selisih_mati_vs_sebagian=d(im_off, im_half),
                     piksel_berubah_nyala_vs_mati=float((np.abs(im_on.astype(int) - im_off.astype(int)).max(2) > 25).mean()))
        try:
            from ultralytics import YOLO
            y = YOLO(os.path.join(a.dir_dika, "Yolo", "best_pure.pt"))
            for n, im in (("nyala", im_on), ("mati", im_off), ("sebagian", im_half)):
                r = y(im, imgsz=320, conf=0.05, verbose=False)[0]
                hasil["yolo_%s_n_kotak" % n] = int(len(r.boxes))
                hasil["yolo_%s_conf_maks" % n] = float(r.boxes.conf.max()) if len(r.boxes) else 0.0
        except Exception as e:
            hasil["yolo"] = "dilewati: %s" % e
    finally:
        cam.destroy()
        g.nyalakan_semua()
    # Selisih piksel global TIDAK dipakai sebagai kriteria: awan bergerak dan anti-aliasing temporal memberi
    # selisih sebesar lubang itu sendiri (run 21 Nov: nyala-vs-nyala-lagi 1,98 > nyala-vs-mati 1,66).
    # Kriteria: YOLO melihat lubang saat nyala dan tidak melihat apa pun saat semua dimatikan + cek visual PNG.
    hasil["lulus"] = bool(hasil.get("yolo_nyala_n_kotak", 0) >= 1 and hasil.get("yolo_mati_n_kotak", 1) == 0)
    json.dump(hasil, open(os.path.join(OUT, "toggle.json"), "w"), indent=1)
    print(json.dumps(hasil, indent=1))
    print("LULUS (YOLO): lubang terdeteksi saat nyala, tidak ada deteksi saat mati. Tetap cek toggle_*.png."
          if hasil["lulus"] else "PERIKSA gambar toggle_*.png: toggle tampaknya tidak berpengaruh")


def uji_spawn(a, carla, c, w):
    import cv2
    lib = w.get_blueprint_library()
    bps = list(lib.filter("static.prop.mesh"))
    hasil = dict(blueprint_ada=bool(bps))
    if not bps:
        print("GAGAL: static.prop.mesh tidak ada -> pakai backend grid saja"); json.dump(hasil, open(os.path.join(OUT, "spawn.json"), "w")); return
    bp = bps[0]
    hasil["atribut"] = [x.id for x in bp]
    mesh = a.mesh or "/Engine/BasicShapes/Plane.Plane"
    hasil["mesh_path"] = mesh
    bp.set_attribute("mesh_path", mesh)
    g = BackendGrid(w, carla, muat_slot_grid(a.gt))
    g.matikan_semua()
    x0, y0 = -255.0, 250.5
    prop = w.try_spawn_actor(bp, carla.Transform(carla.Location(x=x0, y=y0, z=0.039)))
    hasil["spawn_berhasil"] = prop is not None
    if prop is None:
        print("GAGAL spawn mesh %s" % mesh); json.dump(hasil, open(os.path.join(OUT, "spawn.json"), "w"), indent=1); g.nyalakan_semua(); return
    cam, buf = kamera_dika(carla, w, carla.Transform(carla.Location(x=x0 - 8 + 1.5, y=y0, z=2.0), carla.Rotation(pitch=-15)))
    im = ambil(w, buf); cam.destroy()
    cv2.imwrite(os.path.join(OUT, "spawn_tampak.png"), im)
    # lintasi dengan Microlino
    vbp = lib.find("vehicle.micro.microlino")
    veh = w.spawn_actor(vbp, carla.Transform(carla.Location(x=x0 - 25, y=y0, z=0.5)))
    tab, imu = [], []
    cs = w.spawn_actor(lib.find("sensor.other.collision"), carla.Transform(), attach_to=veh)
    cs.listen(lambda e: tab.append((e.other_actor.type_id if e.other_actor else "?", int(e.other_actor.id) if e.other_actor else -1)))
    im_s = w.spawn_actor(lib.find("sensor.other.imu"), carla.Transform(), attach_to=veh)
    im_s.listen(lambda d: imu.append(d.accelerometer.z))
    try:
        for i in range(600):
            veh.apply_control(carla.VehicleControl(throttle=0.3, steer=0.0))
            w.tick()
            if veh.get_location().x > x0 + 6:
                break
        hasil.update(x_akhir=veh.get_location().x, tabrakan=tab, tabrakan_dengan_prop=[t for t in tab if t[1] == prop.id],
                     imu_z_maks=float(np.max(np.abs(np.array(imu) - np.median(imu)))) if imu else None)
    finally:
        for x in (cs, im_s, veh, prop):
            try:
                x.destroy()
            except Exception:
                pass
        g.nyalakan_semua()
    hasil["lulus_tanpa_tabrakan"] = not hasil.get("tabrakan_dengan_prop")
    json.dump(hasil, open(os.path.join(OUT, "spawn.json"), "w"), indent=1)
    print(json.dumps(hasil, indent=1))
    print("Lihat spawn_tampak.png: lubang harus bertekstur (jika --mesh aset lubang). "
          "Tabrakan dengan prop harus kosong; jika tidak, hapus collision pada aset mesh.")


def uji_kecepatan(a, carla, c, w):
    lib = w.get_blueprint_library()
    semua = {}
    for kend in a.kendaraan:
        thr_list = a.throttle if kend == "vehicle.micro.microlino" else a.throttle_lain
        tabel, detail = {}, {}
        for thr in thr_list:
            veh = w.spawn_actor(lib.find(kend), carla.Transform(carla.Location(x=-299.5, y=250.5, z=0.5)))
            vs = []
            try:
                for i in range(int(20 / 0.05)):
                    veh.apply_control(carla.VehicleControl(throttle=thr, steer=0.0))
                    w.tick()
                    v = veh.get_velocity()
                    vs.append(3.6 * math.hypot(v.x, v.y))
                    if veh.get_location().x > -40:
                        break
            finally:
                veh.destroy()
                w.tick()
            ekor = vs[-40:]                                 # 2 s terakhir
            k = "%.2f" % thr
            tabel[k] = round(float(np.mean(ekor)), 2)
            detail[k] = dict(v_akhir=round(float(ekor[-1]), 2), sd_2s=round(float(np.std(ekor)), 3), langkah=len(vs))
            print("%s throttle %.2f -> %.2f km/jam (sd 2 s terakhir %.3f; tunak jika kecil)" % (kend, thr, tabel[k], detail[k]["sd_2s"]))
        semua[kend] = dict(tabel=tabel, detail=detail)
    json.dump(semua, open(os.path.join(OUT, "kecepatan_%s.json" % time.strftime("%Y%m%d_%H%M%S")), "w"), indent=1)
    d = {}
    if os.path.exists(KAL):
        d = json.load(open(KAL, encoding="utf-8"))
    per = d.get("throttle_ke_kmh_per_kendaraan", {})
    for kend, x in semua.items():
        per[kend] = x["tabel"]
    upd = dict(throttle_ke_kmh_per_kendaraan=per)
    if "vehicle.micro.microlino" in semua:
        upd["throttle_ke_kmh"] = semua["vehicle.micro.microlino"]["tabel"]
    simpan_kal(upd)


def uji_azimut(a, carla, c, w):
    import cv2
    lib = w.get_blueprint_library()
    veh = w.spawn_actor(lib.find("vehicle.micro.microlino"), carla.Transform(carla.Location(x=-240.0, y=250.5, z=0.5)))
    cam, buf = kamera_dika(carla, w, carla.Transform(carla.Location(x=1.5, z=2.0), carla.Rotation(pitch=-15)), parent=veh)
    hasil = {}
    try:
        for az in range(0, 360, 30):
            p = carla.WeatherParameters.ClearNoon
            wp = carla.WeatherParameters()          # objek baru; preset statis jangan diubah
            for k in ("cloudiness", "precipitation", "precipitation_deposits", "wind_intensity", "fog_density",
                      "fog_distance", "wetness", "fog_falloff", "scattering_intensity", "mie_scattering_scale",
                      "rayleigh_scattering_scale", "dust_storm"):
                if hasattr(p, k):
                    setattr(wp, k, getattr(p, k))
            wp.sun_azimuth_angle, wp.sun_altitude_angle = float(az), 10.0
            w.set_weather(wp)
            im = ambil(w, buf, 6)
            cv2.imwrite(os.path.join(OUT, "azimut_%03d.png" % az), im)
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            hasil[az] = dict(terang_atas=float(g[: int(0.35 * g.shape[0])].mean()),
                             jenuh_atas=float((g[: int(0.35 * g.shape[0])] > 250).mean()))
            print("azimut %3d: terang area atas %.1f, piksel jenuh %.3f" % (az, hasil[az]["terang_atas"], hasil[az]["jenuh_atas"]))
    finally:
        cam.destroy(); veh.destroy()
        w.set_weather(carla.WeatherParameters.ClearNoon)
    terbaik = max(hasil, key=lambda k: (hasil[k]["jenuh_atas"], hasil[k]["terang_atas"]))
    json.dump(dict(hasil=hasil, terbaik=terbaik), open(os.path.join(OUT, "azimut.json"), "w"), indent=1)
    print("Kandidat azimut menghadap kamera: %d. CEK azimut_*.png: pilih azimut yang mataharinya tepat di ujung jalan "
          "(metrik kecerahan bisa seri; 21 Nov: 180 dan 210 seri, visual = 180)." % terbaik)
    simpan_kal(dict(azimut_menghadap_kamera=float(terbaik), azimut_catatan="otomatis dari uji_carla_24_25.py azimut; cek visual"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("perintah", choices=["slot", "toggle", "spawn", "kecepatan", "azimut", "semua"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=2000)
    ap.add_argument("--gt", default=os.path.normpath(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_lengkap.json")))
    ap.add_argument("--dir_dika", default=os.path.normpath(os.path.join(DIR, "..", "10_runner", "DQN_Akselerasi vertikal")))
    ap.add_argument("--mesh", default="", help="mesh_path aset lubang untuk uji spawn")
    ap.add_argument("--throttle", type=float, nargs="+", default=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0])
    ap.add_argument("--kendaraan", nargs="+", default=["vehicle.micro.microlino"])
    ap.add_argument("--throttle_lain", type=float, nargs="+", default=[0.1, 0.15, 0.2, 0.25, 0.3, 0.4],
                    help="throttle untuk kendaraan selain Microlino (C4 butuh ±7,6 km/jam)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    carla, c, w = koneksi(a)
    try:
        langkah = ["slot", "toggle", "kecepatan", "azimut"] if a.perintah == "semua" else [a.perintah]
        for p in langkah:
            print("\n===== %s =====" % p)
            dict(slot=uji_slot, toggle=uji_toggle, spawn=uji_spawn, kecepatan=uji_kecepatan, azimut=uji_azimut)[p](a, carla, c, w)
    finally:
        lepas(w)


if __name__ == "__main__":
    main()
