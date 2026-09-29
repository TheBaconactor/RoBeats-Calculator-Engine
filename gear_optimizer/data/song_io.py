from __future__ import annotations

import atexit
import json
import logging
import os
import threading
from collections import OrderedDict

from cachetools import LRUCache

from gear_optimizer.chart import read_chart, to_calc_song
from gear_optimizer.settings import paths

logger = logging.getLogger(__name__)

_BASE_CALC_SONG_CACHE_MAX = 64
_BASE_CALC_SONG_CACHE: LRUCache = LRUCache(maxsize=_BASE_CALC_SONG_CACHE_MAX)
_BASE_CALC_SONG_CACHE_LOCK = threading.Lock()

_SONG_HEADER_CACHE_PATH = str(paths().bin_path("song_header_cache.json"))
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


def get_base_calc_song(fp: str, cfg_dict: dict | None = None) -> dict:
    """
    Get the cached base calc_song for a chart file (see gear_optimizer.chart.to_calc_song).

    The returned object is shared; callers must clone via clone_calc_song()
    before applying timing-envelope streams or any other per-run mutation.
    ``cfg_dict`` does not affect the chart; the parameter stays until the website's
    callers move to gear_optimizer.chart.
    """
    abs_fp = os.path.abspath(fp)
    mtime_ns = os.stat(abs_fp).st_mtime_ns

    with _BASE_CALC_SONG_CACHE_LOCK:
        entry = _BASE_CALC_SONG_CACHE.get(abs_fp)
        if entry is not None and entry[0] == mtime_ns:
            return entry[1]

    base = to_calc_song(read_chart(abs_fp))
    with _BASE_CALC_SONG_CACHE_LOCK:
        _BASE_CALC_SONG_CACHE[abs_fp] = (mtime_ns, base)
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
    except (OSError, ValueError):
        return  # No cache yet, or an unreadable one: headers are rescanned and the cache rewritten.
    if not isinstance(payload, dict):
        return
    for key, entry in payload.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        mtime_ns = int(entry.get("mtime_ns", -1))
        file_size = int(entry.get("size", -1))
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
    except OSError:
        logger.warning("[SongIO] Could not write %s", _SONG_HEADER_CACHE_PATH, exc_info=True)
        with _SONG_HEADER_CACHE_LOCK:
            _SONG_HEADER_CACHE_DIRTY = True


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
    except OSError:
        return None
    mtime_ns = st.st_mtime_ns
    file_size = st.st_size

    with _SONG_HEADER_CACHE_LOCK:
        _load_song_header_cache_locked()
        cached = _SONG_HEADER_CACHE.get(abs_fp)
        if isinstance(cached, dict):
            if int(str(cached.get("mtime_ns", -2) or -2)) == int(mtime_ns) and int(
                str(cached.get("size", -2) or -2)
            ) == int(file_size):
                _SONG_HEADER_CACHE.move_to_end(abs_fp)
                meta_cached = cached.get("meta")
                return dict(meta_cached) if isinstance(meta_cached, dict) else None

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
    except (OSError, UnicodeDecodeError):
        return None
    result = meta if meta["Song Name"] else None
    with _SONG_HEADER_CACHE_LOCK:
        _SONG_HEADER_CACHE[abs_fp] = {"mtime_ns": int(mtime_ns), "size": int(file_size), "meta": result}
        _SONG_HEADER_CACHE.move_to_end(abs_fp)
        _prune_song_header_cache_locked()
        global _SONG_HEADER_CACHE_DIRTY
        _SONG_HEADER_CACHE_DIRTY = True
    return dict(result) if isinstance(result, dict) else None
