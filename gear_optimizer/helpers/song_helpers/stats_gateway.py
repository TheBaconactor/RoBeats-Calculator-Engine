"""
Single-source-of-truth gateway for stats computation and inspection.

All variants of "ensure stats exist" converge here so behaviour is
deterministic and auditable from one module.
"""

from __future__ import annotations

from typing import Any, Callable


def details_have_stats(details_obj: Any) -> bool:
    if not isinstance(details_obj, dict) or not details_obj:
        return False
    stats_obj = details_obj.get("Stats")
    return isinstance(stats_obj, dict) and bool(stats_obj)


def ensure_stats(
    details_obj: Any,
    *,
    build_details_fn: Callable[[dict], dict] | None = None,
    eval_data: Any = None,
    force_fail: bool = False,
) -> Any:
    """
    Unified decision tree for ensuring Stats exist on a details dict.

    1. If *details_obj* already carries a valid ``"Stats"`` dict -> return unchanged.
    2. If *build_details_fn* is provided and can rebuild from *eval_data* -> return rebuilt details.
    3. If *force_fail* is True -> raise ``ValueError`` (persistence-canon strict path).
    4. Otherwise -> return *details_obj* as-is (legacy compat for database.py paths
       that do their own heavyweight reconstruction later).
    """
    if details_have_stats(details_obj):
        return details_obj

    if build_details_fn is not None and isinstance(eval_data, dict) and eval_data:
        rebuilt = build_details_fn(eval_data)
        if details_have_stats(rebuilt):
            return rebuilt

    if force_fail:
        raise ValueError(
            "Persistence canonicalization received an entry without replayable Stats."
        )

    return details_obj


def ensure_stats_include_base_effect(stats: dict, base_effect: dict[str, int]) -> dict:
    """
    Ensure *stats* includes the base TeamBuff effect when tiering is expressed as deltas vs base.

    Heuristic: if Perfect Points is less than the base PP add, treat the stats as missing
    TeamBuff and add the base effect.
    """
    if not isinstance(stats, dict) or not stats or not isinstance(base_effect, dict) or not base_effect:
        return stats if isinstance(stats, dict) else {}
    from ...core.utils import safe_int as _safe_int
    base_pp = _safe_int(base_effect.get("Perfect Points", 0), 0)
    if base_pp <= 0:
        return dict(stats)
    pp0 = _safe_int(stats.get("Perfect Points", 0), 0)
    if pp0 < base_pp:
        from .team_buff_tiers import _apply_stat_delta
        return _apply_stat_delta(stats, base_effect)
    return dict(stats)
