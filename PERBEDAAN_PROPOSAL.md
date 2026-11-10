# Perbedaan proposal TA dengan temuan 7–8 November 2026

Dibandingkan dengan: `Proposal_TA_13323035_Muhammad_Keva_Rafferty.pdf` (versi Oktober 2026, 37 halaman).
Nomor subbab dan tabel di bawah mengikuti PDF tersebut. Catatan: `TEMUAN.md` ditulis sebelum PDF ini diterima,
sehingga beberapa nomor di sana merujuk versi lama (misalnya label kegagalan ada di §2.1.2, bukan §2.1.3;
monitor persepsi di §2.1.5; metrik di Tabel 2.3; aset di Tabel 2.5).

Kode T = nomor temuan di `TEMUAN.md`.

## A. Perlu keputusan dosbing (penghalang)

| # | Bagian | Tertulis di proposal | Kenyataan | Usulan perubahan |
|---|---|---|---|---|
| 1 | §2.1.1, Gate 1, R2 | Reproduksi 100/84/47 (±10 poin) di lingkungan asli Dika | Peta `train_fix` hanya bisa dibuka dari CARLA source build (PC lab). Opsi generator (b) di §2.1.2 juga butuh itu (T2, T18) | Gate 1 baru: 19 lubang dari `pothole_gt.json` dibangun ulang di CARLA 0.9.15 paket, π_Dika dievaluasi 30 episode, hasilnya **baseline baru** |
| 2 | Tabel 1.3 (S2) | AUROC-kegagalan ≥ 0,85 dan lebih baik dari MSP serta kecerahan | Pada 8.505 frame asli Dika: deteksi kondisi OOD = 1,00, tetapi prediksi frame gagal di dalam satu kondisi ≈ 0,45–0,50. Kecerahan sama baiknya (T21) | Label kegagalan per **lintasan lubang**, bukan per frame. Tambah skenario yang tidak mengubah kecerahan (kabut tipis, blur, tampilan lubang baru) |
| 3 | §2.1.2 (label persepsi) | Gagal jika lubang High diklasifikasikan sebagai Low | `best_pure.pt` memberi kelas Low pada 43 dari 44 lubang CARLA. Label ini akan bernilai 1 di hampir semua frame (T4) | Pisahkan: kegagalan deteksi (dipakai sebagai label), salah keparahan (dilaporkan sebagai temuan domain gap) |
| 4 | §2.1.7 Opsi B, Batasan 2, Tabel 2.5–2.6 | Fallback ke pengendali LiDAR Retta | Lubang Dika adalah gambar PNG di plane datar. LiDAR tidak bisa melihatnya (T17) | Hapus Opsi B, atau buat lubang 3D sendiri (pekerjaan tambahan) |
| 5 | Abstrak, §1.5 | Densitas fitur = jarak ke "distribusi pelatihan" | Jika di-fit pada foto jalan nyata, alarm menyala di 100% frame CARLA, termasuk cerah (T22) | Tulis eksplisit: jarak ke frame CARLA kondisi ID-0 |

## B. Hipotesis, target, dan metrik yang berisiko

| # | Bagian | Tertulis di proposal | Kenyataan | Usulan perubahan |
|---|---|---|---|---|
| 6 | H1 (bagian kedua) | Energi per deteksi lebih baik untuk menandai salah kelas keparahan | Tidak bisa diuji, karena keparahan hampir selalu Low (T4). Energi ≈ MSP (AUROC 0,923 vs 0,924) (T9) | Ubah H1, atau tandai bagian itu sebagai eksploratif |
| 7 | H2 | Monitor persepsi bernilai tinggi pada A1 dan A2 | Tinggi untuk mendeteksi kondisi, tidak untuk frame yang gagal (T21) | Rumuskan ulang mengikuti #2 |
| 8 | Tabel 2.11 R4 | Peluang monitor kalah dari pembanding: Sedang | Sudah terjadi pada data Dika (T21) | Naikkan ke Tinggi, siapkan narasi "temuan" |
| 9 | Tabel 2.3 (waktu peringatan) | t_kontak − t_alarm | Pada kondisi konstan alarm menyala sejak awal, sehingga waktu peringatan selalu penuh (T23) | Runner membuat transisi di tengah episode (kabut menebal, masuk ruas gelap) |
| 10 | Tabel 2.3 (ISO 2631, jerk vertikal) | Sebanding dengan Dika dan Retta | Lubang datar tidak menimbulkan guncangan, sehingga a_v hanya mencerminkan manuver belok (T17) | Sebut sebagai kenyamanan manuver, atau pakai lubang 3D |

## C. Status aset yang sudah usang

| # | Bagian | Tertulis di proposal | Kenyataan | Usulan perubahan |
|---|---|---|---|---|
| 11 | Tabel 2.5, R1 | Agen DQN: belum tersedia | Ada, termuat di TF 2.21, perilakunya sudah diukur (T12) | Perbarui status. R1 diganti risiko peta/lingkungan |
| 12 | Tabel 2.5 | YOLO best.pt: diterima, terverifikasi | Identik dengan `best_pure.pt` (T16), tetapi kode Dika memetakan High menjadi 0,3 (T3) | Tambah catatan; tunggu jawaban Dika (pesan butir 3) |
| 13 | Tabel 2.5 | Peta: aset tekstur lubang masih dibutuhkan | Tekstur sudah ditemukan (`high.png` dll.). Yang kurang tinggal source build (T17, T18) | Perbarui status |
| 14 | Tabel 2.5, §2.1.2 | Model proyeksi kamera sama dengan Retta | Kamera Retta FOV 120°, 1600×900. Kamera Dika FOV 90°, 640×640 (T15) | Pakai parameter kamera Dika (sudah ada di `05_proyeksi_kamera`) |
| 15 | Tabel 2.8 | Versi Python disesuaikan dengan wheel CARLA | Wheel CARLA di folder Retta hanya untuk Python 3.7, sedangkan Ultralytics butuh ≥ 3.8 (T24) | Ikuti `alat_carla/SETUP_ENV.md` |

## D. Fakta dan jadwal

| # | Bagian | Tertulis di proposal | Kenyataan | Usulan perubahan |
|---|---|---|---|---|
| 16 | §2.1.2 | Lintasan tetap sepanjang 27 m dengan 19 lubang | Di `pothole_gt.json` lubang tersebar sepanjang ±250 m (x −285 s.d. −35) | Perbaiki angkanya (cek laporan Dika) |
| 17 | Abstrak, §1.1 | 47% malam disajikan sebagai kinerja agen | 47% sama persis dengan mobil yang tidak pernah menghindar (T5). Saat malam agen hanya mendeteksi 6% lubang di depannya (T20) | Tambahkan; ini memperkuat argumen *silent failure* |
| 18 | Tabel 2.9 no. 0, Gate 1 (akhir N2 = 15 Nov) | CARLA terpasang di bulan Oktober | CARLA belum terpasang per 8 Nov | Gate 1 hampir pasti mundur. Minta jadwal baru bersama keputusan #1 |
| 19 | Daftar Tabel, halaman pengesahan | — | Tabel 1.3 muncul sebelum Tabel 1.2; Pembimbing 2 belum diisi | Perbaiki saat revisi berikutnya |

## Yang tetap berlaku atau justru diperkuat

- Label kontak roda menggantikan "lubang < 3 m" (§2.1.2): bug logika Dika terbukti dengan angka (T6, T7).
- Logit per deteksi bisa diambil tanpa mengubah YOLO (§2.1.5): terverifikasi pada 689 inferensi (T8).
- C2 (20–30 km/jam) kemungkinan besar gagal karena agen baru bereaksi di 6–8 m (T12). Ini baik untuk H3.
- Evaluasi 30 episode memang perlu, karena simulasi Dika tidak deterministik (T19).
- Metrik utama AUROC-kegagalan, bukan AUROC-OOD (Tabel 2.3): T10 dan T21 menunjukkan keduanya bisa sangat berbeda.

---

## E. Pembaruan setelah kunjungan lab, 10 November 2026

Sumber: `LOG_KERJA.md` entri 10 Nov sore, `08_kunjungan_lab/`, `alat_carla/geometri_terukur.json`.
Ringkasan: 25 butir (19 lama + 6 baru). Butir #13 dan #15 selesai. Butir #1, #3, #6, #16, #18 berubah isi.

### Status butir lama yang berubah

| # | Status baru |
|---|---|
| 1 | Arah berbalik. Peta asli bisa dipakai lagi lewat source build CARLA 0.9.15 di laptop (jalur B). Keputusan dosbing yang tersisa: **kriteria dan jadwal Gate 1** (lihat E3) |
| 3, 6 | Kemungkinan bukan *domain gap*. Lihat E6 |
| 13 | **Selesai.** `train_fix*`, `Aset_Lubang`, `OpenDrive` sudah disalin dari PC lab (masih di SSD) |
| 15 | **Selesai.** Ekspor 9 environment conda ada di `08_kunjungan_lab/hasil_lab/` |
| 16 | Diperjelas: jalan di peta ±400 m (x −285 s.d. +117); GT hanya mencakup x −285 s.d. −35 |
| 18 | Masih penghalang, alasan berganti: source build di laptop butuh berjam-jam dan ±130–165 GB disk |
| 11 | Tambahkan di Tabel 2.5: agen yang dipakai adalah `DQN_Akselerasi vertikal/model_best.h5`, **bukan** folder `Agen DRL` (`model_episode_800.h5`, YOLO lain) |

### Butir baru

| # | Bagian | Tertulis di proposal | Kenyataan | Usulan perubahan |
|---|---|---|---|---|
| E1 | Tabel 1.1, R2 | Dika memakai CARLA 0.9.14; risiko beda versi | Build lab = **0.9.15** (UE4 fork `e22f1e2`). "dirty" hanya 4 perbaikan URL unduhan | Koreksi Tabel 1.1; hapus R2 |
| E2 | Batasan 1, Tabel 2.8, R3, Tabel 2.12 | CARLA 0.9.15 paket Windows | `train_fix` hanya ada di source build; `make package` di lab gagal (disk D: 3,8 GB, C: 4,2 GB) | Tulis: source build sekali → package → eksperimen di versi paket. Tambah kebutuhan disk ke R3 |
| E3 | §2.1.1, Gate 1 | Tereproduksi jika selisih ≤ ±10 poin | Run malam di lab: **7/19 (36,8%)** vs Dika 9/19 (47,4%), selisih 10,5 poin dari **1 episode**, kode dan model identik (hash sama) | Kriteria baru berbasis ≥ 30 episode per kondisi + selang kepercayaan 95% |
| E4 | Abstrak, §1.1 | 47% malam = kinerja agen | 7/19 < 9/19 mobil lurus tanpa menghindar. Agen bisa **lebih buruk** daripada tidak bereaksi | Pakai hanya setelah dikonfirmasi 30 episode **dan** pelabel roda memakai geometri terukur (E7) |
| E5 | §2.1.2, label | GT Dika dianggap lengkap | Hanya 11 dari 19 entri GT cocok dengan objek `hole_low*` yang terukur. 8 entri GT bernama `med_samping detect*` tidak tertangkap kata kunci pengukuran. 7 objek `hole_low*` (x −7 s.d. +117) tidak ada di GT. Peta berisi ≥ 26 lubang | Ukur ulang semua objek lubang (tambah kata kunci `med`, `samping`, `detect`) dan bangun GT sendiri dari peta |
| E6 | §2.1.2, H1, butir #3 | YOLO salah membaca High sebagai Low (*domain gap*) | Semua lubang GT berlabel **High**, padahal 11 objek yang cocok bernama `hole_low*` dan peta mereferensikan material `Aset_Lubang/Low`. **Dugaan:** YOLO benar, label GT yang keliru | Cek material tiap objek di editor. Jika benar, butir #3 dan #6 berubah dari "temuan domain gap" menjadi "koreksi GT"; label keparahan mungkin bisa dipakai lagi |

### Bukan perubahan teks proposal, tetapi mengubah angka

- E7. Geometri Microlino terukur: jejak roda depan 1,19 m, belakang **0,72 m** (estimasi lama 1,20 m untuk keduanya); sumbu depan +0,684 m, belakang −0,841 m; jari-jari ban 0,25 m. Angka T5 (9/19 mobil lurus) dan T6 (rentang 1,84–2,16 m) harus dihitung ulang.
