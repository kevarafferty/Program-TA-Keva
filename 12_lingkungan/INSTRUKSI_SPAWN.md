# Langkah C — backend spawn (ditulis Claude, 22 Nov 2026)

Tujuan: aset StaticMesh lubang yang bisa dimunculkan di posisi bebas lewat `static.prop.mesh`,
tampak sama dengan lubang Dika (Plane 2 × 3 m, material `highh`), tanpa collision.
Perkiraan: editor 20–30 menit + package (sama lamanya dengan 12 Nov) + uji 15 menit.

## 0. Persiapan
1. Tutup CarlaUE4.exe. Commit git folder TA.
2. **Backup build lama**: salin folder `WindowsNoEditor` tempat CarlaUE4.exe sekarang (hasil package 12 Nov) ke mis. `D:\carla_paket_12nov\`. Cek disk dulu (ukuran folder + ±30 GB untuk package baru). Kalau tidak cukup, minimal catat bahwa baseline #21–#22 dibuat dengan build 12 Nov.

## 1. Buka editor
x64 Native Tools Command Prompt for VS 2019:
```
cd /d D:\carla
make launch
```

## 2. Buat aset mesh
1. Content Browser: buat folder `Content/Carla/Static/Lubang`.
2. View Options (kanan bawah Content Browser) → centang **Show Engine Content**. Buka `Engine Content/BasicShapes`.
3. Seret **Plane** ke folder `Carla/Static/Lubang` → **Copy Here**. Rename menjadi **`SM_Lubang_High_2x3`**.
4. Klik dua kali → Static Mesh Editor:
   - Details → **Material Slots** → Element 0 = `highh` (dari `Carla/Maps/Aset_Lubang`).
   - Details → **LOD0 → Build Settings → Build Scale 3D** = X 2, Y 3, Z 1 → **Apply Changes**. Pojok kiri atas viewport harus menunjukkan *Approx Size* 200 × 300 × 0.
   - Toolbar **Collision → Remove Collision**. Details → Collision → **Collision Complexity = Use Simple Collision As Complex** (jadi tidak ada collision sama sekali).
   - Save (Ctrl+S).
5. **Jangan** menaruh aset ini di peta train_fix dan jangan menyimpan peta.

## 3. Pastikan ikut ter-package
Edit → Project Settings → Packaging → (klik panah Advanced) **Additional Asset Directories to Cook** → `+` → pilih `/Game/Carla/Static/Lubang`.
Cek `D:\carla\Unreal\CarlaUE4\Config\DefaultGame.ini` berisi:
```
+DirectoriesToAlwaysCook=(Path="/Game/Carla/Static/Lubang")
```
Pastikan baris `+MapsToCook` untuk train_fix (12 Nov) masih ada. File → Save All, tutup editor.

## 4. Package (sama dengan 12 Nov)
x64 Native Tools Command Prompt for VS 2019:
```
set ROOT_PATH=D:/carla/
set INSTALLATION_DIR=D:/carla/Build/
cd /d D:\carla\Util\BuildTools
BuildCarlaUE4.bat --at-least-write-optionalmodules
Package.bat --ue-version 4.26 --no-zip
```
(Kalau 12 Nov kamu memakai urutan/folder lain yang berhasil, pakai itu.)

## 5. Uji (CarlaUE4.exe BARU, tanpa -quality-level)
```
cd "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\alat_carla"
python uji_package_train_fix.py
cd ..\12_lingkungan
python uji_carla_24_25.py slot
python uji_carla_24_25.py spawn --mesh /Game/Carla/Static/Lubang/SM_Lubang_High_2x3.SM_Lubang_High_2x3
python jalankan_skenario.py --kode D1 --tingkat 2 --backend spawn --episodes 1
python jalankan_skenario.py --kode C1 --tingkat 2 --backend spawn --episodes 1
```

| Uji | Lulus jika |
|---|---|
| uji_package_train_fix | train_fix ada, 18/18 lubang di posisi sama (build baru tidak merusak peta) |
| slot | 40/40 |
| spawn | `spawn_berhasil: true`; `uji_carla\spawn_tampak.png` bertekstur retak seperti `toggle_nyala.png` (bukan abu-abu/kotak-kotak); `tabrakan_dengan_prop: []` |
| D1 t2, C1 t2 | SELESAI, `verif_percobaan` 1, `hook_tidak_cocok` 0 |

Kirim ke Claude: `uji_carla\spawn.json`, `spawn_tampak.png`, dan dua folder run.

## Kalau gagal
- **spawn_berhasil false**: aset tidak ter-cook atau path salah. Path wajib berakhiran `.SM_Lubang_High_2x3`. Cek baris DirectoriesToAlwaysCook.
- **Tekstur abu-abu/kotak-kotak**: material tidak ikut. Cek Element 0 = highh, lalu package ulang.
- **Ada tabrakan dengan prop**: collision belum hilang. Ulangi langkah 2.4 (Remove Collision + Collision Complexity), package ulang. Sementara itu, runner tetap mengabaikan tabrakan dengan lubang hasil spawn (dicatat di `tabrakan_lubang`), tetapi benturan fisik tetap mengubah gerak mobil, jadi jangan dipakai untuk data.
- **`static.prop.mesh` tidak ada di daftar atribut**: build ini tidak mendukung spawn mesh bebas; laporkan, ada jalur lain (mendaftarkan aset sebagai prop CARLA).
- **Build baru bermasalah**: kembali ke backup `D:\carla_paket_12nov\`.

## Setelah lulus
REG t1–t3 × 30 di build baru (malam ini), karena build berganti:
```
python jalankan_matriks.py --kondisi REG:1:konstan REG:2:konstan REG:3:konstan
```
