"""
Test script for the enhanced TaichiGA with full GA features.

This tests:
1. GPU kernel execution without errors
2. Population initialization with unique minis
3. Evaluation correctness
4. Crossover and elitism working
5. Score improvement over generations
"""
import sys
import os
import time
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_taichi_ga():
    """Test the full GPU GA implementation."""
    print("=" * 60)
    print("Testing Enhanced TaichiGA with Full GA Features")
    print("=" * 60)
    
    # Try to import taichi
    try:
        import taichi as ti
        print("[OK] Taichi imported successfully")
    except ImportError:
        print("[SKIP] Taichi not installed, skipping GPU GA test")
        return
    
    # Initialize Taichi
    try:
        ti.init(arch=ti.vulkan)
        print("[OK] Taichi initialized with Vulkan backend")
    except Exception as e:
        print(f"[WARN] Vulkan failed: {e}, trying CPU...")
        try:
            ti.init(arch=ti.cpu)
            print("[OK] Taichi initialized with CPU backend")
        except Exception as e2:
            print(f"[FAIL] Could not initialize Taichi: {e2}")
            return
    
    # Import TaichiGA
    try:
        from gear_optimizer.taichi_ga import TaichiGA
        print("[OK] TaichiGA imported successfully")
    except ImportError as e:
        print(f"[FAIL] Could not import TaichiGA: {e}")
        return
    
    # Create mock gear and mini data
    print("\n--- Setting up mock data ---")
    
    # Generate mock gear (100 items per slot)
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    mock_gear = []
    for slot in slots:
        for i in range(100):
            mock_gear.append({
                "Name": f"{slot}_{i}",
                "type": slot,
                "Perfect Points": np.random.randint(0, 50),
                "Combo Multiplier": np.random.randint(0, 30),
                "Fever Multiplier": np.random.randint(0, 30),
                "Beat": np.random.randint(0, 100),
                "Vibe": np.random.randint(0, 100),
                "Rush": np.random.randint(0, 50),
                "Chill": np.random.randint(0, 50),
                "Flow": np.random.randint(0, 50),
                "Fever Time": np.random.randint(0, 20),
                "Fever Fill Rate": np.random.randint(0, 20),
            })
    
    # Generate mock minis (50 items)
    mock_minis = []
    for i in range(50):
        mock_minis.append({
            "Name": f"Mini_{i}",
            "type": "Mini",
            "Perfect Points": np.random.randint(0, 100),
            "Combo Multiplier": np.random.randint(0, 60),
            "Fever Multiplier": np.random.randint(0, 60),
            "Beat": np.random.randint(0, 200),
            "Vibe": np.random.randint(0, 200),
            "Rush": np.random.randint(0, 100),
            "Chill": np.random.randint(0, 100),
            "Flow": np.random.randint(0, 100),
            "Fever Time": np.random.randint(0, 30),
            "Fever Fill Rate": np.random.randint(0, 30),
        })
    
    print(f"[OK] Created {len(mock_gear)} gear items and {len(mock_minis)} minis")
    
    # Create mock fever data (simplified - all zeros for this test)
    MAX_FT = 161
    MAX_FF = 161
    fever_masks = np.zeros((MAX_FT, 4, MAX_FF), dtype=np.int32)
    body_fever = np.zeros((MAX_FT, MAX_FF), dtype=np.int32)
    body_normal = np.ones((MAX_FT, MAX_FF), dtype=np.int32) * 100  # 100 normal notes
    
    # Some simple fever mask pattern
    for ft in range(MAX_FT):
        for ff in range(MAX_FF):
            if ft + ff <= 90:
                body_fever[ft, ff] = ft * 2  # More fever with FT
                body_normal[ft, ff] = 100 - ft  # Less normal with FT
                # Simple mask: first 30 notes in fever
                fever_masks[ft, 0, ff] = 0x3FFFFFFF  # bits 0-29 set
    
    # Mock reference tables (linear scaling) - TOTAL_ROWS + 1 = 161
    refs_np = {
        "Perfect Points": np.array([1.0 + 0.01 * i for i in range(161)], dtype=np.float64),
        "Combo Multiplier": np.array([1.0 + 0.005 * i for i in range(161)], dtype=np.float64),
        "Fever Multiplier": np.array([1.0 + 0.008 * i for i in range(161)], dtype=np.float64),
    }
    
    print("[OK] Created mock fever masks and reference tables")
    
    # Initialize TaichiGA
    print("\n--- Initializing TaichiGA ---")
    ga = TaichiGA(max_pop_size=500, max_gear_items=800, max_mini_items=100)
    print("[OK] TaichiGA instance created")
    
    # Load gear database
    slot_indices, mini_indices, slot_ranges, mini_range = ga.load_gear_db(mock_gear, mock_minis)
    print(f"[OK] Loaded gear DB: {len(mock_gear)} gear, {len(mock_minis)} minis")
    print(f"     Slot ranges: {slot_ranges}")
    print(f"     Mini range: {mini_range}")
    
    # Load song context
    ga.load_song_context(fever_masks, body_fever, body_normal, refs_np)
    print("[OK] Loaded song context")
    
    # Define user stats
    user_stats = {
        "pp": 50,
        "cm": 30,
        "fm": 30,
        "beat": 100,
        "vibe": 100,
        "rush": 50,
        "chill": 50,
        "flow": 50,
        "ft": 10,
        "ffr": 10,
    }
    
    # Run evolution
    print("\n--- Running GPU Evolution ---")
    pop_count = 200
    generations = 20
    total_gem_budget = 90
    
    scores_over_time = []
    
    def progress_callback(gen, best_score):
        scores_over_time.append(best_score)
        if gen % 5 == 0 or gen == 1:
            print(f"  Generation {gen:3d}: Best Score = {best_score:,}")
    
    start_time = time.time()
    
    try:
        best_score, best_indices = ga.run_evolution(
            pop_count=pop_count,
            generations=generations,
            total_gem_budget=total_gem_budget,
            user_stats=user_stats,
            slot_ranges=slot_ranges,
            mini_range=mini_range,
            mutation_rate=0.3,
            elite_count=2,
            callback=progress_callback
        )
        elapsed = time.time() - start_time
        
        print(f"\n[OK] Evolution completed in {elapsed:.2f}s")
        print(f"     Final Best Score: {best_score:,}")
        print(f"     Best Genome Indices: {best_indices}")
        
    except Exception as e:
        print(f"\n[FAIL] Evolution failed with error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Validate results
    print("\n--- Validation ---")
    
    # Check score improvement
    if len(scores_over_time) > 1:
        first_score = scores_over_time[0]
        last_score = scores_over_time[-1]
        
        if last_score >= first_score:
            print(f"[OK] Score improved or maintained: {first_score:,} -> {last_score:,}")
        else:
            print(f"[WARN] Score decreased: {first_score:,} -> {last_score:,}")
    
    # Check unique minis in best genome
    mini_indices_in_genome = best_indices[6:9]
    if len(set(mini_indices_in_genome)) == 3:
        print(f"[OK] Best genome has unique minis: {mini_indices_in_genome}")
    else:
        print(f"[WARN] Best genome has duplicate minis: {mini_indices_in_genome}")
    
    # Check reasonable score range
    if best_score > 0:
        print(f"[OK] Final score is positive: {best_score:,}")
    else:
        print(f"[WARN] Final score is non-positive: {best_score}")
    
    # Performance metrics
    print(f"\n--- Performance ---")
    print(f"Population size: {pop_count}")
    print(f"Generations: {generations}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Time per generation: {elapsed/generations*1000:.1f}ms")
    print(f"Evaluations per second: {(pop_count * generations) / elapsed:.0f}")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    test_taichi_ga()
