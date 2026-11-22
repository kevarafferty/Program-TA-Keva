# 11_cuaca — mencocokkan preset cuaca CARLA dengan video Dika

Dikerjakan 21 Nov 2026. Detail dan angka lengkap: `LOG_KERJA.md` 21 Nov 20.10 dan 20.40.

## Hasil

- **Hujan Dika = `HardRainNoon`** (skor 0,35 di Editor High / 0,42 di paket Epic; peringkat kedua ±3,7). Kode Dika di repo
  memakai `SoftRainNoon`, yang secara visual hampir sama dengan cerah. Belum dikonfirmasi Dika.
- Video layar Dika menunjukkan run dijalankan di **Unreal Editor (Play), `Scalability: High`**. Untuk cuaca siang,
  statistik citra High ≈ Epic (selisih median < 1 unit). Malam dan perilaku YOLO di High belum diuji.
- Batasan metrik: membedakan atmosfer (awan, kabut) dengan baik, tetapi tidak bisa membedakan preset yang hanya berbeda
  kebasahan jalan pada langit cerah (WetNoon vs ClearNoon seri).

## Isi folder

| Berkas/folder | Isi |
|---|---|
| `cocokkan_cuaca.py` | Tiga langkah: `referensi` (statistik citra dari video Dika), `ambil` (render 7 preset × 8 titik di CARLA), `bandingkan` (skor + montase) |
| `referensi/` | Frame dan statistik video Dika (cerah, hujan, malam) |
| `_pratinjau_dika/` | Tangkapan layar video Dika, termasuk label `Scalability: High` |
| `data_EditorHigh/`, `data_PaketEpic/` | Citra hasil render per preset |
| `hasil_EditorHigh/`, `hasil_PaketEpic/` | `ringkasan_<kondisi>.json` + `montase_<kondisi>.jpg` (baris teratas = Dika, berikutnya urut skor terbaik) |

## Menjalankan ulang

```
conda activate carla_env
cd "...\Program TA Keva\11_cuaca"
python cocokkan_cuaca.py ambil --label PaketEpic          # CarlaUE4.exe paket sudah terbuka
python cocokkan_cuaca.py bandingkan --kondisi hujan --label PaketEpic
```
Langkah `referensi` tidak perlu diulang. Untuk render di Editor: `make launch` di `D:\carla`, buka `train_fix`,
set *Engine Scalability Settings → High*, tekan Play, lalu `ambil --label EditorHigh`.
Uji kewarasan: pada `--kondisi cerah`, ClearNoon (atau WetNoon, seri) harus juara.
