@echo off
REM [#21] Baseline pi_Dika: 30 episode x cerah / hujan / malam, seed 0-29 sama untuk ketiganya.
REM WAJIB: CarlaUE4.exe dibuka TANPA -quality-level (default Epic).
REM Pakai: buka Anaconda Prompt, conda activate carla_env, cd ke folder ini, lalu: jalankan_baseline.bat
REM Lanjut setelah crash: jalankan_baseline.bat <cuaca> <seed_awal> <jumlah>   contoh: jalankan_baseline.bat HardRainNoon 17 13
cd /d "%~dp0"
if not "%1"=="" (
  python cleanTest.py --cuaca %1 --episodes %3 --seed_awal %2 --tampil 0 --label Epic
  goto :eof
)
for %%C in (ClearNoon SoftRainNoon ClearNight) do (
  echo ===== %%C mulai %date% %time% =====
  python cleanTest.py --cuaca %%C --episodes 30 --seed_awal 0 --tampil 0 --label Epic
  echo ===== %%C selesai %date% %time% =====
)
echo SEMUA SELESAI %date% %time%
