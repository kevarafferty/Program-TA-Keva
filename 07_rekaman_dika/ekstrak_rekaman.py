"""
ekstrak_rekaman.py — Mengubah rekaman uji Dika (recordings/cerah.mp4, hujan.mp4, malam.mp4)
menjadi data per frame untuk mengevaluasi monitor persepsi pada frame CARLA ASLI.

Rekaman dibuat oleh cleanTest.py Dika: satu frame per langkah simulasi (20 fps, 640x640),
berisi citra kamera agen + overlay. Skrip ini:

  1. Memulihkan citra yang dilihat YOLO agen:
       - cleanTest.py menulis cv2.cvtColor(current_image, RGB2BGR). current_image sebenarnya
         sudah BGR (raw CARLA), sehingga kanal di video TERTUKAR. Dibalik dengan menukar kanal lagi.
       - Panel kiri (x 0..300) digelapkan 50% (addWeighted 0.5). Dibalik dengan mengalikan 2.
       - Teks overlay dan kotak deteksi yang digambar TIDAK bisa dihapus. Ini dicatat sebagai
         kontaminasi dan diukur dampaknya (kesepakatan deteksi ulang vs deteksi agen).
  2. Membaca dari overlay:
       - status deteksi YOLO agen per frame (baris "Severity" hanya ada jika terdeteksi)
         -> tervalidasi 100% sama dengan kolom pothole_detected di CSV malam dan hujan
       - (kolom ganti_hits / ganti_avoids di .npz TIDAK dipakai: metode kecerahannya keliru.
          Pakai baca_penghitung.py yang membaca warna teks.)
  3. Menjalankan ulang YOLO (best_pure.pt = best.pt, imgsz 320, conf 0.05) dengan hook logit
     dan fitur neck pada citra yang dipulihkan.

Keluaran: <out>/<kondisi>.npz berisi array per frame.

Cara pakai:
  python ekstrak_rekaman.py --video recordings/malam.mp4 --kondisi malam --bobot Yolo/best_pure.pt --out data
"""
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "04_monitor_persepsi"))
from yolo_logit_hook import YoloDenganLogit, joint_energy  # noqa: E402

# posisi baris teks overlay (y_pos mulai 25, naik 23 per baris; lihat draw_overlay di cleanTest.py)
BARIS_SEVERITY = (266, 284)
BARIS_HITS = (473, 491)
BARIS_AVOIDS = (496, 514)
KOLOM_ANGKA = (80, 170)


def pulihkan(frame_video: np.ndarray) -> np.ndarray:
    f = frame_video[:, :, ::-1].astype(np.float32)          # tukar kanal kembali
    f[:, :301] = f[:, :301] * 2.0                            # batalkan penggelapan panel kiri
    return np.clip(f, 0, 255).astype(np.uint8)


def flag_deteksi_agen(frame_video: np.ndarray) -> int:
    band = frame_video[BARIS_SEVERITY[0]:BARIS_SEVERITY[1], 10:250].astype(int)
    return int((band.max(axis=2) > 150).sum() > 40)


def pita_angka(frame_video, baris):
    b = frame_video[baris[0]:baris[1], KOLOM_ANGKA[0]:KOLOM_ANGKA[1]].max(axis=2)
    return (b > 120).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--kondisi", required=True)
    ap.add_argument("--bobot", required=True)
    ap.add_argument("--out", default="data")
    ap.add_argument("--tiap", type=int, default=1, help="proses tiap n frame untuk YOLO (1 = semua)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    yolo = YoloDenganLogit(a.bobot)
    cap = cv2.VideoCapture(a.video)
    rec = dict(det_agen=[], ganti_hits=[], ganti_avoids=[], n_det=[], conf_top=[], kelas_top=[],
               logit_top=[], je_citra=[], terang=[], kontras=[], fitur=[], diproses=[])
    prev_h = prev_a = None
    i = 0
    while True:
        ok, fv = cap.read()
        if not ok:
            break
        rec["det_agen"].append(flag_deteksi_agen(fv))
        ph, pa = pita_angka(fv, BARIS_HITS), pita_angka(fv, BARIS_AVOIDS)
        rec["ganti_hits"].append(0 if prev_h is None else int((ph != prev_h).sum() > 12))
        rec["ganti_avoids"].append(0 if prev_a is None else int((pa != prev_a).sum() > 12))
        prev_h, prev_a = ph, pa

        proses = (i % a.tiap == 0)
        rec["diproses"].append(int(proses))
        if proses:
            img = pulihkan(fv)
            h = yolo.infer(img)
            n = len(h["conf"])
            if n:
                k = int(np.argmax(h["conf"]))
                lg, ct, kt = h["logit"][k], float(h["conf"][k]), int(h["cls"][k])
            else:
                la = h["logit_semua"]
                lg, ct, kt = la[:, int(la.max(axis=0).argmax())], 0.0, -1
            g = cv2.cvtColor(img[:, 301:], cv2.COLOR_BGR2GRAY).astype(np.float32)   # statistik hanya dari area tanpa panel
            rec["n_det"].append(n); rec["conf_top"].append(ct); rec["kelas_top"].append(kt)
            rec["logit_top"].append(lg); rec["je_citra"].append(float(joint_energy(h["logit_semua"].T).mean()))
            rec["terang"].append(float(g.mean())); rec["kontras"].append(float(g.std()))
            rec["fitur"].append(h["fitur"].astype(np.float32))
        else:
            for kk, v in [("n_det", -1), ("conf_top", np.nan), ("kelas_top", -2), ("je_citra", np.nan),
                          ("terang", np.nan), ("kontras", np.nan)]:
                rec[kk].append(v)
            rec["logit_top"].append(np.full(3, np.nan, np.float32))
            rec["fitur"].append(np.full(896, np.nan, np.float32))
        i += 1
        if i % 500 == 0:
            print(a.kondisi, i, flush=True)

    out = {k: np.array(v) for k, v in rec.items()}
    np.savez_compressed(os.path.join(a.out, f"{a.kondisi}.npz"), **out)
    print(a.kondisi, "selesai", i, "frame; deteksi agen", out["det_agen"].mean().round(3),
          "; ganti hits", out["ganti_hits"].sum(), "; ganti avoids", out["ganti_avoids"].sum())


if __name__ == "__main__":
    main()
