# Instruksi TODO #17–#20

Total waktu: ±4–5 jam, bisa dipecah 4 sesi. Kerjakan berurutan; tiap tugas butuh hasil tugas sebelumnya.

Posisi sekarang (17 Nov):
- #16 selesai. Draf GT dari editor sudah ada: `alat_carla/pothole_gt_editor.json` (40 objek: 32 High + 8 Low).
- Skrip bantu sudah dibuat dan dites oleh Claude: `alat_carla/cocokkan_gt.py` (#17), `02_pelabel_roda/baseline_lurus_v2.py` (#18).
- Yang tersisa di #17 hanya: konfirmasi 40 objek itu di CARLA paket, lalu tulis GT v2.

Semua perintah dijalankan di **Anaconda Prompt** dengan env `carla_env`, kecuali ditulis lain.

---

## #17 Ukur ulang semua lubang, bangun GT baru (±45 menit)

**Selesai jika:** terminal mencetak `SELESAI #17` dan ada dua berkas `pothole_gt_v2_*.json`.

1. **Buka CARLA paket.** Jalankan `CarlaUE4.exe` hasil package (yang kamu buka 12 Nov). Tunggu sampai Town10HD muncul. (2 menit)
2. **Buka terminal di folder alat:**
   ```
   conda activate carla_env
   cd /d "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\alat_carla"
   ```
3. **Ukur semua lubang di paket** (`--host` wajib diisi; default skrip masih `localhost`):
   ```
   python ukur_geometri.py --host 127.0.0.1 --peta train_fix --kata_lubang hole_low,med_samping --out geometri_terukur_v2.json
   ```
   Cek baris terakhir: `jumlah_lubang` harus **40**. Kalau bukan 40, berhenti dan kirim angkanya ke Claude. (3 menit)
4. **Cocokkan dengan draf GT editor:**
   ```
   python cocokkan_gt.py --ukur geometri_terukur_v2.json --gt pothole_gt_editor.json
   ```
   Hasil yang diharapkan: `COCOK: 40/40`, tidak ada baris `TIDAK ADA DI PAKET` atau `ADA DI PAKET, TIDAK ADA DI GT`, lalu `SELESAI #17`. (1 menit)
5. **Kalau ada baris `UKURAN BEDA` atau objek tidak cocok:** jangan diedit manual. Salin output terminal ke Claude.
6. **Catat 2 keputusan di `LOG_KERJA.md`** (5 menit):
   - Severity angka untuk 8 objek Low = **0,3** (default skrip; ubah dengan `--sev_low` kalau kamu memilih lain). Alasan: konvensi GT Dika High = 0,9; Low harus paling ringan.
   - 8 objek Low adalah **decal retakan**, bukan lubang. Pelabel roda hanya menghitung Medium/High, jadi Low tidak masuk hitungan "terhindar".
7. **Commit:**
   ```
   cd ..
   git add alat_carla
   git commit -m "#17 GT v2: 40 objek terkonfirmasi di paket"
   ```

---

## #18 Hitung ulang baseline mobil lurus (±20 menit)

**Selesai jika:** ada `02_pelabel_roda/hasil_gt_v2/baseline_lurus_v2.json` dan angkanya tertulis di LOG.

Catatan penting sebelum mulai: mobil lurus tidak memakai kamera, jadi angkanya **sama untuk cerah, hujan, dan malam**. Satu angka untuk tiga kondisi. Kolom "per kondisi" di TODO cukup diisi angka yang sama.

1. **Jalankan:**
   ```
   cd 02_pelabel_roda
   python baseline_lurus_v2.py --gt ..\alat_carla\pothole_gt_v2_segmen_dika.json --out hasil_gt_v2
   ```
   (1 menit)
2. **Baca 3 angka dari output** dan tulis di LOG:
   - `lurus_y_spawn.pct_roda` → hasil tes Claude dengan GT editor: **47,4% (9/19)**, sama dengan angka lama.
   - `lurus_lajur_kiri_247_2.pct_roda` → hasil tes: **52,6% (10/19)**.
   - `offset_acak.pct_roda_rata2` → hasil tes: **47,4%** untuk offset ±0,5 m.
   Kalau angkamu berbeda dari ini, berarti posisi di paket beda dari editor. Kirim output ke Claude.
3. **Kenapa hanya segmen Dika (19 lubang)?** Episode Dika ±2.770 langkah × 0,05 s × 7 km/jam ≈ 270 m, yaitu x −299,5 s.d. −27. 21 objek lain (x −7 s.d. +130) tidak pernah dilewati. GT lengkap 40 objek disimpan untuk generator tata letak (#24).
4. **Commit:** `git add . && git commit -m "#18 baseline mobil lurus GT v2"`

---

## #19 Runner: 127.0.0.1, log posisi, offset acak, tanpa sleep (±2–3 jam)

**Selesai jika:** 1 episode menghasilkan CSV berisi posisi x-y per langkah, dan kolom `frame_kamera` = `frame_dunia` di semua baris.

### A. Buat salinan (10 menit)
Pelajaran dari lab: run di folder asli menimpa video dan CSV Dika.
1. Salin folder `TA_Dika Unlocked\Repository\VS_Code\DQN_Akselerasi vertikal` ke `Program TA Keva\10_runner\`.
2. Semua edit di bawah hanya di `10_runner\`. Folder asli jangan disentuh.
3. Commit dulu salinan aslinya: `git add 10_runner && git commit -m "#19 salinan asli cleanTest"`. Dengan begitu setiap perubahanmu bisa dilihat dengan `git diff`.

### B. Cari baris yang perlu diubah (10 menit)
Di **PowerShell**, di folder `10_runner`:
```
Select-String -Path *.py -Pattern "localhost","sleep","synchronous_mode","fixed_delta","\.tick\(","spawn_actor","get_transform","listen\(" | Format-Table Filename,LineNumber,Line -AutoSize
```
Simpan hasilnya (screenshot cukup). Kamu butuh nomor barisnya.

### C. Lakukan 4 perubahan

**C1. Host (2 menit).** Ganti setiap `'localhost'` menjadi `'127.0.0.1'`.

**C2. Hapus `time.sleep` (20 menit). Cek dulu syaratnya.**
- Pastikan hasil pencarian B berisi `synchronous_mode = True` dan `fixed_delta_seconds = 0.05`. Pelabel roda kita mengasumsikan ini (DT = 0,05).
- **Kalau ya:** server menunggu `world.tick()`, jadi `sleep` hanya membuang waktu.
  - `sleep` di dalam loop langkah → beri `#` di depannya.
  - `sleep` saat setup (setelah `load_world` atau `spawn_actor`) → ganti dengan `for _ in range(10): world.tick()`.
- **Kalau tidak ada `synchronous_mode = True`:** berhenti. Jangan hapus `sleep`. Di mode async, `sleep` ikut mengatur kecepatan agen, jadi menghapusnya mengubah perilaku dan baseline tidak lagi sebanding dengan Dika. Kirim hasil pencarian B ke Claude.
- Risiko yang perlu dicek: banyak skrip CARLA memakai `sleep` untuk menunggu gambar kamera. Tanpa `sleep`, YOLO bisa membaca gambar dari langkah sebelumnya. Itu sebabnya ada kolom `frame_kamera` di C3.

**C3. Log posisi per langkah (40 menit).** Nama variabel (`world`, `vehicle`, `action`, `image`) mungkin beda di kode Dika; sesuaikan dengan hasil pencarian B.

Di bagian atas berkas:
```python
import csv, math, os, random, time
OUT_DIR = "log_runner"
os.makedirs(OUT_DIR, exist_ok=True)
```
Di callback kamera, simpan nomor frame gambar terakhir:
```python
frame_kamera_terakhir = image.frame   # pakai global atau atribut objek env
```
Di awal tiap episode:
```python
nama = f"{CUACA}_ep{ep:02d}_seed{seed}_{time.strftime('%m%d_%H%M%S')}.csv"
f_pos = open(os.path.join(OUT_DIR, nama), "w", newline="")
w_pos = csv.writer(f_pos)
w_pos.writerow(["step", "t_sim", "frame_dunia", "frame_kamera", "x", "y", "yaw", "v_kmh", "aksi"])
t0 = time.perf_counter()
```
Tiap langkah, **setelah** `world.tick()`:
```python
snap = world.get_snapshot()
tf = vehicle.get_transform(); v = vehicle.get_velocity()
w_pos.writerow([step, snap.timestamp.elapsed_seconds, snap.frame, frame_kamera_terakhir,
                tf.location.x, tf.location.y, tf.rotation.yaw, 3.6 * math.hypot(v.x, v.y), action])
```
Di akhir episode:
```python
f_pos.close()
print(f"EPISODE {ep}: {step} langkah, {time.perf_counter() - t0:.1f} s")
```

**C4. Offset awal acak dengan seed (20 menit).** Di tempat transform spawn dibuat, sebelum `spawn_actor`:
```python
seed = ep            # episode 0..29 → seed 0..29, bisa diulang
rng = random.Random(seed)
sp.location.y += rng.uniform(-0.5, 0.5)   # lateral, tetap di dalam lajur (lebar lajur ±3,3 m)
sp.location.x += rng.uniform(-2.0, 2.0)   # longitudinal
```
Kenapa ±0,5 m: setengah lebar Microlino 0,74 m, jadi mobil tetap di lajur spawn. Baseline mobil lurus untuk rentang ini sudah dihitung di #18 (tetap 47,4%).

### D. Uji 1 episode (20 menit)
1. CARLA paket menyala, `train_fix` dimuat.
2. Jalankan `cleanTest.py` dari `10_runner` untuk 1 episode cerah.
3. Buka CSV di `log_runner\`. Cek 3 hal:
   - [ ] `x` bergerak dari sekitar −300 ke sekitar −27
   - [ ] `y` di sekitar 250 (± offset)
   - [ ] `frame_kamera` = `frame_dunia` di semua baris. Kalau selisihnya 1, kamera tertinggal satu langkah: kirim 10 baris CSV ke Claude sebelum lanjut.
4. Commit: `git add 10_runner && git commit -m "#19 runner: 127.0.0.1, log posisi, offset acak, tanpa sleep"`

---

## #20 Ukur detik/episode, lalu putuskan laptop atau cloud (±1 jam)

**Selesai jika:** angka detik/episode dan keputusan tertulis di LOG.

1. **Siapkan pengukuran:** buka Task Manager → tab Performance → GPU. Biarkan terbuka.
2. **Jalankan 5 episode cerah** dengan runner #19 (seed 0–4). Jangan ubah kualitas grafis CARLA: YOLO harus melihat gambar yang sama dengan run Dika. (±15–25 menit)
3. **Catat per episode** (dari baris `EPISODE ...` di terminal): langkah, detik. Hitung:
   - rata-rata detik/episode = **t**
   - faktor real-time = (langkah × 0,05) / detik. Nilai > 1 berarti lebih cepat dari waktu nyata.
   - VRAM terpakai dan suhu GPU tertinggi.
4. **Putuskan dengan tabel ini:**

   | t (detik/episode) | Gate 1: 90 episode | Fase 3: ±3.600 episode | Keputusan |
   |---|---|---|---|
   | ≤ 150 | ≤ 4 jam | ≤ 150 jam (±15 malam) | **Laptop** |
   | 150–250 | 4–6 jam | 150–250 jam (±25 malam) | Laptop untuk Gate 1; Fase 3 dibahas lagi |
   | > 250 | > 6 jam | > 250 jam | Gate 1 tetap laptop (masih 1 malam); Fase 3 perlu PC lab atau cloud |

5. **Hal yang sering terlewat soal cloud:** paketmu adalah build **Windows**. GPU cloud murah umumnya Linux. Pindah ke cloud berarti (a) sewa VM Windows ber-GPU (lebih mahal), atau (b) build ulang CARLA + `train_fix` untuk Linux (berhari-hari). PC lab (`Ryzen_PC`) yang sudah punya source build sering lebih murah daripada keduanya. Jadi pilihannya bukan hanya laptop vs cloud, tetapi laptop vs PC lab vs cloud.
6. **Tulis di LOG:** t, faktor real-time, VRAM, suhu, keputusan, dan alasannya.
7. **Commit**, lalu tandai #17–#20 selesai di `TODO_TA.csv` (tutup dulu di Excel).

---

## Kalau macet
Berikan Claude akses ke folder `TA_Dika Unlocked`, lalu minta: "baca cleanTest.py dan kerjakan C1–C4". Edit di salinan bisa dikerjakan Claude; menjalankan CARLA tetap kamu.
