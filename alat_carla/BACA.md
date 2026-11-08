# Alat untuk dijalankan di CARLA

Baca `SETUP_ENV.md` dulu untuk menyiapkan Python dan CARLA.

**Status:** ditulis dan lolos cek sintaks, tetapi **belum pernah dijalankan** karena Claude tidak punya simulator.
Kalau ada error, kirim pesan error lengkapnya.

## `ukur_geometri.py`

Mengganti angka estimasi di `02_pelabel_roda/kontak_roda.py` dengan angka terukur:

- posisi 4 roda Microlino relatif titik asal aktor, jari-jari ban, sudut setir maksimum
- ukuran kotak pembatas kendaraan dan tinggi titik asal di atas jalan
- kotak pembatas setiap objek lubang di peta (nama mengandung `hole`, `pothole`, `lubang`, atau `med_samping`)

```
# server CARLA sudah berjalan
python ukur_geometri.py --peta train_fix --out geometri_terukur.json
# kalau train_fix belum bisa dimuat, cukup ukur kendaraannya dulu di peta bawaan:
python ukur_geometri.py --peta Town10HD_Opt --out geometri_terukur.json
```

Setelah itu salin nilai di bagian `untuk_kontak_roda_py` ke `GeometriKendaraan(...)`, lalu jalankan ulang
`02_pelabel_roda/bandingkan_dengan_dika.py`.

Catatan (siang): lubang di peta Dika adalah plane bertekstur PNG (T17). Jika nama objeknya tidak mengandung kata kunci
bawaan, jalankan dengan `--kata_lubang plane,decal,hole` atau lihat daftar nama objek di peta lalu sesuaikan.
