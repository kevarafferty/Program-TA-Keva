import os
from environment.carla_env import CarlaEnv
from agent.dqn_agent import DQNAgent
import numpy as np
import time
import json
import torch


def train(resume=True, num_episodes=100, max_steps=5000):
    """
    Training DRL di Train06 dengan YOLO real pothole detection.
    """
    print("="*60)
    print("  TRAINING DEEP REINFORCEMENT LEARNING - CARLA")
    print("  MAP: Train06 | POTHOLE: YOLO Real Detection")
    print("="*60)
    
    checkpoint_file = 'training_checkpoint.json'
    best_model_file = 'model_best.h5'
    
    if resume and os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        start_episode = checkpoint['episode']
        best_reward = checkpoint['best_reward']
        all_rewards = checkpoint['all_rewards']
        print(f"\n✅ Resume dari episode {start_episode}")
        print(f"   Best reward: {best_reward:.2f}")
    else:
        start_episode = 0
        best_reward = -float('inf')
        all_rewards = []
        print("\n🆕 Mulai training baru")
    
    print("\n📍 Environment Configuration:")
    print("   Town: Train06")
    print("   Spawn: carla.Transform(x=-299.5, y=250.5, z=3, yaw=0)")
    print("   Potholes: YOLO Real Detection (basic plane di UE)")
    
    env = CarlaEnv(
        town='train_fix',
        yolo_model_path='Yolo/best_pure.pt',
        gt_json_path='pothole_gt.json'
    )
    
    agent = DQNAgent(
        num_actions=env.num_actions,
        replay_capacity=10000
    )
    
    if resume and os.path.exists(best_model_file):
        try:
            agent.load(best_model_file)
            print(f"✅ Loaded: {best_model_file}")
        except Exception as e:
            print(f"⚠️  Tidak bisa load model: {e}")
            response = input("\n   Backup dan mulai fresh? (y/n): ")
            if response.lower() == 'y':
                import shutil
                shutil.move(best_model_file, best_model_file.replace('.h5', '_backup.h5'))
                start_episode = 0
                best_reward = -float('inf')
                all_rewards = []
            else:
                env.close()
                return
    
    print(f"\n📊 Training Config:")
    print(f"   Episodes: {num_episodes} | Steps: {max_steps}")
    print(f"   Start Episode: {start_episode + 1}")
    print(f"   Epsilon: {agent.epsilon:.3f}")
    
    try:
        for episode in range(start_episode, num_episodes):
            print(f"\n{'='*60}")
            print(f"EPISODE {episode + 1}/{num_episodes}")
            print(f"{'='*60}")
            
            state = env.reset()
            episode_reward = 0
            episode_losses = []
            
            # --- INFO PENGGANTI FLAG: Counter didapatkan dari env.step() ---
            current_hits = 0
            current_avoids = 0
            
            for step in range(max_steps):
                action = agent.select_action(state)
                
                # --- PERUBAHAN: Unpack 4 values dari env.step ---
                next_state, reward, done, info = env.step(action)
                
                current_hits = info['hits']
                current_avoids = info['avoids']
                
                agent.store_experience(state, action, reward, next_state, done)
                loss = agent.train_step()
                if loss is not None:
                    episode_losses.append(loss)
                
                state = next_state
                episode_reward += reward
                
                if (step + 1) % 100 == 0:
                    avg_loss = np.mean(episode_losses[-100:]) if episode_losses else 0
                    print(f"  Step {step+1:4d}/{max_steps} | "
                          f"Reward: {episode_reward:8.1f} | "
                          f"Loss: {avg_loss:.4f} | "
                          f"ε: {agent.epsilon:.3f} | "
                          f"Hits: {current_hits} | Avoids: {current_avoids}")
                
                if done:
                    print(f"  💥 Episode selesai di step {step+1} (collision)")
                    break
            
            # Bersihkan memori GPU di akhir setiap episode
            torch.cuda.empty_cache()
            
            avg_loss = np.mean(episode_losses) if episode_losses else 0
            all_rewards.append(episode_reward)
            
            pothole_encounters = current_hits + current_avoids
            avoid_rate = (current_avoids / max(pothole_encounters, 1)) * 100
            
            print(f"\n📊 EPISODE {episode+1} SUMMARY:")
            print(f"   Total Reward: {episode_reward:.2f}")
            print(f"   Avg Loss: {avg_loss:.4f}")
            print(f"   Steps: {step + 1}")
            print(f"   Epsilon: {agent.epsilon:.3f}")
            print(f"   Pothole Hits: {current_hits}")
            print(f"   Pothole Avoided: {current_avoids} ({avoid_rate:.0f}%)")
            print(f"   Replay Buffer: {len(agent.replay_buffer)}")
            
            if len(all_rewards) >= 5:
                avg_last5 = np.mean(all_rewards[-5:])
                print(f"   Avg Reward (last 5): {avg_last5:.2f}")
            
            if episode_reward > best_reward:
                best_reward = episode_reward
                agent.save(best_model_file)
                print(f"   🔥 NEW BEST! Reward: {best_reward:.2f}")
            
            checkpoint = {
                'episode': episode + 1,
                'best_reward': best_reward,
                'all_rewards': all_rewards,
                'epsilon': agent.epsilon,
                'step_count': agent.step_count
            }
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            
            if (episode + 1) % 100 == 0:
                backup_file = f'model_episode_{episode+1}.h5'
                agent.save(backup_file)
                print(f"   💾 Backup: {backup_file}")
        
        print(f"\n{'='*60}")
        print("🎉 TRAINING SELESAI!")
        print(f"   Best Reward: {best_reward:.2f}")
        print(f"   Total Episodes: {len(all_rewards)}")
        agent.save('model_final.h5')
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Dihentikan (Ctrl+C)")
        checkpoint = {
            'episode': episode,
            'best_reward': best_reward,
            'all_rewards': all_rewards,
            'epsilon': agent.epsilon,
            'step_count': agent.step_count
        }
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        print(f"   Progress tersimpan di: {checkpoint_file}")
    
    finally:
        env.close()
        print("👋 Environment ditutup.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Train DQN di CARLA Train06')
    parser.add_argument('--resume', action='store_true', help='Resume dari checkpoint')
    parser.add_argument('--new', action='store_true', help='Mulai training baru')
    parser.add_argument('--episodes', type=int, default=750)
    parser.add_argument('--steps', type=int, default=10000)
    args = parser.parse_args()
    
    if args.new:
        if os.path.exists('training_checkpoint.json'):
            os.remove('training_checkpoint.json')
            print("🗑️  Checkpoint dihapus.")
    
    print("\n🚗 CARLA DRL TRAINING - Train06 + YOLO Real Potholes")
    print("=" * 60)
    print("⚠️  Pastikan:")
    print("   1. CARLA sudah running (UE build)")
    print("   2. Map Train06 tersedia")
    print("   3. Lubang (basic plane) sudah ada di sekitar spawn point")
    print("   4. YOLO model: Yolo/best_pure.pt")
    print("=" * 60)
    input("\nTekan ENTER untuk mulai...")
    
    train(
        resume=not args.new,
        num_episodes=args.episodes,
        max_steps=args.steps
    )