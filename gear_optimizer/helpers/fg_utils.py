# Hard cap fallbacks to prevent config explosion
# Section 1 can have more FG than section 2, etc. (diminishing returns)
MAX_SECTION_CAPS = [50, 30, 15, 10, 8, 6, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4]

# Mock Scoring Constants for Pruning (Conservative)
MOCK_BASE_SCORE = 1000
MOCK_FEVER_MUL = 3.0
MOCK_PENALTY = 150


def calculate_section_caps(num_sections, non_fever_base, gap=None, fever_activations=None):
    """
    Compute max Forced Greats caps per section.
    
    Args:
        num_sections: Number of non-fever sections
        non_fever_base: Notes in non-fever section (limit)
        gap: Gap value (limit)
        fever_activations: Count of fever windows (limit)
        
    Returns:
        List[int]: Cap for each section
    """
    if num_sections <= 0:
        return []

    caps = []
    actual_base = int(non_fever_base or 0)
    
    # If gap is provided and <= 0, no opportunity - return zeros
    if gap is not None and gap <= 0:
        return [0] * num_sections
    
    # Compute caps per section
    for i in range(num_sections):
        # Sections beyond fever_activations get cap=0 (no benefit from FG there)
        if fever_activations is not None and i >= fever_activations:
            caps.append(0)
            continue
        
        # Get hard cap for this section (diminishing per section)
        hard_cap = MAX_SECTION_CAPS[i] if i < len(MAX_SECTION_CAPS) else 4
        
        # Dynamic cap based on gap (no need to shift more than gap)
        if gap is not None:
            effective = min(actual_base, gap, hard_cap)
        else:
            # Fallback if gap not provided - use hard cap
            effective = min(actual_base, hard_cap)
        
        caps.append(effective)

    return caps


def vectorized_calculate_section_caps_grid(gap_grid, activations_grid, max_per_section=100):
    """
    VECTORIZED: Compute pair_caps_grid (161, 161, 16) from gap and activations grids.
    
    This replaces the 26K-iteration Python loop with NumPy broadcasting,
    achieving ~100x speedup.
    
    Args:
        gap_grid: (161, 161) int array of gap values
        activations_grid: (161, 161) int array of fever activations
        max_per_section: Max notes per section (usually non_fever_base or 100)
        
    Returns:
        (161, 161, 16) int32 array of caps per section
    """
    import numpy as np
    
    grid_h, grid_w = gap_grid.shape
    n_sections = 16
    
    # Hard caps per section (broadcast-ready)
    hard_caps = np.array(MAX_SECTION_CAPS[:n_sections], dtype=np.int32)
    
    # Initialize output: (H, W, 16)
    pair_caps = np.zeros((grid_h, grid_w, n_sections), dtype=np.int32)
    
    # For each section, compute cap as min(hard_cap, gap, max_per_section)
    # But only if section index < activations (otherwise 0)
    for sec in range(n_sections):
        hard_cap = int(hard_caps[sec])
        
        # Base cap: min(hard_cap, gap, max_per_section)
        # Use np.minimum for element-wise min
        base_cap = np.minimum(gap_grid, hard_cap)
        base_cap = np.minimum(base_cap, max_per_section)
        base_cap = np.maximum(base_cap, 0)  # Ensure non-negative
        
        # Zero out where section >= activations
        # activations_grid[i,j] = number of fever windows
        # Section sec is valid only if sec < activations
        mask = sec < activations_grid
        pair_caps[:, :, sec] = np.where(mask, base_cap, 0)
    
    # Zero where gap <= 0 (no FG opportunity)
    no_gap_mask = gap_grid <= 0
    pair_caps[no_gap_mask, :] = 0
    
    return pair_caps


def generate_dynamic_fg_configs(num_sections, non_fever_base, budget=None, gap=None, fever_activations=None):
    """
    Generate a list of FG configs with dynamic caps based on gap.
    
    Uses gap (total_notes - last_fever_end) to limit search space:
    - If gap <= 0: no opportunity (overshoot or at end), return [(0,0,...)] only
    - Otherwise: cap each section by gap (no need to overshoot)
    - Sections beyond fever_activations get cap=0 (no benefit)
    
    Args:
        num_sections: Number of non-fever sections
        non_fever_base: Notes in non-fever section (hard cap by available notes)
        budget: Ignored (kept for API compatibility)
        gap: Gap value (total_notes - last_fever_end). Required for optimal capping.
        fever_activations: Count of fever windows. Sections beyond this get cap=0.
        
    Returns:
        List of tuples, e.g. [(0,), (1,), ...] or [(0,0), (0,1)...]
    """
    caps = calculate_section_caps(num_sections, non_fever_base, gap, fever_activations)
    if not caps:
        return []

    # Generate ranges
    import itertools
    ranges = [range(c + 1) for c in caps]
    
    # Generate all combinations
    return list(itertools.product(*ranges))


def collect_analytic_configs(grid, total_rows=160, stat_bounds=None):
    """
    Collect minimal useful FG configs by analyzing breakpoints on the 161x161 grid.
    
    Instead of simulating all 0..50 counts for every pair, we find 'breakpoints':
    counts that actually change the set of fever-covered notes.
    
    Args:
        grid: SongTimelineGrid instance
        total_rows: Max stat index (usually 160)
        stat_bounds: Optional tuple (min_ft, max_ft, min_ff, max_ff) to restrict search.
                     If None, searches the full 0..total_rows grid.

    Returns:
        List[tuple]: Optimized list of (s0, s1...) tuples.
    """
    import numpy as np
    import itertools
    
    # Per-section sets of useful counts (union across all pairs)
    # We default {0} as always valid/base.
    breakpoints = [set([0]) for _ in range(16)]
    
    # Determine search range
    if stat_bounds:
        min_ft, max_ft, min_ff, max_ff = stat_bounds
        # Clamp to valid grid
        min_ft = max(0, min_ft)
        max_ft = min(total_rows, max_ft)
        min_ff = max(0, min_ff)
        max_ff = min(total_rows, max_ff)
    else:
        min_ft, max_ft = 0, total_rows
        min_ff, max_ff = 0, total_rows

    max_sections = 0
    stride = 10 # Check every 10th stat point

    # Ensure we include the edges of the bounds even if stride misses them?
    # For simplicity, just range(min, max+1, stride)
    
    for ft_idx in range(min_ft, max_ft + 1, stride):
        for ff_idx in range(min_ff, max_ff + 1, stride):
            res_0 = grid.get_timeline(ft_idx, ff_idx)
            acts = res_0[3]
            gap = max(0, grid.total_notes - res_0[4])
            
            if acts > max_sections:
                max_sections = acts
            
            if gap <= 0:
                continue
            
            limit_secs = min(acts, 4)
            for sec in range(limit_secs):
                # Calculate cap for this specific pair
                # We use a localized cap check
                hard_cap = MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4
                effective_cap = min(hard_cap, gap)
                
                prev_mask_fingerprint = (res_0[0], res_0[1]) # (head_bits, body_count)
                
                # Scan 1..Cap
                current_mask_signature = (res_0[0].tobytes(), res_0[1]) # (head_bits_bytes, body_fever)
                
                # Build union of useful breakpoints across all pairs.
                # Each count 'c' is evaluated per-pair to check if it changes the timeline.
                
                for c in range(1, effective_cap + 1):
                    # Construct config: 0 everywhere, c at sec
                    forced_counts_list = [0] * limit_secs
                    forced_counts_list[sec] = c
                    
                    # Simulate
                    mask, cbf, cbn = grid.get_timeline_with_forced(ft_idx, ff_idx, forced_counts_list)
                    
                    new_signature = (mask.tobytes(), cbf)
                    
                    if new_signature != current_mask_signature:
                        # Change detected! Check if it's worth the cost.
                        
                        # Calculate Fever Gain vs Baseline (0 greats = res_0)
                        # res_0[0] is head mask (boolean array?), res_0[1] is body fever
                        # Need to sum head mask
                        base_head = np.sum(res_0[0])
                        base_body = res_0[1]
                        
                        curr_head = np.sum(mask)
                        curr_body = cbf
                        
                        fever_gain_notes = (curr_head + curr_body) - (base_head + base_body)
                        
                        # Gain vs Cost
                        gain_score = fever_gain_notes * MOCK_BASE_SCORE * (MOCK_FEVER_MUL - 1.0)
                        
                        # Cost: Penalty + Fill Penalty?
                        # Grid returns (mask, cbf, cbn). Doesn't explicitly return fill penalty.
                        # But fill penalty reduces score.
                        # Here we assume just basic per-great penalty.
                        cost_score = c * MOCK_PENALTY
                        
                        if gain_score > cost_score:
                             breakpoints[sec].add(c)
                        
                        current_mask_signature = new_signature
                    else:
                        # 'c' produced same result as 'c-1' (or 0). Useless intermediate.
                        pass

    # Sort and return product
    sorted_breakpoints = [sorted(list(bp)) for bp in breakpoints]
    
    # Display up to max_sections (the logical limit for active sections).
    display_limit = max(1, max_sections)
    display_counts = [len(b) for b in sorted_breakpoints[:display_limit]]
    print(f"[FG] Analytic Breakpoints (Active Sections 0-{max_sections-1}): {display_counts}")
    
    # Show explicit values for ALL active sections to demonstrate pruning
    for sec in range(display_limit):
        vals = sorted_breakpoints[sec]
        # Summarize if too long
        if len(vals) > 20:
             val_str = f"{vals[:10]} ... {vals[-5:]}"
        else:
             val_str = str(vals)
        print(f"[FG] Section {sec} (NonFever{sec+1}) Pruned Breakpoints: {val_str}")
    
    # Prune empty tails
    # If a section (e.g. S15) has only {0}, and all subsequent have {0}, we can drop them if we want configs to match active sections.
    # But `generate_dynamic_fg_configs` returns fixed length tuples?
    # No, it returns tuples of length `num_sections`.
    # We should probably return a list of tuples with length = max_sections found.
    
    final_ranges = sorted_breakpoints[:max(1, max_sections)]
    return list(itertools.product(*final_ranges))

