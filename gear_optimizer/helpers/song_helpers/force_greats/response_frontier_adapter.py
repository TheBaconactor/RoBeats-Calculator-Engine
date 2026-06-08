from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ....core.constants import LOADOUTS_PER_SONG_LIMIT
from ....core.utils import safe_int
from ....solver.force_greats_common import extract_base_stats
from ....solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from ....solver.scoring.fg_policy import extract_fg_song_inputs
from ....solver.scoring.stats_scoring import _force_greats_counts_to_dict
from ....solver.taichi_gem.force_greats import (
    FgResponseFrontierSolveResult,
    prepare_force_greats_response_frontier_scoring_batch,
    reconstruct_force_greats_response_trace,
)
from ..ga_entry_utils import candidate_genome_ids, entry_loadout_hash, ga_candidate_key, materialize_entry_names
from .entry_utils import eval_data_from_entry, expected_selected_element
from .result_application import materialize_stats_from_payload


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedBatch:
    rows: tuple[tuple[tuple[Any, ...], dict[str, Any]], ...]
    batch: Any


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedPlan:
    calc_song: dict[str, Any]
    ref_arrays: dict[str, Any]
    pending_jobs: tuple[tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], int, tuple[Any, ...]], ...]
    prepared_batches: tuple[FgResponseFrontierPreparedBatch, ...]


def _entry_items_from_ga_candidates(ga_candidates, *, ga_registry=None) -> list[tuple[str, dict[str, Any]]]:
    items: list[tuple[str, dict[str, Any]]] = []
    for idx, candidate in enumerate(ga_candidates or []):
        if not isinstance(candidate, dict):
            raise ValueError(f"ForceGreats GA candidate {idx} is not a dict.")
        eval_data = candidate.get("Data")
        if not isinstance(eval_data, dict) or not eval_data:
            raise ValueError(f"ForceGreats GA candidate {idx} is missing Data.")
        genome_ids = candidate_genome_ids(candidate)
        registry_obj = ga_registry if ga_registry is not None else candidate.get("_ga_registry")
        score = int(candidate.get("BaseScore") or candidate.get("Score", 0) or 0)
        if score <= 0:
            raise ValueError(f"ForceGreats GA candidate {idx} is missing a positive BaseScore.")
        entry = {
            "gear": list(candidate.get("Gear") or []),
            "minis": list(candidate.get("Minis") or []),
            "score": int(score),
            "base_score": int(score),
            "details": {},
            "fg_score": int(candidate.get("fg_score", 0) or 0),
            "force": candidate.get("force"),
            "eval_data": eval_data,
            "_source": "ga",
            "_candidate_ref": candidate,
        }
        selected = str(eval_data.get("Selected Element", "") or "")
        if selected:
            entry["selected_element"] = selected
        if genome_ids is not None:
            entry["ga_genome_ids"] = list(genome_ids)
        if registry_obj is not None:
            entry["_ga_registry"] = registry_obj

        key = str(candidate.get("loadout_hash") or "").strip()
        if not key and (entry.get("gear") or entry.get("minis")):
            key = str(entry_loadout_hash(entry) or "")
        if not key and genome_ids is not None:
            key = ga_candidate_key(genome_ids)
        if not key:
            key = f"ga-candidate:{int(idx)}"
        entry["loadout_hash"] = str(key)
        items.append((str(key), entry))
    return items


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


def _paired_base_score_from_entry(entry: dict[str, Any], eval_data: dict[str, Any]) -> int:
    for value in (
        entry.get("fg_base_score"),
        entry.get("base_score"),
        entry.get("score"),
        eval_data.get("fg_base_score"),
        eval_data.get("BaseScore"),
        eval_data.get("base_score"),
        eval_data.get("score"),
    ):
        score = safe_int(value, 0)
        if score > 0:
            return int(score)
    raise ValueError("ForceGreats response frontier candidate is missing paired source base score.")


def _force_payload_from_response_frontier(
    *,
    eval_data: dict[str, Any],
    base_stats: dict[str, Any],
    paired_base_score: int,
    selected_element: str,
    result: FgResponseFrontierSolveResult,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    reconstruction_frontier=None,
) -> dict[str, Any]:
    frontier = reconstruction_frontier or result.frontier
    song_inputs = extract_fg_song_inputs(calc_song)
    frontier_trace = reconstruct_force_greats_response_trace(
        frontier=frontier,
        target_surface=result.surface,
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        raw_fever_fill=float(result.raw_fever_fill),
        real_fever_time=float(result.real_fever_time),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )
    trace_counts = tuple(int(row["forced_count"]) for row in frontier_trace)
    if result.forced_counts:
        forced_counts = tuple(int(v) for v in result.forced_counts)
        if forced_counts != trace_counts:
            raise ValueError("ForceGreats response frontier forced_counts do not match the reconstructed trace")
    else:
        forced_counts = trace_counts
    config = _force_greats_counts_to_dict(list(forced_counts), max(2, len(forced_counts)))
    paired_base = safe_int(paired_base_score, 0)
    if paired_base <= 0:
        raise ValueError("ForceGreats response frontier is missing paired source base score.")
    final_score_obj = score_force_greats_response_surface_exact(result.stats, calc_song, ref_arrays, result.surface)
    if final_score_obj is None:
        raise ValueError("ForceGreats response frontier exact surface replay failed")
    final_score = int(final_score_obj)

    payload = dict(eval_data)
    payload["BaseStats"] = dict(base_stats)
    payload["Stats"] = dict(result.stats)
    payload["BaseScore"] = int(paired_base)
    payload["Score"] = int(final_score)
    payload["Selected Element"] = str(selected_element or payload.get("Selected Element", "") or "")
    payload["GemCounts"] = dict(result.gem_counts)
    payload["FT"] = int(result.ft)
    payload["FF"] = int(result.ff)
    payload["forced_counts"] = list(forced_counts)
    payload["response_surface"] = [
        int(result.surface.fever0),
        int(result.surface.fever1),
        int(result.surface.fever2),
        int(result.surface.fever3),
        int(result.surface.great0),
        int(result.surface.great1),
        int(result.surface.great2),
        int(result.surface.great3),
        int(result.surface.body_fever),
        int(result.surface.body_great),
        int(result.surface.body_fever_great),
    ]
    payload["ForceGreats"] = {
        "config": config,
        "final_score": int(final_score),
        "frontier_trace": list(frontier_trace),
        "frontier_first_surfaces": int(len(frontier.first_frontier)),
        "frontier_states": int(frontier.states_evaluated),
        "frontier_max_state": int(frontier.max_state_frontier),
        "frontier_transitions": int(frontier.transitions_evaluated),
        "non_fever_base": int(frontier.non_fever_base),
    }
    return payload


def _prepare_force_greats_response_frontier_plan_from_items(
    entry_items,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    scoring_bundle=None,
) -> FgResponseFrontierPreparedPlan:
    # Fail before GPU launch if the song payload cannot support FG at all.
    song_inputs = extract_fg_song_inputs(calc_song)
    if int(song_inputs.total_notes) <= 0:
        raise ValueError("ForceGreats response frontier requires a song with at least one note")

    pending_jobs: list[tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], int, tuple[Any, ...]]] = []
    pending_by_selected: dict[str, list[tuple[tuple[Any, ...], dict[str, Any]]]] = {}
    pending_keys: set[tuple[Any, ...]] = set()
    for _key, entry in entry_items:
        if not isinstance(entry, dict):
            raise ValueError("ForceGreats response frontier received a non-dict entry.")
        eval_data = eval_data_from_entry(entry, str(meta_primary_color or ""))
        if not isinstance(eval_data, dict) or not eval_data:
            raise ValueError("ForceGreats response frontier entry is missing eval data.")
        selected = expected_selected_element(entry, str(meta_primary_color or ""))
        base_stats = _base_stats_for_response_frontier(eval_data, selected=selected)
        paired_base_score = _paired_base_score_from_entry(entry, eval_data)
        cache_key = (
            str(selected or ""),
            tuple(sorted((str(key), safe_int(value, 0)) for key, value in base_stats.items())),
        )
        pending_jobs.append((entry, eval_data, selected, base_stats, int(paired_base_score), cache_key))
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
                rows=tuple(rows),
                batch=batch,
            )
        )

    return FgResponseFrontierPreparedPlan(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        pending_jobs=tuple(pending_jobs),
        prepared_batches=tuple(prepared_batches),
    )


def prepare_force_greats_response_frontier_plan_for_ga_candidates(
    ga_candidates,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_registry=None,
    scoring_bundle=None,
) -> FgResponseFrontierPreparedPlan:
    return _prepare_force_greats_response_frontier_plan_from_items(
        _entry_items_from_ga_candidates(ga_candidates, ga_registry=ga_registry),
        calc_song,
        ref_arrays,
        meta_primary_color,
        scoring_bundle=scoring_bundle,
    )


def _score_prepared_batches_for_plan(
    plan: FgResponseFrontierPreparedPlan,
    *,
    gpu_client: Any | None,
) -> list[list[FgResponseFrontierSolveResult]]:
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        run_prepared_force_greats_response_frontier_batches_via_client,
        score_prepared_force_greats_response_frontier_batch_sync,
    )

    if gpu_client is not None:
        return [
            batch_results
            for batch_results, _timing in run_prepared_force_greats_response_frontier_batches_via_client(
                gpu_client,
                [prepared.batch for prepared in plan.prepared_batches],
                include_forced_counts=False,
            )
        ]

    prepared_results: list[list[FgResponseFrontierSolveResult]] = []
    for prepared in plan.prepared_batches:
        batch_results = score_prepared_force_greats_response_frontier_batch_sync(
            prepared.batch,
            include_forced_counts=False,
        )
        prepared_results.append(batch_results)
    return prepared_results


def materialize_force_greats_response_frontier_plan_results(
    plan: FgResponseFrontierPreparedPlan,
    prepared_results: list[list[FgResponseFrontierSolveResult]],
) -> list[dict[str, Any]]:
    calc_song = plan.calc_song
    ref_arrays = plan.ref_arrays
    variants: list[dict[str, Any]] = []
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
    for entry, eval_data, selected, base_stats, paired_base_score, cache_key in plan.pending_jobs:
        result = result_cache.get(cache_key)
        if result is None:
            raise ValueError("ForceGreats response frontier batch missed a candidate result")
        gear_names, mini_names = materialize_entry_names(entry, mutate=True)
        pending_variants.append(
            {
                "entry": entry,
                "eval_data": eval_data,
                "selected": selected,
                "base_stats": base_stats,
                "paired_base_score": int(paired_base_score),
                "result": result,
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
            paired_base_score=int(item["paired_base_score"]),
            selected_element=item["selected"],
            result=result,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )

        entry = item["entry"]
        exact_fg_score = safe_int(payload.get("Score", 0), 0)
        exact_base_score = safe_int(payload.get("BaseScore", 0), 0)
        if exact_fg_score <= exact_base_score:
            continue
        if exact_fg_score > safe_int(entry.get("fg_score", 0), 0):
            entry["force"] = payload
            entry["fg_score"] = exact_fg_score
            entry["fg_base_score"] = exact_base_score
        variants.append(
            {
                "data": payload,
                "gear": item["gear"],
                "minis": item["minis"],
                "score": exact_base_score,
                "base_score": exact_base_score,
                "fg_score": exact_fg_score,
                "_entry_ref": entry,
                "_is_ga": bool(item["_is_ga"]),
            }
        )

    variants.sort(key=lambda v: int(v.get("fg_score", 0) or 0), reverse=True)
    return variants[: int(LOADOUTS_PER_SONG_LIMIT)]


def run_force_greats_response_frontier_for_ga_candidates(
    ga_candidates,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_registry=None,
    scoring_bundle=None,
    gpu_client: Any | None = None,
) -> list[dict[str, Any]]:
    plan = prepare_force_greats_response_frontier_plan_for_ga_candidates(
        ga_candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        ga_registry=ga_registry,
        scoring_bundle=scoring_bundle,
    )
    prepared_results = _score_prepared_batches_for_plan(plan, gpu_client=gpu_client)
    return materialize_force_greats_response_frontier_plan_results(plan, prepared_results)
