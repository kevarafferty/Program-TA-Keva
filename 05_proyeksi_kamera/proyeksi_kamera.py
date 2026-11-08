"""
proyeksi_kamera.py — Proyeksi titik/lubang 3D dunia CARLA ke piksel citra kamera
(model pinhole), dan kebalikannya untuk titik di permukaan jalan.

Dipakai untuk:
  * label kegagalan persepsi (Bab 2.1.3): kotak 2D "seharusnya" dari ground truth
    lubang, dibandingkan dengan deteksi YOLO
  * menerjemahkan state DQN (cy kotak YOLO) menjadi jarak lubang dalam meter

Konvensi = CARLA / Unreal: x maju, y kanan, z atas; rotasi (pitch, yaw, roll) dalam derajat.
Matriks transform mengikuti carla.Transform.get_matrix() (urutan yaw-pitch-roll Unreal).
Bingkai kamera pinhole: x kanan, y bawah, z maju  -> sama dengan CameraProjector Retta.

Preset:
  KAMERA_DIKA  : 640x640, FOV 90°, dipasang x=1.5 m, z=2.0 m, pitch -15° (carla_env.py)
  KAMERA_RETTA : 1280x720, FOV 90°, x=1.5 m, z=1.7 m, pitch -15° (nilai bawaan CameraConfig di kode Retta)
  KAMERA_RETTA_RUN : 1600x900, FOV 120° (nilai yang dipakai di perintah run Retta, Prompt.txt)
Asumsi: titik asal aktor kendaraan berada di permukaan jalan (z_jalan = z_kendaraan).
Jika ternyata tidak, isi parameter tinggi_asal_kendaraan dengan nilai yang diukur di CARLA.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Kamera:
    lebar: int
    tinggi: int
    fov: float                     # derajat, horizontal (atribut 'fov' CARLA)
    x: float                       # pemasangan relatif titik asal kendaraan (m)
    y: float
    z: float
    pitch: float                   # derajat, negatif = menunduk
    yaw: float = 0.0
    roll: float = 0.0

    @property
    def f(self) -> float:
        return self.lebar / (2.0 * np.tan(np.radians(self.fov) / 2.0))

    @property
    def K(self) -> np.ndarray:
        return np.array([[self.f, 0, self.lebar / 2.0], [0, self.f, self.tinggi / 2.0], [0, 0, 1.0]])


KAMERA_DIKA = Kamera(640, 640, 90.0, 1.5, 0.0, 2.0, -15.0)
KAMERA_RETTA = Kamera(1280, 720, 90.0, 1.5, 0.0, 1.7, -15.0)
# Perintah run Retta yang sebenarnya (Source Code/Prompt.txt) menimpa nilai bawaan:
# --cam-fov 120 --cam-width 1600 --cam-height 900 --cam-pitch -15 (posisi pasang tidak diubah)
KAMERA_RETTA_RUN = Kamera(1600, 900, 120.0, 1.5, 0.0, 1.7, -15.0)


def matriks_transform(x, y, z, pitch, yaw, roll) -> np.ndarray:
    """Salinan carla.Transform.get_matrix(): lokal -> induk (4x4)."""
    cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    cp, sp = np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
    cr, sr = np.cos(np.radians(roll)), np.sin(np.radians(roll))
    return np.array([
        [cp * cy, cy * sp * sr - sy * cr, -cy * sp * cr - sy * sr, x],
        [sy * cp, sy * sp * sr + cy * cr, -sy * sp * cr + cy * sr, y],
        [sp, -cp * sr, cp * cr, z],
        [0, 0, 0, 1.0]])


def dunia_ke_kamera(kam: Kamera, pose_kendaraan) -> np.ndarray:
    """Matriks 4x4 dunia -> bingkai sensor kamera (x maju, y kanan, z atas)."""
    vx, vy, vz, vyaw = pose_kendaraan[:4]
    vpitch = pose_kendaraan[4] if len(pose_kendaraan) > 4 else 0.0
    vroll = pose_kendaraan[5] if len(pose_kendaraan) > 5 else 0.0
    T_wv = matriks_transform(vx, vy, vz, vpitch, vyaw, vroll)
    T_vc = matriks_transform(kam.x, kam.y, kam.z, kam.pitch, kam.yaw, kam.roll)
    return np.linalg.inv(T_wv @ T_vc)


def proyeksikan(kam: Kamera, pose_kendaraan, titik_dunia: np.ndarray):
    """titik_dunia (N,3) -> piksel (N,2), kedalaman (N,), valid_depan (N,)."""
    P = np.c_[np.atleast_2d(titik_dunia), np.ones(len(np.atleast_2d(titik_dunia)))]
    c = (dunia_ke_kamera(kam, pose_kendaraan) @ P.T).T[:, :3]
    xc, yc, zc = c[:, 1], -c[:, 2], c[:, 0]             # x kanan, y bawah, z maju
    depan = zc > 0.1
    u = np.where(depan, kam.f * xc / np.where(depan, zc, 1) + kam.lebar / 2.0, np.nan)
    v = np.where(depan, kam.f * yc / np.where(depan, zc, 1) + kam.tinggi / 2.0, np.nan)
    return np.c_[u, v], zc, depan


def sudut_lubang(lubang: dict, z_jalan: float = 0.0) -> np.ndarray:
    """4 sudut lubang (persegi panjang di permukaan jalan) dari entri pothole_gt.json."""
    th = np.radians(float(lubang.get("yaw", 0.0)))
    ex, ey = float(lubang["extent_x"]), float(lubang["extent_y"])
    lok = np.array([[ex, ey], [ex, -ey], [-ex, -ey], [-ex, ey]])
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    xy = lok @ R.T + [float(lubang["x"]), float(lubang["y"])]
    return np.c_[xy, np.full(4, z_jalan)]


def kotak_2d_lubang(kam: Kamera, pose_kendaraan, lubang: dict, z_jalan: float = None,
                    min_terlihat: float = 0.3):
    """
    Kotak 2D (x1,y1,x2,y2) lubang di citra, atau None jika tidak cukup terlihat.
    Sudut di belakang kamera ditangani dengan memotong poligon di bidang z_kamera = 0.1 m.
    min_terlihat: proporsi luas kotak yang harus berada di dalam citra.
    """
    if z_jalan is None:
        z_jalan = float(pose_kendaraan[2])
    pts = sudut_lubang(lubang, z_jalan)
    # bagi tiap sisi jadi 20 titik agar kotak tetap benar saat sebagian lubang di luar layar
    sisi = np.concatenate([np.linspace(pts[i], pts[(i + 1) % 4], 20) for i in range(4)])
    uv, z, depan = proyeksikan(kam, pose_kendaraan, sisi)
    if depan.sum() < 2:
        return None
    uv = uv[depan]
    x1, y1 = uv.min(0); x2, y2 = uv.max(0)
    luas = (x2 - x1) * (y2 - y1)
    if luas <= 0:
        return None
    cx1, cy1 = max(x1, 0), max(y1, 0)
    cx2, cy2 = min(x2, kam.lebar), min(y2, kam.tinggi)
    luas_dalam = max(cx2 - cx1, 0) * max(cy2 - cy1, 0)
    if luas_dalam / luas < min_terlihat:
        return None
    return np.array([cx1, cy1, cx2, cy2])


def piksel_ke_jalan(kam: Kamera, u: float, v: float):
    """
    Kebalikan proyeksi untuk titik di PERMUKAAN JALAN datar (z = z kendaraan).
    Kembalikan (maju_m, kanan_m) relatif titik asal kendaraan, atau None jika di atas horizon.
    """
    d = np.array([(u - kam.lebar / 2.0) / kam.f, (v - kam.tinggi / 2.0) / kam.f, 1.0])   # bingkai pinhole
    d_sensor = np.array([d[2], d[0], -d[1]])                                            # x maju, y kanan, z atas
    R = matriks_transform(0, 0, 0, kam.pitch, kam.yaw, kam.roll)[:3, :3]
    d_v = R @ d_sensor
    if d_v[2] >= -1e-9:
        return None
    t = -kam.z / d_v[2]
    return float(kam.x + t * d_v[0]), float(kam.y + t * d_v[1])


def baris_horizon(kam: Kamera) -> float:
    return kam.tinggi / 2.0 - kam.f * np.tan(np.radians(-kam.pitch))
