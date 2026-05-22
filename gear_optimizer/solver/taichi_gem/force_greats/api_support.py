"""
Force Greats GPU APIs (Taichi/Vulkan).

Public entrypoints:
  - solve_force_greats_finder_gpu(...)

This module is called from the scoring pipeline and must remain API-stable.
"""

from __future__ import annotations

import logging
import os
import hashlib
import time
from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.core.parsing import env_flag, env_int
from gear_optimizer.solver.gpu_tuning_policy import plan_fg_stage1_cfg_chunk

from ..api.sync_policy import maybe_sync
from .. import fields as gem_fields
from . import fields as fg_fields
from . import kernels as fg_kernels

logger = logging.getLogger(__name__)


_ENV_GET = os.environ.get


# ============================================================================
# SYNC POLICY
# ============================================================================
# See `gear_optimizer.solver.taichi_gem.api` for rationale.
_SYNC_FOR_TIMING = _ENV_GET("GPU_SYNC_FOR_TIMING", "0") == "1"
_FORCE_SYNC = _ENV_GET("GPU_FORCE_SYNC", "0") == "1"
# Per-chunk sync fallback for TDR-prone Windows systems (default OFF for performance)
_SYNC_PER_CHUNK = _ENV_GET("FG_SYNC_PER_CHUNK", "0") == "1"

# Enable detailed FG GPU timing output
_PERF_TIMING = _ENV_GET("PERF_TIMING", "0") == "1"
_FG_TRANSFER_TRACE = env_flag("FG_TRANSFER_TRACE")
_GPU_PROFILER_ENABLED = _PERF_TIMING or env_flag("GPU_PROFILER")
_GPU_PROFILER_CACHE = None
_GPU_PROFILER_READY = False
_FG_TARGET_THREADS_PER_KERNEL = env_int("FG_TARGET_THREADS_PER_KERNEL", 0)
_FG_STAGE1_SMALL_SECTIONS_FASTPATH = bool(getattr(fg_kernels, "FG_STAGE1_SMALL_SECTIONS_FASTPATH", False))
_FG_STAGE1_DIRECT_ATOMIC = bool(getattr(fg_kernels, "FG_STAGE1_DIRECT_ATOMIC", False))
_FG_SURFACE_PAIR_REDUCTION_MAX_PAIRS = max(0, min(int(fg_fields.FG_MAX_FTFF), 4096))


def _get_gpu_profiler():
    """
    Lazy import of the global GPU profiler to avoid overhead when disabled.

    Enabled when either PERF_TIMING or GPU_PROFILER is on.
    """
    global _GPU_PROFILER_CACHE, _GPU_PROFILER_READY
    if not _GPU_PROFILER_ENABLED:
        return None
    if _GPU_PROFILER_READY:
        return _GPU_PROFILER_CACHE
    try:
        from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

        p = get_gpu_profiler()
        _GPU_PROFILER_CACHE = p if getattr(p, "enabled", False) else None
    except Exception as e:
        logger.debug(f"api:_get_gpu_profiler: {e}")
        _GPU_PROFILER_CACHE = None
    _GPU_PROFILER_READY = True
    return _GPU_PROFILER_CACHE


def _bytes_of_array(arr: Any) -> int:
    try:
        return int(getattr(arr, "nbytes", 0) or 0)
    except Exception as e:
        logger.debug(f"api:_bytes_of_array: {e}")
        return 0


def _record_upload(name: str, dt_sec: float, bytes_count: int) -> None:
    p = _get_gpu_profiler()
    if p is None:
        return
    try:
        p.record_upload(float(dt_sec), bytes_count=int(bytes_count or 0))
        # Add a named measurement so `GpuProfiler.report(verbose=True)` shows a breakdown.
        p._record(f"fg_upload::{name}", float(dt_sec))  # type: ignore[attr-defined]
    except Exception as e:
        logger.debug(f"api:_record_upload: {e}")
        return


def _record_download(name: str, dt_sec: float, bytes_count: int) -> None:
    p = _get_gpu_profiler()
    if p is None:
        return
    try:
        p.record_download(float(dt_sec), bytes_count=int(bytes_count or 0))
        p._record(f"fg_download::{name}", float(dt_sec))  # type: ignore[attr-defined]
    except Exception as e:
        logger.debug(f"api:_record_download: {e}")
        return


def _record_kernel_wall(name: str, dt_sec: float, *, genome_count: int = 0) -> None:
    p = _get_gpu_profiler()
    if p is None:
        return
    try:
        # "Kernel wall time" measured at sync boundaries (can include some dispatch/packing).
        p.record_kernel(float(dt_sec), genome_count=int(genome_count or 0))
        p._record(f"fg_kernel::{name}", float(dt_sec))  # type: ignore[attr-defined]
    except Exception as e:
        logger.debug(f"api:_record_kernel_wall: {e}")
        return


# Recovery: Taichi/Vulkan backend can occasionally fault on Windows (driver reset,
# device lost, or internal assertion failures). Retry with a hard Taichi reset.
try:
    _FG_VULKAN_RETRIES = int(_ENV_GET("FG_VULKAN_RETRIES", "1"))
except Exception as e:
    logger.debug(f"api:_record_kernel_wall: {e}")
    _FG_VULKAN_RETRIES = 1


# ============================================================================
# UPLOAD CACHES (avoid repeated large allocations)
# ============================================================================

# Upload cache keys. Endpoints-only keys caused collisions in tests (different songs
# can share length/first/last but differ internally). Include the backing buffer
# pointer plus a few sampled timestamps to keep this check O(1) and robust.
#
# For cross-process (IPC) workloads, arrays can be unpickled into fresh buffers
# each request; pointer-only keys would miss and force repeated uploads. We keep a
# second, stable (content-hash) key as a fallback so identical timestamp content
# can reuse already-uploaded GPU fields even when the host buffer address changes.
_fg_last_song_ptr_key = None  # (ptr, n, first, last, mid, q1, q3)
_fg_last_song_key = None  # (n, blake2b_digest)
_fg_last_great_ptr_key = None  # (ptr, n, first, last, mid, q1, q3)
_fg_last_great_key = None  # (n, blake2b_digest)
_fg_last_fever_end_tables_key = None  # (song_key, great_key, last_note_time)
_fg_song_upload_buf: np.ndarray | None = None
_fg_great_upload_buf: np.ndarray | None = None
_fg_forced_upload_buf: np.ndarray | None = None
_fg_ftff_upload_buf: dict[str, np.ndarray] | None = None
_fg_last_ftff_key: tuple | None = None  # (n, first, mid, last) or (n, ptr, ...) depending on input type

# IMPORTANT: Taichi specializes kernels on external-array shapes. Since FG config counts
# vary per song, we must keep external-array shapes stable across the whole runtime
# to avoid shape-mismatch recompilation churn.
#
# To reduce wasted host->device uploads when n_cfg is small, we keep a small tiered
# set of staging shapes and pick the smallest tier that fits each upload.
#
# Override tiers via:
#   FG_FORCED_COUNTS_STAGING_TIERS="256,512,1024,2048,4096"
_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT = 4096
_FG_FORCED_COUNTS_STAGING_TIERS_DEFAULT = (256, 512, 1024, 2048, _FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)
_fg_forced_counts_staging_tiers: tuple[int, ...] | None = None
_fg_forced_counts_staging_pool: dict[int, Any] | None = None

# Optional optimization: force a single Stage-1 band for small workloads.
# This does NOT change the search space or scoring; it only reduces kernel launch overhead.
_FG_SMALL_WORK_SINGLE_BAND = env_flag("FG_SMALL_WORK_SINGLE_BAND", "1")
_FG_SMALL_WORK_MAX_WORK_ITEMS = env_int("FG_SMALL_WORK_MAX_WORK_ITEMS", 20000)
_FG_SMALL_WORK_MAX_CFG_LEN = env_int("FG_SMALL_WORK_MAX_CFG_LEN", _FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)

_fg_cfg_defaults_uploaded = False
_fg_cfg_defaults_buf: dict[str, np.ndarray] | None = None


def _ensure_cfg_mode_defaults() -> None:
    global _fg_cfg_defaults_uploaded, _fg_cfg_defaults_buf
    if _fg_cfg_defaults_uploaded:
        return
    try:
        if _fg_cfg_defaults_buf is None:
            _fg_cfg_defaults_buf = {
                "mode": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
                "base": np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32),
            }
        fg_fields.fg_cfg_mode_list.from_numpy(_fg_cfg_defaults_buf["mode"])
        fg_fields.fg_cfg_base_list.from_numpy(_fg_cfg_defaults_buf["base"])
        _fg_cfg_defaults_uploaded = True
    except Exception as e:
        logger.debug(f"api:_ensure_cfg_mode_defaults: {e}")
        return


def _get_stage1_block_dim() -> int:
    try:
        stage1_block_dim = int(getattr(fg_kernels, "FG_STAGE1_BLOCK_DIM", 64))
    except Exception as e:
        logger.debug(f"api:_get_stage1_block_dim: {e}")
        stage1_block_dim = 64
    if stage1_block_dim <= 0:
        stage1_block_dim = 64
    return int(stage1_block_dim)


def _build_stage1_chunk_plan(*, n_work_items: int, cfg_chunk: int | None, max_cfg_len: int):
    return plan_fg_stage1_cfg_chunk(
        n_work_items=int(n_work_items),
        stage1_block_dim=_get_stage1_block_dim(),
        cfg_chunk=cfg_chunk,
        max_cfg_len=int(max_cfg_len),
        is_metal=bool(gem_fields.IS_METAL),
        target_threads_override=int(_FG_TARGET_THREADS_PER_KERNEL),
        small_work_single_band=bool(_FG_SMALL_WORK_SINGLE_BAND),
        small_work_max_work_items=int(_FG_SMALL_WORK_MAX_WORK_ITEMS),
        small_work_max_cfg_len=int(_FG_SMALL_WORK_MAX_CFG_LEN),
    )


def _maybe_log_single_band(plan, *, n_work_items: int, max_cfg_len: int, label: str = "") -> None:
    if not _PERF_TIMING or not bool(getattr(plan, "single_band_forced", False)):
        return
    if int(getattr(plan, "requested_cfg_chunk", 0)) >= int(max_cfg_len):
        return
    try:
        suffix = f" ({label})" if label else ""
        print(
            f"[PERF] FG single-band{suffix}: work={int(n_work_items)} max_cfg={int(max_cfg_len)} "
            f"cfg_chunk={int(getattr(plan, 'cfg_chunk', max_cfg_len))}"
        )
    except Exception as e:
        logger.debug(f"api:_maybe_log_single_band: {e}")
        return


# Cached buffers for genome stats uploads (reuse to avoid alloc churn)
_fg_genome_stats_buf: np.ndarray | None = None
_fg_flat_work_buf: dict[str, np.ndarray] | None = None

# Cached padded buffers for global_best top-K selection uploads.
_fg_download_topk_base_buf: np.ndarray | None = None
_fg_download_topk_keep_buf: np.ndarray | None = None

# Cached padded buffers for FG signature frontier selection uploads.
_fg_frontier_upload_buf: dict[str, np.ndarray] | None = None

# Upload/build caches (avoid huge repeated host->device transfers)
_fg_genome_stats_upload_key: tuple[int, int] | None = None  # (n_genomes, hash)
_fg_flat_work_key: tuple[int, int] | None = None  # (n_genomes, n_ftff)
_fg_forced_configs_upload_key: tuple[int, int, int] | None = None  # (id(fg_configs), n_cfg, n_sections)

# Device-resident forced-config caching (upload full config list once, reuse across many FT/FF chunks).
_fg_forced_resident_key: tuple | None = None  # signature from _forced_configs_sig
_fg_forced_resident_n_cfg_total: int | None = None
_fg_forced_resident_base_offset: int | None = None

# Pair-caps upload state. The flat kernel clamps FP targets using per-section
# forced-count caps stored in fg_pair_caps.
# leaving this field uninitialized (default zeros) effectively disables forced
# greats. When no pair caps grid is provided, default to "no cap" (int32 max).
_fg_pair_caps_state: str | None = None  # "default" | "custom"
_fg_pair_caps_default_buf: np.ndarray | None = None
_fg_pair_caps_custom_key: tuple[Any, ...] | None = None  # (ptr, h, w, sections, digest)


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
    except Exception as e:
        logger.debug(f"api:_forced_configs_sig: {e}")
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
        except Exception as e:
            logger.debug(f"api:_norm: {e}")
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
    global _fg_last_song_ptr_key, _fg_last_song_key
    global _fg_last_great_ptr_key, _fg_last_great_key
    global _fg_last_fever_end_tables_key
    global _fg_song_upload_buf, _fg_great_upload_buf, _fg_forced_upload_buf, _fg_ftff_upload_buf
    global _fg_forced_counts_staging_tiers, _fg_forced_counts_staging_pool
    global _fg_genome_stats_buf, _fg_flat_work_buf
    global _fg_download_topk_base_buf, _fg_download_topk_keep_buf
    global _fg_frontier_upload_buf
    global _fg_genome_stats_upload_key, _fg_flat_work_key
    global _fg_forced_configs_upload_key
    global _fg_forced_resident_key, _fg_forced_resident_n_cfg_total, _fg_forced_resident_base_offset
    global _fg_pair_caps_state, _fg_pair_caps_default_buf, _fg_pair_caps_custom_key
    global _fg_last_ftff_key
    global _GPU_PROFILER_CACHE, _GPU_PROFILER_READY

    _fg_last_song_ptr_key = None
    _fg_last_song_key = None
    _fg_song_upload_buf = None
    _fg_last_great_ptr_key = None
    _fg_last_great_key = None
    _fg_last_fever_end_tables_key = None
    _fg_great_upload_buf = None
    _fg_forced_upload_buf = None
    _fg_ftff_upload_buf = None
    _fg_last_ftff_key = None
    _fg_forced_counts_staging_tiers = None
    _fg_forced_counts_staging_pool = None
    _fg_genome_stats_buf = None
    _fg_flat_work_buf = None
    _fg_download_topk_base_buf = None
    _fg_download_topk_keep_buf = None
    _fg_frontier_upload_buf = None
    _fg_genome_stats_upload_key = None
    _fg_flat_work_key = None
    _fg_forced_configs_upload_key = None
    _fg_forced_resident_key = None
    _fg_forced_resident_n_cfg_total = None
    _fg_forced_resident_base_offset = None
    _fg_pair_caps_state = None
    _fg_pair_caps_default_buf = None
    _fg_pair_caps_custom_key = None
    _GPU_PROFILER_CACHE = None
    _GPU_PROFILER_READY = False


def _get_forced_counts_staging_tiers() -> tuple[int, ...]:
    global _fg_forced_counts_staging_tiers
    if _fg_forced_counts_staging_tiers is not None:
        return _fg_forced_counts_staging_tiers

    raw = str(_ENV_GET("FG_FORCED_COUNTS_STAGING_TIERS", "") or "").strip()
    tiers: list[int] = []
    if raw:
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                tiers.append(int(tok))
            except Exception as e:
                logger.debug(f"api:_get_forced_counts_staging_tiers: {e}")
                continue

    if not tiers:
        tiers = list(_FG_FORCED_COUNTS_STAGING_TIERS_DEFAULT)

    # Normalize: unique, ascending, clamped to max rows.
    norm = sorted({int(x) for x in tiers if int(x) > 0})
    norm = [int(x) for x in norm if int(x) <= int(_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)]
    if not norm:
        norm = [int(_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)]
    if int(norm[-1]) != int(_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT):
        norm.append(int(_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT))

    _fg_forced_counts_staging_tiers = tuple(int(x) for x in norm)
    return _fg_forced_counts_staging_tiers


def _pick_forced_counts_staging_rows(n_cfg: int) -> int:
    n_cfg = int(n_cfg)
    for tier in _get_forced_counts_staging_tiers():
        if n_cfg <= int(tier):
            return int(tier)
    return int(_get_forced_counts_staging_tiers()[-1])


def _get_forced_counts_staging(rows: int) -> Any:
    global _fg_forced_counts_staging_pool
    rows = int(rows)
    if rows <= 0:
        rows = int(_FG_FORCED_COUNTS_STAGING_ROWS_DEFAULT)
    if _fg_forced_counts_staging_pool is None:
        _fg_forced_counts_staging_pool = {}
    staging = _fg_forced_counts_staging_pool.get(rows)
    if staging is None:
        staging = ti.ndarray(dtype=ti.i32, shape=(int(rows), fg_fields.FG_MAX_SECTIONS))
        _fg_forced_counts_staging_pool[int(rows)] = staging
    return staging


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


def fg_reset_global_best(n_genomes: int, *, session_slot: int = 0) -> None:
    """
    Reset global best fields before multi-group processing.

    Call this once at the start of a batch of FG groups, before the loop.
    All global best scores will be set to -1 (sentinel).

    Args:
        n_genomes: Number of genomes to reset
        session_slot: Song/session slot to reset (use the same slot as the FG solve calls).
    """
    fg_fields.ensure_ready_with_warmup()
    slot = int(session_slot)
    if slot < 0 or slot >= int(getattr(gem_fields, "MAX_SONG_SLOTS", 1) or 1):
        raise ValueError(f"session_slot out of range: {slot}")
    fg_kernels.fg_reset_global_best_kernel(int(slot), int(n_genomes))


def fg_download_global_best(
    n_genomes: int,
    *,
    session_slot: int = 0,
    topk: int | None = None,
    base_scores: np.ndarray | None = None,
    keep_mask: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """
    Download final global best results after all groups processed.

    Call this once at the end of multi-group processing to get the final results.

    Args:
        n_genomes: Number of genomes to download

    Args:
        session_slot: Song/session slot to download (use the same slot as the FG solve calls).
        topk: Optional top-K selection for reduced download. When provided with `base_scores`,
              returns only `keep_mask` rows plus up to `topk` high-score candidate rows.
        base_scores: Per-genome base score used for the candidate eligibility filter (final_score > base_score).
        keep_mask: Optional per-genome mask (1=force include). Useful for ensuring top-base entries are always downloaded.

    Returns:
        Dict with numpy arrays for all result fields (same format as return_raw=True).
        When `topk` is enabled, also includes `selected_indices` (genome indices into the global_best buffers).
    """
    # Avoid unconditional host sync in the hot path:
    # - `to_numpy()` already synchronizes when needed.
    # - keep explicit sync only when timing/trace/debug asks for it.
    _t0 = time.perf_counter()
    did_sync = bool(_FORCE_SYNC or _SYNC_FOR_TIMING or _FG_TRANSFER_TRACE)
    if did_sync:
        maybe_sync(
            sync_fn=ti.sync,
            force_sync=bool(_FORCE_SYNC or _FG_TRANSFER_TRACE),
            sync_for_timing=_SYNC_FOR_TIMING,
            for_timing=True,
        )
        _sync_sec = time.perf_counter() - _t0
    else:
        _sync_sec = 0.0
    n = int(n_genomes)
    slot = int(session_slot)
    if slot < 0 or slot >= int(getattr(gem_fields, "MAX_SONG_SLOTS", 1) or 1):
        raise ValueError(f"session_slot out of range: {slot}")

    # Optional reduced download path: select/pack only a small subset.
    if topk is not None and base_scores is not None:
        k = int(topk)
        base_np = np.asarray(base_scores, dtype=np.int32)
        if int(base_np.shape[0]) != n:
            raise ValueError(f"base_scores length mismatch: {int(base_np.shape[0])} != {n}")
        if not base_np.flags["C_CONTIGUOUS"]:
            base_np = np.ascontiguousarray(base_np, dtype=np.int32)

        if keep_mask is None:
            keep_np = np.zeros((n,), dtype=np.int32)
        else:
            keep_np = np.asarray(keep_mask, dtype=np.int32)
            if int(keep_np.shape[0]) != n:
                raise ValueError(f"keep_mask length mismatch: {int(keep_np.shape[0])} != {n}")
            if not keep_np.flags["C_CONTIGUOUS"]:
                keep_np = np.ascontiguousarray(keep_np, dtype=np.int32)

        # Upload selection inputs.
        #
        # Note: Taichi field shapes must match exactly for from_numpy(). We allocate the
        # fields at MAX_GENOMES, so we upload into a persistent padded buffer and only
        # the first `n` entries are read by the selection kernel.
        global _fg_download_topk_base_buf, _fg_download_topk_keep_buf
        try:
            max_g = int(getattr(fg_fields, "MAX_GENOMES", 0) or 0)
        except Exception as e:
            logger.debug(f"api:fg_download_global_best: {e}")
            max_g = 0
        if max_g <= 0:
            max_g = int(n)
        if _fg_download_topk_base_buf is None or int(_fg_download_topk_base_buf.shape[0]) != int(max_g):
            _fg_download_topk_base_buf = np.zeros((int(max_g),), dtype=np.int32)
        if _fg_download_topk_keep_buf is None or int(_fg_download_topk_keep_buf.shape[0]) != int(max_g):
            _fg_download_topk_keep_buf = np.zeros((int(max_g),), dtype=np.int32)

        _fg_download_topk_base_buf[:n] = base_np[:n]
        _fg_download_topk_keep_buf[:n] = keep_np[:n]

        fg_fields.fg_input_base_score.from_numpy(_fg_download_topk_base_buf)
        fg_fields.fg_keep_mask.from_numpy(_fg_download_topk_keep_buf)

        fg_kernels.fg_select_global_best_topk_kernel(int(slot), n, int(k))
        try:
            n_pack = int(getattr(fg_fields, "FG_DOWNLOAD_TOPK_MAX", 0) or 0)
        except Exception as e:
            logger.debug(f"api:fg_download_global_best: {e}")
            n_pack = 0
        if n_pack <= 0:
            n_pack = 256

        # Pack a fixed number of rows to avoid extra sync/scalar reads.
        fg_kernels.fg_pack_selected_global_best_kernel(int(slot), int(n_pack))
        _t1 = time.perf_counter()
        sel_packed_all = fg_fields.fg_selected_packed.to_numpy()
        _dl_sec = time.perf_counter() - _t1
        _record_kernel_wall("global_best_sync", _sync_sec, genome_count=n)
        _bytes_sel = int(getattr(sel_packed_all, "nbytes", 0) or 0)
        _record_download("global_best_topk_packed", _dl_sec, _bytes_sel)
        if _FG_TRANSFER_TRACE:
            try:
                print(
                    f"[FG][XFER] global_best_topk: sync={_sync_sec * 1000:.2f}ms "
                    f"download={_dl_sec * 1000:.2f}ms rows={int(n_pack)} bytes={int(_bytes_sel)}"
                )
            except Exception as e:
                logger.debug(f"api:fg_download_global_best: {e}")

        # Derive actual selected length from the packed idx column (-1 sentinel).
        idx_all = sel_packed_all[:, 0]
        try:
            neg = np.nonzero(np.asarray(idx_all) < 0)[0]
            n_sel = int(neg[0]) if int(getattr(neg, "shape", (0,))[0] or 0) > 0 else int(n_pack)
        except Exception as e:
            logger.debug(f"api:fg_download_global_best: {e}")
            n_sel = int(n_pack)

        sel_packed = sel_packed_all[: int(n_sel), :]
        sel_idx = sel_packed[:, 0]
        cfg_counts = sel_packed[:, 12 : 12 + int(fg_fields.FG_MAX_SECTIONS)]
        return {
            "selected_indices": sel_idx,
            "final_score": sel_packed[:, 1],
            "base_score": sel_packed[:, 2],
            "cfg_idx": sel_packed[:, 3],
            "FT": sel_packed[:, 4],
            "FF": sel_packed[:, 5],
            "g_pp": sel_packed[:, 6],
            "g_cm": sel_packed[:, 7],
            "g_fm": sel_packed[:, 8],
            "g_ov": sel_packed[:, 9],
            "score_penalty": sel_packed[:, 10],
            "fill_penalty": sel_packed[:, 11],
            "cfg_counts": cfg_counts,
        }

    # Default: download all rows
    fg_kernels.fg_pack_global_best_kernel(int(slot), n)
    _t1 = time.perf_counter()
    packed, transfer_bytes, dl_mode = _fg_download_global_best_packed_prefix(int(n))
    _dl_sec = time.perf_counter() - _t1
    _record_kernel_wall("global_best_sync", _sync_sec, genome_count=n)
    _record_download("global_best_packed", _dl_sec, int(transfer_bytes))
    if _FG_TRANSFER_TRACE:
        try:
            print(
                f"[FG][XFER] global_best({dl_mode}): sync={_sync_sec * 1000:.2f}ms download={_dl_sec * 1000:.2f}ms bytes={int(transfer_bytes)}"
            )
        except Exception as e:
            logger.debug(f"api:fg_download_global_best: {e}")
    cfg_counts = packed[:, 11 : 11 + int(fg_fields.FG_MAX_SECTIONS)]
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
        "cfg_counts": cfg_counts,
    }


def fg_pack_global_best_topk_to_batch(
    n_genomes: int,
    *,
    session_slot: int,
    topk: int,
    base_scores: np.ndarray,
    keep_mask: np.ndarray | None,
    batch_idx: int,
    upload_selection_inputs: bool = True,
) -> None:
    """
    Pack a top-K subset of `fg_global_best_*` into `fg_selected_packed_batch[batch_idx]`.

    This is the "download-later" primitive used by the GPU executor's bundled FG path:
      - solve payload N -> update global_best
      - pack payload N -> staging batch slice
      - ... repeat ...
      - single `to_numpy()` download at the end of the bundle
    """
    fg_fields.ensure_ready_with_warmup()

    n = int(n_genomes)
    slot = int(session_slot)
    k = int(topk)
    bidx = int(batch_idx)
    if n <= 0:
        return

    if upload_selection_inputs:
        base_np = np.asarray(base_scores, dtype=np.int32)
        if int(base_np.shape[0]) != n:
            raise ValueError(f"base_scores length mismatch: {int(base_np.shape[0])} != {n}")
        if not base_np.flags["C_CONTIGUOUS"]:
            base_np = np.ascontiguousarray(base_np, dtype=np.int32)

        if keep_mask is None:
            keep_np = np.zeros((n,), dtype=np.int32)
        else:
            keep_np = np.asarray(keep_mask, dtype=np.int32)
            if int(keep_np.shape[0]) != n:
                raise ValueError(f"keep_mask length mismatch: {int(keep_np.shape[0])} != {n}")
            if not keep_np.flags["C_CONTIGUOUS"]:
                keep_np = np.ascontiguousarray(keep_np, dtype=np.int32)

        global _fg_download_topk_base_buf, _fg_download_topk_keep_buf
        try:
            max_g = int(getattr(fg_fields, "MAX_GENOMES", 0) or 0)
        except Exception as e:
            logger.debug(f"api:fg_pack_global_best_topk_to_batch: {e}")
            max_g = 0
        if max_g <= 0:
            max_g = int(n)

        if _fg_download_topk_base_buf is None or int(_fg_download_topk_base_buf.shape[0]) != int(max_g):
            _fg_download_topk_base_buf = np.zeros((int(max_g),), dtype=np.int32)
        if _fg_download_topk_keep_buf is None or int(_fg_download_topk_keep_buf.shape[0]) != int(max_g):
            _fg_download_topk_keep_buf = np.zeros((int(max_g),), dtype=np.int32)

        _fg_download_topk_base_buf[:n] = base_np[:n]
        _fg_download_topk_keep_buf[:n] = keep_np[:n]
        fg_fields.fg_input_base_score.from_numpy(_fg_download_topk_base_buf)
        fg_fields.fg_keep_mask.from_numpy(_fg_download_topk_keep_buf)

    fg_kernels.fg_select_global_best_topk_kernel(int(slot), int(n), int(k))
    n_pack = int(getattr(fg_fields, "FG_DOWNLOAD_TOPK_MAX", 256) or 256)
    fg_kernels.fg_pack_selected_global_best_batch_kernel(int(slot), int(n_pack), int(bidx))


def fg_select_signature_frontier_indices(
    *,
    base_scores: np.ndarray,
    proxy_scores: np.ndarray,
    priorities: np.ndarray,
    force_keep: np.ndarray,
    center_bucket_ft: np.ndarray,
    center_bucket_ff: np.ndarray,
    timing_bucket: np.ndarray,
    limit: int,
    top_base_keep: int,
) -> np.ndarray:
    """
    Select a bounded FG signature frontier on GPU from per-signature metadata.

    Inputs are parallel arrays over signatures in their original order. The result
    is a compact array of selected source indices, preserving the frontier lane
    ordering used by the host heuristic.
    """
    fg_fields.ensure_ready_with_warmup()

    base_np = np.asarray(base_scores, dtype=np.int32)
    proxy_np = np.asarray(proxy_scores, dtype=np.int32)
    priority_np = np.asarray(priorities, dtype=np.int32)
    keep_np = np.asarray(force_keep, dtype=np.int32)
    center_ft_np = np.asarray(center_bucket_ft, dtype=np.int32)
    center_ff_np = np.asarray(center_bucket_ff, dtype=np.int32)
    timing_np = np.asarray(timing_bucket, dtype=np.int32)

    n = int(base_np.shape[0])
    if any(
        int(arr.shape[0]) != int(n) for arr in (proxy_np, priority_np, keep_np, center_ft_np, center_ff_np, timing_np)
    ):
        raise ValueError("FG signature frontier metadata arrays must have matching length")

    cap = int(getattr(fg_fields, "FG_SIGNATURE_FRONTIER_MAX", 0) or 0)
    if cap <= 0:
        cap = int(n)
    if n > cap:
        raise ValueError(f"FG signature frontier exceeds device cap: {n} > {cap}")
    if n <= 0:
        return np.zeros((0,), dtype=np.int32)

    _fg_upload_signature_frontier_inputs(
        cap=int(cap),
        n=int(n),
        base_np=base_np,
        proxy_np=proxy_np,
        priority_np=priority_np,
        keep_np=keep_np,
        center_ft_np=center_ft_np,
        center_ff_np=center_ff_np,
        timing_np=timing_np,
    )

    fg_kernels.fg_select_signature_frontier_kernel(int(n), int(limit), int(top_base_keep))

    _t0 = time.perf_counter()
    did_sync = bool(_FORCE_SYNC or _SYNC_FOR_TIMING or _FG_TRANSFER_TRACE)
    if did_sync:
        maybe_sync(
            sync_fn=ti.sync,
            force_sync=bool(_FORCE_SYNC or _FG_TRANSFER_TRACE),
            sync_for_timing=_SYNC_FOR_TIMING,
            for_timing=True,
        )
        _sync_sec = time.perf_counter() - _t0
    else:
        _sync_sec = 0.0

    _t1 = time.perf_counter()
    selected_all = fg_fields.fg_frontier_selected_indices.to_numpy()
    _dl_sec = time.perf_counter() - _t1
    _record_kernel_wall("signature_frontier_sync", _sync_sec, genome_count=n)
    _record_download("signature_frontier_indices", _dl_sec, int(getattr(selected_all, "nbytes", 0) or 0))

    try:
        neg = np.nonzero(np.asarray(selected_all) < 0)[0]
        n_sel = int(neg[0]) if int(getattr(neg, "shape", (0,))[0] or 0) > 0 else min(int(limit), int(n))
    except Exception as e:
        logger.debug(f"api:fg_select_signature_frontier_indices: {e}")
        n_sel = min(int(limit), int(n))
    return np.asarray(selected_all[: int(n_sel)], dtype=np.int32)


def _ensure_frontier_upload_buf(cap: int) -> dict[str, np.ndarray]:
    global _fg_frontier_upload_buf
    existing_base = None if _fg_frontier_upload_buf is None else _fg_frontier_upload_buf.get("base")
    if existing_base is None or int(existing_base.shape[0]) != int(cap):
        _fg_frontier_upload_buf = {
            "base": np.zeros((int(cap),), dtype=np.int32),
            "proxy": np.zeros((int(cap),), dtype=np.int32),
            "priority": np.zeros((int(cap),), dtype=np.int32),
            "keep": np.zeros((int(cap),), dtype=np.int32),
            "center_ft": np.zeros((int(cap),), dtype=np.int32),
            "center_ff": np.zeros((int(cap),), dtype=np.int32),
            "timing": np.zeros((int(cap),), dtype=np.int32),
        }
    return _fg_frontier_upload_buf


def _fg_upload_signature_frontier_inputs(
    *,
    cap: int,
    n: int,
    base_np: np.ndarray,
    proxy_np: np.ndarray,
    priority_np: np.ndarray,
    keep_np: np.ndarray,
    center_ft_np: np.ndarray,
    center_ff_np: np.ndarray,
    timing_np: np.ndarray,
) -> None:
    buf = _ensure_frontier_upload_buf(int(cap))
    for key in ("base", "proxy", "priority", "keep", "center_ft", "center_ff", "timing"):
        buf[key].fill(0)

    buf["base"][:n] = np.ascontiguousarray(base_np)
    buf["proxy"][:n] = np.ascontiguousarray(proxy_np)
    buf["priority"][:n] = np.ascontiguousarray(priority_np)
    buf["keep"][:n] = np.ascontiguousarray(keep_np)
    buf["center_ft"][:n] = np.ascontiguousarray(center_ft_np)
    buf["center_ff"][:n] = np.ascontiguousarray(center_ff_np)
    buf["timing"][:n] = np.ascontiguousarray(timing_np)

    fg_fields.fg_frontier_base_score.from_numpy(buf["base"])
    fg_fields.fg_frontier_proxy_score.from_numpy(buf["proxy"])
    fg_fields.fg_frontier_priority.from_numpy(buf["priority"])
    fg_fields.fg_frontier_force_keep.from_numpy(buf["keep"])
    fg_fields.fg_frontier_center_bucket_ft.from_numpy(buf["center_ft"])
    fg_fields.fg_frontier_center_bucket_ff.from_numpy(buf["center_ff"])
    fg_fields.fg_frontier_timing_bucket.from_numpy(buf["timing"])


def fg_select_signature_frontier_batch(payloads: list[dict[str, np.ndarray | int]]) -> list[np.ndarray]:
    """
    Select multiple FG signature frontiers with a single device download.

    This keeps the frontier-selection step GPU-side while avoiding a per-group
    sync/download boundary in the FG hot path.
    """
    fg_fields.ensure_ready_with_warmup()
    if not payloads:
        return []

    cap = int(getattr(fg_fields, "FG_SIGNATURE_FRONTIER_MAX", 0) or 0)
    if cap <= 0:
        raise ValueError("FG_SIGNATURE_FRONTIER_MAX is not configured")
    batch_cap = int(getattr(fg_fields, "FG_SIGNATURE_FRONTIER_BATCH_MAX", 0) or 0)
    if batch_cap <= 0:
        batch_cap = 1

    results: list[np.ndarray] = []
    for chunk_start in range(0, len(payloads), int(batch_cap)):
        chunk = payloads[chunk_start : chunk_start + int(batch_cap)]
        for batch_idx, payload in enumerate(chunk):
            base_np = np.asarray(payload["base_scores"], dtype=np.int32)
            proxy_np = np.asarray(payload["proxy_scores"], dtype=np.int32)
            priority_np = np.asarray(payload["priorities"], dtype=np.int32)
            keep_np = np.asarray(payload["force_keep"], dtype=np.int32)
            center_ft_np = np.asarray(payload["center_bucket_ft"], dtype=np.int32)
            center_ff_np = np.asarray(payload["center_bucket_ff"], dtype=np.int32)
            timing_np = np.asarray(payload["timing_bucket"], dtype=np.int32)
            n = int(base_np.shape[0])
            if any(
                int(arr.shape[0]) != int(n)
                for arr in (proxy_np, priority_np, keep_np, center_ft_np, center_ff_np, timing_np)
            ):
                raise ValueError("FG signature frontier batch payload arrays must have matching length")
            if n > int(cap):
                raise ValueError(f"FG signature frontier exceeds device cap: {n} > {cap}")

            _fg_upload_signature_frontier_inputs(
                cap=int(cap),
                n=int(n),
                base_np=base_np,
                proxy_np=proxy_np,
                priority_np=priority_np,
                keep_np=keep_np,
                center_ft_np=center_ft_np,
                center_ff_np=center_ff_np,
                timing_np=timing_np,
            )
            fg_kernels.fg_select_signature_frontier_kernel(
                int(n),
                int(payload["limit"]),
                int(payload["top_base_keep"]),
            )
            fg_kernels.fg_copy_signature_frontier_selected_to_batch_kernel(int(batch_idx))

        _t0 = time.perf_counter()
        did_sync = bool(_FORCE_SYNC or _SYNC_FOR_TIMING or _FG_TRANSFER_TRACE)
        if did_sync:
            maybe_sync(
                sync_fn=ti.sync,
                force_sync=bool(_FORCE_SYNC or _FG_TRANSFER_TRACE),
                sync_for_timing=_SYNC_FOR_TIMING,
                for_timing=True,
            )
            _sync_sec = time.perf_counter() - _t0
        else:
            _sync_sec = 0.0

        _t1 = time.perf_counter()
        selected_batch_all = fg_fields.fg_frontier_selected_indices_batch.to_numpy()
        count_batch_all = fg_fields.fg_frontier_selected_count_batch.to_numpy()
        _dl_sec = time.perf_counter() - _t1
        total_n = 0
        try:
            total_n = sum(int(np.asarray(payload["base_scores"]).shape[0]) for payload in chunk)
        except Exception as e:
            logger.debug(f"api:fg_select_signature_frontier_batch: {e}")
            total_n = 0
        _record_kernel_wall("signature_frontier_batch_sync", _sync_sec, genome_count=total_n)
        _record_download(
            "signature_frontier_batch_indices",
            _dl_sec,
            int(getattr(selected_batch_all, "nbytes", 0) or 0) + int(getattr(count_batch_all, "nbytes", 0) or 0),
        )

        for batch_idx, payload in enumerate(chunk):
            row = np.asarray(selected_batch_all[int(batch_idx)], dtype=np.int32)
            try:
                n_sel = max(0, min(int(count_batch_all[int(batch_idx)]), int(payload["limit"])))
            except Exception as e:
                logger.debug(f"api:fg_select_signature_frontier_batch: {e}")
                try:
                    neg = np.nonzero(row < 0)[0]
                    n_sel = int(neg[0]) if int(getattr(neg, "shape", (0,))[0] or 0) > 0 else int(payload["limit"])
                except Exception as e:
                    logger.debug(f"api:fg_select_signature_frontier_batch: {e}")
                    n_sel = int(payload["limit"])
            results.append(np.asarray(row[: int(n_sel)], dtype=np.int32))

    return results


def fg_download_packed_topk_batch(n_payloads: int) -> list[dict[str, np.ndarray]]:
    """
    Download `fg_selected_packed_batch` (previously filled by `fg_pack_global_best_topk_to_batch`).
    """
    fg_fields.ensure_ready_with_warmup()
    n_payloads = int(n_payloads)
    if n_payloads <= 0:
        return []
    try:
        max_batch = int(getattr(fg_fields, "FG_DOWNLOAD_BATCH_MAX", 0) or 0)
    except Exception as e:
        logger.debug(f"api:fg_download_packed_topk_batch: {e}")
        max_batch = 0
    if max_batch <= 0:
        max_batch = 1
    if n_payloads > int(max_batch):
        raise ValueError(f"n_payloads exceeds FG_DOWNLOAD_BATCH_MAX: {n_payloads} > {max_batch}")

    _t0 = time.perf_counter()
    did_sync = bool(_FORCE_SYNC or _SYNC_FOR_TIMING or _FG_TRANSFER_TRACE)
    if did_sync:
        maybe_sync(
            sync_fn=ti.sync,
            force_sync=bool(_FORCE_SYNC or _FG_TRANSFER_TRACE),
            sync_for_timing=_SYNC_FOR_TIMING,
            for_timing=True,
        )
        _sync_sec = time.perf_counter() - _t0
    else:
        _sync_sec = 0.0

    _t1 = time.perf_counter()
    sel_packed_all = None
    sel_packed_transfer_bytes = 0
    used_staging = "full"
    try:
        staging_candidates = [
            ("staging_1", getattr(fg_fields, "fg_selected_packed_batch_download_staging_1", None)),
            ("staging_8", getattr(fg_fields, "fg_selected_packed_batch_download_staging_8", None)),
            ("staging_32", getattr(fg_fields, "fg_selected_packed_batch_download_staging_32", None)),
            ("staging_128", getattr(fg_fields, "fg_selected_packed_batch_download_staging_128", None)),
        ]
        best = None
        for name, fld in staging_candidates:
            if fld is None:
                continue
            try:
                cap = int(getattr(fld, "shape", (0,))[0] or 0)
            except Exception as e:
                logger.debug(f"api:fg_download_packed_topk_batch: {e}")
                cap = 0
            if cap > 0 and int(n_payloads) <= int(cap):
                best = (name, fld)
                break

        if best is not None:
            used_staging, fld = best
            fg_kernels.fg_copy_selected_packed_batch_to_download_staging_kernel(fld, int(n_payloads))
            sel_packed_full = fld.to_numpy()
            sel_packed_transfer_bytes = int(getattr(sel_packed_full, "nbytes", 0) or 0)
            sel_packed_all = sel_packed_full[: int(n_payloads), :, :]
        else:
            sel_packed_full = fg_fields.fg_selected_packed_batch.to_numpy()
            sel_packed_transfer_bytes = int(getattr(sel_packed_full, "nbytes", 0) or 0)
            sel_packed_all = sel_packed_full[: int(n_payloads), :, :]
    except Exception as e:
        logger.debug(f"api:fg_download_packed_topk_batch: {e}")
        sel_packed_full = fg_fields.fg_selected_packed_batch.to_numpy()
        sel_packed_transfer_bytes = int(getattr(sel_packed_full, "nbytes", 0) or 0)
        sel_packed_all = sel_packed_full[: int(n_payloads), :, :]
    _dl_sec = time.perf_counter() - _t1

    _record_kernel_wall("packed_topk_batch_sync", _sync_sec)
    _record_download("packed_topk_batch", _dl_sec, int(sel_packed_transfer_bytes))
    if _FG_TRANSFER_TRACE:
        try:
            print(
                f"[FG][XFER] packed_topk_batch: sync={_sync_sec * 1000:.2f}ms download={_dl_sec * 1000:.2f}ms "
                f"payloads={n_payloads} bytes={int(sel_packed_transfer_bytes)} staging={used_staging}"
            )
        except Exception as e:
            logger.debug(f"api:fg_download_packed_topk_batch: {e}")

    n_pack = int(getattr(fg_fields, "FG_DOWNLOAD_TOPK_MAX", 256) or 256)
    out: list[dict[str, np.ndarray]] = []
    for batch_idx in range(int(n_payloads)):
        view_all = sel_packed_all[int(batch_idx), : int(n_pack), :]
        idx_all = view_all[:, 0]
        try:
            neg = np.nonzero(np.asarray(idx_all) < 0)[0]
            n_sel = int(neg[0]) if int(getattr(neg, "shape", (0,))[0] or 0) > 0 else int(n_pack)
        except Exception as e:
            logger.debug(f"api:fg_download_packed_topk_batch: {e}")
            n_sel = int(n_pack)
        n_sel = max(0, min(int(n_sel), int(n_pack)))
        sel_packed = view_all[: int(n_sel), :]
        sel_idx = sel_packed[:, 0]
        cfg_counts = sel_packed[:, 12 : 12 + int(fg_fields.FG_MAX_SECTIONS)]
        out.append(
            {
                "selected_indices": sel_idx,
                "final_score": sel_packed[:, 1],
                "base_score": sel_packed[:, 2],
                "cfg_idx": sel_packed[:, 3],
                "FT": sel_packed[:, 4],
                "FF": sel_packed[:, 5],
                "g_pp": sel_packed[:, 6],
                "g_cm": sel_packed[:, 7],
                "g_fm": sel_packed[:, 8],
                "g_ov": sel_packed[:, 9],
                "score_penalty": sel_packed[:, 10],
                "fill_penalty": sel_packed[:, 11],
                "cfg_counts": cfg_counts,
            }
        )
    return out


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
        _t0 = time.perf_counter()
        fg_fields.fg_pair_caps.from_numpy(_fg_pair_caps_default_buf)
        _dt = time.perf_counter() - _t0
        _record_upload("pair_caps_default", _dt, _bytes_of_array(_fg_pair_caps_default_buf))
        _fg_pair_caps_state = "default"
        _fg_pair_caps_custom_key = None
        return

    arr = np.asarray(pair_caps_grid, dtype=np.int32)
    if arr.shape != expected_shape:
        raise ValueError(f"pair_caps_grid must be shape {expected_shape}, got {arr.shape}")
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr, dtype=np.int32)
    try:
        ptr = int(arr.__array_interface__["data"][0])
    except Exception as e:
        logger.debug(f"api:_ensure_pair_caps_uploaded: {e}")
        ptr = 0
    ptr_key = (ptr, int(arr.shape[0]), int(arr.shape[1]), int(arr.shape[2]))
    prev = _fg_pair_caps_custom_key if _fg_pair_caps_state == "custom" else None
    if prev is not None and len(prev) >= 4:
        try:
            if (
                int(prev[0]) == int(ptr_key[0])
                and int(prev[1]) == int(ptr_key[1])
                and int(prev[2]) == int(ptr_key[2])
                and int(prev[3]) == int(ptr_key[3])
            ):
                return
        except Exception as e:
            logger.debug(f"api:_ensure_pair_caps_uploaded: {e}")

    # Stable content key: avoid redundant re-uploads when pair_caps_grid is rebuilt (new pointer) with identical values.
    digest = None
    if prev is not None and len(prev) >= 5:
        try:
            prev_digest = prev[4]
        except Exception as e:
            logger.debug(f"api:_ensure_pair_caps_uploaded: {e}")
            prev_digest = None
        if prev_digest is not None:
            try:
                h = hashlib.blake2b(digest_size=12)
                h.update(memoryview(arr).cast("B"))
                digest = h.digest()
                if digest == prev_digest:
                    _fg_pair_caps_custom_key = (ptr_key[0], ptr_key[1], ptr_key[2], ptr_key[3], digest)
                    return
            except Exception as e:
                logger.debug(f"api:_ensure_pair_caps_uploaded: {e}")
                digest = None
    _t0 = time.perf_counter()
    fg_fields.fg_pair_caps.from_numpy(arr)
    _dt = time.perf_counter() - _t0
    _record_upload("pair_caps_custom", _dt, _bytes_of_array(arr))
    _fg_pair_caps_state = "custom"
    if digest is None:
        try:
            h = hashlib.blake2b(digest_size=12)
            h.update(memoryview(arr).cast("B"))
            digest = h.digest()
        except Exception as e:
            logger.debug(f"api:_ensure_pair_caps_uploaded: {e}")
            digest = None
    _fg_pair_caps_custom_key = (ptr_key[0], ptr_key[1], ptr_key[2], ptr_key[3], digest)


def _ftff_pairs_sig(ftff_pairs: Any, n: int) -> tuple:
    """
    Cheap, robust-ish signature for an FT/FF pair list to avoid redundant uploads.

    We intentionally avoid hashing the full contents (could be large and would add CPU cost).
    The FG pipeline frequently reuses the same FT/FF windows across tasks/groups, especially
    when search radius and centers are stable. Skipping `from_numpy()` avoids a host->device
    transfer and an implicit sync on some backends.
    """
    try:
        n = int(n)
    except Exception as e:
        logger.debug(f"api:_ftff_pairs_sig: {e}")
        n = 0
    if n <= 0:
        return (0,)

    # Numpy fast path: stable hash of the active (n,2) prefix.
    try:
        if isinstance(ftff_pairs, np.ndarray):
            arr = np.asarray(ftff_pairs, dtype=np.int32)
            if arr.ndim == 2 and arr.shape[0] >= n and arr.shape[1] >= 2:
                view = arr[:n, :2]
                if not view.flags["C_CONTIGUOUS"]:
                    view = np.ascontiguousarray(view, dtype=np.int32)
                h = hashlib.blake2b(digest_size=12)
                h.update(memoryview(view).cast("B"))
                return ("np_hash", int(n), h.digest())
    except Exception as e:
        logger.debug(f"api:_ftff_pairs_sig: {e}")

    # Generic sequence path: sample first/mid/last.
    try:
        first_ft, first_ff = ftff_pairs[0]
        last_ft, last_ff = ftff_pairs[n - 1]
        mid_ft, mid_ff = ftff_pairs[n // 2] if n > 1 else (first_ft, first_ff)
        return (
            "seq",
            n,
            (int(first_ft), int(first_ff)),
            (int(mid_ft), int(mid_ff)),
            (int(last_ft), int(last_ff)),
        )
    except Exception as e:
        # Fallback: only length.
        logger.debug(f"api:_ftff_pairs_sig: {e}")
        return ("seq", n)


def _get_genome_stats_buf() -> np.ndarray:
    """Get or allocate a persistent buffer for genome stats (N, 7)."""
    global _fg_genome_stats_buf
    if _fg_genome_stats_buf is None:
        # [pp, cm, fm, p, s, ft, ff]
        _fg_genome_stats_buf = np.zeros((gem_fields.MAX_GENOMES, 7), dtype=np.int16)
    return _fg_genome_stats_buf


def _fg_upload_song_timestamps(timestamps_np: np.ndarray) -> int:
    """Upload song timestamps to GPU (cached by content, with a pointer fast-path)."""
    global _fg_last_song_ptr_key, _fg_last_song_key, _fg_song_upload_buf

    ts = np.asarray(timestamps_np, dtype=np.float32)
    if not ts.flags["C_CONTIGUOUS"]:
        ts = np.ascontiguousarray(ts, dtype=np.float32)

    n = int(len(ts))
    if n <= 0:
        return 0
    if n > fg_fields.FG_MAX_SONG_NOTES:
        raise ValueError(f"Song too long for FG GPU timestamps: {n} > {fg_fields.FG_MAX_SONG_NOTES}")

    # Fast path: cache by backing pointer + sampled points (O(1)).
    try:
        ptr = int(ts.__array_interface__["data"][0])
    except Exception as e:
        logger.debug(f"api:_fg_upload_song_timestamps: {e}")
        ptr = 0
    first = float(ts[0])
    last = float(ts[-1])
    mid = float(ts[n // 2]) if n > 1 else first
    q1 = float(ts[n // 4]) if n > 3 else mid
    q3 = float(ts[(3 * n) // 4]) if n > 3 else mid
    ptr_key = (ptr, n, first, last, mid, q1, q3)
    if _fg_last_song_ptr_key == ptr_key:
        return n

    # Stable content-hash fallback: allow reuse even when host pointer changes (e.g., IPC/unpickle).
    try:
        # Prefer SHA1 here: on this repo's target CPUs, OpenSSL's SHA1 is significantly faster than blake2b
        # for large buffers (timestamps can be 100k-200k floats).
        digest = hashlib.sha1(memoryview(ts).cast("B")).digest()[:12]
        content_key = (int(n), digest)
    except Exception as e:
        logger.debug(f"api:_fg_upload_song_timestamps: {e}")
        content_key = None

    if content_key is not None and _fg_last_song_key == content_key:
        _fg_last_song_ptr_key = ptr_key
        return n

    _t0 = time.perf_counter()
    fg_kernels.fg_upload_song_timestamps_prefix_kernel(int(n), ts)
    _dt = time.perf_counter() - _t0
    _record_upload("song_timestamps", _dt, _bytes_of_array(ts))
    _fg_last_song_ptr_key = ptr_key
    _fg_last_song_key = content_key
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


def _ensure_fever_end_tables(total_notes: int, last_note_time: float) -> None:
    """
    Ensure fever-end lookup tables are computed for the currently uploaded song buffers.

    Stage 1 kernels use these tables to avoid per-section binary searches, which is a major
    throughput win for large config sweeps.
    """
    global _fg_last_fever_end_tables_key
    key = (_fg_last_song_key, _fg_last_great_key, float(last_note_time))
    if _fg_last_fever_end_tables_key == key:
        return
    fg_kernels.fg_precompute_fever_end_idx_tables_kernel(int(total_notes), float(last_note_time))
    _fg_last_fever_end_tables_key = key


def _fg_upload_great_candidate_timestamps(candidate_np: np.ndarray, n: int) -> None:
    """Upload great-candidate timestamps to GPU (cached by content, with a pointer fast-path)."""
    global _fg_last_great_ptr_key, _fg_last_great_key, _fg_great_upload_buf

    if n <= 0:
        return
    candidate = np.asarray(candidate_np, dtype=np.float32)
    if not candidate.flags["C_CONTIGUOUS"]:
        candidate = np.ascontiguousarray(candidate, dtype=np.float32)
    if int(len(candidate)) != n:
        raise ValueError(f"great_candidate_timestamps length mismatch: {len(candidate)} != {n}")

    try:
        ptr = int(candidate.__array_interface__["data"][0])
    except Exception as e:
        logger.debug(f"api:_fg_upload_great_candidate_timestamps: {e}")
        ptr = 0
    first = float(candidate[0])
    last = float(candidate[-1])
    mid = float(candidate[n // 2]) if n > 1 else first
    q1 = float(candidate[n // 4]) if n > 3 else mid
    q3 = float(candidate[(3 * n) // 4]) if n > 3 else mid
    ptr_key = (ptr, n, first, last, mid, q1, q3)
    if _fg_last_great_ptr_key == ptr_key:
        _fg_use_great_candidate_field()
        return

    try:
        digest = hashlib.sha1(memoryview(candidate).cast("B")).digest()[:12]
        content_key = (int(n), digest)
    except Exception as e:
        logger.debug(f"api:_fg_upload_great_candidate_timestamps: {e}")
        content_key = None

    if content_key is not None and _fg_last_great_key == content_key:
        _fg_last_great_ptr_key = ptr_key
        _fg_use_great_candidate_field()
        return

    _t0 = time.perf_counter()
    fg_kernels.fg_upload_great_candidate_timestamps_prefix_kernel(int(n), candidate)
    _dt = time.perf_counter() - _t0
    _record_upload("great_candidate_timestamps", _dt, _bytes_of_array(candidate))
    _fg_last_great_ptr_key = ptr_key
    _fg_last_great_key = content_key
    _fg_use_great_candidate_field()


def _fg_download_packed_prefix(
    n_genomes: int,
    *,
    source_field: Any,
    staging_candidates: list[tuple[str, Any]],
    copy_kernel: Any,
    packed_cols: int,
) -> tuple[np.ndarray, int, str]:
    """Download an active packed-result prefix through the smallest staging field."""

    n = int(n_genomes)
    if n <= 0:
        return np.empty((0, int(packed_cols)), dtype=np.int32), 0, "empty"

    mode = "full"
    out = None
    try:
        full_shape = getattr(source_field, "shape", None)
        full_elems = int(full_shape[0]) * int(full_shape[1]) if full_shape is not None else 0
        best = None
        for name, fld in staging_candidates:
            if fld is None:
                continue
            shape = getattr(fld, "shape", None)
            if not shape or len(shape) < 2:
                continue
            if n <= int(shape[0]):
                elems = int(shape[0]) * int(shape[1])
                if best is None or elems < best[0]:
                    best = (elems, name, fld)

        if best is not None and full_elems > int(best[0]):
            _elems, name, fld = best
            mode = str(name)
            copy_kernel(fld, int(n))
            out = fld.to_numpy()
    except Exception as e:
        logger.debug(f"api:_fg_download_packed_prefix: {e}")
        out = None

    if out is None:
        out = source_field.to_numpy()

    try:
        transfer_bytes = int(getattr(out, "nbytes", 0) or 0)
    except Exception as e:
        logger.debug(f"api:_fg_download_packed_prefix: {e}")
        transfer_bytes = 0

    view = out[:n, :]
    if view.dtype == np.int32 and view.flags["C_CONTIGUOUS"]:
        return view, transfer_bytes, mode
    return np.ascontiguousarray(view, dtype=np.int32), transfer_bytes, mode


def _fg_download_best_packed_prefix(n_genomes: int) -> tuple[np.ndarray, int, str]:
    """
    Download the active prefix of `fg_best_packed`, using bounded staging when available.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES buffer can dominate when n_genomes is small.

    Returns:
        (view, transfer_bytes, mode)
    """
    return _fg_download_packed_prefix(
        int(n_genomes),
        source_field=fg_fields.fg_best_packed,
        staging_candidates=[
            ("staging_256", getattr(fg_fields, "fg_best_packed_download_staging_256", None)),
            ("staging_1024", getattr(fg_fields, "fg_best_packed_download_staging_1024", None)),
        ],
        copy_kernel=fg_kernels.fg_copy_best_packed_to_download_staging_kernel,
        packed_cols=int(getattr(fg_fields, "FG_PACKED_COLS", 0) or 0),
    )


def _fg_download_global_best_packed_prefix(n_genomes: int) -> tuple[np.ndarray, int, str]:
    """
    Download the active prefix of `fg_global_best_packed`, using bounded staging when available.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES buffer can dominate when n_genomes is small.

    Returns:
        (view, transfer_bytes, mode)
    """
    return _fg_download_packed_prefix(
        int(n_genomes),
        source_field=fg_fields.fg_global_best_packed,
        staging_candidates=[
            ("staging_256", getattr(fg_fields, "fg_global_best_packed_download_staging_256", None)),
            ("staging_1024", getattr(fg_fields, "fg_global_best_packed_download_staging_1024", None)),
        ],
        copy_kernel=fg_kernels.fg_copy_global_best_packed_to_download_staging_kernel,
        packed_cols=int(getattr(fg_fields, "FG_PACKED_COLS", 0) or 0),
    )


__all__ = [name for name in globals() if not name.startswith("__")]
