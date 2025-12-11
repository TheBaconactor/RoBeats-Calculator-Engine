
import os
import sys
import numpy as np

# Setup path to import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.scoring import solve_best_fever_combination
from gear_optimizer.utils import cfg_to_dict

def run_debug():
    print("Loading App...")
    app = GearOptimizerApp("config.ini")
    app.setup()
    
    # Target Song
    song_name = "Area XVIII (Hard) by Ardolf vs. Egg Yolk"
    
    # Find song file
    song_path = None
    for item in app.all_gears: # dummy iter
        break
        
    # We need to find the song in the queue or scan folders?
    # Let's brute force scan JobQueue paths
    from gear_optimizer.job_queue import JobQueue
    jq = JobQueue(app.paths, app.cfg)
    for job in jq.get_jobs():
        if job.song_name == song_name:
            song_path = job.file_path
            break
            
    if not song_path:
        print(f"Song '{song_name}' not found!")
        return

    print(f"Found Song: {song_path}")
    
    # Read Song
    from gear_optimizer.song_processor import read_song_file
    song_data = read_song_file(song_path)
    song_data["timestamps"] = np.array(song_data["timestamps"], dtype=np.float64)
    
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_data["timestamps"]}
    }
    
    # Construct Loadout
    # Hat: Legendary Flow Commander's Helmet
    # Neck: Legendary Beat Cyborg's Control Panel
    # Face: Legendary Beat Cyborg's Goggles
    # Shirt: Legendary Beat Cyborg's Jumpsuit
    # Back: Legendary Beat Cyborg's Jetpack
    # Pants: Legendary Beat Cyborg's Jumpsuit Pants
    # Minis: Artcore Maid Marie, Project Skylate, New Year's Bunny-Girl Zara
    
    gear_names = [
        "Legendary Flow Commander's Helmet",
        "Legendary Beat Cyborg's Control Panel",
        "Legendary Beat Cyborg's Goggles",
        "Legendary Beat Cyborg's Jumpsuit",
        "Legendary Beat Cyborg's Jetpack",
        "Legendary Beat Cyborg's Jumpsuit Pants"
    ]
    
    mini_names = [
        "Artcore Maid Marie",
        "Project Skylate",
        "New Year's Bunny-Girl Zara"
    ]
    
    loadout_items = []
    for gn in gear_names:
        g = app.gears_by_name.get(gn)
        if not g:
            print(f"Missing Gear: {gn}")
        else:
            loadout_items.append(g)
            
    for mn in mini_names:
        m = app.minis_by_name.get(mn)
        if not m:
            print(f"Missing Mini: {mn}")
        else:
            loadout_items.append(m)
            
    # Calculate Base Stats
    base_stats_fixed = {k: 0 for k in ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Beat", "Vibe", "Rush", "Chill", "Flow", "Fever Time", "Fever Fill Rate"]}
    
    # Add manual adjustments for song config? (Assuming defaults 0 as per log "NonFever: 0")
    # Actually setup_song_config adds them. We should assume defaults.
    
    final_stats = base_stats_fixed.copy()
    for item in loadout_items:
        for k in base_stats_fixed:
            final_stats[k] += item.get(k, 0)
            
    # Manual T5 Buffs (Flow)
    # T5: {"PP": 25, "Elem": 30}
    final_stats["Perfect Points"] += 25
    final_stats["Flow"] += 30
            
    print("Base Stats:", final_stats)
    
    # Run Solver
    # Use override_cfg matching log
    override_stats = {
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "selected_color": "Flow", # From log "Team Color: Flow"
        "static_elem_input": 0 # Default
    }
    
    print("Solving...")
    res = solve_best_fever_combination(
        None,
        final_stats,
        calc_song,
        app.ref_arrays,
        silent=False,
        override_cfg=override_stats
    )
    

    print("\nXXX RESULTS XXX")
    print(f"Score: {res['Score']}")
    print(f"FT: {res.get('FT', '?')}")
    print(f"GemCounts: {res.get('GemCounts', {})}")
    
    # --- F32 Precision Test ---
    print("\nXXX F32 EMULATION TEST XXX")
    from math import floor
    
    # Reconstruct exact situation from solver result (or defaults)
    # Using the result stats
    # Recalculate 'fast_calculate_score' logic using F32
    
    stats = res.get("Stats", final_stats)
    ft = res.get("FT", 0)
    ff = res.get("FF", 0)
    
    # We need timestamps (mocked from song)
    timestamps = calc_song["song_data"]["timestamps"]
    
    # We need the multipliers (looked up)
    # Ref arrays
    refs = app.ref_arrays
    
    def lookup(full_key, val):
        arr = refs[full_key]
        idx = int(val)
        if idx >= len(arr): return arr[-1]
        return arr[idx]
        
    ft_fac = lookup("Fever Time", stats["Fever Time"])
    ff_fac = lookup("Fever Fill Rate", stats["Fever Fill Rate"])
    
    # Calculate timeline (assumed robust)
    from gear_optimizer.scoring import calculate_fever_timeline_indices
    mask = np.zeros(len(timestamps), dtype=np.bool_)
    f_mask, c_fever, c_normal, _ = calculate_fever_timeline_indices(
        timestamps, len(timestamps), ff_fac, ft_fac,
        int(calc_song["metadata"].get("Long Notes", 0)),
        float(calc_song["metadata"].get("Last Note Time", timestamps[-1])),
        mask
    )
    
    # Stats
    pp_val = lookup("Perfect Points", stats["Perfect Points"])
    cm_val = lookup("Combo Multiplier", stats["Combo Multiplier"])
    fm_val = lookup("Fever Multiplier", stats["Fever Multiplier"])
    
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    p_val = stats.get(p_color, 0)
    s_val = stats.get(s_color, 0)
    
    base = (p_val * 2) + s_val + pp_val
    
    print(f"Base: {base}, CM: {cm_val}, FM: {fm_val}")
    print(f"Body Fever: {c_fever}, Body Normal: {c_normal}, Head Fever: {np.sum(f_mask)}")
    
    def calc_f64():
        b = float(base)
        c = float(cm_val)
        f = float(fm_val)
        
        cv = floor(b * c)
        fv = floor(b * c * f)
        
        body = (c_fever * fv) + (c_normal * cv)
        
        # Head
        factor = (c - 1.0) * b / 100.0
        head = 0.0
        for i in range(len(f_mask)):
            ramp = b + ((i+1) * factor)
            if f_mask[i]:
                head += floor(ramp * f)
            else:
                head += floor(ramp)
        return int(body + head)
        
    def calc_f32():
        b = np.float32(base)
        c = np.float32(cm_val)
        f = np.float32(fm_val)
        
        # Emulate Taichi/GPU ops
        cv = np.floor(b * c)
        fv = np.floor(b * c * f)
        
        body = (c_fever * fv) + (c_normal * cv)
        
        factor = (c - np.float32(1.0)) * b / np.float32(100.0)
        head = np.float32(0.0)
        
        for i in range(len(f_mask)):
            idx_f32 = np.float32(i + 1)
            # ramp = base + (idx * factor)
            ramp = b + (idx_f32 * factor)
            if f_mask[i]:
                head += np.floor(ramp * f)
            else:
                head += np.floor(ramp)
        return int(body + head)
        
    sh64 = calc_f64()
    sh32 = calc_f32()
    
    print(f"Manual F32: {sh32}")
    print(f"Delta: {sh64 - sh32}")
    
    # --- Logic Variant Tests ---
    print("\nXXX LOGIC VARIANT TESTS XXX")
    
    def calc_variant_A_nested_floor():
        """Test: floor(floor(base * combo) * fever) instead of floor(base * combo * fever)"""
        b = float(base)
        c = float(cm_val)
        f = float(fm_val)
        
        cv = floor(b * c)
        # Variant: Apply fever to the ALREADY combo-multiplied note value
        fv = floor(cv * f) 
        
        body = (c_fever * fv) + (c_normal * cv)
        
        # Head logic - usually follows body logic logic?
        # Standard: ramp value is virtual base.
        factor = (c - 1.0) * b / 100.0
        head = 0.0
        for i in range(len(f_mask)):
            ramp = b + ((i+1) * factor)
            # Apply same logic? or just floor(ramp)?
            # If fever: 
            if f_mask[i]:
                # Current: floor(ramp * f)
                # Variant: floor(floor(ramp) * f) ? Unlikely for head ramp
                # Let's try matching the body change:
                # But head notes DON'T have combo mul fully applied yet? 
                # Actually ramp IS the combo-scaled value.
                val = floor(ramp * f)
            else:
                val = floor(ramp)
            head += val
        return int(body + head)

    def calc_variant_B_head_rounding():
        """Test: Round ramp value before multiply?"""
        b = float(base)
        c = float(cm_val)
        f = float(fm_val)
        cv = floor(b * c)
        fv = floor(b * c * f)
        body = (c_fever * fv) + (c_normal * cv)
        
        factor = (c - 1.0) * b / 100.0
        head = 0.0
        for i in range(len(f_mask)):
            ramp = b + ((i+1) * factor)
            if f_mask[i]:
                # Variant: floor(floor(ramp) * f)
                val = floor(floor(ramp) * f)
            else:
                val = floor(ramp)
            head += val
        return int(body + head)

    def calc_variant_C_combo_precision():
        """Test: floor(base * combo) for body normal, but maybe fever uses direct mul?"""
        # Unlikely. 
        # try the 'Variant A' logic?
        pass

    var_a = calc_variant_A_nested_floor()
    var_b = calc_variant_B_head_rounding()
    
    print(f"Variant A (Nested Floor Body): {var_a} (Delta: {var_a - 48079503})")
    print(f"Variant B (Nested Floor Head): {var_b} (Delta: {var_b - 48079503})")
    
    if var_a == 48079503:
        print(">>> MATCH FOUND: Variant A")
    def calc_variant_C_perm():
        """Test: floor(base * floor(c * f))"""
        b = float(base)
        c = float(cm_val)
        f = float(fm_val)
        fv = floor(b * floor(c * f)) # Unlikely
        cv = floor(b * c)
        body = (c_fever * fv) + (c_normal * cv)
        
        factor = (c - 1.0) * b / 100.0
        head = 0.0
        for i in range(len(f_mask)):
            ramp = b + ((i+1) * factor)
            if f_mask[i]:
                head += floor(ramp * f)
            else:
                head += floor(ramp)
        return int(body + head)
        
    def calc_variant_D_head_trunc():
        """Test: Using float32 ONLY in head loop but float64 in body?"""
        # Users often see discrepancies in loops
        b = float(base)
        c = float(cm_val)
        f = float(fm_val)
        
        cv = floor(b * c)
        fv = floor(b * c * f)
        body = (c_fever * fv) + (c_normal * cv)
        
        factor = (c - 1.0) * b / 100.0
        head = 0.0
        for i in range(len(f_mask)):
            ramp = b + ((i+1) * factor)
            if f_mask[i]:
                # What if `ramp * f` loses precision?
                head += floor( np.float32(ramp) * np.float32(f) )
            else:
                head += floor(ramp)
        return int(body + head)
        
    def calc_variant_E_mixed():
        # Maybe head uses variant A logic?
        b = float(base)
        c = float(cm_val)
        f = float(fm_val)
        fv = floor(b * c * f)
        cv = floor(b * c)
        body = (c_fever * fv) + (c_normal * cv)
        
        factor = (c - 1.0) * b / 100.0
        head = 0.0
        for i in range(len(f_mask)):
            ramp = b + ((i+1) * factor)
            if f_mask[i]:
                # Variant A for head: floor(floor(ramp) * f)
                head += floor(floor(ramp) * f)
            else:
                head += floor(ramp)
        return int(body + head)

    var_c = calc_variant_C_perm()
    var_d = calc_variant_D_head_trunc()
    var_e = calc_variant_E_mixed()
    
    print(f"Variant C (Permuted Floor): {var_c} (Delta: {var_c - 48079503})")
    print(f"Variant D (Head F32): {var_d} (Delta: {var_d - 48079503})")
    print(f"Variant E (Head Nested Floor): {var_e} (Delta: {var_e - 48079503})")

    print(f"Variant E (Head Nested Floor): {var_e} (Delta: {var_e - 48079503})")

    # --- Margin Analysis ---
    print("\nXXX MARGIN ANALYSIS XXX")
    # Check how close the head notes are to the next integer
    b = float(base)
    c = float(cm_val)
    f = float(fm_val)
    factor = (c - 1.0) * b / 100.0
    
    close_calls = 0
    min_dist_up = 1.0
    min_dist_down = 1.0
    
    for i in range(len(f_mask)):
        ramp = b + ((i+1) * factor)
        if f_mask[i]:
            val_exact = ramp * f
        else:
            val_exact = ramp
            
        val_floor = floor(val_exact)
        frac = val_exact - val_floor
        
        # Distance to next int
        dist_up = 1.0 - frac
        
        if dist_up < 0.001:
            # Very close to rounding UP (e.g. 1900.999)
            # This is where floating point jitter causes it to miss the threshold
            close_calls += 1
            print(f"Index {i}: {val_exact:.10f} (Frac: {frac:.10f}) -> Needs {dist_up:.10f} to round up")
        
        min_dist_up = min(min_dist_up, dist_up)
        min_dist_down = min(min_dist_down, frac)

    print(f"Close calls (dist < 0.001): {close_calls}")
    print(f"Min Dist Up: {min_dist_up:.10f}")
    print(f"Min Dist Down: {min_dist_down:.10f}")
    
    # Test proposed epsilon for F32 safety
    # F32 machine epsilon is ~1.19e-7
    # Calculations can accumulate error larger than that.
    # 1e-5 is a safe generic epsilon for F32 math.
    
    if close_calls > 0:
        print(f"Recommendation: Epsilon must be > {min_dist_up}")

if __name__ == "__main__":
    run_debug()

