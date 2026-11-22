"""
Uji end-to-end dengan CARLA tiruan + YOLO asli (best_pure.pt) + DQN asli (model_best.h5).
Butuh torch, ultralytics, tensorflow. Lama: ±2-4 menit di CPU.

    python -m pytest -q tests/test_e2e_palsu.py --dir_dika "<...>/10_runner/DQN_Akselerasi vertikal"

Yang diuji (alur kode, bukan perilaku agen):
  1. _detect_potholes_yolo turunan menghasilkan state 10-D IDENTIK dengan fungsi asli Dika pada urutan
     citra CARLA yang sama (termasuk EMA severity), dan hook mencocokkan semua kotak (sigmoid(logit) = conf).
  2. Toggle grid: hanya objek slot terpilih yang menyala; GT env = tata letak episode.
  3. Runner jalankan_skenario.py berjalan untuk ID0 (grid), A3 transisi, A5 konstan, D1 t2 (spawn):
     berkas log lengkap, baris langkah = langkah, hook_tidak_cocok = 0, f_transisi naik 0 -> 1 setelah onset,
     cuaca yang dipasang berubah, lanjut-otomatis melewati seed yang sudah ada.
"""
import csv
import glob
import json
import os
import subprocess
import sys
import types

import numpy as np
import pytest

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(DIR, "tests")
sys.path.insert(0, DIR)
sys.path.insert(0, TESTS)


def _dir_dika(request):
    d = request.config.getoption("--dir_dika")
    if not os.path.isdir(d):
        pytest.skip("folder Dika tidak ada: %s" % d)
    return os.path.abspath(d)


def _citra():
    for c in [os.path.join(DIR, "..", "11_cuaca", "data_PaketEpic"), os.path.join(DIR, "..", "data", "data_PaketEpic")]:
        if glob.glob(os.path.join(c, "**", "*.png"), recursive=True):
            return os.path.abspath(c)
    pytest.skip("citra CARLA (11_cuaca/data_PaketEpic) tidak ada")


GT = os.path.normpath(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_lengkap.json"))


def _toggle_dir():
    for c in [os.path.join(DIR, "uji_carla"), os.path.join(DIR, "..", "data", "toggle")]:
        if os.path.exists(os.path.join(c, "toggle_nyala.png")):
            return os.path.abspath(c)
    pytest.skip("toggle_nyala.png / toggle_mati.png (hasil uji_carla_24_25.py toggle) tidak ada")


@pytest.fixture(scope="module")
def env(request):
    dika = _dir_dika(request)
    import carla_palsu as cp
    cp.Client.CITRA_DIR = _citra()
    cp.Client.SLOT = json.load(open(GT))
    cp.TOGGLE_DIR = _toggle_dir()
    cp.BUG_TOGGLE = 1.0                 # bug toggle selalu terjadi: kode harus tetap benar
    sys.modules["carla"] = cp
    sys.path.insert(0, dika)
    cwd = os.getcwd()
    os.chdir(dika)
    from env_skenario import CarlaEnvSkenario
    e = CarlaEnvSkenario(backend="spawn", gt_v2_path=GT, kalibrasi={}, town="train_fix",
                         yolo_model_path="Yolo/best_pure.pt",
                         gt_json_path=os.path.join(os.path.dirname(GT), "pothole_gt_v2_segmen_dika.json"),
                         weather=cp.WeatherParameters.ClearNoon)
    yield e
    os.chdir(cwd)


def test_state_identik_dengan_fungsi_asli_dika(env):
    from environment.carla_env import CarlaEnv
    import cv2
    fs = sorted(glob.glob(os.path.join(_citra(), "**", "*.png"), recursive=True))
    imgs = [cv2.imread(f) for f in fs] * 3
    asli = types.SimpleNamespace(yolo_model=env.yolo_model, smoothed_severity=0.0)
    env.smoothed_severity = 0.0
    env.transisi = None
    n_kotak = 0
    for im in imgs:
        a = CarlaEnv._detect_potholes_yolo(asli, im)
        b = env._detect_potholes_yolo(im)
        assert np.array_equal(a, b), (a, b)
        r = env.rekam_persepsi
        assert r is not None and r["cocok"]
        n_kotak += len(r["conf"])
        assert r["fitur"].shape == (896,)
        if len(r["conf"]):
            sig = 1 / (1 + np.exp(-r["logit"][np.arange(len(r["conf"])), r["cls"]]))
            assert np.abs(sig - r["conf"]).max() < 1e-4
    assert n_kotak > 0, "YOLO tidak mendeteksi apa pun pada citra uji; uji hook tidak bermakna"


def test_pencocokan_cadangan_sama_dengan_nms_return_idxs(env):
    """Jalur cadangan (versi Ultralytics tanpa return_idxs) harus memilih anchor yang sama."""
    import cv2
    fs = sorted(glob.glob(os.path.join(_citra(), "**", "*.png"), recursive=True))
    env.transisi = None
    n = 0
    for f in fs:
        im = cv2.imread(f)
        env.hook._nms_idx_ok = None
        env._detect_potholes_yolo(im)
        a = env.rekam_persepsi
        env.hook._nms_idx_ok = False
        env._detect_potholes_yolo(im)
        b = env.rekam_persepsi
        assert a["cocok"] and b["cocok"]
        assert np.array_equal(a["anchor"], b["anchor"]) and np.allclose(a["logit"], b["logit"])
        n += len(a["conf"])
    env.hook._nms_idx_ok = None
    assert n >= 3


def test_toggle_grid_dan_gt_episode(env, tmp_path):
    from skenario import resolusi
    sp = resolusi("ID0", 1, 3, "konstan", "grid")
    info = env.siapkan_episode(sp, str(tmp_path / "gt.json"))
    w = env.world
    nyala_slot = {sid for sid, ids in env.grid.peta.items() if ids and all(w.nyala[i] for i in ids)}
    assert nyala_slot == {l["slot"] for l in env.tata_letak.lubang}
    assert all(not w.nyala[i] for sid, ids in env.grid.peta.items() if sid not in nyala_slot for i in ids)
    assert sorted(p["id"] for p in env.gt.potholes) == sorted(l["id"] for l in env.tata_letak.lubang)
    assert w.nyala[1] is True                       # objek non-lubang tidak disentuh
    assert info["tata_letak"]["n"] == env.tata_letak.n


def test_toggle_cara_lama_memicu_bug_tiruan(env):
    """Reproduksi: mati-semua lalu nyala-semua dalam satu frame -> lubang tak tampak (BUG_TOGGLE = 1)."""
    from verifikasi_lubang import PemeriksaLubang
    g, w = env.grid, env.world
    g._toggle(g.peta.keys(), False)
    g._toggle(g.peta.keys(), True)
    w.tick()
    assert not any(w.nyala[i] for ids in g.peta.values() for i in ids)
    import carla
    pem = PemeriksaLubang(w, carla, env.yolo_model)
    assert not pem.cek_satu(next(s for s in env.slot if s["id"] == "ph_0004"))["tampak"]
    pem.tutup()
    g.ulang(g.peta.keys(), tick=w.tick)            # pemulihan: mati, tick, nyala, tick
    assert all(w.nyala[i] for ids in g.peta.values() for i in ids)
    g.aktif = set(g.peta.keys())


def test_cara_baru_semua_lubang_tampak_banyak_episode(env, tmp_path):
    from skenario import resolusi
    w = env.world
    for s in range(12):
        sp = resolusi("ID0", 1, s, "konstan", "grid")
        info = env.siapkan_episode(sp, str(tmp_path / ("gt%d.json" % s)))
        v = info["backend"]["verifikasi"]
        assert v["lolos"] and v["percobaan"] == 1, v
        nyala = {sid for sid, ids in env.grid.peta.items() if all(w.nyala[i] for i in ids)}
        assert nyala == {l["slot"] for l in env.tata_letak.lubang}


def test_verifikasi_memulihkan_lubang_yang_hilang(env, tmp_path):
    from skenario import resolusi
    sp = resolusi("REG", 1, 0, "konstan", "grid")
    env.siapkan_episode(sp, str(tmp_path / "a.json"))
    w = env.world
    for ids in env.grid.peta.values():            # sabotase: lubang hilang tanpa sepengetahuan BackendGrid
        for i in ids:
            w.nyala[i] = False
    v = env.verifikasi_lubang(env.tata_letak)
    assert v["lolos"] and v["percobaan"] == 2
    assert all(w.nyala[i] for l in env.tata_letak.lubang for i in env.grid.peta[l["slot"]])


def test_verifikasi_gagal_permanen_menghentikan_episode(env, tmp_path, monkeypatch):
    import verifikasi_lubang as vl
    from skenario import resolusi
    monkeypatch.setattr(vl.PemeriksaLubang, "cek_satu", lambda self, l: dict(id=l["id"], tampak=False, conf=0.0, jarak=None))
    with pytest.raises(RuntimeError):
        env.siapkan_episode(resolusi("REG", 1, 0, "konstan", "grid"), str(tmp_path / "b.json"))


def test_spawn_mematikan_grid_dan_memunculkan_aktor(env, tmp_path):
    from skenario import resolusi
    sp = resolusi("D1", 2, 1, "konstan", "spawn")
    env.siapkan_episode(sp, str(tmp_path / "gt.json"))
    w = env.world
    assert all(not v for i, v in w.nyala.items() if i != 1)
    props = [a for a in w.actors.values() if a.type_id == "static.prop.mesh"]
    assert len(props) == env.tata_letak.n == len(env.spawner.id_aktor)


def _jalankan(dika, *arg, out):
    e = dict(os.environ)
    e["PYTHONPATH"] = os.pathsep.join([os.path.join(TESTS, "palsu_pkg"), TESTS, e.get("PYTHONPATH", "")])
    e["CARLA_PALSU_CITRA"] = _citra()
    e["CARLA_PALSU_GT"] = GT
    e["CARLA_PALSU_V"] = "300"          # mobil tiruan 10x lebih cepat supaya episode cepat selesai
    e["CARLA_PALSU_SETIR"] = "0"        # dan selalu lurus, supaya mencapai garis finis (uji alur, bukan perilaku)
    e["CARLA_PALSU_BUG"] = "1.0"        # bug toggle selalu terjadi
    e["CARLA_PALSU_TOGGLE_DIR"] = _toggle_dir()
    e["TF_CPP_MIN_LOG_LEVEL"] = "3"
    cmd = [sys.executable, os.path.join(DIR, "jalankan_skenario.py"), "--dir_dika", dika, "--out", out,
           "--maks_langkah", "400", "--label", "palsu"] + list(arg)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1200, env=e)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    return p.stdout


def _baca_run(out, pola):
    d = sorted(glob.glob(os.path.join(out, "*_" + pola)))
    assert d, "folder run %s tidak ada" % pola
    return d[-1]


@pytest.mark.parametrize("arg,pola", [
    (["--kode", "ID0", "--episodes", "2"], "ID0_t1_konstan_grid_palsu"),
    (["--kode", "A3", "--tingkat", "3", "--mode", "transisi", "--episodes", "1", "--seed_awal", "5"], "A3_t3_transisi_grid_palsu"),
    (["--kode", "A5", "--tingkat", "2", "--episodes", "1"], "A5_t2_konstan_grid_palsu"),
    (["--kode", "D1", "--tingkat", "2", "--backend", "spawn", "--episodes", "1"], "D1_t2_konstan_spawn_palsu"),
])
def test_runner_lengkap(request, tmp_path_factory, arg, pola):
    dika = _dir_dika(request)
    out = str(tmp_path_factory.mktemp("log"))
    _jalankan(dika, *arg, out=out)
    run = _baca_run(out, pola)
    ring = list(csv.DictReader(open(os.path.join(run, "ringkasan_episode.csv"))))
    assert len(ring) == int(arg[arg.index("--episodes") + 1])
    from logger_skenario import muat_episode
    for r in ring:
        nama = "ep%03d_seed%s" % (int(r["episode"]), r["seed"])
        ep = muat_episode(run, nama)
        L, P, M = ep["langkah"], ep["persepsi"], ep["meta"]
        T = int(r["langkah"])
        assert len(L["step"]) == T == M["langkah"]
        assert int(r["hook_tidak_cocok"]) == 0 and M["hook_tidak_cocok"] == 0
        assert P["fitur"].shape == (T, 896) and P["topk_logit"].shape == (T, 100, 3)
        assert len(P["det_step"]) == np.nansum(L["n_det"])
        assert np.array_equal(np.argmax(np.c_[L["q0"], L["q1"], L["q2"]], 1), L["aksi"].astype(int))
        assert sorted(g["id"] for g in ep["gt"]) == M["siap"]["tata_letak"]["id"]
        if "transisi" in pola:
            f = L["f_transisi"]
            x_on = M["skenario"]["transisi"]["x_onset"]
            assert (f[L["x"] < x_on - 0.5] == 0).all() and f.max() == 1.0
            assert np.all(np.diff(f) >= -1e-9)                       # rampa tidak pernah mundur
            assert int(r["langkah_onset"]) == int(L["step"][np.argmax(f > 0)]) == M["langkah_onset"]
            fog = L["w_fog_density"]
            assert fog[0] == 0 and fog[-1] == pytest.approx(80.0)
        assert M["akhir"] == "finis" and r["akhir"] == "finis"
        if "spawn" not in pola:
            assert int(r["verif_percobaan"]) == 1 and float(r["verif_conf_min"]) > 0.05
        if "A5" in pola:
            assert np.nanmin(L["f_korupsi"]) == 1.0
    # lanjut otomatis: jalankan lagi -> tidak ada folder run baru
    n0 = len(glob.glob(os.path.join(out, "*")))
    s = _jalankan(dika, *arg, out=out)
    assert "sudah selesai" in s and len(glob.glob(os.path.join(out, "*"))) == n0
