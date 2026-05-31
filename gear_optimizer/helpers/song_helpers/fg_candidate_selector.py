from __future__ import annotations

from ...core.utils import safe_int
from .ga_entry_utils import candidate_loadout_hash
from .item_utils import _item_name


def _split_gear_minis(candidate: dict) -> tuple[list[dict], list[dict]]:
    """
    Robustly extract (gear, minis) from historical candidate shapes.

    Supported shapes:
    - {"Gear": [...], "Minis": [...]}
    - {"Genome": [...]} where first 6 are gear and next 3 are minis.
    """
    genome = candidate.get("Genome")
    if isinstance(genome, list) and genome:
        gear = list(genome[:6])
        minis = list(genome[6:9])
        return gear, minis
    gear = list(candidate.get("Gear") or [])[:6]
    minis = list(candidate.get("Minis") or [])[:3]
    return gear, minis


def _base_score(candidate: dict) -> int:
    v = candidate.get("BaseScore")
    if v is None:
        v = candidate.get("Score", 0)
    return safe_int(v, 0)


def _candidate_key(candidate: dict) -> tuple[str, ...]:
    gear, minis = _split_gear_minis(candidate)
    gear_names = tuple(_item_name(it) for it in gear)
    mini_key = tuple(sorted(_item_name(it) for it in minis))
    return gear_names + mini_key


def select_effective_unique_ga_candidates(
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
            mutate=True,
        )
        if not loadout_hash:
            continue
        # Higher base wins; earlier rows win exact ties to preserve GPU ordering.
        rank = (_base_score(cand), -int(order))
        prev_rank = best_rank_by_hash.get(loadout_hash)
        if prev_rank is None or rank > prev_rank:
            best_by_hash[loadout_hash] = cand
            best_rank_by_hash[loadout_hash] = rank

    unique = list(best_by_hash.values())
    return select_fg_candidates(
        unique,
        limit=limit_i,
    )


def select_fg_candidates(
    candidates: list[dict],
    *,
    limit: int,
) -> list[dict]:
    """
    Deterministically retain the configured top base-score concrete loadouts.
    """
    if not candidates:
        return []

    limit_i = safe_int(limit, 0)
    if limit_i <= 0:
        return []

    best_by_key: dict[tuple[str, ...], dict] = {}
    best_rank_by_key: dict[tuple[str, ...], tuple[int, int]] = {}
    for order, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue
        key = _candidate_key(cand)
        rank = (_base_score(cand), -int(order))
        prev_rank = best_rank_by_key.get(key)
        if prev_rank is None or rank > prev_rank:
            best_by_key[key] = cand
            best_rank_by_key[key] = rank

    rows = [(key, cand) for key, cand in best_by_key.items()]
    rows.sort(key=lambda item: (_base_score(item[1]), item[0]), reverse=True)
    return [cand for _key, cand in rows[:limit_i]]
