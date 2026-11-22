# alat_carla — skrip pengukuran di CARLA, ground truth lubang, env Python

Diperbarui 22 Nov 2026. Semua skrip di sini **sudah dijalankan** di laptop (CARLA paket 0.9.15, env `carla_env`).
Server CARLA dipanggil lewat `--host 127.0.0.1` (bukan `localhost`; lihat `LOG_KERJA.md` 10 Nov).

## Ground truth lubang (dipakai semua analisis)

| Berkas | Isi | Asal |
|---|---|---|
| `pothole_gt_v2_segmen_dika.json` | **19 lubang High** di segmen uji Dika (x −299,5 s.d. −27). GT untuk semua metrik baseline | #17, 17 Nov |
| `pothole_gt_v2_lengkap.json` | Semua 40 objek di peta: 32 High + 8 Low (Low = decal retakan, severity 0,3, tidak dihitung pelabel roda) | #17, 17 Nov |
| `pothole_gt_editor.json` | Draf GT dari editor sebelum dikonfirmasi di paket (sudah digantikan v2) | #16 |
| `geometri_terukur_v2.json` | Hasil `ukur_geometri.py` di paket: 40 objek + geometri Microlino (roda, jari-jari, setir) | #17 |
| `geometri_terukur.json` | Pengukuran pertama (18 objek, kata kunci lama). Arsip | #15 |
| `cek_material_lubang.csv` | Nama objek vs material (`highh` / `Low` / `meds`) dari editor | #16 |
| `hasil_uji_package.json` | Bukti `train_fix` ikut ter-package dan bisa dimuat (12 Nov) | #13 |

## Skrip

| Skrip | Fungsi | Cara jalan |
|---|---|---|
| `ukur_geometri.py` | Ukur posisi roda, bounding box kendaraan, dan semua objek lubang | `python ukur_geometri.py --host 127.0.0.1 --peta train_fix --kata_lubang hole_low,med_samping --out geometri_terukur_v2.json` |
| `cocokkan_gt.py` | Cocokkan hasil ukur paket dengan GT editor, tulis GT v2 | `python cocokkan_gt.py --ukur geometri_terukur_v2.json --gt pothole_gt_editor.json` |
| `uji_package_train_fix.py` | Cek `train_fix` ada di paket dan bisa dimuat | `python uji_package_train_fix.py` (CarlaUE4.exe terbuka) |
| `cek_material_lubang.py` | Baca material tiap objek lubang | Di dalam **Unreal Editor**: Output Log → Python → `py "<path>/cek_material_lubang.py"` |

## Env Python

`env_laptop/README.md` — membuat env `carla_env` di laptop dari ekspor PC lab (Python 3.8.20, `carla==0.9.15` dari PyPI,
TensorFlow 2.10, Ultralytics 8.4.13). Cek dengan `python env_laptop/cek_env.py` → harus `HASIL: LULUS`.
(Panduan lama `SETUP_ENV.md` dengan dua env + socket sudah usang dan dihapus 22 Nov.)
