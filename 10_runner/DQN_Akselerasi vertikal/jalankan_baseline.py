"""
jalankan_baseline.py — [#21] Baseline pi_Dika 30 episode x 3 kondisi, dengan lanjut-otomatis.

Kalau CARLA time-out / crash, skrip menunggu, lalu melanjutkan dari seed yang belum selesai
(maks 3 percobaan ulang per kondisi). Seed yang sudah tercatat di ringkasan_episode.csv tidak diulang.

Pakai (Anaconda Prompt, env carla_env, CARLA dibuka TANPA -quality-level):
    python jalankan_baseline.py
    python jalankan_baseline.py --kondisi ClearNight          # satu kondisi saja
"""
import argparse, csv, glob, os, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--kondisi", nargs="+", default=["ClearNoon", "SoftRainNoon", "ClearNight"])
ap.add_argument("--episodes", type=int, default=30)
ap.add_argument("--label", default="Epic")
ap.add_argument("--maks_ulang", type=int, default=3)
ap.add_argument("--jeda", type=int, default=30, help="detik jeda antar kondisi / sebelum coba ulang")
a = ap.parse_args()
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def seed_selesai(cuaca):
    s = set()
    for f in glob.glob(os.path.join("log_runner", f"*_{cuaca}_{a.label}", "ringkasan_episode.csv")):
        s |= {int(r["seed"]) for r in csv.DictReader(open(f))}
    return s


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(os.path.join("log_runner", "jalankan_baseline.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


os.makedirs("log_runner", exist_ok=True)
for cuaca in a.kondisi:
    gagal = 0
    while True:
        sudah = seed_selesai(cuaca)
        sisa = [s for s in range(a.episodes) if s not in sudah]
        if not sisa:
            log(f"{cuaca}: SELESAI {a.episodes}/{a.episodes}")
            break
        if gagal > a.maks_ulang:
            log(f"{cuaca}: BERHENTI setelah {gagal} kegagalan; sisa seed {sisa}. Restart CarlaUE4.exe lalu jalankan ulang skrip ini.")
            break
        mulai = sisa[0]
        # jalankan blok seed berurutan mulai dari seed pertama yang belum ada
        n = 1
        while mulai + n in sisa and n < len(sisa):
            n += 1
        log(f"{cuaca}: mulai seed {mulai}, {n} episode (sudah {len(sudah)}/{a.episodes})")
        rc = subprocess.call([sys.executable, "cleanTest.py", "--cuaca", cuaca, "--episodes", str(n),
                              "--seed_awal", str(mulai), "--tampil", "0", "--label", a.label])
        if rc != 0:
            gagal += 1
            log(f"{cuaca}: cleanTest keluar dengan kode {rc} (kegagalan ke-{gagal}); tunggu {a.jeda * 2} s lalu lanjut")
            time.sleep(a.jeda * 2)
    time.sleep(a.jeda)
log("SEMUA KONDISI DIPROSES. Cek baris SELESAI/BERHENTI di atas.")
