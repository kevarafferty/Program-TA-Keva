# Instruksi: `analisis_baseline.py`

Merangkum run baseline π_Dika per kondisi: penghindaran lubang (pelabel roda dan logika Dika), CI 95%, cara episode berakhir, dan lubang yang paling sering kena.

**Waktu:** < 1 menit per kondisi. Tidak butuh CARLA.

---

## 1. Syarat

- Folder run ada di `log_runner\` dan berisi:
  - `ringkasan_episode.csv`: satu baris per episode yang selesai
  - `posisi_ep*_seed*.csv`: lintasan x, y, yaw per langkah
- Nama folder mengikuti pola dari `cleanTest.py`: `<tanggal>_<jam>_<Cuaca>[_<label>]`, misalnya `20261121_204019_HardRainNoon_Epic`. Bagian setelah jam (`HardRainNoon_Epic`) menjadi nama kondisi di output. Bagian sebelum `_` pertama (`HardRainNoon`) dipakai untuk mencari angka laporan Dika.
- Jalankan **dari folder `10_runner\DQN_Akselerasi vertikal`**, karena path GT default relatif terhadap folder itu.

## 2. Cara menjalankan

```
conda activate carla_env
cd /d "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\10_runner\DQN_Akselerasi vertikal"
```

| Tujuan | Perintah |
|---|---|
| Satu run | `python analisis_baseline.py --runs "log_runner\20261121_204019_HardRainNoon_Epic"` |
| Semua run Epic sekaligus | `python analisis_baseline.py --runs "log_runner\*_Epic"` |
| Beberapa pola | `python analisis_baseline.py --runs "log_runner\*ClearNoon_Epic" "log_runner\*HardRainNoon_Epic"` |
| Nama file output sendiri | tambahkan `--out hasil_gate1.json` |
| GT lain | tambahkan `--gt "..\..\alat_carla\<file>.json"` (default: `pothole_gt_v2_segmen_dika.json`, 19 lubang) |

Tanda kutip wajib dipakai kalau path mengandung `*` atau spasi. Pola `*` diurai oleh skrip, bukan oleh terminal.

**Jangan masukkan run dari kualitas render berbeda ke satu pola.** Run Low ada di `log_runner\_kualitas_low\` dan run diagnosis di `log_runner\_diagnosis\`. Pola `log_runner\*_Epic` tidak menyentuh keduanya. Kalau dua folder punya nama kondisi yang sama (misalnya dua run `HardRainNoon_Epic`), episodenya digabung, dan seed yang sama akan memicu peringatan `seed ganda`.

## 3. Membaca output

Contoh (HardRainNoon, 21 Nov):
```
== HardRainNoon_Epic: 30 episode
   pelabel roda : 71.9%  CI95 [66.7, 77.2]
   logika Dika  : 71.8%  CI95 [63.5, 79.1]  | laporan Dika 84.2% | mobil lurus 47,4%
   roda, hanya lubang yang dilewati : 66.7%  CI95 [60.8, 72.3]
   roda, tak tercapai = gagal       : 54.6%  CI95 [47.4, 61.6]
   akhir episode: {'finis': 10, 'keluar_jalan': 11, 'tabrak': 9}
   sering kena  : [('ph_0010', 20), ('ph_0013', 18), ...]
   tabrakan 20 ep, finis 10 ep, 114.7 s/ep
```

| Baris | Arti | Kapan dipakai |
|---|---|---|
| `pelabel roda` | % dari 19 lubang yang tidak tersentuh ban (kontak roda–poligon lubang). **Lubang yang tidak tercapai dihitung terhindar.** | Hanya sah kalau semua episode finis. Dipertahankan supaya bisa dibandingkan dengan hasil lama. |
| `logika Dika` | Aturan asli Dika (jarak lateral > ambang = terhindar), cara hitung sama dengan baris di atas | Pembanding dengan laporan Dika. Terbukti melebih-lebihkan (5 poin cerah, 19 poin malam). |
| `roda, hanya lubang yang dilewati` | % dari lubang yang benar-benar dilewati mobil yang tidak tersentuh | Mengukur kemampuan menghindar saat agen masih di jalan. Menyembunyikan episode yang berhenti lebih awal. |
| `roda, tak tercapai = gagal` | Lubang yang tidak tercapai dihitung gagal, dibagi 19 | **Metrik utama yang diusulkan** (paling konservatif). |
| `akhir episode` | `finis` = x_akhir ≥ −28; `tabrak` = ada objek di kolom `tabrakan`; `keluar_jalan` = berhenti sebelum finis tanpa tabrakan (batas y 245,55 di `carla_env.py`) | **Laporkan selalu bersama metrik utama.** Kegagalan episode = tabrak + keluar_jalan. |
| `sering kena` | 5 lubang dengan jumlah episode kena terbanyak (pelabel roda) | Mencari lubang sistematis (contoh: ph_0010 kena 30/30 di cerah). |
| `tabrakan … finis …` | Ringkasan lama: "tabrakan" di sini = semua episode yang tidak finis, termasuk keluar jalan | Pakai baris `akhir episode` untuk rinciannya. |

CI 95% = bootstrap atas episode (5.000 resampel, seed 0, jadi hasilnya selalu sama). CI selebar 0 (misalnya [94.7, 94.7]) berarti semua episode memberi angka yang persis sama, bukan tanda error.

## 4. Pemeriksaan wajib sebelum angka dipakai

1. Jumlah episode = 30 per kondisi. Lebih sedikit berarti ada episode yang crash. Episode itu dilewati otomatis karena tidak punya baris di `ringkasan_episode.csv`, jadi lanjutkan seed yang hilang dengan `jalankan_baseline.py`.
2. Tidak ada `PERINGATAN: seed ganda`. Kalau ada, pindahkan folder run yang gagal atau berulang ke `log_runner\_batal\`, lalu jalankan ulang analisis.
3. Lihat `akhir episode`. Kalau `finis` < 30, baris `pelabel roda` dan `logika Dika` terlalu optimistis, jadi pakai dua baris `roda, ...`.
4. Bandingkan `laporan Dika` hanya kalau preset dan kualitas render sama dengan Dika: HardRainNoon untuk hujan, Editor High ≈ Epic untuk siang. Malam di High belum diuji.

## 5. Output file

- JSON: default `hasil_baseline_<kondisi1>_<kondisi2>....json` di folder yang sama. File lama tidak tertimpa kecuali kamu memberi `--out` dengan nama yang sudah ada.
- Isi per kondisi: semua angka di atas + CI, `akhir_episode`, `lubang_sering_kena`, `detik_rata2`.
- Setelah itu: salin angka ke `HASIL_BASELINE.md`, catat di `LOG_KERJA.md`, lalu commit (`git add -A && git commit -m "..."` dari folder `Program TA Keva`).

## 6. Kalau error

| Pesan | Penyebab | Solusi |
|---|---|---|
| `FileNotFoundError ... pothole_gt_v2_segmen_dika.json` | Dijalankan dari folder lain | `cd` ke `10_runner\DQN_Akselerasi vertikal` atau beri `--gt` path absolut |
| `ModuleNotFoundError: kontak_roda` | Folder `02_pelabel_roda` dipindah | Kembalikan ke `Program TA Keva\02_pelabel_roda` |
| `FileNotFoundError ... ringkasan_episode.csv` | Folder run kosong (gagal sebelum episode 1) | Pindahkan ke `log_runner\_diagnosis\` |
| Output kosong (tidak ada `==`) | Pola `--runs` tidak cocok dengan folder mana pun | Cek nama folder dengan `dir log_runner` |
