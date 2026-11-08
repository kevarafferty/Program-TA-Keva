"""
kontak_roda.py — Pelabel kontak roda–lubang dan energi pelanggaran berbasis
jejak roda (Bab 2.1.3 dan 2.1.7 proposal, persamaan 7).

Hanya butuh NumPy, jadi bisa dipakai di environment CARLA mana pun.

Konvensi koordinat = CARLA (Unreal, tangan kiri, tampak dari atas):
    x maju, y ke KANAN, yaw (derajat) diukur dari +x ke +y.
    vektor maju  = ( cos yaw, sin yaw)
    vektor kanan = (-sin yaw, cos yaw)

Isi modul
---------
GeometriKendaraan   posisi 4 titik kontak ban relatif terhadap titik asal aktor
Lubang              persegi panjang berotasi (pusat, extent = setengah ukuran, yaw)
jarak_bertanda()    signed distance titik -> lubang (negatif = di dalam lubang)
kontak_per_langkah  apakah ada roda yang menyentuh lubang Medium/High pada tiap langkah
label_horizon()     y_t = 1 jika ada kontak dalam H langkah ke depan (label kegagalan keputusan)
energi_pelanggaran  E_V (persamaan 7) untuk satu lintasan prediksi
rollout_sepeda()    lintasan prediksi model kinematik sepeda untuk sebuah aksi
logika_dika()       tiruan setia penghitung HIT/AVOID di carla_env.py Dika (untuk pembanding)

PERINGATAN: angka geometri bawaan Microlino di bawah adalah ESTIMASI. Ukur nilai
sebenarnya dengan alat_carla/ukur_geometri.py sebelum label dipakai untuk hasil TA.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

DT = 0.05                       # langkah simulasi Dika (mode sinkron)
SEV_BOBOT = {"Low": 0.3, "Medium": 0.6, "High": 0.9}


# ---------------------------------------------------------------------------
# Geometri
# ---------------------------------------------------------------------------
@dataclass
class GeometriKendaraan:
    """Semua dalam meter, relatif terhadap titik asal aktor CARLA (x maju, y kanan)."""
    jarak_sumbu_depan: float = 0.75     # ESTIMASI: titik asal -> poros depan
    jarak_sumbu_belakang: float = 0.72  # ESTIMASI: titik asal -> poros belakang
    lebar_jejak: float = 1.20           # ESTIMASI: jarak antar pusat ban kiri-kanan (track)
    setengah_lebar_ban: float = 0.075   # ESTIMASI: r_w pada persamaan 7 (ban ~150 mm)
    setengah_lebar_bodi: float = 0.74   # dipakai Dika (VEHICLE_HALF_WIDTH)
    setengah_panjang_bodi: float = 1.10 # dipakai Dika (VEHICLE_HALF_LEN)
    sumber: str = "estimasi; belum diukur di CARLA"

    @property
    def wheelbase(self) -> float:
        return self.jarak_sumbu_depan + self.jarak_sumbu_belakang

    def roda_lokal(self) -> np.ndarray:
        """(4,2) urutan: depan-kiri, depan-kanan, belakang-kiri, belakang-kanan."""
        t = self.lebar_jejak / 2
        a, b = self.jarak_sumbu_depan, -self.jarak_sumbu_belakang
        return np.array([[a, -t], [a, t], [b, -t], [b, t]], dtype=float)


MICROLINO_ESTIMASI = GeometriKendaraan()


@dataclass
class Lubang:
    id: str
    x: float
    y: float
    ex: float                 # setengah ukuran searah sumbu x lokal lubang
    ey: float                 # setengah ukuran searah sumbu y lokal lubang
    yaw: float = 0.0          # derajat
    severity: str = "High"

    @staticmethod
    def dari_json(d: dict) -> "Lubang":
        return Lubang(d["id"], float(d["x"]), float(d["y"]), float(d["extent_x"]), float(d["extent_y"]),
                      float(d.get("yaw", 0.0)), d.get("severity_label", "High"))


def roda_dunia(x, y, yaw_deg, geo: GeometriKendaraan) -> np.ndarray:
    """Posisi 4 roda di koordinat dunia. x,y,yaw boleh skalar atau array (T,). Hasil (T,4,2)."""
    x, y, yaw = np.atleast_1d(x), np.atleast_1d(y), np.radians(np.atleast_1d(yaw_deg))
    c, s = np.cos(yaw)[:, None], np.sin(yaw)[:, None]
    L = geo.roda_lokal()
    wx = x[:, None] + L[None, :, 0] * c - L[None, :, 1] * s
    wy = y[:, None] + L[None, :, 0] * s + L[None, :, 1] * c
    return np.stack([wx, wy], axis=-1)


def jarak_bertanda(px, py, lub: Lubang) -> np.ndarray:
    """Signed distance titik ke persegi panjang lubang. Negatif = di dalam (meter)."""
    th = np.radians(lub.yaw)
    dx, dy = np.asarray(px) - lub.x, np.asarray(py) - lub.y
    u = dx * np.cos(th) + dy * np.sin(th)          # koordinat lokal lubang
    v = -dx * np.sin(th) + dy * np.cos(th)
    qx, qy = np.abs(u) - lub.ex, np.abs(v) - lub.ey
    luar = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    dalam = np.minimum(np.maximum(qx, qy), 0)
    return luar + dalam


# ---------------------------------------------------------------------------
# Label
# ---------------------------------------------------------------------------
def kontak_per_langkah(xs, ys, yaws, lubang: list[Lubang], geo: GeometriKendaraan = MICROLINO_ESTIMASI,
                       sev_min=("Medium", "High")) -> dict:
    """
    Untuk lintasan tercatat (T langkah) kembalikan:
      kontak      (T,) bool — ada roda yang menyentuh lubang ber-severity >= Medium
      id_lubang   (T,) id lubang yang disentuh (None jika tidak)
      jarak_min   (T,) jarak bertanda terkecil roda->lubang dikurangi r_w (<0 = kontak)
      kejadian    daftar dict per kejadian kontak (lubang, langkah awal, langkah akhir, roda)
    Kontak terjadi jika jarak bertanda pusat ban ke lubang < setengah lebar ban.
    """
    W = roda_dunia(xs, ys, yaws, geo)                       # (T,4,2)
    T = W.shape[0]
    rel = [l for l in lubang if l.severity in sev_min]
    if not rel:
        return dict(kontak=np.zeros(T, bool), id_lubang=[None] * T, jarak_min=np.full(T, np.inf), kejadian=[])
    D = np.stack([jarak_bertanda(W[..., 0], W[..., 1], l) for l in rel], axis=-1)   # (T,4,P)
    marg = D - geo.setengah_lebar_ban
    jmin = marg.min(axis=(1, 2))
    kontak = jmin < 0
    idp = marg.min(axis=1).argmin(axis=1)
    id_lubang = [rel[k].id if c else None for k, c in zip(idp, kontak)]

    kejadian = []
    for p, l in enumerate(rel):
        kena = (marg[:, :, p] < 0)
        langkah = np.where(kena.any(axis=1))[0]
        if len(langkah) == 0:
            continue
        # pisahkan blok langkah yang terputus = kejadian terpisah
        pecah = np.split(langkah, np.where(np.diff(langkah) > 1)[0] + 1)
        for blok in pecah:
            roda = sorted({["DKi", "DKa", "BKi", "BKa"][w] for w in np.where(kena[blok].any(axis=0))[0]})
            kejadian.append(dict(lubang=l.id, severity=l.severity, mulai=int(blok[0]), akhir=int(blok[-1]), roda=roda))
    kejadian.sort(key=lambda k: k["mulai"])
    return dict(kontak=kontak, id_lubang=id_lubang, jarak_min=jmin, kejadian=kejadian)


def label_horizon(kontak: np.ndarray, H: int = int(2.0 / DT)) -> np.ndarray:
    """y_t = 1 jika ada kontak pada langkah t+1 .. t+H (label kegagalan keputusan, horizon 2 s)."""
    k = np.asarray(kontak, bool)
    T = len(k)
    c = np.concatenate([[0], np.cumsum(k)])
    t = np.arange(T)
    hi = np.minimum(t + H, T - 1)
    return (c[hi + 1] - c[t + 1]) > 0


def energi_pelanggaran(xs, ys, yaws, lubang: list[Lubang], geo: GeometriKendaraan = MICROLINO_ESTIMASI,
                       sev_min=("Medium", "High")) -> float:
    """
    Persamaan 7 proposal:
        E_V = (1/H) sum_t sum_w sum_p phi(d_{t,w,p}),   phi(d) = max(0, exp(r_w - d) - 1)
    untuk satu lintasan PREDIKSI sepanjang H langkah (bukan lintasan tercatat).
    phi > 0 tepat ketika d < r_w, yaitu ketika ban menyentuh lubang, dan naik
    eksponensial makin dalam ban masuk ke lubang.
    """
    W = roda_dunia(xs, ys, yaws, geo)
    rel = [l for l in lubang if l.severity in sev_min]
    if not rel:
        return 0.0
    D = np.stack([jarak_bertanda(W[..., 0], W[..., 1], l) for l in rel], axis=-1)
    phi = np.maximum(0.0, np.exp(geo.setengah_lebar_ban - D) - 1.0)
    return float(phi.sum() / W.shape[0])


def rollout_sepeda(x, y, yaw_deg, v, sudut_setir_deg, geo: GeometriKendaraan = MICROLINO_ESTIMASI,
                   H: int = int(2.0 / DT), dt: float = DT):
    """
    Model kinematik sepeda dengan titik referensi = titik asal aktor (dianggap pusat
    massa), memakai sudut slip beta = atan(lr/L * tan(delta)).
    sudut_setir_deg = sudut roda depan sebenarnya (= steer CARLA x max_steer_angle kendaraan).
    Kembalikan xs, ys, yaws (H,) untuk langkah 1..H.
    """
    L = geo.wheelbase
    lr = geo.jarak_sumbu_belakang
    beta = np.arctan(lr / L * np.tan(np.radians(sudut_setir_deg)))
    xs, ys, ps = [], [], []
    psi = np.radians(yaw_deg)
    for _ in range(H):
        x += v * np.cos(psi + beta) * dt
        y += v * np.sin(psi + beta) * dt
        psi += v / lr * np.sin(beta) * dt
        xs.append(x); ys.append(y); ps.append(np.degrees(psi))
    return np.array(xs), np.array(ys), np.array(ps)


# ---------------------------------------------------------------------------
# Tiruan setia logika Dika (environment/carla_env.py, versi Mei 2026)
# ---------------------------------------------------------------------------
@dataclass
class HasilDika:
    hit: list = field(default_factory=list)      # (langkah, id)
    avoid: list = field(default_factory=list)    # (langkah, id)


def logika_dika(xs, ys, yaws, lubang: list[Lubang], half_width=0.74, half_len=1.10,
                hit_margin=0.10, cooldown=100, zs=None, z_lubang=None) -> HasilDika:
    """
    Menirukan _calculate_reward() Dika baris demi baris:
      - hanya lubang TERDEKAT di depan (dot(maju, selisih) > 0, jarak 3D < 20 m) yang diperiksa
      - HIT jika jarak 3D < 2.0 m, cooldown == 0, dan |lateral| < extent_x + half_width + margin
        (catatan: extent_x = ukuran SEARAH jalan; untuk lubang yaw 0 seharusnya extent_y)
      - cooldown 100 langkah setelah HIT
      - AVOID diberikan saat x mobil > x lubang + half_len dan lubang itu belum ditandai HIT
    zs / z_lubang opsional: Dika memakai carla.Location.distance (3D). Selisih z jalan-lubang
    ~0.04 m sehingga pengaruhnya diabaikan bila tidak diberikan.
    """
    out = HasilDika()
    track = {l.id: dict(hit=False, rewarded=False) for l in lubang}
    cd = 0
    for t, (x, y, yw) in enumerate(zip(xs, ys, yaws)):
        if cd > 0:
            cd -= 1                                  # step() mengurangi cooldown SEBELUM reward
        th = np.radians(yw)
        fwd = np.array([np.cos(th), np.sin(th)])
        right = np.array([-np.sin(th), np.cos(th)])
        best, bd = None, 20.0
        for l in lubang:
            diff = np.array([l.x - x, l.y - y])
            d = float(np.hypot(*diff))
            if d > 20.0 or fwd @ diff <= 0:
                continue
            if d < bd:
                bd, best = d, (l, float(right @ diff))
        if best is not None:
            l, lat = best
            if bd < 2.0 and cd == 0 and abs(lat) < l.ex + half_width + hit_margin:
                out.hit.append((t, l.id)); cd = cooldown
                track[l.id]["hit"] = True; track[l.id]["rewarded"] = True
        for l in lubang:
            e = track[l.id]
            if not e["rewarded"] and x > l.x + half_len:
                if not e["hit"]:
                    out.avoid.append((t, l.id))
                e["rewarded"] = True
    return out
