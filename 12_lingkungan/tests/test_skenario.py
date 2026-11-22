"""Uji katalog skenario, transisi, korupsi (tanpa CARLA).  python -m pytest -q tests/test_skenario.py"""
import os
import random
import sys

import numpy as np
import pytest

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DIR)
sys.path.insert(0, os.path.join(DIR, "tests"))
import carla_palsu as cp  # noqa: E402
from generator_tata_letak import buat_tata_letak, muat_slot_grid  # noqa: E402
from skenario import (KATALOG, PARAM_CUACA, Korupsi, cuaca_angka, daftar_kondisi, faktor_transisi,  # noqa: E402
                      interpolasi_cuaca, resolusi, throttle_untuk)

PRESET = {n: {k: getattr(getattr(cp.WeatherParameters, n), k) for k in PARAM_CUACA}
          for n in ["ClearNoon", "CloudyNoon", "HardRainNoon", "ClearNight"]}
KAL = dict(throttle_ke_kmh={"0.30": 7.0, "0.50": 15.0, "0.70": 24.0, "0.90": 33.0}, azimut_menghadap_kamera=180.0,
           throttle_ke_kmh_per_kendaraan={k: {"0.10": 3.0, "0.20": 9.0, "0.30": 18.0} for k in
                                          ("vehicle.nissan.micra", "vehicle.citroen.c3", "vehicle.tesla.model3")})
SLOT = muat_slot_grid()


def test_faktor_transisi():
    tr = dict(x_onset=-200.0, jarak_rampa_m=20.0)
    assert faktor_transisi(-250, tr) == 0.0
    assert faktor_transisi(-190, tr) == pytest.approx(0.5)
    assert faktor_transisi(-150, tr) == 1.0
    assert faktor_transisi(-201, dict(x_onset=-200.0, jarak_rampa_m=0)) == 0.0
    assert faktor_transisi(-200, dict(x_onset=-200.0, jarak_rampa_m=0)) == 1.0
    assert faktor_transisi(-999, None) == 1.0


def test_interpolasi_azimut_jalur_terpendek():
    a = dict(sun_azimuth_angle=350.0, fog_density=0.0)
    b = dict(sun_azimuth_angle=10.0, fog_density=80.0)
    m = interpolasi_cuaca(a, b, 0.5)
    assert m["sun_azimuth_angle"] == pytest.approx(0.0) and m["fog_density"] == pytest.approx(40.0)


@pytest.mark.parametrize("kode,t", daftar_kondisi())
def test_semua_kondisi_konstan_bisa_diresolusi(kode, t):
    be = "spawn" if KATALOG[kode]["tingkat"][t].get("backend_wajib") == "spawn" else "grid"
    sp = resolusi(kode, t, 4, "konstan", be)
    cuaca_angka(sp["cuaca_target"], PRESET, KAL)
    throttle_untuk(sp.get("kecepatan"), KAL, sp.get("kendaraan"))
    tl = buat_tata_letak(4, sp["konfig_tata_letak"], be, SLOT)
    assert tl.n > 0


def test_A2_t3_sama_dengan_HardRainNoon():
    sp = resolusi("A2", 3, 0)
    assert cuaca_angka(sp["cuaca_target"], PRESET) == pytest.approx(PRESET["HardRainNoon"])


def test_A4_tanpa_kalibrasi_ditolak():
    sp = resolusi("A4", 1, 0)
    with pytest.raises(RuntimeError):
        cuaca_angka(sp["cuaca_target"], PRESET, {})
    assert cuaca_angka(sp["cuaca_target"], PRESET, KAL)["sun_azimuth_angle"] == 180.0


def test_C2_tanpa_kalibrasi_ditolak_dan_interpolasi():
    with pytest.raises(RuntimeError):
        throttle_untuk(dict(target_kmh=20), {})
    assert throttle_untuk(dict(target_kmh=11.0), KAL) == pytest.approx(0.40)
    assert throttle_untuk(None, {}) == 0.3


def test_desain_berpasangan_tata_letak_dan_offset_sama_antar_skenario():
    for s in range(5):
        a = resolusi("ID0", 1, s)
        for kode in ("A1", "A3", "A5", "C2"):
            b = resolusi(kode, 2, s)
            ta = buat_tata_letak(s, a["konfig_tata_letak"], "grid", SLOT)
            tb = buat_tata_letak(s, b["konfig_tata_letak"], "grid", SLOT)
            assert ta.sidik() == tb.sidik()
            assert a["spawn"]["offset_x_aktual"] == b["spawn"]["offset_x_aktual"]


def test_offset_ID0_sama_dengan_rumus_dika():
    for s in range(10):
        r = random.Random(s)
        ox, oy = r.uniform(-2.0, 2.0), r.uniform(-0.5, 0.5)
        sp = resolusi("ID0", 1, s)["spawn"]
        assert (sp["offset_x_aktual"], sp["offset_y_aktual"]) == (ox, oy)


def test_C3_selalu_di_luar_rentang_ID0():
    for s in range(30):
        sp = resolusi("C3", 1, s)["spawn"]
        assert 0.5 <= abs(sp["offset_y_aktual"]) <= 0.9 and 1.0 <= abs(sp["heading_deg_aktual"]) <= 4.0


def test_transisi_onset_di_tengah_ruas_dan_cuaca_awal_nominal():
    for s in range(30):
        sp = resolusi("A3", 2, s, "transisi")
        k = sp["konfig_tata_letak"]
        L = k.x_selesai - k.x_mulai
        assert k.x_mulai + 0.30 * L <= sp["transisi"]["x_onset"] <= k.x_mulai + 0.55 * L
        assert sp["cuaca_awal"]["basis"] in ("ClearNoon", "CloudyNoon") and "ubah" not in sp["cuaca_awal"]


def test_mode_transisi_ditolak_untuk_konfigurasi_dan_backend_wajib():
    with pytest.raises(ValueError):
        resolusi("C2", 1, 0, "transisi")
    with pytest.raises(ValueError):
        resolusi("C1", 2, 0, "konstan", "grid")
    with pytest.raises(NotImplementedError):
        resolusi("B1", 1, 0)


def test_E1_gabungan_malam_hujan():
    sp = resolusi("E1", 2, 0)
    w = cuaca_angka(sp["cuaca_target"], PRESET)
    assert w["sun_altitude_angle"] == -60.0 and w["precipitation"] == pytest.approx(80.0) and sp["lampu"] == "LowBeam"


def test_korupsi_deterministik_dan_f0_identitas():
    img = (np.random.default_rng(0).integers(0, 255, (640, 640, 3))).astype(np.uint8)
    k = Korupsi(dict(blur_sigma=3.0, tetes_n=10, derau_sigma=16.0, jpeg_q=15), seed=42)
    assert k.terapkan(img, 0.0, 5) is img
    a = k.terapkan(img, 1.0, 5)
    b = Korupsi(dict(blur_sigma=3.0, tetes_n=10, derau_sigma=16.0, jpeg_q=15), seed=42).terapkan(img, 1.0, 5)
    assert np.array_equal(a, b) and a.shape == img.shape and a.dtype == np.uint8
    assert not np.array_equal(a, k.terapkan(img, 1.0, 6))          # derau berubah per langkah
    assert np.abs(a.astype(int) - img).mean() > np.abs(k.terapkan(img, 0.3, 5).astype(int) - img).mean()


def test_C4_kecepatan_disamakan_dengan_microlino():
    sp = resolusi("C4", 3, 0)
    thr = throttle_untuk(sp["kecepatan"], KAL, sp["kendaraan"])
    # Microlino throttle 0,3 -> 7,0 km/jam; Tesla tiruan 7,0 km/jam di throttle 0,1 + (7-3)/(9-3)*0,1
    assert thr == pytest.approx(0.1 + 4.0 / 6.0 * 0.1)
    with pytest.raises(RuntimeError):
        throttle_untuk(sp["kecepatan"], dict(throttle_ke_kmh=KAL["throttle_ke_kmh"]), sp["kendaraan"])
    assert throttle_untuk(None, {}, "vehicle.tesla.model3") == 0.3
