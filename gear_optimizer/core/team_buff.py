from __future__ import annotations
import logging

"""
TeamBuff helpers (tier definitions, normalization, and baseline resolution).

We persist/load baseline candidates under a single TeamBuff tier per run. In auto mode
(`AutoSelectBuffAndColor=true`), runtime semantics force TeamBuff=T5 regardless of the
configured TeamContributionBuffConstant.TeamBuff value.

This module centralizes:
- tier normalization
- shared TeamBuff stat deltas
- resolving the baseline TeamBuff from either a cfg_dict or configparser-like object
"""

from typing import Any, Mapping, Sequence

import configparser

from .config import read_iteration_engine_settings
from .parsing import truthy


logger = logging.getLogger(__name__)
TEAM_BUFF_TIER_EFFECTS: dict[str, dict[str, int]] = {
    "NONE": {"PP": 0, "Elem": 0},
    "T1": {"PP": 25, "Elem": 35},
    "T5": {"PP": 25, "Elem": 30},
    "T10": {"PP": 20, "Elem": 25},
    "T20": {"PP": 15, "Elem": 20},
    "T50": {"PP": 10, "Elem": 15},
    # Rank 51+ stays a real TeamBuff tier; `NONE` remains the true zero-effect view.
    "T51": {"PP": 5, "Elem": 10},
}
TEAM_BUFF_TIER_ORDER: tuple[str, ...] = ("NONE", "T1", "T5", "T10", "T20", "T50", "T51")
TEAM_BUFF_ELEMENTS: tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")

CANONICAL_TEAM_BUFF_TIERS: frozenset[str] = frozenset(TEAM_BUFF_TIER_EFFECTS)
DEFAULT_TEAM_BUFF_REPLAY_TIERS: tuple[str, ...] = TEAM_BUFF_TIER_ORDER


def canonicalize_team_buff(value: Any) -> str:
    """Return the canonical TeamBuff key, or ``""`` when unknown."""
    s = str(value or "").strip().upper()
    if not s:
        return ""
    return s if s in CANONICAL_TEAM_BUFF_TIERS else ""


def normalize_team_buff(value: Any, *, default: str = "T5") -> str:
    """
    Normalize a TeamBuff tier string and clamp to the canonical set.

    Args:
        value: Raw tier (e.g. "t5", "T10", "none")
        default: Returned when `value` is empty/invalid (also clamped)
    """
    s = canonicalize_team_buff(value)
    if s:
        return s
    d = canonicalize_team_buff(default)
    return d or "T5"


def normalize_team_buff_sequence(
    tiers: Sequence[Any] | None,
    *,
    default: Sequence[str] = DEFAULT_TEAM_BUFF_REPLAY_TIERS,
) -> tuple[str, ...]:
    """
    Normalize a tier list into canonical, de-duplicated TeamBuff keys.
    """
    source = list(tiers) if tiers else list(default)
    out: list[str] = []
    for raw in source:
        tier = canonicalize_team_buff(raw)
        if tier and tier not in out:
            out.append(tier)
    if out:
        return tuple(out)

    fallback: list[str] = []
    for raw in list(default):
        tier = canonicalize_team_buff(raw)
        if tier and tier not in fallback:
            fallback.append(tier)
    return tuple(fallback) or ("T5",)


def team_buff_query_values(team_buff: Any, *, default: str = "T5") -> tuple[str, ...]:
    """
    Return the canonical TeamBuff key to query.
    """
    tier = normalize_team_buff(team_buff, default=default)
    return (tier,)


def team_buff_display_label(team_buff: Any, *, default: str = "T5") -> str:
    tier = normalize_team_buff(team_buff, default=default)
    return "None" if tier == "NONE" else tier


def team_buff_effect(team_buff: Any, team_color: Any) -> dict[str, int]:
    """
    Return the raw stat delta applied by TeamBuff for the provided team color.

    This matches `gear_optimizer.core.stats_calculator.build_base_stats_from_config`.
    """
    tier = TEAM_BUFF_TIER_EFFECTS.get(canonicalize_team_buff(team_buff))
    if not tier:
        return {}

    pp_add = int(tier.get("PP", 0) or 0)
    elem_add = int(tier.get("Elem", 0) or 0)
    out: dict[str, int] = {}
    if pp_add:
        out["Perfect Points"] = pp_add

    color = str(team_color or "").strip()
    valid_color_key = next((k for k in TEAM_BUFF_ELEMENTS if k.lower() == color.lower()), None)
    if valid_color_key and elem_add:
        out[valid_color_key] = elem_add
    return out


def _is_auto_select_buff_and_color(cfg_dict: Mapping[str, Any] | None) -> bool:
    if not isinstance(cfg_dict, Mapping):
        return False
    ie = cfg_dict.get("IterationEngine") or cfg_dict.get("iterationengine") or {}
    if not isinstance(ie, Mapping):
        return False
    raw = ie.get("AutoSelectBuffAndColor", ie.get("autoselectbuffandcolor", ""))
    return truthy(raw)


def _get_team_section_from_cfg_dict(cfg_dict: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(cfg_dict, Mapping):
        return {}
    sec = cfg_dict.get("TeamContributionBuffConstant") or cfg_dict.get("teamcontributionbuffconstant") or {}
    return sec if isinstance(sec, Mapping) else {}


def resolve_team_color_from_cfg_dict(
    cfg_dict: Mapping[str, Any] | None,
    *,
    primary_color: str = "",
) -> str:
    if _is_auto_select_buff_and_color(cfg_dict):
        return str(primary_color or "").strip()
    sec = _get_team_section_from_cfg_dict(cfg_dict)
    color = str(sec.get("TeamColor", sec.get("teamcolor", ""))).strip()
    if not color:
        color = str(primary_color or "").strip()
    return color


def resolve_baseline_team_buff_from_cfg_dict(cfg_dict: Mapping[str, Any] | None, *, default: str = "T5") -> str:
    """
    Resolve the baseline TeamBuff tier for a run from cfg_dict.

    - AutoSelectBuffAndColor => TeamBuff=T5 (runtime semantics)
    - Otherwise => TeamContributionBuffConstant.TeamBuff (fallback default)
    """
    if _is_auto_select_buff_and_color(cfg_dict):
        return "T5"
    sec = _get_team_section_from_cfg_dict(cfg_dict)
    if isinstance(sec, Mapping) and sec:
        raw = sec.get("TeamBuff", sec.get("teambuff", default))
        return normalize_team_buff(raw, default=default)
    return normalize_team_buff(default)


def resolve_baseline_team_buff_from_cfg(cfg: Any, *, default: str = "T5") -> str:
    """
    Resolve the baseline TeamBuff tier for a run from a configparser-like object.
    """
    auto = False
    try:
        auto = bool(read_iteration_engine_settings(cfg).auto_select_buff_and_color)
    except Exception as e:
        logger.debug(f"team_buff:resolve_baseline_team_buff_from_cfg: {e}")
        auto = False
    if auto:
        return "T5"

    raw = default
    try:
        raw = cfg.get("TeamContributionBuffConstant", "TeamBuff", fallback=default)
    except (AttributeError, TypeError, ValueError, configparser.Error):
        raw = default
    return normalize_team_buff(raw, default=default)
