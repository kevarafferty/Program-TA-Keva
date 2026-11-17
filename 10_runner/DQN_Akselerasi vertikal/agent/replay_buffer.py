from collections import deque
import numpy as np
import random

class ReplayBuffer:
    """
    Experience Replay Buffer untuk DQN
    Menyimpan transitions: (state, action, reward, next_state, done)
    """
    
    def __init__(self, capacity=10000):
        """
        Args:
            capacity: Maximum number of experiences to store
        """
        self.buffer = deque(maxlen=capacity)
        print(f"📦 Replay Buffer created (capacity: {capacity:,})")
    
    def add(self, state, action, reward, next_state, done):
        """
        Tambahkan experience ke buffer
        Args:
            state: dict with 'image' and 'vehicle_state'
            action: int
            reward: float
            next_state: dict with 'image' and 'vehicle_state'
            done: bool
        """
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size=32):
        """
        Sample random batch dari buffer
        Args:
            batch_size: Number of samples to return
        Returns:
            dict with batched arrays
        """
        if len(self.buffer) < batch_size:
            batch_size = len(self.buffer)
        
        batch = random.sample(self.buffer, batch_size)
        
        # Separate components
        states = {'image': [], 'vehicle_state': []}
        actions = []
        rewards = []
        next_states = {'image': [], 'vehicle_state': []}
        dones = []
        
        for s, a, r, ns, d in batch:
            states['image'].append(s['image'])
            states['vehicle_state'].append(s['vehicle_state'])
            actions.append(a)
            rewards.append(r)
            next_states['image'].append(ns['image'])
            next_states['vehicle_state'].append(ns['vehicle_state'])
            dones.append(d)
        
        # Convert to numpy arrays
        return {
            'states': {
                'image': np.array(states['image']),
                'vehicle_state': np.array(states['vehicle_state'])
            },
            'actions': np.array(actions),
            'rewards': np.array(rewards, dtype=np.float32),
            'next_states': {
                'image': np.array(next_states['image']),
                'vehicle_state': np.array(next_states['vehicle_state'])
            },
            'dones': np.array(dones, dtype=np.float32)
        }
    
    def __len__(self):
        """Return current size of buffer"""
        return len(self.buffer)
    
    def clear(self):
        """Clear all experiences"""
        self.buffer.clear()
        print("🗑️  Replay buffer cleared")