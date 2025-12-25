# Hard cap fallbacks to prevent config explosion
# Section 1 can have more FG than section 2, etc. (diminishing returns)
MAX_SECTION_CAPS = [50, 30, 15, 10, 8, 6, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4]


def _fp_cap_from_forced(scorer, ft_stat: int, ff_stat: int, forced_cap: int) -> int:
    """Convert a forced-count cap into a fill-penalty cap for this FT/FF."""
    if forced_cap <= 0:
        return 0
    # fill_penalty = ceil(raw_base + forced * 0.5) - ceil(raw_base)
    raw_fill = scorer.non_fever_cas * scorer._lookup(scorer.ref_ff, ff_stat)
    
    import numpy as np
    notes_to_fill = np.ceil(raw_fill + forced_cap * 0.5)
    base_notes = np.ceil(raw_fill)
    return int(max(0, notes_to_fill - base_notes))


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
    
    # For each section, compute cap as min(hard_cap, max_per_section)
    # NOTE: Previously also capped by gap_grid, but this caused regressions
    # (e.g., NonFever1=15 was skipped when gap was small at most FT/FF pairs).
    # The analytic breakpoint collector already handles timeline-change detection,
    # so we don't need to double-cap here.
    for sec in range(n_sections):
        hard_cap = int(hard_caps[sec])
        
        # Base cap: min(hard_cap, max_per_section) - no gap capping
        base_cap = min(hard_cap, max_per_section)
        
        # Zero out where section >= activations
        # activations_grid[i,j] = number of fever windows
        # Section sec is valid only if sec < activations
        mask = sec < activations_grid
        pair_caps[:, :, sec] = np.where(mask, base_cap, 0)
    
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


def collect_analytical_breakpoints(scorer, num_sections, section_caps=None, ff_bounds=None):
    """
    Collect minimal FG configs using pure math breakpoint detection.
    
    This replaces the simulation-based collect_analytic_configs with ~100x speedup.
    
    Breakpoints are where fill_penalty changes:
        fill_penalty = ceil(raw_fill + forced * 0.5) - ceil(raw_fill)
    
    Uses the 3 FG rules to limit sections:
    1. Fever overflow: Skip sections where fever extends past song
    2. Gap constraint: Cap FG at min(non_fever_base, gap)
    3. Section activation: Only use sections with fever activations
    
    Args:
        scorer: AnalyticalFGScorer instance
        num_sections: Requested number of sections (may be reduced by analysis)
        section_caps: Optional list of max FG per section. If None, uses analyzed caps.
        ff_bounds: Optional tuple (min_ff, max_ff) to scope breakpoint calculation.
                   If None, uses single representative point (80).
        
    Returns:
        List[tuple]: FG configs to evaluate, e.g. [(0,0), (0,2), (2,0), (2,2), ...]
    """
    import itertools
    
    if num_sections <= 0:
        return [()]
    
    # Use section analysis to get actual useful sections (applying 3 FG rules)
    analysis = scorer.get_section_analysis(80, 80)  # Representative point
    useful_sections = analysis['useful_sections']
    analyzed_caps = analysis['section_caps']
    gap = analysis['gap']
    
    # Limit to useful sections (sections beyond fever_activations have no benefit)
    actual_sections = min(num_sections, useful_sections)
    
    if actual_sections <= 0:
        print(f"[FG] No useful sections (gap={gap}, activations={useful_sections})")
        return [()]
    
    # Use analyzed caps if none provided, with MAX_SECTION_CAPS as backup
    if section_caps is None:
        section_caps = []
        for i in range(actual_sections):
            if i < len(analyzed_caps) and analyzed_caps[i] > 0:
                # Use analyzed cap, but also respect MAX_SECTION_CAPS
                cap = min(analyzed_caps[i], MAX_SECTION_CAPS[i] if i < len(MAX_SECTION_CAPS) else 4)
            else:
                cap = MAX_SECTION_CAPS[i] if i < len(MAX_SECTION_CAPS) else 4
            section_caps.append(cap)
    else:
        section_caps = section_caps[:actual_sections]
    
    # Skip sections with cap=0 entirely
    valid_section_indices = [i for i, cap in enumerate(section_caps) if cap > 0]
    if not valid_section_indices:
        return [()]
    
    # Calculate breakpoints across ALL FF values (0-160)
    # This ensures complete coverage for any gem allocation the GPU might evaluate.
    # Since it's pure math (not simulation), this is still fast.
    ff_samples = range(0, 161, 10)  # Sample every 10th FF value (covers edge cases)
    
    # Collect fill-penalty targets for valid sections only
    section_breakpoints = []
    for sec in range(actual_sections):
        if section_caps[sec] <= 0:
            # Section has no useful FG - just use [0]
            section_breakpoints.append([0])
        else:
            max_fp = 0
            for ff_stat in ff_samples:
                fp_cap = _fp_cap_from_forced(scorer, 80, ff_stat, int(section_caps[sec]))
                if fp_cap > max_fp:
                    max_fp = fp_cap
            section_breakpoints.append(list(range(0, max_fp + 1)))
    
    # Always log breakpoint info
    total_configs = 1
    for bp in section_breakpoints:
        total_configs *= len(bp)
    
    # Show all breakpoints per section
    print(f"[FG] Breakpoints (FP targets): {actual_sections} sections, {total_configs} configs")
    for i, bp in enumerate(section_breakpoints):
        print(f"     Section {i+1}: {bp}")
    
    return list(itertools.product(*section_breakpoints))


def collect_analytical_breakpoint_groups(
    scorer,
    num_sections,
    ftff_pairs,
    base_stats_pairs,
    gem_scale_fever=3,
):
    """
    Build per-FT/FF breakpoint groups for ForceGreatsFinder.

    Returns:
        List[dict]: Each dict has keys:
            "ftff_pairs": list[(ft_gems, ff_gems)]
            "counts_list": list[tuple] of FG configs
    """
    import itertools

    if num_sections <= 0:
        return [{"ftff_pairs": list(ftff_pairs), "counts_list": [()]}] if ftff_pairs else []

    if not ftff_pairs:
        return []

    base_pairs = {(int(ft), int(ff)) for ft, ff in (base_stats_pairs or [])}
    if not base_pairs:
        return []

    groups = {}
    for ft_gems, ff_gems in ftff_pairs:
        max_fp_by_sec = [0 for _ in range(num_sections)]

        for base_ft_stat, base_ff_stat in base_pairs:
            ft_stat = int(base_ft_stat) + int(ft_gems) * int(gem_scale_fever)
            ff_stat = int(base_ff_stat) + int(ff_gems) * int(gem_scale_fever)

            analysis = scorer.get_section_analysis(ft_stat, ff_stat)
            useful_sections = min(num_sections, int(analysis.get("useful_sections", 0) or 0))
            if useful_sections <= 0:
                continue

            analyzed_caps = analysis.get("section_caps") or []
            for sec in range(useful_sections):
                if sec < len(analyzed_caps) and analyzed_caps[sec] > 0:
                    cap = min(
                        int(analyzed_caps[sec]),
                        MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4,
                    )
                else:
                    cap = MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4

                if cap <= 0:
                    continue

                fp_cap = _fp_cap_from_forced(scorer, ft_stat, ff_stat, cap)
                if fp_cap > max_fp_by_sec[sec]:
                    max_fp_by_sec[sec] = fp_cap

        section_breakpoints = tuple(tuple(range(0, max_fp + 1)) for max_fp in max_fp_by_sec)
        group = groups.get(section_breakpoints)
        if group is None:
            counts_list = list(itertools.product(*section_breakpoints))
            group = {
                "ftff_pairs": [],
                "counts_list": counts_list,
                "section_breakpoints": section_breakpoints,
            }
            groups[section_breakpoints] = group

        group["ftff_pairs"].append((int(ft_gems), int(ff_gems)))

    return list(groups.values())


def iter_analytical_breakpoint_groups(
    scorer,
    num_sections,
    ftff_pairs,
    base_stats_pairs,
    gem_scale_fever=3,
    batch_size=20,
    merge_threshold_cfgs=5000,
    merge_threshold_threads=20_000_000,
    n_genomes=1,
):
    """
    Generator version: yields groups incrementally for GPU pipelining.
    
    Uses early streaming decision: after first batch, estimates total work.
    If above thresholds, switches to streaming mode (yield as built).
    If below thresholds, buffers all groups and merges at end.
    
    Args:
        scorer: AnalyticalFGScorer instance
        num_sections: Number of non-fever sections
        ftff_pairs: List of (ft_gems, ff_gems) pairs to evaluate
        base_stats_pairs: Set of (base_ft_stat, base_ff_stat) pairs
        gem_scale_fever: Gem scale for fever stats (default 3)
        batch_size: Number of FT/FF pairs to process per batch (default 20)
        merge_threshold_cfgs: Max configs to allow merge (default 5000)
        merge_threshold_threads: Max threads to allow merge (default 20M)
        n_genomes: Number of genomes (for thread estimation)
    
    Yields:
        dict: Each dict has keys:
            "ftff_pairs": list[(ft_gems, ff_gems)]
            "counts_list": list[tuple] of FG configs
            "section_breakpoints": tuple of breakpoint tuples per section
    """
    import itertools

    if num_sections <= 0:
        if ftff_pairs:
            yield {"ftff_pairs": list(ftff_pairs), "counts_list": [()], "section_breakpoints": ()}
        return

    if not ftff_pairs:
        return

    base_pairs = {(int(ft), int(ff)) for ft, ff in (base_stats_pairs or [])}
    if not base_pairs:
        return

    ftff_pairs = list(ftff_pairs)
    n_pairs = len(ftff_pairs)
    
    # Track groups and decide streaming mode
    all_groups = {}
    all_union_counts = set()
    streaming_mode = False  # Once True, yield groups as they're built
    
    def _process_pair(ft_gems, ff_gems):
        """Process a single FT/FF pair and return its section breakpoints."""
        max_fp_by_sec = [0 for _ in range(num_sections)]

        for base_ft_stat, base_ff_stat in base_pairs:
            ft_stat = int(base_ft_stat) + int(ft_gems) * int(gem_scale_fever)
            ff_stat = int(base_ff_stat) + int(ff_gems) * int(gem_scale_fever)

            analysis = scorer.get_section_analysis(ft_stat, ff_stat)
            useful_sections = min(num_sections, int(analysis.get("useful_sections", 0) or 0))
            if useful_sections <= 0:
                continue

            analyzed_caps = analysis.get("section_caps") or []
            for sec in range(useful_sections):
                if sec < len(analyzed_caps) and analyzed_caps[sec] > 0:
                    cap = min(
                        int(analyzed_caps[sec]),
                        MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4,
                    )
                else:
                    cap = MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4

                if cap <= 0:
                    continue

                fp_cap = _fp_cap_from_forced(scorer, ft_stat, ff_stat, cap)
                if fp_cap > max_fp_by_sec[sec]:
                    max_fp_by_sec[sec] = fp_cap

        return tuple(tuple(range(0, max_fp + 1)) for max_fp in max_fp_by_sec)
    
    # Process in batches with early streaming decision
    for batch_idx, batch_start in enumerate(range(0, n_pairs, batch_size)):
        batch_pairs = ftff_pairs[batch_start:batch_start + batch_size]
        
        for ft_gems, ff_gems in batch_pairs:
            section_breakpoints = _process_pair(ft_gems, ff_gems)
            
            if section_breakpoints not in all_groups:
                counts_list = list(itertools.product(*section_breakpoints))
                all_groups[section_breakpoints] = {
                    "ftff_pairs": [],
                    "counts_list": counts_list,
                    "section_breakpoints": section_breakpoints,
                }
                # Track union for merge decision
                for cfg in counts_list:
                    all_union_counts.add(tuple(cfg))

            all_groups[section_breakpoints]["ftff_pairs"].append((int(ft_gems), int(ff_gems)))
        
        # After first batch, decide if we should stream
        if batch_idx == 0 and n_pairs > batch_size:
            # Estimate total work based on first batch
            first_batch_cfgs = len(all_union_counts)
            remaining_batches = (n_pairs - batch_size) // batch_size + 1
            # Pessimistic estimate: unique groups grow sub-linearly
            est_total_cfgs = first_batch_cfgs * (1 + remaining_batches * 0.5)
            est_threads = int(n_genomes) * int(n_pairs) * int(est_total_cfgs)
            
            if est_total_cfgs > merge_threshold_cfgs or est_threads > merge_threshold_threads:
                streaming_mode = True
                # Yield all groups from first batch
                for group in all_groups.values():
                    if group["ftff_pairs"]:
                        yield group
                # Clear pairs for next batches
                for grp in all_groups.values():
                    grp["ftff_pairs"] = []
        
        elif streaming_mode:
            # Yield groups with new pairs from this batch
            for group in all_groups.values():
                if group["ftff_pairs"]:
                    yield group
                    group["ftff_pairs"] = []
    
    # Handle empty groups case
    if not all_groups or len(all_union_counts) == 0:
        fallback_cfg = tuple([0] * num_sections) if num_sections > 0 else ()
        yield {
            "ftff_pairs": ftff_pairs,
            "counts_list": [fallback_cfg],
            "section_breakpoints": tuple((0,) for _ in range(num_sections)),
        }
        return
    
    # If we were streaming, we're done
    if streaming_mode:
        return
    
    # Buffer mode: decide merge vs individual yield
    union_cfg_count = len(all_union_counts)
    est_threads = int(n_genomes) * int(n_pairs) * int(union_cfg_count)
    
    if union_cfg_count <= merge_threshold_cfgs and est_threads <= merge_threshold_threads:
        # Merge all into one batch
        merged_group = {
            "ftff_pairs": ftff_pairs,
            "counts_list": sorted(list(all_union_counts)),
            "section_breakpoints": None,
        }
        yield merged_group
    else:
        # Yield groups individually
        for group in all_groups.values():
            yield group


# DEPRECATED: Old simulation-based function (kept for reference)
def collect_analytic_configs(grid, total_rows=160, stat_bounds=None):
    """
    DEPRECATED: Use collect_analytical_breakpoints instead (100x faster).
    
    This simulation-based function is kept temporarily for comparison.
    """
    import warnings
    warnings.warn(
        "collect_analytic_configs is deprecated. Use collect_analytical_breakpoints instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    import numpy as np
    import itertools
    
    # Per-section sets of useful counts (union across all pairs)
    breakpoints = [set([0]) for _ in range(16)]
    
    if stat_bounds:
        min_ft, max_ft, min_ff, max_ff = stat_bounds
        min_ft = max(0, min_ft)
        max_ft = min(total_rows, max_ft)
        min_ff = max(0, min_ff)
        max_ff = min(total_rows, max_ff)
    else:
        min_ft, max_ft = 0, total_rows
        min_ff, max_ff = 0, total_rows

    max_sections = 0
    stride = 10

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
                hard_cap = MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4
                effective_cap = hard_cap
                
                current_mask_signature = (res_0[0].tobytes(), res_0[1])
                
                for c in range(1, effective_cap + 1):
                    forced_counts_list = [0] * limit_secs
                    forced_counts_list[sec] = c
                    
                    mask, cbf, cbn = grid.get_timeline_with_forced(ft_idx, ff_idx, forced_counts_list)
                    new_signature = (mask.tobytes(), cbf)
                    
                    if new_signature != current_mask_signature:
                        breakpoints[sec].add(c)
                        current_mask_signature = new_signature

    sorted_breakpoints = [sorted(list(bp)) for bp in breakpoints]
    display_limit = max(1, max_sections)
    
    print(f"[FG] DEPRECATED Analytic Candidates (Active Sections 0-{max_sections-1}): "
          f"{[len(b) for b in sorted_breakpoints[:display_limit]]}")
    
    final_ranges = sorted_breakpoints[:max(1, max_sections)]
    return list(itertools.product(*final_ranges))
