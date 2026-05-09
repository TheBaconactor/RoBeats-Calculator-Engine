from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.core.utils import safe_int
from gear_optimizer.solver.solver_common import GEAR_SLOTS


def _item_stats6(item: dict[str, Any], *, p_color: str, s_color: str) -> np.ndarray:
    pp = int(item.get("Perfect Points", 0) or 0)
    cm = int(item.get("Combo Multiplier", 0) or 0)
    fm = int(item.get("Fever Multiplier", 0) or 0)
    ft = int(item.get("Fever Time", 0) or 0)
    ff = int(item.get("Fever Fill Rate", 0) or 0)
    p_val = int(item.get(p_color, 0) or 0) if p_color else 0
    s_val = int(item.get(s_color, 0) or 0) if s_color and s_color != p_color else 0
    base_lane = (2 * p_val) + s_val
    return np.array((pp, cm, fm, ft, ff, base_lane), dtype=np.int32)


def _read_cfg_int(
    cfg: Any,
    key: str,
    *,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    raw: Any = default
    if cfg is not None:
        try:
            raw = cfg.get("IterationEngine", key, fallback=default)
        except Exception:
            raw = default
    value = safe_int(raw, default)
    return max(int(min_value), min(int(max_value), int(value)))


def read_marginal_prune_settings(cfg: Any) -> dict[str, int]:
    return {
        "k": _read_cfg_int(cfg, "MarginalPruneK", default=3, min_value=1, max_value=12),
        "iterations": _read_cfg_int(cfg, "MarginalPruneIterations", default=5, min_value=1, max_value=20),
    }


def prune_gear_pool_marginal(
    gear_pool: dict[str, list[dict]],
    *,
    p_color: str,
    s_color: str,
) -> dict[str, list[dict]]:
    """Remove per-slot items strictly dominated by another item in the same slot.

    Theorem (Per-Slot Pareto Dominance): For a Minkowski-sum loadout space
    L = G_1 ⊕ ... ⊕ G_6, the Pareto skyline over L is contained in
    skyline(G_1) ⊕ ... ⊕ skyline(G_6). A strictly dominated item in slot k
    can never appear in the globally optimal loadout.

    Proof: Let A ∈ G_k and B ∈ G_k with B dominating A (B ≥ A componentwise,
    strictly > in at least one). For any loadout L containing A, replace A→B.
    All stat coordinates are ≥ original, with at least one strictly >.
    By monotonicity of the score function, score(L') ≥ score(L).
    Therefore A is never strictly optimal. QED.

    Only truly dominated items are removed (B ≥ A on ALL 6 stats and > on at least 1).
    This is strictly stronger than top-K heuristic ranking.
    """
    if not isinstance(gear_pool, dict):
        return {}

    out = {slot: list(gear_pool.get(slot, []) or []) for slot in gear_pool.keys()}
    for slot in GEAR_SLOTS:
        items = list(gear_pool.get(slot, []) or [])
        if not items:
            continue
        stats = np.asarray(
            [_item_stats6(item, p_color=p_color, s_color=s_color) for item in items],
            dtype=np.int32,
        )
        n = int(stats.shape[0])
        keep = np.ones(n, dtype=np.bool_)
        for i in range(n):
            if not keep[i]:
                continue
            si = stats[i]
            ge = np.all(stats >= si, axis=1)
            strict = np.any(stats > si, axis=1)
            ge[i] = False
            if np.any(ge & strict):
                keep[i] = False
        out[slot] = [items[i] for i in range(n) if keep[i]]
    return out
