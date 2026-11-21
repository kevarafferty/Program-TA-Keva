# Log kerja TA

Satu entri per sesi kerja. Tulis apa yang dikerjakan, keputusan yang diambil, dan asumsi yang dipakai,
supaya siapa pun (termasuk kamu enam bulan lagi) bisa melacak asal setiap angka.

---

## 2026-11-07 (Sabtu) — dikerjakan Claude atas permintaan Keva

**Permintaan:** kerjakan semua tugas di checklist yang bisa diselesaikan tanpa CARLA, dan catat semuanya.

**Lingkungan kerja:** salinan berkas dari `D:\ITB\Teknik Fisika\Tugas Akhir 102284tf` dijalankan di workspace cloud
Claude (Linux, Python 3.13, CPU). Tidak ada berkas asli Dika/Retta yang diubah. Semua hasil ditulis ke folder baru
`Keva_TA_Kerja\`. Versi paket: lihat `requirements.txt`.

### Yang dikerjakan

| No | Pekerjaan | Hasil | Folder |
|---|---|---|---|
| 1 | Inventaris aset + hash SHA-256 | 13 aset tercatat, 5 penghalang | `01_inventaris` |
| 2 | Pelabel kontak roda–lubang + uji unit + perbandingan dengan logika Dika | 14/14 uji lulus, 2 grafik | `02_pelabel_roda` |
| 3 | Uji muat `model_best.h5` + sapuan jarak | Termuat di TF 2.21; NumPy = Keras | `03_cek_dqn` |
| 4 | Hook logit YOLO per deteksi | Identik dengan `predict()` pada 689 inferensi | `04_monitor_persepsi` |
| 5 | Prototipe monitor persepsi offline (53 citra × 13 kondisi) | Tabel AUROC + CI bootstrap | `04_monitor_persepsi` |
| 6 | Fungsi proyeksi kamera 3D → 2D | 8/8 uji lulus | `05_proyeksi_kamera` |
| 7 | Alat ukur geometri untuk dijalankan di CARLA | Ditulis, **belum diuji** (butuh simulator) | `alat_carla` |
| 8 | Draf pesan ke Dika dan Retta | Siap kirim | `06_pesan` |
| 9 | Ringkasan temuan | 15 temuan | `TEMUAN.md` |

### Keputusan dan asumsi (perlu kamu setujui atau ubah)

1. **Geometri Microlino** di pelabel roda memakai estimasi (lebar jejak 1,20 m, setengah lebar ban 0,075 m,
   poros ±0,75 m). Alasan: belum bisa diukur tanpa CARLA. Semua angka rentang offset di `TEMUAN.md` akan bergeser.
2. **Label kegagalan persepsi offline** = kotak conf tertinggi tidak mengenai lubang (IoU < 0,3) atau tidak ada
   deteksi. Alasan: agen DQN hanya melihat kotak teratas. IoU 0,3 (bukan 0,5) karena lubang kecil dan jauh.
3. **Label severity tidak dipakai** sebagai kegagalan, karena `best.pt` hampir tidak pernah memprediksi High
   pada citra CARLA (T4). Ini menyimpang dari definisi di Subbab 2.1.3 proposal dan perlu didiskusikan.
4. **Pembagian data** 26 citra (fit) / 27 citra (uji) dengan seed 13; bootstrap per citra asal.
5. **Git belum dibuat.** Folder di laptopmu tidak mengizinkan Claude menghapus berkas, sedangkan git butuh itu
   untuk berkas kunci. Buat sendiri: `git init` di folder `Keva_TA_Kerja` lalu commit pertama.
6. Hasil "gelap" offline **tidak** dianggap bukti untuk kondisi malam (T11).

### Yang tidak bisa dikerjakan Claude dan tetap menunggu kamu

- Memasang CARLA 0.9.15 dan memastikan berjalan di RTX 4060
- Menjalankan `alat_carla/ukur_geometri.py`
- Menjalankan stack Retta, uji pemunculan lubang dari `lurus.xodr`
- Mengirim pesan ke Dika dan Retta, menemui dosbing
- Reproduksi baseline dan evaluasi 30 episode

### Cara mengulang semua hasil

```
pip install -r requirements.txt
cd 02_pelabel_roda && python -m pytest -q test_kontak_roda.py && python bandingkan_dengan_dika.py --gt "<...>\pothole_gt.json" --out hasil
cd ..\03_cek_dqn && python cek_model_dqn.py --h5 "<...>\model_best.h5" && python sapuan_jarak_dqn.py --h5 "<...>\model_best.h5"
cd ..\04_monitor_persepsi && python verifikasi_hook.py --bobot "<...>\best.pt" --citra "<...>\VS_Code\YOLO\CARLA"
python prototipe_monitor_persepsi.py --bobot "<...>\best.pt" --citra "<...>\VS_Code\YOLO\CARLA" --out hasil
cd ..\05_proyeksi_kamera && python -m pytest -q test_proyeksi_kamera.py
```
Prototipe monitor persepsi butuh ±2 menit di CPU.

---

## 2026-11-07 (Sabtu siang) — dikerjakan Claude setelah Keva mengunduh folder lengkap Dika & Retta

**Permintaan:** cek folder baru, kerjakan yang bisa dikerjakan, dan catat semuanya.

### Yang dikerjakan

| No | Pekerjaan | Hasil | Lokasi |
|---|---|---|---|
| 1 | Memetakan folder baru `TA_Dika` (Dika) dan `Retta` (Retta) | Inventaris diperbarui: 13 aset baru, 4 penghalang tersisa | `01_inventaris/inventaris_aset.md` |
| 2 | Membandingkan hash `best_pure.pt` dengan `best.pt` | Identik; penghalang pertama selesai | T16 |
| 3 | Memeriksa cara lubang dibuat di peta Dika (Bab III + aset) | Gambar PNG di plane datar, bukan cekungan | T17 |
| 4 | Memeriksa cara peta Retta dijalankan | Source build Unreal; kedua peta butuh source build | T18 |
| 5 | Mencocokkan video uji dengan CSV | Cerah: run berbeda. Hujan, malam: cocok 100% | T19 |
| 6 | Mengekstrak 8.505 frame rekaman uji + membaca status deteksi agen dari overlay | Status deteksi sama 100% dengan CSV | `07_rekaman_dika` |
| 7 | Evaluasi monitor persepsi pada frame CARLA asli | Lihat T20, T21, T23 | `07_rekaman_dika/HASIL.md` |
| 8 | Uji jarak frame CARLA ke foto jalan nyata | Alarm 100% bahkan di cerah | T22 |
| 9 | Panduan environment dari catatan Retta | Jebakan Python 3.7 vs 3.8+ dicatat | `alat_carla/SETUP_ENV.md` |
| 10 | Merevisi pesan ke Dika (9 → 5 butir) dan Retta (3 → 2 butir) | Siap kirim | `06_pesan/` |

### Keputusan dan asumsi (perlu kamu setujui atau ubah)

1. **Kesalahan yang sudah diperbaiki di tengah jalan:** pembacaan penghitung Hits/Avoids pertama memakai kecerahan dan
   menghasilkan ratusan kejadian palsu. Diganti dengan pembacaan warna teks + jangkar dari CSV. Integrasi kecepatan juga
   dicoba dan ditolak, karena melenceng 2–13 m akibat gerak zig-zag.
2. **Ambang alarm pertama dikalibrasi pada data fit itu sendiri**, sehingga alarm palsu di cerah 92%. Diganti dengan
   pembagian tiga arah (fit / kalibrasi / uji) dan PCA. Alarm palsu cerah turun menjadi 6%.
3. **Skor per deteksi dari video tidak dilaporkan**, karena YOLO yang dijalankan ulang hanya sepakat 41–46% dengan deteksi
   agen akibat kompresi video.
4. **Label "dalam jangkauan" = pusat lubang 3–15 m di depan**, lajur mana pun, karena posisi lateral tidak tercatat.
5. Sampel foto jalan nyata untuk T22 = 91 citra validasi dataset Retta, bukan data latih `best.pt` yang sebenarnya.
6. File `.npz` (±28 MB) ikut disalin supaya analisis bisa diulang tanpa menjalankan YOLO lagi.

### Yang tidak bisa dikerjakan Claude dan tetap menunggu kamu

- Semua yang butuh CARLA berjalan (tidak berubah dari pagi)
- Menghubungi Dika/Retta soal source build dan env conda
- Memutuskan bersama dosbing: label kegagalan per lintasan lubang (T21), definisi densitas fitur (T22), Opsi B (T17)

### Cara mengulang analisis rekaman

```
cd 07_rekaman_dika
python ekstrak_rekaman.py --video "<...>\recordings\malam.mp4" --kondisi malam --bobot "<...>\Yolo\best_pure.pt" --out data
python baca_penghitung.py --video "<...>\recordings\malam.mp4" --kondisi malam --out data
(ulangi untuk cerah dan hujan)
python analisis_rekaman.py --data data --gt "<...>\pothole_gt.json" --csv_dir "<...>\sensor_data" --out hasil --split selang
python analisis_rekaman.py --data data --gt "<...>\pothole_gt.json" --csv_dir "<...>\sensor_data" --out hasil_paruh --split paruh
python cek_domain_gap.py --bobot "<...>\best_pure.pt" --nyata "<...>\datasets_yolo_9k\images\val" --data data --out hasil
```
Ekstraksi butuh ±10 menit per video di CPU 2 core. Analisis kurang dari 1 menit.

---

## 2026-11-08 (Minggu) — dikerjakan Claude atas permintaan Keva

**Permintaan:** bandingkan PDF proposal (versi Oktober) dengan semua temuan, sajikan dalam tabel.

### Yang dikerjakan

| No | Pekerjaan | Hasil | Lokasi |
|---|---|---|---|
| 1 | Membaca PDF proposal 37 halaman dan mencocokkannya dengan T1–T24 | 19 perbedaan dalam 4 kelompok (5 butuh dosbing) | `PERBEDAAN_PROPOSAL.md` |
| 2 | Mengecek panjang lintasan di `pothole_gt.json` | Lubang tersebar ±250 m, bukan 27 m seperti di §2.1.2 | butir 16 |

### Catatan

- Nomor subbab di `TEMUAN.md` merujuk versi proposal lama. Pakai nomor di `PERBEDAAN_PROPOSAL.md` untuk revisi.
- Belum ada perubahan pada proposal itu sendiri; semua usulan menunggu keputusan Keva dan dosbing.

### Sore: persiapan kunjungan lab (Senin 9 Nov)

| No | Pekerjaan | Hasil | Lokasi |
|---|---|---|---|
| 3 | Script pengumpul info PC lab (hanya membaca): disk, GPU, versi CARLA, lokasi `train_fix.umap`, hash berkas Dika, ekspor semua env conda | Ditulis, **belum diuji** (butuh Windows + PC lab) | `08_kunjungan_lab/kumpulkan_info_lab.bat` |
| 4 | Ceklis lab berurutan + hash pembanding 5 berkas Dika | Siap dipakai | `08_kunjungan_lab/CEKLIS_LAB.md` |

**Asumsi yang belum pasti:** `make package` pada source build Dika akan ikut memasak peta `train_fix`. Belum pernah dicoba;
ceklis memuat uji `get_available_maps()` untuk memastikannya. Lama package (2–4 jam) adalah perkiraan.

---

## 2026-11-10 (Selasa): penggabungan folder kerja

- Isi `Keva_TA_Kerja/` dipindahkan ke `Program TA Keva/`: `08_kunjungan_lab/`, `PERBEDAAN_PROPOSAL.md`, serta versi 8 Nov dari `LOG_KERJA.md` dan `README.md`. Versi baru ini mencakup seluruh isi versi 7 Nov, jadi tidak ada yang hilang. Versi lamanya tetap ada di commit `3f4aaed`.
- **Belum dikerjakan:** commit perubahan ini; folder kosong `Keva_TA_Kerja/` masih ada, hapus secara manual.

---

## 2026-11-10 (Selasa) sore: kunjungan lab dan analisis hasilnya (Claude)

### Yang dikerjakan Keva di lab

| No | Pekerjaan | Hasil | Lokasi |
|---|---|---|---|
| 1 | `kumpulkan_info_lab.bat` | Berhasil. CARLA **0.9.15** source build di `D:\carla`, UE4 fork commit `e22f1e2` | `08_kunjungan_lab/hasil_lab/` |
| 2 | `make launch` + Play `train_fix` | Berhasil (harus dari x64 Native Tools Command Prompt) | — |
| 3 | `ukur_geometri.py` | Berhasil, 18 objek lubang | `alat_carla/geometri_terukur.json` |
| 4 | `cleanTest.py` dari folder **Agen DRL** | Jalan, tetapi itu versi lain (lihat temuan 3) | hasil belum dibawa |
| 5 | `make package` | **Gagal**: D: tinggal 3,8 GB, C: 4,2 GB | — |
| 6 | Migrate `train_fix` | Sebagian: peta + aset Static, **tanpa** `Maps/Aset_Lubang` | `train_fix_migrate/` |
| 7 | `git status/diff/log` CARLA + UE4 | Berhasil | `08_kunjungan_lab/*.txt` |

### Temuan analisis Claude

1. **Geometri Microlino terukur berbeda dengan estimasi.** Jejak roda depan 1,19 m, belakang 0,72 m (estimasi lama 1,20 m untuk keduanya). Sumbu depan +0,684 m, belakang -0,841 m, jari-jari ban 0,25 m. Pelabel roda harus memakai jejak depan dan belakang terpisah, bukan rata-rata 0,957 m.
2. **Lubang di peta: 18 objek, semuanya bernama `hole_low*`**, sedangkan `pothole_gt.json` berisi 19. Lubang ke-19 (kemungkinan `highh`) tidak tertangkap kata kunci.
3. **Folder `Agen DRL` ≠ `DQN_Akselerasi vertikal`.** Agen DRL memakai `model_episode_800.h5`, YOLO hash `3bb64f…`, cuaca `SoftRainNoon`, 3 episode, tanpa CSV. Folder yang cocok dengan video hasil TA Dika (cerah/hujan/malam) dan dengan salinan laptop adalah **DQN_Akselerasi vertikal**. Gate 1 harus memakai folder itu.
4. **"dirty" di build lab hanya perbaikan URL unduhan** (Update.bat, boost, zlib) + plugin di `.uproject`. Tidak ada perubahan kode simulasi C++, jadi CARLA 0.9.15 bersih + 4 perbaikan URL itu setara.
5. **Peta mereferensikan `/Game/Carla/Maps/Aset_Lubang/Low` dan `/highh`**, tetapi keduanya tidak ikut Migrate dan tidak ada di laptop. Tanpa itu lubang tampil tanpa material, dan YOLO tidak akan melihatnya.
6. Peta tidak memakai plugin Houdini (tidak ada referensi `/Script/Houdini*`).

### Keputusan

- Jalur B dipilih Keva: CARLA 0.9.15 **source build** di laptop.

### Belum dikerjakan

- [ ] Ambil dari PC lab: folder `Content\Carla\Maps\Aset_Lubang\`, berkas `Content\Carla\Maps\OpenDrive\train_fix.xodr`, dan semua `Content\Carla\Maps\train_fix*`
- [ ] Hasil Hits/Avoids run Agen DRL hari ini (foto baris 📊) — opsional, bukan run Gate 1
- [ ] Source build CARLA 0.9.15 + UE4 `e22f1e2` di laptop; terapkan 4 perbaikan URL dari `carla_diff.txt`
- [ ] Perbarui `GeometriKendaraan` di `02_pelabel_roda/kontak_roda.py` dengan nilai terukur, lalu jalankan ulang uji
- [ ] Run `cleanTest.py` dari **DQN_Akselerasi vertikal** (malam, cerah, hujan) setelah build jadi

### Tambahan 17:23: run malam `DQN_Akselerasi vertikal` di PC lab (dijalankan Keva)

- Berkas: `cleanTest.py` hash `5a198eaa…` (sama dengan salinan laptop), `model_best.h5` `4a5055b6…`, cuaca `ClearNight`, env `carla_env`, 1 episode.
- **Hasil: Avoids 7, Hits 12 (7/19 = 37%)**, 2769 langkah, reward −405,78. Dika melaporkan 9/19 (47%).
- Lubang yang dihindari: ph_0000, 0001, 0003, 0012, 0014, 0017, 0018. Semua lubang di GT ber-severity 0,9.
- Perbandingan: mobil lurus tanpa menghindar menghasilkan 9/19 (temuan sebelumnya). Run ini **lebih buruk daripada tidak menghindar sama sekali**.
- Model dan kode sama, hasil beda 2 lubang dari angka Dika. Satu episode tidak cukup untuk Gate 1; perlu banyak episode.
- Error `resolve: The requested name is valid, but no data...` di `carla.Client('localhost')` sempat muncul lalu hilang. Dugaan: Cloudflare WARP. Perbaikan: pakai `127.0.0.1`.
- Catatan: run dijalankan di folder asli, jadi `recordings\test_run_ep1.mp4` dan `sensor_data\sensor_log_all_episodes.csv` milik Dika di PC lab tertimpa. Versi lama masih ada di salinan laptop (`TA_Dika Unlocked/Repository/VS_Code/DQN_Akselerasi vertikal/`).

- [ ] Salin video + CSV run ini ke laptop (`08_kunjungan_lab/run_malam_lab/`)
- 17:26: CSV run malam utuh (dicek Keva). Video **tidak terbentuk** karena D: penuh; tidak dibutuhkan, angka sudah tercatat di atas.
- Aset tambahan sudah disalin Keva ke SSD (`asset_lab`): `Aset_Lubang` (10 .uasset termasuk `Low`, `highh`, tekstur `Wall_Crack_PNG…`), `train_fix*`, `OpenDrive\`.
- [ ] Pindahkan `asset_lab` dan `run_malam_lab` dari SSD ke `Program TA Keva/08_kunjungan_lab/`
- [ ] Kabari Dika: `recordings\test_run_ep1.mp4` di PC lab tertimpa/rusak

---

## 2026-11-10 (Selasa) malam: pemeriksaan hasil lab terhadap proposal (Claude)

### Yang dikerjakan

| No | Pekerjaan | Hasil |
|---|---|---|
| 1 | Mencocokkan 18 objek di `geometri_terukur.json` dengan 19 entri `pothole_gt.json` | Hanya 11 cocok (jarak 0 m). 8 entri GT `med_samping detect*` tidak terukur; 7 objek peta di luar GT |
| 2 | Memperbarui `PERBEDAAN_PROPOSAL.md` | Bagian E: 6 butir baru, 7 butir lama berubah status. Total 25 butir |

### Koreksi atas catatan sore

- Temuan 2 sore ("lubang ke-19 kemungkinan `highh`") **keliru**. Yang tidak tertangkap ada 8 lubang bernama `med_samping detect*`, karena kata kunci pengukuran tidak memuat `med`/`samping`/`detect`.

### Belum dikerjakan

- [ ] Ukur ulang lubang dengan kata kunci tambahan (perlu CARLA berjalan)
- [ ] Cek material tiap objek lubang di editor: `Low` atau `highh` (E6)
- [ ] Perbarui `GeometriKendaraan` dengan jejak depan/belakang terpisah, jalankan ulang T5 dan T6
- [ ] Pindahkan `asset_lab` dan `run_malam_lab` dari SSD ke `08_kunjungan_lab/` (belum ada di folder)
- [ ] Commit: `08_kunjungan_lab/`, `PERBEDAAN_PROPOSAL.md`, `geometri_terukur.json`, `train_fix_migrate/` masih untracked

---

## 2026-11-10 (Selasa) malam: todo list TA lengkap (Claude)

- Dibuat `TODO_TA.csv`: 44 tugas (6 milestone) dari 10 Nov 2026 s.d. 28 Feb 2027, dengan tanggal, durasi, ketergantungan, dan critical path. Sudah memperhitungkan 25 butir di `PERBEDAAN_PROPOSAL.md`.
- Gate 1 dijadwalkan ulang ke 24 Nov (dari 15 Nov); Gate 2 tetap ±6 Des; Gate 3 tetap 24 Jan. **Belum disetujui dosbing.**
- **Belum dikerjakan:** memasukkan tugas ke aplikasi tugas Keva (dikerjakan Keva).
- 18:3x: dibuat `09_carla_laptop/PANDUAN_BUILD.md` (source build CARLA 0.9.15 + UE4 e22f1e2 di laptop). Temuan: env `carla_env` Dika = Python 3.8 + `carla==0.9.15` dari pip, jadi `make PythonAPI` tidak diperlukan. Bagian `.uproject` dari diff lab sengaja tidak diterapkan (plugin Houdini/StreetMap). **Belum:** build dijalankan Keva.

---

## 2026-11-11 (Rabu) malam: TODO #11 env Python laptop (Claude)

- Dibuat `alat_carla/env_laptop/`: `README.md` (langkah), `requirements_carla_env.txt` (pip freeze lab tanpa torch), `cek_env.py` (cek import, versi, GPU, koneksi server).
- Temuan: env lab berisi cuDNN 9.10, padahal TF 2.10 butuh cuDNN 8.1 → TF di PC lab kemungkinan jalan di CPU (**Dugaan**, belum dicek di PC lab). Torch membawa CUDA sendiri, jadi YOLO tetap GPU.
- `SETUP_ENV.md` diberi catatan usang (asumsi Python 3.7/dua env sudah tidak berlaku).
- **Belum:** Keva menjalankan langkah README di laptop dan mencatat hasil `cek_env.py` di sini. Putuskan TF GPU (cuDNN 8.1) atau CPU.

## 11 Nov 2026 malam: env carla_env di laptop (tugas #11)
- Selesai: conda env `carla_env` (Python 3.8) + `carla==0.9.15` (pip, tanpa make PythonAPI) + paket dari `pip_carla_env.txt`. Uji impor: carla OK, TF 2.10.0, ultralytics 8.4.13, torch 2.4.1+cu118.
- Belum: `torch.cuda.is_available()` = False (YOLO jalan di CPU). Cek driver lewat `nvidia-smi`. Uji koneksi server menunggu build CARLA.
- 23.37: **CARLA source build jalan di laptop.** `get_server_version()` dari `carla_env` ke 127.0.0.1:2000 = `0.9.15-dirty` (dirty = 3 perbaikan URL, sama dengan PC lab). Tugas #8–#10 selesai.
- Berikutnya: #12 masukkan `train_fix` + `Aset_Lubang` + OpenDrive lalu Play; #16 cek material lubang (E6) sebelum bimbingan Jumat. CUDA torch masih False.
- 23.45: Koreksi: diff lab berisi 3 perbaikan URL (Update.bat, install_boost.bat, install_zlib.bat) + DefaultEngine.ini (opsional) + .uproject (jangan). Label "4 perbaikan URL" di TODO_TA.csv dan PERBEDAAN_PROPOSAL.md diganti "3". Keva perlu cek `git status` di D:\carla.
- 23.50: CUDA torch sekarang True (CUDA 11.8, 1 GPU) -> YOLO bisa pakai GPU. git status D:\carla = tepat 3 berkas URL (terverifikasi). Arsip 20231108_c5101a5.tar.gz (21 GB) masih di Content\Carla; pindahkan/hapus sebelum make package (#13).
- 23.53: **#12 selesai.** train_fix terbuka di editor laptop dan bisa Play (3.299 actor; lubang tampak sebagai tekstur datar, konsisten T17). Peringatan "Reflection captures need to be rebuilt" tidak berpengaruh. Berikutnya: #16 cek material lubang (E6), lalu #13 make package.
- 23.57: train_fix.xodr disalin ke D:\carla\...\Maps\OpenDrive\ (sebelumnya get_map() gagal "unable to parse the OpenDRIVE XML string"). Sekarang get_map().name = Carla/Maps/train_fix. Peringatan "Version mismatch 0.9.15 vs 0.9.15-dirty" aman diabaikan.
- 00.05 (12 Nov): Cek material (#16, sebagian): 10 hole_low* di GT = High (GT benar, E6 gugur untuk ini); 8 hole_low16-24 di luar GT = Low. GT = 10 hole_low + 9 med_samping. Belum: material med_samping detect*. Ditulis di PERBEDAAN_PROPOSAL.md.

## 2026-11-12 (Kamis) dini hari: persiapan TODO #13 make package (Claude)

- Dibaca dari laptop: `D:\carla\Util\BuildTools\Windows.mk`, `Package.bat`, `BuildPythonAPI.bat`, `Unreal\CarlaUE4\Config\DefaultGame.ini`, `DefaultEngine.ini`.
- Temuan 1: `train_fix` **tidak** ada di `+MapsToCook` DefaultGame.ini. Tanpa ditambah, `make package` tidak memasukkan train_fix (paket hanya berisi Town01–10 dkk.). Lubang (Aset_Lubang) ikut otomatis sebagai dependensi peta.
- Temuan 2: `make package` bergantung pada target `PythonAPI` (`py -3 setup.py bdist_egg bdist_wheel`). Tidak dibutuhkan karena client dari pip. Usulan: jalankan `BuildCarlaUE4.bat --at-least-write-optionalmodules` + `Package.bat --ue-version 4.26 --no-zip` langsung (isi sama dengan langkah kedua `make package`).
- Temuan 3: OpenDRIVE ikut terbawa otomatis (`DirectoriesToAlwaysStageAsUFS=Carla/Maps/OpenDrive`), asal `train_fix.xodr` ada di folder itu (sudah, 11 Nov 23.57).
- Temuan 4: default/transition map = `Town10HD_Opt`, jadi peta itu wajib tetap di-cook kalau daftar dipangkas.
- Dibuat `alat_carla/uji_package_train_fix.py`: cek daftar peta, load_world, OpenDRIVE, posisi 18 lubang vs `geometri_terukur.json`, lalu arahkan kamera ke lubang. Hasil ke `alat_carla/hasil_uji_package.json`. **Belum diuji** (butuh hasil package).
- **Belum (dikerjakan Keva):** pindahkan arsip 21 GB, edit DefaultGame.ini, jalankan package, jalankan uji, cek visual tekstur, catat hasil di sini.
- 00.15: Percobaan package pertama gagal (`DirectoryNotFoundException ... D:\UnrealEngine\Engine\Source\Unreal\CarlaUE4`). Penyebab: **kesalahan instruksi Claude**. `Package.bat`/`BuildCarlaUE4.bat` butuh variabel `ROOT_PATH` dan `INSTALLATION_DIR` yang biasanya di-export oleh `make` (Windows.mk). Dipanggil langsung, variabelnya kosong sehingga path .uproject jadi relatif. Perbaikan: `set ROOT_PATH=D:/carla/` dan `set INSTALLATION_DIR=D:/carla/Build/` sebelum kedua .bat.
- Efek samping run gagal: plugin Houdini di-clone ke `D:\carla\Unreal\CarlaUE4\Plugins\HoudiniEngine` (perilaku standar BuildCarlaUE4.bat, sama dengan `make package`); OptionalModules.ini tidak tertulis ulang (tidak masalah, akan ditulis ulang).
- DefaultGame.ini diperbaiki Claude: tanda `;` untuk 11 baris Town01–05 + Town10HD tertulis di **akhir** baris (tidak berlaku sebagai komentar). Dipindah ke awal baris. Yang di-cook sekarang: Town10HD_Opt, OpenDriveMap, EmptyMap, train_fix.
- 14.28 (12 Nov): CarlaUE4.exe hasil package terbuka dan menampilkan Town10HD_Opt (peta awal bawaan, sesuai GameDefaultMap di DefaultEngine.ini; bukan tanda gagal). Belum: jalankan uji_package_train_fix.py untuk memuat train_fix.
- 14.30: **Uji package LULUS** (`alat_carla/hasil_uji_package.json`): `train_fix` ada di daftar peta, `load_world` berhasil, OpenDRIVE terbaca (12.958 waypoint per 2 m), **18/18 lubang hasil ukur editor ada di posisi yang sama** di build Shipping. Nama objek di package sama dengan editor (mis. `hole_low10_SM_0`).
- Catatan: kata kunci baru (hole, med, samping, detect, ...) menangkap 40 objek. Belum dipilah mana yang lubang (bahan #17). Daftar peta hanya berisi Town10HD_Opt + train_fix; OpenDriveMap/EmptyMap kemungkinan disaring oleh `get_available_maps`, **belum dicek** (baru perlu kalau jalur cadangan lurus.xodr dipakai).
- Belum: cek visual tekstur lubang di jendela CARLA (syarat terakhir #13). Lalu #14 milestone.

## 2026-11-12 (Kamis) sore: TODO #15 pelabel roda dengan geometri terukur (Claude + Keva)

- Kode diubah (Claude): `GeometriKendaraan` kini punya `jejak_depan` 1,192 m dan `jejak_belakang` 0,722 m terpisah; poros depan +0,684 m, belakang -0,841 m; bodi 0,740 / 1,104 m. Default fungsi = `MICROLINO` (terukur). `MICROLINO_ESTIMASI` dipertahankan untuk mengulang hasil lama. `logika_dika()` tidak diubah. Angka 2,175 yang tertulis langsung di `bandingkan_dengan_dika.py` diganti nilai hitungan.
- Uji: 2 uji diperbarui (posisi roda; uji mengangkangi kini lubang 0,4 m), 1 uji baru (lubang 0,6 m kena kedua ban belakang). Dijalankan Keva di laptop: **15/15 lulus** (15.36).
- Hasil (`02_pelabel_roda/hasil/ringkasan_perbandingan.json`): rentang salah hitung Dika tetap 1,84–2,16 m (batas kontak 2,175 → 2,171 m); cooldown tetap mulai 11 km/jam pada 13 m; mobil lurus lajur spawn tetap 9/19 = 47,4%, lajur kiri 10/19.
- **Temuan baru:** jejak belakang sempit → lubang yang bisa dikangkangi tanpa kontak hanya < 0,57 m (estimasi lama: 1,05 m). T5, T6 di `TEMUAN.md` dan `02_pelabel_roda/HASIL.md` diperbarui.
- Keputusan: `lebar_jejak` 0,957 m di `geometri_terukur.json` (rata-rata) **tidak dipakai**.
- Cadangan: `02_pelabel_roda/cadangan_estimasi/` (berkas `kontak_roda` di sana sudah berisi edit Keva 15.25, bukan versi asli) dan berkas `hasil/*_estimasi.*`.
- **Belum:** `TODO_TA.csv` belum ditandai selesai (berkas terkunci, kemungkinan terbuka di Excel). r_w (setengah lebar ban) masih estimasi 0,075 m. Angka T5 masih memakai `pothole_gt.json` lama → dihitung ulang di #18 setelah GT baru (#17).
- 13 Nov 01.10: Dibuat `Bimbingan_5_Butir_TA_Keva.pptx` (9 slide, design system Gallery, urutan 3-1-4-5-2, butir 4 berisi dua pilihan: kamera saja / lubang 3D + LiDAR-IMU). Belum: cek material med_samping, arsip 21 GB, make package (#13).

---

## 2026-11-16 (Senin) — Butir TODO #16: cek material lubang (persiapan oleh Claude)

### Yang dikerjakan
| No | Pekerjaan | Hasil | Lokasi |
|---|---|---|---|
| 1 | Membaca string biner aset `Aset_Lubang` dan `train_fix.uasset` (tanpa editor) | Lihat temuan awal di bawah | `train_fix_migrate/Content/Carla/Maps/` |
| 2 | Menulis skrip Python untuk Unreal Editor yang mengekspor nama aktor, posisi, ukuran, material, tekstur, dan label GT Dika | Ditulis, **belum diuji** (butuh editor) | `alat_carla/cek_material_lubang.py` |

### Temuan awal (Dugaan kuat, perlu konfirmasi di editor)
- `High.uasset`, `Med.uasset`, `highs.uasset` adalah **ObjectRedirector**, bukan material. Rantai: `High` → `Med` → `highh`; `highs` → `meds`. Nama material tidak bisa dipercaya.
- Material asli: `highh` → tekstur `hiigh` (sumber `high-removebg-preview.png`); `Low` → tekstur `Lows` (sumber `T_DecRodCrack_1_op.TGA`, decal retakan bawaan CARLA); `meds` → tekstur `medd` (sumber `CRACK-removebg-preview.png`).
- Peta `train_fix.uasset` hanya mereferensikan dua material: `Low` dan `highh`. Ada 18 nama `hole_low*` dan 21 nama `med_samping detect*` (total 39 = jumlah entri `pothole_gt_backup_lengkap.json`).
- Jika `hole_low*` memakai `Low` (retakan), YOLO yang memberi Low benar dan GT "High" yang keliru (E6). Pemetaan per aktor belum bisa dibaca dari biner.

### Belum dikerjakan (menunggu Keva)
- Menjalankan `cek_material_lubang.py` di editor source build dan mengirim CSV-nya.
- Mencocokkan hasil dengan GT, lalu memperbarui E6, T4, H1, dan butir #3 di PERBEDAAN_PROPOSAL.md.

## 2026-11-17 (Selasa) — Butir #16 selesai, draf GT baru (#17)

### Yang dikerjakan
| No | Pekerjaan | Hasil | Lokasi |
|---|---|---|---|
| 1 | Keva menjalankan `cek_material_lubang.py` di editor | 40 objek, CSV lengkap | `alat_carla/cek_material_lubang.csv` |
| 2 | Claude mencocokkan CSV dengan GT Dika | 19/19 GT benar (High, posisi ≤ 0,4 mm, ukuran cocok) | PERBEDAAN_PROPOSAL.md, pembaruan 17 Nov |
| 3 | Claude membangun draf GT dari CSV | 32 High + 8 Low (retakan) | `alat_carla/pothole_gt_editor.json` |

### Koreksi atas entri 16 Nov
- Dugaan "hole_low* memakai material Low, jadi GT keliru" **salah** untuk lubang di area GT. Pembaruan 12 Nov di PERBEDAAN_PROPOSAL.md sebenarnya sudah menunjukkannya, tapi belum Claude baca saat itu.

### Belum
- Menentukan angka `severity` untuk Low di GT baru (konvensi GT Dika: High = 0,9; `carla_env.py`: urutan lain, lihat T3).
- Tanya Dika: apakah segmen x −7 s.d. +130 dipakai untuk training atau evaluasi.
- Hitung ulang T5/T6 dengan GT baru (#18). Tandai #16 selesai di `TODO_TA.csv`.

## 2026-11-17 (Selasa) sore — instruksi TODO #17–#20 (Claude)

### Yang dikerjakan
| No | Pekerjaan | Hasil | Lokasi |
|---|---|---|---|
| 1 | Instruksi langkah demi langkah #17–#20 | Ditulis | `INSTRUKSI_17-20.md` |
| 2 | Skrip pencocokan hasil ukur paket vs GT editor, menulis GT v2 lengkap (40) + segmen Dika (19) | Dites dengan `geometri_terukur.json` lama (18 objek): pencocokan posisi berjalan; hasil wajar BELUM SELESAI karena data lama tidak memuat `med_samping` | `alat_carla/cocokkan_gt.py` |
| 3 | Skrip baseline mobil lurus GT v2 + sapuan offset lateral | Dites dengan GT editor segmen Dika: lajur spawn 9/19 (47,4%), lajur kiri 10/19 (52,6%), offset ±0,5 m tetap 47,4% | `02_pelabel_roda/baseline_lurus_v2.py` |

### Keputusan dan asumsi (perlu Keva setujui)
- Severity angka Low = 0,3 (default `--sev_low`). Low tidak dihitung pelabel roda (hanya Medium/High).
- Baseline Gate 1 memakai segmen Dika saja (x −299,5 s.d. −27, 19 lubang).
- Offset awal acak runner: lateral ±0,5 m, longitudinal ±2 m, seed = nomor episode.
- `time.sleep` hanya boleh dihapus jika `synchronous_mode = True`; perlu cek frame kamera = frame dunia.

### Belum (dikerjakan Keva)
- Menjalankan #17–#20 di laptop sesuai `INSTRUKSI_17-20.md`.

## 2026-11-17 (Selasa) 18.10 — #17 selesai, #18 selesai

- #17 (Keva menjalankan, Claude memeriksa): `geometri_terukur_v2.json` dari CARLA paket = 40 objek. `cocokkan_gt.py`: **40/40 cocok**, jarak maks 0,6 mm, ukuran sama, tidak ada objek lebih/kurang. GT v2: `alat_carla/pothole_gt_v2_lengkap.json` (40: 32 High + 8 Low, severity Low = 0,3) dan `pothole_gt_v2_segmen_dika.json` (19 High). Sudah di-commit Keva (`9ef848b`).
- #18 (dijalankan Claude di laptop): `02_pelabel_roda/hasil_gt_v2/baseline_lurus_v2.json`. Mobil lurus lajur spawn y 250,5: **9/19 = 47,4%** (pelabel roda dan logika Dika sama). Lajur kiri y 247,2: 10/19 = 52,6%. Offset acak ±0,5 m: tetap 47,4%. Sama untuk cerah, hujan, malam. Angka lama T5 terkonfirmasi dengan GT terukur + geometri terukur.
- Dampak: run malam lab 7/19 (36,8%) tetap di bawah mobil lurus (E4), masih 1 episode → tunggu 30 episode (#21).
- Belum: commit hasil #18; lanjut #19.

## 2026-11-17 (Selasa) 18.30 — #19 runner diedit (Claude), belum diuji di CARLA

Lokasi: `10_runner/DQN_Akselerasi vertikal/` (salinan; asli di-commit `9ae5bd2`, lihat `git diff`). Semua edit ditandai `# [#19]`.
- Dicek dulu: `carla_env.py` memakai `synchronous_mode = True`, `fixed_delta_seconds = 0.05` → `sleep` aman diganti.
- `carla_env.py`: host `127.0.0.1`; `time.sleep` di `reset()` dan `step()` diganti `_tunggu_kamera(frame)` (tunggu sampai `image.frame` = frame tick, batas 2 s, hitung `kamera_telat`). Alasan: tanpa sleep, YOLO bisa membaca gambar langkah sebelumnya. Offset spawn acak `random.Random(seed)`; seed None = perilaku asli Dika.
- `cleanTest.py`: argumen `--cuaca --episodes --seed_awal --offset_x 2.0 --offset_y 0.5 --tampil --video`. Keluaran ke `log_runner/<waktu>_<cuaca>/`: `posisi_epXX_seedN.csv` (step, t_sim, frame_dunia, frame_kamera, x, y, yaw, v_kmh, aksi, deteksi, hits, avoids), `ringkasan_episode.csv` (detik, faktor real-time, kamera_telat), `sensor_log_all_episodes.csv` (format Dika). Video default mati (D: pernah penuh).
- Tidak diubah: reward/logika hit-avoid Dika, `pothole_gt.json` lama (posisinya identik dengan GT v2), model, YOLO.
- Belum: uji 1 episode (Keva).

## 2026-11-17 (Selasa) 18.45 — uji 1 episode runner #19 (Keva menjalankan, Claude menganalisis)

- Run `log_runner/20261117_183510_ClearNoon/`: 2.637 langkah, 125,7 s, faktor real-time 1,05, kamera telat 0. Offset seed 0: x +1,378, y +0,258.
- Mekanik runner **lulus**: frame_kamera = frame_dunia di 2.637/2.637 baris, frame naik tepat 1 per langkah, x −298,1 → −27,0.
- **Episode TIDAK VALID sebagai baseline:** `Yolo/best_pure.pt` tidak ada di salinan (`YOLO model error`, kode Dika hanya mencetak peringatan lalu lanjut). Deteksi = 0 di semua langkah → agen buta (STRAIGHT 96%). y melayang ke 248,07 (zona antar-lajur).
- Temuan sampingan (agen buta, 1 episode): logika Dika 12 HIT / 7 AVOID, pelabel roda **17 kena / 2 terhindar**. Selisih 5 lubang = bug ambang lateral (T6) pada lintasan nyata.
- Perbaikan Claude: `carla_env.py` kini `raise RuntimeError` jika YOLO tidak termuat ([#19]).
- Belum: salin `best_pure.pt` (SHA-256 7b6b44f3…, BUKAN versi Agen DRL 3bb64fb3…) ke `10_runner/.../Yolo/`, ulangi 1 episode. Hapus folder kosong `log_runner/20261117_183234_*` dan `_183420_*` (hanya berisi `video/` kosong).

## 2026-11-17 (Selasa) 18.50 — #19 SELESAI: uji ulang dengan YOLO (Keva menjalankan, Claude menganalisis)

- Run `log_runner/20261117_184625_ClearNoon/`, seed 0: YOLO termuat di CUDA. 2.910 langkah, 170,4 s, faktor real-time 0,85 (dengan jendela cv2), kamera telat 0.
- Mekanik: frame_kamera = frame_dunia 2.910/2.910, x −298,1 → −27,0, y 247,4–251,3. Deteksi aktif di 92% langkah; aksi STRAIGHT 76%, LEFT 12%, RIGHT 11%.
- Hasil: **18/19 terhindar (94,7%)**. Logika Dika dan pelabel roda sepakat: satu-satunya kontak ph_0010 (ban kanan depan + belakang). Dika melaporkan 100% cerah. Baru 1 episode.
- YOLO menambah ±45 s/episode dibanding run buta (125,7 s).
- Berikutnya #20: 5 episode `--tampil 0`.

## 2026-11-17 (Selasa) 19.15 — #20 SELESAI: waktu per episode dan keputusan laptop (Keva menjalankan, Claude menganalisis)

- Run `log_runner/20261117_185215_ClearNoon/`, 5 episode, seed 0–4, `--tampil 0`.
- **t = 137,3 s/episode rata-rata** (135,4–138,8), faktor real-time 1,06, kamera telat 0 di semua episode. Jendela cv2 menambah ±33 s (170,4 s di run sebelumnya).
- **Keputusan: laptop.** Gate 1 (90 ep) ≈ 3,4 jam = 1 malam. Fase 3 (±3.600 ep) ≈ 137 jam ≈ 14 malam × 10 jam. Masuk baris "≤ 150 s" di tabel INSTRUKSI. Cloud tidak dibutuhkan; PC lab sebagai cadangan.
- VRAM dan suhu GPU **tidak tercatat**. Rekam otomatis saat run Gate 1 dengan `nvidia-smi ... -l 10` (lihat bawah).
- Hasil lubang: kelima episode 18/19, dan **selalu ph_0010 yang kena** (pelabel roda dan logika Dika sepakat). Ini sistematis, bukan acak. Dika melaporkan 19/19 cerah. Dugaan (belum dicek): agen belok kanan menghindari ph_0009 (x −160,7, lajur kiri) lalu tidak sempat kembali sebelum ph_0010 (x −146,1, lajur kanan, 14,6 m kemudian).
- Episode 4: berhenti di x −32,07 karena **tabrakan** (reward −300, done) setelah semua lubang dilewati, sehingga bonus finis +800 hilang (total 980 vs ±2.085). Metrik lubang tidak terpengaruh. Objek yang ditabrak belum diketahui; `collision_history` tidak mencatat `other_actor`.
- Nondeterminisme terkonfirmasi lagi: seed 0 memberi 2.910 langkah (run 18.46) vs 2.897 langkah (run ini).
- Belum: catat `other_actor` tabrakan di runner; cek video/lintasan ph_0009–ph_0010; lanjut #21 (30 ep × 3 kondisi).

## 2026-11-18 (Rabu) 18.10 — persiapan #21 (Claude)

- `INSTRUKSI_21.md` ditulis.
- `10_runner/.../jalankan_baseline.bat`: ClearNoon → SoftRainNoon → ClearNight, 30 ep, seed 0–29, `--tampil 0`; mode lanjut setelah crash.
- `10_runner/.../analisis_baseline.py`: penghindaran per episode (pelabel roda + logika Dika, GT v2 segmen Dika), rata-rata, CI 95% bootstrap, lubang tersering kena, tabrakan, finis. Dites pada run 5 ep 17 Nov: 94,7% (keduanya), ph_0010 5/5, 1 tabrakan.
- Runner: callback tabrakan kini mencatat `other_actor.type_id` + x ke kolom `tabrakan` di `ringkasan_episode.csv` ([#21]).
- Asumsi: hujan = `SoftRainNoon` (dari `cleanTest copy.py`; laporan Dika tidak menyebut preset) → tanya Dika. Malam tanpa lampu kendaraan (kode Dika tidak menyalakan lampu).
- Belum: Keva menjalankan run (±3,5–4,5 jam).

## 2026-11-18 (Rabu) 22.10 — #21 run malam pertama gagal start (Claude)

- ClearNoon 30/30 dan SoftRainNoon 30/30 selesai (`log_runner/20261118_180956_ClearNoon`, `_193811_SoftRainNoon`).
- ClearNight gagal sebelum episode 1: `apply_settings` time-out 15 s tepat setelah `load_world` (server masih sibuk setelah run hujan). Sama dengan percobaan pertama 17 Nov. Tidak ada data malam yang terekam (folder `_204629_ClearNight` kosong, aman dihapus/dipindah).
- Perbaikan: timeout 60 s saat load_world/apply_settings + coba ulang 3× ([#21] di `carla_env.py`).
- Catatan kosmetik: waktu di baris `=====` bat sama semua karena `%time%` di dalam blok `for` diekspansi sekali.
- Belum: jalankan `jalankan_baseline.bat ClearNight 0 30`.

## 2026-11-19 (Kamis) 00.30 — #21 SELESAI: baseline π_Dika 30 ep × 3 kondisi (Keva menjalankan, Claude menganalisis)

Run: `10_runner/.../log_runner/20261118_180956_ClearNoon`, `_193811_SoftRainNoon`, `_223851_ClearNight`; ringkasan `hasil_baseline.json`. Seed 0–29, offset ±2 m / ±0,5 m, GT v2 segmen Dika.

| Kondisi | Pelabel roda (CI95) | Logika Dika (CI95) | Laporan Dika | Mobil lurus | Deteksi (frac langkah) |
|---|---|---|---|---|---|
| Cerah ClearNoon | 94,6% [94,2–94,7] | 94,7% [94,7–94,7] | 100% | 47,4% | 0,92 |
| Hujan SoftRainNoon | 92,6% [91,6–93,7] | 94,7% [94,7–94,7] | 84,2% | 47,4% | 0,90 |
| Malam ClearNight | 53,5% [50,5–56,3] | 77,9% [75,1–80,5] | 47,4% | 47,4% | 0,27 |

- **Gate 1 (kriteria E3) tidak terpenuhi di ketiga kondisi**: CI 95% tidak mencakup angka Dika. Arahnya berbeda: cerah lebih rendah, hujan dan malam lebih tinggi (menurut logika Dika).
- Cerah: ph_0010 kena 30/30 (sistematis), ph_0002 1/30.
- Hujan: hasil logika Dika identik dengan cerah (18/19 di 30/30 ep) → `SoftRainNoon` kemungkinan lebih ringan dari hujan Dika. Pelabel roda menangkap kontak tambahan (ph_0011 5×, ph_0012 3×, ph_0018 3×) yang tidak dicatat logika Dika.
- Malam: **logika Dika melebih-lebihkan penghindaran 24 poin** (77,9 vs 53,5%). Dengan pelabel roda, agen hanya ±6 poin di atas mobil lurus. ph_0002, ph_0010, ph_0017 kena 30/30.
- **Kejanggalan malam:** logika Dika di sini 77,9% (mode 15/19), padahal laporan Dika 9/19 dan run lab 10 Nov 7/19 (kode & model sama). Deteksi 27% langkah vs ±16% frame di rekaman Dika. Dugaan: render malam build paket laptop ≠ PC lab/editor (pencahayaan/exposure), atau efek offset. Belum diuji.
- Waktu: cerah 175,6 s/ep (lebih lambat; penyebab belum diketahui, mungkin laptop dipakai saat itu), hujan 135,8, malam 134,0. Tabrakan 0 di 90 ep. Kamera telat 0.
- GPU (`log_runner/gpu_baseline.csv`, 1.985 sampel): **VRAM median 7.784 MiB, maks 7.884 MiB (≈ penuh dari 8 GB)**; suhu median 60 °C, maks 74,9 °C (malam); utilisasi median 56%.
- Dampak: VRAM hampir habis → menambah monitor/ensemble di proses yang sama berisiko OOM; perlu dicek sebelum Fase 2.
- Belum: (1) diagnosis malam: 3 ep `--offset_x 0 --offset_y 0` + 1 ep `--video 1` untuk dibandingkan kecerahannya dengan `malam.mp4` Dika; (2) tanya Dika preset hujan; (3) keputusan dosbing: baseline baru vs reproduksi (butir #1); (4) #22 formal.

## 2026-11-19 (Kamis) 00.45 — diagnosis malam #1: offset bukan penyebab (Keva menjalankan, Claude menganalisis)

- Run `log_runner/20261119_003030_ClearNight`, 3 ep, offset 0, seed 0–2.
- Logika Dika: 15, 15, 18 terhindar (rata-rata 84%). Pelabel roda: 11, 11, 13 (61%). Deteksi 25–26% langkah. Pembanding run dengan offset (seed 0–2): logika Dika 16, 12, 15; roda 12, 10, 9.
- **Kesimpulan: offset acak bukan penyebab** angka malam jauh di atas laporan Dika (9/19) dan run lab (7/19). ph_0002, ph_0010, ph_0017 tetap kena.
- Kandidat penyebab tersisa: (a) pengganti `sleep` (`_tunggu_kamera`) membuat YOLO selalu melihat frame terkini; di kode asli, frame bisa basi kalau render malam > 50 ms; (b) render malam build paket laptop ≠ PC lab.
- Ditambahkan flag `--sleep_asli 1` ([#21b]): kembali ke `time.sleep(0.05)` seperti Dika; `frame_kamera` tetap dicatat sehingga keterlambatan frame terlihat. Folder run diberi akhiran `_sleepasli`.
- Belum: jalankan 3 ep `--sleep_asli 1`. Jika hasil turun ke ±7–9/19 → penyebab (a), dan baseline Dika dipengaruhi frame basi (temuan). Jika tetap ±15/19 → penyebab (b).

## 2026-11-19 (Kamis) 01.15 — diagnosis malam #2: sleep bukan penyebab; persepsi di laptop jauh lebih kuat (Claude)

- Run `log_runner/20261119_004205_ClearNight_sleepasli`, 3 ep, offset 0, `--sleep_asli 1`: logika Dika 16, 15, 18; roda 12, 9, 12; deteksi 24–28%. **Lag frame kamera = 0 di semua langkah**: di laptop, gambar selalu tiba dalam 50 ms, jadi pengganti sleep tidak mengubah apa pun. Kandidat (a) gugur. 229–232 s/ep (sleep membuat 70% lebih lambat).
- Metrik T20 (deteksi agen saat pusat lubang 3–15 m di depan) dihitung dari log laptop:

| Kondisi | Laptop (ini) | Rekaman Dika (T20) |
|---|---|---|
| Cerah | 96,8% | 59% |
| Hujan | 96,3% | 50% |
| Malam | 30,7% (sleep asli 30,0%) | 6% |
| Deteksi saat tidak ada lubang 3–15 m: cerah / hujan / malam | 70 / 62 / 9,5% | 10 / 32 / ? |

- Kesimpulan sementara: YOLO yang sama mendeteksi jauh lebih sering di render laptop pada **semua** kondisi → penyebab utama kemungkinan **lingkungan render** (build paket Shipping laptop vs PC lab/editor; tingkat kualitas grafis, LOD/streaming tekstur decal), bukan kode runner. Catatan: definisi "tidak ada lubang" di sini = tidak ada di 3–15 m; lubang > 15 m bisa ikut terdeteksi.
- Usulan: satu uji murah lagi (CARLA `-quality-level=Low`, 3 ep malam), lalu berhenti dan bawa ke dosbing sebagai baseline baru di lingkungan laptop.

## 2026-11-19 (Kamis) 11.30 — koreksi: semua run #20–#21 memakai CARLA `-quality-level=Low`

- Keva: `CarlaUE4.exe` selama ini dijalankan dengan `-quality-level=Low` untuk ketiga kondisi (dan diagnosis malam). Usulan uji "Low" di entri 01.15 tidak berlaku; yang perlu diuji justru **Epic** (default; kemungkinan yang dipakai Dika lewat editor/`make launch`, belum dikonfirmasi).
- Dampak: deteksi YOLO yang jauh lebih tinggi dari rekaman Dika (T20) kemungkinan besar terkait kualitas render Low. Baseline #21 = π_Dika **di lingkungan laptop, kualitas Low**, bukan lingkungan Dika.
- Catatan VRAM: 7,8 GB kemungkinan sebagian besar alokasi rakus TensorFlow (tidak ada `set_memory_growth` di kode), bukan kebutuhan sebenarnya.
- Belum: uji 3 ep malam di Epic (deteksi, waktu, VRAM) → putuskan kualitas standar TA; tanya Dika kualitas & preset hujan.

## 2026-11-19 (Kamis) 13.25 — diagnosis malam #3: kualitas render adalah penyebabnya (Keva menjalankan, Claude menganalisis)

- Run `log_runner/20261119_131412_ClearNight`, CARLA **Epic** (default), 3 ep, offset 0, seed 0–2.
- **Logika Dika: 9, 7, 6** (rata-rata 38,6%) → cocok dengan laporan Dika 9/19 dan run lab 7/19. Di Low dengan seed sama: 15, 15, 18.
- **Pelabel roda: 3, 2, 2 (12,3%)** → jauh di bawah mobil lurus 47,4%. Logika Dika melebih-lebihkan ±26 poin.
- Deteksi: 20–21% langkah; saat lubang 3–15 m 24–25% (Low: 31%; rekaman Dika: 6%). Waktu 131–134 s/ep (sama dengan Low).
- Kesimpulan: **kualitas render (`-quality-level`) adalah penyebab utama** perbedaan dengan angka Dika. Run #21 sebelumnya (Low) bukan lingkungan Dika.
- Usulan keputusan: standar TA = **Epic** (cocok dengan Dika, waktu sama). Data Low disimpan sebagai temuan pergeseran render (kandidat skenario OOD).
- Perapian (Claude): run Low 17–19 Nov dipindah ke `log_runner/_kualitas_low/` (termasuk `gpu_baseline.csv`). Folder Epic diagnosis gagal dipindah (Permission denied, kemungkinan masih terkunci Windows) → Keva pindahkan manual ke `log_runner/_diagnosis/`.
- `cleanTest.py`: argumen `--label` (nama folder diberi akhiran kualitas). `jalankan_baseline.bat`: `--label Epic` + catatan WAJIB buka CARLA tanpa `-quality-level`.
- Belum: ulangi #21 di Epic (90 ep, ±3,5 jam) + perekam GPU; uji VRAM Epic.

## 2026-11-19 (Kamis) 14.25 — persiapan ulang #21 di Epic (Claude)
- `10_runner/.../jalankan_baseline.py`: pengganti `.bat`, lanjut-otomatis dari seed yang belum selesai setelah time-out/crash (maks 3×/kondisi, jeda 60 s), jeda 30 s antar kondisi, log ke `log_runner/jalankan_baseline.log`, label folder `_Epic`.
- Anti time-out di `carla_env.py` (60 s + 3× coba ulang `apply_settings`, dipasang 18 Nov 22.10) tetap berlaku.
- `INSTRUKSI_21_EPIC.md` ditulis.
- Belum: Keva menjalankan run Epic.

## 2026-11-19 (Kamis) 18.00 — #21 dan #22 SELESAI (Epic)
- Run Epic 14.28–17.54 tanpa time-out (3× SELESAI 30/30 di `jalankan_baseline.log`).
- Hasil + kesimpulan: `HASIL_BASELINE.md`, `10_runner/.../hasil_baseline_epic.json`. Cerah tereproduksi (logika Dika 99,5% [98,8–100]); hujan 100% (preset ≠ Dika?); malam logika Dika 36,3%, pelabel roda 17,0% vs mobil lurus 47,4%.
- Tabrakan cerah seed 2 & 8: `static.wall` x ≈ −37.
- `analisis_baseline.py`: perbaikan pencarian angka Dika untuk folder berlabel `_Epic`.
- Belum: #23 Gate 1 (butuh keputusan dosbing atas kriteria); tanya Dika preset hujan; tandai #21–#22 di `TODO_TA.csv`.

## 2026-11-21 (Sabtu) 20.10 — pencocokan preset hujan + temuan Scalability High (Claude)
- **Temuan:** ketiga video layar Dika (`TA_Dika/Video Test/final cerah.mp4`, `hujan.mp4`, `malam.mp4`) menunjukkan Unreal Editor (Play) dengan label viewport **`Scalability: High`**. Lingkungan Dika = Editor + High, bukan paket + Epic. Baseline #21–#22 (paket, Epic) perlu dibaca dengan catatan ini; malam di Epic sudah mendekati angka Dika, tetapi selisih High vs Epic belum diukur.
- Tangkapan dari video Dika disimpan di `11_cuaca/_pratinjau_dika/` (frame layar + potongan label Scalability).
- Dibuat `11_cuaca/cocokkan_cuaca.py` (referensi / ambil / bandingkan) dan `11_cuaca/INSTRUKSI_CUACA.md`.
- `referensi` sudah dijalankan untuk cerah, hujan, dan malam (60 frame/video, area x ≥ 300, kanal R/B dibalik) → `11_cuaca/referensi/`. Median hujan Dika vs cerah Dika: saturasi 12,7 vs 36,3; gradien pita jauh 16,8 vs 43,3 (kabut tebal); luminansi jalan 135,5 vs 174,8.
- `bandingkan` diuji dengan data tiruan (frame Dika sendiri): alur jalan. `ambil` **belum diuji** (butuh CARLA).
- Dugaan sebelum render (dicatat supaya tidak ditafsirkan setelah melihat hasil): hujan Dika ≈ HardRainNoon (langit tertutup penuh, kabut tebal), bukan SoftRainNoon.
- Belum (Keva): render EditorHigh + PaketEpic, bandingkan, kirim hasil; tanya Dika preset hujan dan apakah memang Scalability High.

## 2026-11-21 (Sabtu) 20.40 — hasil pencocokan cuaca: hujan Dika = HardRainNoon (Keva menjalankan, Claude menganalisis)
- Render `ambil` EditorHigh dan PaketEpic berhasil (7 preset × 8 titik). Hasil: `11_cuaca/hasil_EditorHigh/`, `11_cuaca/hasil_PaketEpic/`.
- **Hujan:** HardRainNoon juara di kedua render (skor 0,35 High / 0,42 Epic). Runner-up jauh: 3,69–3,70 (selisih ±9×). Montase cocok: kabut tebal, langit abu rata, jalan basah. SoftRainNoon (yang dipakai #21) skor 4,75 dan secara visual hampir sama dengan cerah → menjelaskan kenapa baseline hujan #21 = cerah.
- **Uji kewarasan cerah: lolos sebagian.** WetNoon (0,17–0,19) dan ClearNoon (0,22–0,30) seri di dalam derau (< 0,3 IQR); semua preset berawan/hujan > 2,5. Artinya metrik membedakan atmosfer (awan, kabut) dengan sangat baik, tetapi tidak bisa membedakan preset yang hanya berbeda kebasahan jalan pada langit cerah. Untuk keputusan hujan ini tidak masalah, karena tidak ada preset lain yang mendekati HardRainNoon.
- **High vs Epic:** median semua metrik berbeda < 1 unit untuk setiap preset → untuk tampilan cuaca siang, Scalability High (Dika) ≈ Epic (paket). Belum diuji: malam, dan perilaku YOLO (bukan hanya statistik citra).
- **Implikasi:** kode Dika yang ada (`SoftRainNoon`) ≠ kode yang dipakai saat laporan (HardRainNoon menurut video). Konsisten dengan T13/T19. Dugaan sebelum render (HardRainNoon) terkonfirmasi.
- Belum (Keva): baseline hujan ulang 30 ep `python jalankan_baseline.py --kondisi HardRainNoon` (paket, Epic); konfirmasi ke Dika; perbarui HASIL_BASELINE.md setelah run.

## 2026-11-21 (Sabtu) 21.45 — baseline hujan HardRainNoon 30 ep + status Gate 1 (Keva menjalankan, Claude menganalisis)
- Run `10_runner/.../log_runner/20261121_204019_HardRainNoon_Epic`, paket Epic, seed 0–29, SELESAI 30/30 tanpa time-out.
- **Akhir episode: finis 10, keluar jalan 11 (y < 245,55, sisi kiri), tabrak tembok 9.** Bandingkan cerah 28 finis / 2 tabrak, SoftRain 30 finis, malam 30 finis. Di hujan lebat agen tidak stabil dan mengakhiri 2/3 episode sebelum garis akhir.
- **Bug metrik ditemukan (Claude):** `analisis_baseline.py` menghitung lubang yang tidak tercapai sebagai "terhindar". Tidak berpengaruh untuk run lama (hampir semua finis), tetapi membesarkan hasil hujan. Ditambahkan dua versi ([#21c]); default `--out` kini `hasil_baseline_<kondisi>.json` agar tidak menimpa hasil lama.

| HardRainNoon, 30 ep | % | CI 95% |
|---|---|---|
| Pelabel roda, cara lama (tak tercapai = terhindar) | 71,9 | 66,7–77,2 |
| Pelabel roda, hanya lubang yang dilewati | 66,7 | 60,8–72,3 |
| Pelabel roda, tak tercapai = gagal | 54,6 | 47,4–61,6 |
| Logika Dika (cara lama) | 71,8 | 63,5–79,1 |
| Laporan Dika | 84,2 | 1 run |

- Logika Dika pada 10 episode yang finis (penghitung avoids di `ringkasan_episode.csv`): 168/190 = **84,0%**, sama dengan laporan Dika. Run hujan Dika juga finis (2.911 langkah). Tafsiran: angka 84,2% Dika konsisten dengan satu run yang kebetulan finis (peluang ±1/3), bukan perilaku rata-rata. Ini pengondisian setelah melihat data → dipakai sebagai penjelasan, bukan klaim reproduksi.
- Status Gate 1 dengan kriteria E3 (CI mencakup angka Dika): cerah ya; hujan tidak (84,2 di luar [63,5–79,1]); malam tidak. Dengan kriteria revisi (baseline ditetapkan + setiap selisih punya penyebab teridentifikasi): ketiganya terjelaskan → usulkan ke dosbing.
- Kecelakaan kecil (Claude): `analisis_baseline.py` versi lama menimpa `hasil_baseline.json`; sudah dipulihkan dari commit 0b69b27, hasil hujan disimpan di `hasil_baseline_hardrain_epic.json`. `git status` dari Claude meninggalkan `.git/index.lock` → dipindah ke `.git/stale-index-lock-claude-2111` (aman dihapus).
- Belum: memo Gate 1 untuk dosbing; perbarui `HASIL_BASELINE.md` (hujan = HardRainNoon); putuskan metrik utama; commit.

- 21.50 (Claude): `10_runner/DQN_Akselerasi vertikal/INSTRUKSI_ANALISIS_BASELINE.md` ditulis (cara pakai, arti tiap baris output, pemeriksaan wajib, error umum).
- 21.55 (Claude): output Keva identik dengan analisis Claude (4 kondisi lolos pemeriksaan: 30 ep, tanpa seed ganda). `analisis_baseline.py`: SoftRainNoon tidak lagi diberi pembanding "laporan Dika 84.2%" (hujan Dika = HardRainNoon).
