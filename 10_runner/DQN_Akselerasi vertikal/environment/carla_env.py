import carla  # pyright: ignore[reportMissingImports]
import numpy as np
import cv2
import time
import math
import json
import os
import random   # [#19] offset spawn acak

# Optional: YOLO integration
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  YOLO tidak terinstall. Install dengan: pip install ultralytics")


# ══════════════════════════════════════════════════════════════════
# POTHOLE GROUND TRUTH LOADER
# Membaca pothole_gt.json dan menyediakan query berbasis posisi 3D.
#
# Alur reward:
#   YOLO  → state / persepsi agen (tidak berubah)
#   GT    → reward hit / avoid (akurat, world-space meter)
#
# Threshold hit / avoid dihitung dari:
#   extent_x lubang  +  half_width kendaraan  +  margin
# sehingga secara fisik benar-benar representatif.
# ══════════════════════════════════════════════════════════════════
class PotholeGroundTruth:
    """
    Load pothole_gt.json dan sediakan query posisi 3D.

    Setiap entry JSON harus punya field:
        id, x, y, z, yaw,
        extent_x, extent_y, extent_z,
        severity, severity_label
    """

    def __init__(self, json_path: str):
        if not os.path.exists(json_path):
            raise FileNotFoundError(
                f"pothole_gt.json tidak ditemukan: {json_path}\n"
                "Jalankan build_gt_from_ue4.py terlebih dahulu."
            )
        with open(json_path, 'r') as f:
            raw = json.load(f)

        self.potholes = []
        for item in raw:
            self.potholes.append({
                'id'      : item['id'],
                'name'    : item.get('name', item['id']),
                'loc'     : carla.Location(
                                x=float(item['x']),
                                y=float(item['y']),
                                z=float(item['z'])),
                # extent = half-size dari pusat ke tepi (meter)
                'extent_x': float(item['extent_x']),
                'extent_y': float(item['extent_y']),
                'extent_z': float(item.get('extent_z', 0.05)),
                'yaw'     : float(item.get('yaw', 0.0)),
                'severity': float(item['severity']),
                'label'   : item.get('severity_label', 'MEDIUM'),
            })

        print(f"✅ GT loaded: {len(self.potholes)} potholes dari {json_path}")

    # ── Query utama ────────────────────────────────────────────────

    def get_closest_ahead(self, vehicle_loc, vehicle_tf, max_dist=30.0):
        """
        Kembalikan pothole terdekat yang ada DI DEPAN kendaraan.
        Menyertakan lateral_offset_m (jarak samping dalam meter).

        lateral_offset_m = seberapa jauh pusat lubang dari sumbu
                           maju kendaraan, diukur ke kanan (positif)
                           atau kiri (negatif).
        """
        fwd   = vehicle_tf.get_forward_vector()
        right = vehicle_tf.get_right_vector()
        fwd_np   = np.array([fwd.x,   fwd.y])
        right_np = np.array([right.x, right.y])

        best, best_dist = None, max_dist

        for ph in self.potholes:
            d = vehicle_loc.distance(ph['loc'])
            if d > max_dist:
                continue

            diff = np.array([ph['loc'].x - vehicle_loc.x,
                             ph['loc'].y - vehicle_loc.y])

            # Hanya yang benar-benar di depan
            if np.dot(fwd_np, diff) <= 0:
                continue

            if d < best_dist:
                best_dist = d
                # Lateral offset: positif = lubang di kanan kendaraan
                lat = float(np.dot(right_np, diff))
                best = {**ph, 'distance': d, 'lateral_offset_m': lat}

        return best  # None jika tidak ada

    def get_nearby(self, vehicle_loc, radius=30.0):
        """Semua pothole dalam radius, diurutkan dari terdekat."""
        out = []
        for ph in self.potholes:
            d = vehicle_loc.distance(ph['loc'])
            if d <= radius:
                out.append({**ph, 'distance': d})
        out.sort(key=lambda x: x['distance'])
        return out


# ══════════════════════════════════════════════════════════════════
# CARLA ENVIRONMENT
# ══════════════════════════════════════════════════════════════════
class CarlaEnv:
    """
    Environment CARLA untuk DRL dengan:
    - Kendaraan terkecil: vehicle.micro.microlino (lebar 1.24 m)
    - YOLO untuk persepsi / state agen
    - Ground truth 3D (pothole_gt.json) untuk perhitungan reward
    - State machine tracking lubang (hit / avoid akurat)
    """

    # ── Dimensi kendaraan Microlino ────────────────────────────────
    VEHICLE_BLUEPRINT  = 'vehicle.micro.microlino'
    VEHICLE_HALF_WIDTH = 0.74 # meter  (lebar 1.24 m / 2)
    VEHICLE_HALF_LEN   = 1.10 # meter  (panjang 2.43 m / 2)

    # Fallback jika Microlino tidak ada di versi CARLA
    VEHICLE_FALLBACKS = [
        'vehicle.nissan.micra',
        'vehicle.citroen.c3',
        'vehicle.mini.cooperst',
        'vehicle.tesla.model3',
    ]

    def __init__(
        self,
        town             = 'train_fix',
        yolo_model_path  = 'Yolo/best_pure.pt',
        gt_json_path     = 'pothole_gt.json',
        spawn_index      = None,
        weather          = carla.WeatherParameters.ClearNoon,
    ):
        print("Inisialisasi CARLA Environment...")

        self.client = carla.Client('127.0.0.1', 2000)   # [#19] bukan localhost (WARP)
        self.client.set_timeout(15.0)

        print(f"Loading map: {town} ...")
        self.world = self.client.load_world(town)
        print(f"✅ Loaded {town}")

        settings = self.world.get_settings()
        settings.synchronous_mode  = True
        settings.fixed_delta_seconds = 0.05   # 20 FPS
        self.world.apply_settings(settings)
        self.world.set_weather(weather)

        # Spawn point default
        self.custom_spawn_transform = carla.Transform(
            carla.Location(x=-299.5, y=250.5, z=3),
            carla.Rotation(yaw=0)
        )
        self.spawn_index = spawn_index

        # [#19] seed + offset spawn acak, sinkronisasi frame kamera
        self.episode_seed      = None
        self.offset_maks_x     = 0.0
        self.offset_maks_y     = 0.0
        self.spawn_offset      = (0.0, 0.0)
        self.camera_frame      = -1
        self.world_frame       = -1
        self.kamera_telat      = 0

        # ── YOLO ──────────────────────────────────────────────────
        self.yolo_model = None
        if YOLO_AVAILABLE:
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    print(f"🔧 CUDA: {torch.cuda.get_device_name(0)}")
                self.yolo_model = YOLO(yolo_model_path)
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.yolo_model.to(device)
                print(f"✅ YOLO loaded on {device.upper()}")
            except Exception as e:
                print(f"⚠️  YOLO model error: {e}")
        # [#19] berhenti kalau YOLO tidak termuat: tanpa YOLO agen buta dan hasil episode tidak valid
        if self.yolo_model is None:
            raise RuntimeError(f"YOLO tidak termuat dari '{yolo_model_path}'. Salin best_pure.pt (SHA-256 7b6b44f3...) ke folder Yolo/.")

        # ── Ground Truth Pothole ───────────────────────────────────
        self.gt = PotholeGroundTruth(gt_json_path)

        # ── Threshold hit / avoid berbasis fisik ──────────────────
        #
        # HIT  : pusat kendaraan vs pusat lubang secara lateral
        #        < half_width_kendaraan + extent_x_lubang
        #        → kendaraan benar-benar melewati atas lubang
        #
        # AVOID: lateral offset > extent_x_lubang + half_width + margin_aman
        #        → kendaraan sudah melewati lubang di samping dengan aman
        #
        # Nilai ini dihitung PER-LUBANG di _calculate_reward()
        # menggunakan extent_x masing-masing pothole dari GT.
        # Konstanta di bawah adalah MARGIN tambahan di atas extent.
        #
        self.HIT_MARGIN_M   = 0.10   # toleransi kecil agar tidak terlalu ketat
        self.AVOID_MARGIN_M = 0.50   # jarak aman tambahan setelah tepi lubang

        # ── Actors & sensors ──────────────────────────────────────
        self.vehicle          = None
        self.camera           = None
        self.collision_sensor = None
        self.imu_sensor       = None

        self.current_image    = None
        self.collision_history = []
        self.imu_data         = None

        # ── Vehicle state ──────────────────────────────────────────
        self.vehicle_state = {
            'speed'         : 0.0,
            'steering_angle': 0.0,
            'acceleration'  : np.zeros(3),
            'position'      : np.zeros(3),
            'collision'     : 0.0,
        }
        self.previous_speed  = 0.0
        self.previous_steer  = 0.0
        self.previous_location = None

        # ── Pothole tracking ───────────────────────────────────────
        self.pothole_hit_cooldown  = 0
        self.pothole_avoid_cooldown = 0
        self.total_hit_events      = 0
        self.total_avoid_events    = 0
        self.smoothed_severity     = 0.0

        # ── Action space ───────────────────────────────────────────
        # 0: Left gentle    1: Right gentle   2: Straight slow
        # 3: Straight fast  4: Brake
        # 5: Left fast      6: Right fast
        self.num_actions = 3

        self.dt = 0.05
        self.finish_x_threshold      = -27
        self.max_steps_per_episode   = 5000
        self.current_step            = 0
        print("Environment siap!")

        self.ROAD_Y_MIN = 245.55   # tepi kiri jalan (jalur 1 luar)
        self.ROAD_Y_MAX = 252.55   # tepi kanan jalan (jalur 2 luar)

        # Penalty keluar jalan
        self.OUT_OF_ROAD_PENALTY = -200.0
        self.pothole_tracking = {}

    def _get_lane_info(self):
        """
        Return dict berisi:
        - current_y      : posisi Y kendaraan sekarang
        - lane           : 1 atau 2 (jalur mana)
        - out_of_road    : True jika keluar batas jalan
        - dist_to_center : jarak ke center jalur aktif (meter)
        """
        if self.vehicle is None:
            return None

        loc = self.vehicle.get_location()
        y   = loc.y

        out_of_road = (y < self.ROAD_Y_MIN or y > self.ROAD_Y_MAX)

        return {
            'current_y'      : y,
            'out_of_road'    : out_of_road,
        }


    # ══════════════════════════════════════════════════════════════
    # RESET & STEP
    # ══════════════════════════════════════════════════════════════

    def reset(self):
        """Reset environment, kembalikan state awal."""
        print("\n=== RESET ENVIRONMENT ===")
        self._cleanup()
        self._spawn_vehicle()
        self._setup_camera()
        self._setup_collision_sensor()
        self._setup_imu_sensor()

        print("Menunggu sensors ready...")
        for _ in range(20):
            frame = self.world.tick()          # [#19] tanpa sleep
            self._tunggu_kamera(frame)
            if self.current_image is not None and self.imu_data is not None:
                break

        self.collision_history  = []
        self.previous_location  = self.vehicle.get_location()
        self.start_location     = self.vehicle.get_location()
        self.previous_speed     = 0.0
        self.previous_steer     = 0.0

        self.pothole_hit_cooldown   = 0
        self.pothole_avoid_cooldown = 0
        self.total_hit_events       = 0
        self.total_avoid_events     = 0
        self.smoothed_severity      = 0.0
        self.current_step           = 0
        self.pothole_tracking = {}

        self.vehicle_state = {
            'speed'         : 0.0,
            'steering_angle': 0.0,
            'acceleration'  : np.zeros(3),
            'position'      : np.zeros(3),
            'collision'     : 0.0,
        }

        state = self._get_state()
        print("Reset selesai!")
        return state

    def step(self, action):
        """Eksekusi satu langkah simulasi."""
        self._apply_action(action)
        self.world_frame = self.world.tick()     # [#19] tanpa sleep
        self._tunggu_kamera(self.world_frame)

        self._update_vehicle_state()
        self.current_step += 1

        if self.pothole_hit_cooldown > 0:
            self.pothole_hit_cooldown -= 1
        if self.pothole_avoid_cooldown > 0:
            self.pothole_avoid_cooldown -= 1

        state = self._get_state()
        reward, done = self._calculate_reward(state)

        info = {
            'hits'  : self.total_hit_events,
            'avoids': self.total_avoid_events,
        }
        return state, reward, done, info

    # ══════════════════════════════════════════════════════════════
    # SPAWN & SENSOR SETUP
    # ══════════════════════════════════════════════════════════════

    def _spawn_vehicle(self):
        """
        Spawn kendaraan terkecil (Microlino).
        Fallback bertingkat jika blueprint tidak tersedia.
        """
        lib = self.world.get_blueprint_library()

        # Cari blueprint utama, fallback jika perlu
        car_bp = None
        for bp_id in [self.VEHICLE_BLUEPRINT] + self.VEHICLE_FALLBACKS:
            candidates = lib.filter(bp_id)
            if len(candidates) > 0:
                car_bp = candidates[0]
                if bp_id != self.VEHICLE_BLUEPRINT:
                    print(f"⚠️  Microlino tidak ditemukan, fallback ke: {bp_id}")
                break

        if car_bp is None:
            raise RuntimeError("Tidak ada blueprint kendaraan yang tersedia!")

        print(f"🚗 Blueprint: {car_bp.id}")

        sp = self.custom_spawn_transform
        # [#19] offset acak dengan seed (seed None = tanpa offset, perilaku asli Dika)
        if self.episode_seed is not None:
            rng = random.Random(self.episode_seed)
            self.spawn_offset = (rng.uniform(-self.offset_maks_x, self.offset_maks_x),
                                 rng.uniform(-self.offset_maks_y, self.offset_maks_y))
        else:
            self.spawn_offset = (0.0, 0.0)
        safe_sp = carla.Transform(
            carla.Location(x=sp.location.x + self.spawn_offset[0],
                           y=sp.location.y + self.spawn_offset[1],
                           z=sp.location.z + 0.5),
            sp.rotation
        )

        try:
            self.vehicle = self.world.spawn_actor(car_bp, safe_sp)
            print(f"✅ Spawn: ({safe_sp.location.x:.1f}, "
                  f"{safe_sp.location.y:.1f}, {safe_sp.location.z:.1f})")
        except Exception as e:
            print(f"⚠️  Spawn eksplisit gagal: {e}")
            spawn_points = self.world.get_map().get_spawn_points()
            if spawn_points:
                idx = (self.spawn_index
                       if self.spawn_index is not None
                       and 0 <= self.spawn_index < len(spawn_points)
                       else 0)
                self.vehicle = self.world.spawn_actor(car_bp, spawn_points[idx])
                print(f"   Fallback spawn index {idx}")
            else:
                raise RuntimeError("Tidak ada spawn point tersedia!")

    def _setup_camera(self):
        """RGB camera — pitch -15° untuk melihat jalan di depan."""
        cam_bp = self.world.get_blueprint_library().find('sensor.camera.rgb')
        cam_bp.set_attribute('image_size_x', '640')
        cam_bp.set_attribute('image_size_y', '640')
        cam_bp.set_attribute('fov', '90')

        tf = carla.Transform(
            carla.Location(x=1.5, z=2.0),
            carla.Rotation(pitch=-15)
        )
        self.camera = self.world.spawn_actor(cam_bp, tf, attach_to=self.vehicle)
        self.camera_frame = -1                    # [#19]
        self.camera.listen(lambda img: self._process_camera(img))
        print("✅ Camera setup")

    def _process_camera(self, image):
        arr = np.frombuffer(image.raw_data, dtype=np.uint8)
        arr = arr.reshape((image.height, image.width, 4))
        self.current_image = arr[:, :, :3]
        self.camera_frame = image.frame           # [#19]

    def _tunggu_kamera(self, frame, timeout=2.0):
        """[#19] Pengganti time.sleep: tunggu sampai gambar kamera untuk frame ini tiba."""
        t0 = time.perf_counter()
        while self.camera_frame < frame:
            if time.perf_counter() - t0 > timeout:
                self.kamera_telat += 1
                break
            time.sleep(0.0005)

    def _setup_collision_sensor(self):
        bp = self.world.get_blueprint_library().find('sensor.other.collision')
        self.collision_sensor = self.world.spawn_actor(
            bp, carla.Transform(), attach_to=self.vehicle)
        self.collision_sensor.listen(
            lambda e: self.collision_history.append(e))
        print("✅ Collision sensor setup")

    def _setup_imu_sensor(self):
        bp = self.world.get_blueprint_library().find('sensor.other.imu')
        self.imu_sensor = self.world.spawn_actor(
            bp, carla.Transform(), attach_to=self.vehicle)
        self.imu_sensor.listen(lambda d: self._process_imu(d))
        print("✅ IMU sensor setup")

    def _process_imu(self, data):
        self.imu_data = data

    # ══════════════════════════════════════════════════════════════
    # ACTION
    # ══════════════════════════════════════════════════════════════

    def _apply_action(self, action):
        ctrl = carla.VehicleControl()
        if   action == 0:   # Straight
            ctrl.throttle, ctrl.steer = 0.3, 0.0
        elif action == 1:   # Left dodge
            ctrl.throttle, ctrl.steer = 0.3, -0.35
        elif action == 2:   # Right dodge
            ctrl.throttle, ctrl.steer = 0.3, +0.35
        self.vehicle.apply_control(ctrl)

    # ══════════════════════════════════════════════════════════════
    # STATE
    # ══════════════════════════════════════════════════════════════

    def _get_state(self):
        """
        Return dict:
          'image'         : (84,84,3) uint8
          'vehicle_state' : (10,) float32  [YOLO(5) + Vehicle(5)]
          'pothole_detected', 'pothole_severity', 'pothole_y'
        """
        if self.current_image is None:
            image        = np.zeros((84, 84, 3), dtype=np.uint8)
            pothole_data = np.zeros(5, dtype=np.float32)
        else:
            image        = cv2.resize(self.current_image, (84, 84))
            pothole_data = self._detect_potholes_yolo(self.current_image)

        vehicle_vec      = self._normalize_vehicle_state()
        full_state_vec   = np.concatenate([pothole_data, vehicle_vec])

        return {
            'image'            : image,
            'vehicle_state'    : full_state_vec,
            'pothole_detected' : pothole_data[4] > 0.0,
            'pothole_severity' : float(pothole_data[4]),
            'pothole_y'        : float(pothole_data[1]),
        }

    def _detect_potholes_yolo(self, image):
        """
        YOLO inference → [cx, cy, w, h, severity] ternormalisasi 0-1.
        Hanya untuk STATE / persepsi agen, bukan reward.
        """
        if self.yolo_model is None:
            return np.zeros(5, dtype=np.float32)

        try:
            import torch
            with torch.no_grad():
                results = self.yolo_model(
                    image, imgsz=320, conf=0.05, verbose=False,
                    device='cuda' if torch.cuda.is_available() else 'cpu'
                )
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            if len(results) > 0 and len(results[0].boxes) > 0:
                boxes      = results[0].boxes
                best_idx   = int(np.argmax(boxes.conf.cpu().numpy()))
                x1,y1,x2,y2 = boxes.xyxy[best_idx].cpu().numpy()
                ih, iw     = image.shape[:2]

                cx  = ((x1+x2)/2) / iw
                cy  = ((y1+y2)/2) / ih
                w   = (x2-x1) / iw
                h   = (y2-y1) / ih

                cls = int(boxes.cls[best_idx].cpu().numpy())
                raw_sev = {0: 0.6, 1: 0.9, 2: 0.3}.get(cls, 0.5)

                # EMA smoothing
                if self.smoothed_severity == 0.0:
                    self.smoothed_severity = raw_sev
                else:
                    self.smoothed_severity = (0.7 * self.smoothed_severity
                                              + 0.3 * raw_sev)
                return np.array([cx, cy, w, h, self.smoothed_severity],
                                dtype=np.float32)
            else:
                self.smoothed_severity = 0.0

        except Exception as e:
            print(f"⚠️  YOLO error: {e}")
            self.smoothed_severity = 0.0

        return np.zeros(5, dtype=np.float32)

    def _normalize_vehicle_state(self):
        speed_n   = np.clip(self.vehicle_state['speed'] / 60.0, 0.0, 1.0)
        steer_n   = self.vehicle_state['steering_angle']
        accel_n   = np.clip(np.linalg.norm(
                        self.vehicle_state['acceleration']) / 10.0, 0.0, 1.0)
        col_n     = self.vehicle_state['collision']
        road_center_y = (self.ROAD_Y_MIN + self.ROAD_Y_MAX) / 2.0  # 249.05
        road_half_w   = (self.ROAD_Y_MAX - self.ROAD_Y_MIN) / 2.0  # 3.5
        loc = self.vehicle.get_location()
        pos_n = np.clip((loc.y - road_center_y) / road_half_w, -1.0, 1.0)
        
        return np.array([speed_n, steer_n, accel_n, pos_n, col_n],
                        dtype=np.float32)

    def _update_vehicle_state(self):
        if self.vehicle is None:
            return
        vel   = self.vehicle.get_velocity()
        speed = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
        self.vehicle_state['speed'] = speed * 3.6

        ctrl  = self.vehicle.get_control()
        self.vehicle_state['steering_angle'] = ctrl.steer

        if self.imu_data is not None:
            a = self.imu_data.accelerometer
            self.vehicle_state['acceleration'] = np.array([a.x, a.y, a.z])

        loc = self.vehicle.get_location()
        self.vehicle_state['position'] = np.array([loc.x, loc.y, loc.z])
        self.vehicle_state['collision'] = (1.0
            if len(self.collision_history) > 0 else 0.0)

    # ══════════════════════════════════════════════════════════════
    # REWARD
    # ══════════════════════════════════════════════════════════════

    def _calculate_reward(self, state=None):
        reward = 0.0
        done   = False

        # 1. COLLISION FATAL
        if len(self.collision_history) > 0:
            self.collision_history.clear()
            return -300.0, True
        
        # ── 2. Y-AXIS BOUNDARY → OUT OF ROAD ────────────────────────
        lane_info = self._get_lane_info()
        if lane_info and lane_info['out_of_road']:
            y = lane_info['current_y']
            print(f"🚧 OUT OF ROAD! Y={y:.2f} (batas: {self.ROAD_Y_MIN} ~ {self.ROAD_Y_MAX})")
            return self.OUT_OF_ROAD_PENALTY, True   


        # 2. GOAL
        current_loc = self.vehicle.get_location()
        if current_loc.x > self.finish_x_threshold:
            return 800.0, True

        # 3. TIMEOUT
        if self.current_step >= self.max_steps_per_episode:
            return -10.0, True

        # 4. POTHOLE — hanya punishment jika HIT
        vehicle_tf = self.vehicle.get_transform()
        closest    = self.gt.get_closest_ahead(current_loc, vehicle_tf, max_dist=20.0)
        pothole_near = closest is not None

        if pothole_near:
            d        = closest['distance']
            severity = closest['severity']
            extent_x = closest['extent_x']
            lat_abs  = abs(closest['lateral_offset_m'])
            hit_thresh = extent_x + self.VEHICLE_HALF_WIDTH + self.HIT_MARGIN_M
            ph_id    = closest['id']

            if ph_id not in self.pothole_tracking:
                self.pothole_tracking[ph_id] = {'hit': False, 'rewarded': False}

            # Hanya hukum saat benar-benar melewati lubang
            if d < 2.0 and self.pothole_hit_cooldown == 0:
                if lat_abs < hit_thresh:
                    penalty = 200.0 * severity
                    reward -= penalty
                    self.total_hit_events     += 1
                    self.pothole_hit_cooldown  = 100
                    self.pothole_tracking[ph_id]['hit']     = True
                    self.pothole_tracking[ph_id]['rewarded'] = True  
                    print(f"🕳️  HIT! {ph_id} | sev={severity:.1f} | penalty={penalty:.1f}")

        # ── 6. POTHOLE: AVOID REWARD (X-axis crossing) ───────────
        #
        # Logika: setiap lubang punya posisi X di dunia (dari GT JSON).
        # Saat posisi X mobil sudah melewati X lubang + panjang setengah mobil,
        # artinya mobil sudah benar-benar melewati lubang itu.
        # Kalau tidak pernah kena (hit=False) → beri reward.
        #
        for ph in self.gt.potholes:
            ph_id = ph['id']

            if ph_id not in self.pothole_tracking:
                self.pothole_tracking[ph_id] = {'hit': False, 'rewarded': False}

            entry = self.pothole_tracking[ph_id]

            # Belum diberi reward dan posisi X mobil sudah melewati X lubang
            if not entry['rewarded']:
                pothole_x  = ph['loc'].x
                # Tambah VEHICLE_HALF_LEN agar mobil benar-benar sudah melewati
                if current_loc.x > pothole_x + self.VEHICLE_HALF_LEN:
                    if not entry['hit']:
                        avoid_reward = 50.0 * ph['severity']
                        # severity 0.6 → +30 | severity 0.9 → +45
                        reward += avoid_reward
                        self.total_avoid_events += 1
                        print(f"✅ AVOIDED {ph_id} | sev={ph['severity']:.1f} | reward={avoid_reward:.1f}")
                    # Tandai sudah diproses (hit atau avoid), jangan reward lagi
                    entry['rewarded'] = True


        # 5. MOVEMENT INCENTIVE — dorong agen terus bergerak
        speed = self.vehicle_state['speed']
        if 5.0 <= speed <= 15.0:
            reward += speed / 15.0 * 0.5
        else:
            reward -= 0.5

        # 6. STEERING PENALTY — jalan lurus saat bebas lubang
        yolo_detected = (state is not None and state.get('pothole_detected', False))

        if not pothole_near and not yolo_detected:
            reward -= abs(self.vehicle_state['steering_angle']) * 1.0

        self.previous_speed = speed
        self.previous_steer = self.vehicle_state['steering_angle']
        return reward, done

    # ══════════════════════════════════════════════════════════════
    # CLEANUP
    # ══════════════════════════════════════════════════════════════

    def _cleanup(self):
        for actor in [self.camera, self.collision_sensor,
                      self.imu_sensor, self.vehicle]:
            if actor is not None:
                try:
                    actor.destroy()
                except Exception:
                    pass
        self.vehicle = self.camera = None
        self.collision_sensor = self.imu_sensor = None

    def close(self):
        self._cleanup()
        settings = self.world.get_settings()
        settings.synchronous_mode = False
        self.world.apply_settings(settings)
        print("Environment ditutup.")

    # ══════════════════════════════════════════════════════════════
    # DEBUG
    # ══════════════════════════════════════════════════════════════

    def get_vehicle_state_info(self):
        state        = self._get_state()
        pothole_data = state['vehicle_state'][:5]
        vehicle_tf   = self.vehicle.get_transform()
        closest      = self.gt.get_closest_ahead(
                           self.vehicle.get_location(), vehicle_tf)

        print(f"\n🚗 Vehicle State:")
        print(f"   Speed    : {self.vehicle_state['speed']:.2f} km/h")
        print(f"   Steering : {self.vehicle_state['steering_angle']:.3f}")
        print(f"   Accel    : {np.linalg.norm(self.vehicle_state['acceleration']):.2f} m/s²")
        print(f"   Position : ({self.vehicle_state['position'][0]:.1f}, "
              f"{self.vehicle_state['position'][1]:.1f})")

        print(f"\n📷 YOLO Detection:")
        if pothole_data[4] > 0.0:
            print(f"   cx={pothole_data[0]:.2f}  cy={pothole_data[1]:.2f}  "
                  f"w={pothole_data[2]:.2f}  h={pothole_data[3]:.2f}  "
                  f"sev={pothole_data[4]:.2f}")
        else:
            print("   Tidak terdeteksi")

        print(f"\n🗺️  Ground Truth (terdekat di depan):")
        if closest:
            ext_x  = closest['extent_x']
            lat    = abs(closest['lateral_offset_m'])
            ht     = ext_x + self.VEHICLE_HALF_WIDTH + self.HIT_MARGIN_M
            at     = ext_x + self.VEHICLE_HALF_WIDTH + self.AVOID_MARGIN_M
            status = ("HIT ZONE"   if lat < ht
                      else "AVOID ZONE" if lat > at
                      else "GREY ZONE")
            print(f"   ID       : {closest['id']} ({closest['label']})")
            print(f"   Jarak    : {closest['distance']:.2f} m")
            print(f"   Lateral  : {lat:.2f} m")
            print(f"   extent_x : {ext_x:.2f} m  (full {ext_x*2:.2f} m)")
            print(f"   Hit  <   : {ht:.2f} m")
            print(f"   Avoid >  : {at:.2f} m")
            print(f"   Status   : {status}")
        else:
            print("   Tidak ada lubang di depan")