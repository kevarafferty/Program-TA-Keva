# Pelabel kontak roda–lubang

**Status:** kode dan uji selesai. Geometri Microlino masih **estimasi**; ganti setelah diukur di CARLA.

## Berkas

| Berkas | Isi |
|---|---|
| `kontak_roda.py` | Pelabel kontak roda, label horizon 2 s, energi pelanggaran E_V (pers. 7), model sepeda, tiruan logika HIT/AVOID Dika. Hanya butuh NumPy. |
| `test_kontak_roda.py` | 14 uji unit dengan jawaban yang bisa dihitung tangan. `hasil/hasil_uji_unit.txt`: 14 lulus. |
| `bandingkan_dengan_dika.py` | Sapuan offset lateral, sapuan kecepatan × jarak, dan lintasan 19 lubang Dika. |
| `hasil/sapuan_offset_lateral.png` | Rentang offset di mana label baru dan logika Dika tidak sepakat. |
| `hasil/sapuan_cooldown.png` | Kombinasi kecepatan dan jarak di mana cooldown Dika menelan kontak. |
| `hasil/ringkasan_perbandingan.json` | Semua angka. |

## Definisi

- **Kontak**: jarak bertanda dari pusat ban ke tepi lubang < setengah lebar ban. Jarak bertanda negatif berarti
  pusat ban sudah di dalam lubang. Hanya lubang Medium/High yang dihitung (Subbab 2.1.3).
- **Label kegagalan keputusan** y_t = 1 jika ada kontak pada langkah t+1 sampai t+40 (2 s pada 0,05 s/langkah).
- **E_V** = (1/H) Σ_t Σ_roda Σ_lubang max(0, e^(r_w − d) − 1). Nilainya > 0 tepat ketika ada kontak
  (diuji di `test_energi_konsisten_dengan_label_kontak`), lalu naik eksponensial makin dalam ban masuk.

## Geometri yang dipakai (ESTIMASI)

| Parameter | Nilai | Asal |
|---|---:|---|
| Titik asal → poros depan | 0,75 m | estimasi |
| Titik asal → poros belakang | 0,72 m | estimasi |
| Lebar jejak (pusat ban kiri–kanan) | 1,20 m | estimasi |
| Setengah lebar ban r_w | 0,075 m | estimasi (ban ~150 mm) |
| Setengah lebar bodi | 0,74 m | kode Dika |

Jalankan `alat_carla/ukur_geometri.py` di CARLA, lalu isi `GeometriKendaraan(...)` dengan angka terukur.

## Hasil utama

| Uji | Label roda | Logika Dika |
|---|---|---|
| Lewat tepat di tengah lubang 2×3 m | kontak | HIT |
| Offset lateral 1,9 m | **kontak** (ban kiri) | **terhindar** |
| Offset lateral 2,3 m | aman | aman |
| Lubang sempit (lebar 0,6 m) dikangkangi | **aman** | **HIT** |
| Dua lubang selajur 4 m, 25 km/jam | 2 kontak | 1 HIT + 1 "terhindar" |
| Dua lubang selajur 13 m, 7 km/jam | 2 kontak | 2 HIT |

- Rentang ketidaksepakatan offset: **1,84–2,16 m** (bergantung pada geometri yang belum diukur).
- Cooldown: untuk lubang selajur berjarak 13 m, kontak kedua mulai hilang dari **11 km/jam**.
- Lintasan 19 lubang Dika:

| Lintasan sintetis | Terhindar (label roda) | Terhindar (logika Dika) |
|---|---:|---:|
| Lurus di lajur spawn (y = 250,5) | 9/19 = 47,4% | 9/19 = 47,4% |
| Lurus di lajur kiri (y = 247,2) | 10/19 = 52,6% | 10/19 = 52,6% |
| Menenun halus ke lajur seberang tiap lubang | 19/19 | 19/19 |

Baris pertama sama persis dengan hasil malam Dika (47%). Lihat T5 di `TEMUAN.md`.

## Batasan

- Log sensor Dika tidak menyimpan posisi x, y, sehingga episode lama tidak bisa dilabeli ulang.
  Semua lintasan di atas sintetis.
- Ground truth lubang Dika sendiri masih estimasi (T14).
- Model sepeda belum dikalibrasi terhadap sudut setir maksimum Microlino (diukur oleh `ukur_geometri.py`).
