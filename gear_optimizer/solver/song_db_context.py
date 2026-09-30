from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from gear_optimizer.core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from gear_optimizer.helpers.song_helpers.database_context import (
    build_db_key,
    load_database_progress_baseline,
)
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_prev_record


@dataclass(frozen=True, slots=True)
class PreparedSongDbContext:
    baseline_team_buff: str
    db_key: str
    prev_record: Optional[dict]
    db_best_score: int
    db_best_fg_score: int
    db_baseline_valid: bool


_DB_CONTEXT_CACHE_LOCK = threading.Lock()
_DB_CONTEXT_CACHE: "OrderedDict[tuple[str, str], tuple[float, Optional[dict], int, int]]" = OrderedDict()
_DB_CONTEXT_CACHE_MAX = 1024
_DB_CONTEXT_CACHE_TTL_S = 1.0


def _cache_key(db_key: str, team_buff: str) -> tuple[str, str]:
    return (str(db_key or "").strip(), str(team_buff or "T5").strip().upper() or "T5")


def _db_context_cache_get(db_key: str, team_buff: str) -> tuple[Optional[dict], int, int] | None:
    key = _cache_key(db_key, team_buff)
    if not key[0]:
        return None
    with _DB_CONTEXT_CACHE_LOCK:
        entry = _DB_CONTEXT_CACHE.get(key)
        if entry is None:
            return None
        ts, prev_record, db_best_score, db_best_fg_score = entry
        if (time.monotonic() - float(ts)) > _DB_CONTEXT_CACHE_TTL_S:
            _DB_CONTEXT_CACHE.pop(key, None)
            return None
        _DB_CONTEXT_CACHE.move_to_end(key)
        rec = compact_prev_record(prev_record, drop_empty_item_names=True) if isinstance(prev_record, dict) else None
        return rec, int(db_best_score), int(db_best_fg_score)


def _db_context_cache_put(
    db_key: str, team_buff: str, prev_record: Optional[dict], db_best_score: int, db_best_fg_score: int
) -> None:
    key = _cache_key(db_key, team_buff)
    if not key[0]:
        return
    record_copy = compact_prev_record(prev_record, drop_empty_item_names=True) if isinstance(prev_record, dict) else None
    with _DB_CONTEXT_CACHE_LOCK:
        _DB_CONTEXT_CACHE[key] = (float(time.monotonic()), record_copy, int(db_best_score or 0), int(db_best_fg_score or 0))
        _DB_CONTEXT_CACHE.move_to_end(key)
        while len(_DB_CONTEXT_CACHE) > _DB_CONTEXT_CACHE_MAX:
            _DB_CONTEXT_CACHE.popitem(last=False)


def load_prepared_song_db_context(
    *,
    found_song_name: str,
    cache_db_context: bool = False,
) -> PreparedSongDbContext:
    baseline_team_buff = OPTIMIZER_BASELINE_TEAM_BUFF
    db_key = build_db_key(found_song_name)

    cached = _db_context_cache_get(db_key, baseline_team_buff) if cache_db_context else None
    if cached is not None:
        prev_record, db_best_score, db_best_fg_score = cached
        return PreparedSongDbContext(
            baseline_team_buff=str(baseline_team_buff or "T5"),
            db_key=str(db_key),
            prev_record=prev_record,
            db_best_score=int(db_best_score),
            db_best_fg_score=int(db_best_fg_score),
            db_baseline_valid=True,
        )

    prev_record, db_best_score, db_best_fg_score, db_baseline_valid = load_database_progress_baseline(
        db_key,
        team_buff=str(baseline_team_buff or "T5"),
    )

    if cache_db_context and bool(db_baseline_valid):
        _db_context_cache_put(db_key, baseline_team_buff, prev_record, int(db_best_score), int(db_best_fg_score))

    return PreparedSongDbContext(
        baseline_team_buff=str(baseline_team_buff or "T5"),
        db_key=str(db_key),
        prev_record=prev_record,
        db_best_score=int(db_best_score or 0),
        db_best_fg_score=int(db_best_fg_score or 0),
        db_baseline_valid=bool(db_baseline_valid),
    )
