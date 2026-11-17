# build_gt_from_ue4.py

import json

# ─────────────────────────────────────────────────────────────────
# CATATAN EXTENT:
#   extent = HALF-SIZE dari titik pusat ke tepi (bukan full width)
#   full_width  = extent_x * 2
#   full_length = extent_y * 2
#
# Diukur dari grid foto (1 kotak = 1m):
#   LOW    : ~1m × 2.5m  → extent_x=0.5,  extent_y=1.25
#   MEDIUM : ~3m × 3m    → extent_x=1.5,  extent_y=1.5
#   HIGH   : ~4m × 4m    → extent_x=2.0,  extent_y=2.0  (estimasi)
# ─────────────────────────────────────────────────────────────────

TYPE_CONFIG = {
    'Low': {
        'severity'      : 0.3,
        'severity_label': 'Low',
        'extent_x'      : 0.5,    # half → full 1.0m
        'extent_y'      : 1.25,   # half → full 2.5m
    },
    'Medium': {
        'severity'      : 0.6,
        'severity_label': 'Medium',
        'extent_y'     : 0.8,    # half → full 3.0m
        'extent_x'     : 1.3,    # half → full 3.0m
    },
    'High': {
        'severity'      : 0.9,
        'severity_label': 'High',
        'extent_y'    : 1.5,    # half → full 4.0m (sesuaikan jika perlu)
        'extent_x'     : 1.0,    # half → full 4.0m
    },
}

# ─────────────────────────────────────────────────────────────────
# FORMAT: (nama, UE4_X, UE4_Y, UE4_Z, yaw, tipe)
# yaw = rotasi lubang di UE4 (Rotation → Z), 0 jika tidak dirotasi
# ─────────────────────────────────────────────────────────────────
UE4_POTHOLES = [
    ('hole_low2',    -28519.4, 25055.1, 3.9,  0.0, 'Medium'),
    # ('med_samping detect3', -28509.439453, 24397.042969, 3.909149,  0.0, 'High'),
    ('hole_low',    -27039.439453, 24725.070312, 3.909149,  0.0, 'Medium'),
    # ('med_samping detect4', -26989.439453, 24105.070312, 3.909149,  0.0, 'High'),
    #('hole_low7',    -25599.439453, 24365.070312, 3.909149,  0.0, 'Medium'),
    ('med_samping detect', -25579.439453, 25025.070312, 3.909149,  0.0, 'High'),
    ('med_samping detect2',    -24369.439453, 24715.070312, 3.909149,  0.0, 'High'),
    #('med_samping detect5', -24359.439453, 24105.070312, 3.909149,  0.0, 'High'),
    ('hole_low4',    -23059.439453, 25055.070312, 3.909149,  0.0, 'Medium'),
    #('med_samping detect8', -23049.439453, 24433.291016, 3.909393, 0.0, 'High'),
    ('hole_low3',    -21579.439453, 24725.070312, 3.909149,  0.0, 'Medium'),
    #('med_samping detect9', -21529.439453, 24105.070312, 3.909149,  0.0, 'High'),
    #('hole_low8',    -20139.439453, 24365.070312, 3.909149,  0.0, 'Medium'),
    ('med_samping detect6', -20119.439453, 25025.070312, 3.909149,  0.0, 'High'),
    ('med_samping detect7',    -18909.439453, 24715.070312, 3.909149,  0.0, 'High'),
    #('med_samping detect10', -18899.439453, 24105.070312, 3.909149,  0.0, 'High'),
    ('hole_low6',    -17549.439453, 25055.070312, 3.909149,  0.0, 'Medium'),
    #('med_samping detect12', -17539.439453, 24379.041016, 3.909149,  0.0, 'High'),
    ('hole_low5',    -16069.439453, 24725.070312, 3.909149,  0.0, 'Medium'),
    ('med_samping detect11', -14609.439453, 25025.070312, 3.909149,  0.0, 'High'),
    #('hole_low9',    -14629.439453, 24365.070312, 3.909149,  0.0, 'Medium'),
    #('med_samping detect39', -13394.211914, 24753.853516, 3.910125,  0.0, 'High'),
    #('med_samping detect14',    -13389.439453, 24105.070312, 3.909149,  0.0, 'High'),
    #('med_samping detect17', -12079.439453, 24380.457031, 3.914032,  0.0, 'High'),
    ('hole_low11',    -12089.439453, 25055.070312, 3.909149,  0.0, 'Medium'),
    #('med_samping detect18', -10559.439453, 24105.070312, 3.909149, 0.0, 'High'),
    ('hole_low10',    -10609.439453, 24725.070312, 3.909149,  0.0, 'Medium'),
    ('med_samping detect15', -9149.439453, 25025.070312, 3.909149,  0.0, 'High'),
    #('hole_low12',    -9169.439453, 24365.070312, 3.909149,  0.0, 'Medium'),
    ('med_samping detect16', -7939.439453, 24715.070312, 3.909149,  0.0, 'High'),
    #('med_samping detect19',    -7929.439453, 24105.070312, 3.909149,  0.0, 'High'),
    ('hole_low14',    -7069.439453, 25055.070312, 3.909149,  0.0, 'Medium'),
    #('med_samping detect22', -7059.439453, 24515.070312, 3.909149,  0.0, 'High'),
    ('hole_low13',    -6159.439453, 24725.070312, 3.909149,  0.0, 'Medium'),
    #('med_samping detect23', -6109.439453, 24105.070312, 3.909149,  0.0, 'High'),
    #('hole_low15',    -4719.439453, 24365.070312, 3.909149,  0.0, 'Medium'),
    ('med_samping detect20', -4699.439453, 25025.070312, 3.909149,  0.0, 'High'),
    ('med_samping detect21',    -3489.439453, 24715.070312, 3.909149,  0.0, 'High'),
    #('med_samping detect24',    -3479.439453, 24105.070312, 3.909149,  0.0, 'High'),
]

def ue4_to_carla(ux, uy, uz):
    """UE4 centimeter → CARLA meter"""
    return ux / 100.0, uy / 100.0, uz / 100.0

output = []
for i, (name, ux, uy, uz, yaw, tipe) in enumerate(UE4_POTHOLES):
    cx, cy, cz = ue4_to_carla(ux, uy, uz)
    cfg = TYPE_CONFIG[tipe]

    entry = {
        'id'            : f'ph_{i:04d}',
        'name'          : name,
        'x'             : round(cx, 4),
        'y'             : round(cy, 4),
        'z'             : round(cz, 4),
        'yaw'           : yaw,
        # extent = half-size dari pusat ke tepi
        'extent_x'      : cfg['extent_x'],
        'extent_y'      : cfg['extent_y'],
        'extent_z'      : 0.05,           # tipis (plane mesh)
        'severity'      : cfg['severity'],
        'severity_label': cfg['severity_label'],
        'n_obs'         : 99,
    }
    output.append(entry)

    print(f"  {entry['id']} | {name:20s} | "
          f"center=({cx:.2f}, {cy:.2f}) | "
          f"extent=({cfg['extent_x']:.2f}, {cfg['extent_y']:.2f}) | "
          f"full={cfg['extent_x']*2:.1f}m × {cfg['extent_y']*2:.1f}m | "
          f"{cfg['severity_label']}")

with open('pothole_gt.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Saved {len(output)} potholes → pothole_gt.json")