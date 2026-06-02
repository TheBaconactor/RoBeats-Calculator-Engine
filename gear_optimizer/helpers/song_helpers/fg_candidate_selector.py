from __future__ import annotations

from ...core.utils import safe_int
from .ga_entry_utils import candidate_loadout_hash


def _base_score(candidate: dict) -> int:
    v = candidate.get("BaseScore")
    if v is None:
        v = candidate.get("Score", 0)
    return safe_int(v, 0)


def select_top_base_ga_candidates(
    candidates: list[dict],
    *,
    limit: int,
    registry: object = None,
    minis_by_name: dict[str, dict] | None = None,
    primary_color: str = "",
    secondary_color: str = "",
    selected_color: str = "",
) -> list[dict]:
    """
    Keep the configured top base-score candidates after effective-loadout dedupe.
    """
    if not candidates:
        return []
    limit_i = safe_int(limit, 0)
    if limit_i <= 0:
        return []

    best_by_hash: dict[str, dict] = {}
    best_rank_by_hash: dict[str, tuple[int, int]] = {}
    for order, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue
        loadout_hash = candidate_loadout_hash(
            cand,
            registry=registry,
            minis_by_name=minis_by_name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            selected_color=selected_color,
            mutate=False,
        )
        if not loadout_hash:
            continue
        # Higher base wins; earlier rows win exact ties to preserve GPU ordering.
        rank = (_base_score(cand), -int(order))
        prev_rank = best_rank_by_hash.get(loadout_hash)
        if prev_rank is None or rank > prev_rank:
            best_by_hash[loadout_hash] = cand
            best_rank_by_hash[loadout_hash] = rank

    rows = [(loadout_hash, cand) for loadout_hash, cand in best_by_hash.items()]
    rows.sort(key=lambda item: (_base_score(item[1]), item[0]), reverse=True)
    return [cand for _key, cand in rows[:limit_i]]
