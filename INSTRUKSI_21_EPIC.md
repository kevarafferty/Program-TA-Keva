# Instruksi ulang #21 di kualitas Epic (menggantikan run Low 18 Nov)

**Selesai jika:** `log_runner\jalankan_baseline.log` berisi `SELESAI 30/30` untuk ClearNoon, SoftRainNoon, ClearNight, dan output `analisis_baseline.py` sudah dikirim ke Claude.
**Waktu:** persiapan 15 menit, run ±3,5–4 jam (tinggal), analisis 5 menit.

## Anti time-out (sudah terpasang)
1. `carla_env.py`: batas tunggu 60 s saat memuat peta + `apply_settings` dicoba ulang 3× (jeda 10 s).
2. `jalankan_baseline.py` (baru, pengganti `.bat`): jeda 30 s antar kondisi; kalau cleanTest gagal (time-out/crash), tunggu 60 s lalu **lanjut otomatis dari seed yang belum selesai** (maks 3× per kondisi). Seed yang sudah tercatat tidak diulang. Semua kejadian dicatat di `log_runner\jalankan_baseline.log`.
3. Kalau tetap BERHENTI: restart `CarlaUE4.exe`, jalankan lagi `python jalankan_baseline.py`. Skrip otomatis hanya mengerjakan sisa seed.

## A. Persiapan (15 menit)
1. Pindahkan `log_runner\20261119_131412_ClearNight` ke `log_runner\_diagnosis\`.
2. Commit: `git add -A && git commit -m "#21 Epic: runner lanjut-otomatis"` (dari `Program TA Keva`).
3. Charger tercolok, sleep mati (`powercfg /change standby-timeout-ac 0`), Windows Update di-pause, tutup aplikasi lain yang memakai GPU.
4. **Restart laptop dulu** kalau sudah menyala lama (VRAM dan CARLA bersih).
5. Buka `CarlaUE4.exe` **tanpa** `-quality-level` (default Epic). Tunggu Town10HD muncul.

## B. Jalankan (2 terminal, folder `10_runner\DQN_Akselerasi vertikal`)
6. Terminal 1, perekam GPU:
   ```
   nvidia-smi --query-gpu=timestamp,memory.used,temperature.gpu,utilization.gpu --format=csv -l 10 > log_runner\gpu_epic.csv
   ```
7. Terminal 2:
   ```
   conda activate carla_env
   python jalankan_baseline.py
   ```
8. Tonton sampai `EPISODE 1: ... kamera telat 0` dan `✅ YOLO loaded on CUDA`, lalu tinggal.

## C. Setelah selesai
9. Ctrl+C di terminal 1.
10. Buka `log_runner\jalankan_baseline.log`: harus ada 3 baris `SELESAI 30/30`.
11. `python analisis_baseline.py --runs "log_runner\*_Epic"`
12. Kirim output + `gpu_epic.csv` + `jalankan_baseline.log` ke Claude. Commit.
