import tensorflow as tf
from tensorflow import keras # type: ignore
from tensorflow.keras import layers  # type: ignore


class DQNNetwork(keras.Model):
    """
    MLP-only DQN Network — tanpa CNN branch.

    Input : vehicle_state (10,)
              [0] cx          — pusat horizontal lubang di image (YOLO)
              [1] cy          — pusat vertikal lubang di image (YOLO)
              [2] w           — lebar bounding box (YOLO)
              [3] h           — tinggi bounding box (YOLO)
              [4] severity    — tingkat keparahan lubang (YOLO)
              [5] speed_n     — kecepatan ternormalisasi
              [6] steer_n     — sudut kemudi
              [7] accel_n     — magnitudo akselerasi
              [8] pos_n       — posisi lateral di jalan [-1, +1]
              [9] collision_n — flag collision

    Output: Q-values (num_actions,)
    """

    def __init__(self, num_actions):
        super(DQNNetwork, self).__init__()

        print("Membuat MLP DQN Network (tanpa CNN)...")
        print("  Input : (10,) [YOLO(5) + Vehicle(5)]")
        print(f"  Output: ({num_actions},) Q-values")

        # Layer 1 — pelajari interaksi antar fitur dasar
        self.fc1 = layers.Dense(128, activation='relu', name='fc1')

        # Layer 2 — representasi lebih abstrak
        self.fc2 = layers.Dense(128, activation='relu', name='fc2')

        # Layer 3 — kompresi ke fitur inti
        self.fc3 = layers.Dense(64, activation='relu', name='fc3')

        # Dropout ringan — cegah overfitting tanpa hambat konvergensi
        self.dropout = layers.Dropout(0.1, name='dropout')

        # Output — Q-value per action
        self.output_layer = layers.Dense(num_actions, name='q_values')

        print("✅ Network architecture created!")

    def call(self, inputs, training=False):
        """
        Forward pass.
        Args:
            inputs : tensor (batch, 10) — vehicle_state vector
            training: bool — aktifkan dropout saat training
        Returns:
            q_values: tensor (batch, num_actions)
        """
        x = tf.cast(inputs, tf.float32)
        x = self.fc1(x)
        x = self.fc2(x)
        x = self.fc3(x)
        x = self.dropout(x, training=training)
        return self.output_layer(x)

    def summary_model(self):
        dummy_state = tf.zeros((1, 10))
        _ = self.call(dummy_state)

        total_params = sum([tf.size(w).numpy() for w in self.trainable_variables])
        print("\n" + "="*50)
        print("MODEL SUMMARY — MLP Only")
        print("="*50)
        print(f"Input  : (10,) vector")
        print(f"Params : {total_params:,}")
        print(f"Layers : fc1(128) → fc2(128) → fc3(64) → out({self.output_layer.units})")
        print("="*50)