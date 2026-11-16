# Pelabel kontak roda–lubang

**Status:** kode dan uji selesai. Geometri Microlino **terukur** dari CARLA (12 Nov 2026, TODO #15), kecuali
setengah lebar ban r_w yang masih estimasi. Hasil dengan geometri tebakan lama disimpan dengan akhiran `_estimasi`.

## Berkas

| Berkas | Isi |
|---|---|
| `kontak_roda.py` | Pelabel kontak roda, label horizon 2 s, energi pelanggaran E_V (pers. 7), model sepeda, tiruan logika HIT/AVOID Dika. Hanya butuh NumPy. |
| `test_kontak_roda.py` | 15 uji unit dengan jawaban yang bisa dihitung tangan. `hasil/hasil_uji_unit.txt`: 15 lulus. |
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

## Geometri yang dipakai (TERUKUR, kecuali r_w)

Sumber: `alat_carla/geometri_terukur.json` (CARLA 0.9.15, peta train_fix, `vehicle.micro.microlino`).

| Parameter | Terukur (dipakai) | Estimasi lama | Asal |
|---|---:|---:|---|
| Titik asal → poros depan | 0,684 m | 0,75 m | terukur |
| Titik asal → poros belakang | 0,841 m | 0,72 m | terukur |
| Jejak depan (pusat ban kiri–kanan) | 1,192 m | 1,20 m | terukur |
| Jejak belakang (pusat ban kiri–kanan) | **0,722 m** | 1,20 m | terukur |
| Setengah lebar ban r_w | 0,075 m | 0,075 m | **masih estimasi** (API tidak memberi lebar ban) |
| Setengah lebar / panjang bodi | 0,740 / 1,104 m | 0,74 / 1,10 m | terukur (bbox) |

Jejak depan dan belakang Microlino berbeda jauh, jadi kode memakai keduanya terpisah (`jejak_depan`,
`jejak_belakang`). Jangan pakai `lebar_jejak` 0,957 m di blok `untuk_kontak_roda_py` JSON: itu rata-rata
dan salah untuk kedua poros. `logika_dika()` tetap memakai 0,74 / 1,10 milik kode Dika.
Geometri lama tetap tersedia sebagai `MICROLINO_ESTIMASI`.

## Hasil utama

| Uji | Label roda | Logika Dika |
|---|---|---|
| Lewat tepat di tengah lubang 2×3 m | kontak | HIT |
| Offset lateral 1,9 m | **kontak** (ban kiri) | **terhindar** |
| Offset lateral 2,3 m | aman | aman |
| Lubang sempit (lebar 0,4 m) dikangkangi | **aman** | **HIT** |
| Lubang lebar 0,6 m tepat di tengah | **kontak** (kedua ban belakang) | HIT |
| Dua lubang selajur 4 m, 25 km/jam | 2 kontak | 1 HIT + 1 "terhindar" |
| Dua lubang selajur 13 m, 7 km/jam | 2 kontak | 2 HIT |

- Rentang ketidaksepakatan offset: **1,84–2,16 m** (batas kontak roda 2,171 m; dengan estimasi lama 2,175 m, jadi
  rentangnya tidak berubah pada resolusi sapuan 0,02 m).
- Lubang yang bisa dikangkangi tanpa kontak: lebar < **0,57 m** (2 × tepi dalam ban belakang 0,286 m).
  Dengan estimasi lama batasnya 1,05 m, jadi klaim "dikangkangi" kini hanya berlaku untuk lubang sempit.
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
- Ground truth lubang Dika sendiri masih estimasi (T14). Angka lintasan memakai `pothole_gt.json` lama dan
  dihitung ulang setelah GT baru (TODO #17–#18).
- r_w masih estimasi; perubahan ±0,015 m menggeser batas kontak ±0,015 m.
- Model sepeda belum dikalibrasi terhadap sudut setir maksimum Microlino (diukur oleh `ukur_geometri.py`).
