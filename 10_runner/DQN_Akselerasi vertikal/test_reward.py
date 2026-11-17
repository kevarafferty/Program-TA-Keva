"""
test_baseline_gui.py
====================
Menguji performa "Straight-Line Baseline" dengan visualisasi.
Reward dihitung sepenuhnya dari CarlaEnv._calculate_reward()
sehingga identik dengan kondisi training.

Strategi integrasi:
  - BaselineEnv meng-extend CarlaEnv
  - Override _calculate_reward() untuk menangkap breakdown komponen
    tanpa mengubah logika reward asli
  - Kontrol baseline: jalan lurus 20 km/h tanpa manuver elak
"""

import carla  # pyright: ignore[reportMissingImports]
import cv2
import numpy as np
import time
import math

from environment.carla_env import CarlaEnv  # reward, GT, sensor semua dari sini

# =====================================================================
# KONFIGURASI
# =====================================================================
TARGET_SPEED       = 20.0   # km/h baseline
MAX_EPISODE_STEPS  = 5000


# =====================================================================
# SUBCLASS: Tambah breakdown reward tanpa ubah logika asli
# =====================================================================
class BaselineEnv(CarlaEnv):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_reward_breakdown = {
            'collision'    : 0.0,
            'finish'       : 0.0,
            'hit_penalty'  : 0.0,
            'movement'     : 0.0,
            'steer_penalty': 0.0,
            'total'        : 0.0,
            'done_reason'  : '',
        }
        self.episode_rewards     = []
        self.total_potholes_seen = 0
        self._last_pothole_id    = None

    # ❌ JANGAN override _calculate_reward() lagi
    # Langsung pakai dari CarlaEnv — otomatis ikut versi terbaru

    def step(self, action):
        """Override step untuk catat breakdown setelah reward dihitung."""
        state, reward, done, info = super().step(action)
        self.episode_rewards.append(reward)
        # Rebuild breakdown dari state terakhir untuk GUI
        self._build_breakdown(reward, done)
        return state, reward, done, info

    def _build_breakdown(self, reward, done, done_reason=''):
        bd = {k: 0.0 for k in self.last_reward_breakdown}
        bd['done_reason'] = done_reason          # ← terima dari luar
        bd['total']       = reward
        bd['hit_penalty'] = -(50.0 * 0.6) if self.total_hit_events > getattr(self, '_prev_hits', 0) else 0.0
        bd['movement']    = (float(np.clip(self.vehicle_state['speed'] / 20.0, 0.0, 1.0))
                            if self.vehicle_state['speed'] >= 10.0 else -2.0)
        bd['steer_penalty'] = -abs(self.vehicle_state['steering_angle']) * 0.3
        self._prev_hits   = self.total_hit_events
        self.last_reward_breakdown = bd


# =====================================================================
# GUI HELPERS
# =====================================================================
def draw_overlay(frame, env: BaselineEnv, pothole_data: np.ndarray):
    """Overlay kiri: info reward breakdown + deteksi YOLO."""
    h, w    = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (330, h), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.45, frame, 0.55, 0)

    bd     = env.last_reward_breakdown
    speed  = env.vehicle_state['speed']

    # GT info
    vehicle_tf = env.vehicle.get_transform()
    closest    = env.gt.get_closest_ahead(
                     env.vehicle.get_location(), vehicle_tf, max_dist=20.0)

    y, dy = 20, 22

    def put(text, color=(220, 220, 220), scale=0.52):
        nonlocal y
        cv2.putText(frame, text, (8, y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
        y += dy

    def sign_color(val):
        return (80, 200, 80) if val >= 0 else (80, 80, 220)

    # ── Header ──
    put("=== BASELINE TEST ===", (0, 230, 230), 0.58)
    put(f"Speed : {speed:.0f} km/h  "
        f"Step : {env.current_step}/{env.max_steps_per_episode}",
        (180, 180, 180))
    put(f"Finish X >{env.finish_x_threshold:.0f}  "
        f"Cur X = {env.vehicle.get_location().x:.1f}", (180, 180, 180))
    put("")

    # ── YOLO detection ──
    sev = float(pothole_data[4])
    if sev > 0.0:
        label = ("LOW" if sev < 0.5
                 else ("MEDIUM" if sev < 0.75 else "HIGH"))
        col   = ((80, 200, 80) if sev < 0.5
                 else ((80, 165, 220) if sev < 0.75 else (80, 80, 220)))
        put("YOLO: TERDETEKSI", (0, 230, 230), 0.56)
        put(f"  Severity : {label} ({sev:.2f})", col)
        put(f"  Pos (cx,cy): {pothole_data[0]:.2f}, {pothole_data[1]:.2f}")
    else:
        put("YOLO: --", (100, 100, 100))
        put("")
        put("")

    # ── GT nearest ──
    put("")
    put("--- GT POTHOLE (terdekat) ---", (200, 200, 0))
    if closest:
        lat   = abs(closest['lateral_offset_m'])
        ex    = closest['extent_x']
        ht    = ex + env.VEHICLE_HALF_WIDTH + env.HIT_MARGIN_M
        at    = ex + env.VEHICLE_HALF_WIDTH + env.AVOID_MARGIN_M
        zone  = ("HIT ZONE"   if lat < ht
                 else ("AVOID ZONE" if lat > at else "GREY ZONE"))
        zcol  = ((80, 80, 220) if lat < ht
                 else ((80, 200, 80) if lat > at else (80, 165, 220)))
        put(f"  ID    : {closest['id']} ({closest['label']})")
        put(f"  Dist  : {closest['distance']:.1f} m")
        put(f"  Lat   : {lat:.2f} m  [hit<{ht:.2f} avoid>{at:.2f}]")
        put(f"  Zone  : {zone}", zcol, 0.56)
    else:
        put("  Tidak ada di depan", (100, 100, 100))
        put("")
        put("")
        put("")

    # ── Reward breakdown ──
    put("")
    put("--- REWARD BREAKDOWN ---", (200, 200, 0))
    components = [
        ("collision"    , bd['collision']),
        ("finish"       , bd['finish']),
        ("hit_penalty"  , bd['hit_penalty']),
        ("movement"     , bd['movement']),
        ("steer_penalty", bd['steer_penalty']),
    ]
    for name, val in components:
        if val != 0.0:
            put(f"  {name:<14}: {val:+.2f}", sign_color(val))
    put(f"  {'─'*22}", (120, 120, 120))
    put(f"  {'TOTAL':<14}: {bd['total']:+.2f}", sign_color(bd['total']), 0.58)

    cum = sum(env.episode_rewards) if env.episode_rewards else 0.0
    put(f"  {'CUMULATIVE':<14}: {cum:+.1f}", (220, 220, 0))

    # ── Statistik episode ──
    put("")
    put("--- STATISTIK ---", (200, 200, 0))
    total_enc = env.total_potholes_seen
    hit_r     = ((env.total_hit_events / total_enc * 100)
                 if total_enc > 0 else 0.0)
    put(f"  Lubang ditemui : {total_enc}")
    put(f"  Hit            : {env.total_hit_events}")
    put(f"  Avoid          : {env.total_avoid_events}")
    put(f"  Impact Rate    : {hit_r:.1f}%",
        (80, 80, 220) if hit_r > 50 else (80, 200, 80))

    # ── Event banner bawah ──
    if bd['hit_penalty'] < 0:
        cv2.rectangle(frame, (0, h-55), (w, h), (30, 0, 120), -1)
        cv2.putText(frame, "!! MENABRAK LUBANG !!",
                    (10, h-20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.72, (80, 80, 255), 2, cv2.LINE_AA)

    # ── Bounding box YOLO di frame ──
    if sev > 0.0:
        cx_n, cy_n = float(pothole_data[0]), float(pothole_data[1])
        bw_n, bh_n = float(pothole_data[2]), float(pothole_data[3])
        x1 = int((cx_n - bw_n / 2) * w)
        y1 = int((cy_n - bh_n / 2) * h)
        x2 = int((cx_n + bw_n / 2) * w)
        y2 = int((cy_n + bh_n / 2) * h)
        col = ((80, 200, 80) if sev < 0.5
               else ((80, 165, 220) if sev < 0.75 else (80, 80, 220)))
        cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
        cv2.putText(frame, f"{sev:.2f}", (x1, max(y1 - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, col, 1)

    return frame


def draw_graph(episode_rewards, max_points=200):
    """Grafik reward per step di bawah frame."""
    gw, gh = 640, 180
    graph  = np.full((gh, gw, 3), 20, dtype=np.uint8)

    if len(episode_rewards) < 2:
        return graph

    recent  = episode_rewards[-max_points:]
    n       = len(recent)
    min_v   = min(recent)
    max_v   = max(recent)
    if max_v == min_v:
        max_v = min_v + 1.0

    def to_px(val, i):
        x = int(i / max(n - 1, 1) * (gw - 1))
        y = int((1.0 - (val - min_v) / (max_v - min_v)) * (gh - 20)) + 10
        return x, y

    # Garis nol
    y0 = to_px(0.0, 0)[1]
    cv2.line(graph, (0, y0), (gw, y0), (80, 80, 80), 1)

    # Garis reward
    for i in range(1, n):
        p1 = to_px(recent[i - 1], i - 1)
        p2 = to_px(recent[i],     i)
        col = (80, 200, 80) if recent[i] >= 0 else (80, 80, 220)
        cv2.line(graph, p1, p2, col, 1)

    # Label
    cv2.putText(graph,
                f"Reward/step  min={min_v:.1f}  max={max_v:.1f}"
                f"  last={recent[-1]:+.2f}",
                (5, gh - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 150, 150), 1)
    return graph


# =====================================================================
# MAIN
# =====================================================================
def main():
    print("Inisialisasi BaselineEnv...")

    env = BaselineEnv(
        town            = 'train_fix',
        yolo_model_path = 'Yolo/best_pure.pt',
        gt_json_path    = 'pothole_gt.json',
        weather         = carla.WeatherParameters.ClearNoon,
    )

    # reset() melakukan spawn, setup sensor, dll — persis seperti training
    state = env.reset()

    # Inisialisasi step counter (dipakai _calculate_reward)
    env.current_step = 0

    print("\n[Baseline: jalan lurus 20 km/h, tanpa manuver elak]")
    print("Tekan 'q' pada window OpenCV untuk keluar.\n")

    done = False

    try:
        while not done and env.current_step < MAX_EPISODE_STEPS:

            # ── Kontrol baseline: throttle PID, steer = 0 ──────────
            speed    = env.vehicle_state['speed']
            throttle = 0.3 if speed < TARGET_SPEED else 0.0
            ctrl     = carla.VehicleControl(throttle=throttle,
                                             steer=0.0,
                                             brake=0.0)
            env.vehicle.apply_control(ctrl)

            # ── Tick simulasi ──────────────────────────────────────
            env.world.tick()
            env.current_step += 1

            if env.pothole_hit_cooldown  > 0: env.pothole_hit_cooldown  -= 1
            if env.pothole_avoid_cooldown > 0: env.pothole_avoid_cooldown -= 1

            env._update_vehicle_state()

            # ── State & reward (dari CarlaEnv via override) ────────
            state          = env._get_state()
            reward, done   = env._calculate_reward(state)
            # FIX 1: Catat reward ke episode_rewards (dulu dilakukan oleh step())
            env.episode_rewards.append(reward)

            # FIX 2: Catat done_reason saat episode berakhir
            if done:
                loc = env.vehicle.get_location()
                if len(env.collision_history) > 0:
                    env.last_reward_breakdown['done_reason'] = 'collision'
                elif loc.x > env.finish_x_threshold:
                    env.last_reward_breakdown['done_reason'] = 'finish'
                else:
                    env.last_reward_breakdown['done_reason'] = 'timeout'

            # FIX 3: Hitung pothole unik yang dihadapi
            vehicle_tf = env.vehicle.get_transform()
            closest_dbg = env.gt.get_closest_ahead(
                env.vehicle.get_location(), vehicle_tf, max_dist=20.0)
            if closest_dbg is not None and closest_dbg['distance'] < 15.0:
                if closest_dbg['id'] != env._last_pothole_id:
                    env._last_pothole_id    = closest_dbg['id']
                    env.total_potholes_seen += 1

            # Update breakdown untuk GUI
            done_reason = ''
            if done:
                loc = env.vehicle.get_location()
                if reward == -100.0:
                    done_reason = 'collision'
                elif loc.x > env.finish_x_threshold:
                    done_reason = 'finish'
                else:
                    done_reason = 'timeout'
           
            env._build_breakdown(reward, done)
            # Ambil pothole_data untuk overlay
            pothole_data   = state['vehicle_state'][:5]

            # ── Spectator follow ───────────────────────────────────
            try:
                spec = env.world.get_spectator()
                vt   = env.vehicle.get_transform()
                spec.set_transform(carla.Transform(
                    vt.location + carla.Location(z=12, x=-8),
                    carla.Rotation(pitch=-35, yaw=vt.rotation.yaw)
                ))
            except Exception:
                pass

            # ── GUI ────────────────────────────────────────────────
            if env.current_image is not None:
                frame   = env.current_image.copy()
                display = draw_overlay(frame, env, pothole_data)
                graph   = draw_graph(env.episode_rewards)

                dh, dw     = display.shape[:2]
                graph_rsz  = cv2.resize(graph, (dw, 180))
                combined   = np.vstack([display, graph_rsz])

                cv2.imshow("Baseline Test — CARLA", combined)
                if cv2.waitKey(1) == ord('q'):
                    print("Keluar manual.")
                    break

    except KeyboardInterrupt:
        print("\nDihentikan manual (Ctrl+C).")

    finally:
        cv2.destroyAllWindows()
        env.close()

        # ── Ringkasan akhir ────────────────────────────────────────
        total_enc = env.total_potholes_seen
        impact_r  = ((env.total_hit_events / total_enc * 100)
                     if total_enc > 0 else 0.0)
        cumulative = sum(env.episode_rewards) if env.episode_rewards else 0.0

        print(f"\n{'='*52}")
        print(f"  HASIL EVALUASI STRAIGHT-LINE BASELINE")
        print(f"{'='*52}")
        print(f"  Total Steps          : {env.current_step}")
        print(f"  Potholes Ditemui     : {total_enc}")
        print(f"  Potholes Hit         : {env.total_hit_events}")
        print(f"  Potholes Avoided     : {env.total_avoid_events}")
        print(f"  Impact Rate          : {impact_r:.1f}%")
        print(f"  Cumulative Reward    : {cumulative:.1f}")
        print(f"  Done Reason          : "
              f"{env.last_reward_breakdown['done_reason'] or 'manual/step_limit'}")
        print(f"{'='*52}\n")


if __name__ == '__main__':
    main()