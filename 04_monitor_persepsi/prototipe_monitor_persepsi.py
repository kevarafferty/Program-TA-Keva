"""
prototipe_monitor_persepsi.py — Studi pendahuluan OFFLINE monitor persepsi
(Bab 2.1.6 proposal, hipotesis H1, sasaran S2) pada 53 citra CARLA milik Dika.

Ini BUKAN hasil akhir. 53 citra terlalu sedikit; tujuannya:
  (1) membuktikan seluruh pipa skor (hook logit, fitur neck, Mahalanobis, kNN,
      AUROC) berjalan ujung ke ujung, dan
  (2) memberi gambaran awal skor mana yang menjanjikan sebelum data CARLA
      closed-loop tersedia.

Alur
----
1. Setiap citra diberi 4 jenis gangguan x 3 tingkat (+ versi bersih):
     gelap (simulasi malam), blur, kabut, derau  -> 13 kondisi x 53 citra
2. YOLO best.pt dijalankan dengan pengaturan Dika (imgsz=320, conf=0.05).
3. Label kegagalan per citra (yang dilihat agen DQN = kotak conf tertinggi):
     GAGAL jika tidak ada deteksi, ATAU kotak conf tertinggi tidak tumpang
     tindih (IoU < IOU_COCOK) dengan lubang mana pun di label.
4. Skor (makin tinggi = makin mencurigakan):
     msp, maxlogit, energi, jointenergy  -> dari logit kotak conf tertinggi
     jointenergy_citra                   -> rata-rata S_JE seluruh 2100 anchor
     mahalanobis, knn                    -> jarak fitur neck ke data ID
     kecerahan                           -> simpangan kecerahan & kontras dari ID
5. Pembagian data: citra dibagi dua secara acak (seed tetap). Separuh A versi
   BERSIH dipakai sebagai "data latih ID" untuk Mahalanobis/kNN/kecerahan;
   semua evaluasi dilakukan pada separuh B (13 kondisi). Tidak ada citra yang
   dipakai untuk fit dan uji sekaligus.
6. AUROC, FPR95 + selang kepercayaan bootstrap 95% (per-citra, 2000 ulangan).

Cara pakai:
    python prototipe_monitor_persepsi.py --bobot best.pt --citra <folder YOLO/CARLA> --out hasil
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import cv2
import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score, roc_curve

from yolo_logit_hook import (CONF_DIKA, IMGSZ_DIKA, YoloDenganLogit, energi, joint_energy, max_logit,
                             msp_sigmoid)

IOU_COCOK = 0.3          # lubang kecil & jauh -> IoU 0.5 terlalu ketat; dicatat sebagai asumsi
SEED = 13
TINGKAT = {
    "gelap": [dict(k=0.60, g=1.2), dict(k=0.35, g=1.5), dict(k=0.15, g=2.0)],
    "blur": [dict(s=1.5), dict(s=3.0), dict(s=5.0)],
    "kabut": [dict(b=0.6), dict(b=1.2), dict(b=2.0)],
    "derau": [dict(sd=10), dict(sd=25), dict(sd=45)],
}


# ---------------------------------------------------------------------------
# Gangguan citra (deterministik)
# ---------------------------------------------------------------------------
def ganggu(img: np.ndarray, jenis: str, p: dict, rng: np.random.Generator) -> np.ndarray:
    x = img.astype(np.float32) / 255.0
    if jenis == "gelap":            # kurva gamma + redaman: kira-kira kamera di malam hari
        x = p["k"] * np.power(x, p["g"])
        x[..., 0] *= 1.10            # sedikit kebiruan (BGR)
    elif jenis == "blur":
        x = cv2.GaussianBlur(x, (0, 0), p["s"])
    elif jenis == "kabut":          # model atmosfer I = J t + A (1 - t), jarak naik ke arah horizon
        H = x.shape[0]
        d = np.linspace(3.0, 0.3, H, dtype=np.float32)[:, None, None]   # atas citra = jauh
        t = np.exp(-p["b"] * d)
        x = x * t + 0.80 * (1 - t)
    elif jenis == "derau":
        x = x + rng.normal(0, p["sd"] / 255.0, x.shape).astype(np.float32)
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Label & IoU
# ---------------------------------------------------------------------------
def baca_label(path_txt: str, w: int, h: int) -> np.ndarray:
    kotak = []
    if os.path.exists(path_txt):
        for baris in open(path_txt):
            a = baris.split()
            if len(a) != 5:
                continue
            c, cx, cy, bw, bh = int(a[0]), *map(float, a[1:])
            kotak.append([(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h, c])
    return np.array(kotak, dtype=np.float32).reshape(-1, 5)


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """IoU antara kotak a (n,4) dan b (m,4) -> (n,m)."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + bb[None, :] - inter + 1e-9)


# ---------------------------------------------------------------------------
# Metrik
# ---------------------------------------------------------------------------
def fpr_at_95tpr(y, s):
    fpr, tpr, _ = roc_curve(y, s)
    i = np.searchsorted(tpr, 0.95, side="left")
    return float(fpr[min(i, len(fpr) - 1)])


def auroc_ci(y, s, grup, n=2000, seed=0):
    """Bootstrap per citra asal (grup) agar 13 versi citra yang sama tidak dihitung independen."""
    y, s, grup = map(np.asarray, (y, s, grup))
    if len(np.unique(y)) < 2:
        return np.nan, (np.nan, np.nan)
    base = roc_auc_score(y, s)
    rng = np.random.default_rng(seed)
    ug = np.unique(grup)
    idx_per = {g: np.where(grup == g)[0] for g in ug}
    vals = []
    for _ in range(n):
        pilih = np.concatenate([idx_per[g] for g in rng.choice(ug, len(ug), replace=True)])
        if len(np.unique(y[pilih])) < 2:
            continue
        vals.append(roc_auc_score(y[pilih], s[pilih]))
    return float(base), (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bobot", required=True)
    ap.add_argument("--citra", required=True)
    ap.add_argument("--out", default="hasil")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    yolo = YoloDenganLogit(a.bobot)
    files = sorted(glob.glob(os.path.join(a.citra, "*.jpg")))
    rng_split = np.random.default_rng(SEED)
    perm = rng_split.permutation(len(files))
    set_A = set(perm[: len(files) // 2].tolist())        # fit ID
    kondisi = [("bersih", 0, None)] + [(j, t + 1, p) for j, ps in TINGKAT.items() for t, p in enumerate(ps)]

    rec = []
    fitur = {}
    t0 = time.time()
    for i, f in enumerate(files):
        img0 = cv2.imread(f)
        H, W = img0.shape[:2]
        gt = baca_label(os.path.splitext(f)[0] + ".txt", W, H)
        for jenis, lvl, p in kondisi:
            rng = np.random.default_rng(SEED * 1000 + i * 17 + lvl)
            img = img0 if p is None else ganggu(img0, jenis, p, rng)
            h = yolo.infer(img)
            n = len(h["conf"])
            if n:
                top = int(np.argmax(h["conf"]))
                lg = h["logit"][top]
                cocok = iou(h["boxes"][top:top + 1], gt[:, :4]).max() >= IOU_COCOK if len(gt) else False
                cls_top = int(h["cls"][top])
                # lubang GT yang tidak tersentuh deteksi mana pun (conf >= 0.05)
                ious = iou(gt[:, :4], h["boxes"])
                terlewat = int((ious.max(axis=1) < IOU_COCOK).sum()) if len(gt) else 0
            else:
                # Tanpa deteksi: pakai logit anchor kandidat terkuat (di bawah ambang conf).
                # Catatan: skor per-deteksi pada citra seperti ini tetap "otomatis tinggi"
                # karena conf < 0.05 menurut definisi -> lihat evaluasi E2 di bawah.
                la = h["logit_semua"]
                lg = la[:, int(la.max(axis=0).argmax())]
                cocok, cls_top, terlewat = False, -1, len(gt)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
            key = (i, jenis, lvl)
            fitur[key] = h["fitur"]
            rec.append(dict(
                citra=os.path.basename(f), idx=i, set="A" if i in set_A else "B", kondisi=jenis, tingkat=lvl,
                ood=int(lvl > 0), n_det=n, n_gt=len(gt), gagal=int(not cocok), terlewat=terlewat,
                kelas_top=cls_top, conf_top=float(h["conf"].max()) if n else 0.0,
                msp=float(1 - msp_sigmoid(lg)), maxlogit=float(-max_logit(lg)),
                energi=float(energi(lg)), jointenergy=float(-joint_energy(lg)),
                jointenergy_citra=float(-joint_energy(h["logit_semua"].T).mean()),
                bright=float(gray.mean()), contrast=float(gray.std()),
            ))
        if (i + 1) % 10 == 0:
            print(f"{i + 1}/{len(files)} citra, {time.time() - t0:.0f} s")

    # --- skor berbasis fitur: fit pada separuh A versi bersih -----------------
    idA = [k for k in fitur if k[0] in set_A and k[2] == 0]
    XA = np.stack([fitur[k] for k in idA])
    mu, sd = XA.mean(0), XA.std(0) + 1e-6
    ZA = (XA - mu) / sd
    lw = LedoitWolf().fit(ZA)
    prec = lw.precision_
    nA = ZA / np.linalg.norm(ZA, axis=1, keepdims=True)
    bA = np.array([r["bright"] for r in rec if r["idx"] in set_A and r["tingkat"] == 0])
    cA = np.array([r["contrast"] for r in rec if r["idx"] in set_A and r["tingkat"] == 0])
    for r in rec:
        z = (fitur[(r["idx"], r["kondisi"], r["tingkat"])] - mu) / sd
        d = z - lw.location_
        r["mahalanobis"] = float(d @ prec @ d)
        zn = z / np.linalg.norm(z)
        r["knn"] = float(np.sort(1 - nA @ zn)[min(2, len(nA) - 1)])        # k=3, jarak kosinus
        r["kecerahan"] = float(abs(r["bright"] - bA.mean()) / bA.std() + abs(r["contrast"] - cA.mean()) / cA.std())

    with open(os.path.join(a.out, "rekaman_per_citra.json"), "w") as fh:
        json.dump(rec, fh, indent=1)

    # --- evaluasi pada separuh B ---------------------------------------------
    B = [r for r in rec if r["set"] == "B"]
    skor = ["msp", "maxlogit", "energi", "jointenergy", "jointenergy_citra", "mahalanobis", "knn", "kecerahan"]
    hasil = {"n_citra_B": len({r['idx'] for r in B}), "n_sampel_B": len(B), "per_skor": {}, "per_kondisi": {},
             "E2_hanya_frame_berdeteksi": {}}
    y_g = np.array([r["gagal"] for r in B]); y_o = np.array([r["ood"] for r in B]); g = np.array([r["idx"] for r in B])
    for s in skor:
        v = np.array([r[s] for r in B])
        au_g, ci_g = auroc_ci(y_g, v, g)
        au_o, ci_o = auroc_ci(y_o, v, g)
        hasil["per_skor"][s] = dict(auroc_gagal=au_g, ci_gagal=ci_g, fpr95_gagal=fpr_at_95tpr(y_g, v),
                                    auroc_ood=au_o, ci_ood=ci_o, fpr95_ood=fpr_at_95tpr(y_o, v))
    # E2: hanya frame yang MEMILIKI deteksi. Pertanyaannya: apakah skor bisa membedakan
    # kotak teratas yang benar (mengenai lubang) dari yang salah (false positive)?
    # Ini satu-satunya uji skor per-deteksi yang tidak sirkular.
    Bd = [r for r in B if r["n_det"] > 0]
    yd = np.array([r["gagal"] for r in Bd]); gd = np.array([r["idx"] for r in Bd])
    hasil["E2_hanya_frame_berdeteksi"]["n"] = len(Bd)
    hasil["E2_hanya_frame_berdeteksi"]["n_gagal"] = int(yd.sum())
    for s in skor:
        au, ci = auroc_ci(yd, np.array([r[s] for r in Bd]), gd)
        hasil["E2_hanya_frame_berdeteksi"][s] = dict(auroc=au, ci=ci)
    for j in TINGKAT:
        sub = [r for r in B if r["kondisi"] in ("bersih", j)]
        yy = np.array([r["gagal"] for r in sub]); gg = np.array([r["idx"] for r in sub])
        hasil["per_kondisi"][j] = {s: auroc_ci(yy, np.array([r[s] for r in sub]), gg, n=500)[0] for s in skor}
    # tingkat kegagalan per kondisi (semua citra) & distribusi kelas
    tabel_gagal = {}
    for j, lvl, _ in kondisi:
        sub = [r for r in rec if r["kondisi"] == j and r["tingkat"] == lvl]
        tabel_gagal[f"{j}-{lvl}"] = dict(gagal=float(np.mean([r["gagal"] for r in sub])),
                                         tanpa_deteksi=float(np.mean([r["n_det"] == 0 for r in sub])),
                                         kelas_top={k: int(sum(r["kelas_top"] == k for r in sub)) for k in (-1, 0, 1, 2)})
    hasil["tingkat_gagal"] = tabel_gagal
    hasil["pengaturan"] = dict(imgsz=IMGSZ_DIKA, conf=CONF_DIKA, iou_cocok=IOU_COCOK, seed=SEED,
                               n_fit_ID=len(idA), dim_fitur=int(XA.shape[1]), tingkat=TINGKAT)
    with open(os.path.join(a.out, "ringkasan.json"), "w") as fh:
        json.dump(hasil, fh, indent=1)
    print(json.dumps(hasil["per_skor"], indent=1))


if __name__ == "__main__":
    main()
