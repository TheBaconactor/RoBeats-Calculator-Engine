"""
Taichi Kernels - Field Placeholders and Helper Functions.

This module contains:
- Field placeholders (bound by fields.bind_fields() at runtime)
- Lookup functions for reference tables with clamping
- RNG helper (xorshift32)
- KERNEL_BLOCK_DIM constant

IMPORTANT: Do NOT import fields directly at module load time.
The field variables below are placeholders that get populated by bind_fields().
"""
import taichi as ti

from ..runtime import get_block_dim

# Resolve once at import time so Taichi sees a plain constant in `ti.loop_config`.
# (Calling Python functions inside kernels triggers Taichi AST warnings.)
_KERNEL_BLOCK_DIM = get_block_dim()


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

# Song data for timeline computation
song_timestamps = None  # (MAX_SONG_NOTES,) f32
song_total_notes = None  # scalar i32
song_long_notes = None   # scalar i32
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
item_stats = None
base_fixed_stats = None
ga_scores = None
ga_rng_state = None
ga_parent_a = None
ga_parent_b = None
slot_start = None    # (MAX_SLOTS,) per-slot first valid item_id
slot_count = None    # (MAX_SLOTS,) per-slot item count

# Results
result_stats = None
# [score, pp, cm, fm, ov, p_val, s_val]

# Genome results
genome_result_stats = None
# [score, ft, ff, pp, cm, fm, ov]
chunk_best_key = None  # u64 packed key per genome for safe reduction
ftff_combo_ft = None   # (MAX_FTFF_COMBOS,) i32
ftff_combo_ff = None   # (MAX_FTFF_COMBOS,) i32


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
    return ref_pp_field[_clamp_stat_idx(value)]


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
