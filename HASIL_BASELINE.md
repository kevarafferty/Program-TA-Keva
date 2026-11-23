# Hasil baseline π_Dika (#21–#22) — kualitas Epic

> **Pembaruan 23 Nov 2026:** build CARLA yang dipakai untuk semua data TA berikutnya adalah **build spawn (package 22 Nov)**. Baseline untuk build itu ada di bagian paling bawah ("Baseline build tetap"). Angka hujan di tabel utama di bawah (build 12 Nov) **tidak sebanding** dengan data build baru.


Diperbarui 21 Nov 2026: hujan kini memakai `HardRainNoon` (preset Dika menurut pencocokan citra, `11_cuaca/`), dan metrik diperbaiki untuk episode yang berhenti sebelum finis ([#21c] di `analisis_baseline.py`).

Data: `10_runner/DQN_Akselerasi vertikal/log_runner/*_Epic/` (30 episode per kondisi, seed 0–29, offset spawn ±2 m / ±0,5 m). Cerah, SoftRain, dan malam dijalankan 19 Nov; HardRain 21 Nov.
Ringkasan mesin: `hasil_baseline_ClearNight_Epic_ClearNoon_Epic_HardRainNoon_Epic_SoftRainNoon_Epic.json`. GT metrik: `alat_carla/pothole_gt_v2_segmen_dika.json` (19 lubang High). CI 95% = bootstrap atas episode.
Memo Gate 1 untuk dosbing: https://claude.ai/artifact/5Xb62EK5SJRjq6WvwJyFwj

## Tabel utama

| Kondisi | Pelabel roda, tak tercapai = gagal (metrik utama) | Episode gagal (keluar jalan + tabrak) | Pelabel roda, hanya yang dilewati | Logika Dika | Laporan Dika | Mobil lurus |
|---|---|---|---|---|---|---|
| Cerah `ClearNoon` | 94,4% [93,9–94,7] | 2/30 (0 + 2) | 94,7% | 99,5% [98,8–100] | 100% | 47,4% |
| Hujan `HardRainNoon` | **54,6% [47,4–61,6]** | **20/30 (11 + 9)** | 66,7% [60,8–72,3] | 71,8% [63,5–79,1] | 84,2% | 47,4% |
| Malam `ClearNight` | **17,0% [15,1–19,1]** | 0/30 | 17,0% | 36,3% [33,3–39,5] | 47,4% | 47,4% |
| (Preset keliru) `SoftRainNoon` | 94,7% | 0/30 | 94,7% | 100% | — | 47,4% |

Gate 1 menurut kriteria E3 (CI logika Dika mencakup angka Dika): cerah ya, hujan tidak, malam tidak. Penyebab setiap selisih terbukti → diusulkan Gate 1 lolos dengan kriteria revisi (lihat memo).

## Kesimpulan
1. Kualitas render menentukan: dengan `-quality-level=Low`, penghindaran malam (logika Dika) 77,9%; dengan Epic 36,3%. Standar TA = Epic. Dika memakai Editor dengan `Scalability: High` (video layar); statistik citra siang High ≈ Epic.
2. Cerah tereproduksi. Lubang ph_0010 selalu tersentuh ban di 30/30 episode, tetapi logika Dika mencatatnya terhindar di hampir semua episode.
3. **Hujan Dika = `HardRainNoon`, bukan `SoftRainNoon`.** Kode Dika di repo memakai SoftRainNoon, tetapi rekamannya cocok dengan HardRainNoon (skor 0,35 vs peringkat kedua 3,7). SoftRainNoon praktis sama dengan cerah, sehingga run 19 Nov tidak menguji hujan Dika.
4. **Hujan lebat: 2/3 episode gagal sebelum finis** (11 keluar jalan di sisi kiri, 9 menabrak tembok). Di 10 episode yang finis, logika Dika = 84,0%, sama dengan laporan Dika (run Dika juga finis). Angka 84,2% Dika kemungkinan berasal dari satu run yang kebetulan finis. Ini pemilahan setelah melihat data, jadi dipakai sebagai penjelasan, bukan klaim reproduksi.
5. **Malam: agen (17,0%) jauh lebih buruk daripada mobil yang tidak pernah menghindar (47,4%)**, dan logika Dika menutupi selisih ±19 poin. Ini *silent failure*: deteksi turun, agen tetap bermanuver, dan metrik lama tetap tampak wajar. Hujan lebat adalah contoh kedua (deteksi palsu → manuver → keluar jalan).
6. Logika Dika melebih-lebihkan penghindaran di semua kondisi (cerah +5, hujan +17, malam +19 poin vs metrik utama) → pelabel roda dipakai sebagai metrik utama, bersama tingkat kegagalan episode.
7. Simulasi tidak deterministik meski seed sama → evaluasi selalu ≥ 30 episode + CI.
8. Bug metrik lama: lubang yang tidak tercapai dihitung "terhindar". Tidak berpengaruh pada run yang semua episodenya finis; untuk hujan menaikkan angka dari 54,6% ke 71,9%. Sudah diperbaiki ([#21c]).

## Catatan teknis
- Tabrakan cerah: 2/90 episode (seed 2 dan 8), `static.wall` di x ≈ −37, setelah semua lubang terlewati.
- Tabrakan hujan: 9/30 episode, `static.wall` di x −32 s.d. −77. Keluar jalan: 11/30, batas y 245,55 (`carla_env.py`), tiga di antaranya sangat awal (x −264, −258, −202).
- Waktu: 133,9–136,7 s/episode (cerah/SoftRain/malam); hujan 114,7 s/ep karena banyak episode berhenti lebih awal. Run 19 Nov 3 jam 26 menit, run hujan 21 Nov 58 menit, tanpa time-out (`log_runner/jalankan_baseline.log`).
- GPU (`log_runner/gpu_epic.csv`, 19 Nov): VRAM median 7.832 MiB, maks 7.878 MiB (kemungkinan alokasi rakus TensorFlow, belum diverifikasi); suhu maks 72,7 °C.
- Cara menjalankan analisis: `INSTRUKSI_ANALISIS_BASELINE.md` di `10_runner/DQN_Akselerasi vertikal/`.


## Baseline build tetap (package 22 Nov dengan aset spawn) — dipakai untuk semua data TA berikutnya

Data: `12_lingkungan/log_skenario/*REG_t*` (runner `jalankan_skenario.py`, skenario REG = 19 lubang Dika, offset ±2 / ±0,5 m, preset Dika; 30 episode per kondisi, seed 0–29; verifikasi lubang per episode, persepsi terekam 100%, 0 episode buta). Analisis: `12_lingkungan/hasil_analisis/laporan.md` (`analisis_skenario.py`, label v2).

| Kondisi | Pelabel roda, tak tercapai = gagal (utama) | Episode gagal | Pelabel roda, hanya yang dilewati | Logika Dika | Persepsi gagal / lintasan | Palsu / frame |
|---|---|---|---|---|---|---|
| Cerah `ClearNoon` | 94,7% [94,7–94,7] | 0/30 | 94,7% | 99,5% [98,8–100] | 0,0% | 25,3% |
| Hujan `HardRainNoon` | **56,0% [50,7–61,1]** | **12/30 (1 keluar jalan + 11 tabrak)** | 60,5% [55,9–65,4] | 79,6% [73,0–85,1] | 84,9% | 40,0% |
| Malam `ClearNight` | **14,9% [13,3–16,5]** | 0/30 | 14,9% | 34,9% [32,3–37,5] | 89,3% | 7,5% |

### Uji regresi runner baru vs baseline lama (#21–#22)
Kriteria: CI 95% bootstrap selisih mencakup 0 untuk roda utama, logika Dika, dan episode gagal.
- Cerah dan malam: **setara** pada ketiga metrik → runner baru tidak mengubah perilaku agen.
- Hujan: roda utama dan logika Dika setara; **episode gagal tidak** (40% vs 66,7%; selisih [−50; −3,3]). Keluar jalan 11 → 1.

### Penyebab perbedaan hujan: build, bukan runner
1. cleanTest asli Dika di build baru, HardRainNoon seed 0–4: fraksi langkah berdeteksi 0,545–0,606, sama dengan runner baru (median 0,552) dan berbeda dari cleanTest di build lama (0,620–0,716; tidak tumpang tindih). Cerah turun sedikit (0,917 → 0,898); malam sama (0,206 vs 0,208).
2. Statistik citra global HardRainNoon identik di kedua build (`11_cuaca/hasil_PaketSpawn`); HardRainNoon tetap paling mirip rekaman Dika (skor 0,41 vs 0,42).
3. Pada 8 posisi yang sama, kotak YOLO untuk lubang asli sama di kedua build. Yang berbeda: **kotak palsu "pita bawah"** (selebar citra, jalan basah beriak dekat kamera) muncul di 4/8 frame hujan build lama dan 0/8 build baru. Di log REG t2 (build baru) kotak ini tetap muncul di 24,5% langkah dan menjadi kotak teratas di 17,6% (cerah 0%, malam 0,6%).
4. Tafsiran (dugaan kuat): mekanisme kegagalan hujan = **deteksi palsu jalan basah → manuver tidak perlu → keluar jalan / tabrak**. Frekuensinya peka terhadap perbedaan render kecil antar-build. Kotak lubang asli tidak berubah.

### Konsekuensi
- **Build spawn dibekukan**: folder `WindowsNoEditor`-nya dicadangkan, tidak di-package ulang selama pengumpulan data. Kalau terpaksa build ulang, jalankan REG lagi.
- Baseline hujan untuk TA = REG t2 di build ini. Angka hujan build lama dipakai hanya sebagai catatan sejarah dan contoh sensitivitas render (bersama temuan Low vs Epic).
