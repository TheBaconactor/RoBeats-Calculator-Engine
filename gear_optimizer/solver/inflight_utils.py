"""
Shared helpers for the in-flight orchestrators.

These functions are intentionally kept in one place to avoid copy/paste drift
between in-flight implementations.
"""

from __future__ import annotations

import os
import copy
from collections import deque
from collections import OrderedDict
from typing import Any, Optional

import numpy as np


def _truthy(v: Any) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


_SONG_FILE_CACHE: "OrderedDict[str, tuple[dict, np.ndarray, np.ndarray]]" = OrderedDict()


def _song_file_cache_max() -> int:
    # Cache parsed song file -> numpy arrays across repeats.
    # Large enough to cover typical SongRepeats / small queues without ballooning RAM.
    try:
        raw = os.environ.get("INFLIGHT_SONG_FILE_CACHE_MAX")
        if raw is not None and str(raw).strip() != "":
            return max(0, int(raw))
        default = 2048 if _truthy(os.environ.get("INFLIGHT_RAM_MODE", "0")) else 128
        return max(0, int(default))
    except Exception:
        return 128


def _song_file_cache_get(fp: str) -> tuple[dict, np.ndarray, np.ndarray] | None:
    try:
        v = _SONG_FILE_CACHE.get(fp)
    except Exception:
        return None
    if v is not None:
        try:
            _SONG_FILE_CACHE.move_to_end(fp)
        except Exception:
            pass
    return v


def _song_file_cache_put(fp: str, meta: dict, ts: np.ndarray, note_types: np.ndarray) -> None:
    try:
        _SONG_FILE_CACHE[fp] = (meta, ts, note_types)
        _SONG_FILE_CACHE.move_to_end(fp)
    except Exception:
        return
    max_n = int(_song_file_cache_max())
    if max_n <= 0:
        try:
            _SONG_FILE_CACHE.clear()
        except Exception:
            pass
        return
    try:
        while len(_SONG_FILE_CACHE) > max_n:
            _SONG_FILE_CACHE.popitem(last=False)
    except Exception:
        pass


class SongSlotPool:
    def __init__(self, max_song_slots: int):
        # Slot 0 is reserved; allocate 1..N-1.
        n = max(2, int(max_song_slots))
        self._free = deque(range(1, n))

    def acquire(self) -> int:
        if not self._free:
            raise RuntimeError("No free GPU song slots")
        return int(self._free.popleft())

    def release(self, slot_id: int) -> None:
        slot_id = int(slot_id)
        if slot_id <= 0:
            return
        if slot_id not in self._free:
            self._free.append(slot_id)


def _build_calc_song_from_file(*, fp: str, found_song_name: str, cfg, cfg_dict: Optional[dict] = None) -> dict:
    from gear_optimizer.pipeline.song_processor import read_song_file

    cached = _song_file_cache_get(fp)
    if cached is None:
        song_data = read_song_file(fp)
        song_timestamps_np = np.array(song_data.get("timestamps") or [], dtype=np.float64)
        song_note_types_np = np.array(song_data.get("note_types") or [], dtype=np.int16)
        if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
            song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)
        meta0 = song_data.get("song_details") or {}
        _song_file_cache_put(fp, meta0 if isinstance(meta0, dict) else {}, song_timestamps_np, song_note_types_np)
        cached = _song_file_cache_get(fp)
    if cached is None:
        # Defensive fallback (shouldn't happen).
        cached = ({}, np.array([], dtype=np.float64), np.array([], dtype=np.int16))
    meta0, song_timestamps_np, song_note_types_np = cached

    calc_song = {
        # NOTE: must not share metadata across runs; HumanHitSim mutates metadata in-place.
        "metadata": copy.deepcopy(meta0) if isinstance(meta0, dict) else {},
        "song_data": {
            "timestamps": song_timestamps_np,
            "chart_timestamps": song_timestamps_np,
            "note_types": song_note_types_np,
        },
    }

    # Optional: HumanHitSim (match song_processor.py semantics).
    try:
        if cfg_dict is None:
            from gear_optimizer.core.utils import cfg_to_dict

            cfg_dict = cfg_to_dict(cfg)
        from gear_optimizer.solver.hit_simulation import apply_human_hit_sim, plan_human_hit_sim

        # Plan deterministically (records seed/knobs), then:
        # - Apply immediately when ApplyTo=ALL (affects GA/base scoring).
        # - Defer when ApplyTo=FG (FG stage will apply later if needed).
        plan_human_hit_sim(calc_song, cfg_dict=cfg_dict or {})
        apply_to = str((calc_song.get("metadata") or {}).get("HumanHitSimApplyTo", "FG") or "").strip().upper()
        if apply_to == "ALL":
            apply_human_hit_sim(calc_song, cfg_dict=cfg_dict or {})
    except Exception:
        pass

    return calc_song


def _compact_items(items: list) -> list[str]:
    out: list[str] = []
    for it in items or []:
        if isinstance(it, dict):
            name = it.get("Name", "")
        else:
            name = str(it) if it else ""
        if name:
            out.append(name)
    return out


def _compact_prev_record(record: Optional[dict]) -> Optional[dict]:
    if not isinstance(record, dict):
        return None
    out = dict(record)
    out["gear"] = _compact_items(record.get("gear"))
    out["minis"] = _compact_items(record.get("minis"))
    if isinstance(out.get("loadout"), (list, tuple)):
        out["loadout"] = [str(x) if x is not None else "" for x in out.get("loadout")]
    force_obj = out.get("force")
    if isinstance(force_obj, dict):
        force_copy = dict(force_obj)
        if isinstance(force_copy.get("gear"), (list, tuple)):
            force_copy["gear"] = [str(x) if x is not None else "" for x in force_copy.get("gear")]
        if isinstance(force_copy.get("minis"), (list, tuple)):
            force_copy["minis"] = [str(x) if x is not None else "" for x in force_copy.get("minis")]
        out["force"] = force_copy
    return out


def _summarize_db_context(
    prev_record: Optional[dict],
    known_loadouts: Optional[dict],
    *,
    db_key: Optional[str] = None,
    use_evo_db: bool = False,
) -> tuple[int, int, int]:
    # Prefer the authoritative `songs.best_fg_score`.
    # `known_loadouts` can be ordered/limited by base score, which can miss the true best FG record.
    db_best_fg_score = 0
    if use_evo_db and db_key:
        try:
            from gear_optimizer.data.database import get_db_connection_cached

            conn = get_db_connection_cached()
            row = conn.execute(
                "SELECT best_fg_score FROM songs WHERE name = ?",
                (str(db_key or "").strip(),),
            ).fetchone()
            if row is not None:
                try:
                    db_best_fg_score = int(row[0] or 0)
                except Exception:
                    db_best_fg_score = 0
        except Exception:
            db_best_fg_score = 0

    # Fallback: for brand-new songs not yet in `songs`, approximate from cached loadouts.
    if (not db_best_fg_score) and known_loadouts:
        try:
            db_best_fg_score = max(v[1] for v in known_loadouts.values() if v[1])
        except Exception:
            db_best_fg_score = 0

    attempt_lifetime_prev = 0
    prev_attempts_first = 0
    if prev_record and "details" in prev_record:
        attempt_lifetime_prev = prev_record["details"].get("attempt_lifetime", 0) or 0
        prev_attempts_first = prev_record["details"].get("attempts_first", 0) or 0
    attempt_lifetime = int(attempt_lifetime_prev) + 1
    return int(db_best_fg_score or 0), int(attempt_lifetime or 0), int(prev_attempts_first or 0)
