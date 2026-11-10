@echo off
REM ============================================================
REM  Kumpulkan info PC lab (Ryzen_PC) untuk TA Keva
REM  Jalankan dari "Anaconda Prompt" supaya perintah conda dikenali.
REM  Script ini HANYA MEMBACA. Tidak ada berkas Dika/Retta yang diubah.
REM  Hasil ditulis ke folder hasil_lab\ di sebelah script ini (taruh di flashdisk/SSD).
REM ============================================================

set "OUT=%~dp0hasil_lab"
if not exist "%OUT%" mkdir "%OUT%"
set "INFO=%OUT%\info.txt"
set "ERR=%OUT%\error.txt"

echo Info PC lab, dibuat %DATE% %TIME% > "%INFO%"

echo.>> "%INFO%" & echo ===== 1. Ruang disk ===== >> "%INFO%"
powershell -NoProfile -Command "Get-PSDrive -PSProvider FileSystem | Format-Table Name,@{n='Bebas_GB';e={[math]::Round($_.Free/1GB,1)}},@{n='Terpakai_GB';e={[math]::Round($_.Used/1GB,1)}}" >> "%INFO%" 2>> "%ERR%"

echo.>> "%INFO%" & echo ===== 2. GPU ===== >> "%INFO%"
nvidia-smi >> "%INFO%" 2>> "%ERR%"

echo.>> "%INFO%" & echo ===== 3. Unreal Engine (UE4_ROOT) ===== >> "%INFO%"
echo UE4_ROOT=%UE4_ROOT% >> "%INFO%"

echo.>> "%INFO%" & echo ===== 4. CARLA source build di D:\carla ===== >> "%INFO%"
if exist "D:\carla" (
  echo D:\carla ADA >> "%INFO%"
  powershell -NoProfile -Command "Get-Content 'D:\carla\CHANGELOG.md' -TotalCount 5" >> "%INFO%" 2>> "%ERR%"
  git -C "D:\carla" describe --tags --dirty >> "%INFO%" 2>> "%ERR%"
  echo -- Isi Content\ ^(paket peta^) -- >> "%INFO%"
  dir /b "D:\carla\Unreal\CarlaUE4\Content" >> "%INFO%" 2>> "%ERR%"
  echo -- Wheel/egg Python API -- >> "%INFO%"
  dir /b "D:\carla\PythonAPI\carla\dist" >> "%INFO%" 2>> "%ERR%"
  echo -- Hasil package yang sudah pernah dibuat -- >> "%INFO%"
  dir /b "D:\carla\Build\UE4Carla" >> "%INFO%" 2>> "%ERR%"
  dir /b "D:\carla\Dist" >> "%INFO%" 2>> "%ERR%"
) else (
  echo D:\carla TIDAK ADA - cari folder CARLA lain di bagian 5 >> "%INFO%"
)

echo.>> "%INFO%" & echo ===== 5. Lokasi peta train_fix dan CarlaUE4.exe ===== >> "%INFO%"
echo (pencarian bisa makan beberapa menit)
where /r D:\ train_fix.umap >> "%INFO%" 2>> "%ERR%"
where /r C:\Users train_fix.umap >> "%INFO%" 2>> "%ERR%"
where /r D:\ CarlaUE4.exe >> "%INFO%" 2>> "%ERR%"
where /r C:\Users CarlaUE4.exe >> "%INFO%" 2>> "%ERR%"

echo.>> "%INFO%" & echo ===== 6. Hash berkas Dika di PC lab (bandingkan dengan CEKLIS_LAB.md) ===== >> "%INFO%"
for %%F in (carla_env.py cleanTest.py model_best.h5 pothole_gt.json best_pure.pt) do (
  for /f "delims=" %%P in ('where /r C:\Users\Ryzen_PC\Documents %%F 2^>nul') do (
    echo %%P >> "%INFO%"
    certutil -hashfile "%%P" SHA256 | findstr /v "hash CertUtil" >> "%INFO%"
  )
)

echo.>> "%INFO%" & echo ===== 7. Environment conda ===== >> "%INFO%"
call conda env list >> "%INFO%" 2>> "%ERR%"
for /f "tokens=1" %%E in ('conda env list ^| findstr /v /b "#"') do (
  echo mengekspor env %%E ...
  call conda env export -n %%E > "%OUT%\env_%%E.yml" 2>> "%ERR%"
  call conda run -n %%E pip freeze > "%OUT%\pip_%%E.txt" 2>> "%ERR%"
  call conda run -n %%E python --version >> "%INFO%" 2>> "%ERR%"
)

echo.
echo Selesai. Kirim seluruh folder hasil_lab ke Claude (atau taruh di Keva_TA_Kerja\08_kunjungan_lab\).
pause
