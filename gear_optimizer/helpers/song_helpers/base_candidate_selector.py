from __future__ import annotations

from ...core.utils import safe_int
from .loadout_entry_utils import candidate_loadout_hash


def _base_score(candidate: dict) -> int:
    value = candidate.get("BaseScore")
    if value is None:
        value = candidate.get("Score", 0)
    return safe_int(value, 0)


def select_top_base_candidates(
    candidates: list[dict],
    *,
    limit: int,
    registry: object = None,
    minis_by_name: dict[str, dict] | None = None,
    primary_color: str = "",
    secondary_color: str = "",
    selected_color: str = "",
) -> list[dict]:
    """Keep the top exact Base scores after effective-loadout deduplication."""

    if not candidates:
        return []
    limit_i = safe_int(limit, 0)
    if limit_i <= 0:
        return []

    best_by_hash: dict[str, dict] = {}
    best_rank_by_hash: dict[str, tuple[int, int]] = {}
    for order, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        loadout_hash = candidate_loadout_hash(
            candidate,
            registry=registry,
            minis_by_name=minis_by_name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            selected_color=selected_color,
            mutate=False,
        )
        if not loadout_hash:
            continue
        rank = (_base_score(candidate), -int(order))
        previous_rank = best_rank_by_hash.get(loadout_hash)
        if previous_rank is None or rank > previous_rank:
            best_by_hash[loadout_hash] = candidate
            best_rank_by_hash[loadout_hash] = rank

    rows = [(loadout_hash, candidate) for loadout_hash, candidate in best_by_hash.items()]
    rows.sort(key=lambda item: (_base_score(item[1]), item[0]), reverse=True)
    return [candidate for _key, candidate in rows[:limit_i]]
