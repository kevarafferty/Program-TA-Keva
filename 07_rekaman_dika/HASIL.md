# Monitor persepsi pada frame CARLA asli (rekaman uji Dika)

**Status:** selesai sebagai analisis *open-loop*. Ini data CARLA asli dari lingkungan Dika
(peta `train_fix`, kamera agen, YOLO `best_pure.pt`), bukan gangguan sintetis seperti di `04_monitor_persepsi`.
Tetap ada batasan penting; baca bagian **Batasan** sebelum mengutip angka.

## Sumber data

`TA_Dika\VS_Code\DQN_Akselerasi vertikal\recordings\{cerah,hujan,malam}.mp4`, ditulis `cleanTest.py`:
satu frame per langkah (20 fps, 640×640), total **8.505 frame**. Di atasnya ada overlay teks dan kotak deteksi.

| Hal yang dibaca | Cara | Validasi |
|---|---|---|
| Citra yang dilihat YOLO agen | Tukar kanal kembali (cleanTest menukar RGB/BGR), panel kiri dikali 2 | Lihat batasan 1 |
| Status deteksi YOLO agen per frame | Baris "Severity" di overlay hanya ada jika terdeteksi | **Sama 100%** dengan kolom `pothole_detected` di CSV hujan dan malam |
| Posisi x kendaraan | Jangkar: momen Hits/Avoids naik = mobil melewati lubang ke-j (posisi diketahui dari `pothole_gt.json`); di antaranya interpolasi | Hujan, malam: dari CSV run yang sama. Cerah: 19/19 jangkar cocok dengan overlay video |
| Fitur neck + logit YOLO | `ekstrak_rekaman.py` dengan hook dari `04_monitor_persepsi` | — |

**Label gagal** = ada pusat lubang 3–15 m di depan kendaraan, tetapi YOLO agen tidak mendeteksi apa pun.

**Pembagian data (utama, "selang-seling")**: lintasan dibagi blok 10 m. Blok mod 3 = 0 dipakai untuk fit
(hanya cerah), mod 3 = 1 untuk kalibrasi ambang p95 (hanya cerah), mod 3 = 2 untuk uji (ketiga kondisi).
Pembagian kedua ("paruh") melatih di paruh pertama lintasan dan menguji di paruh kedua, untuk melihat
apakah monitor tetap berlaku di ruas jalan yang belum pernah dilihat. Bootstrap per lintasan lubang.

## Berkas

| Berkas | Isi |
|---|---|
| `ekstrak_rekaman.py` | Video → citra yang dipulihkan, status deteksi agen, fitur dan logit YOLO per frame |
| `baca_penghitung.py` | Membaca perubahan penghitung Hits/Avoids dari warna teks overlay |
| `analisis_rekaman.py` | Label, pembagian data, skor, AUROC, laju alarm, grafik |
| `cek_domain_gap.py` | Jarak frame CARLA ke foto jalan nyata (sampel 91 citra validasi dataset 9k) |
| `data/*.npz` | Hasil ekstraksi per frame (agar analisis bisa diulang tanpa YOLO, ±10 menit) |
| `hasil/` | Pembagian selang-seling: `ringkasan_rekaman.json`, `skor_sepanjang_lintasan.png`, `domain_gap.json` |
| `hasil_paruh/` | Pembagian paruh lintasan |

## Hasil

### Selang-seling (utama): fit 981 frame, kalibrasi ambang 969 frame, PCA 48 komponen

| Kondisi | Frame uji | Agen mendeteksi saat ada lubang 3–15 m | Agen mendeteksi saat tidak ada lubang | Deteksi ulang sepakat dgn agen | Alarm Mahalanobis | Alarm kecerahan |
|---|---:|---:|---:|---:|---:|---:|
| cerah | 933 | 59% | 10% | 41% | 6% | 25% |
| hujan | 933 | 50% | 32% | 46% | 100% | 100% |
| malam | 869 | 6% | 4% | 90% | 100% | 100% |

| Skor | OOD hujan vs cerah | OOD malam vs cerah | Kegagalan (gabungan) | Kegagalan dalam cerah | dalam hujan | dalam malam |
|---|---|---|---|---:|---:|---:|
| mahalanobis | 1.00 [1.00–1.00] | 1.00 [1.00–1.00] | 0.69 [0.60–0.77] | 0.50 | 0.49 | 0.45 |
| knn | 0.84 [0.74–0.92] | 0.99 [0.98–1.00] | 0.69 [0.59–0.79] | 0.47 | 0.45 | 0.57 |
| kecerahan | 0.98 [0.95–1.00] | 1.00 [1.00–1.00] | 0.76 [0.68–0.83] | 0.68 | 0.50 | 0.46 |
| jointenergy_citra | 0.32 [0.23–0.40] | 0.81 [0.70–0.90] | 0.48 [0.34–0.61] | 0.19 | 0.37 | 0.36 |

Kegagalan gabungan: 2125 frame dengan lubang 3–15 m, 1296 di antaranya tidak terdeteksi agen. Per kondisi: cerah 299/724, hujan 366/731, malam 631/670.

- Kelas deteksi ulang cerah: {'Low': 107, 'Medium': 75, 'High': 1}
- Kelas deteksi ulang hujan: {'Low': 263, 'Medium': 5, 'High': 0}
- Kelas deteksi ulang malam: {'Low': 41, 'Medium': 2, 'High': 0}

### Paruh lintasan: fit 1465 frame, kalibrasi ambang 729 frame, PCA 62 komponen

| Kondisi | Frame uji | Agen mendeteksi saat ada lubang 3–15 m | Agen mendeteksi saat tidak ada lubang | Deteksi ulang sepakat dgn agen | Alarm Mahalanobis | Alarm kecerahan |
|---|---:|---:|---:|---:|---:|---:|
| cerah | 689 | 68% | 11% | 44% | 11% | 12% |
| hujan | 708 | 54% | 27% | 48% | 100% | 100% |
| malam | 637 | 22% | 4% | 79% | 100% | 100% |

| Skor | OOD hujan vs cerah | OOD malam vs cerah | Kegagalan (gabungan) | Kegagalan dalam cerah | dalam hujan | dalam malam |
|---|---|---|---|---:|---:|---:|
| mahalanobis | 1.00 [1.00–1.00] | 1.00 [1.00–1.00] | 0.66 [0.53–0.77] | 0.48 | 0.46 | 0.24 |
| knn | 0.72 [0.63–0.83] | 0.95 [0.92–0.98] | 0.65 [0.53–0.76] | 0.50 | 0.42 | 0.63 |
| kecerahan | 0.99 [0.97–1.00] | 1.00 [1.00–1.00] | 0.73 [0.61–0.84] | 0.74 | 0.55 | 0.50 |
| jointenergy_citra | 0.24 [0.16–0.33] | 0.88 [0.75–0.96] | 0.52 [0.39–0.65] | 0.34 | 0.39 | 0.46 |

Kegagalan gabungan: 1359 frame dengan lubang 3–15 m, 696 di antaranya tidak terdeteksi agen. Per kondisi: cerah 146/462, hujan 218/473, malam 332/424.

- Kelas deteksi ulang cerah: {'Low': 73, 'Medium': 15, 'High': 0}
- Kelas deteksi ulang hujan: {'Low': 180, 'Medium': 11, 'High': 1}
- Kelas deteksi ulang malam: {'Low': 32, 'Medium': 2, 'High': 0}

### Jarak ke foto jalan nyata (`hasil/domain_gap.json`)

Monitor Mahalanobis yang di-fit pada 59 foto jalan nyata dan dikalibrasi pada 32 foto lain (ambang p95 = 15,9)
menyala pada **100% frame CARLA**, termasuk cerah (median skor cerah 58, hujan 92, malam 67; median foto nyata 8,4).

## Yang bisa disimpulkan

1. **Angka kegagalan persepsi yang sebenarnya.** Saat ada lubang 3–15 m di depan, YOLO agen mendeteksinya pada
   59% frame cerah, 50% hujan, dan **6% malam** (pembagian paruh: 68%, 54%, 22%). Ini lebih tepat daripada angka
   "47/43/16% frame berdeteksi" di laporan Dika, yang dihitung atas semua frame tanpa melihat apakah ada lubang.
2. **Hujan menambah deteksi palsu.** Saat tidak ada lubang dalam jangkauan, agen tetap "melihat" lubang pada
   32% frame hujan, dibanding 10% cerah. Ini kategori kegagalan yang berbeda dari malam (deteksi terlewat), dan
   relevan untuk skenario B2 (pola mirip lubang).
3. **Monitor tingkat citra mendeteksi kondisinya, bukan frame yang gagal.** Mahalanobis membedakan hujan dan malam
   dari cerah dengan sempurna (AUROC 1,00) dan alarm palsu di cerah hanya 6%. Tetapi di dalam satu kondisi,
   AUROC prediksi kegagalan sekitar 0,5. Angka gabungan 0,69 hampir seluruhnya berasal dari "malam lebih sering
   gagal". Dengan kata lain, monitor ini berfungsi sebagai detektor kondisi.
4. **Kecerahan menyamai Mahalanobis.** Untuk hujan dan malam, statistik kecerahan + kontras sama baiknya untuk
   OOD (0,98–1,00) dan sedikit lebih baik untuk kegagalan gabungan (0,76 vs 0,69). Ini persis risiko yang sudah
   disebut di Subbab 2.1.6: jika monitor tidak mengalahkan kecerahan, nilai tambahnya tidak ada. Untuk
   menunjukkan nilai tambah, skenario harus mencakup gangguan yang tidak mengubah kecerahan (kabut tipis, blur,
   kaca buram, tampilan lubang baru).
5. **JointEnergy rata-rata semua anchor tidak berguna untuk hujan** (AUROC 0,32, artinya terbalik).
6. **Fit pada data latih YOLO tidak bisa dipakai.** Frame CARLA cerah sudah jauh di luar sebaran foto jalan
   nyata. Data ID untuk monitor harus frame CARLA kondisi ID-0, bukan data latih YOLO. Definisi "densitas fitur"
   di proposal perlu diubah.
7. **Kelas severity tetap salah di frame asli.** Deteksi ulang hampir tidak pernah menghasilkan High.
8. **Waktu peringatan dini belum bisa diukur.** Di hujan dan malam monitor menyala sepanjang episode, sehingga
   "peringatan" sebelum setiap HIT selalu 6 s (seluruh jendela). Angka ini tidak bermakna. Untuk mengukur waktu
   peringatan, skenario perlu memuat **transisi** di tengah episode (misalnya kabut yang menebal atau masuk ruas
   gelap) dan label kegagalan per lintasan lubang, bukan per frame.

## Batasan

1. **Kompresi video.** Video mp4v hanya ±13 KB per frame. YOLO yang dijalankan ulang pada frame ini hanya
   sepakat 41–46% dengan deteksi agen di cerah dan hujan (malam 90% karena keduanya hampir selalu "tidak ada").
   Karena itu **skor per deteksi (MSP, energi, JointEnergy per kotak) tidak dilaporkan dari data ini**. Skor
   tingkat citra tetap dipakai karena kompresinya sama di ketiga kondisi, tetapi nilainya bisa berbeda dari skor
   pada citra asli tanpa kompresi.
2. **Overlay tidak bisa dihapus seluruhnya.** Teks dan kotak deteksi tetap ada di citra. Statistik kecerahan
   dihitung hanya dari area tanpa panel (x > 300).
3. **Satu episode per kondisi**, dengan rute dan pemandangan yang sama. Frame berurutan saling bergantung,
   sehingga selang kepercayaan dihitung dengan bootstrap per lintasan lubang.
4. **Posisi lateral (y) tidak diketahui**, sehingga label "dalam jangkauan" tidak membedakan lajur. Label
   kontak roda tidak bisa dihitung dari data ini.
5. **Video cerah dan CSV cerah berasal dari run yang berbeda** (T19). Untuk cerah, posisi x diperoleh dari
   overlay video dengan bantuan pola waktu run lain.
