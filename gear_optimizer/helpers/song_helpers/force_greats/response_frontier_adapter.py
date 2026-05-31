from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ....core.constants import LOADOUTS_PER_SONG_LIMIT
from ....core.utils import safe_int
from ....solver.force_greats_common import extract_base_stats
from ....solver.scoring.exact_rescore import evaluate_force_greats_exact, score_stats_exact
from ....solver.scoring.fg_policy import extract_fg_song_inputs
from ....solver.scoring.runtime_state import FORCE_GREATS_ALGO_VERSION
from ....solver.scoring.stats_scoring import _force_greats_counts_to_dict, evaluate_stats_score_nojit as evaluate_stats_score
from ....solver.taichi_gem.force_greats import (
    FgResponseFrontierSolveResult,
    prepare_force_greats_response_frontier_scoring_batch,
    reconstruct_force_greats_response_counts,
)
from ..ga_entry_utils import materialize_entry_names
from . import cache_validation
from .entry_resolution import build_direct_ga_entry_items, entry_base_score
from .entry_utils import eval_data_from_entry, expected_selected_element
from .result_application import materialize_stats_from_payload


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedBatch:
    selected: str
    rows: tuple[tuple[tuple[Any, ...], dict[str, Any]], ...]
    batch: Any


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedPlan:
    calc_song: dict[str, Any]
    ref_arrays: dict[str, Any]
    variants: tuple[dict[str, Any], ...]
    pending_jobs: tuple[tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], tuple[Any, ...]], ...]
    prepared_batches: tuple[FgResponseFrontierPreparedBatch, ...]


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
    reconstruction_frontier=None,
) -> dict[str, Any]:
    frontier = reconstruction_frontier or result.frontier
    if result.forced_counts:
        forced_counts = tuple(int(v) for v in result.forced_counts)
    else:
        song_inputs = extract_fg_song_inputs(calc_song)
        forced_counts = tuple(
            int(v)
            for v in reconstruct_force_greats_response_counts(
                frontier=frontier,
                target_surface=result.surface,
                timestamps=song_inputs.timestamps,
                great_candidate_timestamps=song_inputs.great_candidates,
                raw_fever_fill=float(result.raw_fever_fill),
                real_fever_time=float(result.real_fever_time),
                use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
            )
        )
    config = _force_greats_counts_to_dict(list(forced_counts), max(2, len(forced_counts)))
    base_score = int(score_stats_exact(result.stats, calc_song, ref_arrays))
    exact_fg = evaluate_force_greats_exact(result.stats, calc_song, ref_arrays, list(forced_counts))
    if not isinstance(exact_fg, dict):
        raise ValueError("ForceGreats response frontier exact replay failed")
    final_score = int(exact_fg["final_score"])

    payload = dict(eval_data)
    payload["BaseStats"] = dict(base_stats)
    payload["Stats"] = dict(result.stats)
    payload["BaseScore"] = int(base_score)
    payload["Score"] = int(final_score)
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
        "final_score": int(final_score),
        "frontier_first_surfaces": int(len(frontier.first_frontier)),
        "frontier_states": int(frontier.states_evaluated),
        "frontier_max_state": int(frontier.max_state_frontier),
        "frontier_transitions": int(frontier.transitions_evaluated),
        "non_fever_base": int(frontier.non_fever_base),
    }
    return payload


def prepare_force_greats_response_frontier_plan(
    loadout_entries,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_candidates=None,
    ga_registry=None,
    scoring_bundle=None,
) -> FgResponseFrontierPreparedPlan:
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
    pending_jobs: list[tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], tuple[Any, ...]]] = []
    pending_by_selected: dict[str, list[tuple[tuple[Any, ...], dict[str, Any]]]] = {}
    pending_keys: set[tuple[Any, ...]] = set()
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
        pending_jobs.append((entry, eval_data, selected, base_stats, cache_key))
        if cache_key not in pending_keys:
            pending_keys.add(cache_key)
            pending_by_selected.setdefault(str(selected or ""), []).append((cache_key, base_stats))

    prepared_batches: list[FgResponseFrontierPreparedBatch] = []
    for selected, rows in pending_by_selected.items():
        batch = prepare_force_greats_response_frontier_scoring_batch(
            base_stats_list=[base_stats for _cache_key, base_stats in rows],
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            selected_color=selected,
            scoring_bundle=scoring_bundle,
        )
        prepared_batches.append(
            FgResponseFrontierPreparedBatch(
                selected=str(selected or ""),
                rows=tuple(rows),
                batch=batch,
            )
        )

    return FgResponseFrontierPreparedPlan(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        variants=tuple(variants),
        pending_jobs=tuple(pending_jobs),
        prepared_batches=tuple(prepared_batches),
    )


def execute_force_greats_response_frontier_plan(
    plan: FgResponseFrontierPreparedPlan,
    *,
    score_prepared_batch: Callable[..., list[FgResponseFrontierSolveResult]],
) -> list[dict[str, Any]]:
    prepared_results = []
    for prepared in plan.prepared_batches:
        results = score_prepared_batch(prepared.batch, include_forced_counts=False)
        prepared_results.append(results)
    return materialize_force_greats_response_frontier_plan_results(plan, prepared_results)


def materialize_force_greats_response_frontier_plan_results(
    plan: FgResponseFrontierPreparedPlan,
    prepared_results: list[list[FgResponseFrontierSolveResult]],
) -> list[dict[str, Any]]:
    calc_song = plan.calc_song
    ref_arrays = plan.ref_arrays
    variants = list(plan.variants)
    result_cache: dict[tuple[Any, ...], FgResponseFrontierSolveResult] = {}
    if len(prepared_results) != len(plan.prepared_batches):
        raise ValueError("ForceGreats response frontier plan received the wrong number of prepared result batches")
    for prepared, results in zip(plan.prepared_batches, prepared_results, strict=True):
        rows = list(prepared.rows)
        if len(results) != len(rows):
            raise ValueError("ForceGreats response frontier batch returned the wrong number of results")
        for (cache_key, _base_stats), result in zip(rows, results, strict=True):
            result_cache[cache_key] = result

    pending_variants: list[dict[str, Any]] = []
    for entry, eval_data, selected, base_stats, cache_key in plan.pending_jobs:
        result = result_cache.get(cache_key)
        if result is None:
            raise ValueError("ForceGreats response frontier batch missed a candidate result")
        known_base_score = int(entry_base_score(entry))
        if int(result.best_score) <= int(known_base_score):
            continue
        base_score = int(evaluate_stats_score(result.stats, calc_song, ref_arrays))
        if int(result.best_score) <= int(base_score):
            continue
        gear_names, mini_names = materialize_entry_names(entry, mutate=True)
        pending_variants.append(
            {
                "entry": entry,
                "eval_data": eval_data,
                "selected": selected,
                "base_stats": base_stats,
                "result": result,
                "base_score": int(base_score),
                "gear": gear_names,
                "minis": mini_names,
                "fg_score": int(result.best_score),
                "_is_ga": str(entry.get("_source") or "") == "ga",
            }
        )

    pending_variants.sort(key=lambda variant: int(variant["fg_score"]), reverse=True)
    shortlisted = pending_variants[: int(LOADOUTS_PER_SONG_LIMIT)]

    for item in shortlisted:
        result = item["result"]
        payload = _force_payload_from_response_frontier(
            eval_data=item["eval_data"],
            base_stats=item["base_stats"],
            selected_element=item["selected"],
            result=result,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )

        entry = item["entry"]
        exact_fg_score = safe_int(payload.get("Score", 0), 0)
        if int(exact_fg_score) > safe_int(entry.get("fg_score", 0), 0):
            entry["force"] = payload
            entry["fg_score"] = int(exact_fg_score)
        variants.append(
            {
                "data": payload,
                "gear": item["gear"],
                "minis": item["minis"],
                "score": int(payload["BaseScore"]),
                "base_score": int(payload["BaseScore"]),
                "fg_score": int(exact_fg_score),
                "_entry_ref": entry,
                "_is_ga": bool(item["_is_ga"]),
            }
        )

    variants.sort(key=lambda v: int(v.get("fg_score", 0) or 0), reverse=True)
    return variants[: int(LOADOUTS_PER_SONG_LIMIT)]


def process_force_greats_response_frontier_gpu(
    loadout_entries,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_candidates=None,
    ga_registry=None,
    score_prepared_batch: Callable[..., list[FgResponseFrontierSolveResult]],
    scoring_bundle=None,
):
    plan = prepare_force_greats_response_frontier_plan(
        loadout_entries,
        calc_song,
        ref_arrays,
        meta_primary_color,
        ga_candidates=ga_candidates,
        ga_registry=ga_registry,
        scoring_bundle=scoring_bundle,
    )
    return execute_force_greats_response_frontier_plan(plan, score_prepared_batch=score_prepared_batch)
