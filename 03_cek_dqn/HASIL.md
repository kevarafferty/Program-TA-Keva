# Uji muat bobot DQN Dika

**Status:** selesai. `model_best.h5` dan `model_episode_300.h5` bisa dimuat dan dijalankan.

## Berkas

| Berkas | Isi |
|---|---|
| `cek_model_dqn.py` | Memuat bobot dengan dua jalur (Keras, NumPy murni) lalu membandingkannya pada state sintetis. |
| `sapuan_jarak_dqn.py` | Memakai proyeksi kamera untuk mencari jarak saat agen mulai menghindar. |
| `hasil_cek_dqn.md` | Tabel nilai-Q per skenario dan sapuan posisi lubang di citra. |
| `hasil_sapuan_jarak.md` | Aksi agen untuk lubang di depan pada jarak 30 m → 4 m. |

## Hasil

- Berkas disimpan oleh **Keras 2.10.0**, artinya environment Dika memakai TensorFlow 2.10
  (versi terakhir yang mendukung GPU native di Windows, butuh Python ≤ 3.10).
- `load_weights` berhasil di TF 2.21 / Keras 3.15. Jalur NumPy memberi nilai-Q yang sama (selisih maks 4×10⁻⁶).
  Artinya agen bisa dipindahkan ke PyTorch tanpa melatih ulang jika konflik versi muncul (mitigasi R2).
- Perilaku `model_best.h5`:
  - Mulai menghindar saat lubang berjarak **6–8 m** (≈3–4 s pada 7 km/jam). Pada 20–30 km/jam itu hanya 1,0–1,4 s.
  - Saat lubang masih jauh, selisih nilai-Q aksi terbaik dan kedua hanya ~1 dari nilai ~15. Agen ragu.
  - Di lajur kiri tanpa lubang, agen selalu memilih KANAN. Di lajur kanan tanpa lubang, agen sedikit condong
    ke KIRI (Q 12,40 vs 12,26). `model_episode_300.h5` memilih LURUS pada kasus yang sama (lihat T13).

## Batasan

State sintetis hanya mengubah fitur YOLO dan posisi lateral. Kecepatan, setir, dan akselerasi dibuat tetap.
Ini menguji bahwa bobot masuk akal, bukan bahwa agen akan mencapai 19/19 di simulator.
