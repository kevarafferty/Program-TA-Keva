"""
generator_tata_letak.py — [#24] Generator tata letak lubang prosedural untuk peta train_fix.

Satu seed -> satu tata letak lubang -> satu berkas ground truth (GT) berformat sama dengan
pothole_gt.json Dika, sehingga carla_env.PotholeGroundTruth, pelabel roda (02_pelabel_roda) dan
analisis_baseline.py bisa langsung memakainya.

Dua backend (opsi (a) dan (b) di §2.1.2 proposal):

  grid  : 40 objek lubang yang SUDAH ADA di peta train_fix (GT v2, alat_carla/pothole_gt_v2_lengkap.json)
          dinyalakan/dimatikan per episode dengan world.enable_environment_objects().
          Tidak perlu build ulang. Posisi terbatas pada slot yang ada (19 slot di segmen Dika,
          2 lajur, jarak antar slot 8,7–15 m, semuanya High, ukuran 2 x 3 m).
  spawn : lubang dimunculkan di posisi bebas lewat blueprint 'static.prop.mesh' (atribut mesh_path).
          Butuh aset StaticMesh lubang (Plane + material highh, skala 2x3 sudah "dipanggang",
          tanpa collision) yang ikut ter-package. Lihat README.md bagian Langkah C.

Modul ini TIDAK meng-import carla di tingkat modul, supaya pembuatan tata letak, uji unit,
dan pemeriksaan "semua kondisi bisa dibangkitkan dari seed" bisa jalan tanpa simulator.
Bagian yang menyentuh CARLA ada di kelas BackendGrid / BackendSpawn (dipanggil dari env_skenario.py).

Reprodusibilitas: semua angka acak berasal dari random.Random(seed_turunan).random() saja
(Mersenne Twister, identik di Python 3.8 laptop dan 3.13 cloud). Tidak memakai random.sample,
random.choice, atau randrange karena implementasinya pernah berubah antar versi Python.

Konvensi koordinat = CARLA: x maju (arah mobil Dika), y ke kanan. Lajur spawn Dika y = 250,5 (kanan),
lajur kiri y = 247,2. Tepi jalan y 245,55–252,55 (carla_env.py).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

DIR = os.path.dirname(os.path.abspath(__file__))
GT_V2_DEFAULT = os.path.normpath(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_lengkap.json"))

# --- konstanta peta train_fix (dari carla_env.py Dika dan GT v2) -------------------------------
X_SPAWN_DIKA = -299.5
X_FINIS_DIKA = -27.0
ROAD_Y_MIN = 245.55
ROAD_Y_MAX = 252.55
LAJUR_Y = (250.5, 247.2)            # kanan (spawn), kiri
Z_LUBANG = 0.039                    # tinggi plane lubang di peta
LEBAR_MOBIL_MICROLINO = 2 * 0.7405  # bbox terukur
SEV_ANGKA = {"Low": 0.3, "Medium": 0.6, "High": 0.9}


# =============================================================================================
# RNG portabel
# =============================================================================================
def turunkan_seed(seed: int, komponen: str) -> int:
    """Seed independen per komponen (tata_letak, cuaca, korupsi, onset, ...) dari satu seed episode."""
    h = hashlib.sha256(("%d|%s" % (int(seed), komponen)).encode("utf-8")).hexdigest()
    return int(h[:12], 16)


class RNG:
    """Pembungkus random.Random yang hanya memakai .random() (portabel antar versi Python)."""

    def __init__(self, seed: int):
        self._r = random.Random(int(seed))

    def random(self) -> float:
        return self._r.random()

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self._r.random()

    def randint(self, a: int, b: int) -> int:
        """Inklusif di kedua ujung."""
        return min(b, a + int(self._r.random() * (b - a + 1)))

    def pilih(self, xs: Sequence):
        return xs[min(len(xs) - 1, int(self._r.random() * len(xs)))]

    def acak_urutan(self, xs: Sequence) -> list:
        xs = list(xs)
        for i in range(len(xs) - 1, 0, -1):          # Fisher–Yates
            j = min(i, int(self._r.random() * (i + 1)))
            xs[i], xs[j] = xs[j], xs[i]
        return xs


# =============================================================================================
# Konfigurasi
# =============================================================================================
@dataclass
class VarianAset:
    """Satu jenis lubang yang bisa dimunculkan backend spawn."""
    nama: str = "high_2x3"
    mesh_path: str = "/Game/Carla/Static/Lubang/SM_Lubang_High_2x3.SM_Lubang_High_2x3"
    extent_x: float = 1.0
    extent_y: float = 1.5
    severity_label: str = "High"
    bobot: float = 1.0


@dataclass
class KonfigTataLetak:
    # ruas tempat lubang boleh diletakkan (lubang pertama Dika x = -285,2; terakhir -34,9)
    x_mulai: float = -287.0
    x_selesai: float = -33.0
    x_finis: float = X_FINIS_DIKA          # dipakai env sebagai finish_x_threshold
    # kerapatan: jumlah lubang per 100 m, diambil seragam dari rentang ini
    kerapatan_per_100m: Tuple[float, float] = (3.0, 6.0)
    n_min: int = 3
    jarak_min_m: float = 10.0              # jarak longitudinal minimum antar dua lubang (lajur mana pun)
    jarak_min_selajur_m: float = 10.0      # jarak minimum antar lubang di lajur yang sama
    pola: str = "acak"                     # acak | zigzag | semua | pasangan_rapat | klaster
    n_pasangan_rapat: int = 2              # untuk pola pasangan_rapat
    jarak_pasangan_m: Tuple[float, float] = (4.0, 8.0)   # spawn: jarak pusat pasangan rapat
    lajur_y: Tuple[float, ...] = LAJUR_Y
    jitter_lateral_m: float = 0.0          # spawn: geseran acak pusat lubang dari tengah lajur
    severity_boleh: Tuple[str, ...] = ("High",)
    hanya_ukuran_standar: bool = True      # grid: abaikan objek 'Low' selebar 7–9 m (retak melintang)
    jamin_lolos: bool = True               # tolak tata letak yang tidak menyisakan celah selebar mobil
    celah_min_m: float = LEBAR_MOBIL_MICROLINO + 0.12
    maks_percobaan: int = 200
    varian_aset: Tuple[VarianAset, ...] = (VarianAset(),)

    def salin(self, **ubah) -> "KonfigTataLetak":
        k = copy.deepcopy(self)
        for a, b in ubah.items():
            if not hasattr(k, a):
                raise KeyError("KonfigTataLetak tidak punya field '%s'" % a)
            if isinstance(b, list):
                b = tuple(b)
            setattr(k, a, b)
        return k

    def ke_dict(self) -> dict:
        d = asdict(self)
        return d


# =============================================================================================
# Hasil
# =============================================================================================
@dataclass
class TataLetak:
    seed: int
    backend: str
    konfig: dict
    lubang: List[dict]
    n_target: int
    catatan: List[str] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.lubang)

    def ke_gt(self) -> List[dict]:
        """Daftar entri dengan field wajib PotholeGroundTruth Dika (+ field tambahan)."""
        return [dict(l) for l in self.lubang]

    def simpan_gt(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.ke_gt(), f, indent=1, ensure_ascii=False)
        return path

    def ringkas(self) -> dict:
        xs = sorted(l["x"] for l in self.lubang)
        gaps = [b - a for a, b in zip(xs, xs[1:])]
        return dict(seed=self.seed, backend=self.backend, n=self.n, n_target=self.n_target,
                    jarak_min_m=round(min(gaps), 3) if gaps else None,
                    celah_bebas_min_m=round(celah_bebas_min(self.lubang), 3),
                    lajur=[sum(1 for l in self.lubang if abs(l["y"] - y) < 1.0) for y in LAJUR_Y],
                    id=[l["id"] for l in self.lubang], catatan=self.catatan)

    def sidik(self) -> str:
        """Hash pendek isi tata letak (untuk uji determinisme lintas mesin)."""
        s = json.dumps([[l["id"], round(l["x"], 3), round(l["y"], 3), l["severity_label"]] for l in self.lubang])
        return hashlib.sha256(s.encode()).hexdigest()[:16]


# =============================================================================================
# Geometri bantu
# =============================================================================================
def celah_bebas_min(lubang: Sequence[dict], setengah_panjang_mobil: float = 1.104,
                    langkah_m: float = 0.25) -> float:
    """Celah lateral bebas TERLEBAR, diminimumkan sepanjang jalan.

    Pada tiap potongan x, lubang yang rentang x-nya (diperlebar setengah panjang mobil) menutupi
    potongan itu memblokir rentang y-nya. Hasil = min_x (celah bebas terlebar di jalan).
    Nilai < lebar mobil berarti ada potongan jalan yang mustahil dilewati tanpa kontak.
    Kasar (mengabaikan kemampuan belok), tapi cukup untuk menolak tata letak yang 'menutup jalan'.
    """
    if not lubang:
        return ROAD_Y_MAX - ROAD_Y_MIN
    xs0 = min(l["x"] - l["extent_x"] for l in lubang) - setengah_panjang_mobil
    xs1 = max(l["x"] + l["extent_x"] for l in lubang) + setengah_panjang_mobil
    terburuk = ROAD_Y_MAX - ROAD_Y_MIN
    n = int(math.ceil((xs1 - xs0) / langkah_m)) + 1
    for i in range(n):
        x = xs0 + i * langkah_m
        blok = sorted((l["y"] - l["extent_y"], l["y"] + l["extent_y"]) for l in lubang
                      if abs(x - l["x"]) <= l["extent_x"] + setengah_panjang_mobil)
        if not blok:
            continue
        terlebar, kiri = 0.0, ROAD_Y_MIN
        for a, b in blok:
            terlebar = max(terlebar, a - kiri)
            kiri = max(kiri, b)
        terlebar = max(terlebar, ROAD_Y_MAX - kiri)
        terburuk = min(terburuk, terlebar)
    return terburuk


def _lajur_dari_y(y: float, lajur_y: Sequence[float]) -> int:
    return min(range(len(lajur_y)), key=lambda i: abs(lajur_y[i] - y))


def _cocok_jarak(kandidat: dict, terpilih: Sequence[dict], k: KonfigTataLetak, abaikan_min: bool = False) -> bool:
    for t in terpilih:
        dx = abs(kandidat["x"] - t["x"])
        if not abaikan_min and dx < k.jarak_min_m - 1e-9:
            return False
        if abs(kandidat["y"] - t["y"]) < 1.0 and dx < k.jarak_min_selajur_m - 1e-9:
            return False
    return True


def _n_target(rng: RNG, k: KonfigTataLetak) -> int:
    panjang = k.x_selesai - k.x_mulai
    lo, hi = k.kerapatan_per_100m
    return max(k.n_min, int(round(rng.uniform(lo, hi) * panjang / 100.0)))


# =============================================================================================
# Slot grid (objek lubang yang ada di peta)
# =============================================================================================
def muat_slot_grid(path: str = GT_V2_DEFAULT) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out = []
    for e in raw:
        d = dict(e)
        d.setdefault("severity", SEV_ANGKA.get(d.get("severity_label", "High"), 0.9))
        out.append(d)
    return out


def _slot_tersedia(slot: Sequence[dict], k: KonfigTataLetak) -> List[dict]:
    out = []
    for s in slot:
        if not (k.x_mulai <= s["x"] <= k.x_selesai):
            continue
        if s.get("severity_label", "High") not in k.severity_boleh:
            continue
        if k.hanya_ukuran_standar and s["extent_y"] > 2.0:
            continue
        out.append(s)
    return sorted(out, key=lambda s: s["x"])


def _entri_dari_slot(s: dict) -> dict:
    keys = ["id", "name", "x", "y", "z", "yaw", "extent_x", "extent_y", "extent_z", "severity", "severity_label"]
    d = {kk: s[kk] for kk in keys if kk in s}
    d["sumber"] = "grid"
    d["slot"] = s["id"]
    return d


# =============================================================================================
# Generator
# =============================================================================================
def buat_tata_letak(seed: int, konfig: Optional[KonfigTataLetak] = None, backend: str = "grid",
                    slot: Optional[Sequence[dict]] = None) -> TataLetak:
    """Seed -> TataLetak. Deterministik: seed dan konfig sama -> hasil identik."""
    k = konfig or KonfigTataLetak()
    rng = RNG(turunkan_seed(seed, "tata_letak"))
    if backend == "grid":
        return _buat_grid(seed, k, rng, slot if slot is not None else muat_slot_grid())
    if backend == "spawn":
        return _buat_spawn(seed, k, rng)
    raise ValueError("backend harus 'grid' atau 'spawn', bukan %r" % backend)


def _buat_grid(seed: int, k: KonfigTataLetak, rng: RNG, slot: Sequence[dict]) -> TataLetak:
    tersedia = _slot_tersedia(slot, k)
    catatan = []
    if not tersedia:
        raise ValueError("Tidak ada slot grid di x %.1f..%.1f dengan severity %s" % (k.x_mulai, k.x_selesai, k.severity_boleh))

    if k.pola == "semua":
        pilih = list(tersedia)
        n_target = len(pilih)
    elif k.pola == "pasangan_rapat":
        # pasangan slot beda lajur yang paling dekat (8,7–9,1 m di segmen Dika), ditambah lubang jarang
        pasang = []
        for a, b in zip(tersedia, tersedia[1:]):
            if abs(a["y"] - b["y"]) > 1.0:
                pasang.append((b["x"] - a["x"], a, b))
        pasang.sort(key=lambda t: t[0])
        rapat = [p for p in pasang if p[0] < k.jarak_min_m]
        if len(rapat) < k.n_pasangan_rapat:
            catatan.append("hanya %d pasangan rapat (< %.1f m) tersedia di grid" % (len(rapat), k.jarak_min_m))
        rapat = rng.acak_urutan(rapat)[:k.n_pasangan_rapat]
        pilih = []
        for _, a, b in rapat:
            if _cocok_jarak(a, pilih, k) and _cocok_jarak(b, pilih, k):
                pilih += [a, b]
        n_target = _n_target(rng, k)
        for s in rng.acak_urutan(tersedia):
            if len(pilih) >= n_target:
                break
            if s not in pilih and _cocok_jarak(s, pilih, k):
                pilih.append(s)
    elif k.pola in ("acak", "zigzag", "klaster"):
        if k.pola == "klaster":
            catatan.append("pola klaster butuh posisi bebas; di grid diperlakukan sebagai 'acak'")
        n_target = min(_n_target(rng, k), len(tersedia))
        terbaik = []
        for _ in range(k.maks_percobaan):
            pilih = []
            for s in rng.acak_urutan(tersedia):
                if len(pilih) >= n_target:
                    break
                if _cocok_jarak(s, pilih, k):
                    pilih.append(s)
            if k.pola == "zigzag":
                pilih = _paksa_zigzag(pilih, k.lajur_y)
            if len(pilih) > len(terbaik):
                terbaik = pilih
            if len(pilih) >= n_target:
                break
        pilih = terbaik
        if len(pilih) < n_target:
            catatan.append("n %d < target %d (dibatasi slot/jarak minimum)" % (len(pilih), n_target))
    else:
        raise ValueError("pola tidak dikenal: %r" % k.pola)

    lubang = [_entri_dari_slot(s) for s in sorted(pilih, key=lambda s: s["x"])]
    if k.jamin_lolos and celah_bebas_min(lubang) < k.celah_min_m:
        catatan.append("PERINGATAN: celah bebas %.2f m < %.2f m" % (celah_bebas_min(lubang), k.celah_min_m))
    return TataLetak(seed=seed, backend="grid", konfig=k.ke_dict(), lubang=lubang, n_target=n_target, catatan=catatan)


def _paksa_zigzag(pilih: Sequence[dict], lajur_y: Sequence[float]) -> List[dict]:
    out = []
    for s in sorted(pilih, key=lambda s: s["x"]):
        if out and _lajur_dari_y(out[-1]["y"], lajur_y) == _lajur_dari_y(s["y"], lajur_y):
            continue
        out.append(s)
    return out


def _pilih_varian(rng: RNG, k: KonfigTataLetak) -> VarianAset:
    vs = [v for v in k.varian_aset if v.severity_label in k.severity_boleh] or list(k.varian_aset)
    tot = sum(v.bobot for v in vs)
    u, acc = rng.random() * tot, 0.0
    for v in vs:
        acc += v.bobot
        if u <= acc:
            return v
    return vs[-1]


def _entri_spawn(i: int, x: float, y: float, v: VarianAset) -> dict:
    return dict(id="sp_%04d" % i, name=v.nama, x=round(x, 3), y=round(y, 3), z=Z_LUBANG, yaw=0.0,
                extent_x=v.extent_x, extent_y=v.extent_y, extent_z=0.05,
                severity=SEV_ANGKA.get(v.severity_label, 0.9), severity_label=v.severity_label,
                sumber="spawn", mesh_path=v.mesh_path)


def _buat_spawn(seed: int, k: KonfigTataLetak, rng: RNG) -> TataLetak:
    catatan = []
    n_target = _n_target(rng, k)
    nl = len(k.lajur_y)
    terbaik: List[dict] = []
    for _ in range(k.maks_percobaan):
        lub: List[dict] = []
        lajur_prev = rng.randint(0, nl - 1)
        if k.pola == "semua":
            raise ValueError("pola 'semua' hanya untuk grid (tata letak asli Dika)")
        if k.pola == "klaster":
            # klaster (C1): kelompok rapat yang mengisi SEMUA lajur secara selang-seling
            # (jarak antar lubang dalam kelompok = jarak_pasangan_m), dipisah ruas kosong.
            # Selang-seling menjaga jalan tetap bisa dilewati dengan zig-zag (cek celah di bawah).
            x = k.x_mulai + rng.uniform(0.0, k.jarak_min_m)
            while len(lub) < n_target and x <= k.x_selesai:
                urutan = rng.acak_urutan(range(nl))
                for j in urutan:
                    if len(lub) >= n_target or x > k.x_selesai:
                        break
                    yy = k.lajur_y[j] + rng.uniform(-k.jitter_lateral_m, k.jitter_lateral_m)
                    lub.append(_entri_spawn(len(lub), x, yy, _pilih_varian(rng, k)))
                    x += rng.uniform(*k.jarak_pasangan_m)
                x += rng.uniform(k.jarak_min_m, 2.5 * k.jarak_min_m)   # ruas kosong antar kelompok
        else:
            # proses berurutan: jarak antar lubang ~ seragam di sekitar panjang/n
            panjang = k.x_selesai - k.x_mulai
            rata = panjang / max(1, n_target)
            x = k.x_mulai + rng.uniform(0.0, max(0.0, rata - k.jarak_min_m))
            n_pasang_sisa = k.n_pasangan_rapat if k.pola == "pasangan_rapat" else 0
            while x <= k.x_selesai and len(lub) < n_target:
                if k.pola == "zigzag":
                    j = (lajur_prev + 1) % nl
                else:
                    j = rng.randint(0, nl - 1)
                v = _pilih_varian(rng, k)
                y = k.lajur_y[j] + rng.uniform(-k.jitter_lateral_m, k.jitter_lateral_m)
                e = _entri_spawn(len(lub), x, y, v)
                if _cocok_jarak(e, lub, k):
                    lub.append(e)
                    lajur_prev = j
                    if n_pasang_sisa > 0 and len(lub) < n_target and rng.random() < 0.5:
                        # lubang kedua di lajur LAIN, dekat sekali (D1)
                        j2 = (j + 1 + rng.randint(0, nl - 2)) % nl if nl > 1 else j
                        x2 = x + rng.uniform(*k.jarak_pasangan_m)
                        y2 = k.lajur_y[j2] + rng.uniform(-k.jitter_lateral_m, k.jitter_lateral_m)
                        e2 = _entri_spawn(len(lub), x2, y2, _pilih_varian(rng, k))
                        if x2 <= k.x_selesai and _cocok_jarak(e2, lub[:-1], k):
                            lub.append(e2)
                            lajur_prev = j2
                            n_pasang_sisa -= 1
                            x = x2
                lo = max(k.jarak_min_m, 0.5 * rata)
                x += rng.uniform(lo, max(lo, 1.5 * rata))
        lub.sort(key=lambda e: e["x"])
        for i, e in enumerate(lub):
            e["id"] = "sp_%04d" % i
        lolos = (not k.jamin_lolos) or celah_bebas_min(lub) >= k.celah_min_m
        if lolos and len(lub) > len(terbaik):
            terbaik = lub
        if lolos and len(lub) >= n_target:
            break
    if len(terbaik) < n_target:
        catatan.append("n %d < target %d" % (len(terbaik), n_target))
    return TataLetak(seed=seed, backend="spawn", konfig=k.ke_dict(), lubang=terbaik, n_target=n_target, catatan=catatan)


# =============================================================================================
# Backend CARLA
# =============================================================================================
class BackendGrid:
    """Menyalakan/mematikan objek lubang peta per episode (enable_environment_objects).

    Pencocokan slot GT -> objek lingkungan memakai POSISI (toleransi 0,5 m), bukan nama, karena
    nama di build Shipping berbeda dari editor (mis. 'hole_low10_SM_0'). Satu slot bisa terdiri
    dari lebih dari satu objek lingkungan (komponen mesh); semuanya ikut di-toggle.
    """

    def __init__(self, world, carla_mod, slot: Optional[Sequence[dict]] = None, toleransi_m: float = 0.5):
        self.world = world
        self.carla = carla_mod
        self.slot = list(slot) if slot is not None else muat_slot_grid()
        semua = list(world.get_environment_objects(carla_mod.CityObjectLabel.Any))
        self.peta: Dict[str, List[int]] = {}
        self.nama: Dict[str, List[str]] = {}
        for s in self.slot:
            ids, nm = [], []
            for o in semua:
                L = o.transform.location
                if abs(L.x - s["x"]) < toleransi_m and abs(L.y - s["y"]) < toleransi_m and abs(L.z - s["z"]) < toleransi_m:
                    ids.append(int(o.id))
                    nm.append(o.name)
            self.peta[s["id"]] = ids
            self.nama[s["id"]] = nm
        self.tidak_ketemu = [sid for sid, ids in self.peta.items() if not ids]
        self.aktif: Optional[set] = None

    def ringkas(self) -> dict:
        return dict(slot=len(self.slot), slot_ketemu=len(self.slot) - len(self.tidak_ketemu),
                    tidak_ketemu=self.tidak_ketemu,
                    objek_per_slot=sorted({len(v) for v in self.peta.values()}))

    def _toggle(self, slot_ids, nyala: bool):
        ids = set()
        for sid in slot_ids:
            ids.update(self.peta.get(sid, []))
        if ids:
            self.world.enable_environment_objects(ids, nyala)

    def matikan_semua(self):
        self._toggle(self.peta.keys(), False)
        self.aktif = set()

    def nyalakan_semua(self):
        self._toggle(self.peta.keys(), True)
        self.aktif = set(self.peta.keys())

    def terapkan(self, tl: TataLetak, tick=None) -> dict:
        """Ubah HANYA slot yang statusnya berbeda, dengan tick di antara mati dan nyala.

        [22 Nov] Versi lama mematikan semua lalu langsung menyalakan yang dipilih dalam satu saat;
        di CARLA paket ±40% episode berakhir dengan lubang tak tampak. Status awal setelah load_world
        dianggap semua nyala; kebenarannya dipastikan per episode oleh verifikasi_lubang.py.
        """
        if tl.backend != "grid":
            raise ValueError("BackendGrid hanya untuk tata letak grid")
        mau = {l["slot"] for l in tl.lubang}
        hilang = [s for s in mau if not self.peta.get(s)]
        if hilang:
            raise RuntimeError("Slot %s tidak punya objek lingkungan di peta (jalankan uji_carla_24_25.py slot)" % hilang)
        if self.aktif is None:
            self.aktif = set(self.peta.keys())          # load_world: semua objek peta tampak
        mati = self.aktif - mau
        nyala = mau - self.aktif
        if mati:
            self._toggle(mati, False)
            if tick:
                tick()
        if nyala:
            self._toggle(nyala, True)
            if tick:
                tick()
        self.aktif = set(mau)
        return dict(nyala=sorted(mau), dimatikan=len(mati), dinyalakan=len(nyala))

    def ulang(self, slot_ids, tick=None):
        """Paksa ulang: mati, tick, nyala, tick (dipakai bila verifikasi gagal)."""
        self._toggle(slot_ids, False)
        if tick:
            tick()
        self._toggle(slot_ids, True)
        if tick:
            tick()

    def tutup(self):
        # kembalikan peta seperti semula (semua lubang tampak)
        try:
            self.nyalakan_semua()
        except Exception:
            pass


class BackendSpawn:
    """Memunculkan lubang lewat 'static.prop.mesh'. Lubang peta (grid) dimatikan semua lebih dulu."""

    BP_ID = "static.prop.mesh"

    def __init__(self, world, carla_mod, grid: Optional[BackendGrid] = None):
        self.world = world
        self.carla = carla_mod
        self.grid = grid
        lib = world.get_blueprint_library()
        cocok = list(lib.filter(self.BP_ID))
        if not cocok:
            raise RuntimeError("Blueprint '%s' tidak ada di build ini; pakai backend grid" % self.BP_ID)
        self.bp = cocok[0]
        if not self.bp.has_attribute("mesh_path"):
            raise RuntimeError("'%s' tidak punya atribut mesh_path di build ini" % self.BP_ID)
        self.aktor: List = []
        self.id_aktor: set = set()

    def hapus(self):
        for a in self.aktor:
            try:
                a.destroy()
            except Exception:
                pass
        self.aktor, self.id_aktor = [], set()

    def terapkan(self, tl: TataLetak) -> dict:
        if tl.backend != "spawn":
            raise ValueError("BackendSpawn hanya untuk tata letak spawn")
        if self.grid is not None:
            self.grid.matikan_semua()
        self.hapus()
        gagal = []
        C = self.carla
        for l in tl.lubang:
            self.bp.set_attribute("mesh_path", l["mesh_path"])
            tf = C.Transform(C.Location(x=l["x"], y=l["y"], z=l["z"]), C.Rotation(yaw=l.get("yaw", 0.0)))
            a = self.world.try_spawn_actor(self.bp, tf)
            if a is None:
                gagal.append(l["id"])
            else:
                self.aktor.append(a)
                self.id_aktor.add(int(a.id))
        if gagal:
            self.hapus()
            raise RuntimeError("Gagal memunculkan %d lubang (%s...). Cek mesh_path dan aset ter-package." % (len(gagal), gagal[:3]))
        return dict(dimunculkan=len(self.aktor))

    def tutup(self):
        self.hapus()
        if self.grid is not None:
            self.grid.tutup()


# =============================================================================================
# CLI: pratinjau tanpa CARLA
# =============================================================================================
def _main():
    import argparse
    ap = argparse.ArgumentParser(description="Pratinjau tata letak dari seed (tanpa CARLA)")
    ap.add_argument("--seed", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--backend", default="grid", choices=["grid", "spawn"])
    ap.add_argument("--pola", default="acak")
    ap.add_argument("--kerapatan", type=float, nargs=2, default=None)
    ap.add_argument("--gt", default=GT_V2_DEFAULT)
    ap.add_argument("--simpan", default="", help="folder: tulis gt_seed<k>.json")
    a = ap.parse_args()
    k = KonfigTataLetak(pola=a.pola)
    if a.kerapatan:
        k = k.salin(kerapatan_per_100m=tuple(a.kerapatan))
    slot = muat_slot_grid(a.gt) if a.backend == "grid" else None
    for s in a.seed:
        tl = buat_tata_letak(s, k, a.backend, slot)
        r = tl.ringkas()
        print("seed %d: n=%d (target %d) jarak_min=%s celah_min=%s lajur(kanan,kiri)=%s sidik=%s %s" % (
            s, r["n"], r["n_target"], r["jarak_min_m"], r["celah_bebas_min_m"], r["lajur"], tl.sidik(),
            "; ".join(r["catatan"])))
        if a.simpan:
            tl.simpan_gt(os.path.join(a.simpan, "gt_seed%d.json" % s))


if __name__ == "__main__":
    _main()
