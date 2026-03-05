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


def generate_dynamic_fg_configs(num_sections, non_fever_base, *, gap=None, fever_activations=None):
    """
    Generate a list of FG configs with dynamic caps based on gap.

    Uses gap (total_notes - last_fever_end) to limit search space:
    - If gap <= 0: no opportunity (overshoot or at end), return [(0,0,...)] only
    - Otherwise: cap each section by gap (no need to overshoot)
    - Sections beyond fever_activations get cap=0 (no benefit)

    Args:
        num_sections: Number of non-fever sections
        non_fever_base: Notes in non-fever section (hard cap by available notes)
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


def _clamp_stat_idx(x: object) -> int:
    try:
        v = int(x)
    except Exception:
        v = 0
    return max(0, min(160, v))


def _sample_stat_pairs(pairs: set[tuple[int, int]], *, max_pairs: int = 16) -> list[tuple[int, int]]:
    xs = sorted({(int(a), int(b)) for a, b in (pairs or set())})
    if not xs:
        return []
    if len(xs) <= max_pairs:
        return xs
    # Deterministic subsample: evenly spaced across the sorted list.
    idxs = {int(round(i * (len(xs) - 1) / float(max_pairs - 1))) for i in range(max_pairs)}
    return [xs[i] for i in sorted(idxs)]


def collect_analytical_breakpoints(scorer, num_sections, section_caps=None, *, analysis_pairs=None):
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

    Returns:
        List[tuple]: FG configs to evaluate, e.g. [(0,0), (0,2), (2,0), (2,2), ...]
    """
    import itertools

    if num_sections <= 0:
        return [()]

    # Use section analysis to get actual useful sections (applying 3 FG rules).
    #
    # IMPORTANT: Don't assume a fixed FT/FF (e.g. 80/80). Many real base stats
    # can't reach that point under the current loadout/gem budget. Instead, if
    # the caller provides representative FT/FF stat pairs, analyze across those
    # and take the maximum "useful section" envelope so we don't under-prune.
    pairs_in: set[tuple[int, int]] = set()
    if analysis_pairs:
        try:
            for ft, ff in analysis_pairs:
                pairs_in.add((_clamp_stat_idx(ft), _clamp_stat_idx(ff)))
        except Exception:
            pairs_in = set()
    sampled_pairs = _sample_stat_pairs(pairs_in, max_pairs=16)
    if not sampled_pairs:
        sampled_pairs = [(80, 80)]

    analyses = []
    for ft_stat, ff_stat in sampled_pairs:
        try:
            analyses.append(scorer.get_section_analysis(int(ft_stat), int(ff_stat)))
        except Exception:
            continue
    if not analyses:
        analyses = [scorer.get_section_analysis(80, 80)]

    useful_sections = 0
    for a in analyses:
        try:
            useful_sections = max(int(useful_sections), int(a.get("useful_sections", 0) or 0))
        except Exception:
            continue

    analyzed_caps: list[int] = []
    for sec in range(int(useful_sections)):
        best = 0
        for a in analyses:
            try:
                caps0 = a.get("section_caps") or []
                if sec < len(caps0):
                    best = max(int(best), int(caps0[sec] or 0))
            except Exception:
                continue
        analyzed_caps.append(int(best))

    gap = 0
    try:
        gap = max(int(a.get("gap", 0) or 0) for a in analyses)
    except Exception:
        gap = 0

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

    # Calculate breakpoints across FF values (0-160).
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
        print(f"     Section {i + 1}: {bp}")

    return list(itertools.product(*section_breakpoints))


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

    def _pack_groups_for_yield(groups: list[dict]) -> list[dict]:
        """
        Pack multiple breakpoint groups into a smaller set of "super-groups" bounded by:
          - merge_threshold_cfgs
          - merge_threshold_threads

        Correctness is preserved because each super-group evaluates the union of configs across all
        included FT/FF pairs. Config ordering preserves first-seen order so cfg-idx tie-breaking is
        stable vs sequential processing.
        """
        out: list[dict] = []
        if not groups:
            return out

        # Preserve insertion order of `all_groups` (stable tie-breaking in downstream cfg_idx usage).
        items = []
        for g in groups:
            pairs = g.get("ftff_pairs") or []
            cfg_list = g.get("counts_list") or []
            if not pairs or not cfg_list:
                continue
            try:
                cfg_set = set(cfg_list)
            except Exception:
                cfg_set = {tuple(x) for x in cfg_list}
            items.append((g, list(pairs), list(cfg_list), cfg_set))

        if not items:
            return out

        cur_pairs: list[tuple[int, int]] = []
        cur_cfg_list: list[tuple] = []
        cur_cfg_set: set[tuple] = set()
        cur_breakpoints = None
        cur_pair_count = 0
        cur_is_single = True

        def _flush_current() -> None:
            nonlocal cur_pairs, cur_cfg_list, cur_cfg_set, cur_breakpoints, cur_pair_count, cur_is_single
            if not cur_pairs or not cur_cfg_list:
                cur_pairs = []
                cur_cfg_list = []
                cur_cfg_set = set()
                cur_breakpoints = None
                cur_pair_count = 0
                cur_is_single = True
                return
            out.append(
                {
                    "ftff_pairs": cur_pairs,
                    "counts_list": cur_cfg_list,
                    "section_breakpoints": cur_breakpoints if cur_is_single else None,
                }
            )
            cur_pairs = []
            cur_cfg_list = []
            cur_cfg_set = set()
            cur_breakpoints = None
            cur_pair_count = 0
            cur_is_single = True

        for g, pairs, cfg_list, cfg_set in items:
            cfg_count = len(cfg_set)
            pair_count = len(pairs)
            est_threads = int(n_genomes) * int(pair_count) * int(cfg_count)

            # If this group alone exceeds thresholds, emit it as-is (unmerged).
            if cfg_count > int(merge_threshold_cfgs) or est_threads > int(merge_threshold_threads):
                _flush_current()
                out.append(
                    {
                        "ftff_pairs": pairs,
                        "counts_list": cfg_list,
                        "section_breakpoints": g.get("section_breakpoints"),
                    }
                )
                continue

            if not cur_pairs:
                cur_pairs = pairs
                cur_breakpoints = g.get("section_breakpoints")
                cur_is_single = True
                cur_pair_count = pair_count
                cur_cfg_list = []
                cur_cfg_set = set()
                for cfg in cfg_list:
                    if cfg not in cur_cfg_set:
                        cur_cfg_set.add(cfg)
                        cur_cfg_list.append(cfg)
                continue

            new_cfg_count = int(len(cur_cfg_set) + len(cfg_set - cur_cfg_set))
            new_pair_count = int(cur_pair_count + pair_count)
            new_threads = int(n_genomes) * int(new_pair_count) * int(new_cfg_count)

            if new_cfg_count <= int(merge_threshold_cfgs) and new_threads <= int(merge_threshold_threads):
                cur_pairs.extend(pairs)
                cur_pair_count = new_pair_count
                cur_is_single = False
                cur_breakpoints = None
                for cfg in cfg_list:
                    if cfg not in cur_cfg_set:
                        cur_cfg_set.add(cfg)
                        cur_cfg_list.append(cfg)
            else:
                _flush_current()
                cur_pairs = pairs
                cur_breakpoints = g.get("section_breakpoints")
                cur_is_single = True
                cur_pair_count = pair_count
                cur_cfg_list = []
                cur_cfg_set = set()
                for cfg in cfg_list:
                    if cfg not in cur_cfg_set:
                        cur_cfg_set.add(cfg)
                        cur_cfg_list.append(cfg)

        _flush_current()
        return out

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
        batch_pairs = ftff_pairs[batch_start : batch_start + batch_size]

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
                # Yield all groups from first batch, but pack into bounded super-groups to
                # reduce tiny (n_ftff=1/2) GPU tasks.
                groups_to_yield = [g for g in all_groups.values() if g.get("ftff_pairs")]
                for packed in _pack_groups_for_yield(groups_to_yield):
                    yield packed
                for grp in groups_to_yield:
                    grp["ftff_pairs"] = []

        elif streaming_mode:
            # Yield groups with new pairs from this batch, packed to reduce tiny GPU tasks.
            groups_to_yield = [g for g in all_groups.values() if g.get("ftff_pairs")]
            for packed in _pack_groups_for_yield(groups_to_yield):
                yield packed
            for grp in groups_to_yield:
                grp["ftff_pairs"] = []

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
        # Yield groups, but pack into bounded super-groups to reduce tiny GPU tasks.
        groups_to_yield = [g for g in all_groups.values() if g.get("ftff_pairs")]
        for packed in _pack_groups_for_yield(groups_to_yield):
            yield packed
