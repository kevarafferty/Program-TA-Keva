# Hasil baseline π_Dika (#21–#22) — kualitas Epic, 19 Nov 2026

Data: `10_runner/DQN_Akselerasi vertikal/log_runner/20261119_*_Epic/` (30 episode × 3 kondisi, seed 0–29, offset spawn ±2 m / ±0,5 m).
Ringkasan mesin: `hasil_baseline_epic.json`. GT metrik: `alat_carla/pothole_gt_v2_segmen_dika.json` (19 lubang High). CI 95% = bootstrap atas episode.

| Kondisi | Pelabel roda | Logika Dika | Laporan Dika | Mobil lurus | Tereproduksi (logika Dika)? |
|---|---|---|---|---|---|
| Cerah `ClearNoon` | 94,7% [94,7–94,7] | 99,5% [98,8–100] | 100% | 47,4% | **Ya** |
| Hujan `SoftRainNoon` | 94,7% [94,7–94,7] | 100% [100–100] | 84,2% | 47,4% | Tidak (preset hujan Dika tidak diketahui) |
| Malam `ClearNight` | **17,0% [14,9–19,1]** | 36,3% [33,3–39,5] | 47,4% | 47,4% | Tidak, tetapi mencakup run lab 10 Nov (36,8%) |

## Kesimpulan
1. Kualitas render menentukan: dengan `-quality-level=Low` penghindaran malam (logika Dika) 77,9%; dengan Epic 36,3%. Standar TA = Epic.
2. Cerah tereproduksi. Satu lubang (ph_0010) selalu tersentuh ban di 30/30 episode, tetapi logika Dika mencatatnya terhindar di hampir semua episode.
3. Hujan tidak berbeda dari cerah. `SoftRainNoon` kemungkinan lebih ringan dari hujan Dika. Perlu konfirmasi preset ke Dika; sampai saat itu hasil hujan hanya berlaku untuk preset ini.
4. **Malam: agen (17,0%) jauh lebih buruk daripada mobil yang tidak pernah menghindar (47,4%)**, dan logika Dika menutupi selisih ±19 poin (36,3 vs 17,0%). Ini *silent failure*: deteksi turun, agen tetap bermanuver, dan metrik lama tetap tampak wajar.
5. Logika Dika melebih-lebihkan penghindaran di semua kondisi (5 poin cerah/hujan, 19 poin malam) → pelabel roda dipakai sebagai metrik utama.
6. Simulasi tidak deterministik meski seed sama → evaluasi selalu ≥ 30 episode + CI.

## Catatan teknis
- Tabrakan: 2/90 episode (cerah, seed 2 dan 8), `static.wall` di x ≈ −37, setelah semua lubang terlewati. Tidak memengaruhi metrik lubang.
- Waktu: 133,9–136,7 s/episode, faktor real-time ±1,05; seluruh run 3 jam 26 menit tanpa time-out (`log_runner/jalankan_baseline.log`).
- GPU (`log_runner/gpu_epic.csv`): VRAM median 7.832 MiB, maks 7.878 MiB (kemungkinan alokasi rakus TensorFlow, belum diverifikasi); suhu maks 72,7 °C.
