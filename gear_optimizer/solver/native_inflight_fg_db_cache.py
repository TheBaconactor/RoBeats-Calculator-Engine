from __future__ import annotations

import logging
import threading
from collections import OrderedDict

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)

_FG_DB_LOADOUTS_CACHE: "OrderedDict[tuple[str, str], tuple[int, list[dict]]]" = OrderedDict()
_FG_DB_LOADOUTS_CACHE_LOCK = threading.Lock()


def fg_db_cache_max() -> int:
    try:
        raw = env_get("INFLIGHT_FG_DB_CACHE_MAX")
        if raw is not None and str(raw).strip() != "":
            return max(0, int(raw))
    except (ValueError, TypeError):
        pass
    return 256


def fg_db_cache_get(song_name: str, *, limit: int, team_buff: str = "T5") -> list[dict] | None:
    song_key = str(song_name or "").strip()
    if not song_key:
        return None
    tier_key = str(team_buff or "T5").strip().upper() or "T5"
    key = (song_key, tier_key)
    try:
        with _FG_DB_LOADOUTS_CACHE_LOCK:
            entry = _FG_DB_LOADOUTS_CACHE.get(key)
            if entry is None:
                return None
            cached_limit, rows = entry
            if int(cached_limit) < int(limit):
                return None
            _FG_DB_LOADOUTS_CACHE.move_to_end(key)
            return list(rows[: int(limit)])
    except (KeyError, TypeError, ValueError):
        return None


def fg_db_cache_put(song_name: str, *, limit: int, rows: list[dict], team_buff: str = "T5") -> None:
    song_key = str(song_name or "").strip()
    if not song_key:
        return
    tier_key = str(team_buff or "T5").strip().upper() or "T5"
    key = (song_key, tier_key)
    if not isinstance(rows, list):
        return
    try:
        limit_i = max(0, int(limit))
    except (ValueError, TypeError):
        limit_i = 0
    try:
        with _FG_DB_LOADOUTS_CACHE_LOCK:
            prev = _FG_DB_LOADOUTS_CACHE.get(key)
            if prev is not None:
                prev_limit, _prev_rows = prev
                # Keep the wider payload for this song key when possible.
                if int(prev_limit) > int(limit_i):
                    return
            _FG_DB_LOADOUTS_CACHE[key] = (int(limit_i), list(rows))
            _FG_DB_LOADOUTS_CACHE.move_to_end(key)
            max_n = int(fg_db_cache_max())
            if max_n <= 0:
                _FG_DB_LOADOUTS_CACHE.clear()
                return
            while len(_FG_DB_LOADOUTS_CACHE) > max_n:
                _FG_DB_LOADOUTS_CACHE.popitem(last=False)
    except (KeyError, TypeError, ValueError):
        return


def prefetch_db_loadouts_sync(
    song_name: str,
    *,
    limit: int,
    gears_by_name: dict,
    minis_by_name: dict,
    team_buff: str = "T5",
) -> list[dict]:
    try:
        limit_i = max(0, int(limit))
    except (ValueError, TypeError):
        limit_i = 0
    cached = fg_db_cache_get(song_name, limit=limit_i, team_buff=str(team_buff or "T5"))
    if cached is not None:
        return cached

    try:
        from gear_optimizer.data.database import get_best_loadouts

        rows = get_best_loadouts(
            song_name,
            limit=limit_i,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            team_buff=str(team_buff or "T5"),
        )
        if isinstance(rows, list):
            fg_db_cache_put(song_name, limit=limit_i, rows=rows, team_buff=str(team_buff or "T5"))
            return rows
        return []
    except Exception as e:
        logger.debug(f"native_inflight_fg_db_cache:prefetch_db_loadouts_sync: {e}")
        return []
