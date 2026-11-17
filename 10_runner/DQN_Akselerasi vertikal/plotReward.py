import json
import matplotlib.pyplot as plt
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
        
    # Memotong data reward hanya hingga batas maksimum (270)
    rewards = rewards[:max_episodes]
    episodes = range(1, len(rewards) + 1)
    
    # Membuat figure matplotlib
    plt.figure(figsize=(10, 6))
    
    # Plot reward asli tanpa transparansi dan dengan line width lebih tebal
    plt.plot(episodes, rewards, color='dodgerblue', linewidth=2.5, label='Reward per Episode')

    # Kustomisasi tampilan grafik
    plt.title(f'DQN Training Performance', fontsize=14, fontweight='bold')
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