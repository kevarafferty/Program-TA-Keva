"""
sapuan_jarak_dqn.py — Pada jarak berapa agen DQN Dika mulai menghindar?

Lubang 2 m x 3 m (ukuran di pothole_gt.json) ditempatkan tepat di depan mobil pada
jarak 30 m -> 1 m. Untuk tiap jarak, kotak 2D lubang dihitung dengan proyeksi kamera
Dika (05_proyeksi_kamera), dinormalisasi seperti state DQN (cx, cy, w, h), lalu nilai-Q
dihitung dengan bobot .h5. Hasilnya: aksi agen sebagai fungsi jarak lubang.

Batasan: state lain (kecepatan 7 km/jam, setir 0, akselerasi 9,81 m/s², tanpa tabrakan)
dibuat tetap; di simulasi nyata nilai-nilai ini berubah tiap langkah.

Cara pakai:
    python sapuan_jarak_dqn.py --h5 model_best.h5 --out hasil_sapuan_jarak.md
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "05_proyeksi_kamera"))
from cek_model_dqn import AKSI, baca_bobot_h5, buat_state, forward_numpy  # noqa: E402
from proyeksi_kamera import KAMERA_DIKA, kotak_2d_lubang  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5", required=True)
    ap.add_argument("--out", default="hasil_sapuan_jarak.md")
    ap.add_argument("--kmh", type=float, default=7.0)
    a = ap.parse_args()
    bobot, _ = baca_bobot_h5(a.h5)
    y_mobil = 250.5
    baris = ["| Jarak pusat lubang dari mobil (m) | cy | h kotak | sev 0.9 | sev 0.6 | sev 0.3 | margin Q (sev 0.3) |",
             "|---:|---:|---:|---|---|---|---:|"]
    pertama = {}
    for d in np.arange(30, 0.5, -1.0):
        lub = dict(x=d, y=0.0, extent_x=1.0, extent_y=1.5, yaw=0)
        k = kotak_2d_lubang(KAMERA_DIKA, (0, 0, 0, 0), lub)
        if k is None:
            continue
        cx, cy = (k[0] + k[2]) / 2 / 640, (k[1] + k[3]) / 2 / 640
        w, h = (k[2] - k[0]) / 640, (k[3] - k[1]) / 640
        sel = []
        for sev in (0.9, 0.6, 0.3):
            q = forward_numpy(bobot, buat_state(cx, cy, w, h, sev, kmh=a.kmh, y=y_mobil)[None])[0]
            act = AKSI[int(np.argmax(q))]
            sel.append(act)
            if act != "LURUS" and sev not in pertama:
                pertama[sev] = d
        qs = np.sort(q)[::-1]
        baris.append(f"| {d:.0f} | {cy:.3f} | {h:.3f} | {sel[0]} | {sel[1]} | {sel[2]} | {qs[0] - qs[1]:.2f} |")
    v = a.kmh / 3.6
    teks = [f"# Aksi agen terhadap jarak lubang ({os.path.basename(a.h5)})", "",
            f"Mobil di lajur kanan (y = {y_mobil}), {a.kmh:.0f} km/jam, lubang tepat di depan.", ""]
    for sev in (0.9, 0.6, 0.3):
        if sev in pertama:
            teks.append(f"- sev {sev}: mulai menghindar pada jarak **{pertama[sev]:.0f} m** "
                        f"(≈ {pertama[sev] / v:.1f} s sebelum mencapai pusat lubang)")
        else:
            teks.append(f"- sev {sev}: tidak pernah menghindar pada rentang 1–30 m")
    teks += ["", *baris, ""]
    open(a.out, "w", encoding="utf-8").write("\n".join(teks))
    print("\n".join(teks))


if __name__ == "__main__":
    main()
