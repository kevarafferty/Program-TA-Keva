# Program TA Keva — pemantau keselamatan ganda untuk agen DRL penghindar lubang

Folder kerja Tugas Akhir Muhammad Keva Rafferty (13323035, Teknik Fisika ITB).
Diperbarui terakhir: **22 Nov 2026**.

## Ringkasan dalam 1 menit

**Apa yang diteliti.** Kak Dika (TA 2026) melatih agen *Deep Reinforcement Learning* (DQN) yang mengemudikan mobil
Microlino di simulator CARLA dan menghindari lubang jalan yang dideteksi kamera + YOLO. Agen ini bekerja baik di
siang cerah, tetapi turun drastis saat hujan dan malam. Masalahnya: agen **tidak tahu kapan dirinya sedang gagal**.

TA ini membangun **pemantau keselamatan ganda** (*dual safety monitor*) di atas agen Dika:
1. **Monitor persepsi** — apakah YOLO sedang melihat kondisi di luar data latihnya (*out-of-distribution*, OOD)?
   Memakai skor energi (*energy score*) dari logit YOLO dan jarak fitur (Mahalanobis).
2. **Monitor keputusan** — apakah agen DQN ragu dengan keputusannya (*decision uncertainty*)?
   Memakai energi-Q dan ketidaksepakatan *ensemble*.

Kalau salah satu monitor menyala, arbiter mengalihkan mobil ke manuver aman (*minimal risk maneuver*, MRM).
Semua dikerjakan **di simulasi** (CARLA 0.9.15, peta `train_fix` milik Dika). Kode dan data asli Dika/Retta tidak diubah;
semua kode di folder ini baru atau salinan yang diberi tanda.

**Posisi sekarang.** Fase 1 (lingkungan + baseline) hampir selesai:
- Baseline agen Dika sudah direproduksi di laptop (30 episode × 4 kondisi) → `HASIL_BASELINE.md`.
- Gate 1 menunggu keputusan dosbing atas kriteria revisi (memo sudah ditulis).
- Generator tata letak lubang dan runner skenario off-nominal (#24–#25) sudah jalan di CARLA; matriks uji sedang diulang
  setelah perbaikan bug toggle lubang (lihat entri terakhir `LOG_KERJA.md`).

## Temuan terpenting sejauh ini

| # | Temuan | Bukti |
|---|---|---|
| 1 | **Malam: agen lebih buruk daripada mobil yang jalan lurus saja** (17,0% vs 47,4% lubang terhindar). Metrik Dika menutupi selisih ini (36,3%). Ini contoh *silent failure* yang menjadi motivasi TA | `HASIL_BASELINE.md` |
| 2 | **Hujan Dika ternyata `HardRainNoon`, bukan `SoftRainNoon`** seperti di kodenya. Di hujan lebat 2/3 episode gagal sebelum finis | `11_cuaca/`, `HASIL_BASELINE.md` |
| 3 | **Kualitas render menentukan hasil.** CARLA `-quality-level=Low` memberi malam 77,9%, Epic 36,3% (cocok dengan Dika). Standar TA = **Epic** | `LOG_KERJA.md` 19 Nov |
| 4 | Logika HIT/AVOID Dika melebih-lebihkan penghindaran di semua kondisi (+5 / +17 / +19 poin). Metrik utama TA = **pelabel kontak roda** + tingkat kegagalan episode | `02_pelabel_roda/`, `HASIL_BASELINE.md` |
| 5 | Lubang di peta Dika adalah gambar datar (*decal/plane*), jadi LiDAR tidak bisa melihatnya; YOLO memberi kelas Low pada hampir semua lubang CARLA | `TEMUAN.md` T4, T17 |
| 6 | Simulasi tidak deterministik meski seed sama → setiap evaluasi ≥ 30 episode + CI 95% | `LOG_KERJA.md` 17 Nov |

## Urutan membaca (untuk orang baru)

1. **README ini** — gambaran besar dan peta folder.
2. **`HASIL_BASELINE.md`** — hasil utama Fase 1 dalam satu tabel.
3. **`TODO_TA.csv`** — rencana kerja lengkap 44 butir sampai sidang, dengan kolom status.
4. **`LOG_KERJA.md`** — catatan kronologis: apa yang dikerjakan, keputusan, asumsi, dan asal setiap angka. Entri terbaru di bawah.
5. Bila perlu konteks awal: `TEMUAN.md` (24 temuan dari kode Dika/Retta, 7 Nov) dan `PERBEDAAN_PROPOSAL.md`
   (perbedaan proposal Oktober dengan temuan, 8 Nov). Keduanya **arsip**: beberapa isinya sudah diperbarui oleh hasil sesudahnya.

## Peta folder

Nomor folder = urutan dikerjakan. Setiap folder punya `HASIL.md`, `README.md`, atau `BACA.md` yang menjelaskan isinya.

| Folder | Isi | Status |
|---|---|---|
| `01_inventaris/` | Daftar aset Dika/Retta yang ada/belum ada + hash SHA-256 | Selesai (7 Nov) |
| `02_pelabel_roda/` | **Pelabel kontak roda–lubang** (metrik utama TA), pembanding logika Dika, baseline mobil lurus GT v2 (47,4%) | Selesai |
| `03_cek_dqn/` | Uji muat `model_best.h5` Dika dan perilaku agen terhadap jarak lubang | Selesai |
| `04_monitor_persepsi/` | Hook logit YOLO + prototipe monitor persepsi offline (studi pendahuluan) | Selesai |
| `05_proyeksi_kamera/` | Proyeksi 3D ↔ 2D untuk kamera Dika dan Retta | Selesai |
| `07_rekaman_dika/` | Monitor persepsi pada 8.505 frame rekaman uji Dika (open-loop) | Selesai |
| `08_kunjungan_lab/` | Info build CARLA dan env Python dari PC lab `Ryzen_PC` (10 Nov) — rujukan versi | Arsip |
| `09_carla_laptop/` | Panduan *source build* CARLA 0.9.15 + UE4 di laptop Windows | Selesai, bisa dipakai ulang |
| `10_runner/DQN_Akselerasi vertikal/` | Salinan kode Dika + runner baseline (`cleanTest.py`, `jalankan_baseline.py`, `analisis_baseline.py`), log 30-episode | Selesai (#19–#22) |
| `11_cuaca/` | Pencocokan preset cuaca CARLA dengan video Dika | Selesai (21 Nov) |
| `12_lingkungan/` | **Generator tata letak lubang + runner skenario off-nominal + logger** fitur/logit/Q (#24–#25) | Sedang berjalan |
| `alat_carla/` | Skrip pengukuran di CARLA, *ground truth* lubang GT v2, env Python laptop (`env_laptop/`) | Dipakai |
| `asset_lab/`, `train_fix_migrate/` | Aset peta `train_fix` dari PC lab (besar, tidak perlu dibuka) | Aset |

`06_pesan/` (draf pesan ke Dika/Retta) dan berkas `INSTRUKSI_*.md` sekali pakai sudah dihapus 22 Nov; isinya tetap ada di riwayat git.

## Berkas penting yang sering dipakai

| Berkas | Fungsi |
|---|---|
| `alat_carla/pothole_gt_v2_segmen_dika.json` | GT 19 lubang di segmen uji Dika (dipakai semua metrik baseline) |
| `alat_carla/pothole_gt_v2_lengkap.json` | GT semua 40 objek lubang di peta (32 High + 8 Low) |
| `10_runner/.../INSTRUKSI_ANALISIS_BASELINE.md` | Cara menjalankan dan membaca `analisis_baseline.py` |
| `12_lingkungan/README.md` | Cara memakai generator + runner skenario, isi log, keputusan desain |
| `12_lingkungan/kalibrasi_lingkungan.json` | Kalibrasi throttle → kecepatan dan azimut matahari |

## Menyiapkan lingkungan

1. **CARLA:** source build 0.9.15 + UE4 fork (`09_carla_laptop/PANDUAN_BUILD.md`), lalu `make package`. Semua run memakai
   `CarlaUE4.exe` hasil package, dibuka **tanpa** `-quality-level` (= Epic).
2. **Python:** env conda `carla_env` (Python 3.8, `carla==0.9.15`, TensorFlow 2.10, Ultralytics 8.4.13) —
   ikuti `alat_carla/env_laptop/README.md`, cek dengan `python cek_env.py`.
3. Bobot YOLO `best_pure.pt` (SHA-256 `7b6b44f3…`) harus ada di `10_runner/DQN_Akselerasi vertikal/Yolo/`. Tanpa itu runner berhenti dengan error.
4. Skrip analisis offline di `02_`–`07_` (tanpa CARLA) cukup memakai `requirements.txt` di folder ini (Python baru, versi tidak dikunci).

## Tips menjalankan run panjang (semalaman)

- Colok charger, matikan sleep: `powercfg /change standby-timeout-ac 0` dan `powercfg /change hibernate-timeout-ac 0`.
- Pause Windows Update 1 hari; tutup aplikasi lain yang memakai GPU.
- Rekam GPU di terminal terpisah:
  `nvidia-smi --query-gpu=timestamp,memory.used,temperature.gpu,utilization.gpu --format=csv -l 10 > log_runner\gpu.csv`
- Runner (`jalankan_baseline.py`, `jalankan_skenario.py`, `jalankan_matriks.py`) melanjutkan otomatis dari seed yang belum
  selesai. Kalau berhenti: restart `CarlaUE4.exe`, jalankan perintah yang sama lagi.
- Rata-rata ±135–140 s/episode di laptop (GPU 8 GB VRAM). 90 episode ≈ 3,5 jam.

## Pertanyaan terbuka

| Untuk | Pertanyaan | Status |
|---|---|---|
| Dosbing | Gate 1 dengan kriteria revisi, metrik utama = pelabel roda, perlu/tidak uji malam di Editor High (memo: https://claude.ai/artifact/5Xb62EK5SJRjq6WvwJyFwj) | Menunggu |
| Kak Dika | Preset hujan yang dipakai saat laporan (dugaan `HardRainNoon`) dan apakah run dilakukan di Editor `Scalability: High` | Belum dikonfirmasi |
| Keva | Perlu/tidaknya backend spawn (aset lubang baru) untuk skenario C1 t2–3, D1 t2–3, B3 | Belum diputuskan |

## Konvensi kerja

- **`LOG_KERJA.md`**: satu entri per sesi — apa yang dikerjakan, oleh siapa (Keva menjalankan / Claude menganalisis),
  keputusan, asumsi, dan yang belum. Angka di laporan harus bisa dilacak ke entri log.
- **Tanda edit di kode Dika**: setiap baris yang diubah di salinan diberi komentar `# [#nomor_todo]`, misalnya `# [#19]`.
  Versi asli ada di commit `9ae5bd2` (`git diff 9ae5bd2 -- "10_runner"`).
- **Instruksi langkah-demi-langkah sekali pakai** tidak disimpan di folder ini; dibuat sebagai Claude Docs. Folder ini hanya
  berisi kode, data, hasil, dan dokumentasi yang tetap berlaku.
- Data run yang tidak valid dipindah ke subfolder berawalan `_` (misalnya `_kualitas_low/`, `_toggle_lama_tanpa_verifikasi/`)
  dan tidak dipakai untuk analisis.
- Istilah teknis memakai istilah asli dari paper (bahasa Inggris), tidak diterjemahkan.
