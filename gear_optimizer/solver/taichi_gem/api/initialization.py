"""
API Initialization - Reference Arrays, Staging Buffers, and GPU Initialization.

This module provides initialization and setup functions:
- Reference array loading and signature calculation
- FT/FF combo table upload
- Centralized ensure_ready() initialization
"""

from __future__ import annotations

import hashlib
import taichi as ti
import numpy as np

from gear_optimizer.core.env_config import ENV
from ..runtime import init_taichi, is_initialized
from .. import fields
from ..runtime import reset_taichi as _reset_taichi_runtime
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
_last_ref_arrays_sig = None


def _ref_arrays_sig(ref_arrays: dict) -> bytes:
    """
    Stable content signature for ref arrays.

    We avoid caching by `id(ref_arrays)` because in parallel/IPC mode each request
    arrives as a distinct Python object despite having identical contents.
    """
    h = hashlib.blake2b(digest_size=16)
    for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"):
        if key not in ref_arrays:
            # Preserve old behavior: some call sites may omit optional FT/FF.
            h.update(b"\x00")
            continue
        arr = np.asarray(ref_arrays[key])
        h.update(str(arr.dtype).encode("utf-8"))
        h.update(arr.shape[0].to_bytes(4, "little", signed=False))
        h.update(arr.tobytes(order="C"))
    return h.digest()


# ============================================================================
# NUMPY STAGING BUFFERS (avoid huge per-call allocations / CPU zeroing)
# ============================================================================


# Cache for genome_base_stats uploads to avoid redundant from_numpy calls
# Stores (n_genomes, hash_bytes) of last uploaded stats
_GENOME_STATS_CACHE = None
_FTFF_COMBO_CACHE = {"key": None, "n_combos": 0}


def hard_reset_taichi(*, reason: str | None = None) -> None:
    """
    Hard-reset the Taichi runtime and all taichi_gem module state.

    Intended as a recovery path for Vulkan backend failures (e.g. semaphore
    allocation errors) and long-running sessions.
    """
    global _ref_loaded, _last_ref_arrays_sig, _GENOME_STATS_CACHE, _FTFF_COMBO_CACHE

    # Reset runtime first (frees Vulkan resources)
    _reset_taichi_runtime(reason=reason)

    # Clear all Taichi field allocation state (fields are invalid after reset)
    try:
        from ..fields import reset_fields_state as _reset_fields_state

        _reset_fields_state()
    except Exception:
        pass

    try:
        from ..force_greats.fields import reset_fields_state as _reset_fg_fields_state

        _reset_fg_fields_state()
    except Exception:
        pass

    # Clear API-level caches that assume device state exists
    _ref_loaded = False
    _last_ref_arrays_sig = None
    _GENOME_STATS_CACHE = None
    _FTFF_COMBO_CACHE = {"key": None, "n_combos": 0}

    try:
        from .timeline import reset_timeline_state as _reset_timeline_state

        _reset_timeline_state()
    except Exception:
        pass

    try:
        from ..force_greats.api import reset_force_greats_api_state as _reset_fg_api_state

        _reset_fg_api_state()
    except Exception:
        pass

    try:
        from .ga_operations import reset_ga_upload_caches as _reset_ga_caches

        _reset_ga_caches()
    except Exception:
        pass


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

    # Vectorized triangular enumeration preserving the original triangular order:
    # ft=0,ff=0..B ; ft=1,ff=0..B-1 ; ... ; ft=B,ff=0
    dim = int(total_budget) + 1
    tri_i, tri_j = np.triu_indices(dim)
    ft_vals = tri_i.astype(np.int32, copy=False)
    ff_vals = (tri_j - tri_i).astype(np.int32, copy=False)
    if cap_ft < int(total_budget) or cap_ff < int(total_budget):
        valid = (ft_vals <= int(cap_ft)) & (ff_vals <= int(cap_ff))
        ft_vals = ft_vals[valid]
        ff_vals = ff_vals[valid]

    n_combos = int(ft_vals.shape[0])
    ft[:n_combos] = ft_vals
    ff[:n_combos] = ff_vals

    fields.ftff_combo_ft.from_numpy(ft)
    fields.ftff_combo_ff.from_numpy(ff)
    _FTFF_COMBO_CACHE["key"] = cache_key
    _FTFF_COMBO_CACHE["n_combos"] = n_combos
    return n_combos


# ============================================================================
# SYNC POLICY
# ============================================================================
#
# Taichi kernels are ordered on the device; explicit ti.sync() is only required
# when the CPU needs results/timing *right now*. Excess sync points can dominate
# runtime (CPU stalls waiting for GPU).
#
# - GPU_SYNC_FOR_TIMING=1: allow extra syncs to measure kernel wall time
# - GPU_FORCE_SYNC=1: force all optional sync points on (debug)

_SYNC_FOR_TIMING = ENV.gpu_sync_for_timing
_FORCE_SYNC = ENV.gpu_force_sync


def _maybe_sync(*, for_timing: bool = False) -> None:
    """Sync only when explicitly requested (timing/debug)."""
    from .sync_policy import maybe_sync

    maybe_sync(sync_fn=ti.sync, force_sync=_FORCE_SYNC, sync_for_timing=_SYNC_FOR_TIMING, for_timing=for_timing)


def is_refs_loaded() -> bool:
    """Check if reference arrays have been loaded."""
    return _ref_loaded


# ============================================================================
# INITIALIZATION HELPERS
# ============================================================================


def ensure_ready(ref_arrays=None, *, timeline_grid=None):
    """
    Ensure Taichi and GPU fields are ready for use.

    This is the centralized initialization function that maintains
    the same order and semantics as the original scattered checks.

    Args:
        ref_arrays: Reference arrays to load (optional)
        timeline_grid: Timeline grid to upload (optional)
    """
    # Import here to avoid circular dependency
    from .timeline import _upload_timeline_grid, precompute_timeline_gpu

    # 1. Taichi initialization
    if not is_initialized():
        init_taichi()

    # 2. Field allocation (includes bind_fields to kernels)
    if not is_fields_allocated():
        ensure_fields_allocated()

    # 3. Reference arrays - upload only when needed (or when ref source changes)
    # This preserves the old behavior where callers could load once and reuse.
    sig: bytes = b""
    global _last_ref_arrays_sig
    if ref_arrays is not None:
        sig = _ref_arrays_sig(ref_arrays)
        if (not _ref_loaded) or (_last_ref_arrays_sig != sig):
            load_ref_arrays(ref_arrays)
            _last_ref_arrays_sig = sig

    # 4. Grid fields - ALWAYS allocate because Taichi JIT traces both branches
    #    of _calc_score_selector regardless of runtime `mode` value, so accessing
    #    `grid_fever_masks_bits` during compilation fails if the field is None.
    if not is_grid_fields_allocated():
        ensure_grid_fields_allocated()

    if timeline_grid is not None:
        # Prefer GPU-native timeline precompute when possible to avoid CPU staging
        # and keep the "new architecture" GPU-resident by default.
        calc_song = getattr(timeline_grid, "calc_song", None)
        refs = getattr(timeline_grid, "ref_arrays", None)
        if isinstance(calc_song, dict) and isinstance(refs, dict):
            precompute_timeline_gpu(calc_song, refs, song_slot=0)
        else:
            _upload_timeline_grid(timeline_grid)

    # Return the (possibly empty) ref-array signature so hot paths can avoid hashing refs twice.
    return bytes(sig)


# ============================================================================
# REFERENCE ARRAY LOADING
# ============================================================================


def load_ref_arrays(ref_arrays: dict):
    """
    Upload reference arrays to GPU fields.

    Must be called once before using solve_genomes_*() or GA/FG kernels that depend on
    the lookup tables (unless you call `ensure_ready(ref_arrays=...)`, which will
    upload them automatically).
    Typically called when switching songs or on first use.

    Args:
        ref_arrays: Dict with keys "Perfect Points", "Combo Multiplier", "Fever Multiplier"
                    Each value is a NumPy array of shape (161,)

    Optional keys:
        - "Fever Time": Optional FT reference array (161,)
        - "Fever Fill Rate": Optional FF reference array (161,)
    """
    global _ref_loaded

    ensure_fields_allocated()

    # Validate required keys and shapes early (clear errors)
    required = ("Perfect Points", "Combo Multiplier", "Fever Multiplier")
    for k in required:
        if k not in ref_arrays:
            raise KeyError(f"ref_arrays missing required key {k!r}")
        arr = np.asarray(ref_arrays[k])
        if arr.ndim != 1 or arr.shape[0] != GRID_SIZE:
            raise ValueError(f"ref_arrays[{k!r}] must be shape ({GRID_SIZE},), got {arr.shape}")

    fields.ref_pp_field.from_numpy(ref_arrays["Perfect Points"].astype(np.float32))
    fields.ref_cm_field.from_numpy(ref_arrays["Combo Multiplier"].astype(np.float32))
    fields.ref_fm_field.from_numpy(ref_arrays["Fever Multiplier"].astype(np.float32))

    # Precompute a tiny helper table for the bounded exact inner solver:
    # PP-vs-OV prefix argmax for a fixed base PP stat and color-flag combination.
    #
    # This removes the inner O(B) PP scan from each (CM, FM) pair and turns the
    # cold exact solver from O(B^3) into O(B^2) per fixed (FT,FF) combo.
    pp_ref = np.asarray(ref_arrays["Perfect Points"], dtype=np.float32)
    max_budget = int(fields.MAX_TOTAL_BUDGET)
    pp_best_prefix = np.zeros((16, GRID_SIZE, max_budget + 1), dtype=np.int16)
    for flags in range(16):
        is_p_pp = flags & 1
        is_s_pp = (flags >> 1) & 1
        is_p_ov = (flags >> 2) & 1
        is_s_ov = (flags >> 3) & 1

        w_pp = (6 * is_p_pp) + (3 * is_s_pp)
        w_ov = (12 * is_p_ov) + (6 * is_s_ov)
        delta = np.int32(w_pp - w_ov)

        for cur_pp in range(GRID_SIZE):
            best_g = 0
            best_extra = np.float32(pp_ref[cur_pp])
            pp_best_prefix[flags, cur_pp, 0] = 0
            for g_pp in range(1, max_budget + 1):
                pp_stat = cur_pp + (g_pp * 2)
                if pp_stat > 160:
                    pp_stat = 160
                extra = np.float32(g_pp * delta) + np.float32(pp_ref[pp_stat])
                if extra > best_extra:
                    best_extra = extra
                    best_g = g_pp
                pp_best_prefix[flags, cur_pp, g_pp] = best_g
    fields.exact_pp_best_gems_prefix.from_numpy(pp_best_prefix)

    # Optional FT/FF uploads
    if "Fever Time" in ref_arrays:
        arr = np.asarray(ref_arrays["Fever Time"])
        if arr.ndim != 1 or arr.shape[0] != GRID_SIZE:
            raise ValueError(f"ref_arrays['Fever Time'] must be shape ({GRID_SIZE},), got {arr.shape}")
        fields.ref_ft_field.from_numpy(ref_arrays["Fever Time"].astype(np.float32))
    if "Fever Fill Rate" in ref_arrays:
        arr = np.asarray(ref_arrays["Fever Fill Rate"])
        if arr.ndim != 1 or arr.shape[0] != GRID_SIZE:
            raise ValueError(f"ref_arrays['Fever Fill Rate'] must be shape ({GRID_SIZE},), got {arr.shape}")
        fields.ref_ff_field.from_numpy(ref_arrays["Fever Fill Rate"].astype(np.float32))

    _ref_loaded = True
