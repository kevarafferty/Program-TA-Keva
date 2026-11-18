# Instruksi TODO #21 — Baseline π_Dika: 30 episode × cerah / hujan / malam

**Selesai jika:** ada 3 folder run (ClearNoon, SoftRainNoon, ClearNight), masing-masing `ringkasan_episode.csv` berisi 30 baris dengan seed 0–29, dan output `analisis_baseline.py` sudah dikirim ke Claude.

**Waktu:** persiapan 20 menit, run ±3,5–4,5 jam tanpa ditunggu (jalankan malam), analisis 5 menit.

Sudah disiapkan Claude di `10_runner\DQN_Akselerasi vertikal\`:
- `jalankan_baseline.bat` — menjalankan 3 kondisi berurutan, 30 episode, seed 0–29 (seed sama untuk ketiga kondisi, jadi perbandingan antar kondisi berpasangan).
- `analisis_baseline.py` — rata-rata + CI 95% (bootstrap) pelabel roda dan logika Dika, lubang yang paling sering kena, jumlah tabrakan. Sudah dites pada run 5 episode kemarin.
- Runner kini mencatat **objek yang ditabrak** (kolom `tabrakan` di `ringkasan_episode.csv`).

---

## A. Persiapan (20 menit)

1. **Commit dulu** (folder `Program TA Keva`):
   ```
   git add -A
   git commit -m "#21 persiapan: batch baseline, analisis, log tabrakan"
   ```
2. **Laptop jangan tidur.** Colok charger, mode Performance. Di PowerShell:
   ```
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   ```
   Layar boleh mati; laptop jangan sleep.
3. **Tunda Windows Update** 1 hari (Settings → Windows Update → Pause). Restart otomatis di tengah malam = run hilang.
4. **Tutup aplikasi lain yang memakai GPU** (browser dengan video, game, OBS).
5. **Buka `CarlaUE4.exe`** hasil package. Tunggu Town10HD muncul.

## B. Jalankan (2 terminal)

6. **Terminal 1 (Anaconda Prompt), perekam GPU** — mengganti angka VRAM/suhu yang kemarin lupa dicatat:
   ```
   cd /d "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\10_runner\DQN_Akselerasi vertikal"
   nvidia-smi --query-gpu=timestamp,memory.used,temperature.gpu,utilization.gpu --format=csv -l 10 > log_runner\gpu_baseline.csv
   ```
   Biarkan terbuka sampai semua selesai, lalu tutup dengan Ctrl+C.
7. **Terminal 2 (Anaconda Prompt), runner:**
   ```
   conda activate carla_env
   cd /d "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\10_runner\DQN_Akselerasi vertikal"
   jalankan_baseline.bat
   ```
8. **Tonton 2 episode pertama (±5 menit).** Pastikan muncul `✅ YOLO loaded on CUDA` dan baris `EPISODE 1: ... kamera telat 0`. Kalau benar, tinggalkan.

## C. Kalau CARLA crash di tengah jalan

9. Buka folder run terakhir di `log_runner\`. Lihat seed terakhir di `ringkasan_episode.csv`, misalnya seed 16.
10. Tutup dan buka lagi `CarlaUE4.exe`, lalu lanjutkan dari seed berikutnya (contoh: hujan, mulai seed 17, sisa 13 episode):
    ```
    jalankan_baseline.bat SoftRainNoon 17 13
    ```
    Lalu jalankan kondisi yang belum tersentuh satu per satu, contoh: `jalankan_baseline.bat ClearNight 0 30`.
11. Episode yang terputus di tengah otomatis diabaikan oleh skrip analisis (tidak ada barisnya di `ringkasan_episode.csv`).

## D. Besok pagi: analisis (5 menit)

12. Tutup perekam GPU (Ctrl+C di terminal 1).
13. Jalankan (ganti tanggal sesuai folder):
    ```
    python analisis_baseline.py --runs "log_runner\20261118_*"
    ```
14. Cek: tiap kondisi **30 episode**, tidak ada `PERINGATAN: seed ganda`. Kalau ada seed ganda (run diulang), pindahkan folder run yang gagal ke `log_runner\_batal\` lalu ulangi langkah 13.
15. Kirim output terminal + `log_runner\gpu_baseline.csv` ke Claude.
16. Commit: `git add -A && git commit -m "#21 baseline pi_Dika 30 ep x 3 kondisi"`

---

## Asumsi yang dipakai (catat di LOG, tanyakan ke Dika)

| Kondisi | Preset | Dasar |
|---|---|---|
| Cerah | `ClearNoon` | Default `carla_env.py` Dika |
| Hujan | `SoftRainNoon` | Satu-satunya preset hujan di kode Dika (`cleanTest copy.py`). Laporan Dika hanya menulis "Hujan Siang", tanpa nama preset. **Tanyakan ke Dika.** |
| Malam | `ClearNight` | Dipakai di `cleanTest.py` Dika dan run lab 10 Nov |

- Malam **tanpa lampu kendaraan**, sama dengan kode Dika. Proposal A1 nanti memakai lampu menyala; itu skenario terpisah, bukan baseline.
- GT untuk metrik: `pothole_gt_v2_segmen_dika.json` (posisi identik dengan `pothole_gt.json` Dika). Reward agen tetap memakai GT Dika.

## Tulis dugaanmu SEBELUM run (2 menit, di LOG)

Supaya hasilnya tidak ditafsirkan setelah melihat angka. Dugaan Claude dari data yang ada:
- Cerah: sekitar 94,7% (ph_0010 selalu kena di 5/5 episode kemarin). Kalau bertahan, CI 95% tidak mencakup 100% laporan Dika.
- Hujan: di bawah cerah; deteksi palsu naik (T20).
- Malam: sekitar 37–47%, bisa di bawah mobil lurus (47,4%) seperti run lab 7/19.

**Kriteria Gate 1 (E3):** tereproduksi jika CI 95% rata-rata 30 episode mencakup angka Dika (100 / 84,2 / 47,4%). Kalau tidak tercakup, itu bukan kegagalan TA. Itu temuan, asal penyebabnya bisa ditunjukkan (misalnya ph_0010).
