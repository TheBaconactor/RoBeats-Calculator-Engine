from __future__ import annotations

import atexit
import hashlib
import json
import logging
import os
import threading
from collections import OrderedDict
from io import StringIO

import numpy as np
from cachetools import LRUCache

from gear_optimizer.core.constants import PATHS
from gear_optimizer.data.models import WarnOnce

logger = logging.getLogger(__name__)
WARN_ONCE = WarnOnce()

_CFG_HASH_CACHE: dict[int, tuple[int, str]] = {}
_CFG_HASH_CACHE_LOCK = threading.Lock()


def _stable_cfg_hash(cfg_dict: dict | None) -> str:
    if not isinstance(cfg_dict, dict) or not cfg_dict:
        return "cfg0"
    cfg_id = int(id(cfg_dict))
    cfg_len = int(len(cfg_dict))
    with _CFG_HASH_CACHE_LOCK:
        cached = _CFG_HASH_CACHE.get(cfg_id)
        if cached is not None and int(cached[0]) == cfg_len:
            return str(cached[1])
    try:
        payload = json.dumps(cfg_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except Exception as e:
        logger.warning(f"song_io:_stable_cfg_hash: {e}")
        payload = repr(sorted(cfg_dict.items(), key=lambda kv: str(kv[0])))
    h = hashlib.sha1(payload.encode("utf-8", errors="replace")).hexdigest()
    out = h[:16]
    with _CFG_HASH_CACHE_LOCK:
        _CFG_HASH_CACHE[cfg_id] = (cfg_len, out)
        if len(_CFG_HASH_CACHE) > 32:
            _CFG_HASH_CACHE.clear()
    return out


_BASE_CALC_SONG_CACHE_MAX = 64
_BASE_CALC_SONG_CACHE: LRUCache = LRUCache(maxsize=_BASE_CALC_SONG_CACHE_MAX)
_BASE_CALC_SONG_CACHE_LOCK = threading.Lock()

_SONG_HEADER_CACHE_PATH = PATHS.bin_path("song_header_cache.json")
_SONG_HEADER_CACHE_MAX = 4096
_SONG_HEADER_CACHE_LOCK = threading.Lock()
_SONG_HEADER_CACHE: OrderedDict[str, dict[str, object]] = OrderedDict()
_SONG_HEADER_CACHE_LOADED = False
_SONG_HEADER_CACHE_DIRTY = False


def clone_calc_song(calc_song: dict) -> dict:
    """
    Clone a calc_song dict for per-run mutation.

    Arrays are shared by reference (read-only); dicts are copied.
    """
    if not isinstance(calc_song, dict):
        return {}
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    return {"metadata": dict(meta), "song_data": dict(song_data)}


def _build_base_calc_song_from_file(fp: str) -> dict:
    song_data = read_song_file(fp)

    timestamps_raw = song_data.get("timestamps")
    note_types_raw = song_data.get("note_types")
    if isinstance(timestamps_raw, np.ndarray):
        song_timestamps_np = timestamps_raw.astype(np.float32, copy=False)
    else:
        song_timestamps_np = np.asarray(timestamps_raw if timestamps_raw is not None else [], dtype=np.float32)

    if isinstance(note_types_raw, np.ndarray):
        song_note_types_np = note_types_raw.astype(np.int16, copy=False)
    else:
        song_note_types_np = np.asarray(note_types_raw if note_types_raw is not None else [], dtype=np.int16)
    if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
        song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)

    lanes_raw = song_data.get("lanes")
    if isinstance(lanes_raw, np.ndarray):
        song_lanes_np = lanes_raw.astype(np.int32, copy=False)
    else:
        song_lanes_np = np.asarray(lanes_raw if lanes_raw is not None else [], dtype=np.int32)
    if song_lanes_np.shape[0] != song_timestamps_np.shape[0]:
        # Missing/malformed lane column: fall back to all-distinct lanes (every note its own lane),
        # which imposes NO same-lane ordering constraint -- lane-aware reachability then degenerates
        # to the lane-blind result. Fail-safe: never fabricate a constraint that isn't in the chart.
        song_lanes_np = np.arange(song_timestamps_np.shape[0], dtype=np.int32)

    # The frontier cache key (timeline._song_timing_cache_key) now derives its own
    # order-invariant signature from the live (timestamp, note-type) arrays, so no
    # precomputed load-order signature is stored here.
    return {
        "metadata": song_data.get("song_details", {}) or {},
        "song_data": {
            "timestamps": song_timestamps_np,
            "chart_timestamps": song_timestamps_np,
            "note_types": song_note_types_np,
            "lanes": song_lanes_np,
        },
    }


def get_base_calc_song(fp: str, cfg_dict: dict | None = None) -> dict:
    """
    Get cached base calc_song for this file/config pair.

    The returned object is shared; callers must clone via clone_calc_song()
    before applying timing-envelope streams or any other per-run mutation.
    """
    if not fp:
        return {}

    abs_fp = os.path.abspath(fp)
    cfg_h = _stable_cfg_hash(cfg_dict)
    key = (abs_fp, cfg_h)

    try:
        st = os.stat(abs_fp)
        mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
    except Exception as e:
        logger.warning(f"song_io:get_base_calc_song: {e}")
        mtime_ns = -1

    with _BASE_CALC_SONG_CACHE_LOCK:
        entry = _BASE_CALC_SONG_CACHE.get(key)
        if entry is not None:
            cached_mtime_ns, cached_calc_song = entry
            if int(cached_mtime_ns) == int(mtime_ns) and isinstance(cached_calc_song, dict):
                return cached_calc_song

    base = _build_base_calc_song_from_file(abs_fp)
    with _BASE_CALC_SONG_CACHE_LOCK:
        _BASE_CALC_SONG_CACHE[key] = (int(mtime_ns), base)
    return base


def _prune_song_header_cache_locked() -> None:
    while len(_SONG_HEADER_CACHE) > int(_SONG_HEADER_CACHE_MAX):
        _SONG_HEADER_CACHE.popitem(last=False)


def _load_song_header_cache_locked() -> None:
    global _SONG_HEADER_CACHE_LOADED
    if _SONG_HEADER_CACHE_LOADED:
        return
    _SONG_HEADER_CACHE_LOADED = True
    try:
        with open(_SONG_HEADER_CACHE_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        logger.warning(f"song_io:_load_song_header_cache_locked: {e}")
        return
    if not isinstance(payload, dict):
        return
    for key, entry in payload.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        try:
            mtime_ns = int(entry.get("mtime_ns", -1))
            file_size = int(entry.get("size", -1))
        except Exception as e:
            logger.warning(f"song_io:_load_song_header_cache_locked: {e}")
            continue
        meta = entry.get("meta")
        if meta is not None and not isinstance(meta, dict):
            continue
        _SONG_HEADER_CACHE[key] = {"mtime_ns": mtime_ns, "size": file_size, "meta": meta}
    _prune_song_header_cache_locked()


def _flush_song_header_cache() -> None:
    global _SONG_HEADER_CACHE_DIRTY
    with _SONG_HEADER_CACHE_LOCK:
        if not _SONG_HEADER_CACHE_DIRTY:
            return
        payload = {
            key: {
                "mtime_ns": int(str(entry.get("mtime_ns", -1) or -1)),
                "size": int(str(entry.get("size", -1) or -1)),
                "meta": entry.get("meta"),
            }
            for key, entry in _SONG_HEADER_CACHE.items()
        }
        _SONG_HEADER_CACHE_DIRTY = False
    try:
        os.makedirs(os.path.dirname(_SONG_HEADER_CACHE_PATH), exist_ok=True)
        tmp_path = f"{_SONG_HEADER_CACHE_PATH}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True, separators=(",", ":"))
        os.replace(tmp_path, _SONG_HEADER_CACHE_PATH)
    except Exception as e:
        logger.warning(f"song_io:_flush_song_header_cache: {e}")
        with _SONG_HEADER_CACHE_LOCK:
            _SONG_HEADER_CACHE_DIRTY = True


def _reset_song_header_cache_for_tests() -> None:
    global _SONG_HEADER_CACHE_LOADED, _SONG_HEADER_CACHE_DIRTY
    with _SONG_HEADER_CACHE_LOCK:
        _SONG_HEADER_CACHE.clear()
        _SONG_HEADER_CACHE_LOADED = False
        _SONG_HEADER_CACHE_DIRTY = False


atexit.register(_flush_song_header_cache)


def scan_song_header(fp):
    """
    Scan first 20 lines of song file for metadata (fast check).

    Args:
        fp: File path to song file

    Returns:
        dict: Metadata dictionary or None if parse fails
    """
    abs_fp = os.path.abspath(fp)
    try:
        st = os.stat(abs_fp)
        mtime_ns_raw = getattr(st, "st_mtime_ns", None)
        mtime_ns = int(mtime_ns_raw) if isinstance(mtime_ns_raw, int) else int(st.st_mtime * 1e9)
        file_size = int(st.st_size)
    except Exception as e:
        logger.warning(f"song_io:scan_song_header: {e}")
        mtime_ns = -1
        file_size = -1

    with _SONG_HEADER_CACHE_LOCK:
        _load_song_header_cache_locked()
        cached = _SONG_HEADER_CACHE.get(abs_fp)
        if isinstance(cached, dict):
            try:
                if int(str(cached.get("mtime_ns", -2) or -2)) == int(mtime_ns) and int(
                    str(cached.get("size", -2) or -2)
                ) == int(file_size):
                    _SONG_HEADER_CACHE.move_to_end(abs_fp)
                    meta_cached = cached.get("meta")
                    return dict(meta_cached) if isinstance(meta_cached, dict) else None
            except Exception as e:
                logger.warning(f"song_io:scan_song_header: {e}")

    meta = {"Song Name": "", "Primary Color": "", "Secondary Color": "", "Difficulty": ""}
    try:
        with open(abs_fp, "r", encoding="utf-8-sig") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == "Song Data":
                    break
                # Handle both TAB and COLON separators.
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
                elif ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
        result = meta if meta["Song Name"] else None
        with _SONG_HEADER_CACHE_LOCK:
            _SONG_HEADER_CACHE[abs_fp] = {"mtime_ns": int(mtime_ns), "size": int(file_size), "meta": result}
            _SONG_HEADER_CACHE.move_to_end(abs_fp)
            _prune_song_header_cache_locked()
            global _SONG_HEADER_CACHE_DIRTY
            _SONG_HEADER_CACHE_DIRTY = True
        return dict(result) if isinstance(result, dict) else None
    except Exception as e:
        logger.warning(f"song_io:scan_song_header: {e}")
        return None


def read_song_file(fp):
    """
    Read complete song file including metadata and note timestamps.

    Args:
        fp: File path to song file

    Returns:
        dict: Song data with song_details and timestamps
    """
    data = {
        "song_details": {
            "Song Name": "",
            "Difficulty": "",
            "Primary Color": "",
            "Secondary Color": "",
            "Last Note Time": "",
            "Total Notes": "",
            "Fever Fill": "",
            "Fever Time": "",
            "Long Notes": "",
            "Timing Mode": "",
        },
        "timestamps": np.empty((0,), dtype=np.float32),
        "note_types": np.empty((0,), dtype=np.int16),
        # Column 2 (0-indexed) is the LANE/track (1..4); column 3 is the note type. Preserved for lane-aware fever
        # reachability: same-lane notes must be HIT in time order, so an activation can only be
        # delayed as far as its same-lane successor's window allows, and a clawed-in endpoint
        # cannot precede its same-lane predecessor. Lane-blind reachability over-reports the fever
        # window extension (it assumes an out-of-lane-order schedule the game cannot play).
        "lanes": np.empty((0,), dtype=np.int16),
    }
    if not fp:
        return data
    try:
        found_song_data = False
        note_lines = []
        with open(fp, "r", encoding="utf-8-sig") as f:
            for raw_line in f:
                line = raw_line.rstrip("\r\n")
                stripped = line.strip()
                if not found_song_data:
                    if stripped == "Song Data":
                        found_song_data = True
                        continue
                    if not stripped:
                        continue
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in data["song_details"]:
                            data["song_details"][key] = parts[1].strip() or "0"
                    continue

                if not stripped:
                    continue
                c = stripped[0]
                if ("0" <= c <= "9") or c == ".":
                    note_lines.append(line)

        if not found_song_data:
            return data

        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    timestamps = np.asarray(nd[:, 0], dtype=np.float32)
                    # Column 4 is the note type: 1=normal, 2=held head, 3=held tail.
                    note_types = nd[:, 3].astype(np.int16, copy=False)
                    # Column 3 (0-indexed 2) is the lane/track (1..4). Kept for lane-aware fever
                    # reachability (same-lane notes are hit in time order).
                    lanes = nd[:, 2].astype(np.int16, copy=False)
                    # Canonicalize external chart order at ingest: the game exporter
                    # (SongLoggerProd) preserves the in-engine HitObjects array order, NOT
                    # chronological order -- a hold's synthesized tail (type 3) is emitted right
                    # after its head at head_time + duration, so a later note in array order can
                    # sit earlier in time. The optimizer's fever model is strictly time-ordered
                    # (per-note floor/candidate envelopes consumed by searchsorted REQUIRE
                    # nondecreasing timestamps; the FG builder fails loudly otherwise). Stable sort
                    # by time: true chords (equal timestamps) keep the export's within-chord order,
                    # and every note carries its own type/window so a chord-tied held tail keeps
                    # its widened reach. (The legacy SongLogger pre-sorted by time; SongLoggerProd
                    # does not, which is faithful to live game data, not a bug.)
                    order = np.argsort(timestamps, kind="stable")
                    data["timestamps"] = np.ascontiguousarray(timestamps[order])
                    data["note_types"] = np.ascontiguousarray(note_types[order])
                    data["lanes"] = np.ascontiguousarray(lanes[order])
        return data
    except Exception as exc:
        WARN_ONCE.warn("song-file", f"Failed to read song file {fp}: {exc}")
        return data
