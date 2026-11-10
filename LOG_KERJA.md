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
