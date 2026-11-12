# TODO #11 — Env Python `carla_env` di laptop (dari ekspor PC lab)

Sumber: `08_kunjungan_lab/hasil_lab/env_carla_env.yml` dan `pip_carla_env.txt` (PC lab, 10 Nov 2026).
Selesai jika: `python cek_env.py` mencetak `HASIL: LULUS`.

Kenapa tidak langsung `conda env create -f env_carla_env.yml`:
1. `torch==2.4.1+cu118` tidak ada di PyPI biasa, jadi pip gagal di tengah jalan.
2. `gym==0.21.0` gagal di-build dengan pip/setuptools versi baru. Harus pasang pip 21.3.1, setuptools 65.5.0, wheel 0.38.4 dulu.
3. Env lab berisi cuDNN 9.10, padahal TensorFlow 2.10 butuh cuDNN 8.1. Kemungkinan besar TF di PC lab jalan di CPU.

## Langkah (Anaconda Prompt, bukan PowerShell)

```
conda create -n carla_env --override-channels -c conda-forge python=3.8.20 -y
conda activate carla_env
python -m pip install pip==21.3.1 setuptools==65.5.0 wheel==0.38.4
pip install torch==2.4.1+cu118 torchvision==0.19.1+cu118 torchaudio==2.4.1+cu118 --index-url https://download.pytorch.org/whl/cu118
cd "D:\ITB\Teknik Fisika\Tugas Akhir 102284tf\Program TA Keva\alat_carla\env_laptop"
pip install -r requirements_carla_env.txt
python cek_env.py
```

Opsional, supaya TF (DQN) bisa memakai GPU:
```
conda install --override-channels -c conda-forge cudatoolkit=11.2 cudnn=8.1.0 -y
python cek_env.py
```
Ini menyimpang dari env lab (cuDNN 9.10). Catat di LOG_KERJA kalau dipakai. DQN Dika berupa MLP kecil, jadi CPU pun cukup.

## Kalau gagal
- `No matching distribution for carla==0.9.15`: cek `python --version` = 3.8. Cadangan: wheel dari source build sendiri di `<carla>\PythonAPI\carla\dist\` setelah TODO #10.
- `gym` gagal build: langkah pin pip/setuptools/wheel terlewat. Ulangi, lalu `pip install gym==0.21.0`.
- `DLL load failed` saat import tensorflow: pasang Microsoft Visual C++ Redistributable 2015–2022 x64.
- Server CARLA buatanmu melapor versi `0.9.15-dirty`. Peringatan beda versi client/server wajar selama keduanya 0.9.15.
