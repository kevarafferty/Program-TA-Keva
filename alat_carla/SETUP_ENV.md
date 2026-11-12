# Menyiapkan environment Python untuk CARLA + YOLO + DQN

> **Pembaruan 11 Nov 2026:** ekspor PC lab menunjukkan env Dika (`carla_env`) memakai **satu env Python 3.8.20** dengan `carla==0.9.15` dari PyPI. Panduan di bawah sudah usang; pakai `env_laptop/README.md`.


Disusun 7 Nov 2026 dari catatan Retta (`Retta Paper\Source Code\Retta\LIDAR CARLA\aktifin yolo.txt`,
`README_SETUP.md`, `requirements.txt`) dan metadata bobot Dika. **Belum dicoba di laptopmu.**
Catat setiap perintah yang berhasil atau gagal di `LOG_KERJA.md`.

## Masalah utamanya: tiga pustaka, tiga kebutuhan versi Python

| Komponen | Versi yang dipakai senior | Kebutuhan Python | Bukti |
|---|---|---|---|
| CARLA client 0.9.15 | wheel `carla-0.9.15-cp37-cp37m-win_amd64.whl` | **3.7** (wheel ini) | `Retta\PythonAPI\carla\dist\` |
| Ultralytics (YOLO) | 8.4.13 (Dika) | ≥ 3.8 | metadata `best.pt` |
| TensorFlow (DQN Dika) | 2.10 (Keras 2.10.0) | 3.7–3.10 | metadata `model_best.h5` |

Wheel CARLA yang ada di folder Retta hanya untuk Python 3.7, sedangkan Ultralytics versi baru tidak mendukung 3.7.
Retta mengatasinya dengan **dua environment** yang berkomunikasi lewat socket:

- `carla915_py37`: simulator client, LiDAR, pengendali
- `yolo_cuda310`: server YOLO (`yolo_server_gpu_v2.py --port 5001`)

## Pilihan untukmu

**Opsi 1 (dicoba duluan): satu environment Python 3.10.** Lebih sederhana untuk stack Dika (YOLO + DQN + CARLA dalam satu proses).
```
conda create -n ta_keva python=3.10 -y
conda activate ta_keva
pip install carla==0.9.15
```
Kalau `pip install carla==0.9.15` gagal menemukan wheel untuk Python 3.10 di Windows, pakai Opsi 2.
Jika berhasil, lanjutkan:
```
pip install "tensorflow==2.10.*" ultralytics opencv-python numpy pandas scikit-learn matplotlib h5py pytest
python -c "import carla, tensorflow, ultralytics; print('ok')"
```
Catatan: TF 2.10 adalah versi terakhir yang mendukung GPU native di Windows dan butuh CUDA 11.2 + cuDNN 8.1.
Kalau repot, DQN cukup jalan di CPU (MLP kecil). Jalur NumPy di `03_cek_dqn/cek_model_dqn.py`
juga bisa menggantikan TF sepenuhnya.

**Opsi 2: dua environment seperti Retta.**
```
conda create -n carla915_py37 python=3.7 -y
conda activate carla915_py37
pip install "<path>\Retta\PythonAPI\carla\dist\carla-0.9.15-cp37-cp37m-win_amd64.whl"
pip install numpy==1.21.6 pygame==2.1.2 scikit-learn==1.0.2 scipy==1.7.3 open3d==0.15.2

conda create -n yolo_cuda310 python=3.10 -y
conda activate yolo_cuda310
pip install ultralytics opencv-python
```
Kekurangannya: kode Dika memanggil YOLO di dalam `carla_env.py`, jadi harus diubah agar memanggil server YOLO.

## Simulator

- Paket CARLA 0.9.15 Windows (bukan source build) cukup untuk: Town bawaan, jalan dari `lurus.xodr`,
  dan memunculkan objek lewat API.
- **Peta `train_fix` (Dika) dan peta Retta hanya tersedia sebagai aset Unreal.** Retta menjalankannya dari
  CARLA *source build* (`cd /d D:\carla`, `make launch`, lalu `--map current`). Membangun CARLA dari sumber
  di Windows butuh Unreal Engine 4.26 versi CARLA, Visual Studio 2019, ±130 GB ruang disk, dan beberapa jam.
  Jangan mulai ke arah ini sebelum dosbing setuju dan sebelum memastikan PC lab tidak punya build yang siap pakai.
- Jalankan server dengan `CarlaUE4.exe -quality-level=Low` dan pastikan `nvidia-smi` menunjukkan proses itu memakai RTX 4060.
