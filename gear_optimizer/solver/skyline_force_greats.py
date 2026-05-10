from __future__ import annotations

import time
from typing import Any, Callable

from gear_optimizer.core.constants import FG_SEARCH_RADIUS, GEM_SCALE_FEVER
from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.solver.force_greats_common import extract_base_stats
from gear_optimizer.solver.native_force_greats import solve_native_force_greats_gpu_batch
from gear_optimizer.solver.analytical_fg import create_scorer_from_calc_song
from gear_optimizer.solver.scoring.gpu_solver import FORCE_GREATS_ALGO_VERSION
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats


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


def _int_total(value: Any) -> int:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        return int(sum(_int_total(item) for item in value))
    return _safe_int(value, 0)


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


def _timeline_probe_for_candidate(
    *,
    timeline_scorer: Any,
    base_stats: dict[str, Any],
    center_ft: int,
    center_ff: int,
    force_counts: list[int],
) -> dict[str, Any]:
    """
    Research-only structural FG telemetry at the base candidate's FT/FF center.

    This is deliberately not a pruning certificate. It asks whether a tiny
    forced-great nudge changes the timeline around the base-center FT/FF point,
    so we can study why FG helps or fails without turning the observation into
    an unsafe skip rule.
    """

    if timeline_scorer is None:
        return {}

    try:
        ft_stat = _safe_int(base_stats.get("Fever Time", 0), 0) + int(center_ft) * int(GEM_SCALE_FEVER)
        ff_stat = _safe_int(base_stats.get("Fever Fill Rate", 0), 0) + int(center_ff) * int(GEM_SCALE_FEVER)
        analysis = timeline_scorer.get_section_analysis(int(ft_stat), int(ff_stat))
        if not isinstance(analysis, dict):
            analysis = {}

        useful_sections = _safe_int(analysis.get("useful_sections", 0), 0)
        probe_sections = max(1, min(max(int(useful_sections), len(force_counts), 1), 4))

        zero_counts = [0] * int(probe_sections)
        _, base_body_fever, base_body_normal, _ = timeline_scorer.compute_timeline_with_forced(
            int(ft_stat),
            int(ff_stat),
            zero_counts,
        )

        forced_probe_counts = list(force_counts[:probe_sections])
        if len(forced_probe_counts) < probe_sections:
            forced_probe_counts.extend([0] * (probe_sections - len(forced_probe_counts)))

        _, forced_body_fever, forced_body_normal, _ = timeline_scorer.compute_timeline_with_forced(
            int(ft_stat),
            int(ff_stat),
            forced_probe_counts,
        )

        base_fever_total = _int_total(base_body_fever)
        base_normal_total = _int_total(base_body_normal)
        forced_fever_total = _int_total(forced_body_fever)
        forced_normal_total = _int_total(forced_body_normal)

        single_nudge_changed = 0
        single_nudge_max_fever_delta = 0
        single_nudge_max_normal_delta = 0
        for section_idx in range(int(probe_sections)):
            one_count = [0] * int(probe_sections)
            one_count[section_idx] = 1
            _, one_body_fever, one_body_normal, _ = timeline_scorer.compute_timeline_with_forced(
                int(ft_stat),
                int(ff_stat),
                one_count,
            )
            fever_delta = _int_total(one_body_fever) - int(base_fever_total)
            normal_delta = _int_total(one_body_normal) - int(base_normal_total)
            if fever_delta != 0 or normal_delta != 0:
                single_nudge_changed += 1
            single_nudge_max_fever_delta = max(int(single_nudge_max_fever_delta), int(fever_delta))
            single_nudge_max_normal_delta = max(int(single_nudge_max_normal_delta), int(normal_delta))

        return {
            "timeline_probe_scope": "base_center_ftff",
            "timeline_probe_ft_stat": int(ft_stat),
            "timeline_probe_ff_stat": int(ff_stat),
            "timeline_useful_sections": int(useful_sections),
            "timeline_probe_sections": int(probe_sections),
            "timeline_gap": _safe_int(analysis.get("gap", analysis.get("current_gap", 0)), 0),
            "timeline_non_fever_base": _safe_int(analysis.get("non_fever_base", 0), 0),
            "timeline_base_body_fever": int(base_fever_total),
            "timeline_base_body_normal": int(base_normal_total),
            "timeline_force_body_fever_delta": int(forced_fever_total - base_fever_total),
            "timeline_force_body_normal_delta": int(forced_normal_total - base_normal_total),
            "timeline_single_nudge_sections_changed": int(single_nudge_changed),
            "timeline_single_nudge_max_body_fever_delta": int(single_nudge_max_fever_delta),
            "timeline_single_nudge_max_body_normal_delta": int(single_nudge_max_normal_delta),
        }
    except (ArithmeticError, IndexError, KeyError, TypeError, ValueError) as exc:
        return {"timeline_probe_error": f"{type(exc).__name__}: {exc}"}


def _materialize_force_payload(
    *,
    base_data: dict[str, Any],
    base_stats: dict[str, Any],
    fg_result: dict[str, Any],
    selected_color: str,
    search_radius: int | None,
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
        "mode": "finder",
        "algo_version": int(FORCE_GREATS_ALGO_VERSION),
        "search_radius": None if search_radius is None else int(search_radius),
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
    search_radius: int | None,
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

    radius = FG_SEARCH_RADIUS if search_radius is None else int(search_radius)
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

        if int(radius) < 0:
            center_ft_arg = None
            center_ff_arg = None
            radius_arg = None
        else:
            center_ft_arg = int(center_ft)
            center_ff_arg = int(center_ff)
            radius_arg = int(radius)

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
                "center_ft_arg": center_ft_arg,
                "center_ff_arg": center_ff_arg,
                "radius_arg": radius_arg,
            }
        )

    call_t0 = time.perf_counter()
    fg_results, batch_stats = solve_native_force_greats_gpu_batch(
        base_stats_list=[dict(item["base_stats"]) for item in prepared],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_colors=[str(item["selected_color"]) for item in prepared],
        center_fts=[item["center_ft_arg"] for item in prepared],
        center_ffs=[item["center_ff_arg"] for item in prepared],
        search_radius=prepared[0]["radius_arg"] if prepared else None,
    )
    fg_elapsed_total = float(time.perf_counter() - call_t0)
    exact_calls = int(len(prepared))
    fg_elapsed_each = float(fg_elapsed_total) / float(max(1, len(prepared)))

    fg_gains = 0
    telemetry_rows: list[dict[str, Any]] = []
    timeline_scorer = create_scorer_from_calc_song(calc_song, ref_arrays) if telemetry_enabled else None

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
                search_radius=None if search_radius is None else int(search_radius),
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
        telemetry_row.update(
            _timeline_probe_for_candidate(
                timeline_scorer=timeline_scorer,
                base_stats=base_stats,
                center_ft=center_ft,
                center_ff=center_ff,
                force_counts=force_counts,
            )
        )
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
        "mode": "native_joint_gem_gpu",
        "candidate_count": int(len(candidate_records)),
        "bucket_count": 0,
        "ceiling_dp_calls": 0,
        "exact_calls": int(exact_calls),
        "exact_dp_calls": int(exact_calls),
        "gpu_batches": int(batch_stats.get("gpu_batches", 0) if isinstance(batch_stats, dict) else 0),
        "batch_groups": int(batch_stats.get("groups", 0) if isinstance(batch_stats, dict) else 0),
        "ceiling_pruning_enabled": False,
        "hypothetical_skipped_by_ceiling": 0,
        "fg_gains": int(fg_gains),
        "best_fg_score": int(best_fg_score),
        "best_fg_base_score": _safe_int(best_record.get("base_score", 0), 0) if best_record else 0,
        "topk_reference": int(topk_reference),
        "topk_best_fg_score": int(topk_best),
        "best_outside_topk_fg_score": int(outside_best_row["fg_score"]) if outside_best_row else 0,
        "best_outside_topk_rank": int(outside_best_row["rank"]) if outside_best_row else 0,
        "outside_topk_beats_topk": bool(outside_best_row is not None and int(outside_best_row["fg_score"]) > int(topk_best)),
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
