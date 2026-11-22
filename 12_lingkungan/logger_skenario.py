"""
logger_skenario.py — [#25] Perekam per langkah untuk data monitor (Fase 2).

Per episode, di folder run:
  langkah_ep{k:03d}_seed{s}.csv   satu baris per langkah: pose, aksi, nilai-Q, state 10-D, deteksi teratas,
                                  faktor transisi, cuaca terpasang, reward, hits/avoids
  persepsi_ep{k:03d}_seed{s}.npz  fitur neck YOLO (T, 896) float16, logit anchor teratas (T, k, 3) float16,
                                  semua deteksi per langkah (logit 3 kelas, kotak, conf, kelas, anchor)
  gt_ep{k:03d}_seed{s}.json       tata letak lubang episode ini (format pothole_gt.json)
  meta_ep{k:03d}_seed{s}.json     spesifikasi skenario, angka cuaca, throttle, geometri kendaraan, versi, waktu

Penyelarasan waktu: baris langkah t berisi state_t (dari frame yang dirender SEBELUM aksi t), persepsi
yang menghasilkan state_t, nilai-Q dan aksi yang dipilih dari state_t, pose saat frame itu diambil, lalu
reward/done yang dihasilkan aksi t. Jadi label kontak dalam horizon H dari pose bisa langsung dipasangkan
dengan skor monitor di baris yang sama.
"""
from __future__ import annotations

import csv
import json
import os

import numpy as np

KOLOM_CUACA = ["sun_altitude_angle", "precipitation", "precipitation_deposits", "wetness", "fog_density",
               "fog_distance", "cloudiness"]


class LoggerEpisode:
    def __init__(self, run_dir: str, episode: int, seed: int, simpan_fitur: bool = True, n_aksi: int = 3):
        self.dir = run_dir
        self.nama = "ep%03d_seed%d" % (episode, seed)
        self.episode, self.seed = episode, seed
        self.simpan_fitur = simpan_fitur
        self.n_aksi = n_aksi
        self.kolom = (["step", "t_sim", "frame_dunia", "frame_kamera", "x", "y", "z", "yaw", "v_kmh", "steer",
                       "throttle", "aksi"]
                      + ["q%d" % i for i in range(n_aksi)] + ["q_margin"]
                      + ["s%d" % i for i in range(10)]
                      + ["n_det", "conf_top", "cls_top", "hook_cocok", "f_transisi", "f_korupsi"]
                      + ["w_" + c for c in KOLOM_CUACA]
                      + ["reward", "done", "hits", "avoids"])
        self.f = open(os.path.join(run_dir, "langkah_%s.csv" % self.nama), "w", newline="")
        self.w = csv.DictWriter(self.f, fieldnames=self.kolom)
        self.w.writeheader()
        self.fitur, self.topk, self.topk_idx = [], [], []
        self.det = dict(step=[], logit=[], box=[], conf=[], cls=[], anchor=[])
        self.n = 0
        self.n_tidak_cocok = 0
        self.n_tanpa_rekam = 0
        self.logit_dari_sigmoid = False

    def catat(self, step: int, pose: dict, aksi: int, q: np.ndarray, state_vec: np.ndarray, persepsi: dict,
              f_transisi: float, cuaca: dict, reward: float, done: bool, info: dict):
        q = np.asarray(q, dtype=np.float64).ravel()
        qs = np.sort(q)[::-1]
        r = dict(step=step, aksi=int(aksi), reward=round(float(reward), 4), done=int(bool(done)),
                 hits=info.get("hits", 0), avoids=info.get("avoids", 0),
                 f_transisi=round(float(f_transisi), 4), q_margin=round(float(qs[0] - qs[1]), 6) if len(qs) > 1 else "")
        r.update({k: pose[k] for k in ("t_sim", "frame_dunia", "frame_kamera", "x", "y", "z", "yaw", "v_kmh",
                                       "steer", "throttle")})
        for i in range(self.n_aksi):
            r["q%d" % i] = round(float(q[i]), 6)
        for i in range(10):
            r["s%d" % i] = round(float(state_vec[i]), 6)
        for c in KOLOM_CUACA:
            r["w_" + c] = round(float(cuaca.get(c, float("nan"))), 3) if cuaca else ""
        if persepsi is None:
            self.n_tanpa_rekam += 1
            r.update(n_det="", conf_top="", cls_top="", hook_cocok=0, f_korupsi="")
            if self.simpan_fitur:
                self.fitur.append(None)
                self.topk.append(None)
                self.topk_idx.append(None)
        else:
            n = len(persepsi["conf"])
            j = int(np.argmax(persepsi["conf"])) if n else -1
            r.update(n_det=n, conf_top=round(float(persepsi["conf"][j]), 6) if n else 0.0,
                     cls_top=int(persepsi["cls"][j]) if n else -1, hook_cocok=int(persepsi["cocok"]),
                     f_korupsi=round(float(persepsi.get("f_korupsi", 0.0)), 4))
            self.n_tidak_cocok += int(not persepsi["cocok"])
            self.logit_dari_sigmoid |= bool(persepsi.get("logit_dari_sigmoid"))
            if self.simpan_fitur:
                self.fitur.append(persepsi["fitur"].astype(np.float16))
                self.topk.append(persepsi["topk_logit"].astype(np.float16))
                self.topk_idx.append(persepsi["topk_anchor"].astype(np.int32))
                for i in range(n):
                    self.det["step"].append(step)
                    self.det["logit"].append(persepsi["logit"][i])
                    self.det["box"].append(persepsi["boxes"][i])
                    self.det["conf"].append(persepsi["conf"][i])
                    self.det["cls"].append(persepsi["cls"][i])
                    self.det["anchor"].append(persepsi["anchor"][i])
        self.w.writerow(r)
        self.n += 1

    def _tumpuk(self, xs, bentuk, dtype):
        if not xs:
            return np.zeros((0,) + bentuk, dtype)
        ref = next((x for x in xs if x is not None), None)
        if ref is None:
            return np.full((len(xs),) + bentuk, np.nan, dtype)
        isi = np.full(ref.shape, np.nan if np.issubdtype(dtype, np.floating) else -1, dtype)
        return np.stack([x if x is not None else isi for x in xs]).astype(dtype)

    def tutup(self, meta: dict, gt: list):
        self.f.close()
        if self.simpan_fitur:
            ref_f = next((x for x in self.fitur if x is not None), None)
            ref_t = next((x for x in self.topk if x is not None), None)
            fitur = self._tumpuk(self.fitur, ref_f.shape if ref_f is not None else (0,), np.float16)
            topk = self._tumpuk(self.topk, ref_t.shape if ref_t is not None else (0, 3), np.float16)
            topk_idx = self._tumpuk(self.topk_idx, (ref_t.shape[0],) if ref_t is not None else (0,), np.int32)
            d = self.det
            np.savez_compressed(
                os.path.join(self.dir, "persepsi_%s.npz" % self.nama),
                fitur=fitur, topk_logit=topk, topk_anchor=topk_idx,
                det_step=np.asarray(d["step"], np.int32),
                det_logit=np.asarray(d["logit"], np.float32).reshape(-1, 3),
                det_box=np.asarray(d["box"], np.float32).reshape(-1, 4),
                det_conf=np.asarray(d["conf"], np.float32), det_cls=np.asarray(d["cls"], np.int16),
                det_anchor=np.asarray(d["anchor"], np.int32))
        meta = dict(meta)
        meta.update(langkah=self.n, hook_tidak_cocok=self.n_tidak_cocok, tanpa_rekam_persepsi=self.n_tanpa_rekam,
                    logit_dari_sigmoid=self.logit_dari_sigmoid)
        with open(os.path.join(self.dir, "meta_%s.json" % self.nama), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=1, ensure_ascii=False, default=_json_default)
        return meta


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if hasattr(o, "ke_dict"):
        return o.ke_dict()
    return str(o)


def muat_episode(run_dir: str, nama: str) -> dict:
    """Pembaca untuk analisis Fase 2: kembalikan dict berisi tabel langkah (dict kolom -> array), npz, meta, gt."""
    import csv as _csv
    with open(os.path.join(run_dir, "langkah_%s.csv" % nama)) as f:
        rows = list(_csv.DictReader(f))
    kol = {}
    for k in rows[0].keys() if rows else []:
        try:
            kol[k] = np.array([float(r[k]) if r[k] != "" else np.nan for r in rows])
        except ValueError:
            kol[k] = np.array([r[k] for r in rows])
    out = dict(langkah=kol)
    p = os.path.join(run_dir, "persepsi_%s.npz" % nama)
    if os.path.exists(p):
        out["persepsi"] = dict(np.load(p))
    with open(os.path.join(run_dir, "meta_%s.json" % nama), encoding="utf-8") as f:
        out["meta"] = json.load(f)
    with open(os.path.join(run_dir, "gt_%s.json" % nama), encoding="utf-8") as f:
        out["gt"] = json.load(f)
    return out
