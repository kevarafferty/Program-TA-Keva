"""
yolo_logit_hook.py — Mengambil logit kelas PER DETEKSI dan fitur neck dari YOLO
(Ultralytics) tanpa mengubah bobot atau cara inferensi Dika.

Masalah yang diselesaikan
-------------------------
model.predict() hanya mengembalikan kotak SETELAH NMS beserta conf = sigmoid(logit)
kelas tertinggi. Logit mentah tiap kelas (yang dibutuhkan skor energi / JointEnergy)
sudah hilang di titik itu. Modul ini:
  1. memasang forward hook pada lapisan Detect untuk menyalin
       - preds["scores"] : logit mentah semua anchor, bentuk (1, nc, N)
       - preds["feats"]  : tiga peta fitur neck (P3, P4, P5) yang masuk ke Detect
       - y               : prediksi terdekode (1, 4+nc, N) sebelum NMS
  2. menjalankan NMS yang sama dengan predictor Ultralytics, tetapi dengan
     return_idxs=True, sehingga setiap kotak yang lolos diketahui indeks anchor-nya
  3. mengambil logit 3 kelas pada indeks anchor itu.

Pemeriksaan otomatis (fungsi `verifikasi`): untuk setiap kotak, sigmoid(logit kelas
terpilih) harus sama dengan conf dari predict(), dan kelasnya harus sama.

Pengaturan inferensi WAJIB sama dengan kode Dika (environment/carla_env.py):
    imgsz=320, conf=0.05  (iou bawaan predictor Ultralytics = 0.7, max_det = 300)
"""
from __future__ import annotations

import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.utils import ops
from ultralytics.utils.nms import non_max_suppression

IMGSZ_DIKA = 320
CONF_DIKA = 0.05
IOU_DEFAULT = 0.7      # nilai bawaan predictor Ultralytics


class YoloDenganLogit:
    def __init__(self, bobot: str, device: str = "cpu"):
        self.model = YOLO(bobot)
        self.model.to(device)
        self.names = self.model.names
        self._tangkap = {}
        self._hook = None

    # -- hook ---------------------------------------------------------------
    def _pasang_hook(self):
        detect = self.model.model.model[-1]

        def hook(mod, inp, out):
            y, preds = out if isinstance(out, tuple) else (out, {})
            self._tangkap["y"] = y.detach().clone()
            if "scores" in preds:
                self._tangkap["logit"] = preds["scores"].detach().clone()
            self._tangkap["feats"] = [f.detach().clone() for f in inp[0]]

        self._hook = detect.register_forward_hook(hook)

    def _lepas_hook(self):
        if self._hook is not None:
            self._hook.remove()
            self._hook = None

    # -- inferensi ----------------------------------------------------------
    @torch.no_grad()
    def infer(self, img_bgr: np.ndarray, imgsz: int = IMGSZ_DIKA, conf: float = CONF_DIKA,
              iou: float = IOU_DEFAULT, max_det: int = 300) -> dict:
        """
        Kembalikan dict:
          boxes   (n,4) xyxy piksel citra asli   conf (n,)   cls (n,)
          logit   (n,nc) logit mentah per deteksi   anchor (n,) indeks anchor
          logit_semua (nc,N)  logit seluruh anchor (untuk skor tingkat citra)
          fitur   (C,) rata-rata global fitur neck P3|P4|P5 digabung
          pred_ultra : hasil asli model.predict() untuk dibandingkan
        """
        self._tangkap.clear()
        self._pasang_hook()
        try:
            res = self.model.predict(img_bgr, imgsz=imgsz, conf=conf, iou=iou,
                                     max_det=max_det, verbose=False)[0]
        finally:
            self._lepas_hook()

        y = self._tangkap["y"]                                  # (1, 4+nc, N)
        logit_all = self._tangkap["logit"][0]                   # (nc, N)
        nc = logit_all.shape[0]
        out, keep = non_max_suppression(y, conf_thres=conf, iou_thres=iou, max_det=max_det,
                                        nc=nc, return_idxs=True)
        det, idx = out[0], keep[0].long()

        # skala kotak dari ukuran letterbox ke ukuran citra asli, sama seperti predictor
        boxes = det[:, :4].clone()
        if len(boxes):
            boxes = ops.scale_boxes(self._ukuran_input(), boxes, res.orig_img.shape)
        feats = self._tangkap["feats"]
        fitur = torch.cat([f.mean(dim=(2, 3))[0] for f in feats]).cpu().numpy()

        return dict(
            boxes=boxes.cpu().numpy(), conf=det[:, 4].cpu().numpy(), cls=det[:, 5].cpu().numpy().astype(int),
            logit=logit_all[:, idx].T.cpu().numpy(), anchor=idx.cpu().numpy(),
            logit_semua=logit_all.cpu().numpy(), fitur=fitur,
            fitur_peta=[f[0].cpu().numpy() for f in feats],
            pred_ultra=res,
        )

    def _ukuran_input(self):
        """Ukuran tensor yang benar-benar masuk ke jaringan (h, w) setelah letterbox."""
        f = self._tangkap["feats"][0]          # P3 = stride 8
        return (f.shape[2] * 8, f.shape[3] * 8)

    # -- pemeriksaan --------------------------------------------------------
    def verifikasi(self, hasil: dict, tol: float = 1e-4) -> dict:
        """Bandingkan hasil hook dengan predict() asli."""
        r = hasil["pred_ultra"].boxes
        conf_u = r.conf.cpu().numpy()
        cls_u = r.cls.cpu().numpy().astype(int)
        box_u = r.xyxy.cpu().numpy()
        n_h, n_u = len(hasil["conf"]), len(conf_u)
        if n_h != n_u:
            return dict(ok=False, alasan=f"jumlah kotak beda: hook {n_h} vs predict {n_u}")
        if n_h == 0:
            return dict(ok=True, n=0, maks_selisih_conf=0.0, maks_selisih_kotak_px=0.0)
        sig = 1 / (1 + np.exp(-hasil["logit"][np.arange(n_h), hasil["cls"]]))
        d_conf = np.abs(sig - conf_u).max()
        d_box = np.abs(hasil["boxes"] - box_u).max()
        cls_sama = bool((hasil["cls"] == cls_u).all())
        return dict(ok=bool(d_conf < tol and cls_sama and d_box < 0.5), n=n_h,
                    maks_selisih_conf=float(d_conf), maks_selisih_kotak_px=float(d_box), kelas_sama=cls_sama)


# ---------------------------------------------------------------------------
# Skor monitor persepsi (Bab 2.1.6 proposal)
# ---------------------------------------------------------------------------
def joint_energy(logit: np.ndarray) -> np.ndarray:
    """S_JE = sum_c log(1 + e^{f_c}). Tinggi = lebih in-distribution. logit: (..., nc)."""
    return np.logaddexp(0.0, logit).sum(axis=-1)


def energi(logit: np.ndarray, T: float = 1.0) -> np.ndarray:
    """E = -T log sum_c e^{f_c/T}. Rendah = lebih in-distribution."""
    z = logit / T
    m = z.max(axis=-1, keepdims=True)
    return -T * (m.squeeze(-1) + np.log(np.exp(z - m).sum(axis=-1)))


def msp_sigmoid(logit: np.ndarray) -> np.ndarray:
    """Pembanding MSP untuk kepala multi-label: probabilitas sigmoid tertinggi."""
    return 1 / (1 + np.exp(-logit.max(axis=-1)))


def max_logit(logit: np.ndarray) -> np.ndarray:
    return logit.max(axis=-1)
