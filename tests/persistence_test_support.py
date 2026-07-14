from __future__ import annotations

from collections.abc import Callable

from gear_optimizer.helpers.song_helpers.persistence_canon import _collect_raw_entries, _dedupe_entries


def assemble_without_replay(
    *,
    db_payload: dict,
    ga_candidates: list[dict] | None,
    loadout_entries: dict | None,
    build_details_fn: Callable[[dict], dict],
) -> list[dict]:
    """Exercise persistence collection/dedup without the production replay gateway."""
    raw_entries = _collect_raw_entries(
        db_payload=db_payload if isinstance(db_payload, dict) else {},
        ga_candidates=ga_candidates,
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
    )
    return _dedupe_entries(raw_entries)
