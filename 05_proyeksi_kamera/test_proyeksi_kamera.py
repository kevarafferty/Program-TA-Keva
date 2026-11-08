"""Uji unit proyeksi kamera.  Jalankan:  python -m pytest -q test_proyeksi_kamera.py"""
import numpy as np
import pytest

from proyeksi_kamera import (KAMERA_DIKA, KAMERA_RETTA, Kamera, baris_horizon, kotak_2d_lubang, piksel_ke_jalan,
                             proyeksikan)

POSE0 = (0.0, 0.0, 0.0, 0.0)     # kendaraan di titik asal, menghadap +x


def test_panjang_fokus_fov90():
    assert KAMERA_DIKA.f == pytest.approx(320.0)
    assert KAMERA_RETTA.f == pytest.approx(640.0)


def test_titik_di_sumbu_optik_jatuh_di_pusat_citra():
    k = KAMERA_DIKA
    arah = np.array([np.cos(np.radians(15)), 0, -np.sin(np.radians(15))])
    p = np.array([k.x, 0, k.z]) + 10 * arah
    uv, z, ok = proyeksikan(k, POSE0, p[None])
    assert ok[0] and uv[0] == pytest.approx([320, 320], abs=1e-6)


def test_horizon_dan_titik_jalan_lurus_ke_depan():
    k = KAMERA_DIKA
    assert baris_horizon(k) == pytest.approx(320 - 320 * np.tan(np.radians(15)))   # 234,3 px
    d = 8.0                                                                   # meter di depan kamera
    uv, _, _ = proyeksikan(k, POSE0, np.array([[k.x + d, 0, 0]]))
    alpha = np.arctan2(k.z, d)
    assert uv[0, 0] == pytest.approx(320)
    assert uv[0, 1] == pytest.approx(320 + 320 * np.tan(alpha - np.radians(15)))


def test_titik_kanan_jatuh_di_kanan_citra():
    uv, _, _ = proyeksikan(KAMERA_DIKA, POSE0, np.array([[10, 2, 0]]))
    assert uv[0, 0] > 320


def test_invers_jalan_bolak_balik():
    k = KAMERA_DIKA
    for maju, kanan in [(5, 0), (12, -1.5), (25, 3.0)]:
        uv, _, _ = proyeksikan(k, POSE0, np.array([[maju, kanan, 0]]))
        m2, k2 = piksel_ke_jalan(k, *uv[0])
        assert (m2, k2) == pytest.approx((maju, kanan), abs=1e-6)


def test_di_atas_horizon_tidak_punya_titik_jalan():
    assert piksel_ke_jalan(KAMERA_DIKA, 320, 100) is None


def test_pose_kendaraan_ikut_diperhitungkan():
    lub = dict(x=10.0, y=0.0, extent_x=1.0, extent_y=1.5, yaw=0)
    a = kotak_2d_lubang(KAMERA_DIKA, (0, 0, 0, 0), lub)
    b = kotak_2d_lubang(KAMERA_DIKA, (0, 0, 0, 90), lub)       # mobil menoleh 90°: lubang di kiri, di luar FOV
    c = kotak_2d_lubang(KAMERA_DIKA, (5, 0, 0, 0), lub)        # mobil maju 5 m: kotak membesar
    assert a is not None and b is None
    assert (c[2] - c[0]) > (a[2] - a[0])


def test_lubang_di_belakang_tidak_terlihat():
    assert kotak_2d_lubang(KAMERA_DIKA, POSE0, dict(x=-5.0, y=0.0, extent_x=1, extent_y=1.5)) is None
