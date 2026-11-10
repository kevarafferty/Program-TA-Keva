# Panduan source build CARLA 0.9.15 di laptop (Windows 11)

Target: menyamai build PC lab. CARLA tag `0.9.15` (commit `d7b45c1`), UE4 fork CarlaUnreal branch `carla`
commit `e22f1e2`, Visual Studio 2019 (msvc-14.2). Sumber: `08_kunjungan_lab/`.
Total ±8–13 jam, sebagian besar menunggu. Centang tiap langkah.

## 0. Persiapan (30 menit)
- [ ] Disk kosong >= 170 GB di drive yang sama (misalnya D:). Pakai path pendek: `D:\UnrealEngine`, `D:\carla`
- [ ] Laptop dicolok charger, mode Performance, sleep dimatikan saat dicolok
- [ ] Windows Security → Virus & threat protection → Exclusions: tambahkan `D:\UnrealEngine` dan `D:\carla` (build jauh lebih cepat)
- [ ] Hubungkan akun GitHub ke akun Epic Games (epicgames.com → Account → Apps and Accounts → GitHub), lalu terima undangan organisasi EpicGames di email/GitHub. Tanpa ini repo UnrealEngine tidak bisa di-clone

## 1. Prasyarat (1–2 jam)
- [ ] Visual Studio 2019 (Community). Workload: Desktop development with C++. Individual components: MSVC v142 x64/x86, Windows 8.1 SDK (jika tidak ada: Windows 10 SDK 10.0.18362 atau lebih baru), .NET Framework 4.6.2 targeting pack
- [ ] CMake >= 3.15 (centang "Add to PATH")
- [ ] Git
- [ ] GNU Make 3.81 (GnuWin32), tambahkan `C:\Program Files (x86)\GnuWin32\bin` ke PATH
- [ ] 7-Zip
- [ ] Python 3 x64 di PATH, lalu `pip install --user setuptools wheel`
- Cek di Command Prompt baru: `cmake --version`, `git --version`, `make --version`, `python --version`

## 2. Unreal Engine fork (3–6 jam, sebagian besar menunggu)
```
git clone --depth 1 -b carla https://github.com/CarlaUnreal/UnrealEngine.git D:\UnrealEngine
cd /d D:\UnrealEngine
git log -1 --format=%H
```
- [ ] Hash harus diawali `e22f1e2`. Jika berbeda:
  `git fetch --depth 1 origin e22f1e24769303a898b68e574f9856acfc78afeb` lalu `git checkout FETCH_HEAD`
- [ ] `Setup.bat` (30–60 menit, mengunduh dependensi)
- [ ] `GenerateProjectFiles.bat`
- [ ] Buka `UE4.sln` di VS2019 → konfigurasi `Development Editor`, platform `Win64` → klik kanan proyek `UE4` → Build (2–4 jam)
- [ ] Uji: jalankan `D:\UnrealEngine\Engine\Binaries\Win64\UE4Editor.exe`, cukup sampai jendela proyek muncul, lalu tutup
- [ ] Buat environment variable sistem `UE4_ROOT` = `D:\UnrealEngine\`, lalu buka ulang semua Command Prompt

## 3. CARLA 0.9.15 (3–5 jam)
```
git clone https://github.com/carla-simulator/carla D:\carla
cd /d D:\carla
git checkout 0.9.15
```
- [ ] Terapkan 3 perbaikan URL dari PC lab (hanya berkas unduhan; JANGAN terapkan bagian .uproject karena mengaktifkan plugin Houdini/StreetMap yang tidak kita punya):
```
git apply --include=Update.bat --include=Util/InstallersWin/install_boost.bat --include=Util/InstallersWin/install_zlib.bat "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\08_kunjungan_lab\carla_diff.txt"
git status
```
  `git status` harus menunjukkan 3 berkas berubah. Jika `git apply` gagal, edit manual 3 baris (lihat bagian "Edit manual" di bawah)
- [ ] Opsional, membuat editor lebih ringan: di `Unreal\CarlaUE4\Config\DefaultEngine.ini` ganti `EditorStartupMap=...Town10HD_Opt...` menjadi `EditorStartupMap=/Engine/Maps/Entry`
- [ ] `Update.bat` (mengunduh aset CARLA, puluhan GB, 1–2 jam)
- [ ] Buka **x64 Native Tools Command Prompt for VS 2019** (BUKAN Anaconda Prompt), lalu:
```
cd /d D:\carla
make launch
```
  Pertama kali: kompilasi 1–2 jam + shader 30–60 menit. Selesai jika Unreal Editor CARLA terbuka
- `make PythonAPI` tidak perlu: env Dika (`carla_env`, Python 3.8) memakai `pip install carla==0.9.15`

## 4. Uji koneksi (5 menit)
- [ ] Di editor tekan Play
- [ ] Di Anaconda Prompt: `conda activate carla_env` lalu
  `python -c "import carla; c=carla.Client('127.0.0.1',2000); c.set_timeout(10); print(c.get_server_version())"`
- [ ] Harus mencetak `0.9.15...`. Pakai `127.0.0.1`, bukan `localhost` (masalah Cloudflare WARP di lab)

## Edit manual (jika git apply gagal)
- `Update.bat`: `http://carla-assets.s3.amazonaws.com/` → `https://carla-assets.s3.us-east-005.backblazeb2.com/`
- `Util\InstallersWin\install_boost.bat`: `https://boostorg.jfrog.io/artifactory/main/release/` → `https://archives.boost.io/release/`
- `Util\InstallersWin\install_zlib.bat`: `https://www.zlib.net/zlib%ZLIB_VERSION:.=%.zip` → `https://github.com/madler/zlib/releases/download/v%ZLIB_VERSION%/zlib%ZLIB_VERSION:.=%.zip`

## Aturan saat error
- Foto/salin 20 baris terakhir pesan error, kirim ke Claude
- Maksimal 1 jam mencoba sendiri per error
- Jangan pasang VS2022 berdampingan selama build; jika sudah terpasang, beri tahu Claude dulu

## Langkah berikutnya setelah ini (bukan sekarang)
Tugas #12: masukkan `train_fix` + `Aset_Lubang` + OpenDrive ke `D:\carla\Unreal\CarlaUE4\Content\Carla\Maps\`, lalu #13 `make package`.
