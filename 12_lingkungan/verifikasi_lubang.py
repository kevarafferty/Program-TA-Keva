"""
verifikasi_lubang.py — Pastikan lubang tata letak episode BENAR-BENAR tampak sebelum episode dimulai.

Latar (LOG 22 Nov): pada matriks malam 21–22 Nov ±40% episode berjalan dengan lubang tak tampak
(toggle grid mati-lalu-nyala dalam satu saat kadang berakhir 'mati'). Deteksi YOLO jatuh ke 0–9% langkah,
agen buta, dan ringkasan tidak memberi tanda apa pun. Modul ini menutup celah itu.

Cara: kamera RGB berparameter kamera Dika (640x640, FOV 90, z 2 m, pitch -15) diletakkan 8 m di belakang
beberapa lubang aktif (pertama, tengah, terakhir) di lajurnya, cuaca sementara ClearNoon, lalu YOLO
(imgsz 320, conf 0,05 — sama dengan agen) harus menemukan kotak di area tengah citra. Tidak tampak =
toggle diulang (mati, tick, nyala, tick) lalu dicek lagi.
"""
from __future__ import annotations

import time

import numpy as np

JARAK_M = (8.0, 6.0)          # coba dua jarak sebelum menyatakan tak tampak
AREA_CX = (0.25, 0.75)        # pusat kotak harus di area tengah (lubang tepat di depan kamera)
AREA_CY = (0.35, 0.90)


class PemeriksaLubang:
    def __init__(self, world, carla_mod, yolo, device="cpu"):
        self.world, self.carla, self.yolo, self.device = world, carla_mod, yolo, device
        bp = world.get_blueprint_library().find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", "640")
        bp.set_attribute("image_size_y", "640")
        bp.set_attribute("fov", "90")
        self.bp = bp
        self.cam = None
        self._buf = {}

    def _pasang(self, tf):
        C = self.carla
        if self.cam is None:
            self.cam = self.world.spawn_actor(self.bp, tf)
            self.cam.listen(lambda im: self._buf.__setitem__(
                im.frame, np.frombuffer(im.raw_data, np.uint8).reshape(im.height, im.width, 4)[:, :, :3].copy()))
        else:
            self.cam.set_transform(tf)

    def _ambil(self, n_tick=3):
        f = None
        for _ in range(n_tick):
            f = self.world.tick()
        t0 = time.time()
        while f not in self._buf and time.time() - t0 < 3.0:
            time.sleep(0.002)
        im = self._buf.get(f)
        self._buf.clear()
        return im

    def cek_satu(self, lub: dict) -> dict:
        C = self.carla
        terbaik = dict(id=lub["id"], tampak=False, conf=0.0, jarak=None)
        for d in JARAK_M:
            tf = C.Transform(C.Location(x=lub["x"] - d, y=lub["y"], z=2.0), C.Rotation(pitch=-15.0))
            self._pasang(tf)
            im = self._ambil()
            if im is None:
                continue
            r = self.yolo(im, imgsz=320, conf=0.05, verbose=False, device=self.device)[0]
            if len(r.boxes):
                xyxy = r.boxes.xyxy.cpu().numpy()
                conf = r.boxes.conf.cpu().numpy()
                h, w = im.shape[:2]
                cx = (xyxy[:, 0] + xyxy[:, 2]) / 2 / w
                cy = (xyxy[:, 1] + xyxy[:, 3]) / 2 / h
                ok = (cx > AREA_CX[0]) & (cx < AREA_CX[1]) & (cy > AREA_CY[0]) & (cy < AREA_CY[1])
                if ok.any():
                    c = float(conf[ok].max())
                    if c > terbaik["conf"]:
                        terbaik.update(tampak=True, conf=round(c, 4), jarak=d)
                    break
        return terbaik

    def pilih(self, lubang: list, n: int = 3) -> list:
        ls = sorted(lubang, key=lambda l: l["x"])
        idx = sorted({0, len(ls) // 2, len(ls) - 1}) if n >= 3 else [0]
        return [ls[i] for i in idx if i < len(ls)]

    def tutup(self):
        if self.cam is not None:
            try:
                self.cam.stop()
                self.cam.destroy()
            except Exception:
                pass
            self.cam = None
