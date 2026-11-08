"""
bandingkan_dengan_dika.py — Membandingkan label kontak roda–lubang dengan logika
HIT/AVOID Dika pada (1) sapuan offset lateral, (2) sapuan kecepatan x jarak antarlubang,
dan (3) lintasan Dika yang sebenarnya (19 lubang di pothole_gt.json).

Catatan: log sensor Dika (sensor_data/*.csv) tidak menyimpan posisi x, y kendaraan,
sehingga episode lama TIDAK bisa dilabeli ulang. Lintasan di bagian (3) adalah
lintasan sintetis yang dibuat untuk menguji logika, bukan rekaman agen Dika.

Cara pakai:
    python bandingkan_dengan_dika.py --gt pothole_gt.json --out hasil
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from kontak_roda import (DT, GeometriKendaraan, Lubang, energi_pelanggaran, kontak_per_langkah, logika_dika)

GEO = GeometriKendaraan()


def lurus(y, kmh, x0, x1):
    xs = np.arange(x0, x1, kmh / 3.6 * DT)
    return xs, np.full_like(xs, y), np.zeros_like(xs)


def sapuan_offset(out):
    l = Lubang("p", 0, 0, 1.0, 1.5)
    offs = np.round(np.arange(0, 3.01, 0.02), 2)
    roda, dika, ev = [], [], []
    for o in offs:
        tr = lurus(o, 7, -15, 15)
        roda.append(kontak_per_langkah(*tr, [l], GEO)["kontak"].any())
        dika.append(len(logika_dika(*tr, [l]).hit) > 0)
        ev.append(energi_pelanggaran(*lurus(o, 7, -2, 2), [l], GEO))
    roda, dika = np.array(roda), np.array(dika)
    beda = offs[roda != dika]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.fill_between(offs, 0, roda * 1.0, step="mid", alpha=.35, color="#0f6e74", label="kontak roda (label baru)")
    ax.fill_between(offs, 0, dika * 0.6, step="mid", alpha=.55, color="#a2560b", label="HIT Dika")
    ax2 = ax.twinx(); ax2.plot(offs, ev, color="#1b2428", lw=1.2, label="energi pelanggaran $E_V$")
    ax2.set_ylabel("$E_V$")
    ax.set_xlabel("offset lateral pusat mobil ke pusat lubang (m)"); ax.set_yticks([])
    ax.axvline(1.84, ls=":", c="#a2560b"); ax.text(1.85, 0.9, "ambang Dika 1,84 m", fontsize=8, color="#a2560b")
    ax.axvline(2.175, ls=":", c="#0f6e74"); ax.text(2.19, 0.75, "batas kontak roda 2,175 m", fontsize=8, color="#0f6e74")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8, frameon=False, bbox_to_anchor=(1.0, 0.62))
    ax.set_title("Lubang 2 m x 3 m (High, ukuran Dika), Microlino 7 km/jam", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(out, "sapuan_offset_lateral.png"), dpi=150); plt.close(fig)
    return dict(rentang_beda_m=[float(beda.min()), float(beda.max())] if len(beda) else None,
                titik_beda=int(len(beda)), ambang_dika=1.84, batas_roda=2.175)


def sapuan_cooldown(out):
    kmh = np.arange(5, 31, 1)
    jarak = np.arange(2, 16.5, 0.5)
    hilang = np.zeros((len(jarak), len(kmh)))
    for i, s in enumerate(jarak):
        L = [Lubang("p1", 0, 0, 1.0, 1.5), Lubang("p2", s, 0, 1.0, 1.5)]
        for j, v in enumerate(kmh):
            tr = lurus(0.0, v, -10, s + 10)
            n_roda = len({e["lubang"] for e in kontak_per_langkah(*tr, L, GEO)["kejadian"]})
            n_dika = len(logika_dika(*tr, L).hit)
            hilang[i, j] = n_roda - n_dika
    fig, ax = plt.subplots(figsize=(7, 3.6))
    from matplotlib.colors import ListedColormap
    im = ax.imshow(hilang, origin="lower", aspect="auto", cmap=ListedColormap(["#eef3f3", "#c4621b"]), vmin=0, vmax=1,
                   extent=[kmh[0] - .5, kmh[-1] + .5, jarak[0] - .25, jarak[-1] + .25])
    ax.set_xlabel("kecepatan (km/jam)"); ax.set_ylabel("jarak antar pusat lubang selajur (m)")
    ax.plot([7], [13], "o", c="#0f6e74"); ax.text(7.6, 13.2, "setup Dika (7 km/jam, ~13 m)", fontsize=8, color="#0f6e74")
    ax.set_title("Kontak yang tidak tercatat oleh logika Dika (cooldown 100 langkah)", fontsize=10)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#eef3f3", label="kedua kontak tercatat"),
                       Patch(color="#c4621b", label="kontak ke-2 tercatat 'terhindar'")],
              loc="lower right", fontsize=8, framealpha=0.9)
    fig.tight_layout(); fig.savefig(os.path.join(out, "sapuan_cooldown.png"), dpi=150); plt.close(fig)
    return dict(sel_kontak_hilang=int((hilang > 0).sum()), total_sel=int(hilang.size),
                kecepatan_min_bermasalah_pada_13m=int(kmh[(hilang[list(jarak).index(13.0)] > 0)].min())
                if (hilang[list(jarak).index(13.0)] > 0).any() else None)


def lintasan_dika(gt_path, out):
    L = [Lubang.dari_json(d) for d in json.load(open(gt_path))]
    hasil = {}
    # (a) agen yang tidak pernah menghindar: lurus di lajur spawn
    hasil["lurus_lajur_spawn_y250.5"] = lurus(250.5, 7, -299.5, -27)
    # (b) agen "menenun" ideal: berada di lajur seberang tiap kali melewati lubang
    xs = np.arange(-299.5, -27, 7 / 3.6 * DT)
    target = np.interp(xs, [l.x for l in L], [247.2 if l.y > 249 else 250.5 for l in L])
    ys = np.convolve(np.pad(target, 60, mode="edge"), np.ones(121) / 121, mode="valid")   # halus ~6 m
    yaw = np.degrees(np.arctan2(np.gradient(ys), np.gradient(xs)))
    hasil["menenun_halus"] = (xs, ys, yaw)
    # (c) cermin dari (a): lurus di lajur kiri
    hasil["lurus_lajur_kiri_y247.2"] = lurus(247.2, 7, -299.5, -27)
    ringkas = {}
    for nama, tr in hasil.items():
        k = kontak_per_langkah(*tr, L, GEO)
        d = logika_dika(*tr, L)
        ringkas[nama] = dict(kontak_roda=len({e["lubang"] for e in k["kejadian"]}),
                             hit_dika=len(d.hit), avoid_dika=len(d.avoid),
                             penghindaran_dika_pct=round(100 * len(d.avoid) / len(L), 1),
                             penghindaran_roda_pct=round(100 * (1 - len({e['lubang'] for e in k['kejadian']}) / len(L)), 1))
    return ringkas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--out", default="hasil")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    r = dict(geometri=GEO.__dict__, sapuan_offset=sapuan_offset(a.out), sapuan_cooldown=sapuan_cooldown(a.out),
             lintasan_dika=lintasan_dika(a.gt, a.out))
    with open(os.path.join(a.out, "ringkasan_perbandingan.json"), "w") as f:
        json.dump(r, f, indent=1)
    print(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
