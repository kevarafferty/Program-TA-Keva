"""
label_kegagalan.py — Label kegagalan OBJEKTIF dari log runner (§2.1.2 proposal + revisi T21), tanpa CARLA.

Per langkah (sejajar dengan baris langkah_*.csv):
  kontak          ada roda menyentuh lubang Medium/High (02_pelabel_roda/kontak_roda.py, geometri terukur)
  kontak_H        ada kontak pada langkah t+1..t+H, H = 2 s       -> label monitor KEPUTUSAN (U_D)
  target          lubang Medium/High terdekat yang pusatnya 3–15 m di depan DAN kotak proyeksinya tampak di citra
  iou_top         IoU kotak YOLO teratas (yang masuk state agen) dengan kotak proyeksi target
  gagal_persepsi  1 jika ada target dan iou_top < IOU_MIN; 0 jika cocok; -1 jika tidak ada target  -> label per frame
  palsu_top       1 jika kotak teratas tidak mengenai lubang mana pun yang tampak (IoU < 0,1)       -> deteksi palsu

Per lintasan lubang (satu baris per lubang GT; label utama monitor PERSEPSI sesuai T21):
  status          kontak | terhindar | tak_tercapai
  n_terlihat      frame jendela 3–15 m yang kotak proyeksinya tampak
  n_cocok_top     frame jendela dengan kotak teratas cocok (IoU >= IOU_MIN)
  frac_cocok      n_cocok_top / n_terlihat
  gagal_persepsi  1 jika frac_cocok < FRAKSI_MIN (0,5): agen tidak melihat lubang itu secara konsisten; -1 jika n_terlihat = 0
  terlambat       1 jika lubang tidak pernah cocok pada jarak >= D_TERLAMBAT (8 m; agen baru bereaksi di 6–8 m, T12)
  jarak_cocok_pertama  jarak (m) saat lubang pertama kali cocok -> bahan waktu peringatan

[22 Nov] Kriteria awal "kurang dari 3 frame cocok" terlalu longgar: malam (A1) cocok 4–61% frame dan silau (A4)
14–51% tetap berlabel "terlihat". Cerah (C1 t1) 77–100% di semua 19 lubang. Ambang 0,5 dipilih setelah melihat
data uji 1 episode -> hitungan mentah disimpan agar analisis sensitivitas ambang bisa dilakukan.

Proyeksi (05_proyeksi_kamera, KAMERA_DIKA) diverifikasi 22 Nov pada C1 t1 cerah: IoU >= 0,3 pada 86% frame
berlubang 3–15 m, selisih pusat median 1,4 px / 0,1 px. Kotak YOLO ±1,6x lebih tinggi dari proyeksi bidang datar.

Asumsi yang perlu disetujui: IOU_MIN 0,3 (T-log 7 Nov, lubang kecil/jauh), FRAKSI_MIN 0,5, D_TERLAMBAT 8 m,
jangkauan 3–15 m (sama dengan T20), H = 2 s, setengah lebar ban 0,075 m (estimasi) untuk semua kendaraan.
"""
from __future__ import annotations

import csv
import json
import os
import sys

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(DIR, "..", "02_pelabel_roda")))
sys.path.insert(0, os.path.normpath(os.path.join(DIR, "..", "05_proyeksi_kamera")))
from kontak_roda import MICROLINO, GeometriKendaraan, Lubang, kontak_per_langkah, label_horizon  # noqa: E402
from proyeksi_kamera import KAMERA_DIKA, kotak_2d_lubang  # noqa: E402

DT = 0.05
H_DETIK = 2.0
JANGKAUAN = (3.0, 15.0)
IOU_MIN = 0.3
IOU_PALSU = 0.1
FRAKSI_MIN = 0.5
D_TERLAMBAT = 8.0
SEV_RELEVAN = ("Medium", "High")
VERSI = "label_kegagalan v2 (22 Nov 2026, FRAKSI_MIN 0,5 / D_TERLAMBAT 8 m)"


def geometri_dari_meta(meta: dict) -> GeometriKendaraan:
    g = (meta or {}).get("geometri_kendaraan") or {}
    if not g or g.get("blueprint", "vehicle.micro.microlino") == "vehicle.micro.microlino" or not g.get("roda_lokal_xy"):
        return MICROLINO
    r = np.array(g["roda_lokal_xy"], float)
    depan, belakang = r[r[:, 0] > 0], r[r[:, 0] <= 0]
    return GeometriKendaraan(
        jarak_sumbu_depan=float(depan[:, 0].mean()), jarak_sumbu_belakang=float(-belakang[:, 0].mean()),
        jejak_depan=float(np.ptp(depan[:, 1])), jejak_belakang=float(np.ptp(belakang[:, 1])),
        setengah_lebar_ban=0.075, setengah_lebar_bodi=float(g["bbox_extent"][1]),
        setengah_panjang_bodi=float(g["bbox_extent"][0]),
        sumber="%s, roda dari meta runner; r_w estimasi" % g["blueprint"])


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def _baca_csv(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    kol = {}
    for k in rows[0].keys():
        try:
            kol[k] = np.array([float(r[k]) if r[k] != "" else np.nan for r in rows])
        except ValueError:
            kol[k] = np.array([r[k] for r in rows])
    return kol


def label_lintasan(x, y, yaw, gt, geo=MICROLINO, z=None, det=None, f_transisi=None):
    """Inti pelabel. x,y,yaw (T,) pose saat frame diambil; gt = daftar entri GT; det = dict npz persepsi atau None."""
    T = len(x)
    z = np.zeros(T) if z is None else z
    L = [Lubang.dari_json(g) for g in gt]
    rel = [g for g in gt if g.get("severity_label", "High") in SEV_RELEVAN]
    k = kontak_per_langkah(x, y, yaw, L, geo)
    kontak = k["kontak"]
    kontak_H = label_horizon(kontak, int(round(H_DETIK / DT)))
    kena_id = {e["lubang"] for e in k["kejadian"]}
    kontak_pertama = {}
    for e in k["kejadian"]:
        kontak_pertama.setdefault(e["lubang"], e["mulai"])

    target = np.full(T, -1, int)
    iou_top = np.full(T, np.nan)
    gagal_p = np.full(T, -1, np.int8)
    palsu = np.zeros(T, np.int8)
    n_det = np.zeros(T, int)
    per = {g["id"]: dict(n_jendela=0, n_terlihat=0, n_cocok_top=0, n_cocok_any=0, cocok_pertama=None,
                         jarak_cocok_pertama=None, cocok_jauh=False, f_tr=[]) for g in rel}
    if det is not None and len(det.get("det_step", [])):
        urut = np.argsort(det["det_step"], kind="stable")
        ds, db, dc = det["det_step"][urut], det["det_box"][urut], det["det_conf"][urut]
        awal = np.searchsorted(ds, np.arange(1, T + 1), "left")
        akhir = np.searchsorted(ds, np.arange(1, T + 1), "right")
    else:
        awal = akhir = None
    for t in range(T):
        th = np.radians(yaw[t])
        fw = np.array([np.cos(th), np.sin(th)])
        boxes = db[awal[t]:akhir[t]] if awal is not None else np.zeros((0, 4))
        confs = dc[awal[t]:akhir[t]] if awal is not None else np.zeros(0)
        n_det[t] = len(boxes)
        top = boxes[int(np.argmax(confs))] if len(boxes) else None
        pose = (x[t], y[t], z[t], yaw[t])
        tampak = []            # (jarak_maju, idx, kotak) lubang yang kotaknya tampak, 0–30 m
        for i, g in enumerate(rel):
            maju = float(fw @ np.array([g["x"] - x[t], g["y"] - y[t]]))
            if not (0.0 < maju <= 30.0):
                continue
            dalam = JANGKAUAN[0] <= maju <= JANGKAUAN[1]
            if dalam:
                per[g["id"]]["n_jendela"] += 1
                if f_transisi is not None:
                    per[g["id"]]["f_tr"].append(float(f_transisi[t]))
            kb = kotak_2d_lubang(KAMERA_DIKA, pose, g, z_jalan=float(g.get("z", 0.0)))
            if kb is None:
                continue
            tampak.append((maju, i, kb))
            if dalam:
                p = per[g["id"]]
                p["n_terlihat"] += 1
                it = _iou(top, kb) if top is not None else 0.0
                ia = max((_iou(b, kb) for b in boxes), default=0.0)
                if it >= IOU_MIN:
                    p["n_cocok_top"] += 1
                    p["cocok_jauh"] |= maju >= D_TERLAMBAT
                    if p["cocok_pertama"] is None:
                        p["cocok_pertama"], p["jarak_cocok_pertama"] = t + 1, round(maju, 2)
                if ia >= IOU_MIN:
                    p["n_cocok_any"] += 1
        dalam = [(m, i, kb) for m, i, kb in tampak if JANGKAUAN[0] <= m <= JANGKAUAN[1]]
        if dalam:
            m, i, kb = min(dalam, key=lambda q: q[0])
            target[t] = i
            iou_top[t] = _iou(top, kb) if top is not None else 0.0
            gagal_p[t] = int(iou_top[t] < IOU_MIN)
        if top is not None and all(_iou(top, kb) < IOU_PALSU for _, _, kb in tampak):
            palsu[t] = 1

    xmax = float(np.nanmax(x))
    lintasan = []
    for g in gt:
        lewat = g["x"] + g["extent_x"] < xmax
        st = "kontak" if g["id"] in kena_id else ("terhindar" if lewat else "tak_tercapai")
        p = per.get(g["id"])
        b = dict(id=g["id"], x=g["x"], y=g["y"], severity=g.get("severity_label", "High"), status=st,
                 langkah_kontak=(kontak_pertama.get(g["id"], -1) + 1) if g["id"] in kontak_pertama else "")
        if p is not None:
            fr = p["n_cocok_top"] / p["n_terlihat"] if p["n_terlihat"] else float("nan")
            gp = -1 if p["n_terlihat"] == 0 else int(fr < FRAKSI_MIN)
            tl = -1 if p["n_terlihat"] == 0 else int(not p["cocok_jauh"])
            b.update(n_jendela=p["n_jendela"], n_terlihat=p["n_terlihat"], n_cocok_top=p["n_cocok_top"],
                     n_cocok_any=p["n_cocok_any"], frac_cocok=round(fr, 3) if fr == fr else "",
                     gagal_persepsi=gp, terlambat=tl,
                     langkah_cocok_pertama=p["cocok_pertama"] or "", jarak_cocok_pertama=p["jarak_cocok_pertama"] or "",
                     f_transisi_jendela=round(float(np.mean(p["f_tr"])), 3) if p["f_tr"] else "")
        lintasan.append(b)
    langkah = dict(kontak=kontak.astype(np.int8), kontak_H=kontak_H.astype(np.int8), target=target,
                   iou_top=iou_top.astype(np.float32), gagal_persepsi=gagal_p, palsu_top=palsu, n_det=n_det,
                   jarak_min_roda=k["jarak_min"].astype(np.float32))
    return langkah, lintasan


def label_episode(run: str, nama: str) -> dict:
    L = _baca_csv(os.path.join(run, "langkah_%s.csv" % nama))
    with open(os.path.join(run, "gt_%s.json" % nama), encoding="utf-8") as f:
        gt = json.load(f)
    with open(os.path.join(run, "meta_%s.json" % nama), encoding="utf-8") as f:
        meta = json.load(f)
    p = os.path.join(run, "persepsi_%s.npz" % nama)
    det = dict(np.load(p)) if os.path.exists(p) else None
    geo = geometri_dari_meta(meta)
    langkah, lintasan = label_lintasan(L["x"], L["y"], L["yaw"], gt, geo, L.get("z"), det, L.get("f_transisi"))
    return dict(langkah=langkah, lintasan=lintasan, meta=meta, gt=gt, csv=L, geometri=geo.sumber)


def simpan(run: str, nama: str, hasil: dict):
    np.savez_compressed(os.path.join(run, "label_%s.npz" % nama), versi=VERSI, **hasil["langkah"])
    kol = ["id", "x", "y", "severity", "status", "langkah_kontak", "n_jendela", "n_terlihat", "n_cocok_top",
           "n_cocok_any", "frac_cocok", "gagal_persepsi", "terlambat", "langkah_cocok_pertama", "jarak_cocok_pertama",
           "f_transisi_jendela"]
    with open(os.path.join(run, "lintasan_%s.csv" % nama), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kol, extrasaction="ignore")
        w.writeheader()
        for b in hasil["lintasan"]:
            w.writerow(b)


def ringkas_episode(hasil: dict, ring: dict) -> dict:
    lt = hasil["lintasan"]
    N = len(lt)
    n_k = sum(b["status"] == "kontak" for b in lt)
    n_t = sum(b["status"] == "terhindar" for b in lt)
    n_tt = N - n_k - n_t
    lewat = n_k + n_t
    rel = [b for b in lt if "gagal_persepsi" in b and b["gagal_persepsi"] != -1 and b["status"] != "tak_tercapai"]
    lg = hasil["langkah"]
    adag = lg["gagal_persepsi"] >= 0
    return dict(
        n_lubang=N, n_kontak=n_k, n_terhindar=n_t, n_tak_tercapai=n_tt,
        roda_tak_tercapai_gagal=100.0 * n_t / N if N else np.nan,          # metrik utama HASIL_BASELINE
        roda_hanya_dilewati=100.0 * n_t / lewat if lewat else np.nan,
        roda_cara_lama=100.0 * (N - n_k) / N if N else np.nan,
        dika=100.0 * int(ring.get("avoids", 0)) / N if N else np.nan,
        gagal_persepsi_lintasan=100.0 * float(np.mean([b["gagal_persepsi"] for b in rel])) if rel else np.nan,
        terlambat_lintasan=100.0 * float(np.mean([b["terlambat"] for b in rel])) if rel else np.nan,
        gagal_persepsi_frame=100.0 * float(lg["gagal_persepsi"][adag].mean()) if adag.any() else np.nan,
        palsu_top_frame=100.0 * float(lg["palsu_top"][lg["target"] < 0].mean()) if (lg["target"] < 0).any() else np.nan,
        langkah_kontak_H=100.0 * float(lg["kontak_H"].mean()),
        akhir=ring.get("akhir", ""), episode_gagal=100.0 * int(ring.get("akhir", "finis") in ("tabrakan", "keluar_jalan")))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Label satu run (semua episode). Untuk banyak run pakai analisis_skenario.py")
    ap.add_argument("run")
    a = ap.parse_args()
    with open(os.path.join(a.run, "ringkasan_episode.csv")) as f:
        for r in csv.DictReader(f):
            nama = "ep%03d_seed%s" % (int(r["episode"]), r["seed"])
            h = label_episode(a.run, nama)
            simpan(a.run, nama, h)
            print(nama, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in ringkas_episode(h, r).items()})
