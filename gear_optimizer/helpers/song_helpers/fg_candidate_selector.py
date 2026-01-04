from __future__ import annotations

from ...core.constants import LOADOUTS_PER_SONG_LIMIT


def _item_name(item) -> str:
    if isinstance(item, dict):
        return str(item.get("Name", "") or "")
    return str(item) if item else ""


def _split_gear_minis(candidate: dict) -> tuple[list[dict], list[dict]]:
    genome = candidate.get("Genome")
    if isinstance(genome, list) and genome:
        gear = list(genome[:6])
        minis = list(genome[6:9])
        return gear, minis
    gear = list(candidate.get("Gear") or [])[:6]
    minis = list(candidate.get("Minis") or [])[:3]
    return gear, minis


def _gear_mini_key(candidate: dict) -> tuple[str, ...]:
    gear, minis = _split_gear_minis(candidate)
    gear_names = tuple(_item_name(it) for it in gear)
    mini_names = tuple(sorted(_item_name(it) for it in minis))
    return gear_names + mini_names


def _base_score(candidate: dict) -> int:
    v = candidate.get("BaseScore")
    if v is None:
        v = candidate.get("Score", 0)
    try:
        return int(v or 0)
    except Exception:
        return 0


def select_fg_candidates(
    candidates: list[dict],
    *,
    limit: int,
    primary_color: str = "",
    secondary_color: str = "",
    mode: str = "default",
    promising_band_pct: float = 1.0,
    promising_max_pool: int = 20000,
    promising_per_mini: int = 6,
    promising_per_center: int = 6,
    promising_center_bin: int = 2,
) -> list[dict]:
    """
    Pick a bounded candidate funnel for ForceGreatsFinder.

    Minimal behavior: dedupe by (gear, minis) and keep the top `limit` by base score.

    Args:
        candidates: GA/DB candidate dicts
        limit: max number of candidates returned

    Notes:
        - All extra args are accepted for backwards compatibility but ignored.
        - Deterministic tie-breaking is done via (score desc, key desc).
    """
    if not candidates:
        return []

    try:
        limit = int(limit)
    except Exception:
        limit = 0
    if limit <= 0:
        return []

    _ = (
        primary_color,
        secondary_color,
        mode,
        promising_band_pct,
        promising_max_pool,
        promising_per_mini,
        promising_per_center,
        promising_center_bin,
    )

    # Keep the best-scoring instance per unique (gear, minis) key.
    best_by_key: dict[tuple[str, ...], tuple[int, dict]] = {}
    for cand in candidates:
        if not isinstance(cand, dict) or not cand:
            continue
        key = _gear_mini_key(cand)
        score = _base_score(cand)
        prev = best_by_key.get(key)
        if prev is None or score > prev[0]:
            best_by_key[key] = (score, cand)

    uniq = [(score, key, cand) for key, (score, cand) in best_by_key.items()]
    if not uniq:
        return []

    uniq.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [cand for _score, _key, cand in uniq[: max(int(LOADOUTS_PER_SONG_LIMIT), limit)]][:limit]
