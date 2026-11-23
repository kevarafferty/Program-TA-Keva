# Pelabel kegagalan + analisis skenario (ditulis Claude, 22 Nov 2026)

Tidak butuh CARLA. Bisa dijalankan kapan saja setelah ada run di `log_skenario\`, termasuk saat laptop menjalankan run lain.

## Berkas
| Berkas | Fungsi |
|---|---|
| `label_kegagalan.py` | Label per langkah dan per lintasan lubang dari log runner (memakai `02_pelabel_roda/kontak_roda.py` dan `05_proyeksi_kamera/proyeksi_kamera.py`) |
| `analisis_skenario.py` | Label semua run, ringkasan per kondisi + CI 95%, uji regresi REG vs baseline #21–#22, laporan |
| `tests/test_label.py` | 5 uji dengan lintasan dan deteksi sintetis |

## Langkah malam ini: REG di build baru (±3,5–4 jam)
Build spawn (22 Nov) sekarang build tetap untuk semua data berikutnya. CarlaUE4.exe baru, tanpa `-quality-level`:
```
python jalankan_matriks.py --kondisi REG:1:konstan REG:2:konstan REG:3:konstan
```

## Besok pagi: analisis (±3 menit)
```
python cek_kualitas_run.py --run log_skenario\*REG*
python analisis_skenario.py
```
Buka `hasil_analisis\laporan.md`. Bagian **Uji regresi REG** harus menulis **SETARA** untuk ketiga kondisi
(CI 95% selisih REG − baseline mencakup 0 untuk metrik roda utama, logika Dika, dan episode gagal).
Kirim `laporan.md` ke Claude. Kalau ada yang TIDAK SETARA, jangan lanjut ke #26 dulu.

Acuan baseline (dihitung ulang oleh skrip ini dari data #21–#22, sama dengan HASIL_BASELINE.md):
| | Roda utama | Logika Dika | Episode gagal |
|---|---|---|---|
| ClearNoon | 94,4 [93,9–94,7] | 99,5 [98,9–100] | 6,7% (2/30) |
| HardRainNoon | 54,6 [47,2–61,4] | 71,8 [63,5–79,1] | 66,7% (20/30) |
| ClearNight | 17,0 [15,1–19,1] | 36,1 [33,2–39,3] | 0% |

## Label yang dihasilkan
Per run, per episode: `label_ep###_seed#.npz` (per langkah, sejajar baris `langkah_*.csv`) dan `lintasan_ep###_seed#.csv` (per lubang).

| Label | Arti | Dipakai untuk |
|---|---|---|
| `kontak_H` (per langkah) | ada kontak roda–lubang Medium/High dalam 2 s ke depan | monitor keputusan U_D (#30) |
| `gagal_persepsi` (per lintasan) | kotak teratas YOLO cocok (IoU ≥ 0,3) dengan lubang di < 50% frame saat lubang tampak 3–15 m di depan | monitor persepsi U_P (#29), sesuai T21 |
| `terlambat` (per lintasan) | lubang tidak pernah cocok saat masih ≥ 8 m (agen baru bereaksi di 6–8 m, T12) | analisis waktu peringatan |
| `gagal_persepsi` (per langkah) | ada lubang target 3–15 m tetapi kotak teratas tidak cocok (−1 = tidak ada target) | pembanding label per frame (T21) |
| `palsu_top` (per langkah) | kotak teratas tidak mengenai lubang mana pun yang tampak | deteksi palsu (hujan) |
| `status` (per lintasan) | kontak / terhindar / tak_tercapai | metrik roda utama |

## Validasi yang sudah dilakukan
1. **Proyeksi kamera** (pertama kali dicek pada citra CARLA asli): C1 t1 cerah, IoU ≥ 0,3 pada 86% frame berlubang 3–15 m, selisih pusat kotak median 1,4 px / 0,1 px.
2. **Baseline tereproduksi persis**: metrik roda 94,4 / 54,6 / 17,0%, episode gagal 2 / 20 / 0 dari 30 (sama dengan HASIL_BASELINE.md).
3. C1 t1: hanya ph_0010 yang tersentuh, sama dengan baseline (30/30).

## Keputusan yang perlu disetujui (bawa ke dosbing)
- IoU minimum 0,3; jangkauan 3–15 m; horizon H = 2 s (proposal).
- **Ambang `gagal_persepsi` per lintasan = 50% frame** dan **`terlambat` = 8 m**: dipilih setelah melihat 1 episode uji per kondisi (cerah 77–100%, malam 4–61%, silau 14–51%, blur 0–11%). Hitungan mentah disimpan, jadi analisis sensitivitas ambang wajib dilaporkan di Bab IV.
- Setengah lebar ban 0,075 m masih estimasi (semua kendaraan).
- B1/B2 dipindah ke saran penelitian lanjutan.
