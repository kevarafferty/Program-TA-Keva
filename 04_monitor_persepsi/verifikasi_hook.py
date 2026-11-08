"""Jalankan hook pada semua citra x semua gangguan dan bandingkan dengan predict()."""
import argparse, glob, json, os
import cv2, numpy as np
from yolo_logit_hook import YoloDenganLogit
from prototipe_monitor_persepsi import ganggu, TINGKAT, SEED

ap = argparse.ArgumentParser(); ap.add_argument("--bobot", required=True); ap.add_argument("--citra", required=True)
ap.add_argument("--out", default="hasil/verifikasi_hook.json"); a = ap.parse_args()
y = YoloDenganLogit(a.bobot)
kondisi = [("bersih", 0, None)] + [(j, t + 1, p) for j, ps in TINGKAT.items() for t, p in enumerate(ps)]
n, gagal, dc, db, nbox = 0, [], 0.0, 0.0, 0
for i, f in enumerate(sorted(glob.glob(os.path.join(a.citra, "*.jpg")))):
    img0 = cv2.imread(f)
    for j, lvl, p in kondisi:
        img = img0 if p is None else ganggu(img0, j, p, np.random.default_rng(SEED * 1000 + i * 17 + lvl))
        v = y.verifikasi(y.infer(img)); n += 1
        if not v["ok"]: gagal.append((os.path.basename(f), j, lvl, v))
        else:
            dc = max(dc, v.get("maks_selisih_conf", 0)); db = max(db, v.get("maks_selisih_kotak_px", 0)); nbox += v["n"]
r = dict(inferensi=n, kotak=nbox, tidak_cocok=len(gagal), contoh_tidak_cocok=gagal[:5],
         maks_selisih_conf=dc, maks_selisih_kotak_px=db)
json.dump(r, open(a.out, "w"), indent=1); print(r)
