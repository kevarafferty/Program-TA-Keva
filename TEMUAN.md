# Temuan dari pemeriksaan kode, bobot, dan data Dika & Retta

Dikerjakan 7 November 2026 (pagi: T1–T15; siang setelah folder lengkap diunduh: T16–T24 dan pembaruan status). Setiap temuan menyebut bukti (berkas/skrip yang menghasilkannya)
dan dampaknya ke proposal. Status: **Terbukti** = diperiksa langsung dari berkas atau dijalankan;
**Dugaan** = konsisten dengan bukti tapi perlu konfirmasi Dika/Retta.

---

## A. Yang mengubah rencana minggu ini

### T1. Dika dan Retta menjalankan semuanya di PC yang sama — PC lab adalah jalan tercepat ke Gate 1 (Dugaan kuat)
> **Pembaruan siang:** folder lengkap Dika dan Retta sudah diunduh. Yang masih hanya ada di PC lab: CARLA source build berisi peta (T18).
- Bukti: `dataset.yaml` dan `train_args` di `best.pt` menunjuk `C:/Users/Ryzen_PC/Documents/TA_Dika/...`;
  `Retta Paper/Source Code/Prompt.txt` menunjuk `C:\Users\Ryzen_PC\Documents\carla_work`. Folder run
  `yolo11n_150e_9k_gpu` milik Retta juga ada di repo Dika (bobotnya kosong).
- Dampak: build CARLA dengan `train_fix`, `best_pure.pt`, env conda (`yolo_cuda310`, `carla915_py37`),
  dan peta `TownRetta` kemungkinan besar masih ada di PC `Ryzen_PC`. Minta akses PC itu, bukan hanya berkas satu per satu.

### T2. Peta `train_fix` yang ada di folder `Environment` belum bisa langsung dimuat (Terbukti)
- Bukti: `Environment/train_fix.umap` dan `train_fix.uasset` (masing-masing ~53 MB). Ini aset Unreal Editor,
  bukan paket CARLA yang sudah di-*cook*.
- Dampak: untuk memakainya perlu CARLA *source build* + Unreal Editor (impor lalu *package*), atau minta Dika
  paket hasil `make package` / build Windows yang sudah jadi. Tabel 2.6 proposal yang menulis "peta train_fix
  diterima" perlu diperjelas: aset mentah diterima, peta siap pakai belum.

### T3. Urutan kelas severity di kode tidak cocok dengan `best.pt` (Terbukti, juga untuk best_pure.pt — lihat T16)
- Bukti: `best.pt` → `names = {0: Low, 1: Medium, 2: High}`. `carla_env.py` memetakan
  `{0: 0.6, 1: 0.9, 2: 0.3}`, sehingga deteksi **High menjadi 0,3** (paling ringan) dan Low menjadi 0,6.
- Dampak: kalau `best_pure.pt` urutannya sama, fitur severity di state DQN terbalik. Bisa juga pemetaan ini
  disengaja karena `best_pure.pt` urutannya lain. Ini harus ditanyakan sebelum baseline direproduksi.

### T4. `best.pt` hampir tidak pernah mengenali lubang CARLA sebagai High (Terbukti)
- Bukti: `04_monitor_persepsi/hasil/ringkasan.json`. Semua 56 lubang di 53 citra CARLA berlabel High.
  Pada citra bersih: 9 dari 53 citra (17%) tanpa deteksi pada conf 0,05; dari 44 citra yang ada deteksinya,
  kotak teratas berkelas **Low pada 43 citra, Medium 1, High 0**. Median conf kotak teratas 0,52.
- Dampak: label kegagalan persepsi "High diklasifikasikan sebagai Low" di Subbab 2.1.3 akan bernilai 1
  hampir di setiap frame, sehingga tidak bisa dipakai. Usulan: pisahkan (a) kegagalan deteksi dan
  (b) kesalahan keparahan, lalu laporkan (b) sebagai temuan *domain gap* (`best.pt` dilatih pada citra
  jalan nyata dengan imgsz 768, tetapi dijalankan pada render CARLA dengan imgsz 320).

---

## B. Yang memperkuat argumen proposal

### T5. Hasil malam Dika (47%) persis sama dengan mobil yang tidak pernah menghindar (Terbukti secara geometri)
- Bukti: `02_pelabel_roda/hasil/ringkasan_perbandingan.json`. Mobil yang melaju lurus di lajur spawn
  (y = 250,5) melewati 19 lubang Dika dengan **9/19 terhindar = 47,4%**, baik menurut label roda maupun
  logika Dika. Log `malam.csv`: STRAIGHT 2.422 dari 2.711 langkah (89%), deteksi YOLO hanya 16% frame.
- Dampak: mendukung H2 dan narasi Bab 1.1. Pada malam hari agen praktis tidak bereaksi, dan sistem
  tidak memberi tanda apa pun. Ini contoh *silent failure* yang menjadi alasan monitor persepsi.

### T6. Bug ambang lateral Dika terbukti dengan angka (Terbukti, geometri roda masih estimasi)
- Bukti: `02_pelabel_roda/test_kontak_roda.py` (14 uji lulus) dan `hasil/sapuan_offset_lateral.png`.
  Logika Dika mencatat "terhindar" untuk offset lateral 1,84–2,16 m, padahal ban kiri masuk lubang.
  Arah sebaliknya juga ada: lubang sempit yang dikangkangi (ban lewat di kiri-kanannya) dicatat HIT oleh Dika.
- Dampak: mendukung pelabel berbasis kontak roda di Subbab 2.1.3. Angka 1,84–2,16 m akan bergeser
  setelah geometri Microlino diukur dengan `alat_carla/ukur_geometri.py`.

### T7. Bug cooldown sudah berpengaruh mulai 11 km/jam, masih di dalam rentang reward Dika (Terbukti)
- Bukti: `02_pelabel_roda/hasil/sapuan_cooldown.png`. Untuk dua lubang selajur berjarak 13 m, kontak kedua
  tercatat "terhindar" mulai 11 km/jam. Rentang kecepatan yang diberi reward di kode Dika adalah 5–15 km/jam.
- Dampak: proposal menulis bug ini "tidak berpengaruh pada 7 km/jam". Itu benar untuk lintasan Dika,
  tetapi skenario C2 (20–30 km/jam) dan generator prosedural pasti kena. Perlu disebut eksplisit di Tabel 2.1.

### T8. Logit per deteksi bisa diambil tanpa mengubah YOLO (Terbukti) — risiko teknis terbesar sudah hilang
- Bukti: `04_monitor_persepsi/verifikasi_hook.py` → `hasil/verifikasi_hook.json`. Pada 689 inferensi
  (53 citra × 13 kondisi, 432 kotak), sigmoid(logit) sama dengan conf dari `predict()` (selisih maks 6×10⁻⁸),
  kelas sama, dan kotaknya identik (selisih 0 piksel). Tidak ada satu pun yang tidak cocok.
- Dampak: JointEnergy per deteksi dan fitur neck (896 dimensi: P3 128 + P4 256 + P5 512) siap dipakai.

---

## C. Yang perlu kamu waspadai

### T9. Skor energi per deteksi tidak lebih baik dari MSP pada data ini (Terbukti untuk 53 citra; belum general)
- Bukti: `04_monitor_persepsi/hasil/ringkasan.json`, evaluasi E2 (hanya frame yang punya deteksi, 188 sampel,
  8 gagal): AUROC MSP 0,924, energi 0,923, JointEnergy 0,922. Selang kepercayaan lebar (≈0,80–0,98).
- Dampak: target S2 "lebih baik dari MSP" berisiko gagal. Untuk kepala sigmoid 3 kelas yang satu kelasnya
  dominan, energi dan MSP hampir memberi urutan yang sama. Siapkan narasi cadangan: kontribusi monitor
  persepsi datang dari skor **tingkat citra** (densitas fitur), bukan dari energi per deteksi.

### T10. OOD terdeteksi sempurna, tetapi itu tidak sama dengan memprediksi kegagalan (Terbukti)
- Bukti: Mahalanobis fitur neck: AUROC deteksi OOD **1,00**, tetapi AUROC prediksi kegagalan **0,83**.
  kNN: 0,99 vs 0,57. Kecerahan: 0,75 vs 0,50.
- Dampak: persis peringatan Guérin dkk. [15] yang kamu kutip. Ini argumen kuat untuk memakai AUROC-kegagalan
  sebagai metrik utama (Tabel 2.4). Jadikan temuan ini bagian dari Bab IV nanti.

### T11. Penggelapan sintetis bukan pengganti malam CARLA (Terbukti)
- Bukti: penggelapan 3 tingkat hanya menaikkan kegagalan dari 17% ke 25–28%, sedangkan malam CARLA milik Dika
  menurunkan frame berdeteksi dari 47% ke 16%. Kabut dan blur sintetis jauh lebih merusak.
- Dampak: jangan pakai hasil "gelap" offline sebagai bukti untuk A1. Kondisi malam harus dari render CARLA
  dengan lampu kendaraan.

### T12. Perilaku `model_best.h5`: bereaksi dekat, ragu saat jauh (Terbukti untuk state sintetis)
- Bukti: `03_cek_dqn/hasil_cek_dqn.md` dan `hasil_sapuan_jarak.md`. Bobot termuat di TF 2.21 / Keras 3
  (berkas disimpan Keras 2.10). Agen baru belok saat lubang berjarak 6–8 m (≈3–4 s pada 7 km/jam).
  Saat lubang masih jauh, selisih nilai-Q aksi terbaik dan kedua hanya ~1 dari nilai ~15. Di lajur kiri tanpa
  lubang, agen selalu memilih kanan (kembali ke lajur spawn).
- Dampak: pada 20–30 km/jam (C2), 8 m hanya 1,0–1,4 s, sehingga C2 hampir pasti gagal. Ini bagus untuk H3.
  Margin-Q yang kecil juga memberi sinyal awal bahwa monitor keputusan berbasis margin/energi-Q punya bahan.

### T13. Log cerah Dika tidak berisi satu pun aksi STRAIGHT (Terbukti; penyebab terjelaskan sebagian oleh T19)
- Bukti: `cerah.csv`: LEFT 2.550, RIGHT 354, STRAIGHT 0. `hujan.csv` dan `malam.csv` didominasi STRAIGHT.
  `model_best.h5` pada state sintetis "lajur kanan tanpa lubang" memilih KIRI, sedangkan
  `model_episode_300.h5` memilih LURUS.
- Dampak: ada kemungkinan log cerah dan log hujan/malam berasal dari checkpoint atau versi kode yang berbeda.
  Tanyakan ke Dika sebelum memakai ketiga angka itu sebagai satu baseline.

### T14. Ukuran dan severity lubang di ground truth Dika adalah estimasi (Terbukti)
- Bukti: `groundtruth_pothole.py` menulis "Diukur dari grid foto (1 kotak = 1 m)". Skrip itu memberi label
  Medium pada sebagian lubang, tetapi `pothole_gt.json` yang dipakai mencatat **19/19 High** dengan ukuran sama
  (2 m × 3 m). Berkas cadangan berisi 39 lubang, 15 di antaranya Medium dengan ukuran lain.
- Dampak: label kontak roda hanya seakurat ground truth-nya. Ukur ulang dari peta dengan `alat_carla/ukur_geometri.py`.

### T15. Kamera dan YOLO Retta berbeda dari Dika (Terbukti)
- Bukti: `Prompt.txt` Retta: kamera FOV 120°, 1600×900, pitch −15°, YOLO `yolo11n_150e_9k_gpu`, kecepatan 3,5 km/jam,
  peta `TownRetta`. Dika: FOV 90°, 640×640, YOLO11s (`best.pt` / `best_pure.pt`), ~7 km/jam, peta `train_fix`.
- Dampak: model proyeksi kamera dari makalah Retta tidak bisa dipakai apa adanya untuk stack Dika. Kedua preset
  sudah disiapkan di `05_proyeksi_kamera/proyeksi_kamera.py`. Opsi B (fallback Retta) butuh YOLO Retta sendiri.

---

## D. Temuan setelah folder lengkap diunduh (siang)

### T16. `best_pure.pt` identik dengan `best.pt` (Terbukti) — penghalang pertama selesai
- Bukti: SHA-256 `TA_Dika\VS_Code\DQN_Akselerasi vertikal\Yolo\best_pure.pt` = `best.pt` = `7b6b44f3…47bb`.
  `Agen DRL\Yolo\best_pure.pt` (versi lama) berbeda (`3bb64fb3…`); jangan tertukar.
- Dampak: semua hasil `04_monitor_persepsi` berlaku untuk YOLO yang benar-benar dipakai agen. T3 dan T4 kini terbukti
  untuk stack asli Dika: deteksi High masuk ke state sebagai 0,3.

### T17. Lubang di peta Dika adalah gambar PNG di atas bidang datar, bukan cekungan (Terbukti)
- Bukti: Bab III laporan Dika: citra PNG dengan material *Translucent* di *Plane Static Mesh*, dinaikkan 0,05 m di atas
  aspal. Asetnya ada di `TA_Dika\Jalan\Pothole asset\` (`high.png`, `med.png`, ...).
- Dampak: (a) **LiDAR Retta tidak bisa melihat lubang ini**, karena metodenya mencari cekungan. Opsi B (fallback Retta)
  tidak berlaku di peta Dika. (b) Tidak ada guncangan fisik saat roda melewati lubang, jadi data akselerasi vertikal tidak
  mencerminkan benturan. Proksi energi tumbukan di proposal memang harus dihitung dari label, bukan dari IMU.
  (c) Ukuran lubang = ukuran plane di peta, jadi bisa diukur dengan `alat_carla/ukur_geometri.py`.

### T18. Kedua peta (Dika dan Retta) hanya bisa dijalankan dari CARLA *source build* (Terbukti)
- Bukti: catatan Retta `LIDAR CARLA\aktifin yolo.txt`: `cd /d D:\carla`, `make launch`, lalu skrip dengan `--map current`.
  Peta Dika hanya ada sebagai `train_fix.umap`/`.uasset`. Tidak ada `CarlaUE4.exe` atau berkas `.pak` di folder mana pun.
- Dampak: R1 di proposal lebih serius dari perkiraan. Jalur cadangan yang realistis adalah CARLA 0.9.15 versi paket
  + jalan dari `lurus.xodr` + lubang dimunculkan lewat API. Peta Dika hanya bisa dipakai lewat PC lab atau dengan
  membangun CARLA dari sumber (±130 GB, beberapa jam, butuh UE4 versi CARLA). Lihat `alat_carla/SETUP_ENV.md`.

### T19. `cerah.csv` dan `cerah.mp4` berasal dari dua run berbeda (Terbukti)
- Bukti: di langkah 1501, video menunjukkan STRAIGHT, total reward +775,2, Avoids 10; CSV menunjukkan LEFT, +726,2, Avoids 9.
  Panjang 2.883 vs 2.904 langkah. Untuk hujan dan malam, video dan CSV cocok 100%.
- Dampak: (a) T13 terjelaskan sebagian: CSV cerah memang run lain. (b) Dua run cerah dari titik awal yang sama memberi
  urutan aksi berbeda, jadi simulasi Dika **tidak deterministik** walau epsilon 0. Ini memperkuat alasan evaluasi ulang
  30 episode.

### T20. Pada malam hari, agen hanya melihat 6% lubang yang ada di depannya (Terbukti, data asli)
- Bukti: `07_rekaman_dika/HASIL.md`. Saat ada lubang 3–15 m di depan, YOLO agen mendeteksi pada 59% frame cerah,
  50% hujan, 6% malam (pembagian alternatif: 68/54/22%). Hujan juga menaikkan deteksi palsu: 32% frame tanpa lubang
  tetap "terdeteksi", dibanding 10% di cerah.
- Dampak: angka ini lebih tepat untuk Bab I dan Tabel 2.2 daripada "47/43/16% frame berdeteksi". Hujan dan malam
  gagal dengan cara berbeda (deteksi palsu vs deteksi terlewat), yang mendukung taksonomi kegagalan di proposal.

### T21. Monitor tingkat citra mendeteksi KONDISI, bukan frame yang gagal (Terbukti, data asli)
- Bukti: Mahalanobis fitur neck: AUROC OOD 1,00 untuk hujan dan malam, alarm palsu di cerah 6%. Tetapi AUROC prediksi
  kegagalan **di dalam satu kondisi** ≈ 0,45–0,50. Statistik kecerahan menyamai atau mengalahkannya (OOD 0,98–1,00;
  kegagalan gabungan 0,76 vs 0,69).
- Dampak: H1 hanya didukung untuk deteksi OOD, dan di situ kecerahan sama baiknya. Target S2 ("AUROC-kegagalan ≥ 0,85 dan
  lebih baik dari kecerahan") **tidak akan tercapai** dengan definisi per frame. Dua perubahan yang perlu dibahas dengan
  dosbing: (1) label kegagalan per lintasan lubang, bukan per frame; (2) skenario yang tidak mengubah kecerahan
  (kabut tipis, blur, kaca buram, tampilan lubang baru) supaya nilai tambah monitor bisa ditunjukkan.

### T22. Monitor tidak boleh di-fit pada data latih YOLO (Terbukti)
- Bukti: `07_rekaman_dika/hasil/domain_gap.json`. Fit pada 59 foto jalan nyata, kalibrasi pada 32 foto lain: alarm pada
  100% frame CARLA, termasuk cerah (median skor 58 vs ambang 16).
- Dampak: Subbab 2.1.6 dan Daftar Istilah mendefinisikan densitas fitur sebagai jarak ke "data pelatihan". Ganti menjadi
  jarak ke frame CARLA kondisi ID-0.

### T23. Waktu peringatan dini tidak bisa diukur dari episode yang kondisinya konstan (Terbukti)
- Bukti: di hujan dan malam monitor menyala sepanjang episode, sehingga "peringatan" sebelum 13 HIT selalu 6 s penuh.
- Dampak: untuk metrik waktu peringatan (Tabel 2.4), runner skenario perlu membuat **transisi** di tengah episode
  (kabut menebal, masuk ruas gelap, hujan mulai).

### T24. Dataset dan YOLO Retta tersedia, berbeda dari milik Dika (Terbukti)
- Bukti: `Retta\carla_work\datasets_yolo_9k`: 8.652 citra latih + 961 validasi, kelas aman/sedang/parah. YOLO Retta:
  `yolo11n`, imgsz 640. YOLO Dika: `yolo11s`, imgsz 768, data latih di `TrainYolo` yang **tidak ada** di folder.
  Wheel CARLA client `carla-0.9.15-cp37` ada di `Retta\PythonAPI\carla\dist`.
- Dampak: untuk menyiapkan environment, ikuti `alat_carla/SETUP_ENV.md`. Wheel CARLA di folder Retta hanya untuk
  Python 3.7, sedangkan Ultralytics butuh ≥ 3.8; itu sebabnya Retta memakai dua environment.
