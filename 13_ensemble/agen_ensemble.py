"""
agen_ensemble.py — [#26] Bootstrapped DQN dengan K kepala (Osband dkk. 2016) + opsi randomized prior
functions (Osband dkk. 2018; dipakai Hoel dkk. 2020 untuk keputusan taktis kendaraan).

State (10-D) dan aksi (3) SAMA dengan agen Dika (agent/network.py, agent/dqn_agent.py). Arsitektur tiap
kepala = jaringan Dika yang bercabang setelah fc2:

    state(10) -> fc1(128, relu) -> fc2(128, relu)  [batang bersama]
                                     |-> kepala k: fc3_k(64, relu) -> dropout(0.1) -> q_k(3)    k = 1..K
    Q_k(s) = q_k(s) + beta * prior_k(s)        prior_k = jaringan acak BEKU dengan bentuk yang sama

Yang berbeda dari Dika (dan alasannya):
  - K kepala + masker bootstrap Bernoulli(p) per transisi per kepala -> setiap kepala dilatih pada sampel
    pengalaman yang sedikit berbeda, sehingga sebaran Q antar kepala = ketidakpastian epistemik (c_v Hoel).
  - Eksplorasi: satu kepala dipilih acak per episode lalu diikuti secara greedy (Thompson sampling kasar).
    Ini cara eksplorasi bootstrapped DQN; epsilon Dika (decay 0.999 per train step) habis ke 0,1 dalam
    ±2.300 langkah = kurang dari satu episode, jadi praktis tidak berperan.
  - Replay buffer hanya menyimpan vector 10-D (bukan citra 84x84 yang tidak dipakai jaringan), sehingga
    kapasitas bisa dibesarkan (bawaan 100.000 langkah ≈ 35 episode; Dika 10.000 ≈ 3,5 episode).
  - Bobot disimpan sebagai .npz (bukan save_weights .h5) agar terbaca sama di TF 2.10/Keras 2 (laptop) dan
    TF 2.21/Keras 3 (uji di cloud).
Tetap sama dengan Dika: Adam lr 1e-4, batch 32, gamma 0,99, target network diperbarui tiap 1.000 train step,
loss MSE, train step setiap langkah simulasi setelah buffer >= 1.000.

Kebijakan untuk evaluasi dan pengumpulan data: argmax rata-rata Q kepala (Hoel dkk.).
"""
from __future__ import annotations

import json
import os

import numpy as np
import tensorflow as tf

N_STATE = 10
N_AKSI = 3


def _mlp_kepala(n_aksi, nama, trainable=True):
    return [tf.keras.layers.Dense(64, activation="relu", name=nama + "_fc3", trainable=trainable),
            tf.keras.layers.Dropout(0.1, name=nama + "_drop"),
            tf.keras.layers.Dense(n_aksi, name=nama + "_q", trainable=trainable)]


class JaringanEnsemble(tf.keras.Model):
    """Batang bersama + K kepala. call() -> (batch, K, n_aksi). Prior = jaringan lain yang beku."""

    def __init__(self, K=5, n_aksi=N_AKSI, nama="ens", trainable=True):
        super().__init__(name=nama)
        self.K, self.n_aksi = K, n_aksi
        self.fc1 = tf.keras.layers.Dense(128, activation="relu", name=nama + "_fc1", trainable=trainable)
        self.fc2 = tf.keras.layers.Dense(128, activation="relu", name=nama + "_fc2", trainable=trainable)
        self.kepala = [_mlp_kepala(n_aksi, "%s_k%d" % (nama, k), trainable) for k in range(K)]

    def call(self, x, training=False):
        h = self.fc2(self.fc1(tf.cast(x, tf.float32)))
        out = []
        for fc3, drop, q in self.kepala:
            out.append(q(drop(fc3(h), training=training)))
        return tf.stack(out, axis=1)


class BufferBootstrap:
    """Replay buffer cincin untuk vector state + masker bootstrap (N, K)."""

    def __init__(self, kapasitas, K, p_masker, rng):
        self.kap, self.K, self.p = int(kapasitas), int(K), float(p_masker)
        self.rng = rng
        self.s = np.zeros((self.kap, N_STATE), np.float32)
        self.s2 = np.zeros((self.kap, N_STATE), np.float32)
        self.a = np.zeros(self.kap, np.int32)
        self.r = np.zeros(self.kap, np.float32)
        self.d = np.zeros(self.kap, np.float32)
        self.m = np.zeros((self.kap, self.K), np.float32)
        self.i = 0
        self.n = 0

    def __len__(self):
        return self.n

    def tambah(self, s, a, r, s2, d):
        j = self.i
        self.s[j], self.a[j], self.r[j], self.s2[j], self.d[j] = s, a, r, s2, float(d)
        m = (self.rng.random(self.K) < self.p).astype(np.float32)
        if m.sum() == 0:                      # setiap transisi dipakai minimal oleh satu kepala
            m[self.rng.integers(self.K)] = 1.0
        self.m[j] = m
        self.i = (j + 1) % self.kap
        self.n = min(self.n + 1, self.kap)

    def ambil(self, b):
        idx = self.rng.integers(0, self.n, size=b)
        return self.s[idx], self.a[idx], self.r[idx], self.s2[idx], self.d[idx], self.m[idx]

    def simpan(self, path):
        np.savez(path, s=self.s[:self.n], s2=self.s2[:self.n], a=self.a[:self.n], r=self.r[:self.n],
                 d=self.d[:self.n], m=self.m[:self.n], i=self.i, n=self.n, kap=self.kap)

    def muat(self, path):
        z = np.load(path)
        n = int(z["n"])
        if int(z["kap"]) != self.kap or z["m"].shape[1] != self.K:
            raise ValueError("buffer tersimpan tidak cocok (kapasitas/K berbeda)")
        self.s[:n], self.s2[:n], self.a[:n], self.r[:n], self.d[:n], self.m[:n] = (
            z["s"], z["s2"], z["a"], z["r"], z["d"], z["m"])
        self.n, self.i = n, int(z["i"])


class AgenEnsemble:
    def __init__(self, K=5, beta_prior=0.0, p_masker=0.5, kapasitas=100_000, lr=1e-4, gamma=0.99, batch=32,
                 min_replay=1000, target_tiap=1000, seed=0, n_aksi=N_AKSI, double=True, clipnorm=10.0):
        self.K, self.beta, self.p_masker = int(K), float(beta_prior), float(p_masker)
        self.gamma, self.batch, self.min_replay, self.target_tiap = gamma, batch, min_replay, target_tiap
        self.n_aksi, self.seed, self.lr = n_aksi, int(seed), lr
        self.double, self.clipnorm = bool(double), float(clipnorm or 0.0)
        tf.random.set_seed(self.seed)
        self.rng = np.random.default_rng(self.seed)
        self.online = JaringanEnsemble(K, n_aksi, "online")
        self.target = JaringanEnsemble(K, n_aksi, "target", trainable=False)
        self.prior = JaringanEnsemble(K, n_aksi, "prior", trainable=False)
        nol = np.zeros((1, N_STATE), np.float32)
        for net in (self.online, self.target, self.prior):
            net(nol)
        self.target.set_weights(self.online.get_weights())
        self.opt = tf.keras.optimizers.Adam(learning_rate=lr)
        self.buffer = BufferBootstrap(kapasitas, K, p_masker, self.rng)
        self.n_train = 0
        self.kepala_aktif = 0
        self._langkah_tf = tf.function(self._langkah)
        self._q_tf = tf.function(self._q, input_signature=[tf.TensorSpec([None, N_STATE], tf.float32)])

    # ---------------------------------------------------------------- nilai-Q
    def q_semua(self, s):
        """s (10,) atau (B,10) -> Q (K, A) atau (B, K, A), termasuk prior."""
        s = np.asarray(s, np.float32)
        satu = s.ndim == 1
        x = s[None] if satu else s
        q = self._q_tf(tf.constant(x)).numpy()
        return q[0] if satu else q

    def _q(self, x):
        q = self.online(x, training=False)
        if self.beta:
            q = q + self.beta * self.prior(x, training=False)
        return q

    def pilih_kepala_episode(self):
        self.kepala_aktif = int(self.rng.integers(self.K))
        return self.kepala_aktif

    def aksi_latih(self, s, epsilon=0.0):
        if self.rng.random() < epsilon:
            return int(self.rng.integers(self.n_aksi))
        return int(np.argmax(self.q_semua(s)[self.kepala_aktif]))

    def aksi_eval(self, s):
        q = self.q_semua(s)
        return int(np.argmax(q.mean(axis=0))), q

    # ---------------------------------------------------------------- pelatihan
    def _target(self, r, s2, d):
        """y (B,K) per kepala. Double DQN: aksi dari online(+prior), nilai dari target(+prior)."""
        p_s2 = self.beta * self.prior(s2, training=False) if self.beta else 0.0
        q_next = self.target(s2, training=False) + p_s2                # (B,K,A)
        if self.double:                                                # Double DQN (van Hasselt dkk. 2016), per kepala
            a2 = tf.argmax(self.online(s2, training=False) + p_s2, axis=2)                 # (B,K)
            v_next = tf.reduce_sum(q_next * tf.one_hot(a2, self.n_aksi), axis=2)
        else:
            v_next = tf.reduce_max(q_next, axis=2)
        return tf.stop_gradient(r[:, None] + self.gamma * v_next * (1.0 - d[:, None]))

    def _langkah(self, s, a, r, s2, d, m):
        y = self._target(r, s2, d)
        p_s = self.beta * self.prior(s, training=False) if self.beta else 0.0
        with tf.GradientTape() as tape:
            q = self.online(s, training=True) + p_s                       # (B,K,A)
            q_a = tf.reduce_sum(q * tf.one_hot(a, self.n_aksi)[:, None, :], axis=2)        # (B,K)
            err2 = tf.square(y - q_a) * m
            loss_k = tf.reduce_sum(err2, axis=0) / tf.maximum(tf.reduce_sum(m, axis=0), 1.0)  # (K,)
            loss = tf.reduce_mean(loss_k)
        g = tape.gradient(loss, self.online.trainable_variables)
        if self.clipnorm > 0:
            g, _ = tf.clip_by_global_norm(g, self.clipnorm)
        self.opt.apply_gradients(zip(g, self.online.trainable_variables))
        return loss, loss_k

    def latih(self):
        if len(self.buffer) < self.min_replay:
            return None
        s, a, r, s2, d, m = self.buffer.ambil(self.batch)
        loss, _ = self._langkah_tf(tf.constant(s), tf.constant(a), tf.constant(r), tf.constant(s2),
                                   tf.constant(d), tf.constant(m))
        self.n_train += 1
        if self.n_train % self.target_tiap == 0:
            self.target.set_weights(self.online.get_weights())
        return float(loss.numpy())

    # ---------------------------------------------------------------- simpan / muat
    def konfig(self):
        return dict(K=self.K, beta_prior=self.beta, p_masker=self.p_masker, lr=self.lr, gamma=self.gamma,
                    batch=self.batch, min_replay=self.min_replay, target_tiap=self.target_tiap, seed=self.seed,
                    n_aksi=self.n_aksi, kapasitas=self.buffer.kap, n_state=N_STATE, double=self.double,
                    clipnorm=self.clipnorm,
                    arsitektur="fc1(128)-fc2(128) bersama; per kepala fc3(64)-drop(0.1)-q(3); Q=q+beta*prior")

    def simpan_bobot(self, path, ekstra=None):
        """Satu .npz berisi online, prior (selalu, agar Q bisa direkonstruksi), dan konfigurasi."""
        d = {"online_%03d" % i: w for i, w in enumerate(self.online.get_weights())}
        d.update({"prior_%03d" % i: w for i, w in enumerate(self.prior.get_weights())})
        d["konfig"] = np.array(json.dumps(dict(self.konfig(), **(ekstra or {}))))
        tmp = path + ".tmp.npz"
        np.savez(tmp, **d)
        os.replace(tmp, path)

    def simpan_titik(self, path):
        """Checkpoint lengkap untuk lanjut: + target network + status RNG + n_train."""
        d = {"target_%03d" % i: w for i, w in enumerate(self.target.get_weights())}
        d["n_train"] = self.n_train
        d["rng"] = np.array(json.dumps(self.rng.bit_generator.state))
        tmp = path + ".tmp.npz"
        np.savez(tmp, **d)
        os.replace(tmp, path)

    def muat_bobot(self, path):
        z = np.load(path)
        on = [z[k] for k in sorted(k for k in z.files if k.startswith("online_"))]
        pr = [z[k] for k in sorted(k for k in z.files if k.startswith("prior_"))]
        self.online.set_weights(on)
        self.prior.set_weights(pr)
        self.target.set_weights(on)
        return json.loads(str(z["konfig"]))

    def muat_titik(self, path):
        z = np.load(path)
        self.target.set_weights([z[k] for k in sorted(k for k in z.files if k.startswith("target_"))])
        self.n_train = int(z["n_train"])
        self.rng.bit_generator.state = json.loads(str(z["rng"]))


def muat_untuk_evaluasi(path):
    """Bangun agen dari bobot .npz (konfigurasi dibaca dari berkas). Untuk jalankan_skenario.py --ensemble."""
    z = np.load(path)
    k = json.loads(str(z["konfig"]))
    ag = AgenEnsemble(K=k["K"], beta_prior=k["beta_prior"], p_masker=k["p_masker"], kapasitas=10,
                      seed=k.get("seed", 0), n_aksi=k.get("n_aksi", N_AKSI), double=k.get("double", False),
                      clipnorm=k.get("clipnorm", 0.0))
    ag.muat_bobot(path)
    return ag, k
