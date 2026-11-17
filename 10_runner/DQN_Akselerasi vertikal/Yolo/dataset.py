import carla
import cv2
import numpy as np
from ultralytics import YOLO
import queue
import time
import os

# --- KONFIGURASI PENTING ---
MODEL_PATH = "Yolo/best_pure.pt"
CONFIDENCE_THRESHOLD = 0.2

# MASUKKAN KOORDINAT LUBANG ANDA DI SINI
TARGET_SPAWN_POINT = carla.Transform(carla.Location(x=-299.5, y=250.5, z=3), carla.Rotation(yaw=0))

def main():
    print("Memuat model YOLO...")
    model = YOLO(MODEL_PATH)

    print("Menghubungkan ke CARLA...")
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    # Hapus setting cuaca agar terang benderang (ClearNoon)
    world.set_weather(carla.WeatherParameters.ClearNoon)

    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]

    # --- PERBAIKAN POSISI SPAWN ---
    spawn_loc = TARGET_SPAWN_POINT
    spawn_loc.location.z += 1.0
    
    print(f"Mencoba memunculkan mobil di: {spawn_loc.location}")
    vehicle = world.spawn_actor(vehicle_bp, spawn_loc)
    
    vehicle.set_autopilot(False)
    vehicle.apply_control(carla.VehicleControl(throttle=0.15, steer=0.0))

    # --- PERBAIKAN SUDUT KAMERA & RESOLUSI ---
    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', '640') 
    camera_bp.set_attribute('image_size_y', '640')
    camera_bp.set_attribute('fov', '90')
    
    camera_transform = carla.Transform(carla.Location(x=1.5, z=2.0), carla.Rotation(pitch=-25))
    camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)

    image_queue = queue.Queue()
    camera.listen(image_queue.put)

    # --- SETUP FOLDER DATASET ---
    # Membuat folder otomatis jika belum ada
    os.makedirs("dataset_lubang", exist_ok=True)
    img_counter = 0

    try:
        print("Simulasi jalan... Cek jendela OpenCV!")
        time.sleep(2.0) 

        while True:
            # 1. Perintah gas mobil
            vehicle.apply_control(carla.VehicleControl(throttle=0.3, steer=0.0))

            # 2. Lindungi pencarian Spectator
            try:
                spectator = world.get_spectator()
                veh_trans = vehicle.get_transform()
                spectator.set_transform(carla.Transform(veh_trans.location + carla.Location(z=10, x=-5), 
                                                        carla.Rotation(pitch=-45, yaw=veh_trans.rotation.yaw)))
            except RuntimeError:
                pass 

            # 3. Proses Gambar (ANTI-LAG)
            if not image_queue.empty():
                
                # Membuang gambar lama, hanya mengambil 1 gambar terbaru
                while not image_queue.empty():
                    image = image_queue.get() 
                
                array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
                array = np.reshape(array, (image.height, image.width, 4))
                
                # GAMBAR BERSIH (Tanpa kotak deteksi, ini yang akan disimpan)
                clean_frame = array[:, :, :3]

                # Tracking YOLO (Hanya untuk ditampilkan di layar agar Anda tahu posisinya)
                results = model.track(clean_frame, persist=True, verbose=False, conf=CONFIDENCE_THRESHOLD, tracker="botsort.yaml")
                annotated_frame = results[0].plot()
                
                cv2.putText(annotated_frame, "Tekan 'S' untuk Simpan, 'Q' untuk Keluar", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                cv2.imshow("Kamera Koleksi Dataset", annotated_frame)
            
            # --- TOMBOL KONTROL (PENGAMBILAN DATASET) ---
            key = cv2.waitKey(1)
            
            if key == ord('s') or key == ord('S'):
                # Simpan gambar bersih ke folder
                img_name = f"dataset_lubang/lubang_high_{img_counter}.jpg"
                cv2.imwrite(img_name, clean_frame)
                print(f"✅ BERHASIL DISIMPAN: {img_name}")
                img_counter += 1
                
            elif key == ord('q') or key == ord('Q'):
                break

            time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nMembersihkan aktor...")
        camera.stop()
        camera.destroy()
        vehicle.destroy()
        cv2.destroyAllWindows()
        print("Selesai.")

if __name__ == '__main__':
    main()