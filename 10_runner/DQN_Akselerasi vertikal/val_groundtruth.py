# verify_bbox.py
import carla, json

client = carla.Client('localhost', 2000)
client.set_timeout(10.0)
world = client.load_world('train_fix')

with open('pothole_gt.json') as f:
    potholes = json.load(f)

COLOR_MAP = {
    'Low'   : carla.Color(0, 255, 0),    # hijau
    'Medium': carla.Color(255, 165, 0),  # oranye
    'High'  : carla.Color(255, 0, 0),    # merah
}

for ph in potholes:
    center = carla.Location(x=ph['x'], y=ph['y'], z=ph['z'] + 0.3)
    extent = carla.Vector3D(x=ph['extent_x'],
                            y=ph['extent_y'],
                            z=ph['extent_z'])
    rot    = carla.Rotation(yaw=ph.get('yaw', 0.0))
    bb     = carla.BoundingBox(center, extent)
    color  = COLOR_MAP.get(ph['severity_label'], carla.Color(255,255,255))

    world.debug.draw_box(bb, rot,
                         thickness=0.08,
                         color=color,
                         life_time=30.0)

    # Label teks di atas lubang
    world.debug.draw_string(
        carla.Location(x=ph['x'], y=ph['y'], z=ph['z'] + 1.0),
        f"{ph['name']} | {ph['extent_x']*2:.1f}x{ph['extent_y']*2:.1f}m",
        color=color,
        life_time=30.0
    )
    print(f"Drew: {ph['name']} — {ph['extent_x']*2:.1f}m × {ph['extent_y']*2:.1f}m")