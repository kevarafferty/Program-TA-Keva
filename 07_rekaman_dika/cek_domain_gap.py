"""
cek_domain_gap.py — Seberapa jauh frame CARLA dari foto jalan nyata, menurut fitur neck YOLO?

Proposal (Subbab 2.1.6, Daftar Istilah) mendefinisikan densitas fitur sebagai jarak ke "data
pelatihan" YOLO. Data latih best.pt adalah foto jalan Indonesia. Jika frame CARLA cerah (kondisi
nominal TA ini) pun sudah jauh dari foto nyata, monitor yang di-fit pada data latih akan alarm
terus-menerus dan tidak berguna. Skrip ini mengujinya.

Data nyata: sampel citra validasi datasets_yolo_9k (folder kerja Retta; kelas aman/sedang/parah, dari
sumber yang sama dengan data latih YOLO lab). Bukan data latih best.pt yang persis sama, karena data itu
tidak ada di folder (train_args best.pt menunjuk C:/Users/Ryzen_PC/Documents/TA_Dika/VS_Code/TrainYolo).

Cara pakai:
  python cek_domain_gap.py --bobot best_pure.pt --nyata <folder citra val> --data data --out hasil
"""
import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np
from sklearn.covariance import LedoitWolf

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "04_monitor_persepsi"))
from yolo_logit_hook import YoloDenganLogit  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bobot", required=True)
    ap.add_argument("--nyata", required=True)
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="hasil")
    a = ap.parse_args()
    y = YoloDenganLogit(a.bobot)
    files = sorted(glob.glob(os.path.join(a.nyata, "*.jpg")))
    Fr = np.stack([y.infer(cv2.imread(f))["fitur"] for f in files])
    rng = np.random.default_rng(0)
    p = rng.permutation(len(Fr))
    n_fit = int(len(Fr) * 0.65)
    fit, kal = Fr[p[:n_fit]], Fr[p[n_fit:]]
    mu, sd = fit.mean(0), fit.std(0) + 1e-6
    Z = (fit - mu) / sd
    U, S, Vt = np.linalg.svd(Z - Z.mean(0), full_matrices=False)
    n_pc = int(min(np.searchsorted(np.cumsum(S ** 2) / np.sum(S ** 2), 0.90) + 1, 20))
    P = Vt[:n_pc].T
    lw = LedoitWolf().fit((Z - Z.mean(0)) @ P)

    def skor(F):
        dz = ((F - mu) / sd - Z.mean(0)) @ P - lw.location_
        return np.einsum("ij,jk,ik->i", dz, lw.precision_, dz)

    tau = float(np.percentile(skor(kal), 95))
    out = dict(n_citra_nyata=len(files), n_fit=n_fit, n_kalibrasi=len(kal), n_komponen_pca=n_pc,
               ambang_p95=round(tau, 2), median_skor_nyata_kalibrasi=round(float(np.median(skor(kal))), 2))
    for k in ["cerah", "hujan", "malam"]:
        d = np.load(os.path.join(a.data, f"{k}.npz"))
        F = d["fitur"][d["diproses"] == 1]
        s = skor(F)
        out[k] = dict(median_skor=round(float(np.median(s)), 1), laju_alarm=round(float((s > tau).mean()), 3))
    json.dump(out, open(os.path.join(a.out, "domain_gap.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
