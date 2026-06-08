from __future__ import annotations

import time
from typing import Any, Callable

from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService

_TOPK_REFERENCE = 51


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


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

    topk_reference = int(_TOPK_REFERENCE)

    best_fg_score = max((_safe_int(rec.get("base_score", 0), 0) for rec in candidate_records), default=0)
    best_record: dict[str, Any] | None = None
    for rec in candidate_records:
        if _safe_int(rec.get("base_score", 0), 0) == int(best_fg_score):
            best_record = rec
            break

    call_t0 = time.perf_counter()
    scored_rows, batch_stats = FgResponseScoringService.score_candidates_with_stats(
        candidate_records,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        meta_primary_color=default_selected_color,
        gpu_client=None,
        mode="skyline",
    )
    fg_elapsed_total = float(time.perf_counter() - call_t0)
    if len(scored_rows) != len(candidate_records):
        raise RuntimeError("Skyline FG response-frontier scoring returned the wrong candidate count")
    fg_elapsed_each = float(fg_elapsed_total) / float(max(1, len(scored_rows)))

    fg_gains = 0
    telemetry_rows: list[dict[str, Any]] = []
    for idx, scored in enumerate(scored_rows):
        rec = scored.get("record")
        if rec is not candidate_records[idx]:
            raise RuntimeError("Skyline FG response-frontier scoring changed candidate order")
        data = rec.get("data")
        if not isinstance(data, dict) or not data:
            raise ValueError("skyline FG candidate record is missing data")
        force_payload = scored.get("force")
        if not isinstance(force_payload, dict) or not force_payload:
            raise RuntimeError("Skyline FG response-frontier scoring did not materialize a force payload")
        base_stats = dict(scored.get("base_stats") or {})
        base_score = _safe_int(scored.get("base_score", force_payload.get("BaseScore", rec.get("base_score", 0))), 0)
        fg_score = _safe_int(scored.get("fg_score", force_payload.get("Score", base_score)), base_score)
        fg_base_score = _safe_int(force_payload.get("BaseScore", base_score), base_score)

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
        "exact_calls": int(len(scored_rows)),
        "response_frontier_calls": int(len(scored_rows)),
        "gpu_batches": int(batch_stats.get("gpu_batches", 0) if isinstance(batch_stats, dict) else 0),
        "batch_groups": int(batch_stats.get("groups", 0) if isinstance(batch_stats, dict) else 0),
        "fg_batch_input_genomes": int(
            batch_stats.get("input_genomes", len(scored_rows)) if isinstance(batch_stats, dict) else 0
        ),
        "fg_batch_unique_genomes": int(
            batch_stats.get("unique_genomes", len(scored_rows)) if isinstance(batch_stats, dict) else 0
        ),
        "fg_batch_deduped_genomes": int(batch_stats.get("deduped_genomes", 0) if isinstance(batch_stats, dict) else 0),
        "fg_batch_dedupe_groups": int(batch_stats.get("dedupe_groups", 0) if isinstance(batch_stats, dict) else 0),
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
    return summary, best_record
