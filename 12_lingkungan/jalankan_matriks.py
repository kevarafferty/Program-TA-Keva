"""
jalankan_matriks.py — [#25] Jalankan banyak kondisi berurutan dengan lanjut-otomatis (pola jalankan_baseline.py).

Setiap kondisi = KODE:TINGKAT:MODE (mis. A3:2:transisi). Kalau CARLA time-out/crash, skrip menunggu lalu
memanggil jalankan_skenario.py lagi; seed yang sudah tercatat tidak diulang (maks --maks_ulang kali per kondisi).

    python jalankan_matriks.py --cek                      # daftar kondisi + perkiraan waktu, tanpa CARLA
    python jalankan_matriks.py                            # matriks bawaan (grid), 30 episode per kondisi
    python jalankan_matriks.py --kondisi ID0:1:konstan A3:2:transisi --episodes 5
"""
import argparse
import os
import subprocess
import sys
import time

DIR = os.path.dirname(os.path.abspath(__file__))

# Matriks bawaan: semua yang bisa dibuat dengan backend grid tanpa kalibrasi tambahan, ditambah
# A4/C2/E2 (butuh kalibrasi_lingkungan.json dari uji_carla_24_25.py). 3 tingkat untuk kondisi utama A1-A3.
MATRIKS_BAWAAN = (
    ["REG:1:konstan", "REG:2:konstan", "REG:3:konstan", "ID0:1:konstan"]
    + ["A1:%d:konstan" % t for t in (1, 2, 3)] + ["A2:%d:konstan" % t for t in (1, 2, 3)]
    + ["A3:%d:konstan" % t for t in (1, 2, 3)]
    + ["A1:2:transisi", "A2:2:transisi", "A3:2:transisi", "A5:2:transisi"]
    + ["A4:2:konstan", "A5:2:konstan", "A6:2:konstan"]
    + ["C1:1:konstan", "C2:1:konstan", "C2:3:konstan", "C3:2:konstan", "C4:3:konstan", "D1:1:konstan"]
    + ["E1:1:konstan", "E2:1:konstan"]
)

ap = argparse.ArgumentParser()
ap.add_argument("--kondisi", nargs="+", default=MATRIKS_BAWAAN)
ap.add_argument("--episodes", type=int, default=30)
ap.add_argument("--seed_awal", type=int, default=0)
ap.add_argument("--backend", default="grid")
ap.add_argument("--label", default="Epic")
ap.add_argument("--maks_ulang", type=int, default=3)
ap.add_argument("--jeda", type=int, default=30)
ap.add_argument("--detik_per_episode", type=float, default=140.0, help="untuk perkiraan waktu (#20: 137 s)")
ap.add_argument("--cek", action="store_true")
ap.add_argument("--lain", nargs=argparse.REMAINDER, default=[], help="argumen tambahan untuk jalankan_skenario.py")
a = ap.parse_args()

LOG = os.path.join(DIR, "log_skenario", "jalankan_matriks.log")


def log(msg):
    line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sisa_seed(kode, t, mode):
    sys.path.insert(0, DIR)
    import csv
    import glob
    nama = "%s_t%s_%s_%s_%s" % (kode, t, mode, a.backend, a.label)
    sudah = set()
    for f in glob.glob(os.path.join(DIR, "log_skenario", "*_" + nama, "ringkasan_episode.csv")):
        with open(f) as fh:
            sudah |= {int(r["seed"]) for r in csv.DictReader(fh)}
    return [s for s in range(a.seed_awal, a.seed_awal + a.episodes) if s not in sudah]


daftar = [k.split(":") for k in a.kondisi]
if a.cek:
    tot = 0
    for kode, t, mode in daftar:
        n = len(sisa_seed(kode, t, mode))
        tot += n
        print("%-4s t%s %-9s sisa %3d episode" % (kode, t, mode, n))
    print("Total %d episode ≈ %.1f jam (%.0f s/episode)" % (tot, tot * a.detik_per_episode / 3600, a.detik_per_episode))
    sys.exit(0)

for kode, t, mode in daftar:
    gagal = 0
    while True:
        sisa = sisa_seed(kode, t, mode)
        if not sisa:
            log("%s t%s %s: SELESAI" % (kode, t, mode))
            break
        if gagal > a.maks_ulang:
            log("%s t%s %s: BERHENTI setelah %d kegagalan; sisa seed %s" % (kode, t, mode, gagal, sisa))
            break
        log("%s t%s %s: mulai, sisa %d seed" % (kode, t, mode, len(sisa)))
        rc = subprocess.call([sys.executable, os.path.join(DIR, "jalankan_skenario.py"), "--kode", kode, "--tingkat", t,
                              "--mode", mode, "--backend", a.backend, "--episodes", str(a.episodes),
                              "--seed_awal", str(a.seed_awal), "--label", a.label] + a.lain)
        if rc != 0:
            gagal += 1
            log("%s t%s %s: keluar kode %d (kegagalan ke-%d); tunggu %d s" % (kode, t, mode, rc, gagal, 2 * a.jeda))
            time.sleep(2 * a.jeda)
    time.sleep(a.jeda)
log("MATRIKS SELESAI DIPROSES. Cek baris SELESAI/BERHENTI.")
