"""
API Timeline - GPU timeline precomputation and grid upload.

This module provides GPU-accelerated timeline precomputation:
- precompute_timeline_gpu: Compute all 161×161 fever timelines on GPU
"""

import time
import os
import hashlib
import threading
from collections import OrderedDict
from pathlib import Path
import numpy as np
import taichi as ti

from gear_optimizer.core.env_config import env_flag
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.utils import timing_envelope_timing_context
from gear_optimizer.solver.gpu_profiler import get_gpu_profiler
from gear_optimizer.solver.timeline_exact_frontier import (
    TimelineFrontierGridPayload,
    build_timeline_frontier_grid_payload,
)
from ..fields import (
    MAX_SONG_SLOTS,
)
from .. import fields
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _maybe_sync, _SYNC_FOR_TIMING, _FORCE_SYNC, _ref_arrays_sig

_profiler = get_gpu_profiler()

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


@ti.kernel
def _upload_song_timestamps_kernel(n: ti.i32, timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1)):
    """
    Upload song timestamps without padding to MAX_SONG_NOTES.

    This reduces CPU->GPU transfer volume vs `field.from_numpy(padded)` while
    preserving behavior (kernels only read indices < total_notes).
    """
    for i in range(n):
        fields.song_timestamps[i] = timestamps[i]


@ti.kernel
def _upload_song_note_group_idx_kernel(n: ti.i32, note_group_idx: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    """Upload note_idx -> group_idx mapping without padding."""
    for i in range(n):
        fields.song_note_group_idx[i] = note_group_idx[i]


@ti.kernel
def _upload_song_groups_kernel(
    n_groups: ti.i32,
    group_starts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_base_t_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_low_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_high_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """Upload chord-group arrays used by the analytical timing-envelope ceiling kernel."""
    for g in range(n_groups):
        fields.song_group_starts[g] = group_starts[g]
        fields.song_group_base_t_ms[g] = group_base_t_ms[g]
        fields.song_group_low_ms[g] = group_low_ms[g]
        fields.song_group_high_ms[g] = group_high_ms[g]


def _merge_timeline_slot_payload(
    target_field,
    slot_payload: np.ndarray,
    song_slot_i: int,
    *,
    source_slot_i: int = 0,
) -> None:
    """Merge one slot of a slot-shaped payload into a Taichi field without clobbering other slots."""
    current = target_field.to_numpy()
    payload = np.asarray(slot_payload, dtype=current.dtype)
    current[song_slot_i] = payload[int(source_slot_i)]
    target_field.from_numpy(current)


# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot
_CEILING_GROUP_PAYLOAD_CACHE_MAX = max(1, int(os.environ.get("CEILING_GROUP_PAYLOAD_CACHE_MAX", "32") or "32"))
_ceiling_group_payload_cache: "OrderedDict[tuple, dict]" = OrderedDict()
_CEILING_FRONTIER_PAYLOAD_CACHE_MAX = max(
    1, int(os.environ.get("CEILING_FRONTIER_PAYLOAD_CACHE_MAX", "2") or "2")
)
_ceiling_frontier_payload_cache: "OrderedDict[tuple, object]" = OrderedDict()
_ceiling_payload_cache_lock = threading.RLock()
_FRONTIER_DISK_CACHE_VERSION = "exact-frontier-v3"


def _frontier_payload_cache_key(song_key: tuple, ref_ft: np.ndarray, ref_ff: np.ndarray) -> tuple:
    return (
        _FRONTIER_DISK_CACHE_VERSION,
        song_key,
        bytes(array_sig16(np.asarray(ref_ft, dtype=np.float32).reshape(-1))),
        bytes(array_sig16(np.asarray(ref_ff, dtype=np.float32).reshape(-1))),
    )


def _frontier_disk_cache_dir() -> Path:
    override = str(os.environ.get("TIMELINE_FRONTIER_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "bin" / "timeline_frontier_cache"


def _frontier_disk_cache_path(cache_key: tuple) -> Path:
    digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
    return _frontier_disk_cache_dir() / f"{digest}.npz"


def _load_frontier_payload_from_disk(cache_key: tuple) -> TimelineFrontierGridPayload | None:
    if not env_flag("TIMELINE_FRONTIER_DISK_CACHE", "1"):
        return None
    path = _frontier_disk_cache_path(cache_key)
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version != _FRONTIER_DISK_CACHE_VERSION:
                return None
            return TimelineFrontierGridPayload(
                grid_count_body_fever=np.asarray(data["grid_count_body_fever"], dtype=np.int32),
                grid_count_body_normal=np.asarray(data["grid_count_body_normal"], dtype=np.int32),
                grid_head_len=np.asarray(data["grid_head_len"], dtype=np.int8),
                grid_N_hn=np.asarray(data["grid_N_hn"], dtype=np.int16),
                grid_N_hf=np.asarray(data["grid_N_hf"], dtype=np.int16),
                grid_Sigma_hn=np.asarray(data["grid_Sigma_hn"], dtype=np.int16),
                grid_Sigma_hf=np.asarray(data["grid_Sigma_hf"], dtype=np.int16),
                grid_fever_masks_bits=np.asarray(data["grid_fever_masks_bits"], dtype=np.uint32),
                grid_frontier_count=np.asarray(data["grid_frontier_count"], dtype=np.int32),
                grid_frontier_offset=np.asarray(data["grid_frontier_offset"], dtype=np.int32),
                grid_frontier_body_fever_pool=np.asarray(data["grid_frontier_body_fever_pool"], dtype=np.int32),
                grid_frontier_body_normal_pool=np.asarray(data["grid_frontier_body_normal_pool"], dtype=np.int32),
                grid_frontier_masks_bits_pool=np.asarray(data["grid_frontier_masks_bits_pool"], dtype=np.uint32),
                grid_sig0=np.asarray(data["grid_sig0"], dtype=np.uint64),
                grid_sig1=np.asarray(data["grid_sig1"], dtype=np.uint64),
                grid_gap=np.asarray(data["grid_gap"], dtype=np.int32),
                grid_fever_activations=np.asarray(data["grid_fever_activations"], dtype=np.int32),
                frontier_pool_used=int(data["frontier_pool_used"].item()),
            )
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def _save_frontier_payload_to_disk(cache_key: tuple, payload: TimelineFrontierGridPayload) -> None:
    if not env_flag("TIMELINE_FRONTIER_DISK_CACHE", "1"):
        return
    path = _frontier_disk_cache_path(cache_key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
        np.savez(
            tmp,
            version=np.asarray(_FRONTIER_DISK_CACHE_VERSION),
            frontier_pool_used=np.asarray(int(payload.frontier_pool_used), dtype=np.int32),
            grid_count_body_fever=payload.grid_count_body_fever,
            grid_count_body_normal=payload.grid_count_body_normal,
            grid_head_len=payload.grid_head_len,
            grid_N_hn=payload.grid_N_hn,
            grid_N_hf=payload.grid_N_hf,
            grid_Sigma_hn=payload.grid_Sigma_hn,
            grid_Sigma_hf=payload.grid_Sigma_hf,
            grid_fever_masks_bits=payload.grid_fever_masks_bits,
            grid_frontier_count=payload.grid_frontier_count,
            grid_frontier_offset=payload.grid_frontier_offset,
            grid_frontier_body_fever_pool=payload.grid_frontier_body_fever_pool,
            grid_frontier_body_normal_pool=payload.grid_frontier_body_normal_pool,
            grid_frontier_masks_bits_pool=payload.grid_frontier_masks_bits_pool,
            grid_sig0=payload.grid_sig0,
            grid_sig1=payload.grid_sig1,
            grid_gap=payload.grid_gap,
            grid_fever_activations=payload.grid_fever_activations,
        )
        tmp.replace(path)
    except Exception:
        pass


def _timeline_song_profile_key(calc_song: dict | None) -> str | None:
    try:
        meta = (calc_song or {}).get("metadata", {}) or {}
        song_name = str(meta.get("Song Name") or meta.get("Song") or "").strip()
        if not song_name:
            return None
        diff = str(meta.get("Difficulty") or "").strip()
        return f"{song_name} ({diff})" if diff else song_name
    except Exception:
        return None


def _emit_timeline_phase(
    *,
    phase: str,
    start: float,
    calc_song: dict | None,
    song_slot: int,
    **metrics,
) -> None:
    payload = {
        "phase": str(phase),
        "ms": float((time.perf_counter() - float(start)) * 1000.0),
        "song_slot": int(song_slot),
    }
    payload.update(metrics)
    emit_profile_event(
        component="gpu_executor",
        event="timeline_precompute_phase",
        song_key=_timeline_song_profile_key(calc_song),
        metrics=payload,
    )


def _song_timing_cache_key(calc_song: dict) -> tuple:
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    cached = calc_song.get("_gpu_timing_cache_key_frontier", None)
    if isinstance(cached, tuple) and len(cached) == 12:
        return cached
    chart_ts = song_data.get("chart_timestamps", None)
    timestamps = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    ts_sig = song_data.get("_chart_timestamps_sig", None)
    if not isinstance(ts_sig, (bytes, bytearray, memoryview)) or len(ts_sig) != 16:
        ts_sig = array_sig16(timestamps)
    nt_sig = song_data.get("_note_types_sig", None)
    if not isinstance(nt_sig, (bytes, bytearray, memoryview)) or len(nt_sig) != 16:
        nt_sig = array_sig16(song_data.get("note_types"))
    key = (
        str(meta.get("Song Name", "")),
        str(meta.get("Difficulty", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        bytes(ts_sig),
        bytes(nt_sig),
    ) + timing_envelope_timing_context(calc_song)
    # Cache on the calc_song dict to avoid repeated full-array hashing when the
    # same song is revisited and precompute_timeline_gpu() hits the slot cache.
    calc_song["_gpu_timing_cache_key_frontier"] = key
    return key


def _get_or_build_ceiling_group_payload(
    base_song_key: tuple,
    *,
    timestamps: np.ndarray,
    note_types: object,
) -> dict:
    """
    Prepare and cache chord-group payloads used by the analytical timing-envelope ceiling kernel.

    This CPU preprocessing is a pure function of chart timestamps + note types (and the
    fixed Perfect window constants). Caching avoids recomputing grouping + dense note->group
    maps when the same song is revisited across slots or after timeline cache resets.
    """
    global _ceiling_group_payload_cache

    n = int(getattr(timestamps, "shape", (0,))[0] or 0)
    with _ceiling_payload_cache_lock:
        cached = _ceiling_group_payload_cache.get(base_song_key)
        if isinstance(cached, dict):
            try:
                if int(cached.get("n", -1) or -1) == int(n) and int(cached.get("group_count", 0) or 0) > 0:
                    _ceiling_group_payload_cache.move_to_end(base_song_key)
                    return cached
            except Exception:
                pass

    from gear_optimizer.solver.timing_envelope import prepare_perfect_timing_envelope

    prepared = prepare_perfect_timing_envelope(
        timestamps,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )
    group_starts = np.asarray(prepared.get("group_starts", ()), dtype=np.int32)
    group_ends = np.asarray(prepared.get("group_ends", ()), dtype=np.int32)
    group_base_t_ms = np.asarray(prepared.get("group_base_t", ()), dtype=np.int32)
    group_low_ms = np.asarray(prepared.get("group_low", ()), dtype=np.int32)
    group_high_ms = np.asarray(prepared.get("group_high", ()), dtype=np.int32)
    group_count = int(group_starts.shape[0])
    if int(prepared.get("n", n) or 0) != int(n):
        raise ValueError("prepare_perfect_timing_envelope produced mismatched note count")
    if n > 0 and group_count <= 0:
        raise ValueError("prepare_perfect_timing_envelope produced no chord groups")

    if n <= 0:
        note_group_idx = np.zeros((0,), dtype=np.int32)
    else:
        # Fast-path: grouping produces a contiguous partition of note indices, so
        # note->group can be constructed via repeat() instead of a Python loop.
        is_partition = False
        try:
            if int(group_starts[0]) == 0 and int(group_ends[-1]) == int(n):
                if group_count == 1 or bool(np.all(group_starts[1:] == group_ends[:-1])):
                    is_partition = True
        except Exception:
            is_partition = False

        if is_partition:
            lengths = (group_ends - group_starts).astype(np.int32, copy=False)
            note_group_idx = np.repeat(np.arange(int(group_count), dtype=np.int32), lengths)
        else:
            note_group_idx = np.full(int(n), -1, dtype=np.int32)
            for g in range(group_count):
                s = int(group_starts[g])
                e = int(group_ends[g])
                if e > s:
                    note_group_idx[s:e] = int(g)
            if int(np.any(note_group_idx < 0)):
                raise ValueError("prepare_perfect_timing_envelope produced uncovered note indices")

    payload = {
        "n": int(n),
        "group_count": int(group_count),
        "note_group_idx": np.ascontiguousarray(note_group_idx),
        "group_starts": np.ascontiguousarray(group_starts),
        "group_base_t_ms": np.ascontiguousarray(group_base_t_ms),
        "group_low_ms": np.ascontiguousarray(group_low_ms),
        "group_high_ms": np.ascontiguousarray(group_high_ms),
    }

    with _ceiling_payload_cache_lock:
        cached = _ceiling_group_payload_cache.get(base_song_key)
        if isinstance(cached, dict):
            try:
                if int(cached.get("n", -1) or -1) == int(n) and int(cached.get("group_count", 0) or 0) > 0:
                    _ceiling_group_payload_cache.move_to_end(base_song_key)
                    return cached
            except Exception:
                pass
        _ceiling_group_payload_cache[base_song_key] = payload
        _ceiling_group_payload_cache.move_to_end(base_song_key)
        while len(_ceiling_group_payload_cache) > int(_CEILING_GROUP_PAYLOAD_CACHE_MAX):
            _ceiling_group_payload_cache.popitem(last=False)

    return payload


def _get_or_build_ceiling_frontier_payload(
    song_key: tuple,
    *,
    song_slot: int,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    song_profile_key: str | None = None,
    group_payload: dict,
    ref_ft: np.ndarray,
    ref_ff: np.ndarray,
) -> TimelineFrontierGridPayload:
    """Build and cache the packed exact frontier grid for a song/ref signature."""
    global _ceiling_frontier_payload_cache

    cache_key = _frontier_payload_cache_key(song_key, ref_ft, ref_ff)
    with _ceiling_payload_cache_lock:
        cached = _ceiling_frontier_payload_cache.get(cache_key)
        if isinstance(cached, TimelineFrontierGridPayload):
            _ceiling_frontier_payload_cache.move_to_end(cache_key)
            return cached

    cached = _load_frontier_payload_from_disk(cache_key)
    if isinstance(cached, TimelineFrontierGridPayload):
        with _ceiling_payload_cache_lock:
            _ceiling_frontier_payload_cache[cache_key] = cached
            _ceiling_frontier_payload_cache.move_to_end(cache_key)
        return cached

    payload = build_timeline_frontier_grid_payload(
        song_slot=0,
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        song_key=song_profile_key,
        group_starts=np.asarray(group_payload.get("group_starts", ()), dtype=np.int32),
        group_ends=np.asarray(group_payload.get("group_ends", ()), dtype=np.int32),
        group_base_t_ms=np.asarray(group_payload.get("group_base_t_ms", ()), dtype=np.int32),
        group_low_ms=np.asarray(group_payload.get("group_low_ms", ()), dtype=np.int32),
        group_high_ms=np.asarray(group_payload.get("group_high_ms", ()), dtype=np.int32),
        note_group_idx=np.asarray(group_payload.get("note_group_idx", ()), dtype=np.int32),
        ref_ft=np.asarray(ref_ft, dtype=np.float32),
        ref_ff=np.asarray(ref_ff, dtype=np.float32),
    )

    _save_frontier_payload_to_disk(cache_key, payload)
    with _ceiling_payload_cache_lock:
        cached = _ceiling_frontier_payload_cache.get(cache_key)
        if isinstance(cached, TimelineFrontierGridPayload):
            _ceiling_frontier_payload_cache.move_to_end(cache_key)
            return cached
        _ceiling_frontier_payload_cache[cache_key] = payload
        _ceiling_frontier_payload_cache.move_to_end(cache_key)
        while len(_ceiling_frontier_payload_cache) > int(_CEILING_FRONTIER_PAYLOAD_CACHE_MAX):
            _ceiling_frontier_payload_cache.popitem(last=False)

    return payload


def _timeline_payload_context(calc_song: dict, ref_arrays: dict, *, ref_sig: bytes | None = None) -> dict:
    if not isinstance(calc_song, dict):
        raise TypeError("calc_song must be a dict")
    if not isinstance(ref_arrays, dict):
        raise TypeError("ref_arrays must be a dict")

    base_song_key = _song_timing_cache_key(calc_song)
    ref_sig_b = bytes(_ref_arrays_sig(ref_arrays) if ref_sig is None else ref_sig)
    song_key = base_song_key + (ref_sig_b,)
    song_data = calc_song.get("song_data", {}) or {}
    chart_ts = song_data.get("chart_timestamps", None)
    src = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    timestamps = np.asarray(src, dtype=np.float32)
    total_notes = int(len(timestamps))
    if total_notes > fields.MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {fields.MAX_SONG_NOTES}")

    group_payload = _get_or_build_ceiling_group_payload(
        base_song_key[:-1],
        timestamps=timestamps,
        note_types=song_data.get("note_types", None),
    )
    payload_n = int(group_payload.get("n", 0) or 0)
    if int(payload_n) != int(total_notes):
        raise ValueError("prepare_perfect_timing_envelope produced mismatched note count")
    if total_notes > 0 and int(group_payload.get("group_count", 0) or 0) <= 0:
        raise ValueError("prepare_perfect_timing_envelope produced no chord groups")

    return {
        "base_song_key": base_song_key,
        "song_key": song_key,
        "timestamps": timestamps,
        "total_notes": int(total_notes),
        "group_payload": group_payload,
        "long_notes": int(calc_song["metadata"].get("Long Notes", 0)),
        "last_note_time": float(calc_song["metadata"].get("Last Note Time", 0)),
        "song_profile_key": _timeline_song_profile_key(calc_song),
        "ref_ft": np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1),
        "ref_ff": np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1),
    }


def prewarm_timeline_frontier_payload(calc_song: dict, ref_arrays: dict) -> None:
    """
    Build/cache the exact symbolic frontier payload without touching Taichi fields.

    Native in-flight mode uses this on background CPU workers for prepared future
    songs. The later GPU request still owns field upload and kernel execution.
    """
    t0 = time.perf_counter()
    ctx = _timeline_payload_context(calc_song, ref_arrays)
    with _ceiling_payload_cache_lock:
        cache_hit = _frontier_payload_cache_key(ctx["song_key"], ctx["ref_ft"], ctx["ref_ff"]) in _ceiling_frontier_payload_cache
    payload = _get_or_build_ceiling_frontier_payload(
        ctx["song_key"],
        song_slot=0,
        total_notes=int(ctx["total_notes"]),
        long_notes=int(ctx["long_notes"]),
        last_note_time=float(ctx["last_note_time"]),
        song_profile_key=ctx["song_profile_key"],
        group_payload=ctx["group_payload"],
        ref_ft=ctx["ref_ft"],
        ref_ff=ctx["ref_ff"],
    )
    emit_profile_event(
        component="inflight_orchestrator",
        event="timeline_frontier_prewarm",
        song_key=ctx["song_profile_key"],
        metrics={
            "ms": float((time.perf_counter() - t0) * 1000.0),
            "cache_hit": int(bool(cache_hit)),
            "total_notes": int(ctx["total_notes"]),
            "long_notes": int(ctx["long_notes"]),
            "frontier_pool_used": int(payload.frontier_pool_used),
        },
    )


def precompute_timeline_gpu(calc_song: dict, ref_arrays: dict, song_slot: int = 0) -> None:
    """
    Precompute all 161×161 fever timeline entries on GPU.

    This replaces the CPU Numba path (calculate_fever_timeline_indices) which
    had 28.7s typeof() overhead from 20M calls.

    GPU computes all 26,521 timelines in parallel in ~100ms.

    Args:
        calc_song: Song calculation context with timestamps/metadata
        ref_arrays: Reference lookup arrays (must include Fever Time/Fill Rate)
        song_slot: Grid slot to write to (0-7, default 0 for single-song mode)

    After calling this, the grid fields for song_slot are populated:
    - grid_count_body_fever[song_slot, ft, ff]
    - grid_count_body_normal[song_slot, ft, ff]
    - grid_head_len[song_slot, ft, ff]
    - grid_fever_masks[song_slot, ft, ff, :]
    - grid_fever_masks_bits[song_slot, ft, ff, :]
    - grid_gap[song_slot, ft, ff] (computed by CPU upload path)
    - grid_fever_activations[song_slot, ft, ff] (computed by CPU upload path)
    """
    global _gpu_timeline_song_id_by_slot

    song_slot = int(song_slot)
    if song_slot < 0 or song_slot >= MAX_SONG_SLOTS:
        raise ValueError(f"song_slot out of range: {song_slot}")

    # Ensure GPU is ready with refs and grid fields (even on cache hit).
    # Also reuse the ref signature so callers don't hash refs twice.
    ref_sig = ensure_ready(ref_arrays) if isinstance(ref_arrays, dict) else ensure_ready(None)

    ctx = _timeline_payload_context(calc_song, ref_arrays, ref_sig=ref_sig)
    # Check if we already computed for this song+ref set.
    song_key = ctx["song_key"]
    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return  # Already computed

    # Upload chart timestamps and note-group metadata for the exact frontier path.
    timestamps = np.asarray(ctx["timestamps"], dtype=np.float32)
    total_notes = int(ctx["total_notes"])

    # Upload only the used prefix (avoid padding to MAX_SONG_NOTES).
    if _profiler.enabled:
        _t_ts = time.perf_counter()
        _upload_song_timestamps_kernel(int(total_notes), timestamps)
        _profiler.record_upload(time.perf_counter() - _t_ts, bytes_count=int(timestamps.nbytes))
    else:
        _upload_song_timestamps_kernel(int(total_notes), timestamps)

    group_count = 0
    note_group_idx = None
    group_starts = None
    group_base_t_ms = None
    group_low_ms = None
    group_high_ms = None
    payload = ctx["group_payload"]
    payload_n = int(payload.get("n", 0) or 0)
    if int(payload_n) != int(total_notes):
        raise ValueError("prepare_perfect_timing_envelope produced mismatched note count")

    note_group_idx = np.asarray(payload.get("note_group_idx", ()), dtype=np.int32)
    group_starts = np.asarray(payload.get("group_starts", ()), dtype=np.int32)
    group_base_t_ms = np.asarray(payload.get("group_base_t_ms", ()), dtype=np.int32)
    group_low_ms = np.asarray(payload.get("group_low_ms", ()), dtype=np.int32)
    group_high_ms = np.asarray(payload.get("group_high_ms", ()), dtype=np.int32)
    group_count = int(payload.get("group_count", 0) or 0)
    if total_notes > 0 and group_count <= 0:
        raise ValueError("prepare_perfect_timing_envelope produced no chord groups")

    if _profiler.enabled:
        _t_groups = time.perf_counter()
        _upload_song_note_group_idx_kernel(int(total_notes), note_group_idx)
        _upload_song_groups_kernel(
            int(group_count),
            group_starts,
            group_base_t_ms,
            group_low_ms,
            group_high_ms,
        )
        upload_bytes = int(
            note_group_idx.nbytes
            + group_starts.nbytes
            + group_base_t_ms.nbytes
            + group_low_ms.nbytes
            + group_high_ms.nbytes
        )
        _profiler.record_upload(time.perf_counter() - _t_groups, bytes_count=upload_bytes)
    else:
        _upload_song_note_group_idx_kernel(int(total_notes), note_group_idx)
        _upload_song_groups_kernel(
            int(group_count),
            group_starts,
            group_base_t_ms,
            group_low_ms,
            group_high_ms,
        )

    # Extract song metadata
    long_notes = int(ctx["long_notes"])
    last_note_time = float(ctx["last_note_time"])

    # Sync before timing
    _maybe_sync(for_timing=True)
    _t0 = time.perf_counter()

    write_unpacked_masks = (
        1 if (env_flag("GPU_TIMELINE_WRITE_UNPACKED_MASKS", "0") or fields.grid_fever_masks is not None) else 0
    )
    if write_unpacked_masks != 0:
        fields.ensure_grid_unpacked_masks_allocated()
    group_payload = payload
    ref_ft = np.asarray(ctx["ref_ft"], dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ctx["ref_ff"], dtype=np.float32).reshape(-1)
    song_slot_i = int(song_slot)
    song_profile_key = ctx["song_profile_key"]
    frontier_cache_key = _frontier_payload_cache_key(song_key, ref_ft, ref_ff)
    with _ceiling_payload_cache_lock:
        frontier_cache_hit = frontier_cache_key in _ceiling_frontier_payload_cache
    t_frontier = time.perf_counter()
    frontier_payload = _get_or_build_ceiling_frontier_payload(
        song_key,
        song_slot=int(song_slot),
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        song_profile_key=song_profile_key,
        group_payload=group_payload,
        ref_ft=ref_ft,
        ref_ff=ref_ff,
    )
    _emit_timeline_phase(
        phase="frontier_payload_cache_hit" if frontier_cache_hit else "frontier_payload_cache_miss",
        start=t_frontier,
        calc_song=calc_song,
        song_slot=song_slot_i,
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        frontier_pool_used=int(frontier_payload.frontier_pool_used),
    )
    t_merge = time.perf_counter()
    payload_slot_i = 0
    _merge_timeline_slot_payload(fields.grid_count_body_fever, frontier_payload.grid_count_body_fever, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_count_body_normal, frontier_payload.grid_count_body_normal, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_head_len, frontier_payload.grid_head_len, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_N_hn, frontier_payload.grid_N_hn, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_N_hf, frontier_payload.grid_N_hf, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_Sigma_hn, frontier_payload.grid_Sigma_hn, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_Sigma_hf, frontier_payload.grid_Sigma_hf, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_fever_masks_bits, frontier_payload.grid_fever_masks_bits, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_frontier_count, frontier_payload.grid_frontier_count, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_frontier_offset, frontier_payload.grid_frontier_offset, song_slot_i)
    _merge_timeline_slot_payload(
        fields.grid_frontier_body_fever_pool, frontier_payload.grid_frontier_body_fever_pool, song_slot_i
    )
    _merge_timeline_slot_payload(
        fields.grid_frontier_body_normal_pool, frontier_payload.grid_frontier_body_normal_pool, song_slot_i
    )
    _merge_timeline_slot_payload(
        fields.grid_frontier_masks_bits_pool, frontier_payload.grid_frontier_masks_bits_pool, song_slot_i
    )
    _merge_timeline_slot_payload(fields.grid_sig0, frontier_payload.grid_sig0, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_sig1, frontier_payload.grid_sig1, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_gap, frontier_payload.grid_gap, song_slot_i)
    _merge_timeline_slot_payload(fields.grid_fever_activations, frontier_payload.grid_fever_activations, song_slot_i)
    _emit_timeline_phase(
        phase="frontier_field_merge",
        start=t_merge,
        calc_song=calc_song,
        song_slot=song_slot_i,
        frontier_count=int(
            np.count_nonzero(np.asarray(frontier_payload.grid_frontier_count[payload_slot_i], dtype=np.int32))
        ),
        frontier_variants=int(np.sum(np.asarray(frontier_payload.grid_frontier_count[payload_slot_i], dtype=np.int64))),
    )
    if write_unpacked_masks != 0:
        # Build i8 masks from the bitpacked representation on-GPU (debug/tests only).
        t_unpack = time.perf_counter()
        kernels.unpack_timeline_grid_masks_kernel(int(song_slot))
        _emit_timeline_phase(
            phase="unpack_timeline_masks",
            start=t_unpack,
            calc_song=calc_song,
            song_slot=song_slot_i,
        )

    _maybe_sync(for_timing=True)
    _t1 = time.perf_counter()

    _gpu_timeline_song_id_by_slot[song_slot] = song_key

    if _SYNC_FOR_TIMING or _FORCE_SYNC:
        print(f"[GPU Timeline] Computed 161×161 grid in {(_t1 - _t0) * 1000:.1f}ms")


def reset_timeline_state() -> None:
    """Reset module-level timeline upload caches after `ti.reset()`."""
    global _gpu_timeline_song_id_by_slot
    global _ceiling_group_payload_cache, _ceiling_frontier_payload_cache
    _gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS
    with _ceiling_payload_cache_lock:
        _ceiling_group_payload_cache.clear()
        _ceiling_frontier_payload_cache.clear()
