"""
ukur_geometri.py — DIJALANKAN KEVA di laptop dengan CARLA menyala.
(Belum pernah diuji oleh Claude karena butuh simulator.)

Mengukur tiga hal yang saat ini masih ESTIMASI di pelabel kontak roda:
  1. posisi 4 roda Microlino relatif titik asal aktor, sudut setir maksimum, jari-jari ban
  2. tinggi titik asal aktor terhadap jalan (asumsi proyeksi kamera)
  3. kotak pembatas lubang yang SEBENARNYA di peta (bukan dari foto grid seperti
     groundtruth_pothole.py Dika), jika peta yang dimuat berisi mesh lubang

Cara pakai (CARLA server sudah jalan):
    python ukur_geometri.py --peta train_fix --out geometri_terukur.json
    python ukur_geometri.py --peta Town10HD_Opt --out geometri_terukur.json   # jika train_fix belum ada
Hasil JSON dipakai untuk mengisi GeometriKendaraan(...) di 02_pelabel_roda/kontak_roda.py
"""
import argparse
import json

import carla  # noqa: F401  (butuh wheel CARLA yang cocok dengan versi server)


def ke_lokal(tf, loc):
    """Titik dunia -> koordinat lokal aktor (x maju, y kanan, z atas)."""
    f, r, u = tf.get_forward_vector(), tf.get_right_vector(), tf.get_up_vector()
    d = carla.Vector3D(loc.x - tf.location.x, loc.y - tf.location.y, loc.z - tf.location.z)
    return dict(x=d.x * f.x + d.y * f.y + d.z * f.z,
                y=d.x * r.x + d.y * r.y + d.z * r.z,
                z=d.x * u.x + d.y * u.y + d.z * u.z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=2000)
    ap.add_argument("--peta", default=None, help="nama peta yang dimuat; kosongkan untuk peta aktif")
    ap.add_argument("--blueprint", default="vehicle.micro.microlino")
    ap.add_argument("--kata_lubang", default="hole,pothole,lubang,med_samping",
                    help="potongan nama objek lingkungan yang dianggap lubang")
    ap.add_argument("--out", default="geometri_terukur.json")
    a = ap.parse_args()

    client = carla.Client(a.host, a.port)
    client.set_timeout(30.0)
    world = client.load_world(a.peta) if a.peta else client.get_world()
    hasil = dict(versi_server=client.get_server_version(), versi_client=client.get_client_version(),
                 peta=world.get_map().name)

    s = world.get_settings()
    sync0, dt0 = s.synchronous_mode, s.fixed_delta_seconds
    s.synchronous_mode, s.fixed_delta_seconds = True, 0.05
    world.apply_settings(s)
    v = None
    try:
        bp = world.get_blueprint_library().find(a.blueprint)
        sp = world.get_map().get_spawn_points()[0]
        v = world.spawn_actor(bp, sp)
        for _ in range(40):                      # biarkan kendaraan turun dan diam
            world.tick()
        tf = v.get_transform()
        pc = v.get_physics_control()
        roda = []
        for nama, w in zip(["depan_kiri", "depan_kanan", "belakang_kiri", "belakang_kanan"], pc.wheels):
            p = carla.Location(w.position.x / 100.0, w.position.y / 100.0, w.position.z / 100.0)   # cm -> m
            roda.append(dict(nama=nama, lokal=ke_lokal(tf, p), jari_jari_m=w.radius / 100.0,
                             sudut_setir_maks_deg=w.max_steer_angle))
        bb = v.bounding_box
        jalan = world.get_map().get_waypoint(tf.location, project_to_road=True).transform.location
        hasil["kendaraan"] = dict(
            blueprint=bp.id, roda=roda,
            bbox_extent=dict(x=bb.extent.x, y=bb.extent.y, z=bb.extent.z),
            bbox_pusat_lokal=dict(x=bb.location.x, y=bb.location.y, z=bb.location.z),
            tinggi_asal_aktor_di_atas_jalan_m=tf.location.z - jalan.z)
        fl, fr, rl, rr = [r["lokal"] for r in roda]
        hasil["untuk_kontak_roda_py"] = dict(
            jarak_sumbu_depan=(fl["x"] + fr["x"]) / 2, jarak_sumbu_belakang=-(rl["x"] + rr["x"]) / 2,
            lebar_jejak=((fr["y"] - fl["y"]) + (rr["y"] - rl["y"])) / 2,
            setengah_lebar_bodi=bb.extent.y, setengah_panjang_bodi=bb.extent.x,
            catatan="setengah_lebar_ban tidak tersedia di API; ukur dari mesh atau pakai 0.075")
    finally:
        if v is not None:
            v.destroy()
        s.synchronous_mode, s.fixed_delta_seconds = sync0, dt0
        world.apply_settings(s)

    kata = [k.strip().lower() for k in a.kata_lubang.split(",")]
    lub = []
    for o in world.get_environment_objects(carla.CityObjectLabel.Any):
        if any(k in o.name.lower() for k in kata):
            b = o.bounding_box
            lub.append(dict(nama=o.name, id=o.id, x=b.location.x, y=b.location.y, z=b.location.z,
                            yaw=b.rotation.yaw, extent_x=b.extent.x, extent_y=b.extent.y, extent_z=b.extent.z))
    hasil["lubang_di_peta"] = sorted(lub, key=lambda d: d["x"])
    hasil["jumlah_lubang"] = len(lub)
    with open(a.out, "w") as f:
        json.dump(hasil, f, indent=1)
    print(json.dumps({k: hasil[k] for k in hasil if k != "lubang_di_peta"}, indent=1))
    print(f"{len(lub)} objek lubang ditemukan. Hasil lengkap di {a.out}")


if __name__ == "__main__":
    main()
