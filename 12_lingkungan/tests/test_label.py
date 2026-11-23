"""Uji pelabel kegagalan dengan lintasan dan deteksi sintetis.  python -m pytest -q tests/test_label.py"""
import os
import sys

import numpy as np

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DIR)
from label_kegagalan import FRAKSI_MIN, label_lintasan, ringkas_episode  # noqa: E402
from proyeksi_kamera import KAMERA_DIKA, kotak_2d_lubang  # noqa: E402

GT = [dict(id="a", x=-260.0, y=250.5, z=0.039, yaw=0.0, extent_x=1.0, extent_y=1.5, severity_label="High"),
      dict(id="b", x=-230.0, y=247.2, z=0.039, yaw=0.0, extent_x=1.0, extent_y=1.5, severity_label="High"),
      dict(id="c", x=-150.0, y=250.5, z=0.039, yaw=0.0, extent_x=1.0, extent_y=1.5, severity_label="High")]


def lintasan_lurus(y=250.5, x0=-290.0, x1=-200.0, v_kmh=7.2):
    x = np.arange(x0, x1, v_kmh / 3.6 * 0.05)
    return x, np.full_like(x, y), np.zeros_like(x)


def det_sempurna(x, y, yaw, gt, hilangkan=()):
    """Deteksi = kotak proyeksi lubang terdekat 3-15 m, kecuali lubang di 'hilangkan'."""
    st, bx, cf = [], [], []
    for t in range(len(x)):
        best = None
        for g in gt:
            m = g["x"] - x[t]
            if 3 <= m <= 15 and g["id"] not in hilangkan:
                kb = kotak_2d_lubang(KAMERA_DIKA, (x[t], y[t], 0.0, yaw[t]), g, z_jalan=g["z"])
                if kb is not None and (best is None or m < best[0]):
                    best = (m, kb)
        if best is not None:
            st.append(t + 1); bx.append(best[1]); cf.append(0.8)
    return dict(det_step=np.array(st, int), det_box=np.array(bx, float).reshape(-1, 4), det_conf=np.array(cf, float))


def test_kontak_di_lajur_lubang_dan_status():
    x, y, yaw = lintasan_lurus()
    lg, lt = label_lintasan(x, y, yaw, GT)
    s = {b["id"]: b["status"] for b in lt}
    assert s == dict(a="kontak", b="terhindar", c="tak_tercapai")
    assert lg["kontak"].any() and lg["kontak_H"].sum() > lg["kontak"].sum()     # label H mendahului kontak
    i0 = int(np.argmax(lg["kontak"]))
    assert lg["kontak_H"][max(0, i0 - 40):i0].all()


def test_persepsi_sempurna_vs_lubang_terlewat():
    x, y, yaw = lintasan_lurus()
    lg, lt = label_lintasan(x, y, yaw, GT, det=det_sempurna(x, y, yaw, GT))
    b = {q["id"]: q for q in lt}
    assert b["a"]["gagal_persepsi"] == 0 and b["b"]["gagal_persepsi"] == 0
    assert (lg["gagal_persepsi"][lg["gagal_persepsi"] >= 0] == 0).all()
    lg2, lt2 = label_lintasan(x, y, yaw, GT, det=det_sempurna(x, y, yaw, GT, hilangkan=("b",)))
    b2 = {q["id"]: q for q in lt2}
    assert b2["a"]["gagal_persepsi"] == 0 and b2["b"]["gagal_persepsi"] == 1 and b2["b"]["frac_cocok"] < FRAKSI_MIN
    assert b["a"]["terlambat"] == 0 and b2["b"]["terlambat"] == 1
    assert b2["c"].get("gagal_persepsi", -1) == -1                 # tidak pernah dalam jangkauan


def test_tanpa_deteksi_semua_gagal_dan_ringkasan():
    x, y, yaw = lintasan_lurus()
    lg, lt = label_lintasan(x, y, yaw, GT, det=dict(det_step=np.zeros(0, int), det_box=np.zeros((0, 4)), det_conf=np.zeros(0)))
    assert (lg["gagal_persepsi"][lg["gagal_persepsi"] >= 0] == 1).all()
    r = ringkas_episode(dict(langkah=lg, lintasan=lt), dict(avoids="2", akhir="finis"))
    assert r["n_kontak"] == 1 and r["n_tak_tercapai"] == 1
    assert abs(r["roda_tak_tercapai_gagal"] - 100 / 3) < 1e-9 and abs(r["roda_hanya_dilewati"] - 50) < 1e-9
    assert abs(r["roda_cara_lama"] - 200 / 3) < 1e-9 and r["gagal_persepsi_lintasan"] == 100.0


def test_deteksi_palsu_ditandai():
    x, y, yaw = lintasan_lurus(x0=-200, x1=-180)           # tidak ada lubang di depan (c di -150, > 30 m)
    det = dict(det_step=np.arange(1, len(x) + 1), det_box=np.tile([300, 400, 340, 420], (len(x), 1)).astype(float),
               det_conf=np.full(len(x), 0.3))
    lg, _ = label_lintasan(x, y, yaw, GT, det=det)
    assert lg["palsu_top"][:5].all() and (lg["target"] < 0).all()


def test_deteksi_hanya_dekat_terlambat_dan_gagal():
    """Lubang baru cocok saat < 6 m (seperti malam): terlambat = 1 dan fraksi cocok rendah."""
    x, y, yaw = lintasan_lurus()
    d = det_sempurna(x, y, yaw, GT)
    # buang deteksi lubang b saat masih > 6 m
    keep = []
    for i, s in enumerate(d["det_step"]):
        m_b = GT[1]["x"] - x[s - 1]
        m_a = GT[0]["x"] - x[s - 1]
        target_b = (3 <= m_b <= 15) and not (3 <= m_a <= 15 and m_a < m_b)
        keep.append(not (target_b and m_b > 6.0))
    keep = np.array(keep)
    d2 = {k: v[keep] for k, v in d.items()}
    _, lt = label_lintasan(x, y, yaw, GT, det=d2)
    b = {q["id"]: q for q in lt}
    assert b["b"]["terlambat"] == 1 and b["b"]["gagal_persepsi"] == 1 and b["a"]["terlambat"] == 0
