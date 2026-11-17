import os
import csv
import cv2
import numpy as np
import time
import carla
import argparse, math   # [#19]

from environment.carla_env import CarlaEnv
from agent.dqn_agent import DQNAgent

# =====================================================================
# KONFIGURASI TESTING
# =====================================================================
# [#19] konfigurasi lewat argumen; folder keluaran baru supaya data Dika tidak tertimpa
_ap = argparse.ArgumentParser()
_ap.add_argument("--cuaca", default="ClearNoon", help="nama carla.WeatherParameters, mis. ClearNoon, HardRainNoon, ClearNight")
_ap.add_argument("--episodes", type=int, default=1)
_ap.add_argument("--seed_awal", type=int, default=0, help="seed episode ke-k = seed_awal + k - 1")
_ap.add_argument("--offset_x", type=float, default=2.0, help="offset spawn longitudinal maks (m)")
_ap.add_argument("--offset_y", type=float, default=0.5, help="offset spawn lateral maks (m); jangan > 1,0")
_ap.add_argument("--tampil", type=int, default=1, help="1 = jendela cv2, 0 = tanpa jendela (lebih cepat)")
_ap.add_argument("--video", type=int, default=0, help="1 = rekam mp4 (makan disk)")
ARGS = _ap.parse_args()

MODEL_PATH   = "model_best.h5"
NUM_EPISODES = ARGS.episodes
MAX_STEPS    = 10000

CUACA        = ARGS.cuaca
TEST_WEATHER = getattr(carla.WeatherParameters, CUACA)

RECORD_VIDEO = bool(ARGS.video)
TAMPIL       = bool(ARGS.tampil)
STAMP        = time.strftime("%Y%m%d_%H%M%S")
RUN_DIR      = os.path.join("log_runner", f"{STAMP}_{CUACA}")
VIDEO_DIR    = os.path.join(RUN_DIR, "video")
DATA_DIR     = RUN_DIR

ACTION_LABELS = {
    0: "STRAIGHT", 1: "LEFT", 2: "RIGHT", 3: "FASTER",
    4: "BRAKE", 5: "LEFT-FAST", 6: "RIGHT-FAST"
}
ACTION_COLORS = {
    0: (0, 200, 255), 1: (0, 200, 255), 2: (200, 200, 200),
    3: (0, 255, 100), 4: (0, 60, 255), 5: (0, 140, 255), 6: (0, 140, 255)
}

# =====================================================================
# KELAS SENSOR MANAJER
# =====================================================================
class SensorManager:
    """
    Mengelola IMU dan pengambilan data akselerasi + kecepatan horizontal.
    Mengambil env langsung (bukan vehicle) agar selalu up-to-date setelah reset.
    """
    def __init__(self, env):
        self.env = env
        self.imu_data = {
            'accel_x': 0.0,
            'accel_y': 0.0,
            'accel_z': 0.0,
            'timestamp': 0.0
        }
        self._imu_sensor = None
        self._setup_imu()

    def _setup_imu(self):
        imu_bp = self.env.world.get_blueprint_library().find('sensor.other.imu')
        imu_transform = carla.Transform(carla.Location(x=0.0, y=0.0, z=0.0))
        self._imu_sensor = self.env.world.spawn_actor(
            imu_bp, imu_transform, attach_to=self.env.vehicle
        )
        self._imu_sensor.listen(self._on_imu_event)
        print("✅ IMU Sensor (SensorManager) terpasang.")

    def _on_imu_event(self, imu_measurement):
        self.imu_data['accel_x'] = imu_measurement.accelerometer.x
        self.imu_data['accel_y'] = imu_measurement.accelerometer.y
        self.imu_data['accel_z'] = imu_measurement.accelerometer.z
        self.imu_data['timestamp'] = imu_measurement.timestamp

    def get_horizontal_speed(self):
        if self.env.vehicle is None:
            return 0.0
        vel = self.env.vehicle.get_velocity()
        return np.sqrt(vel.x**2 + vel.y**2) * 3.6

    def get_sensor_readings(self):
        return {
            'accel_horizontal_x':   round(self.imu_data['accel_x'], 4),
            'accel_horizontal_y':   round(self.imu_data['accel_y'], 4),
            'accel_vertical_z':     round(self.imu_data['accel_z'], 4),
            'speed_horizontal_kmh': round(self.get_horizontal_speed(), 3),
            'imu_timestamp':        self.imu_data['timestamp']
        }

    def reattach(self):
        self.destroy()
        self.imu_data = {'accel_x': 0.0, 'accel_y': 0.0,
                         'accel_z': 0.0, 'timestamp': 0.0}
        self._imu_sensor = None
        self._setup_imu()
        print("🔄 IMU Sensor di-attach ulang ke vehicle baru.")

    def destroy(self):
        if self._imu_sensor is not None:
            try:
                self._imu_sensor.stop()
                self._imu_sensor.destroy()
            except Exception:
                pass
            self._imu_sensor = None
            print("🧹 IMU Sensor (SensorManager) dihapus.")


# =====================================================================
# CSV DATA LOGGER
# =====================================================================
class DataLogger:
    def __init__(self, filepath):
        self.filepath = filepath
        self.file = open(filepath, 'w', newline='')
        self.writer = csv.DictWriter(self.file, fieldnames=[
            'episode', 'step', 'timestamp',
            'speed_horizontal_kmh',
            'accel_horizontal_x', 'accel_horizontal_y',
            'accel_vertical_z',
            'action', 'reward', 'cumulative_reward',
            'pothole_detected', 'pothole_severity',
            'hits', 'avoids'
        ])
        self.writer.writeheader()
        print(f"📝 Data logger aktif: {filepath}")

    def log(self, episode, step, sensor_readings, action, reward,
            cumulative_reward, state, info):
        self.writer.writerow({
            'episode':              episode,
            'step':                 step,
            'timestamp':            sensor_readings['imu_timestamp'],
            'speed_horizontal_kmh': sensor_readings['speed_horizontal_kmh'],
            'accel_horizontal_x':   sensor_readings['accel_horizontal_x'],
            'accel_horizontal_y':   sensor_readings['accel_horizontal_y'],
            'accel_vertical_z':     sensor_readings['accel_vertical_z'],
            'action':               ACTION_LABELS.get(action, action),
            'reward':               round(reward, 4),
            'cumulative_reward':    round(cumulative_reward, 4),
            'pothole_detected':     int(state.get('pothole_detected', 0)),
            'pothole_severity':     round(state.get('pothole_severity', 0.0), 4),
            'hits':                 info.get('hits', 0),
            'avoids':               info.get('avoids', 0),
        })

    def close(self):
        self.file.close()
        print(f"💾 Data disimpan: {self.filepath}")


# =====================================================================
# HELPER: WARNA YOLO BERDASARKAN SEVERITY
# =====================================================================
def _yolo_color(sev: float):
    """Mengembalikan warna BGR berdasarkan severity pothole."""
    if sev < 0.5:
        return (80, 200, 80)      # Hijau  — LOW
    elif sev < 0.75:
        return (80, 165, 220)     # Oranye — MEDIUM
    else:
        return (80, 80, 220)      # Merah  — HIGH


# =====================================================================
# FUNGSI OVERLAY UNTUK VIDEO
# =====================================================================
def draw_overlay(frame, state, env_info, action, reward, cumulative_reward,
                 step, ep, sensor_readings, pothole_data):
    """
    Menggambar overlay di atas frame kamera CARLA.

    Parameters
    ----------
    pothole_data : np.ndarray shape (5,)
        [cx_norm, cy_norm, bw_norm, bh_norm, severity]
        Diambil dari state['vehicle_state'][:5].
        severity == 0.0 berarti tidak ada deteksi.
    """
    h, w = frame.shape[:2]

    # ── Panel kiri semi-transparan ─────────────────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (300, h), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

    y_pos = 25

    def put_text(text, color=(220, 220, 220), scale=0.52, bold=False):
        nonlocal y_pos
        thickness = 2 if bold else 1
        cv2.putText(frame, text, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, color, thickness, cv2.LINE_AA)
        y_pos += 23

    # ── Header ─────────────────────────────────────────────────────
    put_text(f"DQN TEST - EPISODE {ep}", (0, 255, 255), 0.6, True)
    put_text(f"Step  : {step}/{MAX_STEPS}")

    put_text(f"Speed : {sensor_readings['speed_horizontal_kmh']:.1f} km/h",
             (0, 255, 180))
    put_text("")

    # ── Action & Reward ────────────────────────────────────────────
    albl = ACTION_LABELS.get(action, f"ACT {action}")
    aclr = ACTION_COLORS.get(action, (200, 200, 200))
    put_text("--- ACTION ---", (200, 200, 0))
    put_text(f">> {albl}", aclr, 0.65, True)
    put_text(f"Step Rew: {reward:+.2f}")
    put_text(f"Total   : {cumulative_reward:+.1f}", (0, 255, 100))
    put_text("")

    # ── YOLO Detection ─────────────────────────────────────────────
    put_text("--- YOLO DETECTION ---", (200, 200, 0))
    sev = float(pothole_data[4]) if len(pothole_data) >= 5 else 0.0

    if sev > 0.0:
        label  = "LOW" if sev < 0.5 else ("MEDIUM" if sev < 0.75 else "HIGH")
        y_col  = _yolo_color(sev)
        cx_n   = float(pothole_data[0])
        cy_n   = float(pothole_data[1])
        put_text("TERDETEKSI", y_col, 0.58, True)
        put_text(f"Severity : {label} ({sev:.2f})", y_col)
        put_text(f"Pos (cx,cy): {cx_n:.2f}, {cy_n:.2f}", (200, 220, 255))
    else:
        put_text("Status: Clear", (100, 200, 100))
        put_text("")
        put_text("")

    put_text("")

    # ── Sensor IMU ─────────────────────────────────────────────────
    put_text("--- SENSOR IMU ---", (200, 200, 0))
    ax = sensor_readings['accel_horizontal_x']
    ay = sensor_readings['accel_horizontal_y']
    az = sensor_readings['accel_vertical_z']
    az_color = (0, 60, 255) if abs(az) > 2.0 else (180, 255, 180)
    put_text(f"Accel X (H): {ax:+.2f} m/s^2", (200, 220, 255))
    put_text(f"Accel Y (H): {ay:+.2f} m/s^2", (200, 220, 255))
    put_text(f"Accel Z (V): {az:+.2f} m/s^2", az_color, 0.55,
             bold=(abs(az) > 2.0))
    put_text("")

    # ── Stats ──────────────────────────────────────────────────────
    put_text("--- STATS ---", (200, 200, 0))
    put_text(f"Hits   : {env_info.get('hits', 0)}", (0, 60, 255))
    put_text(f"Avoids : {env_info.get('avoids', 0)}", (0, 255, 0))

    # ── Bounding box YOLO di frame ─────────────────────────────────
    if sev > 0.0:
        cx_n = float(pothole_data[0])
        cy_n = float(pothole_data[1])
        bw_n = float(pothole_data[2])
        bh_n = float(pothole_data[3])

        x1 = int((cx_n - bw_n / 2) * w)
        y1 = int((cy_n - bh_n / 2) * h)
        x2 = int((cx_n + bw_n / 2) * w)
        y2 = int((cy_n + bh_n / 2) * h)

        box_color = _yolo_color(sev)

        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

    return frame


# =====================================================================
# MAIN TESTING LOOP
# =====================================================================
def main():
    print("=" * 60)
    print("  EVALUASI MODEL DRL (TESTING & RECORDING)")
    print("=" * 60)

    for d in [VIDEO_DIR, DATA_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

    env = CarlaEnv(town='train_fix', weather=TEST_WEATHER)

    agent = DQNAgent(num_actions=env.num_actions)
    try:
        agent.load(MODEL_PATH)
        print(f"✅ Model {MODEL_PATH} berhasil dimuat.")
    except Exception as e:
        print(f"❌ Gagal memuat model: {e}")
        env.close()
        return

    agent.epsilon = 0.0

    env.offset_maks_x, env.offset_maks_y = ARGS.offset_x, ARGS.offset_y   # [#19]
    env.episode_seed = ARGS.seed_awal
    state = env.reset()
    sensor_mgr = SensorManager(env=env)

    csv_path = os.path.join(DATA_DIR, "sensor_log_all_episodes.csv")
    data_logger = DataLogger(csv_path)

    # [#19] ringkasan per episode (untuk #20: detik/episode)
    f_ring = open(os.path.join(RUN_DIR, "ringkasan_episode.csv"), "w", newline="")
    w_ring = csv.writer(f_ring)
    w_ring.writerow(["episode", "seed", "offset_x", "offset_y", "langkah", "detik", "faktor_realtime",
                     "hits", "avoids", "reward", "kamera_telat", "x_akhir"])

    try:
        for episode in range(1, NUM_EPISODES + 1):
            print(f"\n▶️  Memulai Episode {episode}")

            seed = ARGS.seed_awal + episode - 1          # [#19]
            if episode > 1:
                env.episode_seed = seed
                state = env.reset()
                sensor_mgr.reattach()

            done = False
            step = 0
            cumulative_reward = 0.0

            # [#19] log posisi per langkah
            f_pos = open(os.path.join(RUN_DIR, f"posisi_ep{episode:02d}_seed{seed}.csv"), "w", newline="")
            w_pos = csv.writer(f_pos)
            w_pos.writerow(["step", "t_sim", "frame_dunia", "frame_kamera", "x", "y", "yaw",
                            "v_kmh", "aksi", "deteksi", "hits", "avoids"])
            env.kamera_telat = 0
            info = {}
            t0 = time.perf_counter()

            video_writer = None
            if RECORD_VIDEO:
                filename = os.path.join(VIDEO_DIR, f"test_run_ep{episode}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (640, 640))
                print(f"🎥 Merekam ke: {filename}")

            while not done and step < MAX_STEPS:
                action = agent.select_action(state)
                next_state, reward, done, info = env.step(action)
                cumulative_reward += reward
                step += 1

                # [#19] posisi setelah tick
                snap = env.world.get_snapshot()
                tf = env.vehicle.get_transform(); v = env.vehicle.get_velocity()
                w_pos.writerow([step, round(snap.timestamp.elapsed_seconds, 3), env.world_frame, env.camera_frame,
                                round(tf.location.x, 4), round(tf.location.y, 4), round(tf.rotation.yaw, 3),
                                round(3.6 * math.hypot(v.x, v.y), 3), ACTION_LABELS.get(action, action),
                                int(next_state.get('pothole_detected', 0)) if isinstance(next_state, dict) else '',
                                info.get('hits', 0), info.get('avoids', 0)])

                # Ambil pothole_data dari vehicle_state[:5]
                # Format: [cx_norm, cy_norm, bw_norm, bh_norm, severity]
                pothole_data = np.array(state['vehicle_state'][:5], dtype=np.float32)

                sensor_readings = sensor_mgr.get_sensor_readings()

                data_logger.log(
                    episode=episode,
                    step=step,
                    sensor_readings=sensor_readings,
                    action=action,
                    reward=reward,
                    cumulative_reward=cumulative_reward,
                    state=state,
                    info=info
                )

                if TAMPIL and env.current_image is not None:   # [#19] jendela opsional
                    frame_bgr = cv2.cvtColor(env.current_image, cv2.COLOR_RGB2BGR)
                    display_frame = draw_overlay(
                        frame_bgr, state, info, action, reward,
                        cumulative_reward, step, episode,
                        sensor_readings, pothole_data   # <-- pothole_data diteruskan
                    )
                    cv2.imshow("CARLA Test - DRL Agent", display_frame)

                    if video_writer is not None:
                        video_writer.write(display_frame)

                state = next_state

                if TAMPIL and cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n⏹️  Dibatalkan oleh user (Tombol Q).")
                    done = True

            if video_writer is not None:
                video_writer.release()

            # [#19] ringkasan episode
            detik = time.perf_counter() - t0
            f_pos.close()
            w_ring.writerow([episode, seed, round(env.spawn_offset[0], 3), round(env.spawn_offset[1], 3), step,
                             round(detik, 1), round(step * 0.05 / detik, 2), info.get('hits', 0),
                             info.get('avoids', 0), round(cumulative_reward, 2), env.kamera_telat,
                             round(env.vehicle.get_location().x, 2)])
            f_ring.flush()
            print(f"EPISODE {episode}: {step} langkah, {detik:.1f} s, faktor real-time {step * 0.05 / detik:.2f}, "
                  f"kamera telat {env.kamera_telat}")

            print(
                f"📊 Ep {episode} | Steps: {step} | "
                f"Reward: {cumulative_reward:.2f} | "
                f"Hits: {info.get('hits', 0)} | Avoids: {info.get('avoids', 0)}"
            )

    except KeyboardInterrupt:
        print("\n⚠️  Dihentikan paksa (Ctrl+C).")

    finally:
        print("\n🧹 Membersihkan environment...")
        sensor_mgr.destroy()
        data_logger.close()
        f_ring.close()
        env.close()
        cv2.destroyAllWindows()
        print("✅ Testing Selesai.")
        print(f"📁 Data sensor tersimpan di: {csv_path}")


if __name__ == '__main__':
    main()