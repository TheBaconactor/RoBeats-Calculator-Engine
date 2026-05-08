from __future__ import annotations

from collections.abc import Callable
from typing import Any
import logging



logger = logging.getLogger(__name__)
def select_retained_hashes(
    items: list[tuple[Any, dict]],
    *,
    limit: int,
    base_score_fn: Callable[[dict], int],
    fg_score_fn: Callable[[dict], int],
    fg_valid_fn: Callable[[dict], bool],
) -> set[str]:
    n = max(0, int(limit))
    if not items or n <= 0:
        return set()

    top_base = sorted(items, key=lambda kv: int(base_score_fn(kv[1]) or 0), reverse=True)[:n]

    fg_candidates: list[tuple[Any, dict]] = []
    for h, e in items:
        try:
            base_s = int(base_score_fn(e) or 0)
            fg_s = int(fg_score_fn(e) or 0)
            if fg_s <= base_s:
                continue
            if not fg_valid_fn(e):
                continue
            fg_candidates.append((h, e))
        except Exception as e:
            logger.debug(f"retention:select_retained_hashes: {e}")
            continue

    top_fg = sorted(fg_candidates, key=lambda kv: int(fg_score_fn(kv[1]) or 0), reverse=True)[:n]

    retained: set[str] = set()
    for h, _e in list(top_base) + list(top_fg):
        retained.add(str(h))
    return retained
