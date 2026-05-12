from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _int_or_zero(value: Any, *, context: str) -> int:
    try:
        return int(value or 0)
    except Exception as exc:
        logger.warning("post_processor_fg_variants:%s: %s", context, exc)
        return 0


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

        fg_score = _int_or_zero(variant.get("fg_score", 0), context="best_fg_improving_score_from_variants")
        base_score = variant.get("base_score")
        if base_score is None:
            base_score = variant.get("score", 0)
        base_score_i = _int_or_zero(base_score, context="best_fg_improving_score_from_variants")
        if fg_score <= base_score_i:
            continue
        if fg_score > best:
            best = fg_score
    return int(best)


def best_fg_improving_score_from_persist_entries(entries: list[dict[str, Any]] | None) -> int:
    best = 0
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        score = _int_or_zero(entry.get("score", 0), context="best_fg_improving_score_from_persist_entries")
        fg_score = _int_or_zero(entry.get("fg_score", 0), context="best_fg_improving_score_from_persist_entries")
        if fg_score <= score:
            continue
        if not entry.get("force"):
            continue
        if fg_score > best:
            best = fg_score
    return int(best)


def fg_variants_from_persist_entries(entries: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        details = entry.get("details") or {}
        if not isinstance(details, dict):
            details = {}
        fg_score = _int_or_zero(entry.get("fg_score", 0), context="fg_variants_from_persist_entries")
        base_score = _int_or_zero(entry.get("score", 0), context="fg_variants_from_persist_entries")
        data = dict(details)
        data["Score"] = fg_score or base_score
        variants.append(
            {
                "data": data,
                "gear": entry.get("gear") or [],
                "minis": entry.get("minis") or [],
                "score": base_score,
                "fg_score": fg_score,
                "_is_ga": bool(entry.get("_is_ga")),
            }
        )
    return variants
