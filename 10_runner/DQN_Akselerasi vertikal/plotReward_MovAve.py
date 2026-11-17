import json
import matplotlib.pyplot as plt
import numpy as np
import os

def plot_training_results(checkpoint_file='training_checkpoint.json', max_episodes=270):
    if not os.path.exists(checkpoint_file):
        print(f"❌ File {checkpoint_file} tidak ditemukan!")
        return

    print("Memuat data training...")
    with open(checkpoint_file, 'r') as f:
        data = json.load(f)
    
    rewards = data.get('all_rewards', [])
    
    if not rewards:
        print("❌ Tidak ada data reward di dalam file checkpoint.")
        return
        
    # Memotong data reward hanya hingga batas maksimum (280)
    rewards = rewards[:max_episodes]
    episodes = range(1, len(rewards) + 1)
    
    # Menghitung Moving Average (Rata-rata bergerak) untuk memperhalus grafik
    # Karena grafik DRL biasanya sangat berisik (naik turun tajam)
    window = 3  # Rata-rata dari 5 episode terakhir
    moving_avg = []
    if len(rewards) >= window:
        moving_avg = np.convolve(rewards, np.ones(window)/window, mode='valid')

    # Membuat figure matplotlib
    plt.figure(figsize=(10, 6))
    
    # Plot reward asli (dibuat agak transparan agar tidak menutupi garis rata-rata)
    plt.plot(episodes, rewards, alpha=0.3, color='dodgerblue', label='Raw Reward per Episode')
    
    # Plot Moving Average (Garis utama yang menunjukkan tren belajar AI)
    if len(moving_avg) > 0:
        plt.plot(range(window, len(rewards) + 1), moving_avg, color='crimson', 
                 linewidth=2.5, label=f'Trendline (Moving Average {window})')

    # Kustomisasi tampilan grafik
    plt.title(f'DQN Training Performance (Up to Episode {max_episodes})', fontsize=14, fontweight='bold')
    plt.xlabel('Episode', fontsize=12)
    plt.ylabel('Total Cumulative Reward', fontsize=12)
    
    # Memastikan sumbu X tidak melebihi batas episode
    plt.xlim(0, max_episodes + 10)
    
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(loc='lower right', fontsize=10)
    plt.tight_layout()

    # Simpan sebagai file gambar berkualitas tinggi
    output_filename = 'training_reward_graph_280.png'
    plt.savefig(output_filename, dpi=300)
    print(f"✅ Grafik berhasil disimpan sebagai '{output_filename}'")
    
    # Tampilkan jendela grafik
    plt.show()

if __name__ == '__main__':
    plot_training_results()