from __future__ import annotations

import time
from typing import Any, Callable

from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.helpers.song_helpers.force_greats.bellman_fixed_adapter import (
    _fixed_note_surfaces,
    _fixed_stat_payloads_for_bellman,
)
from gear_optimizer.solver.force_greats_common import extract_base_stats
from gear_optimizer.solver.scoring.runtime_state import FORCE_GREATS_ALGO_VERSION
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.scoring.stats_scoring import _force_greats_counts_to_dict
from gear_optimizer.solver.taichi_gem.force_greats import solve_force_greats_bellman_fixed_stats_gpu


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


def _gem_count(gem_counts: Any, key: str) -> int:
    if not isinstance(gem_counts, dict):
        return 0
    return _safe_int(gem_counts.get(key, 0), 0)


def _stable_int_mapping_key(values: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((str(key), _safe_int(value, 0)) for key, value in dict(values or {}).items()))


def _solve_bellman_fixed_payload(
    *,
    stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
):
    song_inputs, normal, fever, penalty_prefix, raw_fill, non_fever_base, real_fever_time = _fixed_note_surfaces(
        stats,
        calc_song,
        ref_arrays,
    )
    bellman = solve_force_greats_bellman_fixed_stats_gpu(
        timestamps=song_inputs.timestamps,
        great_candidate_timestamps=song_inputs.great_candidates,
        raw_fever_fill=float(raw_fill),
        non_fever_base=int(non_fever_base),
        real_fever_time=float(real_fever_time),
        normal_score_per_note=normal,
        fever_score_per_note=fever,
        forced_great_penalty_prefix=penalty_prefix,
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )
    return bellman, int(non_fever_base)


def _empty_bellman_batch_stats() -> dict[str, int]:
    return {
        "gpu_batches": 0,
        "groups": 0,
        "input_genomes": 0,
        "unique_genomes": 0,
        "deduped_genomes": 0,
        "dedupe_groups": 0,
    }


def _score_skyline_bellman_force_greats_batch(
    *,
    prepared: list[dict[str, Any]],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> tuple[list[dict[str, Any] | None], dict[str, int]]:
    if not prepared:
        return [], _empty_bellman_batch_stats()

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    total_notes = int(len(timestamps)) if timestamps is not None else 0
    if total_notes <= 0:
        return [None for _ in prepared], _empty_bellman_batch_stats()

    results: list[dict[str, Any] | None] = [None for _ in prepared]
    result_cache: dict[tuple[Any, ...], dict[str, Any] | None] = {}
    result_cache_hits = 0
    cache_member_counts: dict[tuple[Any, ...], int] = {}
    group_keys: set[tuple[Any, ...]] = set()
    gpu_batches = 0
    input_genomes = 0

    for idx, prep in enumerate(prepared):
        data = prep["data"]
        base_stats = dict(prep["base_stats"])
        base_score = _safe_int(prep.get("base_score", 0), 0)
        selected_color = str(prep.get("selected_color", "") or "")
        center_ft = _safe_int(prep.get("center_ft", 0), 0)
        center_ff = _safe_int(prep.get("center_ff", 0), 0)
        gem_counts = dict(data.get("GemCounts") or {}) if isinstance(data.get("GemCounts"), dict) else {}

        input_genomes += 1
        group_keys.add((selected_color,))

        result_key = (
            selected_color,
            _stable_int_mapping_key(base_stats),
            _stable_int_mapping_key(gem_counts),
            int(center_ft),
            int(center_ff),
        )
        cache_member_counts[result_key] = int(cache_member_counts.get(result_key, 0)) + 1
        if result_key in result_cache:
            cached = result_cache[result_key]
            results[idx] = dict(cached) if isinstance(cached, dict) else None
            result_cache_hits += 1
            continue

        eval_data = dict(data)
        eval_data["BaseStats"] = dict(base_stats)
        eval_data["GemCounts"] = dict(gem_counts)
        eval_data["FT"] = int(center_ft)
        eval_data["FF"] = int(center_ff)
        eval_data["Selected Element"] = selected_color
        eval_data["BaseScore"] = int(base_score)
        eval_data["Score"] = int(base_score)

        best_result: dict[str, Any] | None = None
        for fixed_eval_data, stats, fixed_base_score in _fixed_stat_payloads_for_bellman(
            eval_data,
            selected=selected_color,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            paired_base_score=int(base_score),
        ):
            bellman, non_fever_base = _solve_bellman_fixed_payload(
                stats=stats,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
            )
            gpu_batches += 1
            forced_counts = tuple(int(value) for value in bellman.best_forced_counts)
            if not forced_counts or max(forced_counts) <= 0:
                continue
            if int(bellman.best_score) <= int(fixed_base_score):
                continue

            variant_gem_counts = (
                dict(fixed_eval_data.get("GemCounts") or {}) if isinstance(fixed_eval_data, dict) else {}
            )
            candidate_result = {
                "base_score": int(fixed_base_score),
                "final_score": int(bellman.best_score),
                "score_penalty": 0,
                "fill_penalty": 0,
                "total_penalty": 0,
                "num_non_fever_sections": int(bellman.section_count),
                "penalty_analysis": {},
                "config_counts": list(forced_counts),
                "config_dict": _force_greats_counts_to_dict(list(forced_counts), max(2, len(forced_counts))),
                "non_fever_base": int(non_fever_base),
                "gem_counts": dict(variant_gem_counts),
                "FT": _safe_int(fixed_eval_data.get("FT", center_ft), center_ft),
                "FF": _safe_int(fixed_eval_data.get("FF", center_ff), center_ff),
            }
            if best_result is None or int(candidate_result["final_score"]) > int(best_result["final_score"]):
                best_result = candidate_result

        results[idx] = best_result
        result_cache[result_key] = dict(best_result) if isinstance(best_result, dict) else None

    return results, {
        "gpu_batches": int(gpu_batches),
        "groups": int(len(group_keys)),
        "input_genomes": int(input_genomes),
        "unique_genomes": int(len(result_cache)),
        "deduped_genomes": int(result_cache_hits),
        "dedupe_groups": sum(1 for count in cache_member_counts.values() if int(count) > 1),
    }


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


def _materialize_force_payload(
    *,
    base_data: dict[str, Any],
    base_stats: dict[str, Any],
    fg_result: dict[str, Any],
    selected_color: str,
    center_ft: int,
    center_ff: int,
) -> dict[str, Any]:
    final_score = _safe_int(fg_result.get("final_score", 0), 0)
    fg_ft = _safe_int(fg_result.get("FT", center_ft), center_ft)
    fg_ff = _safe_int(fg_result.get("FF", center_ff), center_ff)
    gem_counts = fg_result.get("gem_counts") if isinstance(fg_result.get("gem_counts"), dict) else {}

    g_pp = _gem_count(gem_counts, "Perfect Points")
    g_cm = _gem_count(gem_counts, "Combo Multiplier")
    g_fm = _gem_count(gem_counts, "Fever Multiplier")
    g_ov = _gem_count(gem_counts, "Element")

    force_payload = dict(base_data)
    force_payload["BaseScore"] = _safe_int(
        fg_result.get("base_score", base_data.get("BaseScore", base_data.get("Score", 0))),
        0,
    )
    force_payload["Score"] = int(final_score)
    force_payload["FT"] = int(fg_ft)
    force_payload["FF"] = int(fg_ff)
    force_payload["GemCounts"] = dict(gem_counts)
    force_payload["BaseStats"] = dict(base_stats)
    force_payload["Stats"] = apply_gems_to_base_stats(
        base_stats,
        str(selected_color or ""),
        int(fg_ft),
        int(fg_ff),
        int(g_pp),
        int(g_cm),
        int(g_fm),
        int(g_ov),
        add_missing_element_key=True,
    )
    force_payload["ForceGreats"] = {
        "enabled": True,
        "mode": "bellman",
        "algo_version": int(FORCE_GREATS_ALGO_VERSION),
        "center_ft": int(center_ft),
        "center_ff": int(center_ff),
        "config": fg_result.get("config_dict", {}) or {},
        "final_score": int(final_score),
    }
    force_payload["forced_counts"] = list(fg_result.get("config_counts") or [])
    return force_payload


def score_retained_skyline_force_greats(
    candidate_records: list[dict[str, Any]],
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    default_selected_color: str,
    use_gpu: bool,
    status_cb: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """
    Score retained skyline candidates on the production ForceGreats surface.

    This is intentionally candidate-local: skyline supplies a retained loadout, then
    FG solves the joint gem allocation + forced-great configuration for that loadout.
    It does not enable any FG ceiling pruning.
    """
    if not use_gpu:
        raise RuntimeError("Skyline native FG is GPU-only; CPU FG scoring is not a production path.")

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
        center_ft = _safe_int(data.get("FT", 0), 0)
        center_ff = _safe_int(data.get("FF", 0), 0)

        prepared.append(
            {
                "idx": int(idx),
                "rec": rec,
                "data": data,
                "base_score": int(base_score),
                "selected_color": selected_color,
                "base_stats": base_stats,
                "center_ft": int(center_ft),
                "center_ff": int(center_ff),
            }
        )

    call_t0 = time.perf_counter()
    fg_results, batch_stats = _score_skyline_bellman_force_greats_batch(
        prepared=prepared,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    fg_elapsed_total = float(time.perf_counter() - call_t0)
    exact_calls = int(len(prepared))
    fg_elapsed_each = float(fg_elapsed_total) / float(max(1, len(prepared)))

    fg_gains = 0
    telemetry_rows: list[dict[str, Any]] = []

    for idx, prep in enumerate(prepared):
        rec = prep["rec"]
        data = prep["data"]
        base_score = int(prep["base_score"])
        selected_color = str(prep["selected_color"])
        base_stats = dict(prep["base_stats"])
        center_ft = int(prep["center_ft"])
        center_ff = int(prep["center_ff"])
        fg_result = fg_results[idx] if idx < len(fg_results) else None
        fg_elapsed = float(fg_elapsed_each)

        fg_score = base_score
        fg_base_score = base_score
        force_payload = None
        if isinstance(fg_result, dict) and fg_result:
            fg_score = _safe_int(fg_result.get("final_score", base_score), base_score)
            fg_base_score = _safe_int(fg_result.get("base_score", base_score), base_score)
            force_payload = _materialize_force_payload(
                base_data=data,
                base_stats=base_stats,
                fg_result=fg_result,
                selected_color=selected_color,
                center_ft=center_ft,
                center_ff=center_ff,
            )

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
        rec["fg_elapsed_s"] = float(fg_elapsed)

        rank = int(idx + 1)
        force_counts = []
        force_gem_counts = {}
        force_ft = center_ft
        force_ff = center_ff
        if isinstance(force_payload, dict):
            force_counts = _int_list(force_payload.get("forced_counts"))
            force_gem_counts = (
                dict(force_payload.get("GemCounts") or {}) if isinstance(force_payload.get("GemCounts"), dict) else {}
            )
            force_ft = _safe_int(force_payload.get("FT", center_ft), center_ft)
            force_ff = _safe_int(force_payload.get("FF", center_ff), center_ff)

        telemetry_row = {
            "rank": int(rank),
            "sample_source": str(rec.get("sample_source", "") or ""),
            "base_score": int(base_score),
            "base_gap_to_best": int(max(0, int(candidate_records[0].get("base_score", 0) or 0) - int(base_score)))
            if candidate_records
            else 0,
            "fg_score": int(fg_score),
            "fg_delta": int(fg_delta),
            "fg_base_score": int(fg_base_score),
            "fg_elapsed_s": float(fg_elapsed),
            "gear_names": _genome_names(rec.get("genome"), 0, 6),
            "mini_names": _genome_names(rec.get("genome"), 6, 9),
            "genome_ids": list(data.get("GenomeIDs") or []) if isinstance(data.get("GenomeIDs"), list) else [],
            "ft": int(center_ft),
            "ff": int(center_ff),
            "fg_ft": int(force_ft),
            "fg_ff": int(force_ff),
            "fg_gem_pp": _gem_count(force_gem_counts, "Perfect Points"),
            "fg_gem_cm": _gem_count(force_gem_counts, "Combo Multiplier"),
            "fg_gem_fm": _gem_count(force_gem_counts, "Fever Multiplier"),
            "fg_gem_element": _gem_count(force_gem_counts, "Element"),
            "base_pp": int(base_stats.get("Perfect Points", 0) or 0),
            "base_cm": int(base_stats.get("Combo Multiplier", 0) or 0),
            "base_fm": int(base_stats.get("Fever Multiplier", 0) or 0),
            "base_ft": int(base_stats.get("Fever Time", 0) or 0),
            "base_ff": int(base_stats.get("Fever Fill Rate", 0) or 0),
            "base_primary": int(base_stats.get(str(calc_song.get("metadata", {}).get("Primary Color", "")), 0) or 0),
            "base_secondary": int(
                base_stats.get(str(calc_song.get("metadata", {}).get("Secondary Color", "")), 0) or 0
            ),
            "force_count_sum": int(sum(int(x) for x in force_counts)) if force_counts else 0,
            "force_sections": int(len(force_counts)),
            "force_counts": list(force_counts),
        }
        telemetry_rows.append(telemetry_row)

        if (idx + 1) % 16 == 0 or (idx + 1) == len(candidate_records):
            status_cb(
                "skyline: native FG scored "
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
        "mode": "skyline_bellman_fixed_gpu",
        "candidate_count": int(len(candidate_records)),
        "bucket_count": 0,
        "ceiling_dp_calls": 0,
        "exact_calls": int(exact_calls),
        "bellman_calls": int(exact_calls),
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
        "best_fg_base_score": _safe_int(best_record.get("base_score", 0), 0) if best_record else 0,
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
