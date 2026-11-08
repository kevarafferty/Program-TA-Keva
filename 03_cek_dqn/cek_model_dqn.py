"""
cek_model_dqn.py — Uji apakah bobot DQN Dika (model_best.h5) bisa dimuat dan
apakah keputusan agen masuk akal pada state sintetis.

Dua jalur dijalankan dan hasilnya dibandingkan:
  (A) Keras: kelas DQNNetwork Dika (disalin persis dari agent/network.py) +
      load_weights().
  (B) NumPy murni: bobot dibaca langsung dari berkas .h5 dengan h5py lalu
      forward pass dihitung manual (ReLU MLP 10-128-128-64-3). Jalur ini tidak
      bergantung pada versi TensorFlow, jadi bisa dipakai nanti untuk memindahkan
      agen ke PyTorch (mitigasi risiko R2 di proposal).

Cara pakai (dari folder ini):
    python cek_model_dqn.py --h5 "<path>/model_best.h5" --out hasil_cek_dqn.md

Susunan state 10-D (dari environment/carla_env.py Dika):
  [0] cx  [1] cy  [2] w  [3] h   -> kotak YOLO dengan conf tertinggi, dinormalisasi 0-1
  [4] severity                    -> {cls0:0.6, cls1:0.9, cls2:0.3}, di-EMA
  [5] speed_n = km/jam / 60       [6] steer_n = kontrol setir terakhir [-1,1]
  [7] accel_n = |a_IMU| / 10      [8] pos_n = (y - 249.05) / 3.5
  [9] collision flag
Aksi: 0 = lurus, 1 = belok kiri (steer -0.35), 2 = belok kanan (steer +0.35)
"""
import argparse
import itertools
import os
import sys

import h5py
import numpy as np

AKSI = {0: "LURUS", 1: "KIRI", 2: "KANAN"}


# ---------------------------------------------------------------------------
# (B) Forward pass NumPy dari bobot h5
# ---------------------------------------------------------------------------
def baca_bobot_h5(path):
    """Ambil kernel dan bias tiap lapisan Dense dari berkas save_weights() Keras 2."""
    bobot = {}
    with h5py.File(path, "r") as f:
        meta = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in f.attrs.items()}
        for nama in ["fc1", "fc2", "fc3", "q_values"]:
            grp = f[nama]["dqn_network"][nama]
            bobot[nama] = (np.array(grp["kernel:0"]), np.array(grp["bias:0"]))
    return bobot, meta


def forward_numpy(bobot, x):
    h = np.asarray(x, dtype=np.float32)
    for nama in ["fc1", "fc2", "fc3"]:
        W, b = bobot[nama]
        h = np.maximum(h @ W + b, 0.0)          # Dense + ReLU (dropout mati saat inferensi)
    W, b = bobot["q_values"]
    return h @ W + b                            # keluaran linear = nilai-Q


# ---------------------------------------------------------------------------
# (A) Jalur Keras dengan kelas asli Dika
# ---------------------------------------------------------------------------
def coba_keras(path, X):
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers
    except Exception as e:  # TF tidak ada
        return None, f"TensorFlow tidak tersedia: {e}"

    class DQNNetwork(keras.Model):  # salinan persis arsitektur Dika
        def __init__(self, num_actions):
            super().__init__()
            self.fc1 = layers.Dense(128, activation="relu", name="fc1")
            self.fc2 = layers.Dense(128, activation="relu", name="fc2")
            self.fc3 = layers.Dense(64, activation="relu", name="fc3")
            self.dropout = layers.Dropout(0.1, name="dropout")
            self.output_layer = layers.Dense(num_actions, name="q_values")

        def call(self, inputs, training=False):
            x = tf.cast(inputs, tf.float32)
            x = self.fc1(x); x = self.fc2(x); x = self.fc3(x)
            x = self.dropout(x, training=training)
            return self.output_layer(x)

    net = DQNNetwork(3)
    net(tf.zeros((1, 10)))
    try:
        net.load_weights(path)
    except Exception as e:
        return None, f"load_weights gagal di TF {tf.__version__}: {type(e).__name__}: {str(e)[:300]}"
    return net(np.asarray(X, np.float32)).numpy(), f"load_weights berhasil di TF {tf.__version__} / Keras {keras.__version__}"


# ---------------------------------------------------------------------------
# State sintetis
# ---------------------------------------------------------------------------
def buat_state(cx=0.0, cy=0.0, w=0.0, h=0.0, sev=0.0, kmh=7.0, steer=0.0, acc=9.81, y=250.5, col=0.0):
    return np.array([cx, cy, w, h, sev,
                     np.clip(kmh / 60.0, 0, 1), steer,
                     np.clip(acc / 10.0, 0, 1),
                     np.clip((y - 249.05) / 3.5, -1, 1), col], dtype=np.float32)


def skenario():
    """Kasus yang jawabannya bisa ditebak oleh manusia."""
    LAJUR_KANAN, LAJUR_KIRI = 250.5, 247.2   # y spawn Dika, dan y pusat lubang lajur kiri
    box = dict(cy=0.40, w=0.13, h=0.035)      # ukuran kotak tipikal dari label CARLA Dika
    S = []
    S.append(("Jalan kosong, lajur kanan", buat_state(y=LAJUR_KANAN), "LURUS"))
    S.append(("Jalan kosong, lajur kiri", buat_state(y=LAJUR_KIRI), "LURUS"))
    for sev_nama, sev in [("sev 0.9", 0.9), ("sev 0.6", 0.6), ("sev 0.3", 0.3)]:
        S.append((f"Lubang tepat di depan (cx 0.50), lajur kanan, {sev_nama}",
                  buat_state(cx=0.50, sev=sev, y=LAJUR_KANAN, **box), "KIRI/KANAN"))
    S.append(("Lubang di sisi kiri citra (cx 0.25), lajur kanan, sev 0.9",
              buat_state(cx=0.25, sev=0.9, y=LAJUR_KANAN, **box), "LURUS atau KANAN"))
    S.append(("Lubang di sisi kanan citra (cx 0.75), lajur kanan, sev 0.9",
              buat_state(cx=0.75, sev=0.9, y=LAJUR_KANAN, **box), "LURUS atau KIRI"))
    S.append(("Lubang tepat di depan, lajur kiri, sev 0.9",
              buat_state(cx=0.50, sev=0.9, y=LAJUR_KIRI, **box), "KIRI/KANAN"))
    S.append(("Lubang dekat (cy 0.70, kotak besar), lajur kanan, sev 0.9",
              buat_state(cx=0.50, cy=0.70, w=0.30, h=0.08, sev=0.9, y=LAJUR_KANAN), "KIRI/KANAN"))
    return S


def sapuan_cx(bobot):
    """Aksi terpilih sebagai fungsi cx (posisi horizontal lubang di citra)."""
    baris = []
    for y_nama, y in [("kanan", 250.5), ("kiri", 247.2)]:
        for sev in [0.9, 0.6, 0.3]:
            aksi = []
            for cx in np.linspace(0.05, 0.95, 19):
                q = forward_numpy(bobot, buat_state(cx=cx, cy=0.40, w=0.13, h=0.035, sev=sev, y=y)[None])[0]
                aksi.append("|<>"[int(np.argmax(q))])   # | lurus, < kiri, > kanan
            baris.append((y_nama, sev, "".join(aksi)))
    return baris


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5", required=True, nargs="+", help="satu atau lebih berkas bobot .h5")
    ap.add_argument("--out", default="hasil_cek_dqn.md")
    a = ap.parse_args()

    lines = ["# Hasil uji muat bobot DQN Dika", ""]
    for path in a.h5:
        nama = os.path.basename(path)
        bobot, meta = baca_bobot_h5(path)
        S = skenario()
        X = np.stack([s[1] for s in S])
        Qn = forward_numpy(bobot, X)
        Qk, pesan_keras = coba_keras(path, X)

        lines += [f"## {nama}", "",
                  f"- Versi Keras yang menyimpan berkas: **{meta.get('keras_version')}** (backend {meta.get('backend')})",
                  f"- Urutan lapisan di berkas: {list(meta.get('layer_names'))}",
                  f"- Jalur Keras: {pesan_keras}"]
        if Qk is not None:
            lines.append(f"- Selisih maksimum nilai-Q Keras vs NumPy: {np.abs(Qk - Qn).max():.2e}")
        lines += ["", "| Skenario | Q lurus | Q kiri | Q kanan | Aksi dipilih | Yang diharapkan |",
                  "|---|---:|---:|---:|---|---|"]
        for (desk, _, harap), q in zip(S, Qn):
            lines.append(f"| {desk} | {q[0]:.2f} | {q[1]:.2f} | {q[2]:.2f} | **{AKSI[int(np.argmax(q))]}** | {harap} |")

        lines += ["", "Sapuan posisi lubang di citra, cx 0.05 (kiri) → 0.95 (kanan), 19 titik.",
                  "Simbol: `|` lurus, `<` belok kiri, `>` belok kanan.", "", "```"]
        for y_nama, sev, s in sapuan_cx(bobot):
            lines.append(f"lajur {y_nama:5s} sev {sev:.1f}: " + s)
        lines += ["```", ""]
    teks = "\n".join(lines)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(teks)
    print(teks)


if __name__ == "__main__":
    main()
