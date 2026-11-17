"""
cocokkan_gt.py — TODO #17: cocokkan hasil ukur CARLA paket dengan draf GT dari editor,
lalu tulis GT v2 (lengkap 40 objek + segmen Dika 19 objek).

Contoh:
    python cocokkan_gt.py --ukur geometri_terukur_v2.json --gt pothole_gt_editor.json

Nama objek di paket punya akhiran (mis. hole_low2_93_SM_0), jadi pencocokan memakai posisi x-y.
"""
import argparse
import json
import math

ap = argparse.ArgumentParser()
ap.add_argument("--ukur", required=True, help="keluaran ukur_geometri.py (berisi lubang_di_peta)")
ap.add_argument("--gt", default="pothole_gt_editor.json")
ap.add_argument("--sev_low", type=float, default=0.3, help="angka severity untuk objek Low (keputusan, catat di LOG)")
ap.add_argument("--toleransi", type=float, default=0.05, help="jarak maksimum dianggap cocok (m)")
ap.add_argument("--out_lengkap", default="pothole_gt_v2_lengkap.json")
ap.add_argument("--out_segmen", default="pothole_gt_v2_segmen_dika.json")
a = ap.parse_args()

ukur = json.load(open(a.ukur))["lubang_di_peta"]
gt = json.load(open(a.gt))
dipakai = set()
cocok, tidak_cocok = 0, []
for e in gt:
    jarak = [math.hypot(u["x"] - e["x"], u["y"] - e["y"]) for u in ukur]
    i = min(range(len(ukur)), key=lambda k: jarak[k]) if ukur else None
    ok = i is not None and jarak[i] <= a.toleransi
    e["terkonfirmasi_paket"] = bool(ok)
    e["jarak_cocok_m"] = round(jarak[i], 4) if i is not None else None
    if ok:
        dipakai.add(i)
        cocok += 1
        u = ukur[i]
        if abs(u["extent_x"] - e["extent_x"]) > 0.01 or abs(u["extent_y"] - e["extent_y"]) > 0.01:
            print(f"  UKURAN BEDA {e['id']} {e['name']}: editor {e['extent_x']}x{e['extent_y']}, paket {u['extent_x']:.3f}x{u['extent_y']:.3f}")
    else:
        tidak_cocok.append(e)
    if e.get("severity") is None and e["severity_label"] == "Low":
        e["severity"] = a.sev_low

lebih = [u for k, u in enumerate(ukur) if k not in dipakai]
print(f"GT editor: {len(gt)} objek | terukur di paket: {len(ukur)} objek")
print(f"COCOK (<= {a.toleransi} m): {cocok}/{len(gt)}")
for e in tidak_cocok:
    print(f"  TIDAK ADA DI PAKET: {e['id']} {e['name']} x={e['x']} y={e['y']}")
for u in lebih:
    print(f"  ADA DI PAKET, TIDAK ADA DI GT: {u['nama']} x={u['x']:.2f} y={u['y']:.2f} (cek: lubang atau bukan?)")

json.dump(gt, open(a.out_lengkap, "w"), indent=1)
seg = [e for e in gt if e.get("di_gt_dika")]
json.dump(seg, open(a.out_segmen, "w"), indent=1)
print(f"Ditulis: {a.out_lengkap} ({len(gt)}), {a.out_segmen} ({len(seg)})")
print("SELESAI #17" if cocok == len(gt) and not lebih else "BELUM SELESAI: baca baris di atas")
