# Ceklis kunjungan lab — PC Ryzen_PC (Senin 9 Nov 2026)

**Tujuan utama:** membuat peta `train_fix` bisa dijalankan di laptop sendiri, supaya tidak perlu ke lab lagi.
**Prinsip:** jangan mengubah berkas Dika/Retta. Kalau perlu mengedit skrip, kerjakan di salinan.

## Malam ini (15 menit)

1. Siapkan SSD/flashdisk minimal **128 GB** (hasil package CARLA bisa 15–25 GB).
2. Salin folder `08_kunjungan_lab` dan `alat_carla` ke SSD itu.
3. Cek ruang kosong laptop: minimal 40 GB.
4. Kabari pemegang lab bahwa kamu akan memakai PC itu beberapa jam, dan akan menjalankan `make package`.
5. **Jangan pasang CARLA 0.9.15 dulu.** Versinya harus sama dengan build di lab, dan versi itu baru diketahui besok.

## Di lab, berurutan

| # | Langkah | Waktu | Lanjut jika |
|---|---|---|---|
| 1 | Buka **Anaconda Prompt**, jalankan `kumpulkan_info_lab.bat` dari SSD | 15–20 menit | `info.txt` bagian 4 menunjukkan `D:\carla` ada **dan** bagian 5 menemukan `train_fix.umap` |
| 2 | `cd /d D:\carla` → `make launch` → di Content Browser buka peta `train_fix` → tekan Play | 20–40 menit | Peta tampil dan bisa di-Play |
| 3 | Di env Dika: `python ukur_geometri.py --out <SSD>\geometri_terukur.json` (peta aktif, tanpa `--peta`) | 10 menit | Berkas JSON terisi. Kalau error, foto pesan errornya |
| 4 | Salin `cleanTest.py` ke folder lain, jalankan salinannya sekali (cuaca bawaan: ClearNight) | 10 menit | Catat jumlah Hits/Avoids, bandingkan dengan 9/19 (47%) |
| 5 | Tutup editor. Di `D:\carla` jalankan `make package` | 2–4 jam (belum pasti) | Selesai tanpa error |
| 6 | Uji hasil package (lihat di bawah) | 10 menit | `train_fix` muncul di daftar peta |
| 7 | Salin ke SSD: folder package `WindowsNoEditor`, `D:\carla\PythonAPI\carla\dist\`, `hasil_lab\` | 30 menit | — |

**Kalau langkah 1 gagal** (tidak ada source build atau tidak ada `train_fix`): salin `hasil_lab\`, pulang. Itu bukti untuk dosbing
bahwa butir #1 di `PERBEDAAN_PROPOSAL.md` wajib disetujui.

**Kalau `make package` error:** jangan habiskan lebih dari 1 jam untuk memperbaikinya. Foto pesan errornya, lalu
kerjakan langkah 7 tanpa folder package.

### Uji hasil package (langkah 6)

Jalankan `CarlaUE4.exe` dari folder package (biasanya `D:\carla\Build\UE4Carla\<versi>\WindowsNoEditor\`), lalu:

```
python -c "import carla; c=carla.Client('localhost',2000); c.set_timeout(30); print([m for m in c.get_available_maps() if 'train' in m.lower()])"
```

Jika `train_fix` muncul di daftar, jalankan juga `python -c "...; c.load_world('train_fix')"` untuk memastikan petanya bisa dimuat.
Jika muncul, folder `WindowsNoEditor` itulah CARLA yang kamu bawa pulang.

## Waktu menunggu `make package` (langkah 5)

- Cari folder data latih YOLO Dika (`TrainYolo`) di `C:\Users\Ryzen_PC\Documents\TA_Dika`. Cek ukurannya dulu; salin hanya jika < 10 GB.
- Bandingkan hash di `info.txt` bagian 6 dengan tabel di bawah. Jika ada yang berbeda, salin berkas versi PC lab itu ke SSD.

| Berkas | 16 karakter awal SHA-256 di folder unduhanmu |
|---|---|
| `carla_env.py` | `63e2c286013456f3` |
| `cleanTest.py` | `5a198eaa191e6a04` |
| `model_best.h5` | `4a5055b62dc0949f` |
| `pothole_gt.json` | `15be33df879648fe` |
| `best_pure.pt` | `7b6b44f3a6204f21` |

## Jangan disalin

- Seluruh `D:\carla` (±165 GB). Tanpa Unreal Engine dan Visual Studio, folder itu tidak bisa dijalankan di laptop.
- Peta Retta. Opsi B menunggu keputusan dosbing (butir #4).

## Catatan versi

Kalau `info.txt` menunjukkan build lab adalah **0.9.14**, hasil package juga 0.9.14. Laptopmu harus memakai Python API dari
`PythonAPI\carla\dist` build itu (perhatikan versi Python di nama berkasnya, misalnya `cp37`), bukan `pip install carla==0.9.15`.
`alat_carla/SETUP_ENV.md` perlu disesuaikan setelahnya.

## Bawa pulang

Folder `hasil_lab\` + `geometri_terukur.json` + catatan Hits/Avoids langkah 4 + (jika berhasil) folder package.
Taruh di `Keva_TA_Kerja\08_kunjungan_lab\`, lalu minta Claude memprosesnya.
