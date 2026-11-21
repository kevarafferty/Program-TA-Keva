"""
analisis_baseline.py — #21/#22: ringkas run baseline pi_Dika per kondisi.

Contoh:
    python analisis_baseline.py --runs log_runner\\20261118_*  --gt ..\\..\\alat_carla\\pothole_gt_v2_segmen_dika.json
Membaca semua posisi_ep*.csv + ringkasan_episode.csv di folder run, menghitung penghindaran
(pelabel roda dan logika Dika) per episode, rata-rata, CI 95% bootstrap, dan lubang yang paling sering kena.
"""
import argparse, csv, glob, json, os, sys
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "02_pelabel_roda"))
from kontak_roda import Lubang, kontak_per_langkah, logika_dika

ap = argparse.ArgumentParser()
ap.add_argument("--runs", nargs="+", required=True)
ap.add_argument("--gt", default=os.path.join("..", "..", "alat_carla", "pothole_gt_v2_segmen_dika.json"))
ap.add_argument("--out", default=None, help="default: hasil_baseline_<kondisi>.json (tidak menimpa hasil lama)")
a = ap.parse_args()
L = [Lubang.dari_json(d) for d in json.load(open(a.gt))]
N = len(L)
DIKA = {"ClearNoon": 100.0, "HardRainNoon": 84.2, "ClearNight": 47.4}   # [#21c] hujan Dika = HardRainNoon (11_cuaca); SoftRainNoon tidak punya pembanding
rng = np.random.default_rng(0)

def ci(v):
    v = np.asarray(v, float)
    if len(v) < 2: return [float(v.mean())] * 2
    b = rng.choice(v, (5000, len(v))).mean(1)
    return [round(float(np.percentile(b, 2.5)), 1), round(float(np.percentile(b, 97.5)), 1)]

data = defaultdict(lambda: dict(roda=[], dika=[], roda_lewat=[], roda_gagal=[], akhir=Counter(), kena=Counter(), tabrakan=0, selesai=0, detik=[], seed=[]))
runs = [r for p in a.runs for r in glob.glob(p)]
for run in sorted(runs):
    cuaca = os.path.basename(run.rstrip("\\/")).split("_", 2)[-1]
    ring = {r["seed"]: r for r in csv.DictReader(open(os.path.join(run, "ringkasan_episode.csv")))}
    for f in sorted(glob.glob(os.path.join(run, "posisi_ep*.csv"))):
        seed = f.rsplit("seed", 1)[1].split(".")[0]
        if seed not in ring: continue          # episode terputus (crash) dilewati
        r = list(csv.DictReader(open(f)))
        x, y, yaw = (np.array([float(q[c]) for q in r]) for c in ("x", "y", "yaw"))
        kena = {e["lubang"] for e in kontak_per_langkah(x, y, yaw, L)["kejadian"]}
        d = logika_dika(x, y, yaw, L)
        D = data[cuaca]
        D["roda"].append(100 * (N - len(kena)) / N); D["dika"].append(100 * len(d.avoid) / N)
        # [#21c] episode bisa berhenti sebelum semua lubang dilewati (keluar jalan / tabrak).
        # Cara lama menghitung lubang yang tidak tercapai sebagai "terhindar" -> dilaporkan juga dua versi lain.
        lewat = [l for l in L if l.x + l.ex < x.max()]
        n_kena_lewat = sum(l.id in kena for l in lewat)
        D["roda_lewat"].append(100 * (len(lewat) - n_kena_lewat) / max(len(lewat), 1))
        D["roda_gagal"].append(100 * (len(lewat) - n_kena_lewat) / N)
        xe = float(ring[seed]["x_akhir"])
        D["akhir"]["finis" if xe >= -28 else ("tabrak" if ring[seed].get("tabrakan") else "keluar_jalan")] += 1
        D["kena"].update(kena); D["seed"].append(int(seed)); D["detik"].append(float(ring[seed]["detik"]))
        D["tabrakan"] += bool(ring[seed].get("tabrakan")) or float(ring[seed]["x_akhir"]) < -28
        D["selesai"] += float(ring[seed]["x_akhir"]) >= -28

hasil = {}
for c, D in data.items():
    n = len(D["roda"])
    dup = n - len(set(D["seed"]))
    hasil[c] = dict(episode=n, seed_ganda=dup,
                    roda_pct_rata2=round(float(np.mean(D["roda"])), 1), roda_ci95=ci(D["roda"]),
                    dika_pct_rata2=round(float(np.mean(D["dika"])), 1), dika_ci95=ci(D["dika"]),
                    angka_dika_laporan=DIKA.get(c.split("_")[0]), mobil_lurus_pct=47.4,
                    roda_hanya_dilewati_pct=round(float(np.mean(D["roda_lewat"])), 1), roda_hanya_dilewati_ci95=ci(D["roda_lewat"]),
                    roda_tak_tercapai_gagal_pct=round(float(np.mean(D["roda_gagal"])), 1), roda_tak_tercapai_gagal_ci95=ci(D["roda_gagal"]),
                    akhir_episode=dict(D["akhir"]),
                    lubang_sering_kena=D["kena"].most_common(5),
                    episode_tabrakan=D["tabrakan"], episode_finis=D["selesai"],
                    detik_rata2=round(float(np.mean(D["detik"])), 1))
    print(f"\n== {c}: {n} episode" + (f"  (PERINGATAN: {dup} seed ganda)" if dup else ""))
    print(f"   pelabel roda : {hasil[c]['roda_pct_rata2']}%  CI95 {hasil[c]['roda_ci95']}")
    print(f"   logika Dika  : {hasil[c]['dika_pct_rata2']}%  CI95 {hasil[c]['dika_ci95']}  | laporan Dika {DIKA.get(c.split('_')[0])}% | mobil lurus 47,4%")
    print(f"   roda, hanya lubang yang dilewati : {hasil[c]['roda_hanya_dilewati_pct']}%  CI95 {hasil[c]['roda_hanya_dilewati_ci95']}")
    print(f"   roda, tak tercapai = gagal       : {hasil[c]['roda_tak_tercapai_gagal_pct']}%  CI95 {hasil[c]['roda_tak_tercapai_gagal_ci95']}")
    print(f"   akhir episode: {dict(D['akhir'])}")
    print(f"   sering kena  : {D['kena'].most_common(5)}")
    print(f"   tabrakan {D['tabrakan']} ep, finis {D['selesai']} ep, {hasil[c]['detik_rata2']} s/ep")
out = a.out or ("hasil_baseline_" + "_".join(sorted(hasil)) + ".json")
json.dump(hasil, open(out, "w"), indent=1)
print(f"\nDitulis: {out}")
