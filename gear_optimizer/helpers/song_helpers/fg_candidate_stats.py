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
def _as_genome(candidate: dict) -> list[dict]:
    genome = candidate.get("Genome")
    if isinstance(genome, list) and genome:
        out = list(genome[:9])
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


def _candidate_genome(candidate: dict) -> list[dict]:
    genome = candidate.get("Genome")
    if isinstance(genome, list) and genome:
        return _as_genome(candidate)

    registry = candidate.get("_ga_registry")
    genome_ids = candidate.get("GenomeIDs")
    if registry is not None and genome_ids is not None:
        try:
            genome = registry.decode_genome(np.asarray(genome_ids, dtype=np.int32))
            if isinstance(genome, list) and genome:
                candidate["Genome"] = genome
                return _as_genome(candidate)
        except Exception as e:
            logger.debug(f"fg_candidate_stats:_candidate_genome: {e}")

    return _as_genome(candidate)


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

    Some GA/decode paths intentionally keep candidates lightweight and omit fully
    materialized `Data` payloads. This helper hydrates only the retained subset so
    downstream FG code can read a stable shape without rebuilding stats ad hoc.
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

        ft = data.get("FT", cand.get("FT", 0) or 0) or 0
        ff = data.get("FF", cand.get("FF", 0) or 0) or 0
        try:
            ft = int(ft)
        except Exception as e:
            logger.debug(f"fg_candidate_stats:hydrate_fg_candidate_stats: {e}")
            ft = 0
        try:
            ff = int(ff)
        except Exception as e:
            logger.debug(f"fg_candidate_stats:hydrate_fg_candidate_stats: {e}")
            ff = 0

        gem_counts = cand.get("GemCounts") or data.get("GemCounts") or {}
        if not isinstance(gem_counts, dict):
            gem_counts = {}

        g_pp = safe_int(gem_counts.get("Perfect Points", 0), 0)
        g_cm = safe_int(gem_counts.get("Combo Multiplier", 0), 0)
        g_fm = safe_int(gem_counts.get("Fever Multiplier", 0), 0)
        g_ov = element_gem_count(gem_counts)

        sel = get_selected_element(data, "") or get_selected_element(cand, "") or str(selected_color or "")
        stats_existing = data.get("Stats")
        if isinstance(stats_existing, dict) and stats_existing:
            stats = dict(stats_existing)
            base_stats = data.get("BaseStats")
            if not (isinstance(base_stats, dict) and base_stats):
                base_stats = cand.get("BaseStats")
            if isinstance(base_stats, dict) and base_stats:
                data["BaseStats"] = dict(base_stats)
        else:
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
            else:
                genome = _candidate_genome(cand)
                stats = dict(_base_fixed_stats())
                if not sel:
                    sel = selected_color
                for item in genome[:9]:
                    if not isinstance(item, dict) or not item:
                        continue
                    for k, v in item.items():
                        if k in SKIP_ITEM_KEYS:
                            continue
                        try:
                            stats[k] = stats.get(k, 0) + v
                        except Exception as e:
                            logger.debug(f"fg_candidate_stats:hydrate_fg_candidate_stats: {e}")
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

        raw_ga_search_score = safe_int(
            cand.get("RawGASearchScore", cand.get("BaseScore", cand.get("Score", 0) or 0)),
            0,
        )
        base_score = int(raw_ga_search_score)
        cand["RawGASearchScore"] = int(raw_ga_search_score)
        cand["Score"] = int(base_score)
        cand["BaseScore"] = int(base_score)
        data["RawGASearchScore"] = int(raw_ga_search_score)
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
