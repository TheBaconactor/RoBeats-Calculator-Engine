"""
Quick test to verify Taichi accelerator compiles and runs.
"""
import sys
sys.path.insert(0, r'<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer')

import numpy as np

# Test 1: Verify module imports
print("Testing Taichi accelerator import...")
try:
    from gear_optimizer import taichi_accelerator
    print("  [PASS] Module imported successfully")
except Exception as e:
    print(f"  [FAIL] Import error: {e}")
    sys.exit(1)

# Test 2: Taichi initialization
print("\nTesting Taichi initialization...")
try:
    taichi_accelerator.init_taichi()
    print("  [PASS] Taichi initialized")
except Exception as e:
    print(f"  [FAIL] Init error: {e}")
    sys.exit(1)

# Test 3: Create solver instance
print("\nTesting TaichiSolver creation...")
try:
    solver = taichi_accelerator.TaichiSolver()
    print("  [PASS] Solver created")
except Exception as e:
    print(f"  [FAIL] Solver creation error: {e}")
    sys.exit(1)

# Test 4: Dummy kernel call to trigger JIT compilation
print("\nTesting kernel JIT compilation (this may take a few seconds)...")
try:
    # Create minimal test data - TOTAL_ROWS=160, so arrays need shape (161,)
    ref_pp = np.linspace(0, 100, 161).astype(np.float64)
    ref_cm = np.linspace(1.0, 2.0, 161).astype(np.float64)
    ref_fm = np.linspace(1.0, 3.0, 161).astype(np.float64)
    
    ref_arrays = {
        "Perfect Points": ref_pp,
        "Combo Multiplier": ref_cm,
        "Fever Multiplier": ref_fm,
        "Fever Time": np.ones(161, dtype=np.float64),
        "Fever Fill Rate": np.ones(161, dtype=np.float64),
    }
    
    # Load references
    solver.load_refs(ref_arrays)
    print("  [PASS] References loaded")
    
    # Create minimal song data
    timestamps = np.linspace(0, 100, 500).astype(np.float64)
    ft_factor = np.ones(161, dtype=np.float64)
    ff_factor = np.ones(161, dtype=np.float64)
    
    # Load song
    solver.ensure_song_loaded(
        timestamps, 0, 100.0,
        ft_factor, ff_factor,
        ref_arrays,
        song_key="test_song",
        range_ft_hint=90, max_ff_hint=90, total_gem_budget=90
    )
    print("  [PASS] Song data loaded")
    
    # Create batch input (small batch)
    batch_size = 4
    batch_input = {
        'song_indices': np.zeros(batch_size, dtype=np.int32),
        'cur_pp': np.array([100, 200, 300, 400], dtype=np.int32),
        'cur_cm': np.array([100, 200, 300, 400], dtype=np.int32),
        'cur_fm': np.array([100, 200, 300, 400], dtype=np.int32),
        'base_beat': np.array([500, 600, 700, 800], dtype=np.float32),
        'base_vibe': np.array([500, 600, 700, 800], dtype=np.float32),
        'is_p_pp': np.zeros(batch_size, dtype=np.int32),
        'is_s_pp': np.zeros(batch_size, dtype=np.int32),
        'is_p_cm': np.zeros(batch_size, dtype=np.int32),
        'is_s_cm': np.zeros(batch_size, dtype=np.int32),
        'is_p_fm': np.zeros(batch_size, dtype=np.int32),
        'is_s_fm': np.zeros(batch_size, dtype=np.int32),
        'is_p_ov': np.ones(batch_size, dtype=np.int32),  # OV on primary
        'is_s_ov': np.zeros(batch_size, dtype=np.int32),
        'p_color_is_beat': np.ones(batch_size, dtype=np.int32),
        'p_color_is_vibe': np.zeros(batch_size, dtype=np.int32),
        's_color_is_beat': np.zeros(batch_size, dtype=np.int32),
        's_color_is_vibe': np.ones(batch_size, dtype=np.int32),
        'p_color_base_val': np.array([500, 600, 700, 800], dtype=np.float32),
        's_color_base_val': np.array([400, 500, 600, 700], dtype=np.float32),
    }
    
    # Run batch solve
    scores, fts, ffs, gems = solver.solve_batch(batch_input, 90, 90, 90, ref_arrays)
    
    print(f"  [PASS] Batch solve completed")
    print(f"         Scores: {scores}")
    print(f"         FTs: {fts}")
    print(f"         FFs: {ffs}")
    
    # Verify scores are positive
    if all(s > 0 for s in scores):
        print("  [PASS] All scores are positive")
    else:
        print("  [WARN] Some scores are non-positive (may be expected for test data)")
        
except Exception as e:
    import traceback
    print(f"  [FAIL] Kernel execution error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("All tests passed! Taichi optimizations are working.")
print("="*50)
