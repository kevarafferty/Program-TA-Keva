# Monitor persepsi — studi pendahuluan offline

**Status:** selesai sebagai studi pendahuluan. Bukan hasil akhir TA.
**Data:** 53 citra CARLA milik Dika (`VS_Code/YOLO/CARLA`), 56 lubang, semuanya berlabel High.
**Model:** `best.pt` (YOLO11s, 3 kelas) dengan pengaturan Dika: `imgsz=320`, `conf=0.05`.

## Berkas

| Berkas | Isi |
|---|---|
| `yolo_logit_hook.py` | Kelas `YoloDenganLogit`: logit per deteksi, logit semua anchor, fitur neck. Juga fungsi skor `joint_energy`, `energi`, `msp_sigmoid`, `max_logit`. |
| `verifikasi_hook.py` | Membuktikan hook identik dengan `predict()` pada 689 inferensi. |
| `prototipe_monitor_persepsi.py` | Gangguan citra, label kegagalan, semua skor, AUROC dengan bootstrap. |
| `hasil/ringkasan.json` | Semua angka di bawah. |
| `hasil/rekaman_per_citra.json` | Satu baris per (citra, kondisi): deteksi, label, semua skor. |
| `hasil/contoh_gangguan.jpg` | Satu citra pada 13 kondisi. Hijau = label, merah = kotak teratas YOLO. |

## Cara kerja singkat

1. Setiap citra diberi 4 gangguan × 3 tingkat: gelap, blur, kabut, derau. Ditambah versi bersih, total 13 kondisi.
2. **Label gagal** per citra: kotak dengan conf tertinggi (satu-satunya yang dilihat agen DQN) tidak mengenai lubang
   mana pun (IoU < 0,3), atau tidak ada deteksi sama sekali. IoU 0,3 dipilih karena lubangnya kecil dan jauh.
3. Citra dibagi dua (seed 13). Separuh A versi bersih (26 citra) dipakai untuk mencocokkan Mahalanobis, kNN,
   dan statistik kecerahan. Semua angka di bawah dihitung pada separuh B (27 citra × 13 kondisi = 351 sampel).
4. Selang kepercayaan 95% dari bootstrap 2.000 kali, dengan citra asal sebagai unit (13 versi dari citra yang
   sama tidak dihitung sebagai sampel independen).

## Hasil

### Tingkat kegagalan YOLO per kondisi (53 citra)

| Kondisi | Tingkat 1 | Tingkat 2 | Tingkat 3 |
|---|---:|---:|---:|
| Bersih | 17% | | |
| Gelap | 25% | 28% | 26% |
| Blur | 25% | 53% | 100% |
| Kabut | 75% | 100% | 100% |
| Derau | 17% | 17% | 68% |

Kelas kotak teratas pada citra bersih yang ada deteksinya: Low 43, Medium 1, High 0 (padahal semua lubang High).

### E1 — semua sampel (351, separuh B)

| Skor | AUROC prediksi kegagalan | AUROC deteksi OOD |
|---|---:|---:|
| MSP (1 − conf teratas) | 0,996 | 0,66 |
| MaxLogit | 0,996 | 0,66 |
| Energi per deteksi | 0,996 | 0,66 |
| JointEnergy per deteksi | 0,996 | 0,66 |
| JointEnergy rata-rata semua anchor | 0,991 | 0,66 |
| Mahalanobis fitur neck | 0,832 [0,76–0,92] | **1,00** |
| kNN fitur neck | 0,567 [0,52–0,62] | 0,99 |
| Kecerahan + kontras | 0,504 [0,45–0,56] | 0,75 |

**Jangan kutip angka 0,996 di atas sebagai bukti.** Sebagian besar kegagalan adalah "tidak ada deteksi", dan
menurut definisi itu terjadi ketika conf tertinggi < 0,05. Skor berbasis conf atau logit kotak teratas jadi
otomatis tinggi pada kasus itu. Ini sirkular. Karena itu ada E2.

### E2 — hanya sampel yang punya deteksi (188 sampel, 8 gagal)

Pertanyaannya: bisakah skor membedakan kotak teratas yang benar dari yang salah (false positive)?

| Skor | AUROC | Selang 95% |
|---|---:|---|
| MSP | 0,924 | 0,81–0,98 |
| Energi | 0,923 | 0,81–0,98 |
| JointEnergy | 0,922 | 0,80–0,98 |
| JointEnergy semua anchor | 0,867 | 0,66–0,97 |
| Mahalanobis | 0,790 | 0,66–0,96 |
| kNN | 0,701 | 0,62–0,80 |
| Kecerahan | 0,273 | 0,05–0,62 |

Hanya 8 kegagalan, jadi selangnya lebar. Yang bisa disimpulkan: tidak ada bukti energi lebih baik dari MSP.

## Apa artinya untuk proposal

- **H1** sebagian didukung: densitas fitur (Mahalanobis) jauh lebih baik untuk mendeteksi pergeseran citra
  daripada skor logit. Tetapi deteksi pergeseran ≠ prediksi kegagalan (T10 di `TEMUAN.md`).
- **S2** ("lebih baik dari MSP") berisiko. Lihat T9.
- **Penggelapan sintetis tidak meniru malam CARLA** (T11). Untuk A1 tetap butuh render malam asli.
- Pipa skor sudah lengkap. Saat data CARLA closed-loop tersedia, cukup ganti sumber citranya.

## Langkah berikutnya

1. Jalankan ulang pada frame CARLA asli (cerah/hujan/malam) setelah lingkungan berjalan.
2. Fit Mahalanobis pada ratusan frame ID-0, bukan 26 citra.
3. Coba Mahalanobis per skala (P3, P4, P5 terpisah) dan fitur di lokasi anchor kotak, bukan hanya rata-rata global.
