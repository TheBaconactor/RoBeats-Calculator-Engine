"""
API Initialization - Reference Arrays, Staging Buffers, and GPU Initialization.

This module provides initialization and setup functions:
- Reference array loading and signature calculation
- Staging buffer management (batch, mega, parallel)
- Song flags and FT/FF combo table upload
- Centralized ensure_ready() initialization
"""
from __future__ import annotations

import hashlib
import taichi as ti
import numpy as np

from gear_optimizer.core.env_config import ENV
from ..runtime import init_taichi_vulkan, is_initialized
from .. import fields
from ..runtime import reset_taichi as _reset_taichi_runtime
from ..fields import (
    GRID_SIZE,
    MAX_WORK_ITEMS,
    MAX_HEAD_NOTES,
    MAX_GENOMES,
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

_BATCH_STAGING = None
_MEGA_STAGING = None
_PARALLEL_STAGING = None
_SONG_FLAGS_HOST = None

# Cache for genome_base_stats uploads to avoid redundant from_numpy calls
# Stores (n_genomes, hash_bytes) of last uploaded stats
_GENOME_STATS_CACHE = None
_FTFF_COMBO_CACHE = {"budget": None, "n_combos": 0}


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
    _FTFF_COMBO_CACHE = {"budget": None, "n_combos": 0}

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


def _ensure_song_flags_host():
    global _SONG_FLAGS_HOST
    if _SONG_FLAGS_HOST is not None:
        return _SONG_FLAGS_HOST
    _SONG_FLAGS_HOST = np.zeros((fields.MAX_SONG_SLOTS, 12), dtype=np.int32)
    return _SONG_FLAGS_HOST


def _upload_song_flags(slot_to_flags: dict[int, tuple[int, ...]]) -> None:
    """
    Upload per-slot song flags used by `solve_ftff_parallel_kernel`.

    slot_to_flags entries must be 12-int tuples in this order:
      [is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
       is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov]
    """
    host = _ensure_song_flags_host()
    for slot, flags12 in slot_to_flags.items():
        if len(flags12) != 12:
            raise ValueError(f"song_flags for slot {slot} must be 12 ints, got {len(flags12)}")
        host[int(slot), :] = np.asarray(flags12, dtype=np.int32)
    fields.song_flags.from_numpy(host)


def _ensure_ftff_combo_tables(total_budget: int) -> int:
    """
    Ensure the FT/FF combo lookup tables are resident on GPU.

    The tables enumerate all (ft, ff) integer pairs such that:
      0 <= ft <= total_budget
      0 <= ff <= total_budget - ft

    Returns:
        n_combos: Number of valid combos for this budget.
    """
    # Circular import avoided
    ensure_ready()
    total_budget = int(total_budget)
    if total_budget < 0:
        total_budget = 0
    if total_budget > fields.MAX_TOTAL_BUDGET:
        raise ValueError(
            f"total_budget={total_budget} exceeds fields.MAX_TOTAL_BUDGET={fields.MAX_TOTAL_BUDGET}"
        )

    cached_budget = _FTFF_COMBO_CACHE.get("budget")
    if cached_budget == total_budget:
        return int(_FTFF_COMBO_CACHE.get("n_combos") or 0)

    ft = np.zeros((fields.MAX_FTFF_COMBOS,), dtype=np.int32)
    ff = np.zeros((fields.MAX_FTFF_COMBOS,), dtype=np.int32)

    idx = 0
    for ft_gems in range(total_budget + 1):
        for ff_gems in range(total_budget - ft_gems + 1):
            ft[idx] = ft_gems
            ff[idx] = ff_gems
            idx += 1

    n_combos = idx
    fields.ftff_combo_ft.from_numpy(ft)
    fields.ftff_combo_ff.from_numpy(ff)
    _FTFF_COMBO_CACHE["budget"] = total_budget
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
    if _FORCE_SYNC or (for_timing and _SYNC_FOR_TIMING):
        ti.sync()


def _ensure_batch_staging():
    global _BATCH_STAGING
    if _BATCH_STAGING is not None:
        return _BATCH_STAGING
    _BATCH_STAGING = {
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
        "work_items": np.zeros((MAX_WORK_ITEMS, 8), dtype=np.int32),
        "fever_masks": np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8),
        # [pp, cm, fm, p_val, s_val, ft, ff]
        "genome_base_stats": np.zeros((MAX_GENOMES, 7), dtype=np.int16),
    }
    return _BATCH_STAGING


def _ensure_mega_staging():
    global _MEGA_STAGING
    if _MEGA_STAGING is not None:
        return _MEGA_STAGING
    _MEGA_STAGING = {
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
        "work_items": np.zeros((MAX_WORK_ITEMS, 8), dtype=np.int32),
        "fever_masks": np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8),
        # [pp, cm, fm, p_val, s_val, ft, ff]
        "genome_base_stats": np.zeros((MAX_GENOMES, 7), dtype=np.int16),
    }
    return _MEGA_STAGING


def _ensure_parallel_staging():
    """
    Allocate and reuse staging buffers for solve_genomes_parallel().

    These buffers avoid per-call np.zeros() allocations which are expensive
    due to memory allocation + CPU zeroing overhead.
    """
    global _PARALLEL_STAGING
    if _PARALLEL_STAGING is not None:
        return _PARALLEL_STAGING
    _PARALLEL_STAGING = {
        # Per-genome stats (uploaded once per call)
        # [pp, cm, fm, p_val, s_val, ft, ff]
        "genome_base_stats": np.zeros((MAX_GENOMES, 7), dtype=np.int16),

        # Per-work-item buffers (reused per chunk)
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
        "work_items": np.zeros((MAX_WORK_ITEMS, 8), dtype=np.int32),
    }
    return _PARALLEL_STAGING


def is_refs_loaded() -> bool:
    """Check if reference arrays have been loaded."""
    return _ref_loaded


# ============================================================================
# INITIALIZATION HELPERS
# ============================================================================

def ensure_ready(ref_arrays=None, *, need_grid=False, timeline_grid=None):
    """
    Ensure Taichi and GPU fields are ready for use.

    This is the centralized initialization function that maintains
    the same order and semantics as the original scattered checks.

    Args:
        ref_arrays: Reference arrays to load (optional)
        need_grid: Whether grid fields are required
        timeline_grid: Timeline grid to upload (optional, requires need_grid=True)
    """
    # Import here to avoid circular dependency
    from .timeline import _upload_timeline_grid

    # 1. Taichi initialization
    if not is_initialized():
        init_taichi_vulkan()

    # 2. Field allocation (includes bind_fields to kernels)
    if not is_fields_allocated():
        ensure_fields_allocated()

    # 3. Reference arrays - upload only when needed (or when ref source changes)
    # This preserves the old behavior where callers could load once and reuse.
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
        _upload_timeline_grid(timeline_grid)


# ============================================================================
# REFERENCE ARRAY LOADING
# ============================================================================

def load_ref_arrays(ref_arrays: dict):
    """
    Upload reference arrays to GPU fields.

    Must be called once before using optimize_gems_batch_gpu().
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
