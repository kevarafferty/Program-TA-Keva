# Pesan untuk Kak Dika (siap kirim, sesuaikan sapaan)

*Versi 2 (7 Nov, siang). Versi pertama punya 9 butir; 4 sudah terjawab sendiri dari folder lengkap yang
kamu unduh, jadi tidak perlu ditanyakan lagi: `best_pure.pt` (identik dengan `best.pt`), lokasi aset tekstur
lubang, folder versi final, dan kamera citra CARLA.*

---

Kak Dika, aku Keva, yang lanjutin TA Kakak soal monitor keselamatan untuk DQN. Aku sudah dapat folder
`TA_Dika` lengkap dan sudah jalan cukup jauh, terima kasih banyak. Tinggal beberapa hal yang aku butuh
konfirmasi supaya bisa reproduksi hasil cerah 19/19. Kalau bisa dibalas sampai **Rabu, 11 November**,
itu sangat membantu.

1. **Peta `train_fix`.** Aku punya `train_fix.umap` dan `.uasset`, tapi itu aset Unreal mentah. Apakah Kakak
   menjalankannya dari CARLA 0.9.14 *source build* (Unreal Editor), atau ada build yang sudah di-*package*?
   Kalau source build, apakah masih ada di PC lab (`Ryzen_PC`) dan boleh aku pakai?
2. **Environment.** Boleh minta hasil `conda env export` (atau minimal versi Python, TensorFlow, Ultralytics,
   dan wheel CARLA) dari environment yang dipakai `train.py` dan `cleanTest.py`?
3. **Pemetaan severity.** Di `carla_env.py`, kelas YOLO dipetakan `{0: 0.6, 1: 0.9, 2: 0.3}`. Di `best_pure.pt`,
   urutan kelasnya `{0: Low, 1: Medium, 2: High}`, jadi deteksi High masuk ke state sebagai 0,3. Apakah ini
   disengaja? Aku lihat di `Catatan.txt` ada catatan soal kompromi ukuran lubang dan deteksi YOLO.
4. **Run cerah.** `sensor_data/cerah.csv` dan `recordings/cerah.mp4` sepertinya dari dua run yang berbeda
   (di langkah 1501 video menunjukkan STRAIGHT dengan total reward 775,2, sedangkan CSV menunjukkan LEFT
   dengan 726,2; panjangnya 2.883 vs 2.904 langkah). Keduanya 19/19. Angka di laporan dari run yang mana?
5. **Ground truth lubang.** Di `pothole_gt.json` semua lubang tercatat High dengan ukuran 2 m × 3 m. Apakah ukuran
   itu sesuai ukuran plane di peta, atau perkiraan dari foto grid?

Terima kasih, Kak. Kalau lebih enak dibahas langsung, aku bisa ke lab kapan saja minggu ini.
