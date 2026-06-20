from __future__ import annotations

from typing import Any, Iterable

from gear_optimizer.core.utils import safe_int


def force_score_hint(entry: dict[str, Any]) -> int:
    force_obj = entry.get("force")
    if not isinstance(force_obj, dict):
        return 0
    score = safe_int(force_obj.get("score", 0))
    if score > 0:
        return score
    details = force_obj.get("details") or {}
    if not isinstance(details, dict):
        return 0
    force_greats = details.get("ForceGreats") or {}
    if not isinstance(force_greats, dict):
        return 0
    return safe_int(force_greats.get("final_score", 0))


def is_valid_persistence_entry(
    entry: Any,
    *,
    require_base_score: bool = True,
    accept_force_score_hint: bool = False,
) -> bool:
    if not isinstance(entry, dict):
        return False
    if not (entry.get("gear") or entry.get("minis")):
        return False
    score = safe_int(entry.get("score", 0))
    if require_base_score:
        return score > 0
    fg_score = safe_int(entry.get("fg_score", 0))
    force_score = force_score_hint(entry) if accept_force_score_hint else 0
    return max(score, fg_score, force_score) > 0


def filter_valid_persistence_entries(
    entries: Iterable[Any] | None,
    *,
    require_base_score: bool = True,
    accept_force_score_hint: bool = False,
) -> list[dict[str, Any]]:
    return [
        entry
        for entry in (entries or [])
        if is_valid_persistence_entry(
            entry,
            require_base_score=bool(require_base_score),
            accept_force_score_hint=bool(accept_force_score_hint),
        )
    ]
