"""
baseline_lurus_v2.py — TODO #18: baseline "mobil lurus yang tidak pernah menghindar" dengan GT v2.

Mobil lurus tidak memakai kamera, jadi angkanya SAMA untuk cerah, hujan, dan malam.
Yang berubah hanya posisi lateral awal (y). Karena runner #19 memakai offset awal acak,
skrip ini juga menghitung baseline rata-rata untuk sebaran offset yang sama.

Contoh:
    python baseline_lurus_v2.py --gt ../alat_carla/pothole_gt_v2_segmen_dika.json --out hasil_gt_v2
"""
import argparse
import csv
import json
import os

import numpy as np

from kontak_roda import DT, MICROLINO, Lubang, kontak_per_langkah, logika_dika

ap = argparse.ArgumentParser()
ap.add_argument("--gt", required=True)
ap.add_argument("--out", default="hasil_gt_v2")
ap.add_argument("--kmh", type=float, default=7.0)
ap.add_argument("--x0", type=float, default=-299.5)
ap.add_argument("--x1", type=float, default=-27.0)
ap.add_argument("--y_spawn", type=float, default=250.5)
ap.add_argument("--offset_maks", type=float, default=0.5, help="offset lateral acak runner: uniform(-a, +a)")
ap.add_argument("--y_min", type=float, default=246.5)
ap.add_argument("--y_max", type=float, default=251.5)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

L = [Lubang.dari_json(d) for d in json.load(open(a.gt))]
L = [l for l in L if a.x0 <= l.x <= a.x1]
n_target = sum(l.severity in ("Medium", "High") for l in L)
xs = np.arange(a.x0, a.x1, a.kmh / 3.6 * DT)


def hitung(y):
    ys, yaw = np.full_like(xs, y), np.zeros_like(xs)
    kena = {e["lubang"] for e in kontak_per_langkah(xs, ys, yaw, L, MICROLINO)["kejadian"]}
    d = logika_dika(xs, ys, yaw, L)
    return dict(y=round(float(y), 3), kena_roda=len(kena), terhindar_roda=n_target - len(kena),
                pct_roda=round(100 * (n_target - len(kena)) / n_target, 1),
                avoid_dika=len(d.avoid), pct_dika=round(100 * len(d.avoid) / len(L), 1))


baris = [hitung(y) for y in np.arange(a.y_min, a.y_max + 1e-9, 0.05)]
with open(os.path.join(a.out, "sapuan_y_mobil_lurus.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=baris[0].keys())
    w.writeheader()
    w.writerows(baris)

dalam = [b for b in baris if abs(b["y"] - a.y_spawn) <= a.offset_maks + 1e-9]
ringkas = dict(gt=a.gt, jumlah_lubang_di_segmen=len(L), lubang_target_medium_high=n_target,
               segmen_x=[a.x0, a.x1], kecepatan_kmh=a.kmh,
               lurus_y_spawn=hitung(a.y_spawn), lurus_lajur_kiri_247_2=hitung(247.2),
               offset_acak=dict(rentang=[a.y_spawn - a.offset_maks, a.y_spawn + a.offset_maks],
                                pct_roda_rata2=round(float(np.mean([b["pct_roda"] for b in dalam])), 1),
                                pct_roda_min=min(b["pct_roda"] for b in dalam),
                                pct_roda_maks=max(b["pct_roda"] for b in dalam)),
               catatan="Sama untuk cerah, hujan, malam (mobil lurus tidak memakai persepsi).")
json.dump(ringkas, open(os.path.join(a.out, "baseline_lurus_v2.json"), "w"), indent=1)
print(json.dumps(ringkas, indent=1))
