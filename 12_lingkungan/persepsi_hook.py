"""
persepsi_hook.py — [#25] Rekam logit per deteksi, logit anchor teratas, dan fitur neck YOLO
dari inferensi yang SAMA yang dipakai agen (tanpa inferensi kedua, tanpa mengubah hasil).

Dasar: 04_monitor_persepsi/yolo_logit_hook.py (terverifikasi identik dengan predict() pada 689 inferensi, T8).
Perbedaan: hook dipasang PERMANEN pada lapisan Detect milik env.yolo_model, lalu setelah panggilan
self.yolo_model(image, imgsz=320, conf=0.05) milik kode Dika, kita baca tangkapan hook dan
mencocokkan tiap kotak hasil Ultralytics ke indeks anchor-nya.

Pencocokan anchor (dua cara, yang pertama yang berhasil dipakai):
  1. NMS ulang dengan return_idxs=True pada keluaran Detect (sama seperti yolo_logit_hook.py).
  2. Cadangan untuk versi Ultralytics yang NMS-nya tidak punya return_idxs: cari anchor yang skor
     kelasnya sama dengan conf kotak (selisih < 1e-6) dan kotaknya paling dekat.
Setiap langkah diperiksa: sigmoid(logit kelas terpilih) harus = conf dari Ultralytics, kelas sama,
jumlah kotak sama. Kegagalan dihitung (kolom hook_cocok di log), bukan dibuang diam-diam.

Logit mentah: diambil dari preds["scores"] kalau versi Ultralytics menyediakannya; kalau tidak,
dihitung balik dari probabilitas sigmoid (logit = ln p/(1-p), dipotong di p in [1e-7, 1-1e-7]);
kolom logit_dari_sigmoid = 1 menandai kasus ini.
"""
from __future__ import annotations

import numpy as np

CONF_DIKA = 0.05
IOU_DEFAULT = 0.7
MAX_DET = 300


def _nms_fungsi():
    try:
        from ultralytics.utils.nms import non_max_suppression   # Ultralytics >= 8.3.1xx
        return non_max_suppression
    except Exception:
        from ultralytics.utils.ops import non_max_suppression
        return non_max_suppression


class HookPersepsi:
    def __init__(self, yolo, topk_anchor: int = 100, conf: float = CONF_DIKA, iou: float = IOU_DEFAULT,
                 max_det: int = MAX_DET):
        import torch  # noqa: F401  (pastikan torch ada)
        self.yolo = yolo
        self.topk = int(topk_anchor)
        self.conf, self.iou, self.max_det = conf, iou, max_det
        self._tangkap = {}
        self._nms = _nms_fungsi()
        self._nms_idx_ok = None          # None = belum dicoba
        self.detect = None
        self._h = None
        self.n_panggil = 0
        self.n_tidak_cocok = 0
        self.pastikan()

    def _detect_aktif(self):
        """Lapisan Detect yang BENAR-BENAR dipakai predictor. Di beberapa versi Ultralytics predictor
        memakai salinan model (AutoBackend), sehingga hook pada yolo.model tidak pernah terpanggil."""
        p = getattr(self.yolo, "predictor", None)
        m = getattr(p, "model", None) if p is not None else None
        if m is not None:
            m = getattr(m, "model", m)          # AutoBackend -> DetectionModel
            return m.model[-1]
        return self.yolo.model.model[-1]

    def pastikan(self):
        """Pasang (ulang) hook kalau lapisan Detect aktif berubah. Panggil sebelum tiap inferensi."""
        d = self._detect_aktif()
        if d is not self.detect:
            self.lepas()
            self.detect = d
            self._h = d.register_forward_hook(self._hook)

    def _hook(self, mod, inp, out):
        y, preds = (out if isinstance(out, tuple) else (out, None))
        if isinstance(y, (list, tuple)):   # jaga-jaga: beberapa versi mengembalikan (y, x)
            y = y[0]
        self._tangkap["y"] = y.detach()
        sc = None
        if isinstance(preds, dict) and "scores" in preds:
            sc = preds["scores"].detach()
        self._tangkap["scores"] = sc
        self._tangkap["feats"] = [f.detach() for f in inp[0]]

    def lepas(self):
        if self._h is not None:
            self._h.remove()
            self._h = None

    def kosongkan(self):
        self._tangkap.clear()
        self.pastikan()

    # ------------------------------------------------------------------------------------------
    def ekstrak(self, hasil_ultra) -> dict:
        """hasil_ultra = results[0] dari panggilan yolo milik kode Dika (setelah hook menangkap).

        Tensor tangkapan hook dibuat di dalam torch.inference_mode() oleh predictor Ultralytics.
        NMS di beberapa versi (mis. 8.4.13 di laptop) mengubah tensor secara in-place, yang DILARANG
        untuk inference tensor di luar inference_mode -> seluruh ekstraksi dijalankan di dalamnya.
        """
        import torch
        with torch.inference_mode():
            return self._ekstrak(hasil_ultra)

    def _ekstrak(self, hasil_ultra) -> dict:
        import torch
        if "y" not in self._tangkap:
            raise RuntimeError("Hook Detect tidak menangkap apa pun: model yang dipanggil bukan model yang di-hook")
        self.n_panggil += 1
        y = self._tangkap["y"]                     # (1, 4+nc, N), kotak xywh letterbox, skor sigmoid
        nc = y.shape[1] - 4
        feats = self._tangkap["feats"]
        fitur = torch.cat([f.float().mean(dim=(2, 3))[0] for f in feats]).cpu().numpy().astype(np.float32)
        if self._tangkap.get("scores") is not None:
            logit_all = self._tangkap["scores"][0].float()          # (nc, N)
            dari_sigmoid = False
        else:
            p = y[0, 4:].float().clamp(1e-7, 1 - 1e-7)
            logit_all = torch.log(p / (1 - p))
            dari_sigmoid = True

        b = hasil_ultra.boxes
        conf_u = b.conf.cpu().numpy().astype(np.float32)
        cls_u = b.cls.cpu().numpy().astype(int)
        box_u = b.xyxy.cpu().numpy().astype(np.float32)
        n = len(conf_u)

        idx = self._cocokkan(y, nc, conf_u, cls_u, box_u, hasil_ultra)
        L = logit_all.cpu().numpy().astype(np.float32)               # (nc, N)
        if idx is not None and n:
            logit = L[:, idx].T                                       # (n, nc)
            sig = 1.0 / (1.0 + np.exp(-logit[np.arange(n), cls_u]))
            cocok = bool(np.abs(sig - conf_u).max() < 1e-4 and (np.argmax(logit, 1) == cls_u).all())
        elif n == 0:
            logit = np.zeros((0, nc), np.float32)
            cocok = True
            idx = np.zeros(0, int)
        else:
            logit = np.full((n, nc), np.nan, np.float32)
            cocok = False
            idx = np.full(n, -1, int)
        if not cocok:
            self.n_tidak_cocok += 1

        # anchor teratas (menurut logit maksimum) untuk skor tingkat citra
        mx = L.max(axis=0)
        k = min(self.topk, mx.shape[0])
        top = np.argpartition(-mx, k - 1)[:k] if k > 0 else np.zeros(0, int)
        top = top[np.argsort(-mx[top])]
        return dict(boxes=box_u, conf=conf_u, cls=cls_u, logit=logit.astype(np.float32), anchor=np.asarray(idx),
                    fitur=fitur, topk_logit=L[:, top].T.astype(np.float32), topk_anchor=top.astype(np.int32),
                    n_anchor=int(L.shape[1]), cocok=cocok, logit_dari_sigmoid=dari_sigmoid)

    # ------------------------------------------------------------------------------------------
    def _cocokkan(self, y, nc, conf_u, cls_u, box_u, hasil_ultra):
        n = len(conf_u)
        if n == 0:
            return np.zeros(0, int)
        if self._nms_idx_ok is not False:
            try:
                out, keep = self._nms(y.clone(), conf_thres=self.conf, iou_thres=self.iou, max_det=self.max_det,
                                      nc=nc, return_idxs=True)
                det, idx = out[0], keep[0].long().cpu().numpy()
                self._nms_idx_ok = True
                if len(idx) == n:
                    c_h = det[:, 4].cpu().numpy()
                    if np.abs(c_h - conf_u).max() < 1e-5 and (det[:, 5].cpu().numpy().astype(int) == cls_u).all():
                        return idx
            except TypeError:
                self._nms_idx_ok = False      # versi tanpa return_idxs
            except Exception as e:            # error lain: pakai cadangan untuk langkah ini saja
                if not getattr(self, "_peringatan_nms", False):
                    print("⚠️  NMS return_idxs gagal (%s); memakai pencocokan cadangan" % e)
                    self._peringatan_nms = True
        # cadangan: cocokkan lewat skor kelas
        skor = y[0, 4:].float().cpu().numpy()          # (nc, N)
        xywh = y[0, :4].float().cpu().numpy()          # letterbox
        hasil = []
        for i in range(n):
            kand = np.where(np.abs(skor[cls_u[i]] - conf_u[i]) < 1e-6)[0]
            if len(kand) == 0:
                return None
            if len(kand) > 1:
                # pilih yang ukuran kotaknya paling mirip (rasio w/h tidak berubah oleh letterbox)
                w_u = box_u[i, 2] - box_u[i, 0]
                h_u = box_u[i, 3] - box_u[i, 1]
                r_u = w_u / max(h_u, 1e-6)
                r_k = xywh[2, kand] / np.maximum(xywh[3, kand], 1e-6)
                kand = kand[[int(np.argmin(np.abs(r_k - r_u)))]]
            hasil.append(int(kand[0]))
        return np.array(hasil, int)
