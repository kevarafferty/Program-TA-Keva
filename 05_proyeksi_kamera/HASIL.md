# Proyeksi kamera 3D → 2D

**Status:** kode dan 8 uji unit selesai (`hasil_uji_unit.txt`). Pemeriksaan visual pada frame CARLA
belum dilakukan karena butuh simulator dan pose kendaraan per frame.

## Isi `proyeksi_kamera.py`

| Fungsi | Kegunaan |
|---|---|
| `proyeksikan(kam, pose, titik)` | Titik dunia → piksel |
| `kotak_2d_lubang(kam, pose, lubang)` | Entri `pothole_gt.json` → kotak 2D di citra, atau None jika tidak terlihat |
| `piksel_ke_jalan(kam, u, v)` | Piksel → titik di permukaan jalan (meter di depan dan di kanan mobil) |
| `baris_horizon(kam)` | Baris horizon citra |

Preset: `KAMERA_DIKA` (640×640, FOV 90°, z 2,0 m, pitch −15°), `KAMERA_RETTA` (bawaan kode Retta),
`KAMERA_RETTA_RUN` (FOV 120°, 1600×900, dari perintah run Retta).

Matriks transform disalin dari `carla.Transform.get_matrix()` dan bingkai kamera sama dengan `CameraProjector`
di kode Retta, sehingga hasilnya konsisten dengan kode yang sudah dipakai di lab.

## Angka yang berguna untuk kamera Dika

| Jarak lubang dari mobil | cy (dinormalisasi) |
|---:|---:|
| 30 m | 0,40 |
| 15 m | 0,44 |
| 10 m | 0,49 |
| 8 m | 0,52 |
| 5 m | 0,65 |

Horizon ada di baris 234 dari 640 (cy 0,37). Semua lubang lebih jauh dari ~15 m terjepit di pita sempit cy 0,37–0,44,
sehingga resolusi jarak dari YOLO di imgsz 320 sangat kasar pada jarak jauh.

## Untuk diverifikasi di CARLA

1. Ukur tinggi titik asal Microlino terhadap jalan (`alat_carla/ukur_geometri.py`). Proyeksi mengasumsikan 0.
2. Rekam 10 frame dengan pose kendaraan, gambar `kotak_2d_lubang` di atas citra, cek apakah menempel di lubang.
3. Catatan: 53 citra di `YOLO/CARLA` kemungkinan diambil dengan kamera lain (terlihat kap mobil; `TestYolo.py`
   memakai Tesla Model 3), jadi tidak bisa dipakai untuk verifikasi ini.
