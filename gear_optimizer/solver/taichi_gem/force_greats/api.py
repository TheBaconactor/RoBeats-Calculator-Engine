"""
ForceGreatsFinder GPU - Python wrapper (Taichi/Vulkan).

Public entrypoint:
  - solve_force_greats_finder_gpu(...)

This module is called from the scoring pipeline and must remain API-stable.
"""

from __future__ import annotations

import os
import time
from typing import Any

import numpy as np
import taichi as ti

from .. import api as gem_api
from .. import fields as gem_fields
from . import fields as fg_fields
from . import kernels as fg_kernels


# ============================================================================
# ASYNC PIPELINING (enabled by default, disable with USE_ASYNC_FG=0)
# ============================================================================
# When enabled, dict construction is offloaded to background thread
# while GPU can continue with other work.
_USE_ASYNC_FG = os.environ.get("USE_ASYNC_FG", "1") == "1"


# ============================================================================
# SYNC POLICY
# ============================================================================
# See `gear_optimizer.solver.taichi_gem.api` for rationale.
_SYNC_FOR_TIMING = os.environ.get("GPU_SYNC_FOR_TIMING", "0") == "1"
_FORCE_SYNC = os.environ.get("GPU_FORCE_SYNC", "0") == "1"
# Per-chunk sync fallback for TDR-prone Windows systems (default OFF for performance)
_SYNC_PER_CHUNK = os.environ.get("FG_SYNC_PER_CHUNK", "0") == "1"


def _maybe_sync(*, for_timing: bool = False) -> None:
    if _FORCE_SYNC or (for_timing and _SYNC_FOR_TIMING):
        ti.sync()


# Enable detailed FG GPU timing output
_PERF_TIMING = os.environ.get("PERF_TIMING", "0") == "1"

# Recovery: Taichi/Vulkan backend can occasionally fault on Windows (driver reset,
# device lost, or internal assertion failures). Retry with a hard Taichi reset.
try:
    _FG_VULKAN_RETRIES = int(os.environ.get("FG_VULKAN_RETRIES", "1"))
except Exception:
    _FG_VULKAN_RETRIES = 1


# ============================================================================
# UPLOAD CACHES (avoid repeated large allocations)
# ============================================================================

# Upload cache keys. Endpoints-only keys caused collisions in tests (different songs
# can share length/first/last but differ internally). Include the backing buffer
# pointer plus a few sampled timestamps to keep this check O(1) and robust.
_fg_last_song_key = None  # (ptr, n, first, last, mid, q1, q3)
_fg_last_great_key = None  # (ptr, n, first, last, mid, q1, q3)
_fg_song_upload_buf: np.ndarray | None = None
_fg_great_upload_buf: np.ndarray | None = None
_fg_forced_upload_buf: np.ndarray | None = None
_fg_ftff_upload_buf: dict[str, np.ndarray] | None = None

# Cached buffers for genome stats uploads (reuse to avoid alloc churn)
_fg_genome_stats_buf: np.ndarray | None = None
_fg_flat_work_buf: dict[str, np.ndarray] | None = None

# Upload/build caches (avoid huge repeated host->device transfers)
_fg_genome_stats_upload_key: tuple[int, int] | None = None  # (n_genomes, hash)
_fg_flat_work_key: tuple[int, int] | None = None  # (n_genomes, n_ftff)
_fg_forced_configs_upload_key: tuple[int, int, int] | None = None  # (id(fg_configs), n_cfg, n_sections)

# Pair-caps upload state. The flat kernel clamps FP targets using per-section
# forced-count caps stored in fg_pair_caps.
# leaving this field uninitialized (default zeros) effectively disables forced
# greats. When no pair caps grid is provided, default to "no cap" (int32 max).
_fg_pair_caps_state: str | None = None  # "default" | "custom"
_fg_pair_caps_default_buf: np.ndarray | None = None
_fg_pair_caps_custom_key: tuple[int, int, int, int] | None = None  # (ptr, h, w, sections)


def _forced_configs_sig(fg_configs: list, n_sections: int) -> tuple:
    """
    Lightweight, content-based signature for an FG config list.

    Important: Caching by `id(fg_configs)` is unsafe because `id` values can be
    reused after GC, leading to stale forced-config buffers being reused across
    different config lists (wrong results). This signature is intentionally O(1)
    (samples a few configs) to remain cheap in hot paths.
    """
    try:
        n_total = int(len(fg_configs))
    except Exception:
        return (0, 0, ())

    if n_total <= 0:
        return (0, int(n_sections), ())

    n_sections = int(n_sections)
    if n_sections <= 0:
        return (n_total, 0, ())

    def _norm(cfg) -> tuple:
        try:
            seq = cfg  # tuple/list
            k = len(seq)
        except Exception:
            return (0,) * n_sections
        out = []
        for i in range(n_sections):
            out.append(int(seq[i]) if i < k else 0)
        return tuple(out)

    # Sample first/middle/last (and a second element when present).
    first = _norm(fg_configs[0])
    mid = _norm(fg_configs[n_total // 2])
    last = _norm(fg_configs[n_total - 1])
    second = _norm(fg_configs[1]) if n_total > 1 else first
    return (n_total, n_sections, first, second, mid, last)


def reset_force_greats_api_state() -> None:
    """Reset module-level upload caches after `ti.reset()`."""
    global _fg_last_song_key, _fg_last_great_key
    global _fg_song_upload_buf, _fg_great_upload_buf, _fg_forced_upload_buf, _fg_ftff_upload_buf
    global _fg_genome_stats_buf, _fg_flat_work_buf
    global _fg_genome_stats_upload_key, _fg_flat_work_key
    global _fg_forced_configs_upload_key
    global _fg_pair_caps_state, _fg_pair_caps_default_buf, _fg_pair_caps_custom_key

    _fg_last_song_key = None
    _fg_song_upload_buf = None
    _fg_last_great_key = None
    _fg_great_upload_buf = None
    _fg_forced_upload_buf = None
    _fg_ftff_upload_buf = None
    _fg_genome_stats_buf = None
    _fg_flat_work_buf = None
    _fg_genome_stats_upload_key = None
    _fg_flat_work_key = None
    _fg_forced_configs_upload_key = None
    _fg_pair_caps_state = None
    _fg_pair_caps_default_buf = None
    _fg_pair_caps_custom_key = None


def _is_vulkan_backend_failure(exc: BaseException) -> bool:
    msg = str(exc)
    needles = (
        "taichi::lang::gfx",
        "RHI Error",
        "Vulkan",
        "failed to create semaphore",
        "device_->map(",
        "HostDeviceContextBlitter",
        "VK_ERROR_DEVICE_LOST",
        "VK_ERROR_OUT_OF_DEVICE_MEMORY",
    )
    return any(n in msg for n in needles)


# ============================================================================
# GLOBAL BEST API (GPU-resident accumulation across groups)
# ============================================================================


def fg_reset_global_best(n_genomes: int) -> None:
    """
    Reset global best fields before multi-group processing.

    Call this once at the start of a batch of FG groups, before the loop.
    All global best scores will be set to -1 (sentinel).

    Args:
        n_genomes: Number of genomes to reset
    """
    fg_fields.ensure_ready_with_warmup()
    fg_kernels.fg_reset_global_best_kernel(int(n_genomes))


def fg_accumulate_global_best(n_genomes: int) -> None:
    """
    Update global best with current call's results (GPU-side comparison).

    Call this after each solve_force_greats_finder_gpu() call (with accumulate_global=True)
    to track the best results across all groups without downloading to CPU.

    Args:
        n_genomes: Number of genomes to compare
    """
    fg_kernels.fg_update_global_best_kernel(int(n_genomes))


def fg_download_global_best(n_genomes: int) -> dict[str, np.ndarray]:
    """
    Download final global best results after all groups processed.

    Call this once at the end of multi-group processing to get the final results.

    Args:
        n_genomes: Number of genomes to download

    Returns:
        Dict with numpy arrays for all result fields (same format as return_raw=True)
    """
    ti.sync()  # Ensure all GPU work is complete
    n = int(n_genomes)
    fg_kernels.fg_pack_global_best_kernel(n)
    packed = fg_fields.fg_global_best_packed.to_numpy()[:n, :]
    return {
        "final_score": packed[:, 0],
        "base_score": packed[:, 1],
        "cfg_idx": packed[:, 2],
        "FT": packed[:, 3],
        "FF": packed[:, 4],
        "g_pp": packed[:, 5],
        "g_cm": packed[:, 6],
        "g_fm": packed[:, 7],
        "g_ov": packed[:, 8],
        "score_penalty": packed[:, 9],
        "fill_penalty": packed[:, 10],
    }


def _ensure_pair_caps_uploaded(pair_caps_grid: np.ndarray | None) -> None:
    global _fg_pair_caps_state, _fg_pair_caps_default_buf
    global _fg_pair_caps_custom_key

    expected_shape = (
        fg_fields.FG_MAX_STAT + 1,
        fg_fields.FG_MAX_STAT + 1,
        fg_fields.FG_MAX_SECTIONS,
    )

    if pair_caps_grid is None:
        if _fg_pair_caps_state == "default":
            return
        if _fg_pair_caps_default_buf is None:
            _fg_pair_caps_default_buf = np.full(
                expected_shape,
                np.iinfo(np.int32).max,
                dtype=np.int32,
            )
        fg_fields.fg_pair_caps.from_numpy(_fg_pair_caps_default_buf)
        _fg_pair_caps_state = "default"
        _fg_pair_caps_custom_key = None
        return

    arr = np.asarray(pair_caps_grid, dtype=np.int32)
    if arr.shape != expected_shape:
        raise ValueError(f"pair_caps_grid must be shape {expected_shape}, got {arr.shape}")
    try:
        ptr = int(arr.__array_interface__["data"][0])
    except Exception:
        ptr = 0
    key = (ptr, int(arr.shape[0]), int(arr.shape[1]), int(arr.shape[2]))
    if _fg_pair_caps_state == "custom" and _fg_pair_caps_custom_key == key:
        return
    fg_fields.fg_pair_caps.from_numpy(arr)
    _fg_pair_caps_state = "custom"
    _fg_pair_caps_custom_key = key


def _get_genome_stats_buf() -> np.ndarray:
    """Get or allocate a persistent buffer for genome stats (N, 7)."""
    global _fg_genome_stats_buf
    if _fg_genome_stats_buf is None:
        # [pp, cm, fm, p, s, ft, ff]
        _fg_genome_stats_buf = np.zeros((gem_fields.MAX_GENOMES, 7), dtype=np.int16)
    return _fg_genome_stats_buf


def _fg_upload_song_timestamps(timestamps_np: np.ndarray) -> int:
    """Upload song timestamps to GPU (cached by (len, first, last))."""
    global _fg_last_song_key, _fg_song_upload_buf

    n = int(len(timestamps_np))
    if n <= 0:
        return 0
    if n > fg_fields.FG_MAX_SONG_NOTES:
        raise ValueError(f"Song too long for FG GPU timestamps: {n} > {fg_fields.FG_MAX_SONG_NOTES}")

    # Cache key must disambiguate different charts with identical endpoints.
    # Use backing pointer + a few sampled points (O(1), robust in practice).
    try:
        ptr = int(timestamps_np.__array_interface__["data"][0])
    except Exception:
        ptr = 0
    first = float(timestamps_np[0])
    last = float(timestamps_np[-1])
    mid = float(timestamps_np[n // 2]) if n > 1 else first
    q1 = float(timestamps_np[n // 4]) if n > 3 else mid
    q3 = float(timestamps_np[(3 * n) // 4]) if n > 3 else mid
    key = (ptr, n, first, last, mid, q1, q3)
    if _fg_last_song_key == key:
        return n

    if _fg_song_upload_buf is None:
        _fg_song_upload_buf = np.zeros((fg_fields.FG_MAX_SONG_NOTES,), dtype=np.float32)

    buf = _fg_song_upload_buf
    buf[:n] = np.asarray(timestamps_np, dtype=np.float32)
    if n < fg_fields.FG_MAX_SONG_NOTES:
        buf[n:] = 0.0

    fg_fields.song_timestamps.from_numpy(buf)
    _fg_last_song_key = key
    return n


def _fg_use_great_candidate_alias() -> None:
    """
    Alias great-candidate timestamps to the main song timestamps field.

    This avoids a redundant upload when great candidates are not provided (or
    intentionally identical to timestamps). Kernels will read the same field for
    both `song_timestamps` and `song_timestamps_great_candidate`.
    """
    # Rebind kernel-side pointer (safe: Taichi reads global field reference).
    fg_kernels.song_timestamps_great_candidate = fg_fields.song_timestamps


def _fg_use_great_candidate_field() -> None:
    """Use the separate great-candidate field (must have been uploaded)."""
    fg_kernels.song_timestamps_great_candidate = fg_fields.song_timestamps_great_candidate


def _fg_upload_great_candidate_timestamps(candidate_np: np.ndarray, n: int) -> None:
    """Upload great-candidate timestamps to GPU (cached by (len, first, last))."""
    global _fg_last_great_key, _fg_great_upload_buf

    if n <= 0:
        return
    if int(len(candidate_np)) != n:
        raise ValueError(f"great_candidate_timestamps length mismatch: {len(candidate_np)} != {n}")

    try:
        ptr = int(candidate_np.__array_interface__["data"][0])
    except Exception:
        ptr = 0
    first = float(candidate_np[0])
    last = float(candidate_np[-1])
    mid = float(candidate_np[n // 2]) if n > 1 else first
    q1 = float(candidate_np[n // 4]) if n > 3 else mid
    q3 = float(candidate_np[(3 * n) // 4]) if n > 3 else mid
    key = (ptr, n, first, last, mid, q1, q3)
    if _fg_last_great_key == key:
        _fg_use_great_candidate_field()
        return

    if _fg_great_upload_buf is None:
        _fg_great_upload_buf = np.zeros((fg_fields.FG_MAX_SONG_NOTES,), dtype=np.float32)

    buf = _fg_great_upload_buf
    buf[:n] = np.asarray(candidate_np, dtype=np.float32)
    if n < fg_fields.FG_MAX_SONG_NOTES:
        buf[n:] = 0.0

    fg_fields.song_timestamps_great_candidate.from_numpy(buf)
    _fg_last_great_key = key
    _fg_use_great_candidate_field()


def _solve_force_greats_finder_gpu_impl(
    genome_stats_list: list[dict[str, Any]] | np.ndarray,
    timestamps_np: np.ndarray,
    great_candidate_timestamps_np: np.ndarray | None,
    long_notes: int,
    last_note_time: float,
    fg_configs: list,
    ftff_pairs: list,
    *,
    n_sections: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    pair_caps_grid: np.ndarray | None = None,
    cfg_chunk: int | None = None,
    return_raw: bool = False,
    accumulate_global: bool = False,
    base_cfg_offset: int = 0,
    upload_genome_stats: bool = True,
) -> list[dict[str, Any]] | dict[str, np.ndarray] | None:
    """
    Full GPU ForceGreatsFinder (tolerant mode).

    Args:
        genome_stats_list: Either list[dict] with keys base_pp/cm/fm/p_val/s_val/ft_stat/ff_stat,
                          OR numpy array of shape (n_genomes, 7) with same column order.
        return_raw: If True, return dict of numpy arrays instead of list[dict].
                    Keys: 'final_score', 'base_score', 'cfg_idx', 'FT', 'FF',
                          'g_pp', 'g_cm', 'g_fm', 'g_ov', 'score_penalty', 'fill_penalty'
        accumulate_global: If True, update GPU-resident global best fields instead of downloading.
                          Caller must use fg_reset_global_best() before the loop and
                          fg_download_global_best() after. Returns None when True.
        base_cfg_offset: Offset added to cfg indices before storing. Use this when making
                        multiple GPU calls with different config lists to maintain global
                        cfg indexing. Default 0 for single-call usage.

    Returns:
        If accumulate_global=True: None (results accumulated on GPU)
        If return_raw=False: list aligned with genome_stats_list with dict per genome.
        If return_raw=True: dict of numpy arrays (much faster, no Python object creation).
    """
    if cfg_chunk is None:
        cfg_chunk = fg_fields.FG_MAX_CONFIGS

    # Handle both list and numpy array (numpy arrays have ambiguous truth value)
    if isinstance(genome_stats_list, np.ndarray):
        if genome_stats_list.shape[0] == 0:
            return [] if not return_raw else {}
    elif not genome_stats_list:
        return [] if not return_raw else {}

    if "Fever Time" not in ref_arrays or "Fever Fill Rate" not in ref_arrays:
        raise KeyError("FG finder GPU requires ref_arrays to include 'Fever Time' and 'Fever Fill Rate'")

    # Ensure shared Taichi runtime + base fields + reference arrays are ready.
    gem_api.ensure_ready(ref_arrays)

    # Ensure FG-specific fields are allocated, bound, AND kernels pre-warmed.
    fg_fields.ensure_ready_with_warmup()

    n_genomes = int(len(genome_stats_list))
    if n_genomes > gem_fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes for FG finder: {n_genomes} > {gem_fields.MAX_GENOMES}")

    timestamps_np = np.asarray(timestamps_np, dtype=np.float32)
    total_notes = _fg_upload_song_timestamps(timestamps_np)

    if great_candidate_timestamps_np is None:
        # Default: alias great candidates to the main timestamps field (no upload).
        _fg_last_great_key = _fg_last_song_key
        _fg_use_great_candidate_alias()
    else:
        great_candidate_timestamps_np = np.asarray(great_candidate_timestamps_np, dtype=np.float32)
        # If caller passed the same array (or a view), alias and skip upload.
        try:
            same_buf = np.shares_memory(great_candidate_timestamps_np, timestamps_np)
        except Exception:
            same_buf = False
        if same_buf:
            _fg_last_great_key = _fg_last_song_key
            _fg_use_great_candidate_alias()
        else:
            _fg_upload_great_candidate_timestamps(great_candidate_timestamps_np, total_notes)
    if total_notes <= 0:
        return []

    # Timing instrumentation (when PERF_TIMING=1)
    _perf = _PERF_TIMING
    t_upload = 0.0
    t_kernel = 0.0
    t_download = 0.0
    _t0 = time.perf_counter() if _perf else 0.0

    global _fg_genome_stats_upload_key
    if upload_genome_stats:
        # Upload per-genome base stats using cached buffers
        stats_buf = _get_genome_stats_buf()

        # Fast path: if genome_stats_list is already a numpy array, use directly
        if isinstance(genome_stats_list, np.ndarray):
            # Expect shape (n_genomes, 7) with columns: pp, cm, fm, p_val, s_val, ft_stat, ff_stat
            stats_buf[:n_genomes, :7] = genome_stats_list[:n_genomes, :7]
        else:
            # Slow path: unpack list of dicts
            for i, st in enumerate(genome_stats_list):
                stats_buf[i, 0] = int(st.get("base_pp", 0))
                stats_buf[i, 1] = int(st.get("base_cm", 0))
                stats_buf[i, 2] = int(st.get("base_fm", 0))
                stats_buf[i, 3] = int(st.get("base_p_val", 0))
                stats_buf[i, 4] = int(st.get("base_s_val", 0))
                stats_buf[i, 5] = int(st.get("base_ft_stat", 0))
                stats_buf[i, 6] = int(st.get("base_ff_stat", 0))

        # Upload genome base stats.
        #
        # IMPORTANT: `genome_base_stats` is shared across multiple GPU entrypoints
        # (gem solver, GA solver, FG solver). Caching across independent entrypoints
        # can be unsafe because another entrypoint may overwrite the field.
        #
        # For in-process batched FG tasks (GpuExecutor), callers can intentionally
        # set `upload_genome_stats=False` for subsequent tasks when they know the
        # field is still valid (no intervening GPU entrypoints).
        gem_fields.genome_base_stats.from_numpy(stats_buf)

        try:
            if isinstance(genome_stats_list, np.ndarray):
                ptr = int(genome_stats_list.__array_interface__["data"][0])
            else:
                ptr = int(id(genome_stats_list))
        except Exception:
            ptr = int(id(genome_stats_list))
        _fg_genome_stats_upload_key = (int(n_genomes), int(ptr))
    else:
        try:
            ok = _fg_genome_stats_upload_key is not None and int(_fg_genome_stats_upload_key[0]) == int(n_genomes)
        except Exception:
            ok = False
        if not ok:
            raise RuntimeError(
                "Skipping genome stats upload without a compatible prior upload; "
                "this indicates a misuse of upload_genome_stats=False."
            )

    # Upload FT/FF list
    n_ftff = int(len(ftff_pairs))
    if n_ftff <= 0:
        return []
    if n_ftff > fg_fields.FG_MAX_FTFF:
        raise ValueError(f"Too many FT/FF pairs: {n_ftff} > {fg_fields.FG_MAX_FTFF}")

    global _fg_ftff_upload_buf
    if _fg_ftff_upload_buf is None:
        _fg_ftff_upload_buf = {
            "ft": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
            "ff": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
        }

    ft_buf = _fg_ftff_upload_buf["ft"]
    ff_buf = _fg_ftff_upload_buf["ff"]

    # Fast path: vectorized fill (ftff_pairs is typically list[tuple[int,int]]).
    # Kernel bounds use n_ftff, so we don't need to zero the remainder.
    try:
        arr_pairs = np.asarray(ftff_pairs, dtype=np.int32)
        if arr_pairs.ndim == 2 and arr_pairs.shape[1] >= 2 and int(arr_pairs.shape[0]) >= n_ftff:
            ft_buf[:n_ftff] = arr_pairs[:n_ftff, 0]
            ff_buf[:n_ftff] = arr_pairs[:n_ftff, 1]
        else:
            for i, (ftg, ffg) in enumerate(ftff_pairs):
                ft_buf[i] = int(ftg)
                ff_buf[i] = int(ffg)
    except Exception:
        for i, (ftg, ffg) in enumerate(ftff_pairs):
            ft_buf[i] = int(ftg)
            ff_buf[i] = int(ffg)

    fg_fields.fg_ft_list.from_numpy(ft_buf)
    fg_fields.fg_ff_list.from_numpy(ff_buf)

    # Reset outputs and init stage1
    fg_kernels.fg_reset_best_kernel(n_genomes)
    fg_kernels.fg_stage1_init_kernel(n_genomes, n_ftff)
    _maybe_sync(for_timing=True)

    # Mark end of upload phase
    if _perf:
        t_upload = time.perf_counter() - _t0
        _t1 = time.perf_counter()

    # Generate flat work items: (genome_id, ftff_id) pairs
    # Total work items = n_genomes * n_ftff
    n_work_items = n_genomes * n_ftff
    if n_work_items > fg_fields.FG_MAX_FLAT_WORK_ITEMS:
        raise ValueError(f"Too many flat work items: {n_work_items} > {fg_fields.FG_MAX_FLAT_WORK_ITEMS}")

    # Build flat work items ON GPU (cached by (n_genomes, n_ftff)).
    # This avoids uploading two 4M-element arrays from CPU on every call.
    global _fg_flat_work_key
    flat_key = (n_genomes, n_ftff)
    if _fg_flat_work_key != flat_key:
        fg_kernels.fg_build_flat_work_kernel(int(n_genomes), int(n_ftff))
        _fg_flat_work_key = flat_key

    # Pair caps (once per call). The flat kernel always clamps by fg_pair_caps,
    # so we must ensure it is initialized even when the caller does not supply
    # a caps grid.
    _ensure_pair_caps_uploaded(pair_caps_grid)

    # Upload configs in chunks and run Stage 1 FLAT kernel
    n_cfg_total = int(len(fg_configs))
    if n_cfg_total <= 0:
        return []

    n_sections = int(n_sections) if int(n_sections) > 0 else 1
    if n_sections > fg_fields.FG_MAX_SECTIONS:
        raise ValueError(f"Too many FG sections: {n_sections} > {fg_fields.FG_MAX_SECTIONS}")

    global _fg_forced_upload_buf
    # Ensure buffer is allocated AND large enough (in case FG_MAX_CONFIGS changed)
    if _fg_forced_upload_buf is None or _fg_forced_upload_buf.shape[0] < fg_fields.FG_MAX_CONFIGS:
        _fg_forced_upload_buf = np.zeros((fg_fields.FG_MAX_CONFIGS, fg_fields.FG_MAX_SECTIONS), dtype=np.int32)

    # Adaptive cfg_chunk: target ~2M threads per kernel to avoid TDR while staying 100% utilized.
    #
    # NOTE: The Vulkan stage1 flat kernel uses cfg-tiling: one thread handles up to FG_STAGE1_CFG_TILE configs.
    # So "threads per kernel" is ~n_work_items * ceil(cfg_chunk / tile), not n_work_items * cfg_chunk.
    #
    # TDR (Timeout Detection and Recovery) triggers after ~2s on Windows if GPU is unresponsive.
    # With heavy per-thread work (gem optimization + penalty loops), we need to limit work per launch.
    TARGET_THREADS_PER_KERNEL = 2_000_000
    try:
        stage1_cfg_tile = int(getattr(fg_kernels, "FG_STAGE1_CFG_TILE", 1))
    except Exception:
        stage1_cfg_tile = 1
    if stage1_cfg_tile <= 0:
        stage1_cfg_tile = 1

    if cfg_chunk is None or int(cfg_chunk) <= 0:
        # Auto-calculate based on work items
        if gem_fields.IS_METAL:
            # Metal kernel (fg_stage1_kernel) loops SEQUENTIALLY over cfg_chunk.
            # We must keep this small to avoid TDR (watchdog timeout).
            # A safe bet is ~16-32 configs per kernel launch.
            cfg_chunk = 16
        else:
            # Flattened kernel parallelizes over cfg tiles (each thread handles up to stage1_cfg_tile configs).
            target_tiles = max(1, TARGET_THREADS_PER_KERNEL // max(1, n_work_items))
            cfg_chunk = max(256, int(target_tiles * stage1_cfg_tile))
    else:
        cfg_chunk = int(cfg_chunk)

    cfg_chunk = min(cfg_chunk, n_cfg_total, fg_fields.FG_MAX_CONFIGS)
    n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk

    if _perf:
        approx_tiles = (cfg_chunk + stage1_cfg_tile - 1) // stage1_cfg_tile
        print(
            f"[PERF] FG adaptive chunking: n_work={n_work_items} cfg_chunk={cfg_chunk} "
            f"n_cfg={n_cfg_total} n_chunks={n_chunks} threads_per_kernel~={n_work_items * approx_tiles:,} "
            f"(tiles={approx_tiles}, tile={stage1_cfg_tile})"
        )

    # Pre-fetch buffer reference
    buf = _fg_forced_upload_buf

    # Config upload caching: avoid repeated CPU packing and host->device uploads
    # when the config list content is unchanged across calls.
    global _fg_forced_configs_upload_key
    cfg_upload_key = None
    can_skip_forced_upload = False
    if n_chunks == 1:
        try:
            cfg_upload_key = _forced_configs_sig(fg_configs, int(n_sections))
            can_skip_forced_upload = _fg_forced_configs_upload_key == cfg_upload_key
        except Exception:
            cfg_upload_key = None
    else:
        # Chunked mode packs different slices into the same buffer; skip caching.
        _fg_forced_configs_upload_key = None

    for cfg_offset in range(0, n_cfg_total, cfg_chunk):
        chunk = fg_configs[cfg_offset : cfg_offset + cfg_chunk]
        n_cfg = int(len(chunk))

        if can_skip_forced_upload:
            # Configs unchanged (n_chunks==1 only); keep existing GPU buffer.
            can_skip_forced_upload = False
        else:
            # Zero out and pack config chunk
            buf[:n_cfg, :] = 0
            try:
                arr_chunk = np.array(chunk, dtype=np.int32)
                if arr_chunk.ndim == 2:
                    k = arr_chunk.shape[1]
                    cols = min(k, n_sections)
                    buf[:n_cfg, :cols] = arr_chunk[:, :cols]
                else:
                    for i, cfg in enumerate(chunk):
                        limit = min(n_sections, len(cfg))
                        buf[i, :limit] = cfg[:limit]
            except Exception:
                for i, cfg in enumerate(chunk):
                    limit = min(n_sections, len(cfg))
                    buf[i, :limit] = cfg[:limit]

            # Upload only the active chunk via a small external array (avoid 64MB from_numpy each call).
            fg_kernels.fg_upload_forced_counts_kernel(int(n_cfg), buf[:n_cfg, :])
            if cfg_upload_key is not None and n_chunks == 1 and cfg_offset == 0:
                _fg_forced_configs_upload_key = cfg_upload_key

        # Call Kernel based on platform
        # On Metal (macOS), 64-bit atomics for the flat kernel are not supported.
        # Fallback to the sequential-loop kernel (fg_stage1_kernel) which is atomic-free.
        # Add base_cfg_offset for global cfg indexing across multiple GPU calls
        global_cfg_offset = cfg_offset + base_cfg_offset
        if gem_fields.IS_METAL:
            fg_kernels.fg_stage1_kernel(
                int(n_genomes),
                int(total_notes),
                int(long_notes),
                float(last_note_time),
                int(total_budget),
                int(gem_scale_fever),
                int(n_cfg),
                int(n_sections),
                int(n_ftff),
                int(global_cfg_offset),
                int(is_p_ft),
                int(is_s_ft),
                int(is_p_ff),
                int(is_s_ff),
                int(is_p_pp),
                int(is_s_pp),
                int(is_p_cm),
                int(is_s_cm),
                int(is_p_fm),
                int(is_s_fm),
                int(is_p_ov),
                int(is_s_ov),
            )
        else:
            # FLATTENED kernel (GPU-friendly: one thread per (work_item, cfg_tile)).
            # Specialize the local state for small section counts (common path) to reduce register pressure.
            if int(n_sections) <= 3:
                fg_kernels.fg_stage1_flat_kernel_small3(
                    int(n_work_items),
                    int(n_cfg),
                    int(global_cfg_offset),
                    int(total_notes),
                    int(long_notes),
                    float(last_note_time),
                    int(total_budget),
                    int(gem_scale_fever),
                    int(n_sections),
                    int(is_p_ft),
                    int(is_s_ft),
                    int(is_p_ff),
                    int(is_s_ff),
                    int(is_p_pp),
                    int(is_s_pp),
                    int(is_p_cm),
                    int(is_s_cm),
                    int(is_p_fm),
                    int(is_s_fm),
                    int(is_p_ov),
                    int(is_s_ov),
                )
            else:
                fg_kernels.fg_stage1_flat_kernel(
                    int(n_work_items),
                    int(n_cfg),
                    int(global_cfg_offset),
                    int(total_notes),
                    int(long_notes),
                    float(last_note_time),
                    int(total_budget),
                    int(gem_scale_fever),
                    int(n_sections),
                    int(is_p_ft),
                    int(is_s_ft),
                    int(is_p_ff),
                    int(is_s_ff),
                    int(is_p_pp),
                    int(is_s_pp),
                    int(is_p_cm),
                    int(is_s_cm),
                    int(is_p_fm),
                    int(is_s_fm),
                    int(is_p_ov),
                    int(is_s_ov),
                )
        # Optional per-chunk sync for TDR-prone systems (disabled by default)
        if _SYNC_PER_CHUNK:
            ti.sync()

    # Single sync after all config chunks dispatched - required before Stage 2
    # This is the key optimization: N chunks now cause 1 sync instead of N syncs
    ti.sync()

    # Stage 2: Reduce across ftff to find best per genome
    fg_kernels.fg_stage2_kernel(n_genomes, n_ftff)
    _maybe_sync(for_timing=True)

    # Accumulate global best (GPU-resident) if requested
    if accumulate_global:
        fg_kernels.fg_update_global_best_kernel(n_genomes)
        if _perf:
            ti.sync()
            t_kernel = time.perf_counter() - _t1
            t_total = t_upload + t_kernel
            n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
            print(
                f"[PERF] FG GPU (ACCUMULATE): upload={t_upload * 1000:.1f}ms kernel={t_kernel * 1000:.1f}ms "
                f"total={t_total * 1000:.1f}ms (genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
            )
        return None  # Results accumulated on GPU, not downloaded

    # Mark end of kernel phase
    if _perf:
        t_kernel = time.perf_counter() - _t1
        _t2 = time.perf_counter()

    # Pack results on GPU (all 11 fields → 1 array)
    fg_kernels.fg_pack_results_kernel(n_genomes)

    # Download results (1 transfer instead of 11!)
    packed_results = fg_fields.fg_best_packed.to_numpy()[:n_genomes, :]

    # Unpack on CPU (trivial cost compared to 11 GPU waits)
    out_final = packed_results[:, 0]
    out_base = packed_results[:, 1]
    out_cfg = packed_results[:, 2]
    out_ft = packed_results[:, 3]
    out_ff = packed_results[:, 4]
    out_gpp = packed_results[:, 5]
    out_gcm = packed_results[:, 6]
    out_gfm = packed_results[:, 7]
    out_gov = packed_results[:, 8]
    out_sp = packed_results[:, 9]
    out_fp = packed_results[:, 10]

    # Mark end of download phase (before dict construction)
    if _perf:
        t_download = time.perf_counter() - _t2
        _t3 = time.perf_counter()

    # Build result dicts (optionally offload to background thread)
    def _build_results(arrays: dict, n: int) -> list[dict[str, Any]]:
        """Helper to build result dicts from numpy arrays."""
        results = []
        for i in range(n):
            results.append(
                {
                    "final_score": int(arrays["final"][i]),
                    "base_score": int(arrays["base"][i]),
                    "cfg_idx": int(arrays["cfg"][i]),
                    "FT": int(arrays["ft"][i]),
                    "FF": int(arrays["ff"][i]),
                    "gem_counts": {
                        "Perfect Points": int(arrays["gpp"][i]),
                        "Combo Multiplier": int(arrays["gcm"][i]),
                        "Fever Multiplier": int(arrays["gfm"][i]),
                        "Element": int(arrays["gov"][i]),
                    },
                    "score_penalty": int(arrays["sp"][i]),
                    "fill_penalty": int(arrays["fp"][i]),
                }
            )
        return results

    # Pack arrays for helper function
    arrays_dict = {
        "final": out_final,
        "base": out_base,
        "cfg": out_cfg,
        "ft": out_ft,
        "ff": out_ff,
        "gpp": out_gpp,
        "gcm": out_gcm,
        "gfm": out_gfm,
        "gov": out_gov,
        "sp": out_sp,
        "fp": out_fp,
    }

    # Fast path: return raw numpy arrays (skip expensive dict building)
    if return_raw:
        if _perf:
            t_dict_build = 0.0  # No dict building
            t_total = t_upload + t_kernel + t_download
            n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
            print(
                f"[PERF] FG GPU (RAW): upload={t_upload * 1000:.1f}ms kernel={t_kernel * 1000:.1f}ms "
                f"download={t_download * 1000:.1f}ms total={t_total * 1000:.1f}ms "
                f"(genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks})"
            )
        return {
            "final_score": out_final,
            "base_score": out_base,
            "cfg_idx": out_cfg,
            "FT": out_ft,
            "FF": out_ff,
            "g_pp": out_gpp,
            "g_cm": out_gcm,
            "g_fm": out_gfm,
            "g_ov": out_gov,
            "score_penalty": out_sp,
            "fill_penalty": out_fp,
        }

    if _USE_ASYNC_FG:
        # Async path: offload dict construction to background thread
        from .async_buffers import get_result_processor

        proc = get_result_processor()
        proc.submit_result_build(arrays_dict, n_genomes, _build_results)
        results = proc.get_results()  # Wait for completion (for now, single-call)
    else:
        # Sync path: build directly
        results = _build_results(arrays_dict, n_genomes)

    # Print timing breakdown
    if _perf:
        t_dict_build = time.perf_counter() - _t3
        t_total = t_upload + t_kernel + t_download + t_dict_build
        n_chunks = (n_cfg_total + cfg_chunk - 1) // cfg_chunk
        async_tag = " [ASYNC]" if _USE_ASYNC_FG else ""
        print(
            f"[PERF] FG GPU: upload={t_upload * 1000:.1f}ms kernel={t_kernel * 1000:.1f}ms "
            f"download={t_download * 1000:.1f}ms dict={t_dict_build * 1000:.1f}ms total={t_total * 1000:.1f}ms "
            f"(genomes={n_genomes}, cfgs={n_cfg_total}, ftff={n_ftff}, chunks={n_chunks}){async_tag}"
        )

    return results


def solve_force_greats_finder_gpu(*args, **kwargs) -> list[dict[str, Any]] | dict[str, np.ndarray] | None:
    """
    Wrapper with recovery for transient Taichi/Vulkan backend failures.

    Also accepts an older positional calling convention used by some scripts:
      - v1: (genome_stats_list, timestamps_np, long_notes, last_note_time, fg_configs, ftff_pairs, *, ...)
      - v2: (genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, fg_configs, ftff_pairs, *, ...)
    """
    # Normalize positional args across legacy and current call patterns.
    if len(args) == 6:
        # Legacy: no great-candidate array positional.
        genome_stats_list, timestamps_np, long_notes, last_note_time, fg_configs, ftff_pairs = args
        great_candidate_timestamps_np = None
    elif len(args) == 7:
        (
            genome_stats_list,
            timestamps_np,
            great_candidate_timestamps_np,
            long_notes,
            last_note_time,
            fg_configs,
            ftff_pairs,
        ) = args
    else:
        raise TypeError(
            "solve_force_greats_finder_gpu expected 6 or 7 positional args: "
            "(genomes, timestamps, [great_candidates], long_notes, last_note_time, fg_configs, ftff_pairs)"
        )

    # Required keyword-only args (kept explicit to avoid silently wrong dispatch).
    required = (
        "n_sections",
        "is_p_ft",
        "is_s_ft",
        "is_p_ff",
        "is_s_ff",
        "is_p_pp",
        "is_s_pp",
        "is_p_cm",
        "is_s_cm",
        "is_p_fm",
        "is_s_fm",
        "is_p_ov",
        "is_s_ov",
        "ref_arrays",
    )
    missing = [k for k in required if k not in kwargs]
    if missing:
        raise TypeError(f"solve_force_greats_finder_gpu missing required keyword arguments: {', '.join(missing)}")

    for attempt in range(max(0, _FG_VULKAN_RETRIES) + 1):
        try:
            return _solve_force_greats_finder_gpu_impl(
                genome_stats_list,
                timestamps_np,
                great_candidate_timestamps_np,
                int(long_notes),
                float(last_note_time),
                fg_configs,
                ftff_pairs,
                n_sections=int(kwargs["n_sections"]),
                is_p_ft=int(kwargs["is_p_ft"]),
                is_s_ft=int(kwargs["is_s_ft"]),
                is_p_ff=int(kwargs["is_p_ff"]),
                is_s_ff=int(kwargs["is_s_ff"]),
                is_p_pp=int(kwargs["is_p_pp"]),
                is_s_pp=int(kwargs["is_s_pp"]),
                is_p_cm=int(kwargs["is_p_cm"]),
                is_s_cm=int(kwargs["is_s_cm"]),
                is_p_fm=int(kwargs["is_p_fm"]),
                is_s_fm=int(kwargs["is_s_fm"]),
                is_p_ov=int(kwargs["is_p_ov"]),
                is_s_ov=int(kwargs["is_s_ov"]),
                ref_arrays=kwargs["ref_arrays"],
                total_budget=int(kwargs.get("total_budget", 90)),
                gem_scale_fever=int(kwargs.get("gem_scale_fever", 3)),
                pair_caps_grid=kwargs.get("pair_caps_grid"),
                cfg_chunk=kwargs.get("cfg_chunk"),
                return_raw=bool(kwargs.get("return_raw", False)),
                accumulate_global=bool(kwargs.get("accumulate_global", False)),
                base_cfg_offset=int(kwargs.get("base_cfg_offset", 0)),
            )
        except Exception as e:
            if attempt >= max(0, _FG_VULKAN_RETRIES) or not _is_vulkan_backend_failure(e):
                raise
            print(
                "[FG GPU] Vulkan backend error; retrying after hard reset "
                f"(attempt {attempt + 1}/{max(0, _FG_VULKAN_RETRIES)})"
            )
            gem_api.hard_reset_taichi(reason=str(e).splitlines()[0][:200])


def solve_force_greats_finder_gpu_tasks(
    genome_stats_list: list[dict[str, Any]] | np.ndarray,
    timestamps_np: np.ndarray,
    great_candidate_timestamps_np: np.ndarray | None,
    long_notes: int,
    last_note_time: float,
    *,
    fg_tasks: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    n_sections: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    pair_caps_grid: np.ndarray | None = None,
    cfg_chunk: int | None = None,
    base_cfg_offset: int = 0,
    accumulate_global: bool = True,
    return_raw: bool = True,
) -> None:
    """
    Execute multiple FG finder tasks as one logical GPU job.

    This is intended for `GpuExecutor` in in-process mode so we can amortize the
    expensive `genome_base_stats` upload across many small breakpoint groups.

    Each task must be a dict containing:
      - counts_list: list of forced-count configs
      - ftff_pairs: list of (ft_gems, ff_gems)
      - optional base_cfg_offset: global cfg index offset
    """
    if not accumulate_global:
        raise ValueError("solve_force_greats_finder_gpu_tasks requires accumulate_global=True")
    if not return_raw:
        raise ValueError("solve_force_greats_finder_gpu_tasks requires return_raw=True")
    if not isinstance(fg_tasks, (list, tuple)):
        raise TypeError("solve_force_greats_finder_gpu_tasks fg_tasks must be a list/tuple of dicts")
    if not fg_tasks:
        return

    uploaded = False
    for task in fg_tasks:
        if not isinstance(task, dict):
            continue
        fg_configs = task.get("counts_list")
        ftff_pairs = task.get("ftff_pairs")
        if not fg_configs or not ftff_pairs:
            continue

        task_offset = int(base_cfg_offset)
        if "base_cfg_offset" in task:
            try:
                task_offset = int(task.get("base_cfg_offset", task_offset) or task_offset)
            except Exception:
                task_offset = int(base_cfg_offset)

        _solve_force_greats_finder_gpu_impl(
            genome_stats_list,
            timestamps_np,
            great_candidate_timestamps_np,
            int(long_notes),
            float(last_note_time),
            fg_configs,
            ftff_pairs,
            n_sections=int(n_sections),
            is_p_ft=int(is_p_ft),
            is_s_ft=int(is_s_ft),
            is_p_ff=int(is_p_ff),
            is_s_ff=int(is_s_ff),
            is_p_pp=int(is_p_pp),
            is_s_pp=int(is_s_pp),
            is_p_cm=int(is_p_cm),
            is_s_cm=int(is_s_cm),
            is_p_fm=int(is_p_fm),
            is_s_fm=int(is_s_fm),
            is_p_ov=int(is_p_ov),
            is_s_ov=int(is_s_ov),
            ref_arrays=ref_arrays,
            total_budget=int(total_budget),
            gem_scale_fever=int(gem_scale_fever),
            pair_caps_grid=pair_caps_grid,
            cfg_chunk=cfg_chunk,
            return_raw=True,
            accumulate_global=True,
            base_cfg_offset=int(task_offset),
            upload_genome_stats=(not uploaded),
        )
        uploaded = True
