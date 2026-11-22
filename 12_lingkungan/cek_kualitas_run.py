"""
cek_kualitas_run.py — Tandai episode yang kemungkinan berjalan dengan lubang TAK TAMPAK ("buta").

Tanda buta: YOLO mendeteksi sama seringnya saat ada lubang 3–15 m di depan dan saat tidak ada
(selisih < AMBANG), karena yang terdeteksi hanya objek lain / deteksi palsu. Episode normal di semua
kondisi baseline punya selisih jelas (laptop Epic: cerah 0,97 vs 0,70; malam 0,30 vs 0,10; hujan 0,70 vs 0,48).

Batasan: pada kondisi yang memang membuat YOLO gagal total (mis. A6 berat) episode valid juga bisa
tertandai. Untuk run baru, kolom verif_percobaan/verif_conf_min (verifikasi_lubang.py) adalah bukti utama.

    python cek_kualitas_run.py                    # semua run di log_skenario
    python cek_kualitas_run.py --run log_skenario\\2026..._REG_t1_...
"""
import argparse
import csv
import glob
import json
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
AMBANG = 0.08


def cek_episode(run, r):
    nama = "ep%03d_seed%s" % (int(r["episode"]), r["seed"])
    with open(os.path.join(run, "langkah_%s.csv" % nama)) as f:
        L = list(csv.DictReader(f))
    with open(os.path.join(run, "gt_%s.json" % nama), encoding="utf-8") as f:
        px = np.array([g["x"] for g in json.load(f)])
    x = np.array([float(l["x"]) for l in L])
    det = np.array([float(l["n_det"] or 0) > 0 for l in L])
    dekat = np.array([((px - xx > 3) & (px - xx < 15)).any() for xx in x])
    dd = det[dekat].mean() if dekat.any() else np.nan
    dj = det[~dekat].mean() if (~dekat).any() else np.nan
    return dict(seed=int(r["seed"]), det_dekat=dd, det_jauh=dj, selisih=dd - dj,
                buta=bool(dd - dj < AMBANG), verif=r.get("verif_percobaan", ""), hits=int(r["hits"]),
                avoids=int(r["avoids"]), akhir=r["akhir"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="*", default=None)
    ap.add_argument("--rinci", action="store_true")
    a = ap.parse_args()
    runs = a.run or sorted(glob.glob(os.path.join(DIR, "log_skenario", "2026*")))
    for run in runs:
        f = os.path.join(run, "ringkasan_episode.csv")
        if not os.path.exists(f):
            continue
        with open(f) as fh:
            rows = [cek_episode(run, r) for r in csv.DictReader(fh)]
        buta = [x for x in rows if x["buta"]]
        tanpa_verif = all(x["verif"] == "" for x in rows)
        print("%-48s %2d ep | tersangka buta %2d %s%s" % (
            os.path.basename(run)[16:], len(rows), len(buta),
            ("seed " + ",".join(str(x["seed"]) for x in buta)) if buta else "",
            "  [run lama, tanpa verifikasi]" if tanpa_verif else ""))
        if a.rinci:
            for x in rows:
                print("    seed %3d dekat %.2f jauh %.2f selisih %+.2f %s hits %d %s verif=%s" % (
                    x["seed"], x["det_dekat"], x["det_jauh"], x["selisih"], "BUTA?" if x["buta"] else "     ",
                    x["hits"], x["akhir"], x["verif"]))


if __name__ == "__main__":
    main()
