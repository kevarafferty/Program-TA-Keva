# Inventaris aset Dika & Retta (diperiksa 7 November 2026, diperbarui siang setelah folder lengkap diunduh)

Lokasi dasar: `D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\`

## Ada dan sudah diperiksa

| Aset | Lokasi | Keterangan |
|---|---|---|
| Kode agen DQN | `TA_Dika Unlocked\Repository\VS_Code\DQN_Akselerasi vertikal\agent\` | `network.py` (MLP 10-128-128-64-3), `dqn_agent.py`, `replay_buffer.py` |
| Lingkungan CARLA | `...\DQN_Akselerasi vertikal\environment\carla_env.py` | Reward, kamera 640×640 FOV 90, sinkron 0,05 s |
| Bobot DQN | `...\DQN_Akselerasi vertikal\model_best.h5` + ep 100/200/300 | Keras 2.10. **Termuat dan diuji** (`03_cek_dqn`) |
| Riwayat pelatihan | `...\training_checkpoint.json` | Berhenti di episode 389, epsilon 0,0999, 349.810 langkah |
| Ground truth lubang | `...\pothole_gt.json` | 19 lubang, semua High, 2 m × 3 m (estimasi, lihat T14) |
| Log pengujian | `...\sensor_data\cerah.csv`, `hujan.csv`, `malam.csv` | Tanpa posisi x, y |
| Skrip uji | `...\cleanTest.py` | `NUM_EPISODES = 1`, epsilon 0, peta `train_fix` |
| Bobot YOLO | `TA_Dika Unlocked\Repository\YOLO-Model-main\YOLO-Model-main\best.pt` | YOLO11s, 3 kelas Low/Medium/High, dilatih imgsz 768. **Diuji** (`04_monitor_persepsi`) |
| Citra CARLA berlabel | `...\VS_Code\YOLO\CARLA\` | 53 citra 640×640, 56 kotak, semua kelas High |
| Jalan OpenDRIVE | `...\VS_Code\Map\lurus.xodr`, `map.py`, `spawnhole.py` | Belum dicoba (butuh CARLA) |
| Aset peta | `TA_Dika Unlocked\Repository\Environment\train_fix.umap`, `.uasset` | Aset Unreal mentah, belum siap dimuat (T2) |
| Kode Retta | `Retta Paper\Source Code\` | Pengendali fusi + server YOLO + `Prompt.txt` berisi perintah run |
| Laporan & makalah | `TA Dika\`, `Retta Paper\` | PDF |

## Baru ditemukan (siang, setelah folder lengkap diunduh)

| Aset | Lokasi | Keterangan |
|---|---|---|
| `best_pure.pt` versi final | `TA_Dika Unlocked\Repository\TA_Dika\VS_Code\DQN_Akselerasi vertikal\Yolo\` | **Identik** dengan `best.pt` (SHA-256 sama). Penghalang selesai |
| Rekaman uji cerah/hujan/malam | `...\DQN_Akselerasi vertikal\recordings\*.mp4` | Kamera agen + overlay, 8.505 frame. Dianalisis di `07_rekaman_dika` |
| Video uji resolusi tinggi | `TA_Dika\Video Test\` | `final cerah.mp4`, `hujan.mp4`, `malam.mp4` (±320–390 MB). Belum dianalisis |
| Aset tekstur lubang | `TA_Dika\Jalan\Pothole asset\` | PNG (`high.png`, `med.png`, ...). Lubang = gambar di plane datar (T17) |
| Ekspor jalan RoadRunner | `TA_Dika\Jalan\lurus\`, `Jalan\1\Exports\` | `R1.fbx`, `lurus.fbx`, `fix.xodr`, `fix.udatasmith` |
| Versi agen lama | `TA_Dika\VS_Code\Agen DRL\`, `progress\` | Model 7,4 MB (arsitektur lain), `best_pure.pt` lama (berbeda), pelatihan 1.200 episode |
| Catatan Dika | `TA_Dika\Catatan.txt`, `VS_Code\Perbaikan.txt`, `Model\catatan.txt` | Kompromi ukuran lubang vs deteksi YOLO |
| Kode dan catatan kerja Retta | `Retta Paper\Source Code\Retta\carla_work\` | ±40 versi skrip, log run `final7_v2_21_6_run01.csv` |
| YOLO Retta | `...\carla_work\runs\detect\runs_pothole\yolo11n_150e_9k_gpu\weights\best.pt` | yolo11n, kelas aman/sedang/parah, imgsz 640 |
| Dataset latih YOLO Retta | `...\carla_work\datasets_yolo_9k\` | 8.652 latih + 961 validasi |
| CARLA Python API 0.9.15 | `Retta\PythonAPI\carla\dist\` | Wheel `cp37` (Python 3.7 saja) |
| Panduan setup Retta | `Retta\LIDAR CARLA\README_SETUP.md`, `aktifin yolo.txt`, `requirements.txt` | Dasar `alat_carla/SETUP_ENV.md` |
| Salinan folder Dika di folder Retta | `Retta\TA_Dika\` | Duplikat; isi sama dengan `TA_Dika Unlocked\Repository\TA_Dika` |

## Masih belum ada (penghalang)

| Aset | Dibutuhkan untuk | Siapa |
|---|---|---|
| CARLA *source build* atau paket berisi `train_fix` | Reproduksi baseline di peta asli | Dika / PC lab |
| Export env conda Dika | Menjalankan kode tanpa menebak versi | Dika |
| Peta Retta (juga hanya di source build) | Opsi B, dan itu pun tidak berlaku di peta Dika (T17) | Retta / PC lab |
| Data latih YOLO Dika (`TrainYolo`) | Opsional: analisis domain gap yang persis | Dika |

## Hash SHA-256

Lihat `hash_sha256.txt`. Pakai untuk membandingkan `best.pt` dengan `best_pure.pt` saat diterima:
jika hash-nya sama, berkasnya identik.
