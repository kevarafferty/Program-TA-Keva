# Instruksi: mencocokkan preset hujan dengan rekaman Dika (`11_cuaca/cocokkan_cuaca.py`)

**Selesai jika:** ada `hasil_EditorHigh/` dan `hasil_PaketEpic/`, masing-masing berisi `ringkasan_hujan.json`, `ringkasan_cerah.json`, dan montasenya, lalu output terminal sudah dikirim ke Claude.
**Waktu:** ±30 menit total (dua kali render ±2 menit; sisanya buka/tutup CARLA).

## Yang sudah dikerjakan Claude
- Skrip `cocokkan_cuaca.py` (3 langkah: `referensi`, `ambil`, `bandingkan`).
- **Langkah `referensi` sudah dijalankan** untuk cerah, hujan, dan malam dari `recordings/*.mp4` Dika. Hasilnya ada di `11_cuaca/referensi/`. Tidak perlu diulang.
- Langkah `bandingkan` sudah diuji dengan data tiruan (frame Dika sendiri): cerah → ClearNoon, hujan → HardRainNoon, jadi alurnya berjalan. Langkah `ambil` **belum diuji** karena butuh CARLA.

## Temuan baru yang mengubah rencana
Video layar Dika (`TA_Dika/Video Test/*.mp4`) menunjukkan ketiga run dijalankan di **Unreal Editor (Play), `Scalability: High`**, bukan paket dan bukan Epic. Karena itu render dilakukan dua kali:
- **A. EditorHigh**: sama dengan lingkungan Dika. Ini yang menentukan preset hujan.
- **B. PaketEpic**: lingkungan baseline #21–#22. Gunanya untuk melihat apakah Epic dan High berbeda jauh.

## A. Render di Editor, Scalability High
1. Jalankan Unreal Editor source build (seperti saat #12: `make launch` di `D:\carla`), lalu buka peta `train_fix`.
2. Di toolbar viewport: **Settings → Engine Scalability Settings → High**. Pastikan label kuning di viewport bertuliskan `Scalability: High`, sama dengan video Dika.
3. Klik **Play** dan tunggu sampai peta berjalan.
4. Anaconda Prompt:
   ```
   conda activate carla_env
   cd /d "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\11_cuaca"
   python cocokkan_cuaca.py ambil --label EditorHigh
   ```
   Seharusnya muncul 7 baris `[k/56] <preset> selesai`. Citra tersimpan di `data_EditorHigh\<preset>\`.
5. Stop Play, lalu tutup Editor.

## B. Render di paket, Epic
6. Buka `CarlaUE4.exe` hasil package **tanpa** `-quality-level`. Tunggu Town10HD muncul.
7. ```
   python cocokkan_cuaca.py ambil --label PaketEpic
   ```
   Skrip memuat `train_fix` sendiri.

## C. Bandingkan (tanpa CARLA)
8. ```
   python cocokkan_cuaca.py bandingkan --kondisi cerah --label EditorHigh
   python cocokkan_cuaca.py bandingkan --kondisi hujan --label EditorHigh
   python cocokkan_cuaca.py bandingkan --kondisi cerah --label PaketEpic
   python cocokkan_cuaca.py bandingkan --kondisi hujan --label PaketEpic
   ```
9. **Uji kewarasan dulu:** pada `--kondisi cerah`, ClearNoon harus juara. Kalau bukan, metriknya tidak bisa dipercaya untuk memilih preset hujan. Berhenti di sini dan kirim hasilnya ke Claude.
10. Buka `hasil_EditorHigh\montase_hujan.jpg`. Baris paling atas = Dika, baris berikutnya diurutkan dari skor terbaik. Pastikan secara visual juaranya memang paling mirip (kabut, langit, jalan basah).
11. Kirim keempat output terminal + kedua `montase_hujan.jpg` ke Claude. Lalu commit:
    `git add -A && git commit -m "cuaca: pencocokan preset hujan vs rekaman Dika"`

## Aturan keputusan (tulis di LOG sebelum melihat hasil)
- Preset hujan dipilih dari **skor + montase**, bukan dari angka penghindaran mana yang mendekati 84,2%.
- Kalau dua teratas hampir seri (skrip memberi PERHATIAN), pilih dari montase dan catat alasannya.
- Baru setelah preset ditetapkan: ulangi baseline hujan 30 episode,
  `python jalankan_baseline.py --kondisi <PresetTerpilih>` (di `10_runner\DQN_Akselerasi vertikal`).
- Konfirmasi ke Dika tetap dikirim. Sampai Dika menjawab, statusnya: "preset dipilih dari kecocokan citra dengan rekaman Dika, belum dikonfirmasi".

## Kalau ada masalah
- `Gagal spawn Microlino`: ada kendaraan tersisa dari run lain. Restart CARLA atau Play ulang.
- Editor macet setelah skrip error: skrip mengembalikan mode asinkron di blok `finally`. Kalau tetap macet, Stop/Play ulang.
- Mobil tampak melayang atau terbenam di citra: kirim satu citra ke Claude (z diambil dari waypoint + 0,5 m, lalu jatuh selama 20 tick).
