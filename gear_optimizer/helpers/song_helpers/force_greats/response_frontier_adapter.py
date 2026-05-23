from __future__ import annotations

from typing import Any

from ....core.constants import LOADOUTS_PER_SONG_LIMIT
from ....core.utils import safe_int
from ....solver.force_greats_common import extract_base_stats
from ....solver.scoring.fg_policy import extract_fg_song_inputs
from ....solver.scoring.runtime_state import FORCE_GREATS_ALGO_VERSION
from ....solver.scoring.stats_scoring import _force_greats_counts_to_dict, evaluate_stats_score
from ....solver.taichi_gem.force_greats import (
    FgResponseFrontierSolveResult,
    solve_force_greats_response_frontier_batch_gpu,
)
from ..ga_entry_utils import materialize_entry_names
from . import cache_validation
from .entry_resolution import build_direct_ga_entry_items, entry_base_score
from .entry_utils import eval_data_from_entry, expected_selected_element
from .result_application import materialize_stats_from_payload


def _base_stats_for_response_frontier(eval_data: dict[str, Any], *, selected: str) -> dict[str, Any]:
    base_stats = eval_data.get("BaseStats")
    if isinstance(base_stats, dict) and base_stats:
        return dict(base_stats)

    stats = eval_data.get("Stats")
    if not isinstance(stats, dict) or not stats:
        stats = materialize_stats_from_payload(eval_data, selected_element=selected, mutate_payload=True)
    if not isinstance(stats, dict) or not stats:
        raise ValueError("ForceGreats response frontier requires Stats or BaseStats")

    base_stats = extract_base_stats(
        stats,
        eval_data.get("GemCounts") if isinstance(eval_data.get("GemCounts"), dict) else {},
        str(selected or eval_data.get("Selected Element", "") or ""),
        safe_int(eval_data.get("FT", 0), 0),
        safe_int(eval_data.get("FF", 0), 0),
    )
    if not isinstance(base_stats, dict) or not base_stats:
        raise ValueError("ForceGreats response frontier BaseStats extraction failed")
    eval_data["BaseStats"] = dict(base_stats)
    return dict(base_stats)


def _force_payload_from_response_frontier(
    *,
    eval_data: dict[str, Any],
    base_stats: dict[str, Any],
    selected_element: str,
    result: FgResponseFrontierSolveResult,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> dict[str, Any]:
    forced_counts = tuple(int(v) for v in result.forced_counts)
    config = _force_greats_counts_to_dict(list(forced_counts), max(2, len(forced_counts)))
    base_score = int(evaluate_stats_score(result.stats, calc_song, ref_arrays))

    payload = dict(eval_data)
    payload["BaseStats"] = dict(base_stats)
    payload["Stats"] = dict(result.stats)
    payload["BaseScore"] = int(base_score)
    payload["Score"] = int(result.best_score)
    payload["Selected Element"] = str(selected_element or payload.get("Selected Element", "") or "")
    payload["GemCounts"] = dict(result.gem_counts)
    payload["FT"] = int(result.ft)
    payload["FF"] = int(result.ff)
    payload["forced_counts"] = list(forced_counts)
    payload["ForceGreats"] = {
        "enabled": True,
        "mode": "response_frontier",
        "algo_version": int(FORCE_GREATS_ALGO_VERSION),
        "config": config,
        "final_score": int(result.best_score),
        "frontier_first_surfaces": int(len(result.frontier.first_frontier)),
        "frontier_states": int(result.frontier.states_evaluated),
        "frontier_max_state": int(result.frontier.max_state_frontier),
        "frontier_transitions": int(result.frontier.transitions_evaluated),
        "non_fever_base": int(result.frontier.non_fever_base),
    }
    return payload


def process_force_greats_response_frontier_gpu(
    loadout_entries,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_candidates=None,
    ga_registry=None,
):
    direct_ga_items = build_direct_ga_entry_items(ga_candidates, ga_registry=ga_registry)
    base_items = list(loadout_entries.items()) if isinstance(loadout_entries, dict) else []
    if direct_ga_items:
        base_items = [(k, v) for k, v in base_items if not (isinstance(v, dict) and bool(v.get("_fg_direct_ga")))]
    entry_items = list(base_items) + list(direct_ga_items)

    # Fail before GPU launch if the song payload cannot support FG at all.
    song_inputs = extract_fg_song_inputs(calc_song)
    if int(song_inputs.total_notes) <= 0:
        raise ValueError("ForceGreats response frontier requires a song with at least one note")

    variants: list[dict[str, Any]] = []
    result_cache: dict[tuple[Any, ...], FgResponseFrontierSolveResult] = {}
    for _key, entry in entry_items:
        if not isinstance(entry, dict):
            continue
        eval_data = eval_data_from_entry(entry, str(meta_primary_color or ""))
        if not isinstance(eval_data, dict) or not eval_data:
            continue
        selected = expected_selected_element(entry, str(meta_primary_color or ""))
        cached_force = entry.get("force")
        if cached_force and cache_validation.is_cached_force_valid_for_response_frontier(cached_force, selected):
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            fg_score = int(entry.get("fg_score", 0) or cached_force.get("Score", 0) or 0)
            base_score = int(cached_force.get("BaseScore", 0) or entry_base_score(entry))
            variants.append(
                {
                    "data": cached_force,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": int(base_score),
                    "base_score": int(base_score),
                    "fg_score": int(fg_score),
                    "_entry_ref": entry,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            continue

        base_stats = _base_stats_for_response_frontier(eval_data, selected=selected)
        cache_key = (
            str(selected or ""),
            tuple(sorted((str(key), safe_int(value, 0)) for key, value in base_stats.items())),
        )
        result = result_cache.get(cache_key)
        if result is None:
            result = solve_force_greats_response_frontier_batch_gpu(
                base_stats=base_stats,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                selected_color=selected,
            )
            result_cache[cache_key] = result

        payload = _force_payload_from_response_frontier(
            eval_data=eval_data,
            base_stats=base_stats,
            selected_element=selected,
            result=result,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )
        if int(result.best_score) <= int(payload["BaseScore"]):
            continue

        if int(result.best_score) > safe_int(entry.get("fg_score", 0), 0):
            entry["force"] = payload
            entry["fg_score"] = int(result.best_score)
        gear_names, mini_names = materialize_entry_names(entry, mutate=True)
        variants.append(
            {
                "data": payload,
                "gear": gear_names,
                "minis": mini_names,
                "score": int(payload["BaseScore"]),
                "base_score": int(payload["BaseScore"]),
                "fg_score": int(result.best_score),
                "_entry_ref": entry,
                "_is_ga": str(entry.get("_source") or "") == "ga",
            }
        )

    variants.sort(key=lambda v: int(v.get("fg_score", 0) or 0), reverse=True)
    return variants[: int(LOADOUTS_PER_SONG_LIMIT)]
