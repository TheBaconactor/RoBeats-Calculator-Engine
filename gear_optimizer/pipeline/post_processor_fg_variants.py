from __future__ import annotations

from typing import Any

from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_payload import has_valid_fg_payload, require_response_surface


def best_fg_improving_score_from_variants(variants: list[dict[str, Any]] | None) -> int:
    best = 0
    for variant in variants or []:
        if not isinstance(variant, dict):
            continue
        data = variant.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        if not has_valid_fg_payload(data):
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


def best_fg_improving_score_from_persist_entries(entries: list[dict[str, Any]] | None) -> int:
    best = 0
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        score = safe_int(entry.get("score", 0))
        fg_score = safe_int(entry.get("fg_score", 0))
        if fg_score <= score:
            continue
        if not has_valid_fg_payload(entry.get("force")):
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
        fg_score = safe_int(entry.get("fg_score", 0))
        base_score = safe_int(entry.get("score", 0))
        data = dict(details)
        force = entry.get("force")
        if has_valid_fg_payload(force):
            data["response_surface"] = list(require_response_surface(force))
            force_meta = force.get("ForceGreats") if isinstance(force, dict) else None
            if isinstance(force_meta, dict):
                data["ForceGreats"] = dict(force_meta)
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
