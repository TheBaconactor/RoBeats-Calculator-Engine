"""
API Initialization - Reference Arrays, Staging Buffers, and GPU Initialization.

This module provides initialization and setup functions:
- Reference array loading and signature calculation
- FT/FF combo table upload
- Centralized ensure_ready() initialization
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.gamedata import CURVE_STATS, StatCurves
from gear_optimizer.core.array_signature import arrays_sig16
from ..runtime import init_taichi, is_initialized
from .. import fields
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from ..runtime import reset_taichi as _reset_taichi_runtime, run_hard_reset_hooks
from .ga_eval_cache import reset_ga_evaluation_cache
from ..fields import (
    GRID_SIZE,
    ensure_fields_allocated,
    ensure_grid_fields_allocated,
    is_fields_allocated,
    is_grid_fields_allocated,
)



# ============================================================================
# REFERENCE LOADING STATE
# ============================================================================

_ref_loaded = False
_last_curves_sig = None


def _curves_sig(curves: StatCurves) -> bytes:
    """Content signature of the float32 curves the kernels read (identical content skips the upload)."""
    return arrays_sig16(*(curves.f32[stat] for stat in CURVE_STATS))


def _build_exact_pp_best_gems_prefix(pp_ref: np.ndarray) -> np.ndarray:
    """Build PP-vs-OV prefix argmax table without Python inner loops."""
    pp_ref = np.asarray(pp_ref, dtype=np.float32)
    max_budget = int(fields.MAX_TOTAL_BUDGET)
    gems = np.arange(max_budget + 1, dtype=np.int32)
    cur_pp = np.arange(GRID_SIZE, dtype=np.int32)[:, None]
    pp_stat = np.minimum(cur_pp + (gems[None, :] * 2), GRID_SIZE - 1)
    pp_extra = pp_ref[pp_stat]

    deltas = np.empty((16,), dtype=np.int32)
    for flags in range(16):
        is_p_pp = flags & 1
        is_s_pp = (flags >> 1) & 1
        is_p_ov = (flags >> 2) & 1
        is_s_ov = (flags >> 3) & 1
        deltas[flags] = ((6 * is_p_pp) + (3 * is_s_pp)) - ((12 * is_p_ov) + (6 * is_s_ov))

    extra = pp_extra[None, :, :] + (deltas[:, None, None].astype(np.float32) * gems[None, None, :])
    best_idx = np.zeros((16, GRID_SIZE, max_budget + 1), dtype=np.int16)
    best_val = extra[:, :, 0].copy()
    for g_pp in range(1, max_budget + 1):
        layer = best_idx[:, :, g_pp]
        layer[:, :] = best_idx[:, :, g_pp - 1]
        cand = extra[:, :, g_pp]
        better = cand > best_val
        layer[better] = np.int16(g_pp)
        best_val[better] = cand[better]
    return best_idx


# ============================================================================
# NUMPY STAGING BUFFERS (avoid huge per-call allocations / CPU zeroing)
# ============================================================================


# Cache for genome_base_stats uploads to avoid redundant from_numpy calls
# Stores (n_genomes, hash_bytes) of last uploaded stats
_GENOME_STATS_CACHE = None
_FTFF_COMBO_CACHE = {"key": None, "n_combos": 0}
_TIMING_RESPONSE_COMBO_CACHE = {"key": None, "n_combos": 0}


def hard_reset_taichi(*, reason: str | None = None) -> None:
    """
    Hard-reset the Taichi runtime and all taichi_gem module state.

    Intended as a recovery path for Vulkan backend failures (e.g. semaphore
    allocation errors) and long-running sessions.
    """
    global _ref_loaded, _last_curves_sig, _GENOME_STATS_CACHE, _FTFF_COMBO_CACHE, _TIMING_RESPONSE_COMBO_CACHE

    # Reset runtime first (frees Vulkan resources)
    _reset_taichi_runtime(reason=reason)

    # Clear all Taichi field allocation state (fields are invalid after reset)
    fields.reset_fields_state()

    # Clear API-level caches that assume device state exists
    _ref_loaded = False
    _last_curves_sig = None
    _GENOME_STATS_CACHE = None
    _FTFF_COMBO_CACHE = {"key": None, "n_combos": 0}
    _TIMING_RESPONSE_COMBO_CACHE = {"key": None, "n_combos": 0}

    # Then the state the modules above the fields registered (timeline, GA upload caches, FG warmup).
    run_hard_reset_hooks()


def _ensure_ftff_combo_tables(
    total_budget: int,
    *,
    max_ft_gems: int | None = None,
    max_ff_gems: int | None = None,
) -> int:
    """
    Ensure the FT/FF combo lookup tables are resident on GPU.

    The tables enumerate all (ft, ff) integer pairs such that:
      0 <= ft <= total_budget
      0 <= ff <= total_budget - ft

    Optional global caps can further prune impossible combos:
      ft <= max_ft_gems
      ff <= max_ff_gems

    Returns:
        n_combos: Number of valid combos for this budget/cap pair.
    """
    # Circular import avoided
    ensure_ready()
    total_budget = int(total_budget)
    if total_budget < 0:
        total_budget = 0
    if total_budget > fields.MAX_TOTAL_BUDGET:
        raise ValueError(f"total_budget={total_budget} exceeds fields.MAX_TOTAL_BUDGET={fields.MAX_TOTAL_BUDGET}")

    cap_ft = int(total_budget) if max_ft_gems is None else int(max_ft_gems)
    cap_ff = int(total_budget) if max_ff_gems is None else int(max_ff_gems)
    cap_ft = max(0, min(int(total_budget), int(cap_ft)))
    cap_ff = max(0, min(int(total_budget), int(cap_ff)))

    cache_key = (int(total_budget), int(cap_ft), int(cap_ff))
    if _FTFF_COMBO_CACHE.get("key") == cache_key:
        return int(_FTFF_COMBO_CACHE.get("n_combos") or 0)

    ft = np.zeros((fields.MAX_FTFF_COMBOS,), dtype=np.int32)
    ff = np.zeros((fields.MAX_FTFF_COMBOS,), dtype=np.int32)

    ft_vals, ff_vals, _budget_left = ftff_combo_arrays(
        int(total_budget),
        max_ft_gems=int(cap_ft),
        max_ff_gems=int(cap_ff),
    )

    n_combos = int(ft_vals.shape[0])
    ft[:n_combos] = ft_vals
    ff[:n_combos] = ff_vals

    fields.ftff_combo_ft.from_numpy(ft)
    fields.ftff_combo_ff.from_numpy(ff)
    _FTFF_COMBO_CACHE["key"] = cache_key
    _FTFF_COMBO_CACHE["n_combos"] = n_combos
    return n_combos


# ============================================================================
# INITIALIZATION HELPERS
# ============================================================================


def ensure_ready(curves=None):
    """
    Ensure Taichi and GPU fields are ready for use.

    This is the centralized initialization function that maintains
    the same order and semantics as the original scattered checks.

    Args:
        curves: StatCurves to upload (optional)
    """
    # 1. Taichi initialization
    if not is_initialized():
        init_taichi()

    # 2. Field allocation (bound into the kernels)
    _ensure_bound_fields()

    # 3. Stat curves - upload only when their content changes.
    if curves is not None and ((not _ref_loaded) or _last_curves_sig != _curves_sig(curves)):
        load_curves(curves)

    # 4. Grid fields - ALWAYS allocate because Taichi JIT traces both branches
    #    of _calc_score_selector regardless of runtime `mode` value, so accessing
    #    `grid_fever_masks_bits` during compilation fails if the field is None.
    _ensure_bound_fields(grid=True)


def _ensure_bound_fields(*, grid: bool = False) -> None:
    """Allocate the fields (with `grid`, the timeline grid fields too) and bind a new allocation into the kernels'
    module: the kernels read the fields as module globals of kernels_helpers."""
    allocated = not is_fields_allocated() or (grid and not is_grid_fields_allocated())
    ensure_fields_allocated()
    if grid:
        ensure_grid_fields_allocated()
    if allocated:
        from ..kernels import kernels_helpers

        fields.bind_fields(kernels_helpers)


# ============================================================================
# REFERENCE ARRAY LOADING
# ============================================================================


def load_curves(curves: StatCurves):
    """
    Upload the float32 stat curves to the GPU fields.

    Must be called before solve_genomes_*() or the GA/FG kernels that read the curves, unless
    `ensure_ready(curves)` uploads them.
    """
    global _ref_loaded, _last_curves_sig

    _ensure_bound_fields()
    reset_ga_evaluation_cache()
    f32 = curves.f32
    fields.ref_pp_field.from_numpy(f32["Perfect Points"])
    fields.ref_cm_field.from_numpy(f32["Combo Multiplier"])
    fields.ref_fm_field.from_numpy(f32["Fever Multiplier"])
    # PP-vs-OV prefix argmax for a fixed base PP stat and color-flag combination: removes the inner
    # O(B) PP scan from each (CM, FM) pair of the bounded exact inner solver (O(B^3) -> O(B^2)).
    fields.exact_pp_best_gems_prefix.from_numpy(_build_exact_pp_best_gems_prefix(f32["Perfect Points"]))
    fields.ref_ft_field.from_numpy(f32["Fever Time"])
    fields.ref_ff_field.from_numpy(f32["Fever Fill Rate"])

    _ref_loaded = True
    _last_curves_sig = _curves_sig(curves)
