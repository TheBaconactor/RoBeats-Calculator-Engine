from __future__ import annotations

import logging
from typing import Any

from gear_optimizer.pipeline.post_processor_fg_variants import (
    best_fg_improving_score_from_persist_entries,
    fg_variants_from_persist_entries,
)

logger = logging.getLogger(__name__)


def canonicalize_fg_update_entries(
    entries: list[dict[str, Any]],
    *,
    file_path: str,
    cfg_dict: dict[str, Any],
    ref_arrays: Any,
    song_name: str,
) -> list[dict[str, Any]]:
    if not entries:
        return []
    fp = str(file_path or "").strip()
    if not fp:
        logger.warning("[POST][FG] Skipping FG deferred save for %s: missing file_path", song_name)
        return []

    cfg_local = dict(cfg_dict) if isinstance(cfg_dict, dict) else {}
    try:
        from gear_optimizer.data.song_io import get_base_calc_song

        calc_song = get_base_calc_song(fp, cfg_local)
    except Exception as exc:
        logger.warning("post_processor_fg_updates:canonicalize_fg_update_entries: %s", exc)
        logger.warning("[POST][FG] Skipping FG deferred save for %s: calc_song load failed", song_name)
        return []
    if not isinstance(calc_song, dict) or not calc_song:
        logger.warning("[POST][FG] Skipping FG deferred save for %s: calc_song unavailable", song_name)
        return []

    resolved_ref_arrays = ref_arrays
    if not (isinstance(resolved_ref_arrays, dict) and resolved_ref_arrays):
        try:
            from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached

            resolved_ref_arrays = _get_team_buff_ref_arrays_cached()
        except Exception as exc:
            logger.warning("post_processor_fg_updates:canonicalize_fg_update_entries: %s", exc)
            resolved_ref_arrays = None
    if not (isinstance(resolved_ref_arrays, dict) and resolved_ref_arrays):
        logger.warning("[POST][FG] Skipping FG deferred save for %s: ref_arrays unavailable", song_name)
        return []

    try:
        from gear_optimizer.helpers.song_helpers.persistence_authority import canonicalize_authoritative_fg_entries

        canonical = canonicalize_authoritative_fg_entries(
            list(entries),
            calc_song=calc_song,
            ref_arrays=resolved_ref_arrays,
        )
        valid: list[dict[str, Any]] = []
        for entry in canonical:
            if not isinstance(entry, dict):
                continue
            try:
                fg_score = int(entry.get("fg_score", 0) or 0)
                fg_base_score = int(entry.get("fg_base_score", entry.get("score", 0)) or 0)
            except Exception as exc:
                raise ValueError(f"invalid canonical FG score fields for {song_name}") from exc
            if isinstance(entry.get("force"), dict) and fg_score > fg_base_score:
                valid.append(entry)
        return valid
    except Exception as exc:
        logger.warning(
            "[POST][FG] Skipping FG deferred save for %s: canonicalization failed (%s: %s)",
            song_name,
            type(exc).__name__,
            exc,
        )
        return []


def build_fg_update_state(
    existing_state: dict[str, Any] | None,
    valid_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    state = dict(existing_state or {})
    state["saw_fg_update"] = True
    state["saved_count"] = len(valid_entries)
    # `fg_score` can equal `score` when the optimal FG config is "no forced greats"
    # (config all zeros). For reporting, treat "best FG" as the best *improving* FG
    # result that has a valid force payload, matching DB `best_fg_score` semantics.
    state["best_fg"] = int(best_fg_improving_score_from_persist_entries(valid_entries))
    state["fg_variants"] = fg_variants_from_persist_entries(valid_entries)
    return state
