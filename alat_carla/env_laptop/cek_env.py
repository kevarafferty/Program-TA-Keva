"""Cek env carla_env di laptop. Jalankan: python cek_env.py
Selesai jika: import carla, tensorflow, ultralytics berhasil (TODO #11)."""
import sys, importlib

print("Python", sys.version.split()[0], "di", sys.executable)
if sys.version_info[:2] != (3, 8):
    print("  PERINGATAN: env lab memakai Python 3.8.20")

harapan = {"carla": None, "tensorflow": "2.10.0", "keras": "2.10.0", "torch": "2.4.1+cu118",
           "ultralytics": "8.4.13", "numpy": "1.24.4", "cv2": None, "gym": "0.21.0", "h5py": "3.11.0"}
gagal = []
for nama, versi in harapan.items():
    try:
        m = importlib.import_module(nama)
        v = getattr(m, "__version__", "?")
        tanda = "" if versi in (None, v) else f"   <-- beda dari lab ({versi})"
        print(f"  OK  {nama:12s} {v}{tanda}")
    except Exception as e:
        gagal.append(nama)
        print(f"  GAGAL {nama:10s} {type(e).__name__}: {e}")

print("\n--- GPU ---")
try:
    import torch
    print("  torch CUDA:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
except Exception as e:
    print("  torch:", e)
try:
    import tensorflow as tf
    print("  TF GPU    :", tf.config.list_physical_devices("GPU") or "TIDAK ADA (DQN jalan di CPU)")
except Exception as e:
    print("  TF:", e)

print("\n--- Server CARLA (opsional, hanya jika CarlaUE4 / make launch sedang jalan) ---")
try:
    import carla
    c = carla.Client("127.0.0.1", 2000); c.set_timeout(5.0)
    print("  client", c.get_client_version(), "| server", c.get_server_version(),
          "| peta", c.get_world().get_map().name)
except Exception as e:
    print("  tidak tersambung (wajar kalau server belum jalan):", type(e).__name__)

print("\nHASIL:", "LULUS" if not {"carla", "tensorflow", "ultralytics"} & set(gagal) else "GAGAL: " + ", ".join(gagal))
