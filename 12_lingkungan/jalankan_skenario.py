"""
jalankan_skenario.py — [#25] Runner satu kondisi (kode x tingkat x mode) untuk banyak seed, dengan logger
fitur/logit/Q. Kebijakan = pi_Dika (model_best.h5, epsilon 0) kecuali --model diganti.

Contoh (Anaconda Prompt, env carla_env, CarlaUE4.exe sudah terbuka TANPA -quality-level):
    python jalankan_skenario.py --kode ID0 --episodes 5
    python jalankan_skenario.py --kode A3 --tingkat 2 --mode transisi --episodes 30
    python jalankan_skenario.py --kode C1 --tingkat 1 --episodes 30          # tata letak asli Dika (grid)
    python jalankan_skenario.py --cek --kode A2 --tingkat 3 --seed_awal 0 --episodes 3   # tanpa CARLA

Lanjut otomatis: seed yang sudah tercatat di ringkasan_episode.csv folder run dengan konfigurasi sama
(kode, tingkat, mode, backend, label) dilewati. Folder run:
    log_skenario/<waktu>_<kode>_t<tingkat>_<mode>_<backend>_<label>/
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import platform
import sys
import time

DIR = os.path.dirname(os.path.abspath(__file__))
DIR_DIKA_DEFAULT = os.path.normpath(os.path.join(DIR, "..", "10_runner", "DQN_Akselerasi vertikal"))

ap = argparse.ArgumentParser()
ap.add_argument("--kode", default="ID0")
ap.add_argument("--tingkat", type=int, default=1)
ap.add_argument("--mode", default="konstan", choices=["konstan", "transisi"])
ap.add_argument("--backend", default="grid", choices=["grid", "spawn"])
ap.add_argument("--episodes", type=int, default=1)
ap.add_argument("--seed_awal", type=int, default=0)
ap.add_argument("--label", default="Epic", help="kualitas render (tidak bisa dibaca dari API)")
ap.add_argument("--rampa", type=float, default=20.0, help="panjang rampa transisi (m); 0 = mendadak")
ap.add_argument("--dir_dika", default=DIR_DIKA_DEFAULT)
ap.add_argument("--model", default="model_best.h5", help="relatif terhadap --dir_dika atau path absolut")
ap.add_argument("--yolo", default="Yolo/best_pure.pt")
ap.add_argument("--gt_v2", default=os.path.normpath(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_lengkap.json")))
ap.add_argument("--kalibrasi", default=os.path.join(DIR, "kalibrasi_lingkungan.json"))
ap.add_argument("--simpan_fitur", type=int, default=1, help="1 = simpan npz fitur/logit (±3-6 MB/episode)")
ap.add_argument("--topk_anchor", type=int, default=100)
ap.add_argument("--maks_langkah", type=int, default=10000)
ap.add_argument("--out", default=os.path.join(DIR, "log_skenario"))
ap.add_argument("--tanpa_lanjut", action="store_true", help="jangan lewati seed yang sudah ada")
ap.add_argument("--cek", action="store_true", help="hanya cetak spesifikasi + tata letak (tanpa CARLA)")
A = ap.parse_args()

sys.path.insert(0, DIR)
from skenario import muat_kalibrasi, resolusi, spesifikasi_ke_json, throttle_untuk   # noqa: E402
from generator_tata_letak import buat_tata_letak, muat_slot_grid                      # noqa: E402

NAMA_KONFIG = "%s_t%d_%s_%s_%s" % (A.kode, A.tingkat, A.mode, A.backend, A.label)


def seed_sudah():
    s = set()
    for f in glob.glob(os.path.join(A.out, "*_" + NAMA_KONFIG, "ringkasan_episode.csv")):
        with open(f) as fh:
            s |= {int(r["seed"]) for r in csv.DictReader(fh)}
    return s


def daftar_seed():
    semua = list(range(A.seed_awal, A.seed_awal + A.episodes))
    if A.tanpa_lanjut or A.cek:
        return semua
    sudah = seed_sudah()
    return [s for s in semua if s not in sudah]


def mode_cek():
    slot = muat_slot_grid(A.gt_v2)
    kal = muat_kalibrasi(A.kalibrasi)
    for s in daftar_seed():
        sp = resolusi(A.kode, A.tingkat, s, A.mode, A.backend, jarak_rampa_m=A.rampa)
        tl = buat_tata_letak(s, sp["konfig_tata_letak"], A.backend, slot)
        try:
            thr = "%.3f" % throttle_untuk(sp.get("kecepatan"), kal, sp.get("kendaraan"))
        except RuntimeError as e:
            thr = "BELUM: %s" % e
        print("seed %d | %s t%d %s | cuaca awal %s -> target %s | lampu %s | korupsi %s | throttle %s | kendaraan %s"
              % (s, A.kode, A.tingkat, A.mode, sp["cuaca_awal"], sp["cuaca_target"], sp["lampu"], sp["korupsi"],
                 thr, sp["kendaraan"]))
        print("        spawn %s | transisi %s | lubang %d %s | sidik %s" % (
            sp["spawn"], sp["transisi"], tl.n, [l["id"] for l in tl.lubang], tl.sidik()))


if A.cek:
    mode_cek()
    sys.exit(0)

# ------------------------------------------------------------------------------------------------
# Mode CARLA
# ------------------------------------------------------------------------------------------------
import numpy as np  # noqa: E402

sys.path.insert(0, A.dir_dika)
os.chdir(A.dir_dika)                    # path relatif kode Dika (Yolo/, model) tetap berlaku
import carla  # noqa: E402
# Urutan import sama dengan cleanTest.py Dika: env (torch/ultralytics) dulu, baru TensorFlow.
from env_skenario import CarlaEnvSkenario   # noqa: E402
from logger_skenario import LoggerEpisode   # noqa: E402

try:                                    # TF jangan memesan seluruh VRAM (tidak mengubah hasil)
    import tensorflow as tf
    for g in tf.config.list_physical_devices("GPU"):
        tf.config.experimental.set_memory_growth(g, True)
except Exception as _e:                 # noqa: F841
    pass
from agent.dqn_agent import DQNAgent    # noqa: E402

AKHIR = {800.0: "finis", -300.0: "tabrakan", -200.0: "keluar_jalan", -10.0: "timeout"}


def main():
    seeds = daftar_seed()
    if not seeds:
        print("Semua seed %d..%d untuk %s sudah selesai." % (A.seed_awal, A.seed_awal + A.episodes - 1, NAMA_KONFIG))
        return 0
    # validasi semua spesifikasi SEBELUM membuka CARLA (gagal cepat)
    kal = muat_kalibrasi(A.kalibrasi)
    specs = {s: resolusi(A.kode, A.tingkat, s, A.mode, A.backend, jarak_rampa_m=A.rampa) for s in seeds}
    for sp in specs.values():
        throttle_untuk(sp.get("kecepatan"), kal, sp.get("kendaraan"))

    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(A.out, "%s_%s" % (stamp, NAMA_KONFIG))
    os.makedirs(run_dir, exist_ok=True)
    print("Folder run:", run_dir)

    env = CarlaEnvSkenario(backend=A.backend, gt_v2_path=A.gt_v2, kalibrasi=kal, topk_anchor=A.topk_anchor,
                           town="train_fix", yolo_model_path=A.yolo,
                           gt_json_path=os.path.join(os.path.dirname(A.gt_v2), "pothole_gt_v2_segmen_dika.json"),
                           weather=carla.WeatherParameters.ClearNoon)
    with open(os.path.join(run_dir, "grid_slot.json"), "w") as f:
        json.dump(dict(ringkas=env.grid.ringkas(), peta=env.grid.peta, nama=env.grid.nama), f, indent=1)
    if env.grid.tidak_ketemu:
        print("⚠️  slot tak ketemu:", env.grid.tidak_ketemu)

    agent = DQNAgent(num_actions=env.num_actions)
    agent.load(A.model)
    agent.epsilon = 0.0

    f_ring = open(os.path.join(run_dir, "ringkasan_episode.csv"), "w", newline="")
    w_ring = csv.writer(f_ring)
    w_ring.writerow(["episode", "seed", "kode", "tingkat", "mode", "backend", "n_lubang", "sidik_tata_letak",
                     "offset_x", "offset_y", "heading", "throttle", "langkah", "detik", "faktor_realtime", "hits",
                     "avoids", "reward", "akhir", "x_akhir", "x_onset", "langkah_onset", "hook_tidak_cocok",
                     "kamera_telat", "tabrakan", "tabrakan_lubang", "verif_percobaan", "verif_conf_min"])
    versi = dict(python=platform.python_version(), carla_client=_versi("carla"), ultralytics=_versi("ultralytics"),
                 torch=_versi("torch"), tensorflow=_versi("tensorflow"))
    try:
        versi["carla_server"] = env.client.get_server_version()
    except Exception:
        pass

    try:
        for ep, seed in enumerate(seeds, start=1):
            sp = specs[seed]
            nama = "ep%03d_seed%d" % (ep, seed)
            gt_path = os.path.join(run_dir, "gt_%s.json" % nama)
            info_siap = env.siapkan_episode(sp, gt_path)
            state = env.reset()
            geo = env.ukur_geometri_kendaraan()
            persepsi = env.rekam_persepsi
            log = LoggerEpisode(run_dir, ep, seed, simpan_fitur=bool(A.simpan_fitur), n_aksi=env.num_actions)
            env.kamera_telat = 0
            t0 = time.perf_counter()
            done, step, total, info, reward = False, 0, 0.0, {}, 0.0
            langkah_onset = None                # baris pertama yang frame-nya dirender dengan f_transisi > 0
            while not done and step < A.maks_langkah:
                pose = _pose(env)
                f_tr = env._f_terpasang if env.transisi is not None else 1.0
                if env.transisi is not None and f_tr > 0 and langkah_onset is None:
                    langkah_onset = step + 1
                cuaca = env._cuaca_terpasang
                vs = np.asarray(state["vehicle_state"], dtype=np.float32)
                q = agent.network(vs[None, :], training=False).numpy()[0]   # = select_action (epsilon 0)
                action = int(np.argmax(q))
                next_state, reward, done, info = env.step(action)
                total += reward
                step += 1
                log.catat(step, pose, action, q, vs, persepsi, f_tr, cuaca, reward, done, info)
                state, persepsi = next_state, env.rekam_persepsi
            detik = time.perf_counter() - t0
            akhir = AKHIR.get(round(float(reward), 1), "maks_langkah" if step >= A.maks_langkah else "lain")
            meta = dict(skenario=spesifikasi_ke_json(sp), siap=info_siap, geometri_kendaraan=geo, versi=versi,
                        spawn_offset=list(env.spawn_offset), langkah_onset=langkah_onset,
                        detik=round(detik, 2), akhir=akhir, hits=info.get("hits", 0), avoids=info.get("avoids", 0),
                        tabrakan=env.tabrakan_log, tabrakan_lubang=env.tabrakan_lubang, label_render=A.label)
            meta = log.tutup(meta, env.tata_letak.ke_gt())
            gagal_hook = meta["hook_tidak_cocok"] + meta["tanpa_rekam_persepsi"]   # tidak cocok + tidak terekam
            if gagal_hook > 0.01 * max(step, 1):
                print("⚠️⚠️  PERSEPSI TIDAK TEREKAM di %d dari %d langkah. Perilaku agen tetap valid, tetapi data "
                      "monitor episode ini tidak lengkap. Cek pesan 'hook persepsi error' di atas." % (gagal_hook, step))
            tr = sp.get("transisi") or {}
            w_ring.writerow([ep, seed, A.kode, A.tingkat, A.mode, A.backend, env.tata_letak.n, env.tata_letak.sidik(),
                             round(env.spawn_offset[0], 3), round(env.spawn_offset[1], 3), env.heading_awal,
                             round(env.throttle, 4), step, round(detik, 1), round(step * 0.05 / max(detik, 1e-9), 2),
                             info.get("hits", 0), info.get("avoids", 0), round(total, 2), akhir,
                             round(env.vehicle.get_location().x, 2), tr.get("x_onset", ""),
                             langkah_onset if langkah_onset is not None else "",
                             gagal_hook, env.kamera_telat,
                             ";".join("%s@x%s" % (n, x) for _, n, x in env.tabrakan_log), len(env.tabrakan_lubang),
                             info_siap["backend"]["verifikasi"].get("percobaan", ""),
                             info_siap["backend"]["verifikasi"].get("conf_min", "")])
            f_ring.flush()
            print("EPISODE %d seed %d: %d langkah, %.1f s, akhir %s, hits %s avoids %s, persepsi gagal/tak terekam %d"
                  % (ep, seed, step, detik, akhir, info.get("hits", 0), info.get("avoids", 0), gagal_hook))
    except KeyboardInterrupt:
        print("\n⚠️  Dihentikan (Ctrl+C). Seed yang belum tercatat akan diulang saat skrip dijalankan lagi.")
    finally:
        f_ring.close()
        try:
            env.tutup_lingkungan()
        finally:
            env.close()
    return 0


def _pose(env):
    snap = env.world.get_snapshot()
    tf_ = env.vehicle.get_transform()
    v = env.vehicle.get_velocity()
    c = env.vehicle.get_control()
    return dict(t_sim=round(snap.timestamp.elapsed_seconds, 3), frame_dunia=snap.frame, frame_kamera=env.camera_frame,
                x=round(tf_.location.x, 4), y=round(tf_.location.y, 4), z=round(tf_.location.z, 4),
                yaw=round(tf_.rotation.yaw, 3), v_kmh=round(3.6 * math.hypot(v.x, v.y), 3),
                steer=round(c.steer, 3), throttle=round(c.throttle, 3))


def _versi(mod):
    try:
        m = __import__(mod)
        return getattr(m, "__version__", "?")
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())
