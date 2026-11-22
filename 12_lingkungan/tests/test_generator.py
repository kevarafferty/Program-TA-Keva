"""Uji generator tata letak (tanpa CARLA).  python -m pytest -q tests/test_generator.py"""
import json
import os
import random
import sys

import pytest

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DIR)
from generator_tata_letak import (RNG, KonfigTataLetak, X_FINIS_DIKA, buat_tata_letak, celah_bebas_min,  # noqa: E402
                                  muat_slot_grid, turunkan_seed)

SLOT = muat_slot_grid()
SEGMEN_DIKA = json.load(open(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_segmen_dika.json")))

# Sidik seed 0-2 (grid, KonfigTataLetak bawaan + kerapatan ID-0) dihitung di cloud Python 3.13.
# Jika uji ini gagal di laptop (Python 3.8), tata letak TIDAK reprodusibel lintas mesin -> lapor.
SIDIK_ACUAN = {0: '290ebf5c4299e6e5', 1: 'ce0cec7e71114a9f', 2: '0ef6b73b68a39735'}


def k_id0():
    return KonfigTataLetak().salin(kerapatan_per_100m=(2.0, 5.0))


def test_rng_portabel_hanya_pakai_random():
    # random.Random(seed).random() identik lintas versi Python (Mersenne Twister)
    r = random.Random(12345)
    assert abs(r.random() - 0.41661987254534116) < 1e-15
    a, b = RNG(7), RNG(7)
    assert [a.randint(0, 9) for _ in range(50)] == [b.randint(0, 9) for _ in range(50)]
    assert sorted(RNG(3).acak_urutan(range(20))) == list(range(20))


def test_seed_turunan_independen():
    assert turunkan_seed(0, "tata_letak") != turunkan_seed(0, "cuaca")
    assert turunkan_seed(0, "tata_letak") == turunkan_seed(0, "tata_letak")


@pytest.mark.parametrize("seed", range(30))
def test_grid_deterministik_dan_patuh_batas(seed):
    k = k_id0()
    a = buat_tata_letak(seed, k, "grid", SLOT)
    b = buat_tata_letak(seed, k, "grid", SLOT)
    assert a.sidik() == b.sidik()
    ids = {s["id"] for s in SLOT}
    xs = sorted(l["x"] for l in a.lubang)
    assert a.n >= k.n_min
    assert all(k.x_mulai <= x <= k.x_selesai for x in xs)
    assert all(l["slot"] in ids for l in a.lubang)
    assert all(l["severity_label"] == "High" and l["extent_y"] == 1.5 for l in a.lubang)
    assert all(b_ - a_ >= k.jarak_min_m - 1e-9 for a_, b_ in zip(xs, xs[1:]))
    assert celah_bebas_min(a.lubang) >= k.celah_min_m
    assert len({l["slot"] for l in a.lubang}) == a.n                    # tanpa duplikat


def test_seed_berbeda_menghasilkan_tata_letak_beragam():
    sidik = {buat_tata_letak(s, k_id0(), "grid", SLOT).sidik() for s in range(30)}
    assert len(sidik) >= 25


def test_pola_semua_sama_dengan_segmen_dika():
    tl = buat_tata_letak(0, KonfigTataLetak(pola="semua"), "grid", SLOT)
    assert sorted(l["id"] for l in tl.lubang) == sorted(e["id"] for e in SEGMEN_DIKA)
    for l in tl.lubang:
        e = next(e for e in SEGMEN_DIKA if e["id"] == l["id"])
        assert (l["x"], l["y"], l["extent_x"], l["extent_y"]) == (e["x"], e["y"], e["extent_x"], e["extent_y"])


def test_format_gt_cocok_dengan_PotholeGroundTruth(tmp_path):
    tl = buat_tata_letak(3, k_id0(), "grid", SLOT)
    p = tl.simpan_gt(str(tmp_path / "gt.json"))
    raw = json.load(open(p))
    wajib = ["id", "x", "y", "z", "extent_x", "extent_y", "severity"]
    assert all(all(w in e for w in wajib) for e in raw)


@pytest.mark.parametrize("pola", ["acak", "zigzag", "pasangan_rapat", "klaster"])
def test_spawn_semua_pola(pola):
    k = KonfigTataLetak(pola=pola, jarak_min_m=5.0 if pola in ("klaster", "pasangan_rapat") else 10.0,
                        jarak_min_selajur_m=7.0 if pola == "klaster" else 10.0,
                        kerapatan_per_100m=(8.0, 10.0) if pola == "klaster" else (3.0, 6.0))
    for s in range(10):
        tl = buat_tata_letak(s, k, "spawn")
        assert tl.n > 0
        assert all(k.x_mulai <= l["x"] <= k.x_selesai for l in tl.lubang)
        assert celah_bebas_min(tl.lubang) >= k.celah_min_m
        assert all(l["mesh_path"] for l in tl.lubang)
        assert tl.sidik() == buat_tata_letak(s, k, "spawn").sidik()


def test_pasangan_rapat_grid_benar_benar_rapat():
    k = KonfigTataLetak(pola="pasangan_rapat", n_pasangan_rapat=2)
    tl = buat_tata_letak(0, k, "grid", SLOT)
    xs = sorted(l["x"] for l in tl.lubang)
    assert min(b - a for a, b in zip(xs, xs[1:])) < 10.0


def test_celah_bebas_mendeteksi_jalan_tertutup():
    tutup = [dict(x=-100, y=250.5, extent_x=1.0, extent_y=1.5), dict(x=-100, y=247.2, extent_x=1.0, extent_y=1.5)]
    assert celah_bebas_min(tutup) < 1.6
    selang = [dict(x=-100, y=250.5, extent_x=1.0, extent_y=1.5), dict(x=-92, y=247.2, extent_x=1.0, extent_y=1.5)]
    assert celah_bebas_min(selang) > 3.0


def test_x_finis_bawaan_dika():
    assert KonfigTataLetak().x_finis == X_FINIS_DIKA


def test_sidik_acuan_lintas_mesin():
    k = k_id0()
    got = {s: buat_tata_letak(s, k, "grid", SLOT).sidik() for s in range(3)}
    if not SIDIK_ACUAN:
        pytest.skip("acuan belum diisi: %s" % got)
    assert got == SIDIK_ACUAN
