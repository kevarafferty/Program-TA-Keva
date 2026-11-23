"""
env_latih.py — [#26] Lingkungan pelatihan pi_ens = CarlaEnvSkenario (12_lingkungan) + dua perbaikan reward
yang ditulis di proposal (Subbab 2.1.5): "ukuran lubang melintang jalan" dan "tidak ada lubang yang dihitung
berhasil dihindari selama masa jeda". Kode Dika tidak diubah; perbaikan = override _calculate_reward.

Perbaikan terhadap carla_env.py Dika (bagian 4, POTHOLE HIT):
  1. Ambang lateral memakai setengah ukuran lubang MELINTANG terhadap arah kendaraan
     (|ex sin dyaw| + |ey cos dyaw|; untuk lubang Dika yaw 0: ey = 1,5 m), bukan extent_x (1,0 m, ukuran
     searah jalan). Bukti bug: TEMUAN T6.
  2. Tanpa cooldown global 100 langkah. Setiap lubang dicek sendiri (tidak hanya lubang terdekat) dan
     HIT paling banyak sekali per lubang. Dulu lubang kedua yang dilewati < 100 langkah setelah HIT tidak
     pernah dicek, lalu dihitung AVOID dan diberi reward (TEMUAN T7, mulai 11 km/jam).
  Jendela memanjang dibuat eksplisit: pusat lubang 0..2 m di depan titik asal kendaraan (sama dengan
  maksud kode Dika: get_closest_ahead + d < 2,0), diukur sepanjang sumbu maju kendaraan, bukan jarak Euclid
  (jarak Euclid membuat lubang dengan offset lateral 2,0-2,34 m tidak pernah bisa HIT walau bodi menimpanya).

Semua bagian lain identik dengan Dika: tabrakan -300, keluar jalan -200, finis +800, timeout -10, HIT
-200*severity, AVOID +50*severity saat x mobil melewati x lubang + setengah panjang mobil, insentif kecepatan,
penalti setir saat tidak ada lubang di depan/terdeteksi.

--reward dika memakai _calculate_reward asli tanpa perubahan (untuk pembanding).
"""
from __future__ import annotations

import math
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(DIR, "..", "12_lingkungan")))

from env_skenario import CarlaEnvSkenario   # noqa: E402

JENDELA_DEPAN_M = 2.0


def setengah_lebar_melintang(ex, ey, yaw_lubang_deg, yaw_kendaraan_deg):
    d = math.radians(yaw_lubang_deg - yaw_kendaraan_deg)
    return abs(ex * math.sin(d)) + abs(ey * math.cos(d))


def offset_lokal(lx, ly, vx, vy, yaw_kendaraan_deg):
    """(maju, kanan) pusat lubang relatif kendaraan, konvensi CARLA (y ke kanan)."""
    r = math.radians(yaw_kendaraan_deg)
    dx, dy = lx - vx, ly - vy
    return dx * math.cos(r) + dy * math.sin(r), -dx * math.sin(r) + dy * math.cos(r)


class CarlaEnvLatih(CarlaEnvSkenario):
    def __init__(self, reward="perbaikan", **kw):
        if reward not in ("perbaikan", "dika"):
            raise ValueError("reward harus 'perbaikan' atau 'dika'")
        self.mode_reward = reward
        super().__init__(**kw)

    def _calculate_reward(self, state=None):
        if self.mode_reward == "dika":
            return super()._calculate_reward(state)
        reward, done = 0.0, False

        # 1-3: identik dengan Dika
        if len(self.collision_history) > 0:
            self.collision_history.clear()
            return -300.0, True
        lane_info = self._get_lane_info()
        if lane_info and lane_info['out_of_road']:
            return self.OUT_OF_ROAD_PENALTY, True
        loc = self.vehicle.get_location()
        if loc.x > self.finish_x_threshold:
            return 800.0, True
        if self.current_step >= self.max_steps_per_episode:
            return -10.0, True

        tf_ = self.vehicle.get_transform()
        yaw_v = tf_.rotation.yaw

        # 4. HIT (diperbaiki): semua lubang, sekali per lubang, ambang lateral melintang
        for ph in self.gt.potholes:
            ent = self.pothole_tracking.setdefault(ph['id'], {'hit': False, 'rewarded': False})
            if ent['hit'] or ent['rewarded']:
                continue
            maju, kanan = offset_lokal(ph['loc'].x, ph['loc'].y, loc.x, loc.y, yaw_v)
            if not (0.0 < maju < JENDELA_DEPAN_M):
                continue
            ambang = (setengah_lebar_melintang(ph['extent_x'], ph['extent_y'], ph.get('yaw', 0.0), yaw_v)
                      + self.VEHICLE_HALF_WIDTH + self.HIT_MARGIN_M)
            if abs(kanan) < ambang:
                reward -= 200.0 * ph['severity']
                self.total_hit_events += 1
                ent['hit'] = ent['rewarded'] = True

        # 6. AVOID: identik dengan Dika (per lubang, saat x mobil melewati x lubang + setengah panjang)
        for ph in self.gt.potholes:
            ent = self.pothole_tracking.setdefault(ph['id'], {'hit': False, 'rewarded': False})
            if not ent['rewarded'] and loc.x > ph['loc'].x + self.VEHICLE_HALF_LEN:
                if not ent['hit']:
                    reward += 50.0 * ph['severity']
                    self.total_avoid_events += 1
                ent['rewarded'] = True

        # 5. insentif kecepatan: identik
        speed = self.vehicle_state['speed']
        reward += speed / 15.0 * 0.5 if 5.0 <= speed <= 15.0 else -0.5

        # 6. penalti setir saat bebas lubang: identik (lubang di depan = get_closest_ahead 20 m, seperti Dika)
        dekat = self.gt.get_closest_ahead(loc, tf_, max_dist=20.0) is not None
        yolo = state is not None and state.get('pothole_detected', False)
        if not dekat and not yolo:
            reward -= abs(self.vehicle_state['steering_angle']) * 1.0

        self.previous_speed = speed
        self.previous_steer = self.vehicle_state['steering_angle']
        return reward, done
