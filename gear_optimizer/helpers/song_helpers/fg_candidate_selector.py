from __future__ import annotations

from dataclasses import dataclass

from ...core.constants import LOADOUTS_PER_SONG_LIMIT


def _item_name(item) -> str:
    if isinstance(item, dict):
        return str(item.get("Name", "") or "")
    return str(item) if item else ""


def _gear_mini_key(candidate: dict) -> tuple[str, ...]:
    gear = candidate.get("Gear") or []
    minis = candidate.get("Minis") or []
    gear_names = tuple(_item_name(it) for it in gear)
    mini_names = tuple(sorted(_item_name(it) for it in minis))
    return gear_names + mini_names


def _mini_key(candidate: dict) -> tuple[str, ...]:
    minis = candidate.get("Minis") or []
    return tuple(sorted(_item_name(it) for it in minis))


def _center_key(candidate: dict) -> tuple[int, int]:
    data = candidate.get("Data") or {}
    ft = data.get("FT", candidate.get("FT", 0) or 0) or 0
    ff = data.get("FF", candidate.get("FF", 0) or 0) or 0
    try:
        return int(ft), int(ff)
    except Exception:
        return 0, 0


def _base_score(candidate: dict) -> int:
    v = candidate.get("BaseScore")
    if v is None:
        v = candidate.get("Score", 0)
    try:
        return int(v or 0)
    except Exception:
        return 0


def _fg_proxy(candidate: dict, *, primary_color: str, secondary_color: str) -> int:
    """
    Proxy for FG potential.

    This is intentionally simple and uses readily-available stats; it is NOT an FG score.
    """
    items = list(candidate.get("Gear") or []) + list(candidate.get("Minis") or [])

    def _i(item: dict, key: str) -> int:
        try:
            return int((item or {}).get(key, 0) or 0)
        except Exception:
            return 0

    score = 0
    for it in items:
        if not it:
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


@dataclass(frozen=True)
class _CandMeta:
    cand: dict
    key: tuple[str, ...]
    base: int
    fg_proxy: int
    mini_key: tuple[str, ...]
    center: tuple[int, int]
    fg_priority: int


def select_fg_candidates(
    candidates: list[dict],
    *,
    limit: int,
    primary_color: str = "",
    secondary_color: str = "",
) -> list[dict]:
    """
    Pick a bounded candidate funnel for ForceGreatsFinder.

    Goal: keep the best base-score candidates (for DB/leaderboard stability) while also
    retaining candidates with high fever potential that may only become optimal once
    ForceGreats is applied.
    """
    if not candidates:
        return []

    try:
        limit = int(limit)
    except Exception:
        limit = 0
    if limit <= 0:
        return []

    primary_color = str(primary_color or "")
    secondary_color = str(secondary_color or "")

    # 1) Deduplicate by (gear slots, mini set) key; keep the best base-score copy.
    best_by_key: dict[tuple[str, ...], dict] = {}
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        k = _gear_mini_key(cand)
        prev = best_by_key.get(k)
        if prev is None:
            best_by_key[k] = cand
            continue
        if _base_score(cand) > _base_score(prev):
            best_by_key[k] = cand

    uniq = list(best_by_key.values())
    if len(uniq) <= limit:
        uniq.sort(key=_base_score, reverse=True)
        return uniq

    metas: list[_CandMeta] = []
    for cand in uniq:
        try:
            fg_priority = int(cand.get("_fg_priority", 0) or 0)
        except Exception:
            fg_priority = 0
        meta = _CandMeta(
            cand=cand,
            key=_gear_mini_key(cand),
            base=_base_score(cand),
            fg_proxy=_fg_proxy(cand, primary_color=primary_color, secondary_color=secondary_color),
            mini_key=_mini_key(cand),
            center=_center_key(cand),
            fg_priority=fg_priority,
        )
        metas.append(meta)

    # Deterministic ordering helpers
    metas_by_base = sorted(metas, key=lambda m: (m.base, m.fg_proxy), reverse=True)
    metas_by_fg = sorted(metas, key=lambda m: (m.fg_proxy, m.base), reverse=True)

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
