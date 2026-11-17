# cek_dimensi_kendaraan.py — jalankan sekali untuk verifikasi
import carla, time

client = carla.Client('localhost', 2000)
client.set_timeout(10.0)
world  = client.load_world('train_fix')

settings = world.get_settings()
settings.synchronous_mode = True
settings.fixed_delta_seconds = 0.05
world.apply_settings(settings)

lib    = world.get_blueprint_library()
bp     = lib.filter('vehicle.micro.microlino')[0]
sp     = carla.Transform(carla.Location(x=-299.5, y=250.5, z=3))
vehicle = world.spawn_actor(bp, sp)

world.tick()
time.sleep(0.1)

# Bounding box CARLA = dimensi AKURAT dari mesh kendaraan
bb = vehicle.bounding_box
print(f"Blueprint : {bp.id}")
print(f"extent.x  : {bb.extent.x:.4f} m  → half-LENGTH (maju-mundur)")
print(f"extent.y  : {bb.extent.y:.4f} m  → half-WIDTH  (kiri-kanan) ← ini yang dipakai")
print(f"extent.z  : {bb.extent.z:.4f} m  → half-HEIGHT")
print(f"\nFull width : {bb.extent.y * 2:.4f} m")
print(f"\nGunakan nilai ini di CarlaEnv:")
print(f"  VEHICLE_HALF_WIDTH = {bb.extent.y:.4f}")

vehicle.destroy()
settings.synchronous_mode = False
world.apply_settings(settings)