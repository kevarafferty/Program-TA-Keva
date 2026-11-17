# -*- coding: utf-8 -*-
"""
Butir TODO #16 - Cek material tiap objek lubang di peta train_fix.

Dijalankan DI DALAM Unreal Editor (CARLA 0.9.15 source build, UE4.26), BUKAN di python biasa.
Cara: Window > Developer Tools > Output Log > ubah dropdown "Cmd" ke "Python" > ketik:
    py "D:/.../alat_carla/cek_material_lubang.py"
atau File > Execute Python Script... > pilih berkas ini.

Skrip hanya MEMBACA level yang sedang terbuka. Tidak ada yang diubah atau disimpan.
Hasil: <Proyek>/Saved/cek_material_lubang.csv  (path lengkap dicetak di Output Log)
"""
import csv
import json
import os

import unreal

# Path GT Dika untuk dibandingkan (ganti kalau letaknya beda; kosongkan "" untuk melewati).
GT_PATH = r"D:/ITB/Teknik Fisika/Tugas Akhir 102284tf/TA_Dika Unlocked/Repository/VS_Code/DQN_Akselerasi vertikal/pothole_gt.json"

KATA_NAMA = ("hole", "pothole", "lubang", "detect", "med_samping")
KATA_MATERIAL = ("aset_lubang", "pothole")


def tekstur_dari_material(mat):
    """Kembalikan list (path tekstur, file sumber saat impor)."""
    hasil = []
    try:
        texs = unreal.MaterialEditingLibrary.get_used_textures(mat)
    except Exception as e:  # versi API lain
        return [("ERR get_used_textures: %s" % e, "")]
    for t in texs:
        sumber = ""
        try:
            aid = t.get_editor_property("asset_import_data")
            if aid:
                sumber = aid.get_first_filename()
        except Exception:
            pass
        hasil.append((t.get_path_name(), sumber))
    return hasil


def muat_gt(path):
    if not path or not os.path.exists(path):
        unreal.log_warning("GT tidak ditemukan, kolom GT dikosongkan: %s" % path)
        return {}
    with open(path, "r") as f:
        data = json.load(f)
    return {d.get("name", ""): d for d in data}


def main():
    gt = muat_gt(GT_PATH)
    baris = []
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        label = a.get_actor_label()
        comps = a.get_components_by_class(unreal.StaticMeshComponent)
        mats = []
        for c in comps:
            for i in range(c.get_num_materials()):
                m = c.get_material(i)
                if m is not None:
                    mats.append((c, i, m))
        cocok_nama = any(k in label.lower() for k in KATA_NAMA)
        cocok_mat = any(any(k in m.get_path_name().lower() for k in KATA_MATERIAL) for _, _, m in mats)
        if not (cocok_nama or cocok_mat):
            continue
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        scl = a.get_actor_scale3d()
        _, ext = a.get_actor_bounds(False)
        g = gt.get(label, {})
        if not mats:
            mats = [(None, -1, None)]
        for c, i, m in mats:
            mesh = c.static_mesh.get_path_name() if (c and c.static_mesh) else ""
            mat_path = m.get_path_name() if m else ""
            # material instance -> catat juga parent-nya
            parent = ""
            if isinstance(m, unreal.MaterialInstance):
                p = m.get_editor_property("parent")
                parent = p.get_path_name() if p else ""
            tex = tekstur_dari_material(m) if m else []
            baris.append({
                "label": label,
                "kelas_aktor": a.get_class().get_name(),
                # CARLA = koordinat UE dalam meter (cm / 100)
                "x_m": round(loc.x / 100.0, 3),
                "y_m": round(loc.y / 100.0, 3),
                "z_m": round(loc.z / 100.0, 3),
                "yaw_deg": round(rot.yaw, 2),
                "panjang_x_m": round(2 * ext.x / 100.0, 3),
                "lebar_y_m": round(2 * ext.y / 100.0, 3),
                "skala": "%.3f;%.3f;%.3f" % (scl.x, scl.y, scl.z),
                "mesh": mesh,
                "slot": i,
                "material": mat_path,
                "material_parent": parent,
                "tekstur": " | ".join(t for t, _ in tex),
                "file_sumber_tekstur": " | ".join(s for _, s in tex),
                "gt_ada": "ya" if g else "tidak",
                "gt_x": g.get("x", ""),
                "gt_y": g.get("y", ""),
                "gt_severity_label": g.get("severity_label", ""),
            })
    baris.sort(key=lambda r: r["x_m"])
    out = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()),
                       "cek_material_lubang.csv")
    if baris:
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(baris[0].keys()))
            w.writeheader()
            w.writerows(baris)
    # ringkasan
    hitung = {}
    for r in baris:
        k = (r["material"].split(".")[-1], r["gt_severity_label"] or "-")
        hitung[k] = hitung.get(k, 0) + 1
    unreal.log("=== cek_material_lubang: %d baris, %d aktor unik ===" % (len(baris), len({r['label'] for r in baris})))
    for (mat, gtl), n in sorted(hitung.items()):
        unreal.log("  material=%-12s  GT=%-6s  : %d" % (mat, gtl, n))
    unreal.log("CSV: " + out)


main()
