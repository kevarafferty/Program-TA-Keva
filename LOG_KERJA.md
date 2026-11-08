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
