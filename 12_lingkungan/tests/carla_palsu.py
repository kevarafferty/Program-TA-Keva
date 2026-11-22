"""
carla_palsu.py — Modul 'carla' tiruan untuk menguji env_skenario + runner tanpa simulator.

Yang ditiru hanya API yang dipakai carla_env.py Dika, env_skenario.py, dan generator_tata_letak.py.
Fisika sangat sederhana (model sepeda kinematik, kecepatan menuju throttle * V_MAKS). Kamera mengirim
citra CARLA asli (11_cuaca/data_PaketEpic) bergiliran, sehingga YOLO asli menghasilkan deteksi sungguhan.
Tujuannya menguji ALUR KODE (urutan panggilan, penyelarasan log, hook, toggle, transisi), bukan perilaku agen.
"""
from __future__ import annotations

import glob
import math
import os
import types

import numpy as np

V_MAKS_KMH_PER_THROTTLE = 23.3      # throttle 0,3 -> ±7 km/jam seperti Dika
FAKTOR_SETIR = 1.0                  # 0 = mobil tiruan selalu lurus (uji alur sampai garis finis)
# Tiruan bug CARLA paket (22 Nov): objek yang dimatikan lalu dinyalakan dalam frame yang sama
# berakhir TAK TAMPAK dengan peluang BUG_TOGGLE.
BUG_TOGGLE = 0.0
TOGGLE_DIR = ""                     # folder berisi toggle_nyala.png / toggle_mati.png untuk kamera bebas


class Location:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def distance(self, o):
        return math.sqrt((self.x - o.x) ** 2 + (self.y - o.y) ** 2 + (self.z - o.z) ** 2)


class Vector3D(Location):
    pass


class Rotation:
    def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
        self.pitch, self.yaw, self.roll = float(pitch), float(yaw), float(roll)


class Transform:
    def __init__(self, location=None, rotation=None):
        self.location = location or Location()
        self.rotation = rotation or Rotation()

    def get_forward_vector(self):
        r = math.radians(self.rotation.yaw)
        return Vector3D(math.cos(r), math.sin(r), 0.0)

    def get_right_vector(self):
        r = math.radians(self.rotation.yaw)
        return Vector3D(-math.sin(r), math.cos(r), 0.0)


_PARAM = ["cloudiness", "precipitation", "precipitation_deposits", "wind_intensity", "sun_azimuth_angle",
          "sun_altitude_angle", "fog_density", "fog_distance", "wetness", "fog_falloff", "scattering_intensity",
          "mie_scattering_scale", "rayleigh_scattering_scale", "dust_storm"]


class WeatherParameters:
    def __init__(self, **kw):
        for k in _PARAM:
            setattr(self, k, float(kw.get(k, 0.0)))


def _preset(**kw):
    w = WeatherParameters(fog_falloff=0.2, rayleigh_scattering_scale=0.0331, mie_scattering_scale=0.03,
                          scattering_intensity=1.0, fog_distance=0.0)
    for k, v in kw.items():
        setattr(w, k, float(v))
    return w


# angka preset kira-kira (cukup untuk uji alur)
WeatherParameters.ClearNoon = _preset(cloudiness=5, sun_altitude_angle=45, wind_intensity=10)
WeatherParameters.CloudyNoon = _preset(cloudiness=60, sun_altitude_angle=45, wind_intensity=10)
WeatherParameters.WetNoon = _preset(cloudiness=5, sun_altitude_angle=45, wetness=50, precipitation_deposits=50)
WeatherParameters.WetCloudyNoon = _preset(cloudiness=60, sun_altitude_angle=45, wetness=50, precipitation_deposits=50)
WeatherParameters.SoftRainNoon = _preset(cloudiness=20, precipitation=30, precipitation_deposits=50, sun_altitude_angle=45)
WeatherParameters.MidRainyNoon = _preset(cloudiness=60, precipitation=60, precipitation_deposits=60, sun_altitude_angle=45)
WeatherParameters.HardRainNoon = _preset(cloudiness=100, precipitation=100, precipitation_deposits=90,
                                         wind_intensity=100, sun_altitude_angle=45, fog_density=7, fog_distance=0.75)
WeatherParameters.ClearNight = _preset(cloudiness=5, sun_altitude_angle=-90)
WeatherParameters.ClearSunset = _preset(cloudiness=5, sun_altitude_angle=15)


class VehicleControl:
    def __init__(self, throttle=0.0, steer=0.0, brake=0.0):
        self.throttle, self.steer, self.brake = throttle, steer, brake


class VehicleLightState(int):
    pass


VehicleLightState.NONE = VehicleLightState(0)
VehicleLightState.Position = VehicleLightState(1)
VehicleLightState.LowBeam = VehicleLightState(2)
VehicleLightState.HighBeam = VehicleLightState(4)

CityObjectLabel = types.SimpleNamespace(Any=255)


class _BBox:
    def __init__(self, ex, ey, ez):
        self.extent = Vector3D(ex, ey, ez)


class BP:
    def __init__(self, id_, attrs=()):
        self.id = id_
        self.attr = {a: "" for a in attrs}

    def set_attribute(self, k, v):
        self.attr[k] = v

    def has_attribute(self, k):
        return k in self.attr

    def __iter__(self):
        return iter([types.SimpleNamespace(id=k) for k in self.attr])


class Library:
    def __init__(self, ids):
        self.bps = {i: BP(i, ("mesh_path",) if i == "static.prop.mesh" else ()) for i in ids}

    def filter(self, pat):
        return [b for i, b in self.bps.items() if i == pat or (pat.endswith("*") and i.startswith(pat[:-1]))]

    def find(self, i):
        return self.bps[i]


class Actor:
    _next = 100

    def __init__(self, world, bp, tf, parent=None):
        Actor._next += 1
        self.id = Actor._next
        self.world, self.type_id, self.parent = world, bp.id, parent
        self.tf = Transform(Location(tf.location.x, tf.location.y, tf.location.z),
                            Rotation(tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll))
        self.bp = bp
        self.cb = None
        self.alive = True
        self.v = 0.0
        self.ctrl = VehicleControl()
        self.light = None
        self.bounding_box = _BBox(1.1036, 0.7405, 0.688)

    # kendaraan
    def get_location(self):
        return self.tf.location

    def set_transform(self, tf):
        self.tf = Transform(Location(tf.location.x, tf.location.y, tf.location.z),
                            Rotation(tf.rotation.pitch, tf.rotation.yaw, tf.rotation.roll))

    def get_transform(self):
        return self.tf

    def get_velocity(self):
        r = math.radians(self.tf.rotation.yaw)
        return Vector3D(self.v * math.cos(r), self.v * math.sin(r), 0.0)

    def get_control(self):
        return self.ctrl

    def apply_control(self, c):
        self.ctrl = c

    def set_light_state(self, s):
        self.light = s

    def get_physics_control(self):
        fw, rt = self.tf.get_forward_vector(), self.tf.get_right_vector()
        out = []
        for lx, ly in ((0.684, -0.596), (0.684, 0.596), (-0.841, -0.361), (-0.841, 0.361)):
            p = Vector3D(100 * (self.tf.location.x + lx * fw.x + ly * rt.x), 100 * (self.tf.location.y + lx * fw.y + ly * rt.y), 0)
            out.append(types.SimpleNamespace(position=p))
        return types.SimpleNamespace(wheels=out)

    def _gerak(self, dt):
        target = self.ctrl.throttle * V_MAKS_KMH_PER_THROTTLE / 3.6
        self.v += (target - self.v) * min(1.0, dt / 1.0)
        L = 1.525
        dyaw = self.v / L * math.tan(math.radians(self.ctrl.steer * 30.0 * FAKTOR_SETIR)) * dt
        self.tf.rotation.yaw += math.degrees(dyaw)
        r = math.radians(self.tf.rotation.yaw)
        self.tf.location.x += self.v * math.cos(r) * dt
        self.tf.location.y += self.v * math.sin(r) * dt
        self.tf.location.z = 0.0

    # sensor
    def listen(self, cb):
        self.cb = cb

    def stop(self):
        self.cb = None

    def destroy(self):
        self.alive = False
        self.world.actors.pop(self.id, None)
        return True


class _Img:
    def __init__(self, arr, frame):
        self.raw_data = arr.tobytes()
        self.height, self.width = arr.shape[:2]
        self.frame = frame


class World:
    def __init__(self, citra_dir, slot):
        import cv2
        self.frame = 0
        self.t = 0.0
        self.settings = types.SimpleNamespace(synchronous_mode=False, fixed_delta_seconds=None)
        self.weather = WeatherParameters.ClearNoon
        self.riwayat_cuaca = []
        self.actors = {}
        fs = sorted(glob.glob(os.path.join(citra_dir, "**", "*.png"), recursive=True))
        self.citra = [cv2.imread(f) for f in fs]
        self.lib = Library(["vehicle.micro.microlino", "vehicle.nissan.micra", "vehicle.citroen.c3",
                            "vehicle.tesla.model3", "sensor.camera.rgb", "sensor.other.collision",
                            "sensor.other.imu", "static.prop.mesh"])
        self.env_obj = []
        oid = 9000
        for s in slot:
            for k in range(2):     # dua komponen per slot, seperti mungkin terjadi di build asli
                oid += 1
                self.env_obj.append(types.SimpleNamespace(
                    id=oid, name="%s_SM_%d" % (s["name"], k),
                    transform=Transform(Location(s["x"], s["y"], s["z"]))))
        self.env_obj.append(types.SimpleNamespace(id=1, name="Road_1", transform=Transform(Location(-150, 249, 0))))
        self.nyala = {o.id: True for o in self.env_obj}
        self.n_toggle_call = 0
        self._hist_frame = {}
        self._rng = np.random.default_rng(0)
        self.im_nyala = self.im_mati = None
        if TOGGLE_DIR and os.path.exists(os.path.join(TOGGLE_DIR, "toggle_nyala.png")):
            self.im_nyala = cv2.imread(os.path.join(TOGGLE_DIR, "toggle_nyala.png"))
            self.im_mati = cv2.imread(os.path.join(TOGGLE_DIR, "toggle_mati.png"))

    def get_settings(self):
        return types.SimpleNamespace(**vars(self.settings))

    def apply_settings(self, s):
        self.settings = s

    def set_weather(self, w):
        self.weather = w
        self.riwayat_cuaca.append((self.frame, w.sun_altitude_angle, w.precipitation, w.fog_density))

    def get_weather(self):
        return self.weather

    def get_blueprint_library(self):
        return self.lib

    def spawn_actor(self, bp, tf, attach_to=None):
        a = Actor(self, bp, tf, attach_to)
        self.actors[a.id] = a
        return a

    def try_spawn_actor(self, bp, tf, attach_to=None):
        return self.spawn_actor(bp, tf, attach_to)

    def get_environment_objects(self, label):
        return list(self.env_obj)

    def enable_environment_objects(self, ids, on):
        self.n_toggle_call += 1
        for i in ids:
            h = self._hist_frame.setdefault(i, [])
            h.append(bool(on))
            akhir = bool(on)
            if on and len(h) >= 2 and h[-2] is False and self._rng.random() < BUG_TOGGLE:
                akhir = False                       # bug: mati+nyala dalam satu frame -> tetap tak tampak
            self.nyala[i] = akhir

    def _citra_kamera_bebas(self, cam):
        """Kamera tanpa induk (verifikasi): lubang tampak jika ada slot NYALA 4-10 m di depan, selajur."""
        L = cam.tf.location
        pos = [o.transform.location for o in self.env_obj if o.id != 1 and self.nyala[o.id]]
        pos += [a.tf.location for a in self.actors.values() if a.type_id == "static.prop.mesh"]
        for p in pos:
            dx, dy = p.x - L.x, p.y - L.y
            if 4.0 <= dx <= 10.0 and abs(dy) < 1.0:
                return self.im_nyala
        return self.im_mati

    def get_snapshot(self):
        return types.SimpleNamespace(frame=self.frame, timestamp=types.SimpleNamespace(elapsed_seconds=self.t))

    def get_map(self):
        return types.SimpleNamespace(name="Carla/Maps/train_fix")

    def tick(self):
        dt = 0.05
        self.frame += 1
        self.t += dt
        self._hist_frame = {}
        for a in list(self.actors.values()):
            if a.type_id.startswith("vehicle"):
                a._gerak(dt)
        for a in list(self.actors.values()):
            if a.cb is None:
                continue
            if a.type_id == "sensor.camera.rgb" and self.citra:
                im = self.citra[self.frame % len(self.citra)]
                if a.parent is None and self.im_nyala is not None:
                    im = self._citra_kamera_bebas(a)
                bgra = np.concatenate([im, np.full(im.shape[:2] + (1,), 255, np.uint8)], axis=2)
                a.cb(_Img(bgra, self.frame))
            elif a.type_id == "sensor.other.imu":
                a.cb(types.SimpleNamespace(accelerometer=Vector3D(0.0, 0.0, 9.81), timestamp=self.t))
        return self.frame


class Client:
    WORLD = None
    CITRA_DIR = ""
    SLOT = []

    def __init__(self, host, port):
        pass

    def set_timeout(self, t):
        pass

    def load_world(self, name):
        Client.WORLD = World(Client.CITRA_DIR, Client.SLOT)
        return Client.WORLD

    def get_world(self):
        return Client.WORLD

    def get_server_version(self):
        return "palsu"

    def get_client_version(self):
        return "palsu"
