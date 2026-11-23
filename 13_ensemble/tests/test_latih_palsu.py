"""
Uji end-to-end dengan CARLA tiruan (12_lingkungan/tests/carla_palsu.py) + YOLO asli + TensorFlow.
Menguji ALUR (checkpoint, lanjut, evaluasi, seleksi, berkas keluaran, --ensemble di runner skenario),
bukan perilaku agen. ±3-6 menit di CPU.

    python -m pytest -q tests/test_latih_palsu.py
"""
import csv
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pytest

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LING = os.path.normpath(os.path.join(DIR, "..", "12_lingkungan"))
TESTS_LING = os.path.join(LING, "tests")
DIKA = os.path.normpath(os.path.join(DIR, "..", "10_runner", "DQN_Akselerasi vertikal"))
GT = os.path.normpath(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_lengkap.json"))


def _env():
    citra = os.path.normpath(os.path.join(DIR, "..", "11_cuaca", "data_PaketEpic"))
    tog = os.path.join(LING, "uji_carla")
    if not glob.glob(os.path.join(citra, "**", "*.png"), recursive=True) or not os.path.exists(
            os.path.join(tog, "toggle_nyala.png")) or not os.path.isdir(DIKA):
        pytest.skip("citra CARLA / toggle / folder Dika tidak ada")
    e = dict(os.environ)
    e["PYTHONPATH"] = os.pathsep.join([os.path.join(TESTS_LING, "palsu_pkg"), TESTS_LING, e.get("PYTHONPATH", "")])
    e.update(CARLA_PALSU_CITRA=citra, CARLA_PALSU_GT=GT, CARLA_PALSU_V="300", CARLA_PALSU_SETIR="0.3",
             CARLA_PALSU_BUG="1.0", CARLA_PALSU_TOGGLE_DIR=tog, TF_CPP_MIN_LOG_LEVEL="3")
    return e


def _latih(out, *arg, rc_harap=0):
    cmd = [sys.executable, os.path.join(DIR, "latih_ensemble.py"), "--out", out, "--label", "palsu", "--seed", "1",
           "--K", "3", "--min_replay", "50", "--eval_langkah", "1", "--eval_ep", "1", "--maks_langkah", "300",
           "--jeda", "0"] + list(arg)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800, env=_env())
    assert p.returncode == rc_harap, p.stdout[-4000:] + p.stderr[-4000:]
    return p.stdout


def _baca(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def test_cek_tanpa_carla(tmp_path):
    p = subprocess.run([sys.executable, os.path.join(DIR, "latih_ensemble.py"), "--cek", "--out", str(tmp_path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    assert p.returncode == 0, p.stderr
    assert "seed 100000" in p.stdout and "seed  90000" in p.stdout


@pytest.fixture(scope="module")
def run_latih(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("latih"))
    s1 = _latih(out, "--episodes", "3")
    return out, os.path.join(out, "seed1_K3_b0"), s1


def test_berkas_dan_isi(run_latih):
    out, run, _ = run_latih
    ep = _baca(os.path.join(run, "episode.csv"))
    assert [int(r["episode"]) for r in ep] == [1, 2, 3]
    assert [int(r["seed_tata_letak"]) for r in ep] == [110000, 110001, 110002]
    assert all(0 <= int(r["kepala"]) < 3 for r in ep)
    assert int(ep[-1]["n_train"]) > 0 and int(ep[-1]["buffer"]) == sum(int(r["langkah"]) for r in ep)
    assert all(r["verif_percobaan"] == "1" for r in ep)
    ring = _baca(os.path.join(run, "eval_ringkas.csv"))
    assert [int(r["episode_latih"]) for r in ring] == [1, 2, 3]         # eval_langkah 1 = setiap episode
    assert [int(r["langkah_latih"]) for r in ring] == [int(r["langkah_total"]) for r in ep]
    assert int(ep[-1]["langkah_total"]) == sum(int(r["langkah"]) for r in ep)
    ev = _baca(os.path.join(run, "eval.csv"))
    assert [int(r["seed"]) for r in ev] == [90000, 90000, 90000]
    assert os.path.exists(os.path.join(run, "bobot", "bobot_ep0002.npz"))
    assert os.path.exists(os.path.join(run, "bobot", "bobot_terbaik.npz"))
    assert os.path.exists(os.path.join(run, "bobot", "bobot_akhir.npz"))
    st = json.load(open(os.path.join(run, "titik", "status.json")))
    assert st["selesai"] and st["episode"] == 3 and st["ep_terbaik"] in (1, 2, 3)
    assert st["langkah"] == int(ep[-1]["langkah_total"])
    k = json.load(open(os.path.join(run, "konfig.json")))
    assert k["agen"]["K"] == 3 and k["argumen"]["seed_latih_awal"] == 110000


def test_jalankan_lagi_tidak_mengulang(run_latih):
    out, run, _ = run_latih
    s = _latih(out, "--episodes", "3")
    assert "SELESAI" in s
    assert len(_baca(os.path.join(run, "episode.csv"))) == 3


def test_lanjut_menambah_episode_dan_konfig_dijaga(run_latih):
    out, run, _ = run_latih
    st = json.load(open(os.path.join(run, "titik", "status.json")))
    st["selesai"] = False                          # tiru run yang belum selesai, lalu perpanjang ke 4 episode
    json.dump(st, open(os.path.join(run, "titik", "status.json"), "w"))
    n_buf = len(np.load(os.path.join(run, "titik", "buffer.npz"))["r"])
    _latih(out, "--episodes", "4")
    ep = _baca(os.path.join(run, "episode.csv"))
    assert [int(r["episode"]) for r in ep] == [1, 2, 3, 4]
    assert int(ep[-1]["buffer"]) == n_buf + int(ep[-1]["langkah"])     # buffer lama dimuat, bukan mulai kosong
    assert [int(r["episode_latih"]) for r in _baca(os.path.join(run, "eval_ringkas.csv"))] == [1, 2, 3, 4]
    # konfigurasi berbeda pada folder yang sama -> ditolak
    st = json.load(open(os.path.join(run, "titik", "status.json")))
    st["selesai"] = False
    json.dump(st, open(os.path.join(run, "titik", "status.json"), "w"))
    s = _latih(out, "--episodes", "5", "--p_masker", "0.7", "--nama", "seed1_K3_b0", "--maks_ulang", "0", rc_harap=1)
    assert "BERHENTI" in s


def test_anggaran_langkah_dan_eval_berkala(tmp_path):
    """Tanpa batas episode: berhenti begitu langkah_total tercapai; eval tiap eval_langkah + di akhir."""
    out = str(tmp_path)
    _latih(out, "--episodes", "0", "--langkah_total", "500", "--eval_langkah", "250", "--nama", "anggaran")
    run = os.path.join(out, "anggaran")
    ep = _baca(os.path.join(run, "episode.csv"))
    tot = [int(r["langkah_total"]) for r in ep]
    assert tot[-1] >= 500 and (len(tot) == 1 or tot[-2] < 500)            # berhenti di episode pertama yang melewati
    ring = _baca(os.path.join(run, "eval_ringkas.csv"))
    l_eval = [int(r["langkah_latih"]) for r in ring]
    assert l_eval[-1] == tot[-1]
    batas = 250
    for le in l_eval[:-1]:                                                # setiap eval terjadi setelah melewati ambang
        assert le >= batas
        while batas <= le:
            batas += 250
    assert all(float(r["epsilon_akhir"]) <= 1.0 for r in ep)


def test_runner_skenario_dengan_ensemble(run_latih, tmp_path):
    out, run, _ = run_latih
    bobot = os.path.join(run, "bobot", "bobot_terbaik.npz")
    log = str(tmp_path / "log")
    cmd = [sys.executable, os.path.join(LING, "jalankan_skenario.py"), "--dir_dika", DIKA, "--out", log,
           "--maks_langkah", "300", "--label", "palsu", "--kode", "ID0", "--episodes", "1", "--ensemble", bobot]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1200, env=_env())
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    runs = glob.glob(os.path.join(log, "*_ID0_t1_konstan_grid_palsu_ens-seed1-K3-b0"))
    assert len(runs) == 1
    sys.path.insert(0, LING)
    from logger_skenario import muat_episode
    ep = muat_episode(runs[0], "ep001_seed0")
    qk = np.load(os.path.join(runs[0], "qkepala_ep001_seed0.npy"))
    L = ep["langkah"]
    assert qk.shape == (len(L["step"]), 3, 3)
    assert np.allclose(qk.mean(1), np.c_[L["q0"], L["q1"], L["q2"]], atol=1e-3)
    assert np.array_equal(qk.mean(1).argmax(1), L["aksi"].astype(int))
    assert ep["meta"]["kebijakan"]["jenis"] == "ensemble"
