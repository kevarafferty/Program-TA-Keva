"""
Uji unit agen ensemble + perbaikan reward (tanpa CARLA). ±1 menit di CPU.

    python -m pytest -q tests/test_agen.py
"""
import os
import sys
import types

import numpy as np
import pytest

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DIR)
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

# torch HARUS dimuat sebelum TensorFlow (urutan yang sama dengan latih_ensemble.py dan jalankan_skenario.py).
# Di Windows, TF 2.10 (CUDA 11.2) dan torch cu118 sama-sama membawa cublas64_11.dll; kalau TF dimuat dulu,
# torch gagal dengan WinError 127 saat fixture modul_env mengimpor env_latih.
try:
    import torch  # noqa: F401
except Exception:
    pass

from agen_ensemble import AgenEnsemble, BufferBootstrap, muat_untuk_evaluasi   # noqa: E402


def _isi_bandit(ag, n=3000, reward_aksi=(1.0, 5.0, -2.0)):
    """MDP satu langkah: setiap transisi terminal, reward bergantung aksi -> Q*(s,a) = reward_aksi[a]."""
    rng = np.random.default_rng(1)
    for _ in range(n):
        s = rng.normal(size=10).astype(np.float32)
        a = int(rng.integers(3))
        ag.buffer.tambah(s, a, reward_aksi[a], s, True)


def test_bentuk_dan_kepala_berbeda():
    ag = AgenEnsemble(K=5, seed=0, kapasitas=100)
    q = ag.q_semua(np.zeros(10, np.float32))
    assert q.shape == (5, 3)
    qb = ag.q_semua(np.random.default_rng(0).normal(size=(7, 10)).astype(np.float32))
    assert qb.shape == (7, 5, 3)
    s = np.ones(10, np.float32)
    q = ag.q_semua(s)
    assert np.std(q, axis=0).max() > 1e-4          # kepala diinisialisasi berbeda


def test_masker_bootstrap():
    buf = BufferBootstrap(20000, 5, 0.5, np.random.default_rng(0))
    for i in range(20000):
        buf.tambah(np.zeros(10), 0, 0.0, np.zeros(10), False)
    assert abs(buf.m.mean() - 0.5) < 0.01
    assert (buf.m.sum(1) >= 1).all()                # tidak ada transisi yang tidak dipakai kepala mana pun
    assert len(buf) == 20000


def test_buffer_cincin_dan_simpan(tmp_path):
    buf = BufferBootstrap(5, 3, 0.5, np.random.default_rng(0))
    for i in range(8):
        buf.tambah(np.full(10, i), i % 3, float(i), np.full(10, i + 1), i == 7)
    assert len(buf) == 5 and sorted(buf.r.tolist()) == [3, 4, 5, 6, 7]
    buf.simpan(str(tmp_path / "b.npz"))
    b2 = BufferBootstrap(5, 3, 0.5, np.random.default_rng(9))
    b2.muat(str(tmp_path / "b.npz"))
    assert np.array_equal(b2.s, buf.s) and np.array_equal(b2.m, buf.m) and b2.i == buf.i and len(b2) == 5


def test_belajar_bandit_dan_aksi_eval():
    ag = AgenEnsemble(K=5, seed=0, kapasitas=5000, min_replay=100, lr=1e-3)
    _isi_bandit(ag)
    for _ in range(2500):
        ag.latih()
    s = np.random.default_rng(5).normal(size=(50, 10)).astype(np.float32)
    q = ag.q_semua(s).mean(axis=1)                  # (50, 3)
    assert (q.argmax(1) == 1).mean() > 0.95
    assert abs(np.median(q[:, 1]) - 5.0) < 1.0
    a, qk = ag.aksi_eval(s[0])
    assert a == int(np.argmax(qk.mean(0)))


def test_kepala_tanpa_masker_tidak_berubah():
    """Masker benar-benar mengisolasi kepala: kepala 0 tidak pernah dipakai -> bobotnya tetap."""
    ag = AgenEnsemble(K=3, seed=0, kapasitas=2000, min_replay=10, target_tiap=10 ** 9)
    _isi_bandit(ag, 500)
    ag.buffer.m[:, 0] = 0.0
    ag.buffer.m[:, 1:] = 1.0
    w0 = [w.copy() for w in ag.online.kepala[0][0].get_weights() + ag.online.kepala[0][2].get_weights()]
    w1 = [w.copy() for w in ag.online.kepala[1][0].get_weights()]
    trunk = ag.online.fc1.get_weights()[0].copy()
    for _ in range(50):
        ag.latih()
    w0b = ag.online.kepala[0][0].get_weights() + ag.online.kepala[0][2].get_weights()
    assert all(np.array_equal(a, b) for a, b in zip(w0, w0b))
    assert not np.array_equal(w1[0], ag.online.kepala[1][0].get_weights()[0])
    assert not np.array_equal(trunk, ag.online.fc1.get_weights()[0])


def test_prior_beku_dan_ditambahkan():
    ag = AgenEnsemble(K=3, beta_prior=3.0, seed=0, kapasitas=2000, min_replay=10)
    s = np.ones((4, 10), np.float32)
    q_on = ag.online(s).numpy()
    q_pr = ag.prior(s).numpy()
    assert np.allclose(ag.q_semua(s), q_on + 3.0 * q_pr, atol=1e-5)
    pw = [w.copy() for w in ag.prior.get_weights()]
    _isi_bandit(ag, 200)
    for _ in range(20):
        ag.latih()
    assert all(np.array_equal(a, b) for a, b in zip(pw, ag.prior.get_weights()))
    assert len(ag.prior.trainable_variables) == 0


def test_simpan_muat_dan_lanjut(tmp_path):
    ag = AgenEnsemble(K=4, beta_prior=1.0, seed=3, kapasitas=2000, min_replay=10, target_tiap=7)
    _isi_bandit(ag, 300)
    for _ in range(30):
        ag.latih()
    ag.simpan_bobot(str(tmp_path / "w.npz"), dict(episode_latih=12))
    ag.simpan_titik(str(tmp_path / "t.npz"))
    s = np.random.default_rng(0).normal(size=(6, 10)).astype(np.float32)
    ev, k = muat_untuk_evaluasi(str(tmp_path / "w.npz"))
    assert k["K"] == 4 and k["beta_prior"] == 1.0 and k["episode_latih"] == 12
    assert np.allclose(ev.q_semua(s), ag.q_semua(s), atol=1e-6)
    ag2 = AgenEnsemble(K=4, beta_prior=1.0, seed=99, kapasitas=2000, min_replay=10, target_tiap=7)
    ag2.muat_bobot(str(tmp_path / "w.npz"))
    ag2.muat_titik(str(tmp_path / "t.npz"))
    assert ag2.n_train == 30
    assert np.allclose(ag2.target(s).numpy(), ag.target(s).numpy(), atol=1e-6)
    assert ag2.rng.random() == ag.rng.random()      # status RNG ikut tersimpan


# ------------------------------------------------------------------------------------------------
# Perbaikan reward
# ------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def modul_env():
    sys.path.insert(0, os.path.normpath(os.path.join(DIR, "..", "12_lingkungan", "tests")))
    import carla_palsu
    sys.modules["carla"] = carla_palsu
    dika = os.path.normpath(os.path.join(DIR, "..", "10_runner", "DQN_Akselerasi vertikal"))
    if not os.path.isdir(dika):
        pytest.skip("folder Dika tidak ada")
    sys.path.insert(0, dika)
    import env_latih
    from environment.carla_env import CarlaEnv
    return env_latih, CarlaEnv, carla_palsu


def _sim(modul_env, lubang, y=250.5, langkah_m=0.1, mode="perbaikan"):
    """Mobil lurus di y sepanjang +x; jalankan _calculate_reward per langkah. Kembalikan (hits, avoids)."""
    env_latih, CarlaEnv, cp = modul_env

    class GT:
        def __init__(self, ph):
            self.potholes = ph

        get_closest_ahead = CarlaEnv.__dict__["_calculate_reward"].__globals__["PotholeGroundTruth"].get_closest_ahead

    ph = [dict(id="p%d" % i, loc=cp.Location(x, yy, 0), extent_x=1.0, extent_y=1.5, yaw=0.0, severity=0.9,
               label="High") for i, (x, yy) in enumerate(lubang)]
    veh = types.SimpleNamespace(tf=cp.Transform(cp.Location(-300.0, y, 0), cp.Rotation(yaw=0.0)))
    veh.get_location = lambda: veh.tf.location
    veh.get_transform = lambda: veh.tf
    e = types.SimpleNamespace(
        collision_history=[], OUT_OF_ROAD_PENALTY=-200.0, ROAD_Y_MIN=245.55, ROAD_Y_MAX=252.55,
        finish_x_threshold=0.0, current_step=0, max_steps_per_episode=10 ** 9, vehicle=veh, gt=GT(ph),
        pothole_tracking={}, pothole_hit_cooldown=0, pothole_avoid_cooldown=0, total_hit_events=0,
        total_avoid_events=0, VEHICLE_HALF_WIDTH=0.74, VEHICLE_HALF_LEN=1.10, HIT_MARGIN_M=0.10,
        vehicle_state=dict(speed=7.0, steering_angle=0.0), mode_reward=mode)
    e._get_lane_info = lambda: dict(current_y=y, out_of_road=False)
    fungsi = (env_latih.CarlaEnvLatih._calculate_reward if mode == "perbaikan"
              else CarlaEnv._calculate_reward)
    import builtins
    cetak = builtins.print
    builtins.print = lambda *a, **k: None
    try:
        while veh.tf.location.x < max(p[0] for p in lubang) + 5:
            veh.tf.location.x += langkah_m
            e.current_step += 1
            if e.pothole_hit_cooldown > 0:            # sama dengan CarlaEnv.step
                e.pothole_hit_cooldown -= 1
            fungsi(e, None)
    finally:
        builtins.print = cetak
    return e.total_hit_events, e.total_avoid_events


def test_helper_geometri(modul_env):
    env_latih = modul_env[0]
    assert env_latih.setengah_lebar_melintang(1.0, 1.5, 0.0, 0.0) == pytest.approx(1.5)
    assert env_latih.setengah_lebar_melintang(1.0, 1.5, 90.0, 0.0) == pytest.approx(1.0)
    maju, kanan = env_latih.offset_lokal(10.0, 2.0, 0.0, 0.0, 0.0)
    assert (maju, kanan) == pytest.approx((10.0, 2.0))
    maju, kanan = env_latih.offset_lokal(0.0, 10.0, 0.0, 0.0, 90.0)   # yaw 90 = menghadap +y
    assert (maju, kanan) == pytest.approx((10.0, 0.0))


def test_perbaikan_1_ukuran_melintang(modul_env):
    """Lubang 1,9 m di samping: bodi (setengah lebar 0,74) menimpa lubang (setengah lebar melintang 1,5)."""
    assert _sim(modul_env, [(-280.0, 250.5 + 1.9)], mode="perbaikan") == (1, 0)
    assert _sim(modul_env, [(-280.0, 250.5 + 1.9)], mode="dika") == (0, 1)          # bug Dika: AVOID
    assert _sim(modul_env, [(-280.0, 250.5 + 2.5)], mode="perbaikan") == (0, 1)     # benar-benar di samping
    assert _sim(modul_env, [(-280.0, 250.5)], mode="perbaikan") == (1, 0)


def test_perbaikan_2_tanpa_cooldown(modul_env):
    """Dua lubang selajur berjarak 8 m dilewati pada 0,2 m/langkah (14,4 km/jam): keduanya HIT."""
    lub = [(-280.0, 250.5), (-272.0, 250.5)]
    assert _sim(modul_env, lub, langkah_m=0.2, mode="perbaikan") == (2, 0)
    assert _sim(modul_env, lub, langkah_m=0.2, mode="dika") == (1, 1)               # bug Dika: AVOID kedua


def test_tidak_ada_perubahan_untuk_kasus_biasa(modul_env):
    """Kasus yang benar di kode Dika tetap sama: lurus melewati 3 lubang selajur berjauhan + 2 lubang lajur lain."""
    lub = [(-290.0, 250.5), (-260.0, 250.5), (-230.0, 250.5), (-275.0, 247.0), (-245.0, 247.0)]
    assert _sim(modul_env, lub, mode="perbaikan") == _sim(modul_env, lub, mode="dika") == (3, 2)
