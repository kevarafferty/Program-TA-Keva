# 13_ensemble — pelatihan ulang DQN *ensemble* π_ens (#26)

Dokumentasi folder. Ditulis 23 Nov 2026 (Claude). Langkah menjalankan yang sekali pakai ada di Claude Docs,
bukan di sini.

**Status:** kode selesai; pilot 30 episode di CARLA laptop jalan tanpa crash (24 Nov, ±23 langkah/s). 17 uji lulus tanpa CARLA (CARLA tiruan + YOLO `best_pure.pt` asli + TensorFlow 2.21).
Uji 12_lingkungan tetap lulus setelah `jalankan_skenario.py` diberi opsi `--ensemble` (114 uji).
**Belum pernah dijalankan di CARLA sungguhan.** Laptop memakai TF 2.10/Keras 2; kode tidak memakai fitur yang
khusus Keras 3 (bobot disimpan sebagai `.npz`), tetapi kecocokan di laptop baru terbukti setelah pilot.

## Apa yang dilatih

Proposal Subbab 2.1.5: agen DQN dengan *state* 10-D dan 3 aksi yang sama dengan Dika, dilatih ulang pada
ID-0 dengan *K* = 5 kepala *bootstrapped* yang berbagi *replay buffer*, opsi *randomized prior functions*,
reward Dika + 2 perbaikan, model terbaik dipilih dari episode evaluasi tanpa eksplorasi, 3 *seed*.

| Bagian | Pilihan | Catatan |
|---|---|---|
| Arsitektur | fc1(128)–fc2(128) bersama; tiap kepala fc3(64)–dropout(0,1)–q(3) | = jaringan Dika yang bercabang setelah fc2 |
| Masker *bootstrap* | Bernoulli(0,5) per transisi per kepala, minimal 1 kepala | Osband dkk. 2016 |
| Prior | `Q_k = q_k + β·prior_k`, prior beku; **β = 3** (25 Nov) | β = 30 (24 Nov) gagal: sumbangan prior ke rata-rata Q (0,94) > margin aksi (0,19) → agen meliuk, roda 47,5% vs π_Dika 57,6% |
| Target | Double DQN per kepala + clip norma gradien 10 (25 Nov) | Dika: DQN biasa tanpa clip; skor eval seed 0 lama puncak di 100k langkah lalu turun |
| Eksplorasi | 1 kepala acak per episode, diikuti greedy; ε 1,0 sampai buffer ≥ 1.000, lalu 0,1 → 0,02 linear dalam 100.000 langkah | ε Dika (0,999/train step) turun ke 0,1 dalam < 1 episode lalu tetap 0,1 |
| Buffer | 100.000 transisi, hanya vector 10-D | Dika 10.000 (≈ 3,5 episode) termasuk citra yang tidak dipakai |
| Sama dengan Dika | Adam 1e-4, batch 32, γ 0,99, target tiap 1.000 train step, MSE, 1 train step per langkah, dropout 0,1 | |
| Reward | Dika + perbaikan ukuran melintang (T6) + tanpa *cooldown* (T7) | `env_latih.py`; `--reward dika` = asli |
| Lingkungan | ID0 tingkat 1, backend grid, cuaca ClearNoon/CloudyNoon per seed | sama dengan matriks #25 |
| Tata letak latih | ID0 seed 100000 + 10000·s + e | tidak tumpang tindih dengan evaluasi/data |
| Anggaran | 350.000 langkah latih per seed (= train step π_Dika, 349.810) | dalam langkah, bukan episode: episode awal hanya 80–800 langkah (pilot) |
| Evaluasi seleksi | tiap 50.000 langkah + di akhir, 10 episode ID0 seed 90000–90009, ε 0, argmax rata-rata Q | skor = avoids / semua lubang (tak tercapai = gagal) |
| Gate 2 | ID0 seed 0–29 lewat `jalankan_skenario.py --ensemble`, dibanding π_Dika pada seed yang sama | metrik roda dari `analisis_skenario.py` |

## Berkas

| Berkas | Fungsi |
|---|---|
| `agen_ensemble.py` | `AgenEnsemble` (jaringan, buffer bertopeng, train step, simpan/muat `.npz`), `muat_untuk_evaluasi()` |
| `env_latih.py` | `CarlaEnvLatih` = `CarlaEnvSkenario` + `_calculate_reward` dengan 2 perbaikan |
| `latih_ensemble.py` | Pelatihan satu seed: proses induk mengulang proses anak setelah crash; checkpoint tiap episode; lanjut otomatis |
| `tests/test_agen.py` | 11 uji: bentuk, masker, isolasi kepala, prior beku, belajar bandit, simpan/muat/RNG, perbaikan reward vs bug Dika |
| `tests/test_latih_palsu.py` | 5 uji end-to-end CARLA tiruan: berkas keluaran, seleksi, lanjut, tolak konfigurasi beda, runner `--ensemble` |

Perubahan di luar folder ini: `12_lingkungan/jalankan_skenario.py` opsi `--ensemble <bobot.npz>` (aksi = argmax
rata-rata Q; kolom q* di log = rata-rata; Q per kepala → `qkepala_<ep>.npy` (T, K, 3)) dan `--tag_kebijakan`
(akhiran nama folder run, bawaan `ens-<run>`, supaya run π_ens dan π_Dika tidak tercampur saat lanjut otomatis
maupun di `analisis_skenario.py`). Tanpa `--ensemble` perilaku runner tidak berubah.

## Keluaran per run: `latih/<nama>/`

| Berkas | Isi |
|---|---|
| `konfig.json` | argumen, konfigurasi agen, versi paket |
| `episode.csv` | 1 baris/episode latih: seed tata letak, kepala, ε, langkah, detik, reward, hits/avoids (reward diperbaiki), akhir, loss, buffer, `cv_aksi_median`, `std_q_rata`, `abs_q_rata`, fraksi aksi |
| `eval.csv`, `eval_ringkas.csv` | episode evaluasi dan ringkasannya per titik evaluasi; kolom `terbaik` |
| `bobot/bobot_epNNNN.npz` | bobot di setiap titik evaluasi (bisa dipilih ulang tanpa melatih lagi) |
| `bobot/bobot_terbaik.npz`, `bobot_akhir.npz` | pilihan seleksi dan bobot terakhir |
| `titik/` | checkpoint untuk lanjut (bobot, target, buffer ±10 MB, RNG, status). Tidak perlu di-commit |
| `induk.log` | mulai/ulang/berhenti proses anak |

## Uji tanpa CARLA

```
cd 13_ensemble
python -m pytest -q tests
```
Butuh `11_cuaca/data_PaketEpic` dan `12_lingkungan/uji_carla/toggle_*.png` (sudah ada). Di cloud, torch 2.15 +
TF 2.21 crash (LLVM ganda) saat TF diimpor sebelum inferensi YOLO; dengan torch 2.6 lulus. Laptop (torch 2.4.1 +
TF 2.10) memakai urutan yang sama dengan `jalankan_skenario.py`, yang sudah terbukti jalan.

## Pertanyaan terbuka

- β = 3 belum terbukti cukup memberi keragaman OOD untuk c_v (#30). Yang sudah terbukti: β = 30 merusak kebijakan.
- Kriteria "kinerja ID ≥ π_Dika" (Gate 2) perlu ditetapkan sebelum melihat hasil (usulan: batas non-inferioritas).
- Seed π_ens mana yang dipakai untuk data monitor (#28): ketiganya, atau satu yang dipilih dengan aturan tetap.
