# Keva_TA_Kerja

Folder kerja TA Keva (pemantau keselamatan ganda untuk perencana DRL Dika).
Semua kode di sini **baru**; kode dan data asli Dika/Retta tidak diubah.

## Baca dulu

1. `TEMUAN.md` — 24 temuan dari kode dan data Dika/Retta, beserta dampaknya ke proposal
2. `LOG_KERJA.md` — apa yang dikerjakan, kapan, dengan asumsi apa
3. `PERBEDAAN_PROPOSAL.md` — 19 perbedaan PDF proposal dengan temuan, dalam tabel (8 Nov)
4. `06_pesan/` — pesan ke Dika dan Retta yang perlu dikirim **hari ini**

## Isi folder

| Folder | Isi | Status |
|---|---|---|
| `01_inventaris` | Daftar aset yang ada/belum ada, hash SHA-256 | Selesai |
| `02_pelabel_roda` | Label kontak roda–lubang, energi pelanggaran E_V, pembanding logika Dika | Selesai (geometri masih estimasi) |
| `03_cek_dqn` | Uji muat `model_best.h5` dan perilaku agen terhadap jarak lubang | Selesai |
| `04_monitor_persepsi` | Hook logit YOLO, prototipe monitor persepsi offline | Selesai sebagai studi pendahuluan |
| `05_proyeksi_kamera` | Proyeksi 3D ↔ 2D untuk kamera Dika dan Retta | Selesai (belum dicek visual di CARLA) |
| `06_pesan` | Draf pesan ke Dika dan Retta (versi 2, lebih pendek) | Siap kirim |
| `07_rekaman_dika` | Monitor persepsi pada 8.505 frame CARLA asli dari rekaman uji Dika | Selesai (open-loop, ada batasan kompresi) |
| `08_kunjungan_lab` | Ceklis + script pengumpul info untuk PC lab `Ryzen_PC` (9 Nov) | Siap dipakai, script belum diuji |
| `alat_carla` | Skrip ukur geometri untuk CARLA + panduan environment (`SETUP_ENV.md`) | Belum diuji |

Setiap folder punya `HASIL.md` yang menjelaskan berkas, cara kerja, angka, dan batasannya.

## Menjalankan

```
pip install -r requirements.txt
```
Lalu ikuti perintah di bagian akhir `LOG_KERJA.md`.
