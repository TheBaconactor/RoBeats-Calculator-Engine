from __future__ import annotations

import os
from collections import OrderedDict
import hashlib
from typing import Any


REGISTRY_STATIC_HANDLE_CACHE_MAX = max(
    16, int(os.environ.get("GPU_EXECUTOR_REGISTRY_HANDLE_CACHE_MAX", "256") or "256")
)
REGISTRY_STATIC_HANDLE_CACHE: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
_REGISTRY_STATIC_HANDLE_COUNTER = 0


def minimize_calc_song_for_gpu_timeline_grid(calc_song: Any) -> Any:
    """
    Reduce IPC payload size for `timeline_grid` when it is actually a `calc_song` dict.

    `taichi_gem.api.timeline.precompute_timeline_gpu` only needs:
      - calc_song["song_data"]["timestamps"] / chart_timestamps
      - calc_song["song_data"]["note_types"]
      - calc_song["metadata"]["Long Notes"]
      - calc_song["metadata"]["Last Note Time"]
      - timing-envelope metadata used by cache keys
    """
    if not isinstance(calc_song, dict):
        return calc_song

    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    if not isinstance(meta, dict) or not isinstance(song_data, dict):
        return calc_song

    timestamps = song_data.get("timestamps")
    if timestamps is None:
        return calc_song

    def _contiguous_array(value: Any, dtype: Any) -> Any:
        if value is None:
            return None
        out = value
        try:
            import numpy as np

            out = np.asarray(value, dtype=dtype)
            if not out.flags["C_CONTIGUOUS"]:
                out = np.ascontiguousarray(out)
        except (ValueError, TypeError):
            out = value
        return out

    ts_out = _contiguous_array(timestamps, "float32")
    chart_ts = song_data.get("chart_timestamps")
    chart_ts_out = _contiguous_array(chart_ts, "float32") if chart_ts is not None else None
    note_types = song_data.get("note_types")
    note_types_out = _contiguous_array(note_types, "int16") if note_types is not None else None

    song_data_out: dict[str, Any] = {"timestamps": ts_out}
    if chart_ts_out is not None:
        song_data_out["chart_timestamps"] = chart_ts_out
    if note_types_out is not None:
        song_data_out["note_types"] = note_types_out
    for sig_key in ("_timestamps_sig", "_chart_timestamps_sig", "_note_types_sig"):
        sig_val = song_data.get(sig_key)
        if isinstance(sig_val, (bytes, bytearray, memoryview)) and len(sig_val) == 16:
            song_data_out[sig_key] = bytes(sig_val)

    meta_out = {
        "Song Name": meta.get("Song Name", ""),
        "Difficulty": meta.get("Difficulty", ""),
        "Long Notes": int(meta.get("Long Notes", 0) or 0),
        "Last Note Time": float(meta.get("Last Note Time", 0) or 0.0),
        "TimingEnvelopeApplied": bool(meta.get("TimingEnvelopeApplied")),
        "TimingEnvelopeMode": meta.get("TimingEnvelopeMode", ""),
        "TimingEnvelopeFGCarry": meta.get("TimingEnvelopeFGCarry", ""),
    }
    return {"metadata": meta_out, "song_data": song_data_out}


def registry_base_fixed_stats_sig(arr: Any) -> tuple[Any, ...]:
    """
    Build a compact content signature for small base-fixed arrays.

    This keeps handle reuse robust even when callers rebuild small numpy arrays
    with identical values between requests.
    """
    try:
        import numpy as np

        a = np.asarray(arr, dtype=np.int32)
        if a.ndim == 0:
            return ("scalar", int(a))
        h = hashlib.blake2b(digest_size=8)
        h.update(memoryview(np.ascontiguousarray(a)).cast("B"))
        return ("arr", tuple(int(x) for x in a.shape), str(a.dtype), h.digest())
    except (ValueError, TypeError, AttributeError):
        return ("obj", id(arr))


def clear_registry_static_handle_cache() -> None:
    REGISTRY_STATIC_HANDLE_CACHE.clear()


def registry_static_handle_entry(
    *,
    item_stats: Any,
    slot_start: Any,
    slot_count: Any,
    base_fixed_stats: Any,
    timeline_grid: Any,
    ref_arrays: Any,
) -> dict[str, Any]:
    """
    Get or create a worker-local handle entry for registry static payload parts.

    The entry retains strong references for identity-based keys to prevent ID reuse
    collisions while the handle is alive.
    """
    global _REGISTRY_STATIC_HANDLE_COUNTER

    key = (
        int(id(item_stats)),
        int(id(slot_start)),
        int(id(slot_count)),
        registry_base_fixed_stats_sig(base_fixed_stats),
        int(id(timeline_grid)),
        int(id(ref_arrays)),
    )
    cached = REGISTRY_STATIC_HANDLE_CACHE.get(key)
    if cached is not None:
        REGISTRY_STATIC_HANDLE_CACHE.move_to_end(key)
        return cached

    _REGISTRY_STATIC_HANDLE_COUNTER += 1
    timeline_grid_send = minimize_calc_song_for_gpu_timeline_grid(timeline_grid)
    entry = {
        "handle": int(_REGISTRY_STATIC_HANDLE_COUNTER),
        "registered": False,
        "item_stats_ref": item_stats,
        "slot_start_ref": slot_start,
        "slot_count_ref": slot_count,
        "timeline_grid_ref": timeline_grid,
        "timeline_grid_send": timeline_grid_send,
        "ref_arrays_ref": ref_arrays,
    }
    REGISTRY_STATIC_HANDLE_CACHE[key] = entry
    REGISTRY_STATIC_HANDLE_CACHE.move_to_end(key)
    while len(REGISTRY_STATIC_HANDLE_CACHE) > REGISTRY_STATIC_HANDLE_CACHE_MAX:
        REGISTRY_STATIC_HANDLE_CACHE.popitem(last=False)
    return entry
