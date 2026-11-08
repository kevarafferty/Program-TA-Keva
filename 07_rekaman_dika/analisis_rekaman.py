"""
analisis_rekaman.py — Evaluasi monitor persepsi pada frame CARLA asli dari rekaman uji Dika
(cerah, hujan, malam), memakai keluaran ekstrak_rekaman.py.

Label dan pembagian data
------------------------
* Posisi x kendaraan per frame: dari JANGKAR kejadian Hits/Avoids di overlay. Kejadian ke-j
  adalah lubang ke-j (urut x). AVOID terjadi saat x > x_lubang + 1,10 m (kode Dika); HIT terjadi
  saat lubang < 2 m di depan, dianggap x = x_lubang - 1,5 m. Di antara jangkar: interpolasi linear.
  Frame pertama = x spawn (-299,5); frame terakhir = garis finis (-27) bila episode selesai di finis.
  Untuk hujan dan malam, hasilnya dicek terhadap integrasi kecepatan dari CSV.
* "Lubang dalam jangkauan": ada pusat lubang 3–15 m di depan titik asal kendaraan (lajur mana pun;
  kamera FOV 90° melihat kedua lajur pada jarak ini).
* GAGAL (kegagalan persepsi): lubang dalam jangkauan TETAPI YOLO agen tidak mendeteksi apa pun.
  Status deteksi agen dibaca dari overlay (tervalidasi 100% terhadap CSV).
* Data ID untuk mencocokkan Mahalanobis/kNN/kecerahan: frame CERAH di paruh pertama lintasan
  (x < -163). Semua evaluasi memakai paruh kedua lintasan (x >= -163) untuk KETIGA kondisi,
  sehingga ruas jalan yang diuji sama dan tidak ada frame yang dipakai untuk fit sekaligus uji.
* Bootstrap per "lintasan lubang" (kondisi x lubang terdekat), karena frame berurutan saling bergantung.

Cara pakai:  python analisis_rekaman.py --data data --gt pothole_gt.json --csv_dir sensor_data --out hasil
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score, roc_curve

X0, XF, DT = -299.5, -27.0, 0.05
X_BELAH = -163.0
KONDISI = ["cerah", "hujan", "malam"]
SKOR = ["jointenergy_citra", "mahalanobis", "knn", "kecerahan"]
SKOR_PER_DETEKSI = ["msp", "energi", "jointenergy"]   # dilaporkan terpisah; tidak andal pada video terkompresi


def _jangkar_ke_x(n, fr, xs, finis=True):
    fr, xs = [0] + list(fr), [X0] + list(xs)
    if finis:
        fr.append(n - 1); xs.append(XF)
    fr, xs = np.array(fr), np.array(xs)
    o = np.argsort(fr)
    return np.interp(np.arange(n), fr[o], xs[o])


def kejadian_csv(c):
    """Langkah (indeks frame) saat Hits/Avoids naik di CSV. Frame i = baris CSV i (langkah i+1)."""
    av = np.where(np.diff(c.avoids.values) > 0)[0] + 1
    ht = np.where(np.diff(c.hits.values) > 0)[0] + 1
    ev = np.sort(np.r_[av, ht])
    return ev, ["avoid" if e in set(av) else "hit" for e in ev]


def kejadian_overlay_warna(d_ganti, prediksi, toleransi=40):
    """Untuk video tanpa CSV: pilih perubahan penghitung di overlay yang paling dekat dengan prediksi."""
    kand = np.where(d_ganti == 1)[0]
    hasil, cocok = [], 0
    for p in prediksi:
        dekat = kand[np.abs(kand - p) <= toleransi]
        if len(dekat):
            hasil.append(int(dekat[np.argmin(np.abs(dekat - p))])); cocok += 1
        else:
            hasil.append(int(p))
    return np.array(hasil), cocok


def x_dari_kejadian(n, ev, jenis, px_urut):
    xs = [px_urut[j] + (1.10 if t == "avoid" else -1.5) for j, t in enumerate(jenis[:len(px_urut)])]
    return _jangkar_ke_x(n, ev[:len(xs)], xs)


def auroc_ci(y, s, grup, n=1000, seed=0):
    y, s, grup = map(np.asarray, (y, s, grup))
    ok = ~np.isnan(s)
    y, s, grup = y[ok], s[ok], grup[ok]
    if len(np.unique(y)) < 2:
        return dict(auroc=None, ci=None)
    base = roc_auc_score(y, s)
    rng = np.random.default_rng(seed)
    ug = np.unique(grup); idx = {g: np.where(grup == g)[0] for g in ug}
    v = []
    for _ in range(n):
        p = np.concatenate([idx[g] for g in rng.choice(ug, len(ug))])
        if len(np.unique(y[p])) == 2:
            v.append(roc_auc_score(y[p], s[p]))
    return dict(auroc=round(float(base), 3), ci=[round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)])


def fpr95(y, s):
    ok = ~np.isnan(s)
    fpr, tpr, _ = roc_curve(np.asarray(y)[ok], np.asarray(s)[ok])
    return round(float(fpr[min(np.searchsorted(tpr, 0.95), len(fpr) - 1)]), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--gt", required=True)
    ap.add_argument("--csv_dir", required=True)
    ap.add_argument("--out", default="hasil")
    ap.add_argument("--split", choices=["selang", "paruh"], default="selang")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    px = np.sort([p["x"] for p in json.load(open(a.gt))])
    D, ringkas = {}, {"validasi_odometri": {}, "per_kondisi": {}}
    for k in KONDISI:
        d = dict(np.load(os.path.join(a.data, f"{k}.npz")))
        d.update(dict(np.load(os.path.join(a.data, f"{k}_penghitung.npz"))))
        n = len(d["det_agen"])
        csvp = os.path.join(a.csv_dir, f"{k}.csv")
        c = pd.read_csv(csvp)
        ev_c, jenis_c = kejadian_csv(c)
        if k == "cerah":
            # cerah.csv berasal dari RUN LAIN (lihat HASIL.md). Momen avoid-nya diskalakan ke panjang
            # video sebagai prediksi, lalu dicocokkan dengan perubahan penghitung Avoids di overlay video.
            pred = np.round(ev_c * (n - 1) / (len(c) - 1)).astype(int)
            ev, n_cocok = kejadian_overlay_warna(d["ganti_avoids_warna"], pred)
            jenis = jenis_c
        else:
            ev, jenis, n_cocok = ev_c, jenis_c, None
        x = x_dari_kejadian(n, ev, jenis, px)
        d["hit_frames"] = np.array([e for e, t in zip(ev, jenis) if t == "hit"], dtype=int)
        d["x"] = x
        dist = px[None, :] - x[:, None]
        maju = np.where((dist >= 3) & (dist <= 15), dist, np.inf)
        d["dalam_jangkauan"] = np.isfinite(maju).any(axis=1)
        d["lubang_terdekat"] = np.where(d["dalam_jangkauan"], np.argmin(maju, axis=1), -1)
        d["gagal"] = d["dalam_jangkauan"] & (d["det_agen"] == 0)
        # skor per deteksi dari logit kotak teratas (atau kandidat terkuat jika tanpa deteksi)
        lg = d["logit_top"].astype(np.float64)
        d["msp"] = 1 - 1 / (1 + np.exp(-lg.max(axis=1)))
        m = lg.max(axis=1, keepdims=True)
        d["energi"] = -(m[:, 0] + np.log(np.exp(lg - m).sum(axis=1)))
        d["jointenergy"] = -np.logaddexp(0, lg).sum(axis=1)
        d["jointenergy_citra"] = -d["je_citra"]
        D[k] = d
        r = dict(frame=n, sumber_jangkar=("overlay video, dicocokkan ke prediksi dari run cerah lain" if k == "cerah"
                                          else "CSV run yang sama"),
                 jumlah_jangkar=int(len(ev)), hits=int(sum(t == "hit" for t in jenis)),
                 avoids=int(sum(t == "avoid" for t in jenis)))
        if n_cocok is not None:
            r["jangkar_cocok_dengan_overlay"] = int(n_cocok)
        ringkas["validasi_odometri"][k] = r

    # --- pembagian data ---------------------------------------------------------
    # "selang": blok 10 m sepanjang lintasan, mod 3 -> 0 = fit, 1 = kalibrasi ambang (cerah), 2 = uji.
    #           Ruas jalan yang diuji tersebar di seluruh lintasan, dan ambang tidak diambil dari data fit.
    # "paruh":  fit = cerah x < -163, kalibrasi = cerah blok genap di paruh kedua, uji = blok ganjil paruh kedua.
    #           Menguji apakah monitor yang di-fit di satu ruas jalan tetap berlaku di ruas lain.
    c = D["cerah"]
    blok = lambda x: np.floor((x - X0) / 10.0).astype(int)
    if a.split == "paruh":
        peran = lambda d: np.where(d["x"] < X_BELAH, 0, np.where(blok(d["x"]) % 2 == 0, 1, 2))
    else:
        peran = lambda d: blok(d["x"]) % 3
    fit = (peran(c) == 0) & (c["diproses"] == 1)
    kal = (peran(c) == 1) & (c["diproses"] == 1)
    F = c["fitur"][fit]
    mu, sd = F.mean(0), F.std(0) + 1e-6
    Z = (F - mu) / sd
    # PCA ke dimensi kecil dulu: 896 dimensi dari ~1000 frame berurutan membuat kovarians tidak stabil
    U, S, Vt = np.linalg.svd(Z - Z.mean(0), full_matrices=False)
    var = np.cumsum(S ** 2) / np.sum(S ** 2)
    n_pc = int(min(np.searchsorted(var, 0.95) + 1, 64))
    P = Vt[:n_pc].T
    Zp = (Z - Z.mean(0)) @ P
    lw = LedoitWolf().fit(Zp)
    Zn = Z / np.linalg.norm(Z, axis=1, keepdims=True)
    bmu, bsd = c["terang"][fit].mean(), c["terang"][fit].std()
    kmu, ksd = c["kontras"][fit].mean(), c["kontras"][fit].std()
    for k, d in D.items():
        z = (d["fitur"] - mu) / sd
        dz = (z - Z.mean(0)) @ P - lw.location_
        d["mahalanobis"] = np.einsum("ij,jk,ik->i", dz, lw.precision_, dz)
        zn = z / np.linalg.norm(z, axis=1, keepdims=True)
        d["knn"] = np.sort(1 - zn @ Zn.T, axis=1)[:, 4]          # k = 5
        d["kecerahan"] = np.abs(d["terang"] - bmu) / bsd + np.abs(d["kontras"] - kmu) / ksd
    tau = {s: float(np.nanpercentile(c[s][kal], 95)) for s in SKOR}
    ringkas["n_komponen_pca"] = n_pc

    # --- statistik per kondisi (frame uji) ---------------------------------------
    uji = {k: (peran(d) == 2) & (d["diproses"] == 1) for k, d in D.items()}
    for k, d in D.items():
        u = uji[k]; j = u & d["dalam_jangkauan"]
        kel = d["kelas_top"][u & (d["n_det"] > 0)]
        ringkas["per_kondisi"][k] = dict(
            frame_uji=int(u.sum()),
            deteksi_agen_saat_lubang_dalam_jangkauan=round(float(d["det_agen"][j].mean()), 3),
            deteksi_agen_saat_tidak_ada_lubang=round(float(d["det_agen"][u & ~d["dalam_jangkauan"]].mean()), 3),
            kesepakatan_deteksi_ulang_vs_agen=round(float(((d["n_det"][u] > 0) == (d["det_agen"][u] == 1)).mean()), 3),
            kelas_deteksi_ulang={"Low": int((kel == 0).sum()), "Medium": int((kel == 1).sum()), "High": int((kel == 2).sum())},
            laju_alarm_pada_ambang_p95_ID={s: round(float((d[s][u] > tau[s]).mean()), 3) for s in SKOR})

    # --- (a) deteksi OOD: hujan/malam vs cerah paruh kedua -------------------
    ringkas["auroc_ood"] = {}
    for k in ["hujan", "malam"]:
        y = np.r_[np.zeros(uji["cerah"].sum()), np.ones(uji[k].sum())]
        g = np.r_[D["cerah"]["lubang_terdekat"][uji["cerah"]], 100 + D[k]["lubang_terdekat"][uji[k]]]
        ringkas["auroc_ood"][f"{k}_vs_cerah"] = {
            s: auroc_ci(y, np.r_[D["cerah"][s][uji["cerah"]], D[k][s][uji[k]]], g) for s in SKOR}

    # --- (b) prediksi kegagalan persepsi (frame dengan lubang dalam jangkauan) ---
    yy, gg, ss = [], [], {s: [] for s in SKOR}
    for i, (k, d) in enumerate(D.items()):
        m = uji[k] & d["dalam_jangkauan"]
        yy.append(d["gagal"][m]); gg.append(i * 100 + d["lubang_terdekat"][m])
        for s in SKOR:
            ss[s].append(d[s][m])
    yy, gg = np.concatenate(yy), np.concatenate(gg)
    ringkas["auroc_kegagalan_gabungan"] = dict(n=int(len(yy)), n_gagal=int(yy.sum()), **{
        s: dict(**auroc_ci(yy, np.concatenate(ss[s]), gg), fpr95=fpr95(yy, np.concatenate(ss[s]))) for s in SKOR})
    # dalam satu kondisi saja (apakah skor membedakan frame gagal vs tidak, di cuaca yang sama?)
    ringkas["auroc_kegagalan_dalam_kondisi"] = {}
    for k, d in D.items():
        m = uji[k] & d["dalam_jangkauan"]
        ringkas["auroc_kegagalan_dalam_kondisi"][k] = dict(
            n=int(m.sum()), n_gagal=int(d["gagal"][m].sum()),
            **{s: auroc_ci(d["gagal"][m], d[s][m], d["lubang_terdekat"][m])["auroc"] for s in SKOR})

    # --- (c) waktu peringatan dini sebelum HIT --------------------------------
    ringkas["peringatan_dini_sebelum_hit_s"] = {}
    for k, d in D.items():
        hits = d["hit_frames"]
        out = {}
        for s in ["mahalanobis", "jointenergy_citra", "kecerahan"]:
            lead = []
            for h in hits:
                w = np.arange(max(0, h - 120), h)            # jendela 6 s sebelum HIT
                al = w[d[s][w] > tau[s]]
                lead.append(round((h - al[0]) * DT, 2) if len(al) else 0.0)
            out[s] = lead
        ringkas["peringatan_dini_sebelum_hit_s"][k] = dict(jumlah_hit=int(len(hits)), **out)
    ringkas["ambang_p95_ID"] = {s: round(v, 4) for s, v in tau.items()}
    ringkas["split"] = a.split
    ringkas["n_frame_fit_ID"] = int(fit.sum())
    ringkas["n_frame_kalibrasi_ambang"] = int(kal.sum())

    with open(os.path.join(a.out, "ringkasan_rekaman.json"), "w") as f:
        json.dump(ringkas, f, indent=1)

    # --- grafik ----------------------------------------------------------------
    warna = {"cerah": "#0f6e74", "hujan": "#5470a8", "malam": "#a2560b"}
    fig, ax = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True)
    for i, (k, d) in enumerate(D.items()):
        t = np.arange(len(d["x"]))
        ax[i].plot(d["x"], np.log10(d["mahalanobis"] + 1), lw=0.8, color=warna[k])
        ax[i].axhline(np.log10(tau["mahalanobis"] + 1), ls=":", c="#1b2428", lw=1)
        ax[i].fill_between(d["x"], 0, 1, where=d["gagal"], transform=ax[i].get_xaxis_transform(),
                           color="#c4621b", alpha=0.18, lw=0)
        for h in d["hit_frames"]:
            ax[i].axvline(d["x"][h], color="#8a2f3b", lw=1.2)
        for p in px:
            ax[i].plot([p], [0.02], "v", color="#5b6a71", ms=4, transform=ax[i].get_xaxis_transform())
        if a.split == "paruh":
            ax[i].axvline(X_BELAH, color="#5b6a71", lw=0.8, ls="--")
        ax[i].set_ylabel(f"{k}\nlog10(M+1)")
    ax[0].set_title("Skor Mahalanobis fitur neck per frame. Oranye = lubang 3–15 m tak terdeteksi agen; "
                    "merah = HIT; garis titik = ambang p95 ID", fontsize=9)
    if a.split == "paruh":
        ax[0].text(X_BELAH - 2, 0.9, "fit ID ←", ha="right", fontsize=8, transform=ax[0].get_xaxis_transform())
        ax[0].text(X_BELAH + 2, 0.9, "→ uji", fontsize=8, transform=ax[0].get_xaxis_transform())
    ax[-1].set_xlabel("posisi x kendaraan (m)")
    fig.tight_layout(); fig.savefig(os.path.join(a.out, "skor_sepanjang_lintasan.png"), dpi=140); plt.close(fig)
    print(json.dumps({k: ringkas[k] for k in ["validasi_odometri", "per_kondisi"]}, indent=1))
    print(json.dumps(ringkas["auroc_kegagalan_gabungan"], indent=1))


if __name__ == "__main__":
    main()
