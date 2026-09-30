from __future__ import annotations

import logging
from typing import Any

from gear_optimizer.gamedata import StatCurves, load_stat_curves
from gear_optimizer.pipeline.post_processor_fg_variants import (
    best_fg_improving_score_from_persist_entries,
    fg_variants_from_persist_entries,
)
from gear_optimizer.settings import paths

logger = logging.getLogger(__name__)


def canonicalize_fg_update_entries(
    entries: list[dict[str, Any]],
    *,
    file_path: str,
    curves: StatCurves | None,
    song_name: str,
) -> list[dict[str, Any]]:
    if not entries:
        return []
    fp = str(file_path or "").strip()
    if not fp:
        logger.warning("[POST][FG] Skipping FG deferred save for %s: missing file_path", song_name)
        return []

    from gear_optimizer.solver.song_preparation import prepare_song

    # The frontier cache keys include the timing model, so FG persistence prepares the song
    # exactly like startup prebuild and GA scoring do (via this same helper).
    song = prepare_song(fp)

    if curves is None:
        curves = load_stat_curves(paths().stats_txt)

    from gear_optimizer.helpers.song_helpers.persistence_authority import canonicalize_authoritative_fg_entries

    # Canonicalization errors (including a missing prebuilt frontier cache) propagate: silently
    # dropping the FG score while the base score persists would hide the failure.
    canonical = canonicalize_authoritative_fg_entries(
        list(entries),
        song=song,
        curves=curves,
    )
    valid: list[dict[str, Any]] = []
    for entry in canonical:
        if not isinstance(entry, dict):
            continue
        fg_score = int(entry.get("fg_score", 0) or 0)
        fg_base_score = int(entry.get("fg_base_score", entry.get("score", 0)) or 0)
        if isinstance(entry.get("force"), dict) and fg_score > fg_base_score:
            valid.append(entry)
    return valid


def build_fg_update_state(
    existing_state: dict[str, Any] | None,
    valid_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    state = dict(existing_state or {})
    state["saw_fg_update"] = True
    state["saved_count"] = len(valid_entries)
    # `fg_score` can equal `score` when the optimal response surface applies no score change.
    # For reporting, treat "best FG" as the best *improving* FG
    # result that has a valid force payload, matching DB `best_fg_score` semantics.
    state["best_fg"] = int(best_fg_improving_score_from_persist_entries(valid_entries))
    state["fg_variants"] = fg_variants_from_persist_entries(valid_entries)
    return state
