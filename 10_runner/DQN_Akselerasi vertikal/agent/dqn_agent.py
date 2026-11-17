import tensorflow as tf
import numpy as np
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agent.network import DQNNetwork
    from agent.replay_buffer import ReplayBuffer  # NEW IMPORT
except ImportError:
    from network import DQNNetwork
    from replay_buffer import ReplayBuffer  # NEW IMPORT

class DQNAgent:
    """DQN Agent dengan multi-modal input support"""
    
    def __init__(self, num_actions, replay_capacity=10000):  # NEW: replay_capacity param
        print("\n=== Inisialisasi DQN Agent ===")
        
        self.num_actions = num_actions
        
        # Create main network
        self.network = DQNNetwork(num_actions)
        
        # === NEW: Create target network ===
        self.target_network = DQNNetwork(num_actions)
        
        # Build networks dengan dummy input (UPDATED: 10 features)
        dummy_state = np.zeros((1, 10), dtype=np.float32)
        self.network(dummy_state)
        self.target_network(dummy_state)
        
        # Copy weights to target network
        self.update_target_network()  # NEW
        
        # Print model summary
        self.network.summary_model()
        
        # Optimizer
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001)
        
        # === NEW: Replay buffer ===
        self.replay_buffer = ReplayBuffer(capacity=replay_capacity)
        self.batch_size = 32
        self.min_replay_size = 1000  # Minimal samples sebelum training
        
        # Epsilon untuk exploration
        self.epsilon = 1.0
        self.epsilon_min = 0.1
        # ============================================================
        # [PERBAIKAN 4] Perlambat epsilon decay: 0.995 → 0.999
        # LOKASI: dqn_agent.py __init__, self.epsilon_decay
        # ALASAN: Dengan decay=0.995, setelah ~460 train_step epsilon
        #   sudah mendekati 0.1 (min). Artinya sejak awal training,
        #   agen hampir tidak eksplorasi. Agen yang belum tahu cara
        #   bergerak tidak pernah mencoba aksi random yang bisa
        #   menghasilkan reward positif. Dengan 0.999, epsilon baru
        #   mencapai ~0.1 setelah ~2300 step → eksplorasi lebih lama.
        # ============================================================
        self.epsilon_decay = 0.999  # [DIUBAH dari 0.995 ke 0.999]
        
        # === NEW: Target network update ===
        self.target_update_freq = 1000  # Update every N steps
        self.step_count = 0
        
        # Discount factor
        self.gamma = 0.99
        
        print(f"✅ Agent siap!")
        print(f"   Replay buffer capacity: {replay_capacity:,}")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Min replay size: {self.min_replay_size}")
        print(f"   Target update freq: {self.target_update_freq}")
    
    # === NEW FUNCTION ===
    def update_target_network(self):
        """Copy weights dari main network ke target network"""
        self.target_network.set_weights(self.network.get_weights())
        print("🎯 Target network updated")
    
    def select_action(self, state):
        """
        Pilih action: random (explore) atau terbaik (exploit)
        Args:
            state: dict with 'image' and 'vehicle_state'
        """
        if np.random.rand() < self.epsilon:
            # Random action
            action = np.random.randint(self.num_actions)
        else:
            # Best action dari Q-values
            vehicle_state = np.expand_dims(state['vehicle_state'], axis=0)
            
            q_values = self.network(vehicle_state, training=False)
            action = int(np.argmax(q_values[0]))
        
        return action
    
    # === NEW FUNCTION ===
    def store_experience(self, state, action, reward, next_state, done):
        """Store experience di replay buffer"""
        self.replay_buffer.add(state, action, reward, next_state, done)
    
    # === UPDATED FUNCTION: Now uses replay buffer ===
    def train_step(self):
        """
        Training step dengan experience replay
        Returns: loss value atau None jika buffer belum cukup
        """
        # Check jika buffer cukup
        if len(self.replay_buffer) < self.min_replay_size:
            return None
        
        # Sample batch dari replay buffer
        batch = self.replay_buffer.sample(self.batch_size)
        
        vehicle_states      = batch['states']['vehicle_state']
        actions             = batch['actions']
        rewards             = batch['rewards']
        next_vehicle_states = batch['next_states']['vehicle_state']
        dones               = batch['dones']

        with tf.GradientTape() as tape:
            current_q_values = self.network(
                vehicle_states,
                training=True
            )
            next_q_values = self.target_network(
                next_vehicle_states,
                training=False
            )
            
            # Max Q-value untuk next state
            max_next_q = tf.reduce_max(next_q_values, axis=1)
            
            # Target = reward + gamma * max_next_q * (1 - done)
            target_q = rewards + self.gamma * max_next_q * (1 - dones)
            
            # Get Q-values untuk actions yang dipilih
            action_masks = tf.one_hot(actions, self.num_actions)
            q_actions = tf.reduce_sum(current_q_values * action_masks, axis=1)
            
            # Loss: Mean Squared Error
            loss = tf.reduce_mean(tf.square(target_q - q_actions))
        
        # Update weights
        grads = tape.gradient(loss, self.network.trainable_variables)
        self.optimizer.apply_gradients(
            zip(grads, self.network.trainable_variables)
        )
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # === NEW: Update target network periodically ===
        self.step_count += 1
        if self.step_count % self.target_update_freq == 0:
            self.update_target_network()
        
        return float(loss.numpy())
    
    def save(self, filepath):
        """Save model weights"""
        self.network.save_weights(filepath)
        print(f"💾 Model saved to {filepath}")
    
    def load(self, filepath):
        """Load model weights"""
        self.network.load_weights(filepath)
        self.update_target_network()  # NEW: Sync target network
        print(f"✅ Model loaded from {filepath}")