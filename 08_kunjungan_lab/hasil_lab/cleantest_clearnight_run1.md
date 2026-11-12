# cleanTest.py di PC lab — run 1

- Dijalankan oleh Keva di PC lab (Ryzen_PC), env `carla_env`, peta `train_fix`, CARLA 0.9.15-dirty
- Cuaca: ClearNight (bawaan `TEST_WEATHER` di cleanTest.py), epsilon 0, model `model_best.h5`
- Hasil: Steps 2769 | Reward -405,78 | **Hits 12 | Avoids 7 (7/19 = 37%)**
- Pembanding: laporan Dika malam 9/19 (47%); mobil yang selalu lurus juga 9/19 (T5)
- Lubang terhindar: ph_0000, 0001, 0003, 0012, 0014, 0017, 0018. Semua sev=0.9 (dari pothole_gt.json)
- Catatan: n = 1, belum bisa disimpulkan. "-dirty" hanya perbaikan URL unduhan + plugin (lihat carla_diff.txt), bukan perubahan fisika
- Disalin dari log terminal yang ditempel Keva, 10 Nov 2026
