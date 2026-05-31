from __future__ import annotations

import heapq
from dataclasses import dataclass

from ...core.constants import LOADOUTS_PER_SONG_LIMIT
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


def _center_key(candidate: dict) -> tuple[int, int]:
    data = candidate.get("Data")
    if not isinstance(data, dict):
        data = candidate.get("data")
        if not isinstance(data, dict):
            data = {}
    ft_fallback = safe_int(candidate.get("FT", 0), 0)
    ff_fallback = safe_int(candidate.get("FF", 0), 0)
    ft = safe_int(data.get("FT", ft_fallback), ft_fallback)
    ff = safe_int(data.get("FF", ff_fallback), ff_fallback)
    return int(ft), int(ff)


def _base_score(candidate: dict) -> int:
    v = candidate.get("BaseScore")
    if v is None:
        v = candidate.get("Score", 0)
    return safe_int(v, 0)


def _fg_proxy_from_items(items: list[dict], *, primary_color: str, secondary_color: str) -> int:
    """FG proxy variant that reuses already split gear+mini item lists."""

    def _i(item: dict, key: str) -> int:
        return safe_int((item or {}).get(key, 0), 0)

    score = 0
    for it in items:
        if not isinstance(it, dict) or not it:
            continue
        score += _i(it, "Fever Multiplier") * 4
        score += _i(it, "Fever Fill Rate") * 4
        score += _i(it, "Fever Time") * 3
        score += _i(it, "Combo Multiplier") * 2
        score += _i(it, "Perfect Points")
        if primary_color:
            score += _i(it, primary_color) * 2
        if secondary_color and secondary_color != primary_color:
            score += _i(it, secondary_color)
    return int(score)


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
    Keep one best-base candidate per persisted loadout hash.

    GPU GA dedupes selected rows by exact gear/mini IDs, but DB persistence dedupes
    by song-context effective mini signatures. This selector bridges that contract
    before persistence so 51 raw candidates do not collapse to a tiny DB frontier.
    """
    if not candidates:
        return []
    limit_i = safe_int(limit, 0)
    if limit_i <= 0:
        return []

    best_by_hash: dict[str, dict] = {}
    best_rank_by_hash: dict[str, tuple[int, int, int]] = {}
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
        fg_priority = safe_int(cand.get("_fg_priority", 0), 0)
        # Higher base/priority wins; earlier rows win exact ties to preserve GPU ordering.
        rank = (_base_score(cand), fg_priority, -int(order))
        prev_rank = best_rank_by_hash.get(loadout_hash)
        if prev_rank is None or rank > prev_rank:
            best_by_hash[loadout_hash] = cand
            best_rank_by_hash[loadout_hash] = rank

    unique = list(best_by_hash.values())
    if len(unique) <= limit_i:
        unique.sort(key=_base_score, reverse=True)
        return unique

    return select_fg_candidates(
        unique,
        limit=limit_i,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )


@dataclass(frozen=True)
class _CandMeta:
    cand: dict
    key: tuple[str, ...]
    base: int
    fg_proxy: int
    mini_key: tuple[str, ...]
    center: tuple[int, int]
    fg_priority: int


def _meta_base_key(meta: _CandMeta) -> tuple[int, int, tuple[str, ...]]:
    return meta.base, meta.fg_proxy, meta.key


def _meta_fg_key(meta: _CandMeta) -> tuple[int, int, tuple[str, ...]]:
    return meta.fg_proxy, meta.base, meta.key


def select_fg_candidates(
    candidates: list[dict],
    *,
    limit: int,
    primary_color: str = "",
    secondary_color: str = "",
) -> list[dict]:
    """
    Deterministically compact candidates for persistence/output payloads.

    This is an ordering/retention helper, not an exact FG pruning certificate.
    Production exact FG must keep all effective candidates unless an owning
    `U <= L` certificate removes them before scoring.
    """
    if not candidates:
        return []

    limit = safe_int(limit, 0)
    if limit <= 0:
        return []

    primary_color = str(primary_color or "")
    secondary_color = str(secondary_color or "")

    # 1) Deduplicate by (gear slots, mini set) key; keep the best base-score copy.
    best_by_key: dict[tuple[str, ...], dict] = {}
    best_score_by_key: dict[tuple[str, ...], int] = {}
    split_cache_by_key: dict[tuple[str, ...], tuple[list[dict], list[dict], tuple[str, ...]]] = {}
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        gear, minis = _split_gear_minis(cand)
        gear_names = tuple(_item_name(it) for it in gear)
        mini_key = tuple(sorted(_item_name(it) for it in minis))
        k = gear_names + mini_key
        score = _base_score(cand)
        prev_score = best_score_by_key.get(k)
        if prev_score is None or score > prev_score:
            best_by_key[k] = cand
            best_score_by_key[k] = score
            split_cache_by_key[k] = (gear, minis, mini_key)

    uniq_items = list(best_by_key.items())
    uniq = [cand for _k, cand in uniq_items]
    if len(uniq) <= limit:
        uniq.sort(key=_base_score, reverse=True)
        return uniq

    metas: list[_CandMeta] = []
    for key, cand in uniq_items:
        fg_priority = safe_int(cand.get("_fg_priority", 0), 0)
        gear, minis, mini_key = split_cache_by_key.get(key, ([], [], tuple()))
        fg_proxy = _fg_proxy_from_items(
            list(gear) + list(minis), primary_color=primary_color, secondary_color=secondary_color
        )
        meta = _CandMeta(
            cand=cand,
            key=key,
            base=_base_score(cand),
            fg_proxy=fg_proxy,
            mini_key=mini_key,
            center=_center_key(cand),
            fg_priority=fg_priority,
        )
        metas.append(meta)

    # Deterministic ordering helpers
    # Avoid full sorts for very large funnels; keep deterministic tie-breakers via `m.key`.
    base_pool_k = min(len(metas), max(limit, 20000))
    metas_by_base = heapq.nlargest(base_pool_k, metas, key=_meta_base_key)
    metas_by_fg = heapq.nlargest(base_pool_k, metas, key=_meta_fg_key)

    selected: list[dict] = []
    seen_keys: set[tuple[str, ...]] = set()
    seen_minis: set[tuple[str, ...]] = set()
    seen_centers: set[tuple[int, int]] = set()

    def _add(meta: _CandMeta) -> bool:
        if meta.key in seen_keys:
            return False
        seen_keys.add(meta.key)
        selected.append(meta.cand)
        seen_minis.add(meta.mini_key)
        seen_centers.add(meta.center)
        return True

    # Hard guarantee: keep at least the top-N by base score (DB stability).
    top_base_keep = min(limit, int(LOADOUTS_PER_SONG_LIMIT))
    for meta in metas_by_base:
        if len(selected) >= top_base_keep:
            break
        _add(meta)

    # Preserve a small slice of explicitly marked FG-priority candidates.
    priority_budget = max(0, min(limit - len(selected), max(5, limit // 10)))
    if priority_budget:
        priority = [m for m in metas_by_fg if m.fg_priority]
        for meta in priority:
            if len(selected) >= (top_base_keep + priority_budget):
                break
            _add(meta)

    # Budgets: mix exploitation + FG-proxy + diversity.
    base_budget = min(limit, max(top_base_keep, int(limit * 0.55)))
    fg_budget_end = min(limit, base_budget + int(limit * 0.30))

    # 1) Fill by base score (stable exploitation).
    for meta in metas_by_base:
        if len(selected) >= base_budget:
            break
        _add(meta)

    # 2) Fill by FG proxy; prefer new FT/FF centers first.
    for meta in metas_by_fg:
        if len(selected) >= fg_budget_end:
            break
        if meta.center in seen_centers:
            continue
        _add(meta)
    for meta in metas_by_fg:
        if len(selected) >= fg_budget_end:
            break
        _add(meta)

    # 3) Mini-team diversity fill.
    for meta in metas_by_base:
        if len(selected) >= limit:
            break
        if meta.mini_key in seen_minis:
            continue
        _add(meta)

    # 4) Final fill by base score.
    for meta in metas_by_base:
        if len(selected) >= limit:
            break
        _add(meta)

    return selected[:limit]
