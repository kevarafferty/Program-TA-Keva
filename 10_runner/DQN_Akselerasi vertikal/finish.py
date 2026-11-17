from environment.carla_env import CarlaEnv
import time

def test_finish_line():
    print("Mulai Test Run Garis Finish Virtual...")
    # Inisialisasi env
    env = CarlaEnv(town='train_fix')
    
    env.reset()
    done = False
    step_count = 0
    total_reward = 0.0
    
    print("Mobil melaju gas penuh (Action 3)...")
    while not done:
        # Gunakan Action 3 (Faster - throttle 0.6) agar mensimulasikan 
        # kondisi training yang bikin mobil cepat sampai tembok
        state, reward, done, info = env.step(action=3)
        total_reward += reward
        step_count += 1
        
        # Tampilkan progress kecepatan setiap 20 step
        if step_count % 20 == 0:
            speed = env.vehicle_state['speed']
            print(f"Step: {step_count} | Speed: {speed:.1f} km/h")
            
        # PENGAMAN JAGA-JAGA: Kalau lewat 1500 step tapi belum done, paksa stop
        if step_count > 1500:
            print("⚠️ Terlalu lama, sepertinya garis finish gagal dideteksi!")
            break

    print("\n" + "="*50)
    print("🏁 TEST RUN SELESAI 🏁")
    print(f"Episode berhenti pada step ke: {step_count}")
    print(f"Total Reward Akhir: {total_reward:.1f}")
    print("="*50)
    
    env.close()

if __name__ == "__main__":
    test_finish_line()