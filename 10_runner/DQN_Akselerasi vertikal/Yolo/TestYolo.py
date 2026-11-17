import carla # type: ignore
import cv2
import numpy as np
from ultralytics import YOLO
import queue
import time

# --- KONFIGURASI PENTING ---
MODEL_PATH = "Yolo/best_pure.pt"
CONFIDENCE_THRESHOLD = 0.4 # Turunkan sedikit agar lebih sensitif

# MASUKKAN KOORDINAT LUBANG ANDA DI SINI
TARGET_SPAWN_POINT = carla.Transform(carla.Location(x=-299.5, y=250.5, z=3), carla.Rotation(yaw=0))

def main():
    print("Memuat model YOLO...")
    model = YOLO(MODEL_PATH)

    print("Menghubungkan ke CARLA...")
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    
    # TAMBAHKAN BARIS INI: Paksa load map resmi yang stabil (misal Town06 atau Town01)
    print("Memuat map train_fix...")
    world = client.load_world('train_fix')

    # Hapus setting cuaca agar terang benderang (ClearNoon)
    world.set_weather(carla.WeatherParameters.ClearNoon)

    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]

    # --- PERBAIKAN POSISI SPAWN ---
    spawn_loc = TARGET_SPAWN_POINT
    spawn_loc.location.z += 1.0
    
    print(f"Mencoba memunculkan mobil di: {spawn_loc.location}")
    vehicle = world.spawn_actor(vehicle_bp, spawn_loc)
    
    # --- PERBAIKAN KECEPATAN ---
    vehicle.set_autopilot(False)
    vehicle.apply_control(carla.VehicleControl(throttle=0.15, steer=0.0))

    # --- PERBAIKAN SUDUT KAMERA & RESOLUSI (ANTI-LAG) ---
    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', '640') # Resolusi diturunkan agar lebih ringan
    camera_bp.set_attribute('image_size_y', '640')
    camera_bp.set_attribute('fov', '90')
    
    # Pasang di kap mesin, TUNDUKKAN (-25 derajat) agar melihat aspal
    camera_transform = carla.Transform(carla.Location(x=1.5, z=2.0), carla.Rotation(pitch=-25))
    camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)

    image_queue = queue.Queue()
    camera.listen(image_queue.put)

    try:
        print("Simulasi jalan... Cek jendela OpenCV!")
        time.sleep(2.0) 

        while True:
            # 1. Perintah gas mobil
            vehicle.apply_control(carla.VehicleControl(throttle=0.3, steer=0.0))

            # 2. Lindungi pencarian Spectator agar tidak bikin crash
            try:
                spectator = world.get_spectator()
                veh_trans = vehicle.get_transform()
                spectator.set_transform(carla.Transform(veh_trans.location + carla.Location(z=10, x=-5), 
                                                        carla.Rotation(pitch=-45, yaw=veh_trans.rotation.yaw)))
            except RuntimeError:
                pass 

            # 3. Proses Gambar YOLO (ANTI-LAG DENGAN PENGURASAN ANTREAN)
            if not image_queue.empty():
                
                # Membuang gambar lama, hanya mengambil 1 gambar yang paling baru
                while not image_queue.empty():
                    image = image_queue.get() 
                
                array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
                array = np.reshape(array, (image.height, image.width, 4))
                frame = array[:, :, :3]

                # Tracking YOLO
                results = model.track(frame, persist=True, verbose=False, conf=CONFIDENCE_THRESHOLD, tracker="botsort.yaml")
                annotated_frame = results[0].plot()
                
                cv2.putText(annotated_frame, "Status: Mencari Lubang... (Real-time)", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow("Deteksi Lubang - Realtime", annotated_frame)
            
            # Tombol 'q' untuk keluar
            if cv2.waitKey(1) == ord('q'):
                break

            time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        camera.destroy()
        vehicle.destroy()
        cv2.destroyAllWindows()
        print("Selesai.")

if __name__ == '__main__':
    main()