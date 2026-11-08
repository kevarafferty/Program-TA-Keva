"""
baca_penghitung.py — Membaca perubahan penghitung Hits (teks merah) dan Avoids (teks hijau) di overlay
rekaman Dika, berdasarkan WARNA teks.

Versi pertama di ekstrak_rekaman.py membaca kecerahan, dan itu salah: panel kiri hanya digelapkan 50%,
sehingga pemandangan terang di belakang panel ikut terbaca sebagai "perubahan" (177 hit palsu di cerah).
Metode warna menemukan kejadian yang sama persis dengan CSV (contoh malam: hit 473, 597, 728; avoid 216,
363), tetapi masih ada sisa deteksi palsu. Karena itu hasilnya hanya dipakai bila CSV run yang sama tidak
ada (video cerah), dan selalu dicocokkan dengan prediksi (lihat analisis_rekaman.py).

Cara pakai:  python baca_penghitung.py --video recordings/cerah.mp4 --kondisi cerah --out data
"""
import argparse
import os

import cv2
import numpy as np


def masker(f):
    b = f[470:492, 70:150].astype(int)
    a = f[495:516, 70:150].astype(int)
    mh = (b[:, :, 2] > 150) & (b[:, :, 1] < 130) & (b[:, :, 0] < 130)   # merah
    ma = (a[:, :, 1] > 160) & (a[:, :, 2] < 140) & (a[:, :, 0] < 140)   # hijau
    return mh, ma


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--kondisi", required=True)
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    gh, ga, ph, pa = [], [], None, None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        mh, ma = masker(f)
        gh.append(0 if ph is None else int((mh != ph).sum() > 8))
        ga.append(0 if pa is None else int((ma != pa).sum() > 8))
        ph, pa = mh, ma
    np.savez_compressed(os.path.join(a.out, f"{a.kondisi}_penghitung.npz"),
                        ganti_hits_warna=np.array(gh), ganti_avoids_warna=np.array(ga))
    print(a.kondisi, "perubahan hits", int(sum(gh)), "avoids", int(sum(ga)))


if __name__ == "__main__":
    main()
