"""
latih_ensemble.py — [#26] Latih pi_ens (bootstrapped DQN, K kepala) pada kondisi ID-0, satu seed per pemanggilan.

Contoh (Anaconda Prompt, env carla_env, CarlaUE4.exe build tetap sudah terbuka TANPA -quality-level):
    python latih_ensemble.py --cek                                  # cetak rencana + tata letak, tanpa CARLA
    python latih_ensemble.py --seed 0                               # pelatihan penuh seed 0 (350.000 langkah)
    python latih_ensemble.py --seed 0 --jam_maks 7                  # berhenti rapi setelah 7 jam; jalankan lagi = lanjut

Anggaran pelatihan dihitung dalam LANGKAH simulasi, bukan episode (24 Nov, setelah pilot): episode awal hanya
80-800 langkah karena agen cepat keluar jalan, jadi "300 episode" berarti jumlah pengalaman yang sangat berbeda
antar seed. Bawaan 350.000 langkah = jumlah train step pi_Dika (training_checkpoint.json: 349.810).

Skrip induk menjalankan proses anak (skrip ini dengan --anak) dan mengulangnya bila CARLA time-out/crash
(maks --maks_ulang kali). Setiap episode selesai -> checkpoint (bobot, target, buffer, RNG, status), jadi
crash hanya mengulang episode yang sedang berjalan. Menjalankan ulang perintah yang sama = melanjutkan.

Seed:
  --seed s           seed TF/NumPy (inisialisasi bobot, masker, kepala per episode) = "seed acak" proposal.
  tata letak latih   episode e memakai ID0 seed (seed_latih_awal + e), seed_latih_awal = 100000 + 10000*s.
                     Tidak bertumpang tindih dengan seed evaluasi (90000-...) maupun data monitor (0-...).
  evaluasi seleksi   tiap --eval_langkah langkah latih: --eval_ep episode ID0 seed 90000.. (tetap untuk semua seed),
                     epsilon 0, aksi = argmax rata-rata Q kepala, tanpa belajar. Model terbaik dipilih dari sini,
                     BUKAN dari reward episode latih (proposal 2.1.5). Gate 2 memakai seed lain (0-29).

Keluaran: 13_ensemble/latih/<nama>/
  konfig.json, episode.csv (1 baris/episode latih), eval.csv (1 baris/episode evaluasi), eval_ringkas.csv,
  bobot/bobot_epNNNN.npz (tiap evaluasi), bobot/bobot_terbaik.npz, bobot/bobot_akhir.npz, titik/ (checkpoint)
"""
from __future__ import annotations

import argparse
import atexit
import csv
import json
import os
import platform
import subprocess
import sys
import time

DIR = os.path.dirname(os.path.abspath(__file__))
DIR_LING = os.path.normpath(os.path.join(DIR, "..", "12_lingkungan"))
DIR_DIKA_DEFAULT = os.path.normpath(os.path.join(DIR, "..", "10_runner", "DQN_Akselerasi vertikal"))
KODE_BATAS_WAKTU = 3

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--nama", default=None, help="nama folder run (bawaan seed<s>_K<K>_b<beta>)")
ap.add_argument("--K", type=int, default=5)
ap.add_argument("--beta_prior", type=float, default=3.0, help="skala randomized prior; 0 = tanpa prior (run 24 Nov: 30)")
ap.add_argument("--double", type=int, default=1, help="1 = target Double DQN (25 Nov); 0 = DQN biasa seperti Dika")
ap.add_argument("--clipnorm", type=float, default=10.0, help="clip norma gradien global; 0 = tanpa clip")
ap.add_argument("--p_masker", type=float, default=0.5)
ap.add_argument("--langkah_total", type=int, default=350_000, help="anggaran langkah latih (pi_Dika: 349.810)")
ap.add_argument("--episodes", type=int, default=0, help="opsional: batas episode latih (0 = tanpa batas)")
ap.add_argument("--kapasitas", type=int, default=100_000)
ap.add_argument("--min_replay", type=int, default=1000, help="Dika: 1000")
ap.add_argument("--eps_awal", type=float, default=0.1, help="epsilon setelah buffer >= min_replay")
ap.add_argument("--eps_akhir", type=float, default=0.02)
ap.add_argument("--eps_langkah", type=int, default=100_000, help="epsilon turun linear eps_awal -> eps_akhir")
ap.add_argument("--eval_langkah", type=int, default=50_000, help="evaluasi seleksi tiap N langkah latih")
ap.add_argument("--eval_ep", type=int, default=10)
ap.add_argument("--eval_seed_awal", type=int, default=90000)
ap.add_argument("--seed_latih_awal", type=int, default=None)
ap.add_argument("--reward", default="perbaikan", choices=["perbaikan", "dika"])
ap.add_argument("--backend", default="grid", choices=["grid", "spawn"])
ap.add_argument("--label", default="Epic")
ap.add_argument("--maks_langkah", type=int, default=6000, help="pengaman; env Dika sudah timeout di 5000")
ap.add_argument("--jam_maks", type=float, default=0.0, help="0 = tanpa batas; >0 = berhenti rapi setelah N jam")
ap.add_argument("--maks_ulang", type=int, default=5)
ap.add_argument("--jeda", type=int, default=60)
ap.add_argument("--carla_exe", default="", help="opsional: path CarlaUE4.exe untuk dijalankan ulang otomatis setelah crash")
ap.add_argument("--dir_dika", default=DIR_DIKA_DEFAULT)
ap.add_argument("--yolo", default="Yolo/best_pure.pt")
ap.add_argument("--gt_v2", default=os.path.normpath(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_lengkap.json")))
ap.add_argument("--kalibrasi", default=os.path.join(DIR_LING, "kalibrasi_lingkungan.json"))
ap.add_argument("--out", default=os.path.join(DIR, "latih"))
ap.add_argument("--cek", action="store_true")
ap.add_argument("--anak", action="store_true", help=argparse.SUPPRESS)
A = ap.parse_args()
if A.seed_latih_awal is None:
    A.seed_latih_awal = 100000 + 10000 * A.seed
A.nama = A.nama or "seed%d_K%d_b%g%s" % (A.seed, A.K, A.beta_prior, "_ddqn" if A.double else "")
RUN = os.path.join(A.out, A.nama)

sys.path.insert(0, DIR_LING)
sys.path.insert(0, DIR)


def epsilon_untuk(langkah, buffer_cukup):
    if not buffer_cukup:
        return 1.0
    f = min(1.0, langkah / float(max(A.eps_langkah, 1)))
    return A.eps_awal + f * (A.eps_akhir - A.eps_awal)


def batas_tercapai(st):
    return st["langkah"] >= A.langkah_total or (A.episodes > 0 and st["episode"] >= A.episodes)


def baca_status():
    p = os.path.join(RUN, "titik", "status.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


# ================================================================================================
# Induk: jalankan anak, ulangi setelah crash
# ================================================================================================
def induk():
    if A.cek:
        return cek()
    os.makedirs(RUN, exist_ok=True)
    log_induk = os.path.join(RUN, "induk.log")

    def log(m):
        s = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), m)
        print(s, flush=True)
        with open(log_induk, "a", encoding="utf-8") as f:
            f.write(s + "\n")

    t0 = time.time()
    gagal = 0
    argv = [a for a in sys.argv[1:]]
    while True:
        st = baca_status()
        if st and st.get("selesai"):
            log("SELESAI: %d episode / %d langkah latih, skor eval terbaik %.3f di episode %s" % (
                st["episode"], st.get("langkah", 0), st.get("skor_terbaik", float("nan")), st.get("ep_terbaik")))
            return 0
        sisa_jam = 0.0
        if A.jam_maks > 0:
            sisa_jam = A.jam_maks - (time.time() - t0) / 3600.0
            if sisa_jam <= 0.05:
                log("BATAS WAKTU %.1f jam tercapai. Jalankan perintah yang sama lagi untuk melanjutkan." % A.jam_maks)
                return 0
        cmd = [sys.executable, os.path.abspath(__file__)] + [a for a in argv if a != "--anak"] + ["--anak"]
        if A.jam_maks > 0:
            cmd = _ganti_arg(cmd, "--jam_maks", "%.4f" % sisa_jam)
        log("mulai proses anak (episode selesai: %s)" % (st["episode"] if st else 0))
        rc = subprocess.call(cmd)
        if rc == 0 or rc == KODE_BATAS_WAKTU:
            if rc == KODE_BATAS_WAKTU:
                log("BATAS WAKTU tercapai di proses anak. Jalankan perintah yang sama lagi untuk melanjutkan.")
                return 0
            continue
        gagal += 1
        log("proses anak keluar kode %d (kegagalan ke-%d dari maks %d)" % (rc, gagal, A.maks_ulang))
        if gagal > A.maks_ulang:
            log("BERHENTI: terlalu banyak kegagalan. Restart CarlaUE4.exe lalu jalankan perintah yang sama.")
            return 1
        if A.carla_exe:
            _restart_carla(log)
        time.sleep(A.jeda)


def _ganti_arg(cmd, nama, nilai):
    if nama in cmd:
        i = cmd.index(nama)
        return cmd[:i + 1] + [nilai] + cmd[i + 2:]
    return cmd + [nama, nilai]


def _restart_carla(log):
    """Belum diuji di Windows (TA Keva). Matikan semua CarlaUE4 lalu buka lagi tanpa -quality-level."""
    log("restart CARLA: %s" % A.carla_exe)
    if platform.system() == "Windows":
        for im in ("CarlaUE4-Win64-Shipping.exe", "CarlaUE4.exe"):
            subprocess.call(["taskkill", "/IM", im, "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(10)
    subprocess.Popen([A.carla_exe], cwd=os.path.dirname(A.carla_exe))
    time.sleep(90)                     # peta train_fix butuh waktu dimuat


def cek():
    from skenario import resolusi
    from generator_tata_letak import buat_tata_letak, muat_slot_grid
    slot = muat_slot_grid(A.gt_v2)
    print("Run: %s" % RUN)
    print("K=%d beta_prior=%g p_masker=%g | %d langkah latih | eval %d ep tiap %d langkah (seed %d..%d)" % (
        A.K, A.beta_prior, A.p_masker, A.langkah_total, A.eval_ep, A.eval_langkah, A.eval_seed_awal,
        A.eval_seed_awal + A.eval_ep - 1))
    n_eval = -(-A.langkah_total // A.eval_langkah)
    print("Perkiraan: latih %.1f jam (23 langkah/s, pilot 24 Nov) + %d evaluasi x %d ep (maks %.1f jam bila semua finis)"
          % (A.langkah_total / 23 / 3600, n_eval, A.eval_ep, n_eval * A.eval_ep * 2900 / 23 / 3600))
    for nama, seeds in (("latih", [A.seed_latih_awal + e for e in range(3)]),
                        ("eval", [A.eval_seed_awal + i for i in range(A.eval_ep)])):
        for s in seeds:
            sp = resolusi("ID0", 1, s, "konstan", A.backend)
            tl = buat_tata_letak(s, sp["konfig_tata_letak"], A.backend, slot)
            print("  %-5s seed %6d | cuaca %-10s | %2d lubang %s | offset %s" % (
                nama, s, sp["cuaca_target"]["basis"], tl.n, [l["id"] for l in tl.lubang],
                (round(sp["spawn"]["offset_x_aktual"], 2), round(sp["spawn"]["offset_y_aktual"], 2))))
    st = baca_status()
    print("Status checkpoint:", st if st else "belum ada (mulai dari awal)")
    return 0


# ================================================================================================
# Anak: pelatihan sesungguhnya
# ================================================================================================
AKHIR = {800.0: "finis", -300.0: "tabrakan", -200.0: "keluar_jalan", -10.0: "timeout"}
KOLOM_EP = ["episode", "langkah_total", "seed_tata_letak", "cuaca", "n_lubang", "kepala", "epsilon", "epsilon_akhir", "langkah", "detik",
            "faktor_realtime", "reward", "hits", "avoids", "akhir", "x_akhir", "loss_rata", "n_train", "buffer",
            "cv_aksi_median", "std_q_rata", "abs_q_rata", "frac_aksi0", "frac_aksi1", "frac_aksi2", "verif_percobaan"]
KOLOM_EVAL = ["episode_latih", "seed", "cuaca", "n_lubang", "langkah", "detik", "reward", "hits", "avoids", "akhir",
              "x_akhir", "cv_aksi_median", "std_q_rata", "abs_q_rata", "frac_aksi0", "frac_aksi1", "frac_aksi2"]
KOLOM_RING = ["episode_latih", "langkah_latih", "n_ep", "lubang", "avoids", "hits", "skor", "frac_finis", "reward_rata", "terbaik"]


def _tambah_csv(path, kolom, baris):
    baru = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom)
        if baru:
            w.writeheader()
        w.writerow(baris)


def anak():
    import numpy as np
    sys.path.insert(0, A.dir_dika)
    os.chdir(A.dir_dika)
    import carla   # noqa: F401
    from env_latih import CarlaEnvLatih          # env (torch/ultralytics) dulu, baru TensorFlow (pola Dika)
    from skenario import muat_kalibrasi, resolusi
    try:
        import tensorflow as tf
        for g in tf.config.list_physical_devices("GPU"):
            tf.config.experimental.set_memory_growth(g, True)
    except Exception:
        pass
    from agen_ensemble import AgenEnsemble

    t_mulai = time.time()
    os.makedirs(os.path.join(RUN, "bobot"), exist_ok=True)
    os.makedirs(os.path.join(RUN, "titik"), exist_ok=True)
    kal = muat_kalibrasi(A.kalibrasi)

    st = baca_status()
    if st:                               # cek SEBELUM membuka CARLA (keluar di sini tidak meninggalkan mode sinkron)
        # konfigurasi harus sama dengan run yang dilanjutkan
        with open(os.path.join(RUN, "konfig.json")) as f:
            k_lama = json.load(f)["argumen"]
        for kunci in ("K", "beta_prior", "p_masker", "kapasitas", "seed", "seed_latih_awal", "eval_seed_awal",
                      "eval_ep", "eval_langkah", "reward", "backend", "eps_awal", "eps_akhir", "eps_langkah",
                      "min_replay", "double", "clipnorm"):
            if k_lama.get(kunci) != getattr(A, kunci):
                raise SystemExit("Konfigurasi berbeda dengan run yang ada (%s: %r vs %r). Pakai --nama lain."
                                 % (kunci, k_lama.get(kunci), getattr(A, kunci)))

    # env (YOLO/torch) dibuat SEBELUM model TensorFlow, sama dengan jalankan_skenario.py; urutan terbalik
    # membuat proses crash (LLVM ganda) di sebagian kombinasi versi torch/TF.
    env = CarlaEnvLatih(reward=A.reward, backend=A.backend, gt_v2_path=A.gt_v2, kalibrasi=kal, town="train_fix",
                        yolo_model_path=A.yolo,
                        gt_json_path=os.path.join(os.path.dirname(A.gt_v2), "pothole_gt_v2_segmen_dika.json"),
                        weather=carla.WeatherParameters.ClearNoon)
    _ditutup = [False]

    def tutup_env():                     # dipanggil di finally DAN atexit: error apa pun -> CARLA kembali asinkron
        if _ditutup[0]:
            return
        _ditutup[0] = True
        try:
            env.tutup_lingkungan()
        finally:
            env.close()
    atexit.register(tutup_env)
    agen = AgenEnsemble(K=A.K, beta_prior=A.beta_prior, p_masker=A.p_masker, kapasitas=A.kapasitas, seed=A.seed,
                        min_replay=A.min_replay, double=bool(A.double), clipnorm=A.clipnorm)
    if st:
        agen.muat_bobot(os.path.join(RUN, "titik", "bobot_titik.npz"))
        agen.muat_titik(os.path.join(RUN, "titik", "titik_agen.npz"))
        agen.buffer.muat(os.path.join(RUN, "titik", "buffer.npz"))
        print("▶️  Lanjut setelah episode %d (buffer %d, train step %d)" % (st["episode"], len(agen.buffer), agen.n_train))
    else:
        st = dict(episode=0, langkah=0, eval_berikut=A.eval_langkah, eval_tertunda=False, skor_terbaik=-1.0,
                  ep_terbaik=None, langkah_terbaik=None, selesai=False, eval_selesai=[])
        with open(os.path.join(RUN, "konfig.json"), "w") as f:
            json.dump(dict(argumen=vars(A), agen=agen.konfig(), versi=_versi_paket(),
                           mulai=time.strftime("%Y-%m-%d %H:%M:%S")), f, indent=1)

    gt_tmp = os.path.join(RUN, "titik", "gt_episode.json")

    def jalankan_episode(seed_tl, latih, epsilon=0.0):
        sp = resolusi("ID0", 1, seed_tl, "konstan", A.backend)
        info_siap = env.siapkan_episode(sp, gt_tmp)
        state = env.reset()
        if latih:
            agen.pilih_kepala_episode()
        t0 = time.perf_counter()
        done, step, total, info, reward = False, 0, 0.0, {}, 0.0
        losses, cvs, stds, abss, aksi_n = [], [], [], [], [0, 0, 0]
        while not done and step < A.maks_langkah:
            s = np.asarray(state["vehicle_state"], np.float32)
            q = agen.q_semua(s)                                     # (K, A)
            if latih:
                a = (int(agen.rng.integers(agen.n_aksi)) if agen.rng.random() < epsilon
                     else int(np.argmax(q[agen.kepala_aktif])))
            else:
                a = int(np.argmax(q.mean(axis=0)))
            mu, sd = q[:, a].mean(), q[:, a].std()
            cvs.append(sd / max(abs(mu), 1e-6))
            stds.append(sd)
            abss.append(abs(mu))
            aksi_n[a] += 1
            state2, reward, done, info = env.step(a)
            total += reward
            step += 1
            if latih:
                agen.buffer.tambah(s, a, reward, np.asarray(state2["vehicle_state"], np.float32), done)
                l = agen.latih()
                if l is not None:
                    losses.append(l)
                epsilon = epsilon_untuk(st["langkah"] + step, len(agen.buffer) >= agen.min_replay)
            state = state2
        detik = time.perf_counter() - t0
        akhir = AKHIR.get(round(float(reward), 1), "maks_langkah" if step >= A.maks_langkah else "lain")
        n = max(step, 1)
        return dict(epsilon_akhir=round(epsilon, 4), cuaca=sp["cuaca_target"]["basis"], n_lubang=env.tata_letak.n, langkah=step,
                    detik=round(detik, 1), faktor_realtime=round(step * 0.05 / max(detik, 1e-9), 2),
                    reward=round(total, 2), hits=info.get("hits", 0), avoids=info.get("avoids", 0), akhir=akhir,
                    x_akhir=round(env.vehicle.get_location().x, 2),
                    loss_rata=round(float(np.mean(losses)), 4) if losses else "",
                    cv_aksi_median=round(float(np.median(cvs)), 4), std_q_rata=round(float(np.mean(stds)), 4), abs_q_rata=round(float(np.mean(abss)), 3),
                    frac_aksi0=round(aksi_n[0] / n, 3), frac_aksi1=round(aksi_n[1] / n, 3),
                    frac_aksi2=round(aksi_n[2] / n, 3),
                    verif_percobaan=info_siap["backend"]["verifikasi"].get("percobaan", ""))

    def evaluasi(ep_latih):
        hasil = []
        for i in range(A.eval_ep):
            s = A.eval_seed_awal + i
            r = jalankan_episode(s, latih=False)
            hasil.append(r)
            row = {k: r[k] for k in KOLOM_EVAL if k in r}
            row.update(episode_latih=ep_latih, seed=s)
            _tambah_csv(os.path.join(RUN, "eval.csv"), KOLOM_EVAL, row)
            print("   eval seed %d: %s, avoids %s/%s lubang" % (s, r["akhir"], r["avoids"], r["n_lubang"]))
        lub = sum(r["n_lubang"] for r in hasil)
        av = sum(r["avoids"] for r in hasil)
        skor = av / max(lub, 1)                     # lubang tak tercapai (tabrakan sebelum lubang) = gagal
        finis = float(np.mean([r["akhir"] == "finis" for r in hasil]))
        rew = float(np.mean([r["reward"] for r in hasil]))
        terbaik = (skor, finis, rew) > tuple(st.get("kunci_terbaik", (-1.0, -1.0, -1e9)))
        agen.simpan_bobot(os.path.join(RUN, "bobot", "bobot_ep%04d.npz" % ep_latih), dict(episode_latih=ep_latih))
        if terbaik:
            agen.simpan_bobot(os.path.join(RUN, "bobot", "bobot_terbaik.npz"),
                              dict(episode_latih=ep_latih, skor_eval=skor, frac_finis=finis))
            st.update(skor_terbaik=skor, ep_terbaik=ep_latih, langkah_terbaik=st["langkah"],
                      kunci_terbaik=[skor, finis, rew])
        _tambah_csv(os.path.join(RUN, "eval_ringkas.csv"), KOLOM_RING,
                    dict(episode_latih=ep_latih, langkah_latih=st["langkah"], n_ep=len(hasil), lubang=lub, avoids=av,
                         hits=sum(r["hits"] for r in hasil), skor=round(skor, 4), frac_finis=round(finis, 3),
                         reward_rata=round(rew, 1), terbaik=int(terbaik)))
        st["eval_selesai"].append(ep_latih)
        st["eval_tertunda"] = False
        while st["eval_berikut"] <= st["langkah"]:
            st["eval_berikut"] += A.eval_langkah
        print("📊 EVAL setelah episode %d: skor %.3f (avoids %d/%d lubang), finis %.0f%%%s" % (
            ep_latih, skor, av, lub, 100 * finis, "  🔥 TERBAIK" if terbaik else ""))
        simpan_titik()

    def simpan_titik():
        d = os.path.join(RUN, "titik")
        agen.simpan_bobot(os.path.join(d, "bobot_titik.npz"))
        agen.simpan_titik(os.path.join(d, "titik_agen.npz"))
        tmp = os.path.join(d, "buffer.tmp.npz")
        agen.buffer.simpan(tmp)
        os.replace(tmp, os.path.join(d, "buffer.npz"))
        tmp = os.path.join(d, "status.tmp.json")
        with open(tmp, "w") as f:
            json.dump(st, f, indent=1)
        os.replace(tmp, os.path.join(d, "status.json"))

    def perlu_eval():
        if st["episode"] == 0 or st["episode"] in st["eval_selesai"]:
            return False
        return st["langkah"] >= st["eval_berikut"] or batas_tercapai(st)

    def waktu_habis():
        return A.jam_maks > 0 and (time.time() - t_mulai) / 3600.0 >= A.jam_maks

    rc = 0
    try:
        if perlu_eval():                                # crash terjadi di tengah evaluasi
            evaluasi(st["episode"])
        while not batas_tercapai(st):
            if waktu_habis():
                rc = KODE_BATAS_WAKTU
                break
            ep = st["episode"] + 1
            seed_tl = A.seed_latih_awal + ep - 1
            eps = epsilon_untuk(st["langkah"], len(agen.buffer) >= agen.min_replay)
            r = jalankan_episode(seed_tl, latih=True, epsilon=eps)
            st["langkah"] += r["langkah"]
            row = dict(r, episode=ep, seed_tata_letak=seed_tl, kepala=agen.kepala_aktif, epsilon=round(eps, 3),
                       n_train=agen.n_train, buffer=len(agen.buffer), langkah_total=st["langkah"])
            _tambah_csv(os.path.join(RUN, "episode.csv"), KOLOM_EP, {k: row.get(k, "") for k in KOLOM_EP})
            st["episode"] = ep
            simpan_titik()
            print("EPISODE %d (%d/%d langkah) seed %d kepala %d eps %.2f: %d langkah, %.0f s, %s, reward %.1f, hits %s avoids %s/%s, cv %.3f"
                  % (ep, st["langkah"], A.langkah_total, seed_tl, agen.kepala_aktif, eps, r["langkah"], r["detik"], r["akhir"], r["reward"],
                     r["hits"], r["avoids"], r["n_lubang"], r["cv_aksi_median"]))
            if perlu_eval():
                evaluasi(ep)
        if batas_tercapai(st) and rc == 0:
            agen.simpan_bobot(os.path.join(RUN, "bobot", "bobot_akhir.npz"), dict(episode_latih=st["episode"]))
            st["selesai"] = True
            simpan_titik()
            print("🎉 SELESAI. Terbaik: episode %s, skor eval %.3f" % (st["ep_terbaik"], st["skor_terbaik"]))
    except KeyboardInterrupt:
        print("\n⚠️  Dihentikan (Ctrl+C). Episode yang belum selesai akan diulang saat skrip dijalankan lagi.")
        rc = KODE_BATAS_WAKTU          # jangan diulang otomatis oleh induk
    finally:
        tutup_env()
    return rc


def _versi_paket():
    v = dict(python=platform.python_version())
    for m in ("tensorflow", "torch", "ultralytics", "numpy", "carla"):
        try:
            v[m] = getattr(__import__(m), "__version__", "?")
        except Exception:
            v[m] = None
    return v


if __name__ == "__main__":
    if A.anak:
        sys.exit(anak())
    try:
        sys.exit(induk())
    except KeyboardInterrupt:
        print("\n⚠️  Dihentikan. Checkpoint episode terakhir tersimpan; jalankan perintah yang sama untuk melanjutkan.")
        sys.exit(KODE_BATAS_WAKTU)
