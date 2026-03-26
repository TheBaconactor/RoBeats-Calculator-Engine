from __future__ import annotations

"""
TeamBuff helpers (baseline tier resolution).

We persist/load baseline candidates under a single TeamBuff tier per run. In auto mode
(`AutoSelectBuffAndColor=true`), runtime semantics force TeamBuff=T5 regardless of the
configured TeamContributionBuffConstant.TeamBuff value.

This module centralizes:
- tier normalization
- resolving the baseline TeamBuff from either a cfg_dict or configparser-like object
"""

from typing import Any, Mapping

CANONICAL_TEAM_BUFF_TIERS: frozenset[str] = frozenset({"NONE", "T1", "T5", "T10", "T15"})

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def normalize_team_buff(value: Any, *, default: str = "T5") -> str:
    """
    Normalize a TeamBuff tier string and clamp to the canonical set.

    Args:
        value: Raw tier (e.g. "t5", "T10", "none")
        default: Returned when `value` is empty/invalid (also clamped)
    """
    s = str(value or "").strip().upper()
    if s in CANONICAL_TEAM_BUFF_TIERS:
        return s
    d = str(default or "").strip().upper() or "T5"
    return d if d in CANONICAL_TEAM_BUFF_TIERS else "T5"


def _truthy_cfg(v: Any) -> bool:
    return str(v or "").strip().lower() in _TRUTHY


def resolve_baseline_team_buff_from_cfg_dict(cfg_dict: Mapping[str, Any] | None, *, default: str = "T5") -> str:
    """
    Resolve the baseline TeamBuff tier for a run from cfg_dict.

    - AutoSelectBuffAndColor => TeamBuff=T5 (runtime semantics)
    - Otherwise => TeamContributionBuffConstant.TeamBuff (fallback default)
    """
    if not isinstance(cfg_dict, Mapping):
        return normalize_team_buff(default)

    ie = cfg_dict.get("IterationEngine") or cfg_dict.get("iterationengine") or {}
    if isinstance(ie, Mapping):
        raw = ie.get("AutoSelectBuffAndColor", ie.get("autoselectbuffandcolor", ""))
        if _truthy_cfg(raw):
            return "T5"

    sec = cfg_dict.get("TeamContributionBuffConstant") or cfg_dict.get("teamcontributionbuffconstant") or {}
    if isinstance(sec, Mapping):
        raw = sec.get("TeamBuff", sec.get("teambuff", default))
        return normalize_team_buff(raw, default=default)

    return normalize_team_buff(default)


def resolve_baseline_team_buff_from_cfg(cfg: Any, *, default: str = "T5") -> str:
    """
    Resolve the baseline TeamBuff tier for a run from a configparser-like object.
    """
    auto = False
    try:
        auto = bool(cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False))
    except Exception:
        auto = False
    if auto:
        return "T5"

    raw = default
    try:
        raw = cfg.get("TeamContributionBuffConstant", "TeamBuff", fallback=default)
    except Exception:
        raw = default
    return normalize_team_buff(raw, default=default)
