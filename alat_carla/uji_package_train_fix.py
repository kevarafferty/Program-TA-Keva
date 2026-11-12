"""Uji hasil `make package` (TODO #13): apakah train_fix ikut ter-package dan bisa dimuat.

Jalankan SETELAH CarlaUE4.exe dari folder WindowsNoEditor terbuka, di env carla_env:
    python uji_package_train_fix.py
Hasil ditulis ke hasil_uji_package.json (di folder ini) dan dicetak ke layar.

Lulus jika: train_fix ada di daftar peta, load_world berhasil, dan get_map() bisa membaca OpenDRIVE.
Langkah 4 (posisi 18 lubang) dicetak sebagai informasi. Cek visual tekstur lubang tetap harus kamu lakukan di jendela CARLA.
"""
import argparse, json, sys, time
import carla

ap = argparse.ArgumentParser()
ap.add_argument("--host", default="127.0.0.1")   # bukan 'localhost' (masalah WARP, lihat LOG_KERJA 10 Nov)
ap.add_argument("--port", type=int, default=2000)
ap.add_argument("--kata_lubang", default="hole,pothole,lubang,med,samping,detect")
ap.add_argument("--out", default="hasil_uji_package.json")
a = ap.parse_args()

hasil = {"waktu": time.strftime("%Y-%m-%d %H:%M:%S"), "lulus": False}
def selesai(pesan):
    hasil["pesan"] = pesan
    json.dump(hasil, open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(hasil, indent=2, ensure_ascii=False))
    sys.exit(0 if hasil["lulus"] else 1)

c = carla.Client(a.host, a.port)
c.set_timeout(60.0)
hasil["versi_server"] = c.get_server_version()
hasil["versi_client"] = c.get_client_version()

# 1. Apakah train_fix ada di daftar peta?
peta = c.get_available_maps()
hasil["jumlah_peta"] = len(peta)
hasil["peta_tersedia"] = peta
cocok = [m for m in peta if "train_fix" in m.lower()]
if not cocok:
    selesai("GAGAL di langkah 1: train_fix TIDAK ada di daftar peta. Cek MapsToCook di DefaultGame.ini.")

# 2. Muat petanya
c.set_timeout(180.0)
try:
    world = c.load_world("train_fix")
except Exception as e:
    selesai(f"GAGAL di langkah 2: load_world error: {e}")
hasil["peta_aktif"] = world.get_map().name

# 3. OpenDRIVE ikut ter-package? (tanpa .xodr, get_map/topologi gagal)
try:
    hasil["jumlah_waypoint_2m"] = len(world.get_map().generate_waypoints(2.0))
except Exception as e:
    selesai(f"GAGAL di langkah 3: OpenDRIVE tidak terbaca: {e}. Cek train_fix.xodr di Content/Carla/Maps/OpenDrive.")

# 4. Objek lubang ada? Dua cara: nama, dan posisi dibanding geometri_terukur.json (editor).
#    Nama objek di build Shipping bisa berbeda dari di editor, jadi cocok-posisi lebih bisa dipercaya.
semua = list(world.get_environment_objects(carla.CityObjectLabel.Any))
kata = [k.strip().lower() for k in a.kata_lubang.split(",")]
lubang = [o for o in semua if any(k in o.name.lower() for k in kata)]
hasil["jumlah_objek_lubang_dari_nama"] = len(lubang)
hasil["contoh_nama"] = sorted({o.name for o in lubang})[:10]
try:
    ref = json.load(open("geometri_terukur.json", encoding="utf-8"))["lubang_di_peta"]
    ketemu = 0
    for r in ref:
        for o in semua:
            L = o.transform.location
            if abs(L.x - r["x"]) < 0.5 and abs(L.y - r["y"]) < 0.5 and abs(L.z - r["z"]) < 0.5:
                ketemu += 1
                break
    hasil["lubang_editor_ditemukan_di_package"] = f"{ketemu}/{len(ref)}"
except Exception as e:
    hasil["lubang_editor_ditemukan_di_package"] = f"tidak bisa dicek: {e}"

# 5. Arahkan kamera penonton ke deretan lubang untuk cek visual
sp = world.get_spectator()
sp.set_transform(carla.Transform(carla.Location(x=-245.0, y=250.5, z=8.0),
                                 carla.Rotation(pitch=-35.0, yaw=0.0)))

hasil["lulus"] = True   # langkah 1-3 lolos; langkah 4 informasi, dinilai bersama cek visual
selesai("LULUS langkah 1-3. Bandingkan 'lubang_editor_ditemukan_di_package' (harus 18/18), lalu lihat "
        "jendela CARLA: lubang harus tampak sebagai tekstur retak, bukan kotak abu-abu/kotak-kotak.")
