# 12_lingkungan — generator tata letak lubang (#24) + runner skenario off-nominal (#25)

Dokumentasi folder ini (dulu `INSTRUKSI_24_25.md`). Diperbarui 22 Nov 2026.

**Status:** kode selesai, 113 uji lulus tanpa CARLA (CARLA tiruan + YOLO dan DQN asli; Ultralytics 8.4.13 dan 8.4.216).
Pemeriksaan di CARLA sungguhan (slot, toggle, kecepatan, azimut) **lulus 21 Nov**. Matriks malam 21–22 Nov dibuang karena
bug toggle lubang (±40% episode lubang tak tampak); sudah diperbaiki dengan verifikasi per episode, run diulang.
Riwayat lengkap: `LOG_KERJA.md` 21–22 Nov.

## Isi folder

| Berkas | Fungsi |
|---|---|
| `generator_tata_letak.py` | Seed → tata letak lubang → GT JSON (format sama dengan `pothole_gt.json`). Backend **grid** (nyalakan/matikan 40 objek lubang yang sudah ada di `train_fix` lewat `enable_environment_objects`) dan **spawn** (`static.prop.mesh`, posisi bebas, butuh aset) |
| `skenario.py` | Katalog Tabel 2.2 (REG, ID0, A1–A6, B3, C1–C4, D1, E1, E2) × 3 tingkat, mode `konstan`/`transisi`, korupsi citra A5/A6 |
| `env_skenario.py` | Turunan `CarlaEnv` Dika (kode Dika tidak diubah): tata letak, cuaca, transisi, lampu, throttle, kendaraan, hook persepsi |
| `persepsi_hook.py` | Logit per deteksi + 100 logit anchor teratas + fitur neck 896-D dari **inferensi yang sama** dengan agen |
| `logger_skenario.py` | Log per langkah (CSV) + persepsi (NPZ) + GT + meta per episode; `muat_episode()` untuk analisis |
| `jalankan_skenario.py` | Runner satu kondisi, lanjut-otomatis per seed |
| `jalankan_matriks.py` | Banyak kondisi berurutan, coba ulang setelah crash |
| `verifikasi_lubang.py` | Verifikasi per episode: kamera di belakang lubang pertama/tengah/terakhir, YOLO harus melihat lubang; gagal → toggle diulang (maks 3×) lalu error |
| `cek_kualitas_run.py` | Menandai episode "buta" (deteksi dekat − jauh < 0,08) di folder run |
| `uji_carla_24_25.py` | Pemeriksaan di CARLA (Langkah A) + kalibrasi kecepatan dan azimut |
| `kalibrasi_lingkungan.json` | Hasil kalibrasi: throttle → km/jam, azimut matahari 180° |
| `tests/` | Uji unit + uji end-to-end dengan CARLA tiruan |

## Langkah A — pemeriksaan di CARLA (±20 menit)

Sudah lulus 21 Nov. Ulangi hanya jika paket CARLA atau peta dibangun ulang.

CarlaUE4.exe paket dibuka **tanpa** `-quality-level` (Epic). Anaconda Prompt, env `carla_env`:

```
cd "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\12_lingkungan"
python -m pytest -q tests\test_generator.py tests\test_skenario.py
python uji_carla_24_25.py semua
```

| Bagian | Lulus jika | Kalau gagal |
|---|---|---|
| pytest | Semua lulus. `test_sidik_acuan_lintas_mesin` lulus = tata letak dari seed identik di laptop dan cloud | Kirim output; tata letak tidak reprodusibel lintas mesin |
| `slot` | `slot_ketemu: 40`, `tidak_ketemu: []` | Kirim `uji_carla/slot.json` |
| `toggle` | `selisih_nyala_vs_mati > 0,5`, `selisih_nyala_vs_nyala_lagi < 0,5`; di `toggle_mati.png` lubang hilang, di `toggle_sebagian_*.png` hanya 2 lubang | Backend grid tidak bisa dipakai → wajib spawn |
| `kecepatan` | Throttle 0,30 ≈ 7 km/jam (pembanding baseline). Tabel masuk `kalibrasi_lingkungan.json` | Kirim `uji_carla/kecepatan.json` |
| `azimut` | Di `azimut_<terbaik>.png` matahari tampak di depan kamera | Isi `azimut_menghadap_kamera` secara manual di `kalibrasi_lingkungan.json` |

Lalu uji runner (±5 menit):

```
python jalankan_skenario.py --kode REG --tingkat 1 --episodes 2
python jalankan_skenario.py --kode A3 --tingkat 2 --mode transisi --episodes 1
```
Cek di `log_skenario\<folder>\ringkasan_episode.csv`: kolom `hook_tidak_cocok` = 0, `akhir` = finis, dan untuk A3 kolom `langkah_onset` terisi. Kirim kedua folder (atau cukup CSV + meta) ke Claude.

## Langkah B — uji regresi (1 malam, sebelum data monitor)

```
python jalankan_matriks.py --kondisi REG:1:konstan REG:2:konstan REG:3:konstan
```
REG = 19 lubang Dika + offset dan preset yang sama dengan baseline #21–#22. Hasilnya harus setara `HASIL_BASELINE.md` (cerah logika Dika ±99,5%, hujan HardRainNoon ±72%, malam ±36%). Kalau setara, runner baru terbukti tidak mengubah perilaku agen, dan sekaligus kita punya fitur/logit/Q untuk kondisi baseline.

## Langkah C — backend spawn (opsional; perlu untuk C1 t2–3, D1 t2–3, B3)

Grid hanya bisa memakai 19 posisi Dika (2 lajur, jarak 8,7–15 m, semua High). Untuk klaster rapat, pasangan < 8 m, dan lubang di tepi lajur dibutuhkan posisi bebas:

1. Di Unreal Editor: duplikat `/Engine/BasicShapes/Plane` → simpan sebagai `/Game/Carla/Static/Lubang/SM_Lubang_High_2x3`.
2. Buka mesh: *Build Scale* X=2, Y=3 (ukuran sama dengan lubang Dika 2 × 3 m), material slot 0 = `/Game/Carla/Maps/Aset_Lubang/highh`, *Collision Complexity* = *No Collision* / hapus *simple collision*.
3. *Project Settings → Packaging → Additional Asset Directories to Cook*: tambahkan `/Game/Carla/Static/Lubang`. Lalu `make package`.
4. `python uji_carla_24_25.py spawn --mesh /Game/Carla/Static/Lubang/SM_Lubang_High_2x3.SM_Lubang_High_2x3` → lulus jika `spawn_tampak.png` bertekstur retak dan `tabrakan_dengan_prop` kosong.

Kalau `mesh_path` aset berbeda, ubah `VarianAset.mesh_path` di `generator_tata_letak.py`.

## Matriks data

`python jalankan_matriks.py --cek` → matriks bawaan 28 kondisi × 30 episode = 840 episode ≈ 33 jam (140 s/episode) ≈ 3–4 malam. Disk: ±5–6 MB/episode dengan `--simpan_fitur 1` (≈ 5 GB untuk matriks bawaan).

## Isi log per episode

| Berkas | Isi |
|---|---|
| `langkah_ep###_seed#.csv` | Satu baris per langkah: pose (x, y, yaw, v), aksi, `q0–q2`, `q_margin`, state 10-D `s0–s9`, `n_det`, `conf_top`, `cls_top`, `hook_cocok`, `f_transisi`, `f_korupsi`, cuaca terpasang `w_*`, reward, hits/avoids |
| `persepsi_ep###_seed#.npz` | `fitur` (T, 896), `topk_logit` (T, 100, 3), `det_*` (semua deteksi: step, logit 3 kelas, box, conf, cls, anchor) |
| `gt_ep###_seed#.json` | Lubang episode ini (input pelabel roda) |
| `meta_ep###_seed#.json` | Spesifikasi skenario, angka cuaca awal/target, throttle, geometri kendaraan (roda), versi paket, akhir episode |

Penyelarasan: baris *t* = state dari frame sebelum aksi *t* + persepsi yang menghasilkannya + Q dan aksi dari state itu + pose saat frame itu diambil. Label kontak roda dalam horizon H = 2 s dihitung dari pose + GT dan langsung sejajar dengan skor monitor di baris yang sama.

## Keputusan desain (belum dikonfirmasi dosbing)

1. **Desain berpasangan.** Tata letak dan offset awal hanya bergantung pada seed, bukan kode skenario. A3 seed 5 dan ID0 seed 5 memakai lubang dan titik awal yang sama.
2. **ID-0 = 2–5 lubang/100 m** (5–13 lubang), lebih jarang dari Dika (7,5/100 m), jarak minimum 10 m. Akibatnya tata letak asli Dika (19 lubang) menjadi **C1 tingkat 1** ("padat" relatif ID-0).
3. **A2 tingkat 3 = HardRainNoon persis** (cocok dengan video Dika); tingkat 1–2 = interpolasi ClearNoon → HardRainNoon (f = 0,6 dan 0,8). Ini menggantikan rentang angka di Tabel 2.2.
4. **A1 memakai lampu LowBeam** sesuai proposal; baseline Dika (REG t3) **tanpa** lampu. Jangan bandingkan keduanya langsung.
5. **Transisi berbasis posisi**: onset di 30–55% ruas, rampa 20 m (`--rampa 0` = mendadak). Pada 7 km/jam rampa 20 m ≈ 10 s.
6. **C3 diambil dari pita** |offset_y| dan |heading| di luar rentang ID-0 (±0,5 m, 0°), bukan dari 0.
7. **A5/A6 diterapkan pada citra yang masuk YOLO saja.** Atribut kamera `motion_blur_intensity` tidak diubah.
8. **REG ditambahkan** (tidak ada di proposal) sebagai uji regresi dan pembanding baseline.

## Batasan yang sudah diketahui

- **B1 dan B2 belum bisa dibuat**: butuh tekstur lubang tergenang dan pola mirip lubang. B3 hanya posisi (tepi lajur), tanpa variasi ukuran.
- Dengan grid, ID-0 hanya mengacak **subset** dari 19 posisi yang sama. Agen DQN tidak melihat posisi absolut x, jadi kebocoran kecil, tetapi klaim "tata letak baru" untuk C1/D1 butuh backend spawn.
- **C4**: penghitung HIT Dika memakai lebar Microlino (0,74 m) untuk semua kendaraan. Pakai pelabel roda dengan geometri dari `meta_*.json` (`roda_lokal_xy`).
- C2/A4/E2 menolak berjalan sebelum `kalibrasi_lingkungan.json` ada (sengaja, supaya tidak ada run dengan throttle tebakan).
- Uji end-to-end memakai CARLA **tiruan**: membuktikan alur kode, penyelarasan log, toggle, transisi, dan state identik dengan logika Dika, **bukan** bahwa render/fisika CARLA berperilaku seperti diharapkan. Itu tugas Langkah A dan B.
- Setelah setiap run, jalankan `python cek_kualitas_run.py --run log_skenario\<folder_run>` sebelum analisis.
- Belum: pelabel kegagalan per lintasan lubang dan skrip analisis Fase 2 (membaca log ini).
