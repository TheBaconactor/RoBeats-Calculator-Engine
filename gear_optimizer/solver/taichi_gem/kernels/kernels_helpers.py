"""
Taichi Kernels - Field Placeholders and Helper Functions.

This module contains:
- Field placeholders (bound by fields.bind_fields() at runtime)
- Lookup functions for reference tables with clamping
- RNG helper (xorshift32)
- Common math helpers and search functions
- KERNEL_BLOCK_DIM constant

IMPORTANT: Do NOT import fields directly at module load time.
The field variables below are placeholders that get populated by bind_fields().
"""

import taichi as ti

from ..runtime import get_block_dim

# Resolve once at import time so Taichi sees a plain constant in `ti.loop_config`.
# (Calling Python functions inside kernels triggers Taichi AST warnings.)
_KERNEL_BLOCK_DIM = get_block_dim()
CHUNK_BEST_KEY_TILES = 8  # Must match fields.CHUNK_BEST_KEY_TILES

# FT/FF combo reduction scratch (Vulkan path).
# Must match constants in `gear_optimizer/solver/taichi_gem/fields.py`.
GA_FTFF_REDUCE_BLOCK_DIM = 256
GA_FTFF_REDUCE_WAVE_STRIDE = GA_FTFF_REDUCE_BLOCK_DIM // 32  # lane//32 indexing (works for wave32 and wave64)


# ============================================================================
# FIELD PLACEHOLDERS (bound by fields.bind_fields() after allocation)
# ============================================================================

# Reference tables
ref_pp_field = None
ref_cm_field = None
ref_fm_field = None
ref_ft_field = None
ref_ff_field = None

# Grid fields
grid_count_body_fever = None
grid_count_body_normal = None
grid_head_len = None
grid_fever_masks = None
grid_fever_masks_bits = None
grid_sig0 = None  # (MAX_SONG_SLOTS, 161, 161) u64 - timeline signature (mask-derived)
grid_sig1 = None  # (MAX_SONG_SLOTS, 161, 161) u64 - timeline signature (counts-derived)
grid_gap = None  # (MAX_SONG_SLOTS, 161, 161) i16 - gap to song end per (FT, FF)
grid_fever_activations = None  # (MAX_SONG_SLOTS, 161, 161) i8 - fever activations per (FT, FF)

# Song data for timeline computation
song_timestamps = None  # (MAX_SONG_NOTES,) f32
song_total_notes = None  # scalar i32
song_long_notes = None  # scalar i32
song_last_note_time = None  # scalar f32

# Work item data
fever_masks = None
work_items = None
# [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]

# Genome base stats
genome_base_stats = None
# [pp, cm, fm, p_val, s_val, ft, ff]

# Per-slot song flags (batch coalescing)
song_flags = None  # (MAX_SONG_SLOTS, 12) i32

# GPU-native GA / stat aggregation fields
population_indices = None
population_next_indices = None
ga_initial_populations = None  # (MAX_GA_RUNS, MAX_GA_RUN_GENOMES, MAX_SLOTS) staged initial populations
ga_init_heuristic_topk = None  # (MAX_SLOTS, K) per-slot heuristic sampling table (K may be 1 when disabled)
item_stats = None
base_fixed_stats = None
ga_scores = None
ga_rng_state = None
ga_parent_a = None
ga_parent_b = None
slot_start = None  # (MAX_SLOTS,) per-slot first valid item_id
slot_count = None  # (MAX_SLOTS,) per-slot item count

# Results
result_stats = None
# [score, pp, cm, fm, ov, p_val, s_val]

# Genome results
genome_result_stats = None
# [score, ft, ff, pp, cm, fm, ov]
genome_hint_allocation = None  # [pp_gems, cm_gems, fm_gems, ov_gems] - warm-start hints
chunk_best_key = None  # u64 packed key per genome for safe reduction
chunk_best_key_tiles = None  # (MAX_GENOMES, CHUNK_BEST_KEY_TILES) u64 packed keys (contention reduction)
chunk_best_key_waves = None  # (MAX_GENOMES, GA_FTFF_REDUCE_SCRATCH_COLS) u64 scratch (per-wave best keys)
chunk_best_score = None  # (MAX_GENOMES,) i32 best score per genome (Metal)
chunk_best_idx = None  # (MAX_GENOMES,) i32 work item index (Metal)
ftff_combo_ft = None  # (MAX_FTFF_COMBOS,) i32
ftff_combo_ff = None  # (MAX_FTFF_COMBOS,) i32
chunk_best_results = None  # (MAX_GENOMES, 4) i32 - cached [pp, cm, fm, ov] from winning combo

# GPU-side global best tracking (avoids per-generation CPU downloads)
ga_global_best_score = None  # (1,) i32 - best score across all generations
ga_global_best_genome = None  # (MAX_SLOTS,) i32 - item IDs of best genome
ga_global_best_results = None  # (7,) i32 - [score, ft, ff, pp, cm, fm, ov] for best genome
ga_runs_payload_packed = None  # (MAX_GA_RUNS, MAX_GA_RUN_GENOMES+1, 17) i32 - packed snapshots per run
ga_run_payload_packed = None  # (MAX_GENOMES+1, 17) i32 - packed snapshot payload for one-shot downloads
ga_fg_candidates_packed = None  # (MAX_SONG_SLOTS, MAX_GA_RUNS, K+1, 24) i32 - compact GA->FG candidate table
ga_fg_candidates_download_staging = None  # (MAX_GA_RUNS, K+1, 24) i32 - single-slot download staging

# GPU-side GA->FG candidate selection (avoid downloading full candidate tables)
ga_fg_select_hash_used = None  # (HASH_SIZE,) i32 - open-addressing value (0=empty, else stub_index+1)
ga_fg_select_hash_keys = None  # (HASH_SIZE, 9) i32 - canonical (gear+minis) key
ga_fg_select_stub_count = None  # (1,) i32 - number of unique stubs
ga_fg_select_stub_run = None  # (STUBS_MAX,) i32
ga_fg_select_stub_row = None  # (STUBS_MAX,) i32
ga_fg_select_stub_score = None  # (STUBS_MAX,) i32
ga_fg_select_stub_fg_proxy = None  # (STUBS_MAX,) i64
ga_fg_select_stub_center_ft = None  # (STUBS_MAX,) i32
ga_fg_select_stub_center_ff = None  # (STUBS_MAX,) i32
ga_fg_select_stub_ids = None  # (STUBS_MAX, 9) i32
ga_fg_select_selected_mask = None  # (STUBS_MAX,) i32
ga_fg_selected_count = None  # (1,) i32
ga_fg_selected_coords = None  # (MAX_SELECTED, 2) i32
ga_fg_selected_payload_staging_256 = None  # (257, 26) i32 - row0 header + up to 256 candidates
ga_fg_selected_payload_staging_1024 = None  # (1025, 26) i32 - row0 header + up to 1024 candidates
ga_fg_selected_payload_staging_5000 = None  # (5001, 26) i32 - row0 header + up to 5000 candidates

# GPU-side island elitism (avoids per-generation score downloads)
island_boundaries = None  # (MAX_ISLANDS+1,) i32 - island start/end indices
island_elite_indices = None  # (MAX_GENOMES,) i32 - output: elite genome indices
island_elite_count = None  # (1,) i32 - output: total elites found


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


@ti.func
def _clamp_stat_idx(value: ti.i32) -> ti.i32:
    """
    Clamp stat index to valid range [0, 160].

    Args:
        value: Stat value to clamp

    Returns:
        Clamped value in range [0, 160]
    """
    return ti.max(0, ti.min(160, value))


@ti.func
def lookup_ref_pp(value: ti.i32) -> ti.f32:
    """
    O(1) lookup from Perfect Points reference table. Clamps to [0, 160].

    Args:
        value: PP stat value

    Returns:
        PP multiplier from reference table
    """
    return ti.cast(ref_pp_field[_clamp_stat_idx(value)], ti.f32)


@ti.func
def lookup_ref_cm(value: ti.i32) -> ti.f32:
    """
    O(1) lookup from Combo Multiplier reference table. Clamps to [0, 160].

    Args:
        value: CM stat value

    Returns:
        CM multiplier from reference table
    """
    return ref_cm_field[_clamp_stat_idx(value)]


@ti.func
def lookup_ref_fm(value: ti.i32) -> ti.f32:
    """
    O(1) lookup from Fever Multiplier reference table. Clamps to [0, 160].

    Args:
        value: FM stat value

    Returns:
        FM multiplier from reference table
    """
    return ref_fm_field[_clamp_stat_idx(value)]


@ti.func
def lookup_ref_ft(value: ti.i32) -> ti.f32:
    """
    O(1) lookup from Fever Time reference table. Clamps to [0, 160].

    Args:
        value: FT stat value

    Returns:
        FT multiplier from reference table
    """
    return ref_ft_field[_clamp_stat_idx(value)]


@ti.func
def lookup_ref_ff(value: ti.i32) -> ti.f32:
    """
    O(1) lookup from Fever Fill reference table. Clamps to [0, 160].

    Args:
        value: FF stat value

    Returns:
        FF multiplier from reference table
    """
    return ref_ff_field[_clamp_stat_idx(value)]


@ti.func
def _xorshift32(x: ti.u32) -> ti.u32:
    """
    Deterministic per-thread RNG (fast, good enough for GA operators).

    Uses xorshift32 algorithm for fast, low-quality random numbers.
    Perfect for genetic algorithm mutation/crossover.

    Args:
        x: Current RNG state

    Returns:
        Next RNG state
    """
    x ^= x << ti.u32(13)
    x ^= x >> ti.u32(17)
    x ^= x << ti.u32(5)
    return x


# ============================================================================
# SEARCH HELPERS
# ============================================================================


@ti.func
def binary_search_left_from(timestamps: ti.template(), n: ti.i32, target: ti.f32, lo: ti.i32) -> ti.i32:
    """
    Binary search for leftmost index where timestamps[i] >= target, starting at `lo`.

    Equivalent to np.searchsorted(timestamps, target, side='left') with a lower bound.

    Args:
        timestamps: Sorted array of timestamps (Taichi field)
        n: Length of array
        target: Value to search for
        lo: Lower bound starting index

    Returns:
        Leftmost index where timestamps[i] >= target, or n if not found
    """
    hi = n
    while lo < hi:
        mid = (lo + hi) // 2
        if timestamps[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def binary_search_left(timestamps: ti.template(), n: ti.i32, target: ti.f32) -> ti.i32:
    """
    Binary search for leftmost index where timestamps[i] >= target.

    Equivalent to np.searchsorted(timestamps, target, side='left').

    Args:
        timestamps: Sorted array of timestamps (Taichi field)
        n: Length of array
        target: Value to search for

    Returns:
        Leftmost index where timestamps[i] >= target, or n if not found
    """
    return binary_search_left_from(timestamps, n, target, 0)


# ============================================================================
# SCORING HELPERS
# ============================================================================


@ti.func
def _calc_body_score(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.f32:
    """
    Calculate score for body notes (notes past the head).

    Body notes are at full combo, so no ramping. Just multiply base score
    by combo and fever multipliers.

    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        count_fever: Number of fever notes in body
        count_normal: Number of normal notes in body

    Returns:
        Body score as float
    """
    # All values are non-negative; truncation toward zero matches floor and is faster.
    combo_val = ti.cast(base_value * combo_mul, ti.i32)
    fever_val = ti.cast(base_value * combo_mul * fever_mul, ti.i32)
    # Use integer multiplication to avoid f32 precision loss with large counts
    return ti.cast((count_fever * fever_val) + (count_normal * combo_val), ti.f32)


@ti.func
def _calc_head_factor(base_value: ti.f32, combo_mul: ti.f32) -> ti.f32:
    """
    Calculate combo ramp factor for head notes.

    The head (first 100 notes) has ramping combo multiplier.
    Factor is added per note: score[i] = base_value + (i * factor)

    Args:
        base_value: Base score value
        combo_mul: Combo multiplier at full combo

    Returns:
        Ramp factor per note
    """
    return (combo_mul - 1.0) * base_value / 100.0


@ti.func
def _calc_head_score_bits(
    base_value: ti.f32,
    factor: ti.f32,
    fever_mul: ti.f32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
) -> ti.f32:
    """
    Calculate head score using bitpacked fever masks.

    More efficient than grid lookup - masks passed as 4×u32 = 128 bits.
    Bit i corresponds to head note i being a fever note.

    Args:
        base_value: Base score value
        factor: Combo ramp factor
        fever_mul: Fever multiplier
        m0: Bits 0-31 (notes 0-31)
        m1: Bits 32-63 (notes 32-63)
        m2: Bits 64-95 (notes 64-95)
        m3: Bits 96-127 (notes 96-99 used)
        head_len: Number of notes in head

    Returns:
        Head score as float
    """
    head_score = ti.i32(0)
    # Split by bitmask word to avoid per-iteration branching on i<32/64/96.
    n0 = ti.min(head_len, 32)
    for i in range(n0):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        is_fever = (m0 >> ti.u32(i)) & ti.u32(1)
        # Branchless select: mul is either 1.0 or fever_mul.
        mul = 1.0 + (fever_mul - 1.0) * ti.cast(is_fever, ti.f32)
        head_score += ti.cast(ramp_val * mul, ti.i32)

    if head_len > 32:
        n1 = ti.min(head_len, 64)
        for i in range(32, n1):
            ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
            is_fever = (m1 >> ti.u32(i - 32)) & ti.u32(1)
            mul = 1.0 + (fever_mul - 1.0) * ti.cast(is_fever, ti.f32)
            head_score += ti.cast(ramp_val * mul, ti.i32)

    if head_len > 64:
        n2 = ti.min(head_len, 96)
        for i in range(64, n2):
            ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
            is_fever = (m2 >> ti.u32(i - 64)) & ti.u32(1)
            mul = 1.0 + (fever_mul - 1.0) * ti.cast(is_fever, ti.f32)
            head_score += ti.cast(ramp_val * mul, ti.i32)

    if head_len > 96:
        for i in range(96, head_len):
            ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
            is_fever = (m3 >> ti.u32(i - 96)) & ti.u32(1)
            mul = 1.0 + (fever_mul - 1.0) * ti.cast(is_fever, ti.f32)
            head_score += ti.cast(ramp_val * mul, ti.i32)
    return ti.cast(head_score, ti.f32)


@ti.func
def calc_score_with_grid_bits(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using bitpacked fever masks (4x u32 = 128 bits).
    Bit i corresponds to head note i being a fever note.

    More efficient than grid lookup for repeated score calculations
    in optimize_core_device.

    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        m0-m3: Bitpacked fever masks (4×32 bits)
        head_len: Number of notes in head
        count_fever: Fever notes in body
        count_normal: Normal notes in body

    Returns:
        Total score as int32
    """
    body_score = _calc_body_score(base_value, combo_mul, fever_mul, count_fever, count_normal)
    factor = _calc_head_factor(base_value, combo_mul)
    head_score = _calc_head_score_bits(base_value, factor, fever_mul, m0, m1, m2, m3, head_len)
    # Cast each component to i32 first, then add as integers for exact result
    return ti.cast(body_score, ti.i32) + ti.cast(head_score, ti.i32)
