"""
env_skenario.py — [#24 #25] CarlaEnv Dika + generator tata letak + skenario off-nominal + perekam persepsi.

Turunan dari environment/carla_env.py (10_runner/DQN_Akselerasi vertikal). Kode Dika TIDAK diubah.
Yang ditimpa (override) dan alasannya:

  _spawn_vehicle          blueprint dari skenario (C4) tanpa fallback diam-diam, heading awal (C3),
                          lampu kendaraan (A1) dipasang sebelum sensor siap.
  _setup_collision_sensor tabrakan dengan aktor lubang hasil spawn tidak mengakhiri episode (dicatat terpisah).
  _apply_action           throttle dari skenario (C2). Steer identik dengan Dika (0 / -0,35 / +0,35).
  _detect_potholes_yolo   SALINAN logika Dika (imgsz 320, conf 0,05, kotak conf tertinggi, peta severity
                          {0:0,6, 1:0,9, 2:0,3}, EMA 0,7/0,3) + korupsi citra (A5/A6) sebelum YOLO
                          + ekstraksi logit/fitur dari inferensi yang sama.
  step                    perbarui transisi (cuaca/korupsi) dari posisi x SEBELUM world.tick().

Jika skenario = ID0 dengan throttle 0,3 dan Microlino, perilaku env identik dengan CarlaEnv Dika
kecuali tata letak lubang (diuji di tests/test_e2e_palsu.py: state 10-D sama persis dengan logika Dika).
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np
import carla  # pyright: ignore[reportMissingImports]

from environment.carla_env import CarlaEnv, PotholeGroundTruth   # dari folder Dika (sys.path diatur runner)

from generator_tata_letak import BackendGrid, BackendSpawn, buat_tata_letak, muat_slot_grid
from persepsi_hook import HookPersepsi
from verifikasi_lubang import PemeriksaLubang
from skenario import (PARAM_CUACA, Korupsi, cuaca_angka, faktor_transisi, interpolasi_cuaca,
                      spesifikasi_ke_json, throttle_untuk)

PRESET_DIPAKAI = ["ClearNoon", "CloudyNoon", "WetNoon", "WetCloudyNoon", "SoftRainNoon", "MidRainyNoon",
                  "HardRainNoon", "ClearNight", "ClearSunset"]


def cuaca_ke_dict(w) -> dict:
    return {k: float(getattr(w, k)) for k in PARAM_CUACA if hasattr(w, k)}


def dict_ke_cuaca(d: dict):
    """Objek WeatherParameters BARU (jangan setattr pada preset statis carla.WeatherParameters.X)."""
    w = carla.WeatherParameters()
    for k, v in d.items():
        if hasattr(w, k):
            setattr(w, k, float(v))
    return w


class CarlaEnvSkenario(CarlaEnv):
    def __init__(self, backend: str = "grid", gt_v2_path: str = None, kalibrasi: dict = None,
                 topk_anchor: int = 100, **kw):
        super().__init__(**kw)
        self.kalibrasi = kalibrasi or {}
        self.backend_nama = backend
        self.preset = {n: cuaca_ke_dict(getattr(carla.WeatherParameters, n))
                       for n in PRESET_DIPAKAI if hasattr(carla.WeatherParameters, n)}
        self.slot = muat_slot_grid(gt_v2_path) if gt_v2_path else muat_slot_grid()
        self.grid = BackendGrid(self.world, carla, self.slot)
        if self.grid.tidak_ketemu:
            print("⚠️  %d slot GT tidak ketemu di peta: %s" % (len(self.grid.tidak_ketemu), self.grid.tidak_ketemu[:5]))
        self.spawner = BackendSpawn(self.world, carla, self.grid) if backend == "spawn" else None
        # pemanasan: membuat predictor Ultralytics (pengaturan sama dengan kode Dika) supaya hook bisa
        # dipasang pada model yang benar-benar dipakai sejak langkah pertama. Tidak mengubah hasil inferensi.
        import torch
        self.yolo_model(np.zeros((640, 640, 3), np.uint8), imgsz=320, conf=0.05, verbose=False,
                        device='cuda' if torch.cuda.is_available() else 'cpu')
        self.hook = HookPersepsi(self.yolo_model, topk_anchor=topk_anchor)
        self.verifikasi_aktif = True

        # status per episode
        self.spec = None
        self.tata_letak = None
        self.throttle = 0.3
        self.blueprint_mau = self.VEHICLE_BLUEPRINT
        self.lampu = None
        self.korupsi = Korupsi(None, 0)
        self.transisi = None
        self.cuaca_awal_angka = None
        self.cuaca_target_angka = None
        self._f_terpasang = 1.0
        self._cuaca_terpasang = None
        self.rekam_persepsi = None
        self.tabrakan_lubang = []
        self.heading_awal = 0.0
        self.offset_aktual = (0.0, 0.0)
        self.geometri_kendaraan = None

    # ==========================================================================================
    # Persiapan episode
    # ==========================================================================================
    def siapkan_episode(self, spec: dict, gt_path: str) -> dict:
        """Terapkan spesifikasi episode (dari skenario.resolusi). Panggil SEBELUM reset()."""
        # [24 Nov] Hapus kendaraan + sensor episode sebelumnya SEBELUM verifikasi lubang. Dulu baru dihapus di
        # reset(), sehingga mobil yang berhenti/menabrak di atas sebuah lubang menutupi lubang itu dari kamera
        # verifikasi -> "tak tampak" 3x -> RuntimeError (ID0 seed 3 setelah seed 2 menabrak di x -48,9 di atas
        # ph_0017). reset() tetap memanggil _cleanup(); memanggilnya dua kali aman (aktor sudah None).
        self._cleanup()
        self.spec = spec
        tl = buat_tata_letak(spec["seed"], spec["konfig_tata_letak"], spec["backend"], self.slot)
        if tl.n == 0:
            raise RuntimeError("tata letak kosong untuk seed %s" % spec["seed"])
        self.tata_letak = tl
        tl.simpan_gt(gt_path)
        if spec["backend"] == "grid":
            info_be = self.grid.terapkan(tl, tick=self.world.tick)
        else:
            info_be = self.spawner.terapkan(tl)
        info_be["verifikasi"] = self.verifikasi_lubang(tl)
        self.gt = PotholeGroundTruth(gt_path)            # reward/hit Dika memakai GT episode ini
        self.finish_x_threshold = spec["x_finis"]

        self.throttle = throttle_untuk(spec.get("kecepatan"), self.kalibrasi, spec.get("kendaraan"))
        self.blueprint_mau = spec.get("kendaraan") or self.VEHICLE_BLUEPRINT
        self.lampu = spec.get("lampu")
        sp = spec["spawn"]
        self.offset_maks_x, self.offset_maks_y = float(sp["offset_x"]), float(sp["offset_y"])
        self.offset_aktual = (float(sp["offset_x_aktual"]), float(sp["offset_y_aktual"]))
        self.heading_awal = float(sp.get("heading_deg_aktual", 0.0))
        self.episode_seed = int(spec["seed"])

        self.cuaca_target_angka = cuaca_angka(spec["cuaca_target"], self.preset, self.kalibrasi)
        self.cuaca_awal_angka = cuaca_angka(spec["cuaca_awal"], self.preset, self.kalibrasi)
        self.transisi = spec.get("transisi")
        self.korupsi = Korupsi(spec.get("korupsi"), spec["seed_korupsi"])
        self._pasang_faktor(0.0 if self.transisi else 1.0, paksa=True)
        return dict(tata_letak=tl.ringkas(), backend=info_be, throttle=self.throttle,
                    cuaca_awal=self.cuaca_awal_angka, cuaca_target=self.cuaca_target_angka)

    def verifikasi_lubang(self, tl, maks_coba: int = 3) -> dict:
        """Cek lubang aktif (pertama, tengah, terakhir) benar-benar tampak, cuaca sementara ClearNoon.
        Gagal setelah maks_coba -> RuntimeError (episode tidak dijalankan; matriks akan mencoba ulang)."""
        if not self.verifikasi_aktif:
            return dict(dilewati=True)
        import torch
        dev = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.world.set_weather(carla.WeatherParameters.ClearNoon)
        self._cuaca_terpasang = None                 # paksa pasang ulang cuaca skenario sesudahnya
        pem = PemeriksaLubang(self.world, carla, self.yolo_model, dev)
        riwayat = []
        try:
            cek = pem.pilih(tl.lubang)
            for coba in range(1, maks_coba + 1):
                hasil = [pem.cek_satu(l) for l in cek]
                gagal = [h["id"] for h in hasil if not h["tampak"]]
                riwayat.append(dict(coba=coba, hasil=hasil))
                if not gagal:
                    break
                print("⚠️  verifikasi: lubang %s tak tampak (percobaan %d/%d), toggle diulang" % (gagal, coba, maks_coba))
                if tl.backend == "grid":
                    slot_gagal = [l["slot"] for l in tl.lubang if l["id"] in gagal]
                    # kalau satu tak tampak, kemungkinan semuanya: ulang semua slot aktif
                    self.grid.ulang([l["slot"] for l in tl.lubang] if slot_gagal else [], tick=self.world.tick)
                else:
                    self.spawner.terapkan(tl)
            else:
                raise RuntimeError("Lubang tetap tak tampak setelah %d percobaan: %s" % (maks_coba, gagal))
        finally:
            pem.tutup()
        akhir = riwayat[-1]["hasil"]
        return dict(lolos=True, percobaan=len(riwayat), dicek=len(akhir),
                    conf_min=min(h["conf"] for h in akhir), riwayat=riwayat)

    def _pasang_faktor(self, f: float, paksa: bool = False):
        """Pasang cuaca untuk faktor transisi f (0 nominal .. 1 target)."""
        if self.transisi is None:
            f = 1.0
        berubah = abs(f - self._f_terpasang) >= 0.01 or (f in (0.0, 1.0) and f != self._f_terpasang)
        if not paksa and self._cuaca_terpasang is not None and not berubah:
            return
        d = interpolasi_cuaca(self.cuaca_awal_angka, self.cuaca_target_angka, f) if self.transisi else self.cuaca_target_angka
        self.world.set_weather(dict_ke_cuaca(d))
        self._cuaca_terpasang = d
        self._f_terpasang = f

    # ==========================================================================================
    # Override
    # ==========================================================================================
    def reset(self):
        self.tabrakan_lubang = []
        self.hook.n_panggil = self.hook.n_tidak_cocok = 0
        if self.spec is not None:
            self._pasang_faktor(0.0 if self.transisi else 1.0, paksa=True)
        return super().reset()

    def step(self, action):
        if self.transisi is not None and self.vehicle is not None:
            x = self.vehicle.get_location().x
            self._pasang_faktor(faktor_transisi(x, self.transisi))
        return super().step(action)

    def _spawn_vehicle(self):
        lib = self.world.get_blueprint_library()
        cand = list(lib.filter(self.blueprint_mau))
        if not cand:
            raise RuntimeError("Blueprint kendaraan '%s' tidak ada di build ini" % self.blueprint_mau)
        car_bp = cand[0]
        print(f"🚗 Blueprint: {car_bp.id}")
        sp = self.custom_spawn_transform
        # offset dihitung skenario._offset_spawn (ID-0: rumus random.Random(seed) yang sama dengan Dika [#19])
        self.spawn_offset = self.offset_aktual if self.spec is not None else (0.0, 0.0)
        tf = carla.Transform(
            carla.Location(x=sp.location.x + self.spawn_offset[0], y=sp.location.y + self.spawn_offset[1],
                           z=sp.location.z + 0.5),
            carla.Rotation(pitch=sp.rotation.pitch, yaw=sp.rotation.yaw + self.heading_awal, roll=sp.rotation.roll))
        self.vehicle = self.world.spawn_actor(car_bp, tf)   # gagal = error (tanpa fallback spawn point)
        print(f"✅ Spawn: ({tf.location.x:.2f}, {tf.location.y:.2f}) yaw {tf.rotation.yaw:.2f}")
        if self.lampu:
            st = getattr(carla.VehicleLightState, self.lampu)
            if self.lampu == "HighBeam":
                st = carla.VehicleLightState(int(carla.VehicleLightState.HighBeam) | int(carla.VehicleLightState.LowBeam)
                                             | int(carla.VehicleLightState.Position))
            elif self.lampu == "LowBeam":
                st = carla.VehicleLightState(int(carla.VehicleLightState.LowBeam) | int(carla.VehicleLightState.Position))
            self.vehicle.set_light_state(st)
        self.geometri_kendaraan = None   # diukur setelah reset (fisika sudah siap)

    def _setup_collision_sensor(self):
        bp = self.world.get_blueprint_library().find('sensor.other.collision')
        self.collision_sensor = self.world.spawn_actor(bp, carla.Transform(), attach_to=self.vehicle)
        def cb(e):
            try:
                oid = int(e.other_actor.id) if e.other_actor is not None else -1
            except Exception:
                oid = -1
            if self.spawner is not None and oid in self.spawner.id_aktor:
                self.tabrakan_lubang.append((self.current_step, oid))
                return
            self.collision_history.append(e)
            self._catat_tabrakan(e)
        self.collision_sensor.listen(cb)
        print("✅ Collision sensor setup")

    def _apply_action(self, action):
        ctrl = carla.VehicleControl()
        if action == 0:
            ctrl.throttle, ctrl.steer = self.throttle, 0.0
        elif action == 1:
            ctrl.throttle, ctrl.steer = self.throttle, -0.35
        elif action == 2:
            ctrl.throttle, ctrl.steer = self.throttle, +0.35
        self.vehicle.apply_control(ctrl)

    def _detect_potholes_yolo(self, image):
        """Salinan _detect_potholes_yolo Dika + korupsi + perekaman. Lihat docstring modul."""
        f = self._f_terpasang if self.transisi is not None else 1.0
        img_in = self.korupsi.terapkan(image, f, self.current_step) if self.korupsi.aktif else image
        self.rekam_persepsi = None
        self.hook.kosongkan()
        hasil = np.zeros(5, dtype=np.float32)
        try:
            import torch
            with torch.no_grad():
                results = self.yolo_model(
                    img_in, imgsz=320, conf=0.05, verbose=False,
                    device='cuda' if torch.cuda.is_available() else 'cpu'
                )
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            try:
                self.rekam_persepsi = self.hook.ekstrak(results[0])
            except Exception as e:                       # perekaman tidak boleh mengubah perilaku agen
                print(f"⚠️  hook persepsi error: {e}")
                self.rekam_persepsi = None

            if len(results) > 0 and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                best_idx = int(np.argmax(boxes.conf.cpu().numpy()))
                x1, y1, x2, y2 = boxes.xyxy[best_idx].cpu().numpy()
                ih, iw = img_in.shape[:2]
                cx = ((x1 + x2) / 2) / iw
                cy = ((y1 + y2) / 2) / ih
                w = (x2 - x1) / iw
                h = (y2 - y1) / ih
                cls = int(boxes.cls[best_idx].cpu().numpy())
                raw_sev = {0: 0.6, 1: 0.9, 2: 0.3}.get(cls, 0.5)
                if self.smoothed_severity == 0.0:
                    self.smoothed_severity = raw_sev
                else:
                    self.smoothed_severity = (0.7 * self.smoothed_severity + 0.3 * raw_sev)
                hasil = np.array([cx, cy, w, h, self.smoothed_severity], dtype=np.float32)
            else:
                self.smoothed_severity = 0.0
        except Exception as e:
            print(f"⚠️  YOLO error: {e}")
            self.smoothed_severity = 0.0
        if self.rekam_persepsi is not None:
            self.rekam_persepsi["f_korupsi"] = float(f if self.korupsi.aktif else 0.0)
        return hasil

    # ==========================================================================================
    # Bantuan logger
    # ==========================================================================================
    def ukur_geometri_kendaraan(self) -> dict:
        """Posisi roda lokal + bbox (meter), untuk pelabel roda pada kendaraan selain Microlino (C4)."""
        v = self.vehicle
        tf = v.get_transform()
        out = dict(blueprint=v.type_id,
                   bbox_extent=[v.bounding_box.extent.x, v.bounding_box.extent.y, v.bounding_box.extent.z])
        try:
            fw = tf.get_forward_vector()
            rt = tf.get_right_vector()
            roda = []
            for w in v.get_physics_control().wheels:
                p = w.position                                # cm, koordinat dunia
                dx, dy = p.x / 100.0 - tf.location.x, p.y / 100.0 - tf.location.y
                roda.append([round(dx * fw.x + dy * fw.y, 4), round(dx * rt.x + dy * rt.y, 4)])
            out["roda_lokal_xy"] = roda
        except Exception as e:
            out["roda_lokal_xy"] = None
            out["catatan"] = "gagal baca roda: %s" % e
        self.geometri_kendaraan = out
        return out

    def tutup_lingkungan(self):
        try:
            self.hook.lepas()
        except Exception:
            pass
        if self.spawner is not None:
            self.spawner.tutup()
        else:
            self.grid.tutup()
