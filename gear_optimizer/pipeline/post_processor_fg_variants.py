from __future__ import annotations

from typing import Any

from gear_optimizer.core.utils import safe_int


def _force_greats_config_total(data: dict[str, Any]) -> int:
    fg_meta = data.get("ForceGreats") or {}
    if not isinstance(fg_meta, dict):
        return 0
    cfg = fg_meta.get("config") or {}
    if not isinstance(cfg, dict):
        return 0
    return sum(int(value) if isinstance(value, (int, float)) else 0 for value in cfg.values())


def best_fg_improving_score_from_variants(variants: list[dict[str, Any]] | None) -> int:
    best = 0
    for variant in variants or []:
        if not isinstance(variant, dict):
            continue
        data = variant.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        if _force_greats_config_total(data) <= 0:
            continue

        fg_score = safe_int(variant.get("fg_score", 0))
        base_score = variant.get("base_score")
        if base_score is None:
            base_score = variant.get("score", 0)
        base_score_i = safe_int(base_score)
        if fg_score <= base_score_i:
            continue
        if fg_score > best:
            best = fg_score
    return int(best)
