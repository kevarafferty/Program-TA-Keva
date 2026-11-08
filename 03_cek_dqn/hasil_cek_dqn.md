# Hasil uji muat bobot DQN Dika

## model_best.h5

- Versi Keras yang menyimpan berkas: **2.10.0** (backend tensorflow)
- Urutan lapisan di berkas: ['fc1', 'fc2', 'fc3', 'dropout', 'q_values']
- Jalur Keras: load_weights berhasil di TF 2.21.0 / Keras 3.15.1
- Selisih maksimum nilai-Q Keras vs NumPy: 1.91e-06

| Skenario | Q lurus | Q kiri | Q kanan | Aksi dipilih | Yang diharapkan |
|---|---:|---:|---:|---|---|
| Jalan kosong, lajur kanan | 12.26 | 12.40 | 10.24 | **KIRI** | LURUS |
| Jalan kosong, lajur kiri | 12.28 | 11.39 | 13.03 | **KANAN** | LURUS |
| Lubang tepat di depan (cx 0.50), lajur kanan, sev 0.9 | 15.71 | 15.15 | 14.27 | **LURUS** | KIRI/KANAN |
| Lubang tepat di depan (cx 0.50), lajur kanan, sev 0.6 | 16.50 | 16.29 | 15.13 | **LURUS** | KIRI/KANAN |
| Lubang tepat di depan (cx 0.50), lajur kanan, sev 0.3 | 12.39 | 11.38 | 10.89 | **LURUS** | KIRI/KANAN |
| Lubang di sisi kiri citra (cx 0.25), lajur kanan, sev 0.9 | 16.58 | 16.21 | 15.22 | **LURUS** | LURUS atau KANAN |
| Lubang di sisi kanan citra (cx 0.75), lajur kanan, sev 0.9 | 13.98 | 12.98 | 12.31 | **LURUS** | LURUS atau KIRI |
| Lubang tepat di depan, lajur kiri, sev 0.9 | 15.60 | 14.54 | 16.04 | **KANAN** | KIRI/KANAN |
| Lubang dekat (cy 0.70, kotak besar), lajur kanan, sev 0.9 | -14.12 | -10.78 | -16.13 | **KIRI** | KIRI/KANAN |

Sapuan posisi lubang di citra, cx 0.05 (kiri) → 0.95 (kanan), 19 titik.
Simbol: `|` lurus, `<` belok kiri, `>` belok kanan.

```
lajur kanan sev 0.9: |||||||||||||||||||
lajur kanan sev 0.6: <<<||||||||||||||||
lajur kanan sev 0.3: <<<<<<<||||||||||||
lajur kiri  sev 0.9: >>>>>>>>>>>>>>>>>>>
lajur kiri  sev 0.6: >>>>>>>>>>>>>>>>>>>
lajur kiri  sev 0.3: >>>>>>>>>>>>>>>>>>>
```

## model_episode_300.h5

- Versi Keras yang menyimpan berkas: **2.10.0** (backend tensorflow)
- Urutan lapisan di berkas: ['fc1', 'fc2', 'fc3', 'dropout', 'q_values']
- Jalur Keras: load_weights berhasil di TF 2.21.0 / Keras 3.15.1
- Selisih maksimum nilai-Q Keras vs NumPy: 3.81e-06

| Skenario | Q lurus | Q kiri | Q kanan | Aksi dipilih | Yang diharapkan |
|---|---:|---:|---:|---|---|
| Jalan kosong, lajur kanan | 10.08 | 8.71 | 9.09 | **LURUS** | LURUS |
| Jalan kosong, lajur kiri | 16.47 | 16.35 | 16.89 | **KANAN** | LURUS |
| Lubang tepat di depan (cx 0.50), lajur kanan, sev 0.9 | 18.15 | 16.67 | 17.58 | **LURUS** | KIRI/KANAN |
| Lubang tepat di depan (cx 0.50), lajur kanan, sev 0.6 | 18.88 | 17.64 | 18.37 | **LURUS** | KIRI/KANAN |
| Lubang tepat di depan (cx 0.50), lajur kanan, sev 0.3 | 14.78 | 13.61 | 13.98 | **LURUS** | KIRI/KANAN |
| Lubang di sisi kiri citra (cx 0.25), lajur kanan, sev 0.9 | 17.92 | 16.17 | 17.54 | **LURUS** | LURUS atau KANAN |
| Lubang di sisi kanan citra (cx 0.75), lajur kanan, sev 0.9 | 18.77 | 17.80 | 17.73 | **LURUS** | LURUS atau KIRI |
| Lubang tepat di depan, lajur kiri, sev 0.9 | 20.34 | 20.03 | 20.19 | **LURUS** | KIRI/KANAN |
| Lubang dekat (cy 0.70, kotak besar), lajur kanan, sev 0.9 | -13.48 | -10.98 | -14.34 | **KIRI** | KIRI/KANAN |

Sapuan posisi lubang di citra, cx 0.05 (kiri) → 0.95 (kanan), 19 titik.
Simbol: `|` lurus, `<` belok kiri, `>` belok kanan.

```
lajur kanan sev 0.9: |||||||||||||||||||
lajur kanan sev 0.6: |||||||||||||||||||
lajur kanan sev 0.3: |||||||||||||||||||
lajur kiri  sev 0.9: ||||||||||||||||||<
lajur kiri  sev 0.6: |||||>>||||||||||||
lajur kiri  sev 0.3: |>>>>>>>>>>>>||||||
```
