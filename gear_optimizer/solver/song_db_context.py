from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from gear_optimizer.helpers.song_helpers.database_context import (
    build_db_key,
    load_database_progress_baseline,
    resolve_database_baseline_team_buff,
)
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_prev_record

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedSongDbContext:
    baseline_team_buff: str
    db_key: str
    prev_record: Optional[dict]
    db_best_score: int
    db_best_fg_score: int
    attempt_lifetime: int
    attempts_first: int
    prev_attempts_first: int
    db_baseline_valid: bool


_DB_CONTEXT_CACHE_LOCK = threading.Lock()
_DB_CONTEXT_CACHE: "OrderedDict[tuple[str, str], tuple[float, Optional[dict], int, int, int, int]]" = OrderedDict()


def _db_context_cache_max() -> int:
    return 1024


def _db_context_cache_ttl_s() -> float:
    return 1.0


def _cache_key(db_key: str, team_buff: str) -> tuple[str, str]:
    return (str(db_key or "").strip(), str(team_buff or "T5").strip().upper() or "T5")


def _db_context_cache_get(
    db_key: str,
    team_buff: str,
) -> tuple[Optional[dict], int, int, int, int] | None:
    key = _cache_key(db_key, team_buff)
    if not key[0]:
        return None
    ttl_s = float(_db_context_cache_ttl_s())
    try:
        with _DB_CONTEXT_CACHE_LOCK:
            entry = _DB_CONTEXT_CACHE.get(key)
            if entry is None:
                return None
            ts, prev_record, db_best_score, db_best_fg_score, attempt_lifetime, prev_attempts_first = entry
            if ttl_s > 0.0 and (time.monotonic() - float(ts)) > ttl_s:
                _DB_CONTEXT_CACHE.pop(key, None)
                return None
            _DB_CONTEXT_CACHE.move_to_end(key)
            rec = compact_prev_record(prev_record, drop_empty_item_names=True) if isinstance(prev_record, dict) else None
            return rec, int(db_best_score), int(db_best_fg_score), int(attempt_lifetime), int(prev_attempts_first)
    except Exception as e:
        logger.debug(f"song_db_context:_db_context_cache_get: {e}")
        return None


def _db_context_cache_put(
    db_key: str,
    team_buff: str,
    prev_record: Optional[dict],
    db_best_score: int,
    db_best_fg_score: int,
    attempt_lifetime: int,
    prev_attempts_first: int,
) -> None:
    key = _cache_key(db_key, team_buff)
    if not key[0]:
        return
    try:
        record_copy = compact_prev_record(prev_record, drop_empty_item_names=True) if isinstance(prev_record, dict) else None
        with _DB_CONTEXT_CACHE_LOCK:
            _DB_CONTEXT_CACHE[key] = (
                float(time.monotonic()),
                record_copy,
                int(db_best_score or 0),
                int(db_best_fg_score or 0),
                int(attempt_lifetime or 0),
                int(prev_attempts_first or 0),
            )
            _DB_CONTEXT_CACHE.move_to_end(key)
            max_n = int(_db_context_cache_max())
            if max_n <= 0:
                _DB_CONTEXT_CACHE.clear()
                return
            while len(_DB_CONTEXT_CACHE) > max_n:
                _DB_CONTEXT_CACHE.popitem(last=False)
    except Exception as e:
        logger.debug(f"song_db_context:_db_context_cache_put: {e}")


def load_prepared_song_db_context(
    *,
    found_song_name: str,
    calc_song: dict | None,
    cfg: Any | None,
    cfg_dict: Mapping[str, Any] | None,
    gears_by_name: dict,
    minis_by_name: dict,
    allow_fallback: bool,
    cache_db_context: bool = False,
) -> PreparedSongDbContext:
    baseline_team_buff = resolve_database_baseline_team_buff(cfg, cfg_dict=cfg_dict)
    db_key = build_db_key(found_song_name, calc_song)

    cached = None
    if cache_db_context:
        cached = _db_context_cache_get(db_key, baseline_team_buff)
    if cached is not None:
        prev_record, db_best_score, db_best_fg_score, attempt_lifetime, prev_attempts_first = cached
        return PreparedSongDbContext(
            baseline_team_buff=str(baseline_team_buff or "T5"),
            db_key=str(db_key),
            prev_record=prev_record,
            db_best_score=int(db_best_score),
            db_best_fg_score=int(db_best_fg_score),
            attempt_lifetime=int(attempt_lifetime),
            attempts_first=(int(prev_attempts_first) + 1) if int(prev_attempts_first or 0) else 1,
            prev_attempts_first=int(prev_attempts_first),
            db_baseline_valid=True,
        )

    (
        prev_record,
        db_best_score,
        db_best_fg_score,
        attempt_lifetime,
        prev_attempts_first,
        db_baseline_valid,
    ) = load_database_progress_baseline(
        db_key,
        gears_by_name,
        minis_by_name,
        allow_fallback=bool(allow_fallback),
        team_buff=str(baseline_team_buff or "T5"),
    )

    if cache_db_context and bool(db_baseline_valid):
        _db_context_cache_put(
            db_key,
            baseline_team_buff,
            prev_record,
            int(db_best_score),
            int(db_best_fg_score),
            int(attempt_lifetime),
            int(prev_attempts_first),
        )

    return PreparedSongDbContext(
        baseline_team_buff=str(baseline_team_buff or "T5"),
        db_key=str(db_key),
        prev_record=prev_record,
        db_best_score=int(db_best_score or 0),
        db_best_fg_score=int(db_best_fg_score or 0),
        attempt_lifetime=int(attempt_lifetime or 0),
        attempts_first=(int(prev_attempts_first or 0) + 1) if int(prev_attempts_first or 0) else 1,
        prev_attempts_first=int(prev_attempts_first or 0),
        db_baseline_valid=bool(db_baseline_valid),
    )
