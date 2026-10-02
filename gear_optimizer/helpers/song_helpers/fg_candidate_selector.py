from __future__ import annotations

from ...gamedata import SongMini
from .ga_entry_utils import candidate_loadout_hash


def select_top_base_ga_candidates(
    candidates: list[dict],
    *,
    limit: int,
    registry: object = None,
    minis_by_name: dict[str, SongMini] | None = None,
    primary_color: str = "",
    secondary_color: str = "",
    selected_color: str = "",
) -> list[dict]:
    """The top `limit` GA candidates by base score (their BaseScore) after the effective-loadout dedupe."""
    if not candidates or limit <= 0:
        return []

    best_by_hash: dict[str, dict] = {}
    best_rank_by_hash: dict[str, tuple[int, int]] = {}
    for order, cand in enumerate(candidates):
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
        rank = (cand["BaseScore"], -order)
        prev_rank = best_rank_by_hash.get(loadout_hash)
        if prev_rank is None or rank > prev_rank:
            best_by_hash[loadout_hash] = cand
            best_rank_by_hash[loadout_hash] = rank

    rows = [(loadout_hash, cand) for loadout_hash, cand in best_by_hash.items()]
    rows.sort(key=lambda item: (item[1]["BaseScore"], item[0]), reverse=True)
    return [cand for _key, cand in rows[:limit]]
