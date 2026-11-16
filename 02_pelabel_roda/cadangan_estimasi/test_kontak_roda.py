"""
Uji unit pelabel kontak roda–lubang.  Jalankan:  python -m pytest -q test_kontak_roda.py

Setiap uji memakai kasus yang jawabannya bisa dihitung dengan tangan. Geometri
memakai estimasi Microlino (lebar jejak 1,20 m, setengah lebar ban 0,075 m),
sehingga roda terdekat menyentuh lubang ber-setengah-lebar 1,5 m selama
|offset lateral| < 1,5 + 0,6 + 0,075 = 2,175 m.
"""
import numpy as np
import pytest

from kontak_roda import (DT, GeometriKendaraan, Lubang, energi_pelanggaran, jarak_bertanda, kontak_per_langkah,
                         label_horizon, logika_dika, rollout_sepeda, roda_dunia)

GEO = GeometriKendaraan()
LUB_DIKA = dict(ex=1.0, ey=1.5)          # ukuran lubang di pothole_gt.json Dika


def lintasan_lurus(y, kmh, x0=-20.0, x1=20.0):
    v = kmh / 3.6
    xs = np.arange(x0, x1, v * DT)
    return xs, np.full_like(xs, y), np.zeros_like(xs)


# --------------------------------------------------------------- geometri dasar
def test_jarak_bertanda_luar_dalam_tepi():
    l = Lubang("p", 0, 0, 1.0, 0.5)
    assert jarak_bertanda(0, 0, l) == pytest.approx(-0.5)       # pusat: 0,5 m ke tepi terdekat (sisi y)
    assert jarak_bertanda(1.0, 0, l) == pytest.approx(0.0)      # tepat di tepi
    assert jarak_bertanda(2.0, 0, l) == pytest.approx(1.0)
    assert jarak_bertanda(2.0, 1.5, l) == pytest.approx(np.hypot(1, 1))   # dekat sudut


def test_jarak_bertanda_lubang_berotasi():
    l = Lubang("p", 0, 0, 1.0, 0.25, yaw=90)                   # panjang 2 m kini melintang (searah y)
    assert jarak_bertanda(0, 0.9, l) < 0                       # masih di dalam
    assert jarak_bertanda(0.9, 0, l) > 0                       # di luar sisi sempit


def test_posisi_roda_yaw_0_dan_90():
    w0 = roda_dunia(0, 0, 0, GEO)[0]
    assert w0[0] == pytest.approx([0.75, -0.6])                # depan-kiri: x maju, y negatif = kiri
    w90 = roda_dunia(0, 0, 90, GEO)[0]
    assert w90[0] == pytest.approx([0.6, 0.75], abs=1e-9)      # setelah putar 90°, kiri = +x


# --------------------------------------------------------------- kasus kunci
def test_lewat_tepat_di_tengah_kena_di_kedua_metode():
    l = Lubang("p", 0, 0, **LUB_DIKA)
    xs, ys, yw = lintasan_lurus(0.0, 7)
    k = kontak_per_langkah(xs, ys, yw, [l], GEO)
    assert k["kontak"].any()
    assert len(logika_dika(xs, ys, yw, [l]).hit) == 1


def test_offset_1_9m_bug_ambang_lateral_dika():
    """Pusat mobil 1,9 m dari pusat lubang. Roda kiri di 1,3 m < 1,5 m -> roda masuk lubang.
    Dika: 1,9 > extent_x(1,0) + 0,74 + 0,10 = 1,84 -> dicatat TERHINDAR."""
    l = Lubang("p", 0, 0, **LUB_DIKA)
    xs, ys, yw = lintasan_lurus(1.9, 7)
    k = kontak_per_langkah(xs, ys, yw, [l], GEO)
    d = logika_dika(xs, ys, yw, [l])
    assert k["kontak"].any()
    assert d.hit == [] and len(d.avoid) == 1
    roda = k["kejadian"][0]["roda"]
    assert set(roda) == {"DKi", "BKi"}                         # hanya ban kiri yang masuk


def test_offset_2_3m_aman_di_kedua_metode():
    l = Lubang("p", 0, 0, **LUB_DIKA)
    xs, ys, yw = lintasan_lurus(2.3, 7)
    assert not kontak_per_langkah(xs, ys, yw, [l], GEO)["kontak"].any()
    assert logika_dika(xs, ys, yw, [l]).hit == []


def test_mengangkangi_lubang_sempit_dika_hit_padahal_ban_tidak_kena():
    """Lubang Medium sempit (setengah lebar 0,3 m) tepat di tengah. Ban ada di ±0,6 m,
    tepi dalam ban di ±0,525 m -> tidak ada ban yang masuk. Dika: lateral 0 -> HIT."""
    l = Lubang("p", 0, 0, ex=0.5, ey=0.3, severity="Medium")
    xs, ys, yw = lintasan_lurus(0.0, 7)
    assert not kontak_per_langkah(xs, ys, yw, [l], GEO)["kontak"].any()
    assert len(logika_dika(xs, ys, yw, [l]).hit) == 1


def test_cooldown_dika_menelan_lubang_kedua_pada_kecepatan_tinggi():
    """Dua lubang selajur berjarak 4 m, 25 km/jam -> 0,35 m/langkah -> ~12 langkah < cooldown 100.
    Ban mengenai keduanya; Dika mencatat 1 HIT + 1 TERHINDAR."""
    L = [Lubang("p1", 0, 0, **LUB_DIKA), Lubang("p2", 4, 0, **LUB_DIKA)]
    xs, ys, yw = lintasan_lurus(0.0, 25)
    k = kontak_per_langkah(xs, ys, yw, L, GEO)
    d = logika_dika(xs, ys, yw, L)
    assert {e["lubang"] for e in k["kejadian"]} == {"p1", "p2"}
    assert [h[1] for h in d.hit] == ["p1"] and [a[1] for a in d.avoid] == ["p2"]


def test_cooldown_tidak_berpengaruh_pada_setup_dika_7kmh_13m():
    L = [Lubang("p1", 0, 0, **LUB_DIKA), Lubang("p2", 13, 0, **LUB_DIKA)]
    xs, ys, yw = lintasan_lurus(0.0, 7, x1=30)
    assert len(logika_dika(xs, ys, yw, L).hit) == 2


def test_severity_low_diabaikan():
    l = Lubang("p", 0, 0, **LUB_DIKA, severity="Low")
    xs, ys, yw = lintasan_lurus(0.0, 7)
    assert not kontak_per_langkah(xs, ys, yw, [l], GEO)["kontak"].any()


# --------------------------------------------------------------- label & energi
def test_label_horizon_tepat_H_langkah_sebelum_kontak():
    k = np.zeros(100, bool); k[60:65] = True
    y = label_horizon(k, H=40)
    assert y[19] == False and y[20] == True                    # 20+40 = 60
    assert y[63] == True and y[64] == False                    # langkah 64 tidak punya kontak di 65..


def test_energi_nol_jika_jauh_dan_naik_jika_masuk():
    l = Lubang("p", 5, 0, **LUB_DIKA)
    jauh = energi_pelanggaran(*lintasan_lurus(4.0, 7, x0=0, x1=10), [l], GEO)
    serempet = energi_pelanggaran(*lintasan_lurus(2.1, 7, x0=0, x1=10), [l], GEO)
    tengah = energi_pelanggaran(*lintasan_lurus(0.0, 7, x0=0, x1=10), [l], GEO)
    assert jauh == 0.0 and 0 < serempet < tengah


def test_energi_konsisten_dengan_label_kontak():
    l = Lubang("p", 5, 0, **LUB_DIKA)
    for off in np.linspace(0, 3, 31):
        tr = lintasan_lurus(off, 7, x0=0, x1=10)
        assert (energi_pelanggaran(*tr, [l], GEO) > 0) == kontak_per_langkah(*tr, [l], GEO)["kontak"].any()


def test_rollout_sepeda_lurus_dan_belok():
    xs, ys, ps = rollout_sepeda(0, 0, 0, 2.0, 0.0, GEO, H=40)
    assert xs[-1] == pytest.approx(4.0) and abs(ys[-1]) < 1e-9
    _, ys_k, _ = rollout_sepeda(0, 0, 0, 2.0, 15.0, GEO, H=40)
    _, ys_ki, _ = rollout_sepeda(0, 0, 0, 2.0, -15.0, GEO, H=40)
    assert ys_k[-1] > 0 > ys_ki[-1]                            # setir positif = ke kanan (+y)
