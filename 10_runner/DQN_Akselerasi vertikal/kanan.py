"""
test_kanan.py
==============
Script untuk menguji mobil belok KANAN keluar jalan dan
mengetes respons sensor collision.
"""

import carla  # type: ignore
import cv2
import numpy as np
import time
import math
import queue
from ultralytics import YOLO  # type: ignore

MODEL_PATH = "Yolo/best_pure.pt"
CONFIDENCE_THRESHOLD = 0.3

TARGET_SPAWN_POINT = carla.Transform(
    carla.Location(x=-299.5, y=250.5, z=3),
    carla.Rotation(yaw=0)
)

K1, K2, K3 = 3.0, 0.5, 0.5
DT = 0.05
TARGET_SPEED = 30.0

class RewardCalculator:
    def __init__(self):
        self.previous_accel = 0.0
        self.previous_steer = 0.0
        self.previous_location = None
        self.pothole_hit_cooldown = 0
        self.pothole_avoid_cooldown = 0
        self.total_hit_events = 0
        self.total_avoid_events = 0
        self.total_reward = 0.0
        self.episode_step = 0
        self.reward_history, self.safety_history, self.avoid_history, self.step_history = [], [], [], []
    
    def calculate(self, vehicle, imu_data, pothole_data):
        if self.pothole_hit_cooldown > 0: self.pothole_hit_cooldown -= 1
        if self.pothole_avoid_cooldown > 0: self.pothole_avoid_cooldown -= 1
        
        vel = vehicle.get_velocity()
        speed_kmh = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2) * 3.6
        current_steer = vehicle.get_control().steer
        accel_magnitude = math.sqrt(imu_data.accelerometer.x**2 + imu_data.accelerometer.y**2 + imu_data.accelerometer.z**2) if imu_data else 0.0
        current_location = vehicle.get_location()
        
        pothole_x, pothole_y, pothole_w, pothole_severity = float(pothole_data[0]), float(pothole_data[1]), float(pothole_data[2]), float(pothole_data[4])
        pothole_detected = pothole_severity > 0.0
        
        R_safety, hit_event, avoid_event = 0.0, False, False
        if pothole_detected:
            lateral_dist = abs(pothole_x - 0.5)
            if pothole_y > 0.82 and lateral_dist < 0.2 and pothole_w > 0.05:
                if self.pothole_hit_cooldown == 0:
                    R_safety, self.pothole_hit_cooldown, hit_event = -50.0 * pothole_severity, 20, True
                    self.total_hit_events += 1
            elif pothole_y > 0.65:
                R_safety = -20.0 * ((pothole_y - 0.65) / 0.35) * pothole_severity
        
        R_avoid = 0.0
        if pothole_detected and pothole_y > 0.65 and abs(pothole_x - 0.5) > 0.25:
            R_avoid = 15.0 * pothole_severity * abs(pothole_x - 0.5)
            if pothole_y > 0.8 and self.pothole_avoid_cooldown == 0:
                avoid_event, self.pothole_avoid_cooldown = True, 20
                self.total_avoid_events += 1
        
        R_comfort = -0.3 * (abs(accel_magnitude - self.previous_accel) / DT) - 8.0 * abs(current_steer - self.previous_steer)
        R_eff = -0.1 * abs(speed_kmh - TARGET_SPEED) + (0.5 if 25.0 <= speed_kmh <= 40.0 else 0.0) - (2.0 if speed_kmh < 5.0 else 0.0)
        R_forward = (math.sqrt((current_location.x - self.previous_location.x)**2 + (current_location.y - self.previous_location.y)**2) * 0.5) if self.previous_location else 0.0
        
        total = K1 * R_safety + R_avoid + K2 * R_comfort + K3 * R_eff + R_forward
        self.total_reward += total
        self.episode_step += 1
        self.previous_accel, self.previous_steer, self.previous_location = accel_magnitude, current_steer, current_location
        self.reward_history.append(total)
        self.safety_history.append(K1 * R_safety)
        self.avoid_history.append(R_avoid)
        
        return {'total': total, 'cumulative': self.total_reward, 'speed_kmh': speed_kmh, 'hit_event': hit_event, 'avoid_event': avoid_event}

def main():
    print("=" * 60)
    print("  TEST BELOK KANAN + COLLISION SENSOR")
    print("=" * 60)
    
    model = YOLO(MODEL_PATH)
    client = carla.Client('localhost', 2000)
    client.set_timeout(15.0)
    world = client.get_world()
    world.set_weather(carla.WeatherParameters.ClearNoon)
    
    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]
    
    spawn_loc = carla.Transform(carla.Location(x=TARGET_SPAWN_POINT.location.x, y=TARGET_SPAWN_POINT.location.y, z=TARGET_SPAWN_POINT.location.z + 0.5), TARGET_SPAWN_POINT.rotation)
    vehicle = world.spawn_actor(vehicle_bp, spawn_loc)
    vehicle.set_autopilot(False)
    
    # Sensors
    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', '640'); camera_bp.set_attribute('image_size_y', '480'); camera_bp.set_attribute('fov', '90')
    camera = world.spawn_actor(camera_bp, carla.Transform(carla.Location(x=1.5, z=2.0), carla.Rotation(pitch=-15)), attach_to=vehicle)
    
    imu_sensor = world.spawn_actor(blueprint_library.find('sensor.other.imu'), carla.Transform(), attach_to=vehicle)
    
    # TAMBAHAN: Sensor Collision
    collision_bp = blueprint_library.find('sensor.other.collision')
    collision_sensor = world.spawn_actor(collision_bp, carla.Transform(), attach_to=vehicle)
    
    image_queue, collision_queue = queue.Queue(), queue.Queue()
    imu_data_holder = [None]
    
    camera.listen(image_queue.put)
    imu_sensor.listen(lambda d: imu_data_holder.__setitem__(0, d))
    collision_sensor.listen(collision_queue.put)
    
    reward_calc = RewardCalculator()
    smoothed_severity = 0.0
    is_colliding = False
    collision_text_timer = 0
    
    print("\n▶ Mobil dipaksa belok KANAN (steer=0.3). Tekan 'q' untuk keluar\n")
    time.sleep(1.5)
    
    try:
        while True:
            # AKSI BELOK KANAN
            vehicle.apply_control(carla.VehicleControl(throttle=0.4, steer=0.3))
            
            # Cek Collision Event
            while not collision_queue.empty():
                event = collision_queue.get()
                actor_hit = event.other_actor.type_id
                intensity = math.sqrt(event.normal_impulse.x**2 + event.normal_impulse.y**2 + event.normal_impulse.z**2)
                print(f"[{reward_calc.episode_step}] 💥 FISIK TABRAKAN! Menabrak: {actor_hit} | Intensitas: {intensity:.0f}")
                is_colliding = True
                collision_text_timer = 15 # Tampilkan teks selama 15 frame
            
            try:
                spec = world.get_spectator(); vt = vehicle.get_transform()
                spec.set_transform(carla.Transform(vt.location + carla.Location(z=12, x=-8), carla.Rotation(pitch=-35, yaw=vt.rotation.yaw)))
            except: pass
            
            if not image_queue.empty():
                while not image_queue.empty(): image = image_queue.get()
                array = np.reshape(np.frombuffer(image.raw_data, dtype=np.uint8), (image.height, image.width, 4))
                frame = array[:, :, :3].copy()
                
                import torch
                with torch.no_grad(): results = model(frame, imgsz=640, conf=CONFIDENCE_THRESHOLD, verbose=False)
                
                pothole_data = np.zeros(5, dtype=np.float32)
                if len(results) > 0 and len(results[0].boxes) > 0:
                    boxes = results[0].boxes
                    best_idx = int(np.argmax(boxes.conf.cpu().numpy()))
                    x1, y1, x2, y2 = boxes.xyxy[best_idx].cpu().numpy()
                    raw_severity = {0: 0.3, 1: 0.6, 2: 0.9}.get(int(boxes.cls[best_idx].cpu().numpy()), 0.5)
                    smoothed_severity = raw_severity if smoothed_severity == 0.0 else (0.7 * smoothed_severity) + (0.3 * raw_severity)
                    pothole_data = np.array([((x1 + x2) / 2) / 640, ((y1 + y2) / 2) / 480, (x2 - x1) / 640, (y2 - y1) / 480, smoothed_severity], dtype=np.float32)
                else: smoothed_severity = 0.0
                
                reward_info = reward_calc.calculate(vehicle, imu_data_holder[0], pothole_data)
                
                # Visual Feedback Collision
                if collision_text_timer > 0:
                    cv2.putText(frame, "!! COLLISION SENSOR AKTIF !!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                    collision_text_timer -= 1
                    
                cv2.imshow("Test Belok Kanan", frame)
            
            if cv2.waitKey(1) == ord('q'): break
            time.sleep(0.01)
    
    finally:
        camera.destroy(); imu_sensor.destroy(); collision_sensor.destroy(); vehicle.destroy(); cv2.destroyAllWindows()

if __name__ == '__main__':
    main()