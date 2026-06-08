from __future__ import annotations

import time
from typing import Any, Callable

from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.solver.force_greats_common import extract_base_stats
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
from gear_optimizer.solver.scoring.stats_scoring import _force_greats_counts_to_dict
from gear_optimizer.solver.taichi_gem.force_greats import (
    FgResponseFrontierSolveResult,
    FgResponseSurface,
    prepare_force_greats_response_frontier_scoring_batch,
    reconstruct_force_greats_response_trace,
    score_prepared_force_greats_response_frontier_batch_sync,
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _candidate_base_stats(data: dict[str, Any], *, selected_color: str) -> dict[str, Any]:
    base_stats = data.get("BaseStats")
    if isinstance(base_stats, dict) and base_stats:
        return dict(base_stats)

    stats = data.get("Stats")
    if not isinstance(stats, dict) or not stats:
        raise ValueError("skyline FG candidate is missing Stats/BaseStats")

    base_stats = extract_base_stats(
        stats,
        data.get("GemCounts") if isinstance(data.get("GemCounts"), dict) else {},
        str(selected_color or data.get("Selected Element", "") or ""),
        _safe_int(data.get("FT", 0), 0),
        _safe_int(data.get("FF", 0), 0),
    )
    if not isinstance(base_stats, dict) or not base_stats:
        raise ValueError("skyline FG candidate BaseStats extraction failed")
    data["BaseStats"] = dict(base_stats)
    return dict(base_stats)


def _stable_int_mapping_key(values: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((str(key), _safe_int(value, 0)) for key, value in dict(values or {}).items()))


def _gem_count(gem_counts: Any, key: str) -> int:
    if not isinstance(gem_counts, dict):
        return 0
    return _safe_int(gem_counts.get(key, 0), 0)


def _percentile_int(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(int(v) for v in values)
    if len(ordered) == 1:
        return int(ordered[0])
    pos = (float(pct) / 100.0) * float(len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - float(lo)
    return int(round(float(ordered[lo]) * (1.0 - frac) + float(ordered[hi]) * frac))


def _int_list(values: Any) -> list[int]:
    if values is None:
        return []
    if hasattr(values, "tolist"):
        values = values.tolist()
    if not isinstance(values, (list, tuple)):
        return []
    return [_safe_int(value, 0) for value in values]


def _item_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("Name") or item.get("name") or item.get("DisplayName") or "")
    for attr_name in ("Name", "name", "display_name"):
        value = getattr(item, attr_name, None)
        if value:
            return str(value)
    return str(item) if item is not None else ""


def _genome_names(genome: Any, start: int, stop: int) -> list[str]:
    if not isinstance(genome, (list, tuple)):
        return []
    return [_item_name(item) for item in genome[start:stop]]


def _surface_payload(surface: FgResponseSurface) -> dict[str, int]:
    return {
        "fever0": int(surface.fever0),
        "fever1": int(surface.fever1),
        "fever2": int(surface.fever2),
        "fever3": int(surface.fever3),
        "great0": int(surface.great0),
        "great1": int(surface.great1),
        "great2": int(surface.great2),
        "great3": int(surface.great3),
        "body_fever": int(surface.body_fever),
        "body_great": int(surface.body_great),
        "body_fever_great": int(surface.body_fever_great),
    }


def _materialize_force_payload(
    *,
    base_data: dict[str, Any],
    base_stats: dict[str, Any],
    fg_result: FgResponseFrontierSolveResult,
    selected_color: str,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    paired_base_score: int,
) -> dict[str, Any]:
    forced_counts = tuple(int(v) for v in fg_result.forced_counts)
    if not forced_counts:
        raise ValueError("skyline response frontier requires forced_counts on the solve result")
    config = _force_greats_counts_to_dict(list(forced_counts), max(2, len(forced_counts)))
    base_score = int(paired_base_score)
    if base_score <= 0:
        raise ValueError("skyline response frontier requires a positive source paired base score.")
    final_score_obj = score_force_greats_response_surface_exact(fg_result.stats, calc_song, ref_arrays, fg_result.surface)
    if final_score_obj is None:
        raise ValueError("skyline response frontier exact surface replay failed")
    final_score = int(final_score_obj)
    song_inputs = extract_fg_song_inputs(calc_song)
    frontier_trace = reconstruct_force_greats_response_trace(
        frontier=fg_result.frontier,
        target_surface=fg_result.surface,
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        raw_fever_fill=float(fg_result.raw_fever_fill),
        real_fever_time=float(fg_result.real_fever_time),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )

    force_payload = dict(base_data)
    force_payload["BaseScore"] = int(base_score)
    force_payload["Score"] = int(final_score)
    force_payload["FT"] = int(fg_result.ft)
    force_payload["FF"] = int(fg_result.ff)
    force_payload["GemCounts"] = dict(fg_result.gem_counts)
    force_payload["BaseStats"] = dict(base_stats)
    force_payload["Stats"] = dict(fg_result.stats)
    force_payload["Selected Element"] = str(selected_color or force_payload.get("Selected Element", "") or "")
    force_payload["forced_counts"] = list(forced_counts)
    force_payload["ForceGreats"] = {
        "config": config,
        "final_score": int(final_score),
        "response_surface": _surface_payload(fg_result.surface),
        "frontier_trace": list(frontier_trace),
        "frontier_first_surfaces": int(len(fg_result.frontier.first_frontier)),
        "frontier_states": int(fg_result.frontier.states_evaluated),
        "frontier_max_state": int(fg_result.frontier.max_state_frontier),
        "frontier_transitions": int(fg_result.frontier.transitions_evaluated),
        "non_fever_base": int(fg_result.frontier.non_fever_base),
    }
    return force_payload


def _empty_batch_stats() -> dict[str, int]:
    return {
        "gpu_batches": 0,
        "groups": 0,
        "input_genomes": 0,
        "unique_genomes": 0,
        "deduped_genomes": 0,
        "dedupe_groups": 0,
    }


def _score_skyline_response_force_greats_batch(
    *,
    prepared: list[dict[str, Any]],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> tuple[list[FgResponseFrontierSolveResult | None], dict[str, int]]:
    if not prepared:
        return [], _empty_batch_stats()

    results: list[FgResponseFrontierSolveResult | None] = [None for _ in prepared]
    result_cache: dict[tuple[Any, ...], FgResponseFrontierSolveResult | None] = {}
    cache_member_counts: dict[tuple[Any, ...], int] = {}
    result_cache_hits = 0

    for idx, prep in enumerate(prepared):
        base_stats = dict(prep["base_stats"])
        selected_color = str(prep.get("selected_color", "") or "")
        result_key = (selected_color, _stable_int_mapping_key(base_stats))
        cache_member_counts[result_key] = int(cache_member_counts.get(result_key, 0)) + 1
        if result_key in result_cache:
            results[idx] = result_cache[result_key]
            result_cache_hits += 1
            continue

        batch = prepare_force_greats_response_frontier_scoring_batch(
            base_stats_list=[base_stats],
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            selected_color=selected_color,
        )
        scored = score_prepared_force_greats_response_frontier_batch_sync(batch)
        if not scored:
            raise ValueError("response frontier exact GPU batch produced no pair result")
        result = scored[0]
        results[idx] = result
        result_cache[result_key] = result

    return results, {
        "gpu_batches": int(len(result_cache)),
        "groups": int(len({str(item.get("selected_color", "") or "") for item in prepared})),
        "input_genomes": int(len(prepared)),
        "unique_genomes": int(len(result_cache)),
        "deduped_genomes": int(result_cache_hits),
        "dedupe_groups": sum(1 for count in cache_member_counts.values() if int(count) > 1),
    }


def score_retained_skyline_force_greats(
    candidate_records: list[dict[str, Any]],
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    default_selected_color: str,
    use_gpu: bool,
    status_cb: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not use_gpu:
        raise RuntimeError("Skyline FG is GPU-only; CPU FG scoring is not a production path.")

    if status_cb is None:

        def _noop_status_cb(_message: str) -> None:
            return None

        status_cb = _noop_status_cb

    telemetry_enabled = env_flag("SKYLINE_FG_TELEMETRY", "0")
    try:
        topk_reference = int(env_get("SKYLINE_FG_TOPK_REFERENCE", "51") or "51")
    except (TypeError, ValueError):
        topk_reference = 51
    topk_reference = max(1, int(topk_reference))

    best_fg_score = max((_safe_int(rec.get("base_score", 0), 0) for rec in candidate_records), default=0)
    best_record: dict[str, Any] | None = None
    for rec in candidate_records:
        if _safe_int(rec.get("base_score", 0), 0) == int(best_fg_score):
            best_record = rec
            break

    prepared: list[dict[str, Any]] = []
    for idx, rec in enumerate(candidate_records):
        data = rec.get("data")
        if not isinstance(data, dict) or not data:
            raise ValueError("skyline FG candidate record is missing data")

        base_score = _safe_int(rec.get("base_score", data.get("BaseScore", data.get("Score", 0))), 0)
        selected_color = str(data.get("Selected Element", "") or default_selected_color or "")
        base_stats = _candidate_base_stats(data, selected_color=selected_color)
        prepared.append(
            {
                "idx": int(idx),
                "rec": rec,
                "data": data,
                "base_score": int(base_score),
                "selected_color": selected_color,
                "base_stats": base_stats,
            }
        )

    call_t0 = time.perf_counter()
    fg_results, batch_stats = _score_skyline_response_force_greats_batch(
        prepared=prepared,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    fg_elapsed_total = float(time.perf_counter() - call_t0)
    fg_elapsed_each = float(fg_elapsed_total) / float(max(1, len(prepared)))

    fg_gains = 0
    telemetry_rows: list[dict[str, Any]] = []
    for idx, prep in enumerate(prepared):
        rec = prep["rec"]
        data = prep["data"]
        base_score = int(prep["base_score"])
        selected_color = str(prep["selected_color"])
        base_stats = dict(prep["base_stats"])
        fg_result = fg_results[idx] if idx < len(fg_results) else None

        fg_score = base_score
        fg_base_score = base_score
        force_payload = None
        if isinstance(fg_result, FgResponseFrontierSolveResult):
            force_payload = _materialize_force_payload(
                base_data=data,
                base_stats=base_stats,
                fg_result=fg_result,
                selected_color=selected_color,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                paired_base_score=base_score,
            )
            fg_score = int(force_payload["Score"])
            fg_base_score = int(force_payload["BaseScore"])

        fg_delta = int(fg_score) - int(base_score)
        if fg_delta > 0:
            fg_gains += 1
        if int(fg_score) > int(best_fg_score):
            best_fg_score = int(fg_score)
            best_record = rec

        data["BaseStats"] = dict(base_stats)
        data["FGScore"] = int(fg_score)
        data["FGDelta"] = int(fg_delta)
        data["FGBaseScore"] = int(fg_base_score)
        data["FGUpperBound"] = int(fg_score)
        data["NativeFGWouldSkipByCeiling"] = False
        if force_payload is not None:
            data["force"] = force_payload
            rec["force"] = force_payload

        rec["fg_score"] = int(fg_score)
        rec["fg_delta"] = int(fg_delta)
        rec["fg_base_score"] = int(fg_base_score)
        rec["fg_elapsed_s"] = float(fg_elapsed_each)

        force_counts = []
        force_gem_counts = {}
        force_ft = _safe_int(data.get("FT", 0), 0)
        force_ff = _safe_int(data.get("FF", 0), 0)
        if isinstance(force_payload, dict):
            force_counts = _int_list(force_payload.get("forced_counts"))
            force_gem_counts = (
                dict(force_payload.get("GemCounts") or {}) if isinstance(force_payload.get("GemCounts"), dict) else {}
            )
            force_ft = _safe_int(force_payload.get("FT", force_ft), force_ft)
            force_ff = _safe_int(force_payload.get("FF", force_ff), force_ff)

        rank = int(idx + 1)
        telemetry_rows.append(
            {
                "rank": int(rank),
                "sample_source": str(rec.get("sample_source", "") or ""),
                "base_score": int(base_score),
                "base_gap_to_best": int(
                    max(0, int(candidate_records[0].get("base_score", 0) or 0) - int(base_score))
                )
                if candidate_records
                else 0,
                "fg_score": int(fg_score),
                "fg_delta": int(fg_delta),
                "fg_base_score": int(fg_base_score),
                "fg_elapsed_s": float(fg_elapsed_each),
                "gear_names": _genome_names(rec.get("genome"), 0, 6),
                "mini_names": _genome_names(rec.get("genome"), 6, 9),
                "genome_ids": list(data.get("GenomeIDs") or []) if isinstance(data.get("GenomeIDs"), list) else [],
                "fg_ft": int(force_ft),
                "fg_ff": int(force_ff),
                "fg_gem_pp": _gem_count(force_gem_counts, "Perfect Points"),
                "fg_gem_cm": _gem_count(force_gem_counts, "Combo Multiplier"),
                "fg_gem_fm": _gem_count(force_gem_counts, "Fever Multiplier"),
                "fg_gem_element": _gem_count(force_gem_counts, "Element"),
                "force_count_sum": int(sum(int(x) for x in force_counts)) if force_counts else 0,
                "force_sections": int(len(force_counts)),
                "force_counts": list(force_counts),
            }
        )

        if (idx + 1) % 8 == 0 or (idx + 1) == len(candidate_records):
            status_cb(
                "skyline: response-frontier FG scored "
                f"{idx + 1}/{len(candidate_records)} candidates "
                f"(best_fg={int(best_fg_score)})"
            )

    deltas = [int(row["fg_delta"]) for row in telemetry_rows]
    elapsed_values_ms = [int(round(float(row["fg_elapsed_s"]) * 1000.0)) for row in telemetry_rows]
    topk_rows = [row for row in telemetry_rows if int(row["rank"]) <= int(topk_reference)]
    outside_rows = [row for row in telemetry_rows if int(row["rank"]) > int(topk_reference)]
    topk_best = max((int(row["fg_score"]) for row in topk_rows), default=0)
    outside_best_row = max(outside_rows, key=lambda row: int(row["fg_score"]), default=None)

    summary = {
        "candidate_count": int(len(candidate_records)),
        "exact_calls": int(len(prepared)),
        "response_frontier_calls": int(len(prepared)),
        "gpu_batches": int(batch_stats.get("gpu_batches", 0) if isinstance(batch_stats, dict) else 0),
        "batch_groups": int(batch_stats.get("groups", 0) if isinstance(batch_stats, dict) else 0),
        "fg_batch_input_genomes": int(
            batch_stats.get("input_genomes", len(prepared)) if isinstance(batch_stats, dict) else 0
        ),
        "fg_batch_unique_genomes": int(
            batch_stats.get("unique_genomes", len(prepared)) if isinstance(batch_stats, dict) else 0
        ),
        "fg_batch_deduped_genomes": int(batch_stats.get("deduped_genomes", 0) if isinstance(batch_stats, dict) else 0),
        "fg_batch_dedupe_groups": int(batch_stats.get("dedupe_groups", 0) if isinstance(batch_stats, dict) else 0),
        "ceiling_pruning_enabled": False,
        "hypothetical_skipped_by_ceiling": 0,
        "fg_gains": int(fg_gains),
        "best_fg_score": int(best_fg_score),
        "best_fg_base_score": _safe_int(best_record.get("fg_base_score", 0), 0) if best_record else 0,
        "topk_reference": int(topk_reference),
        "topk_best_fg_score": int(topk_best),
        "best_outside_topk_fg_score": int(outside_best_row["fg_score"]) if outside_best_row else 0,
        "best_outside_topk_rank": int(outside_best_row["rank"]) if outside_best_row else 0,
        "outside_topk_beats_topk": bool(
            outside_best_row is not None and int(outside_best_row["fg_score"]) > int(topk_best)
        ),
        "fg_elapsed_total_s": float(fg_elapsed_total),
        "fg_elapsed_p50_ms": int(_percentile_int(elapsed_values_ms, 50.0)),
        "fg_elapsed_p95_ms": int(_percentile_int(elapsed_values_ms, 95.0)),
        "fg_delta_max": int(max(deltas, default=0)),
        "fg_delta_p50": int(_percentile_int(deltas, 50.0)),
        "fg_delta_p95": int(_percentile_int(deltas, 95.0)),
    }
    if telemetry_enabled:
        summary["candidate_telemetry"] = list(telemetry_rows)
    return summary, best_record
