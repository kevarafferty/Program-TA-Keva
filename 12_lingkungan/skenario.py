"""
skenario.py — [#25] Katalog skenario off-nominal (Tabel 2.2 proposal), resolusi spesifikasi dari seed,
jadwal transisi di tengah episode, dan korupsi citra (A5, A6).

Tanpa import carla di tingkat modul. Spesifikasi cuaca di sini masih SIMBOLIK (nama preset + perubahan);
angka akhirnya dihitung env_skenario.py dari carla.WeatherParameters lalu dicatat di log.

Desain penting
--------------
1. Desain berpasangan: tata letak lubang dan offset awal hanya bergantung pada (seed, konfig tata letak),
   TIDAK pada kode skenario. Jadi A3 seed 5 dan ID0 seed 5 memakai lubang dan titik awal yang sama;
   selisih hasil berasal dari kondisinya saja.
2. Tiga tingkat intensitas per kondisi (§2.1.3). Tingkat yang hanya bisa dibuat backend spawn ditandai
   'backend_wajib': 'spawn'; runner menolak menjalankannya dengan backend grid.
3. Mode 'transisi' (T23): kondisi berubah dari nominal ke target di posisi x_onset yang diacak per seed,
   dengan rampa sepanjang jarak_rampa_m. Faktor f(x) = clip((x - x_onset)/rampa, 0, 1).
   Berbasis POSISI (bukan waktu) supaya lubang sebelum onset selalu nominal, berapa pun kecepatannya.
4. Kondisi yang butuh aset baru (B1, B2, B3 ukuran) BELUM bisa dibuat dan ditandai 'butuh_aset'.
"""
from __future__ import annotations

import copy
import json
import math
import os
from typing import Dict, List, Optional

import numpy as np

from generator_tata_letak import KonfigTataLetak, RNG, VarianAset, turunkan_seed

DIR = os.path.dirname(os.path.abspath(__file__))
KALIBRASI_DEFAULT = os.path.join(DIR, "kalibrasi_lingkungan.json")

THROTTLE_DIKA = 0.3
MICROLINO = "vehicle.micro.microlino"
OFFSET_ID0 = dict(offset_x=2.0, offset_y=0.5, heading_deg=0.0)   # sama dengan baseline #19-#21

# Tata letak ID-0: jarang–sedang (Dika = 7,5 lubang/100 m; ID-0 sengaja di bawahnya)
TL_ID0 = dict(pola="acak", kerapatan_per_100m=(2.0, 5.0), jarak_min_m=10.0, jarak_min_selajur_m=10.0)

# ---------------------------------------------------------------------------------------------
# Katalog. Field per tingkat (semua opsional, default = ID-0):
#   cuaca      : {"basis": nama preset | [daftar, dipilih per seed], "menuju": preset, "f": 0..1,
#                 "ubah": {param: nilai | "AZIMUT_MENGHADAP_KAMERA"}}
#   lampu      : None | "LowBeam" | "HighBeam"
#   korupsi    : None | {"blur_sigma": px, "tetes_n": jumlah, "derau_sigma": DN, "jpeg_q": kualitas}
#   kecepatan  : None (throttle Dika 0,3) | {"target_kmh": v}  -> throttle dari kalibrasi
#   kendaraan  : blueprint (default vehicle.micro.microlino)
#   spawn      : {"offset_x", "offset_y", "heading_deg"}
#   tata_letak : perubahan KonfigTataLetak
#   backend_wajib : "spawn" jika tidak bisa dibuat dengan grid
# ---------------------------------------------------------------------------------------------
KATALOG: Dict[str, dict] = {
    # REG: replikasi baseline #21-#22 (tata letak asli Dika 19 lubang, offset ±2/±0,5 m, preset Dika).
    # Dipakai untuk uji regresi runner baru (hasil harus setara HASIL_BASELINE.md) sekaligus
    # merekam fitur/logit/Q pada kondisi baseline. t3 = ClearNight TANPA lampu, seperti kode Dika.
    "REG": dict(kelompok="Regresi", ket="Replikasi baseline: 19 lubang Dika, preset cuaca Dika", transisi_bisa=False,
                tingkat={1: dict(cuaca=dict(basis="ClearNoon"), tata_letak=dict(pola="semua")),
                         2: dict(cuaca=dict(basis="HardRainNoon"), tata_letak=dict(pola="semua")),
                         3: dict(cuaca=dict(basis="ClearNight"), tata_letak=dict(pola="semua"))}),

    "ID0": dict(kelompok="Nominal", ket="Cerah/berawan siang, tata letak acak jarang-sedang",
                transisi_bisa=False,
                tingkat={1: dict(cuaca=dict(basis=["ClearNoon", "CloudyNoon"]))}),

    "A1": dict(kelompok="Persepsi", ket="Malam, lampu utama LowBeam, tanpa penerangan jalan",
               transisi_bisa=True,
               tingkat={1: dict(cuaca=dict(basis="ClearNoon", ubah=dict(sun_altitude_angle=-30.0)), lampu="LowBeam"),
                        2: dict(cuaca=dict(basis="ClearNoon", ubah=dict(sun_altitude_angle=-60.0)), lampu="LowBeam"),
                        3: dict(cuaca=dict(basis="ClearNoon", ubah=dict(sun_altitude_angle=-90.0)), lampu="LowBeam")}),

    # Tingkat 3 = HardRainNoon persis (preset yang cocok dengan rekaman hujan Dika, LOG 21 Nov 20.40).
    # Tingkat 1-2 = interpolasi semua parameter ClearNoon -> HardRainNoon.
    "A2": dict(kelompok="Persepsi", ket="Hujan lebat, jalan basah, genangan", transisi_bisa=True,
               tingkat={1: dict(cuaca=dict(basis="ClearNoon", menuju="HardRainNoon", f=0.6)),
                        2: dict(cuaca=dict(basis="ClearNoon", menuju="HardRainNoon", f=0.8)),
                        3: dict(cuaca=dict(basis="ClearNoon", menuju="HardRainNoon", f=1.0))}),

    "A3": dict(kelompok="Persepsi", ket="Kabut", transisi_bisa=True,
               tingkat={1: dict(cuaca=dict(basis="ClearNoon", ubah=dict(fog_density=30.0, fog_distance=20.0))),
                        2: dict(cuaca=dict(basis="ClearNoon", ubah=dict(fog_density=55.0, fog_distance=10.0))),
                        3: dict(cuaca=dict(basis="ClearNoon", ubah=dict(fog_density=80.0, fog_distance=0.0)))}),

    "A4": dict(kelompok="Persepsi", ket="Silau matahari rendah searah kamera", transisi_bisa=True,
               tingkat={l: dict(cuaca=dict(basis="ClearNoon", ubah=dict(sun_altitude_angle=alt,
                                                                       sun_azimuth_angle="AZIMUT_MENGHADAP_KAMERA")))
                        for l, alt in ((1, 15.0), (2, 10.0), (3, 5.0))}),

    "A5": dict(kelompok="Persepsi", ket="Kaca buram/kotor: Gaussian blur + tetes air statis di lensa",
               transisi_bisa=True,
               tingkat={1: dict(korupsi=dict(blur_sigma=1.5, tetes_n=6)),
                        2: dict(korupsi=dict(blur_sigma=3.0, tetes_n=14)),
                        3: dict(korupsi=dict(blur_sigma=5.0, tetes_n=25))}),

    "A6": dict(kelompok="Persepsi", ket="Derau sensor + kompresi JPEG (gaya ImageNet-C)", transisi_bisa=True,
               tingkat={1: dict(korupsi=dict(derau_sigma=8.0, jpeg_q=30)),
                        2: dict(korupsi=dict(derau_sigma=16.0, jpeg_q=15)),
                        3: dict(korupsi=dict(derau_sigma=32.0, jpeg_q=7))}),

    "B1": dict(kelompok="Tampilan lubang", ket="Lubang tergenang air", butuh_aset=True, tingkat={}),
    "B2": dict(kelompok="Tampilan lubang", ket="Pola mirip lubang (tambalan, noda, bayangan)", butuh_aset=True, tingkat={}),
    "B3": dict(kelompok="Tampilan lubang", ket="Lubang di tepi lajur (ukuran lain butuh aset)", transisi_bisa=False,
               tingkat={l: dict(tata_letak=dict(jitter_lateral_m=j), backend_wajib="spawn")
                        for l, j in ((1, 0.6), (2, 1.0), (3, 1.4))}),

    # C1: tingkat 1 = tata letak asli Dika (19 slot, padat relatif ID-0). Tingkat 2-3 butuh posisi bebas.
    "C1": dict(kelompok="Konfigurasi", ket="Klaster padat, semua lajur terisi, zig-zag", transisi_bisa=False,
               tingkat={1: dict(tata_letak=dict(pola="semua")),
                        2: dict(tata_letak=dict(pola="klaster", kerapatan_per_100m=(8.0, 10.0), jarak_min_m=6.0,
                                                jarak_min_selajur_m=8.0, jarak_pasangan_m=(5.0, 7.0)),
                                backend_wajib="spawn"),
                        3: dict(tata_letak=dict(pola="klaster", kerapatan_per_100m=(10.0, 14.0), jarak_min_m=5.0,
                                                jarak_min_selajur_m=7.0, jarak_pasangan_m=(4.0, 6.0)),
                                backend_wajib="spawn")}),

    "C2": dict(kelompok="Konfigurasi", ket="Kecepatan ego 20-30 km/jam (throttle dinaikkan)", transisi_bisa=False,
               tingkat={1: dict(kecepatan=dict(target_kmh=20.0)), 2: dict(kecepatan=dict(target_kmh=25.0)),
                        3: dict(kecepatan=dict(target_kmh=30.0))}),

    "C3": dict(kelompok="Konfigurasi", ket="Offset lateral dan heading awal di luar rentang ID-0 (±0,5 m, 0°)",
               transisi_bisa=False,
               # besaran |offset_y| dan |heading| diambil dari pita [min, maks] dengan tanda acak,
               # supaya setiap episode benar-benar di luar rentang ID-0
               tingkat={1: dict(spawn=dict(offset_y_min=0.5, offset_y=0.9, heading_min=1.0, heading_deg=4.0)),
                        2: dict(spawn=dict(offset_y_min=0.9, offset_y=1.2, heading_min=4.0, heading_deg=7.0)),
                        3: dict(spawn=dict(offset_y_min=1.2, offset_y=1.5, heading_min=7.0, heading_deg=10.0))}),

    # [22 Nov] Kecepatan disamakan dengan Microlino pada throttle 0,3 (kalibrasi per kendaraan). Tanpa ini
    # Tesla throttle 0,3 melaju 18,2 km/jam (Microlino 7,6) sehingga C4 tercampur dengan C2.
    "C4": dict(kelompok="Konfigurasi", ket="Dimensi kendaraan berbeda, kecepatan sama dengan Microlino",
               transisi_bisa=False,
               tingkat={1: dict(kendaraan="vehicle.nissan.micra", kecepatan=dict(target_kmh="ACUAN_MICROLINO")),
                        2: dict(kendaraan="vehicle.citroen.c3", kecepatan=dict(target_kmh="ACUAN_MICROLINO")),
                        3: dict(kendaraan="vehicle.tesla.model3", kecepatan=dict(target_kmh="ACUAN_MICROLINO"))}),

    # D1: tingkat 1 = pasangan slot beda lajur terdekat di grid (8,7-9,1 m); 2-3 pasangan lebih rapat (spawn)
    "D1": dict(kelompok="ID-sulit", ket="Dua lubang High berjarak sempit", transisi_bisa=False,
               tingkat={1: dict(tata_letak=dict(pola="pasangan_rapat", n_pasangan_rapat=2)),
                        2: dict(tata_letak=dict(pola="pasangan_rapat", n_pasangan_rapat=3, jarak_pasangan_m=(5.5, 7.0),
                                                jarak_min_m=5.0), backend_wajib="spawn"),
                        3: dict(tata_letak=dict(pola="pasangan_rapat", n_pasangan_rapat=4, jarak_pasangan_m=(4.0, 5.5),
                                                jarak_min_m=4.0), backend_wajib="spawn")}),

    "E1": dict(kelompok="Gabungan", ket="Malam + hujan (A1 + A2 pada tingkat yang sama)", transisi_bisa=True,
               gabungan=("A1", "A2"), tingkat={1: {}, 2: {}, 3: {}}),
    "E2": dict(kelompok="Gabungan", ket="Kabut + kecepatan tinggi (A3 + C2 pada tingkat yang sama)", transisi_bisa=False,
               gabungan=("A3", "C2"), tingkat={1: {}, 2: {}, 3: {}}),
}


def daftar_kondisi(termasuk_butuh_aset: bool = False) -> List[tuple]:
    out = []
    for kode, d in KATALOG.items():
        if d.get("butuh_aset") and not termasuk_butuh_aset:
            continue
        for t in sorted(d["tingkat"]):
            out.append((kode, t))
    return out


# =============================================================================================
# Resolusi spesifikasi
# =============================================================================================
def _gabung(a: dict, b: dict) -> dict:
    """Gabungkan dua spesifikasi tingkat (untuk E1/E2). Cuaca: 'ubah' digabung, basis/menuju dari yang punya."""
    out = copy.deepcopy(a)
    for k, v in b.items():
        if k == "cuaca" and "cuaca" in out:
            ca, cb = out["cuaca"], v
            c = dict(ca)
            for kk in ("menuju", "f"):
                if kk in cb:
                    c[kk] = cb[kk]
            c["ubah"] = dict(ca.get("ubah", {}), **cb.get("ubah", {}))
            out["cuaca"] = c
        elif k == "korupsi" and "korupsi" in out:
            out["korupsi"] = dict(out["korupsi"], **v)
        elif k == "tata_letak" and "tata_letak" in out:
            out["tata_letak"] = dict(out["tata_letak"], **v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def spesifikasi_tingkat(kode: str, tingkat: int) -> dict:
    if kode not in KATALOG:
        raise KeyError("kode skenario tidak dikenal: %s (ada: %s)" % (kode, ", ".join(KATALOG)))
    d = KATALOG[kode]
    if d.get("butuh_aset"):
        raise NotImplementedError("%s butuh aset lubang baru yang belum dibuat" % kode)
    if tingkat not in d["tingkat"]:
        raise KeyError("%s tidak punya tingkat %s (ada: %s)" % (kode, tingkat, sorted(d["tingkat"])))
    if "gabungan" in d:
        out = {}
        for sub in d["gabungan"]:
            out = _gabung(out, spesifikasi_tingkat(sub, tingkat))
        return out
    return copy.deepcopy(d["tingkat"][tingkat])


def resolusi(kode: str, tingkat: int, seed: int, mode: str = "konstan", backend: str = "grid",
             segmen: Optional[dict] = None, jarak_rampa_m: float = 20.0,
             jendela_onset: tuple = (0.30, 0.55), varian_aset: Optional[List[VarianAset]] = None) -> dict:
    """(kode, tingkat, seed, mode) -> spesifikasi episode lengkap (masih simbolik untuk cuaca).

    mode 'konstan' : kondisi target berlaku sejak awal.
    mode 'transisi': kondisi nominal (cuaca ID-0 seed ini) sampai x_onset, lalu rampa ke target.
    """
    if mode not in ("konstan", "transisi"):
        raise ValueError("mode harus 'konstan' atau 'transisi'")
    d = KATALOG[kode]
    tk = spesifikasi_tingkat(kode, tingkat)
    if mode == "transisi" and not d.get("transisi_bisa", False):
        raise ValueError("%s tidak punya mode transisi (kondisinya konfigurasi, bukan perubahan lingkungan)" % kode)
    wajib = tk.get("backend_wajib")
    if wajib and wajib != backend:
        raise ValueError("%s tingkat %d butuh backend '%s' (sekarang '%s')" % (kode, tingkat, wajib, backend))

    # --- tata letak (berpasangan: tidak bergantung kode skenario) ---
    seg = dict(segmen or {})
    k = KonfigTataLetak(**{kk: (tuple(v) if isinstance(v, list) else v) for kk, v in seg.items()
                           if kk in KonfigTataLetak.__dataclass_fields__})
    k = k.salin(**TL_ID0)
    if varian_aset:
        k = k.salin(varian_aset=tuple(varian_aset))
    if "tata_letak" in tk:
        k = k.salin(**tk["tata_letak"])

    # --- cuaca: basis ID-0 dipilih per seed, dipakai juga sebagai kondisi awal mode transisi ---
    rng_c = RNG(turunkan_seed(seed, "cuaca"))
    basis_id0 = rng_c.pilih(["ClearNoon", "CloudyNoon"])
    cuaca_target = copy.deepcopy(tk.get("cuaca", dict(basis=["ClearNoon", "CloudyNoon"])))
    if isinstance(cuaca_target.get("basis"), list):
        cuaca_target["basis"] = basis_id0
    cuaca_awal = dict(basis=basis_id0)

    spawn = dict(OFFSET_ID0)
    spawn.update(tk.get("spawn", {}))
    spawn.update(_offset_spawn(seed, spawn))

    korupsi = tk.get("korupsi")
    spec = dict(
        kode=kode, tingkat=tingkat, seed=seed, mode=mode, backend=backend,
        kelompok=d["kelompok"], ket=d["ket"],
        konfig_tata_letak=k,
        cuaca_awal=cuaca_awal if mode == "transisi" else cuaca_target,
        cuaca_target=cuaca_target,
        lampu=tk.get("lampu"),
        korupsi=korupsi,
        seed_korupsi=turunkan_seed(seed, "korupsi"),
        kecepatan=tk.get("kecepatan"),
        kendaraan=tk.get("kendaraan", "vehicle.micro.microlino"),
        spawn=spawn,
        x_finis=k.x_finis,
        transisi=None,
    )
    if mode == "transisi":
        rng_o = RNG(turunkan_seed(seed, "onset"))
        L = k.x_selesai - k.x_mulai
        x_on = k.x_mulai + rng_o.uniform(jendela_onset[0] * L, jendela_onset[1] * L)
        spec["transisi"] = dict(x_onset=round(x_on, 3), jarak_rampa_m=float(jarak_rampa_m))
    return spec


def _offset_spawn(seed: int, sp: dict) -> dict:
    """Offset awal aktual. Tanpa pita (ID-0 dll.): PERSIS rumus CarlaEnv Dika [#19],
    random.Random(seed).uniform(-maks, maks) untuk x lalu y, supaya sama dengan baseline #21."""
    import random as _random
    if "offset_y_min" not in sp and "heading_min" not in sp:
        r = _random.Random(int(seed))
        ox = r.uniform(-sp["offset_x"], sp["offset_x"])
        oy = r.uniform(-sp["offset_y"], sp["offset_y"])
        return dict(offset_x_aktual=ox, offset_y_aktual=oy, heading_deg_aktual=0.0)
    rng = RNG(turunkan_seed(seed, "spawn_pita"))
    ox = rng.uniform(-sp["offset_x"], sp["offset_x"])
    tanda_y = 1.0 if rng.random() < 0.5 else -1.0
    oy = tanda_y * rng.uniform(sp.get("offset_y_min", 0.0), sp["offset_y"])
    tanda_h = 1.0 if rng.random() < 0.5 else -1.0
    h = tanda_h * rng.uniform(sp.get("heading_min", 0.0), sp.get("heading_deg", 0.0))
    return dict(offset_x_aktual=round(ox, 4), offset_y_aktual=round(oy, 4), heading_deg_aktual=round(h, 4))


def spesifikasi_ke_json(spec: dict) -> dict:
    out = dict(spec)
    out["konfig_tata_letak"] = spec["konfig_tata_letak"].ke_dict()
    return out


# =============================================================================================
# Transisi
# =============================================================================================
def faktor_transisi(x: float, transisi: Optional[dict]) -> float:
    """0 = nominal, 1 = kondisi target penuh. Tanpa transisi (mode konstan) selalu 1."""
    if not transisi:
        return 1.0
    r = transisi["jarak_rampa_m"]
    if r <= 0:
        return 1.0 if x >= transisi["x_onset"] else 0.0
    return float(min(1.0, max(0.0, (x - transisi["x_onset"]) / r)))


PARAM_CUACA = ["cloudiness", "precipitation", "precipitation_deposits", "wind_intensity",
               "sun_azimuth_angle", "sun_altitude_angle", "fog_density", "fog_distance", "wetness",
               "fog_falloff", "scattering_intensity", "mie_scattering_scale", "rayleigh_scattering_scale",
               "dust_storm"]


def interpolasi_cuaca(a: Dict[str, float], b: Dict[str, float], f: float) -> Dict[str, float]:
    """Interpolasi linear parameter cuaca (dict angka). Azimut lewat jalur terpendek di lingkaran."""
    out = {}
    for k in a:
        if k not in b:
            out[k] = a[k]
            continue
        if k == "sun_azimuth_angle":
            d = ((b[k] - a[k] + 180.0) % 360.0) - 180.0
            out[k] = (a[k] + f * d) % 360.0
        else:
            out[k] = a[k] + f * (b[k] - a[k])
    return out


def cuaca_angka(simbolik: dict, preset: Dict[str, Dict[str, float]], kalibrasi: Optional[dict] = None) -> Dict[str, float]:
    """Spesifikasi cuaca simbolik -> dict angka. preset: {nama: dict angka} (dibaca dari carla di env)."""
    base = dict(preset[simbolik["basis"]])
    if "menuju" in simbolik:
        base = interpolasi_cuaca(base, preset[simbolik["menuju"]], float(simbolik.get("f", 1.0)))
    for k, v in simbolik.get("ubah", {}).items():
        if v == "AZIMUT_MENGHADAP_KAMERA":
            if not kalibrasi or "azimut_menghadap_kamera" not in kalibrasi:
                raise RuntimeError("A4 butuh 'azimut_menghadap_kamera' di kalibrasi_lingkungan.json "
                                   "(jalankan: python uji_carla_24_25.py azimut)")
            v = float(kalibrasi["azimut_menghadap_kamera"])
        base[k] = float(v)
    return base


def _tabel_kendaraan(kalibrasi: dict, kendaraan: str):
    per = (kalibrasi or {}).get("throttle_ke_kmh_per_kendaraan", {})
    if kendaraan in per:
        return per[kendaraan]
    if kendaraan == MICROLINO and "throttle_ke_kmh" in (kalibrasi or {}):
        return kalibrasi["throttle_ke_kmh"]
    return None


def throttle_untuk(kecepatan: Optional[dict], kalibrasi: Optional[dict], kendaraan: str = None) -> float:
    """Throttle konstan untuk target kecepatan, dari tabel kalibrasi kendaraan itu (interpolasi linear).
    target_kmh = "ACUAN_MICROLINO" -> kecepatan tunak Microlino pada throttle Dika 0,3."""
    kendaraan = kendaraan or MICROLINO
    if not kecepatan:
        return THROTTLE_DIKA
    tab = _tabel_kendaraan(kalibrasi, kendaraan)
    if tab is None:
        raise RuntimeError("Butuh tabel kalibrasi throttle untuk %s di kalibrasi_lingkungan.json "
                           "(jalankan: python uji_carla_24_25.py kecepatan --kendaraan %s)" % (kendaraan, kendaraan))
    v = kecepatan["target_kmh"]
    if v == "ACUAN_MICROLINO":
        tm = _tabel_kendaraan(kalibrasi, MICROLINO)
        if tm is None:
            raise RuntimeError("Butuh tabel kalibrasi Microlino (python uji_carla_24_25.py kecepatan)")
        pm = sorted((float(t), float(k)) for t, k in tm.items())
        v = float(np.interp(THROTTLE_DIKA, [t for t, _ in pm], [k for _, k in pm]))
    v = float(v)
    pasangan = sorted((float(t), float(k)) for t, k in tab.items())
    ts, vs = [t for t, _ in pasangan], [k for _, k in pasangan]
    if not (min(vs) <= v <= max(vs)):
        raise RuntimeError("target %.1f km/jam di luar tabel kalibrasi %s (%.1f-%.1f)" % (v, kendaraan, min(vs), max(vs)))
    if any(b <= a for a, b in zip(vs, vs[1:])):
        raise RuntimeError("tabel kalibrasi %s tidak naik monoton: %s" % (kendaraan, tab))
    return float(np.interp(v, vs, ts))


def muat_kalibrasi(path: str = KALIBRASI_DEFAULT) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


# =============================================================================================
# Korupsi citra (A5, A6) — diterapkan HANYA pada citra yang masuk YOLO
# =============================================================================================
class Korupsi:
    """Deterministik per episode (seed) dan per langkah. Intensitas diskalakan faktor f in [0,1]."""

    def __init__(self, param: Optional[dict], seed: int, ukuran=(640, 640)):
        self.param = dict(param or {})
        self.seed = int(seed)
        self.aktif = bool(self.param)
        self._tetes = None
        if self.param.get("tetes_n"):
            self._tetes = self._buat_tetes(int(self.param["tetes_n"]), ukuran)

    def _buat_tetes(self, n, ukuran):
        """Peta tetes air statis: tiap tetes = lensa kecil (blur kuat + sedikit terang) berbentuk elips."""
        h, w = ukuran
        rng = np.random.default_rng(self.seed)
        mask = np.zeros((h, w), np.float32)
        yy, xx = np.mgrid[0:h, 0:w]
        for _ in range(n):
            cx, cy = rng.uniform(0, w), rng.uniform(0, h)
            rx, ry = rng.uniform(12, 40), rng.uniform(12, 40) * rng.uniform(1.0, 1.6)
            d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
            mask = np.maximum(mask, np.clip(1.0 - d, 0.0, 1.0) ** 0.5)
        return mask

    def terapkan(self, img: np.ndarray, f: float, langkah: int) -> np.ndarray:
        if not self.aktif or f <= 0.0:
            return img
        import cv2
        out = img
        p = self.param
        if p.get("blur_sigma"):
            s = float(p["blur_sigma"]) * f
            if s > 0.05:
                out = cv2.GaussianBlur(out, (0, 0), s)
        if self._tetes is not None:
            m = (self._tetes * f)[..., None]
            buram = cv2.GaussianBlur(out, (0, 0), 9.0)
            terang = np.clip(buram.astype(np.float32) * 1.08 + 6.0, 0, 255)
            out = (out.astype(np.float32) * (1 - m) + terang * m).astype(np.uint8)
        if p.get("derau_sigma"):
            rng = np.random.default_rng((self.seed * 1000003 + langkah) % (2 ** 63))
            n = rng.normal(0.0, float(p["derau_sigma"]) * f, out.shape).astype(np.float32)
            out = np.clip(out.astype(np.float32) + n, 0, 255).astype(np.uint8)
        if p.get("jpeg_q"):
            q = int(round(95 - (95 - int(p["jpeg_q"])) * f))
            ok, buf = cv2.imencode(".jpg", np.ascontiguousarray(out), [int(cv2.IMWRITE_JPEG_QUALITY), q])
            if ok:
                out = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return np.ascontiguousarray(out)


# =============================================================================================
# CLI: cek semua kondisi bisa dibangkitkan dari seed (tanpa CARLA)
# =============================================================================================
def _main():
    import argparse
    from generator_tata_letak import buat_tata_letak, muat_slot_grid
    ap = argparse.ArgumentParser(description="Cek semua kondisi x tingkat x mode bisa dibangkitkan dari seed")
    ap.add_argument("--seed", type=int, nargs="+", default=list(range(30)))
    ap.add_argument("--backend", nargs="+", default=["grid", "spawn"])
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    slot = muat_slot_grid()
    baris = []
    for kode, t in daftar_kondisi():
        for mode in ("konstan", "transisi"):
            for be in a.backend:
                n_ok, alasan, ns = 0, "", []
                for s in a.seed:
                    try:
                        sp = resolusi(kode, t, s, mode, be)
                        tl = buat_tata_letak(s, sp["konfig_tata_letak"], be, slot)
                        if tl.n == 0:
                            raise ValueError("tata letak kosong")
                        n_ok += 1
                        ns.append(tl.n)
                    except (ValueError, NotImplementedError) as e:
                        alasan = str(e)
                        break
                status = "OK" if n_ok == len(a.seed) else "-"
                baris.append(dict(kode=kode, tingkat=t, mode=mode, backend=be, status=status,
                                  n_lubang="%d-%d" % (min(ns), max(ns)) if ns else "", alasan=alasan if status != "OK" else ""))
    lebar = "%-4s %-2s %-9s %-6s %-3s %-7s %s"
    print(lebar % ("kode", "t", "mode", "backend", "ok", "n", "keterangan"))
    for b in baris:
        if "tidak punya mode transisi" in b["alasan"]:
            continue                       # kondisi konfigurasi memang tidak punya mode transisi
        print(lebar % (b["kode"], b["tingkat"], b["mode"], b["backend"], b["status"], b["n_lubang"], b["alasan"]))
    n_ok = sum(1 for b in baris if b["status"] == "OK")
    print("\n%d kombinasi bisa dibangkitkan untuk %d seed; %d tidak berlaku (lihat keterangan)." % (n_ok, len(a.seed), len(baris) - n_ok))
    for kode, d in KATALOG.items():
        if d.get("butuh_aset"):
            print("BELUM: %s (%s) butuh aset lubang baru" % (kode, d["ket"]))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(baris, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    _main()
