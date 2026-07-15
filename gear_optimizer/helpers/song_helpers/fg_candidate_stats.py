from __future__ import annotations

from typing import Optional
import logging

import numpy as np

from ...core.constants import SKIP_ITEM_KEYS
from ...core.gem_defs import element_gem_count
from ...core.utils import get_selected_element, safe_int
from ...solver.base_stats import build_base_fixed_stats_list, build_stats_dict
from ...solver.scoring.exact_rescore import score_stats_exact_batch
from ...solver.scoring.stats_ops import apply_gems_to_base_stats



logger = logging.getLogger(__name__)
def _as_loadout(candidate: dict) -> list[dict]:
    loadout = candidate.get("Loadout")
    if isinstance(loadout, list) and loadout:
        out = list(loadout[:9])
        while len(out) < 9:
            out.append({})
        return out
    gear = list(candidate.get("Gear") or [])[:6]
    minis = list(candidate.get("Minis") or [])[:3]
    while len(gear) < 6:
        gear.append({})
    while len(minis) < 3:
        minis.append({})
    return gear + minis


def _candidate_loadout(candidate: dict) -> list[dict]:
    loadout = candidate.get("Loadout")
    if isinstance(loadout, list) and loadout:
        return _as_loadout(candidate)

    registry = candidate.get("_item_registry")
    loadout_ids = candidate.get("LoadoutIDs")
    if registry is not None and loadout_ids is not None:
        try:
            loadout = registry.decode_loadout(np.asarray(loadout_ids, dtype=np.int32))
            if isinstance(loadout, list) and loadout:
                candidate["Loadout"] = loadout
                return _as_loadout(candidate)
        except Exception as e:
            logger.debug(f"fg_candidate_stats:_candidate_loadout: {e}")

    return _as_loadout(candidate)


def _candidate_gem_config(cand: dict, data: dict) -> tuple[int, int, dict, int, int, int, int]:
    """Read the candidate's (FT, FF, GemCounts, per-type gem counts) with the
    data-then-candidate precedence the hydration contract defines."""
    ft_raw = data.get("FT", cand.get("FT", 0) or 0) or 0
    ff_raw = data.get("FF", cand.get("FF", 0) or 0) or 0
    # Exact original coercion semantics (int(), NOT safe_int: safe_int parses
    # decimal strings via float and would turn "3.5" into 3 instead of 0).
    try:
        ft = int(ft_raw)
    except Exception as e:
        logger.debug(f"fg_candidate_stats:_candidate_gem_config: {e}")
        ft = 0
    try:
        ff = int(ff_raw)
    except Exception as e:
        logger.debug(f"fg_candidate_stats:_candidate_gem_config: {e}")
        ff = 0
    gem_counts = cand.get("GemCounts") or data.get("GemCounts") or {}
    if not isinstance(gem_counts, dict):
        gem_counts = {}
    g_pp = safe_int(gem_counts.get("Perfect Points", 0), 0)
    g_cm = safe_int(gem_counts.get("Combo Multiplier", 0), 0)
    g_fm = safe_int(gem_counts.get("Fever Multiplier", 0), 0)
    g_ov = element_gem_count(gem_counts)
    return ft, ff, gem_counts, g_pp, g_cm, g_fm, g_ov


def _resolve_candidate_stats(
    cand: dict,
    data: dict,
    *,
    sel: str,
    selected_color: str,
    ft: int,
    ff: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
    base_fixed_stats,
) -> tuple[dict, str]:
    """Resolve the candidate's gem-applied Stats (and effective element).

    Precedence: existing Data.Stats verbatim -> gems re-applied over carried
    BaseStats -> loadout-accumulated stats over the song's fixed base. Mutates
    only data["BaseStats"] (the pre-gem row downstream FG code reads).
    """
    stats_existing = data.get("Stats")
    if isinstance(stats_existing, dict) and stats_existing:
        stats = dict(stats_existing)
        base_stats = data.get("BaseStats")
        if not (isinstance(base_stats, dict) and base_stats):
            base_stats = cand.get("BaseStats")
        if isinstance(base_stats, dict) and base_stats:
            data["BaseStats"] = dict(base_stats)
        return stats, sel

    base_stats = data.get("BaseStats")
    if not (isinstance(base_stats, dict) and base_stats):
        base_stats = cand.get("BaseStats")

    if isinstance(base_stats, dict) and base_stats:
        data["BaseStats"] = dict(base_stats)
        stats = apply_gems_to_base_stats(
            base_stats,
            str(sel),
            int(ft),
            int(ff),
            int(g_pp),
            int(g_cm),
            int(g_fm),
            int(g_ov),
            add_missing_element_key=False,
        )
        return stats, sel

    loadout = _candidate_loadout(cand)
    stats = dict(base_fixed_stats())
    if not sel:
        sel = selected_color
    for item in loadout[:9]:
        if not isinstance(item, dict) or not item:
            continue
        for k, v in item.items():
            if k in SKIP_ITEM_KEYS:
                continue
            try:
                stats[k] = stats.get(k, 0) + v
            except Exception as e:
                logger.debug(f"fg_candidate_stats:_resolve_candidate_stats: {e}")
                continue

    data["BaseStats"] = dict(stats)
    stats = apply_gems_to_base_stats(
        stats,
        str(sel),
        int(ft),
        int(ff),
        int(g_pp),
        int(g_cm),
        int(g_fm),
        int(g_ov),
        add_missing_element_key=False,
    )
    return stats, sel


def hydrate_fg_candidate_stats(
    candidates: list[dict],
    *,
    base_stats_fixed: dict,
    selected_color: str,
    cfg_data: Optional[dict] = None,
    calc_song: Optional[dict] = None,
    ref_arrays: Optional[dict] = None,
) -> None:
    """
    Ensure FG candidates carry `Data["Stats"]` before finder/exact-DP work.

    Exact Base decode keeps retained candidates lightweight and may omit fully
    materialized `Data` payloads. This helper hydrates only that retained subset so
    downstream FG code reads a stable shape without rebuilding stats ad hoc.
    """
    if not candidates:
        return

    cfg_data = cfg_data if isinstance(cfg_data, dict) else {}
    selected_color = str(selected_color or cfg_data.get("selected_color", "") or "")

    base_fixed: dict[str, int] | None = None

    def _base_fixed_stats() -> dict[str, int]:
        nonlocal base_fixed, selected_color
        if base_fixed is None:
            base_fixed_list, fallback_sel = build_base_fixed_stats_list(
                base_stats_fixed,
                cfg_data,
                fallback_selected_color=selected_color,
            )
            base_fixed = build_stats_dict(base_fixed_list)
            if fallback_sel and not selected_color:
                selected_color = str(fallback_sel)
        return base_fixed

    if (calc_song is None) != (ref_arrays is None):
        raise ValueError("calc_song and ref_arrays must be provided together for canonical FG candidate scores")

    for cand in candidates:
        if not isinstance(cand, dict):
            continue

        data = cand.get("Data")
        if not isinstance(data, dict):
            data = {}

        ft, ff, gem_counts, g_pp, g_cm, g_fm, g_ov = _candidate_gem_config(cand, data)
        sel = get_selected_element(data, "") or get_selected_element(cand, "") or str(selected_color or "")
        stats, sel = _resolve_candidate_stats(
            cand,
            data,
            sel=sel,
            selected_color=selected_color,
            ft=ft,
            ff=ff,
            g_pp=g_pp,
            g_cm=g_cm,
            g_fm=g_fm,
            g_ov=g_ov,
            base_fixed_stats=_base_fixed_stats,
        )

        raw_base_search_score = safe_int(
            cand.get("RawBaseSearchScore", cand.get("BaseScore", cand.get("Score", 0) or 0)),
            0,
        )
        base_score = int(raw_base_search_score)
        cand["RawBaseSearchScore"] = int(raw_base_search_score)
        cand["Score"] = int(base_score)
        cand["BaseScore"] = int(base_score)
        data["RawBaseSearchScore"] = int(raw_base_search_score)
        data["Score"] = int(base_score)
        data["BaseScore"] = int(base_score)
        data["FT"] = int(ft)
        data["FF"] = int(ff)
        data["GemCounts"] = gem_counts
        data["Selected Element"] = sel
        data["Stats"] = stats
        cand["Data"] = data

    if calc_song is None:
        return

    stats_rows = []
    candidates_with_stats = []
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        data = cand.get("Data")
        if not isinstance(data, dict):
            continue
        stats = data.get("Stats")
        if not isinstance(stats, dict) or not stats:
            raise ValueError("FG candidate hydration produced a candidate without replayable Stats")
        stats_rows.append(stats)
        candidates_with_stats.append(cand)

    exact_scores = score_stats_exact_batch(stats_rows, calc_song, ref_arrays)
    if len(exact_scores) != len(candidates_with_stats):
        raise ValueError("FG candidate exact score batch returned the wrong number of scores")
    for cand, base_score in zip(candidates_with_stats, exact_scores, strict=True):
        data = cand.get("Data")
        if not isinstance(data, dict):
            raise ValueError("FG candidate exact score batch lost candidate Data")
        cand["Score"] = int(base_score)
        cand["BaseScore"] = int(base_score)
        data["Score"] = int(base_score)
        data["BaseScore"] = int(base_score)
