"""Validate Near-Winner Frontier candidates against observed FG-overall rows.

This is an offline/shadow verifier. It does not change production selection and
does not submit GPU work. It evaluates candidate "possible FG lift" functions for
the theorem shape:

    base_deficit <= conservative_possible_lift

Rows outside that frontier would be considered FG-overall-doomed by the tested
bound. Any observed FG-overall row outside the frontier is therefore a miss for
that bound.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.verify.analyze_combo_ramp_breakpoints import Analyzer  # noqa: E402


BoundFn = Callable[[dict[str, Any]], int]


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return float(default)


def _parse_ints(raw: str) -> list[int]:
    out: list[int] = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(max(0, int(part)))
    return out or [0]


def _best_weighted(row: dict[str, Any]) -> int:
    return max(
        _safe_int(row.get("marginal_ft_weighted")),
        _safe_int(row.get("marginal_ff_weighted")),
        _safe_int(row.get("marginal_pp_weighted")),
        _safe_int(row.get("marginal_cm_weighted")),
        _safe_int(row.get("marginal_fm_weighted")),
    )


def _timeline_weighted(row: dict[str, Any]) -> int:
    return max(_safe_int(row.get("marginal_ft_weighted")), _safe_int(row.get("marginal_ff_weighted")))


def _score_floor_weighted(row: dict[str, Any]) -> int:
    return max(
        _safe_int(row.get("marginal_pp_weighted")),
        _safe_int(row.get("marginal_cm_weighted")),
        _safe_int(row.get("marginal_fm_weighted")),
    )


def _make_bound(name: str, margin: int, scale: float) -> BoundFn:
    margin = max(0, int(margin))
    scale = max(0.0, float(scale))

    if name == "oracle_actual_lift":
        return lambda row: max(0, _safe_int(row.get("fg_lift"))) + margin
    if name == "observed_song_best_lift":
        # Filled later by annotating each row with the max observed retained lift
        # for that song. This is not production-usable, but it shows the ideal
        # shape of a song-local conservative cap.
        return lambda row: max(0, _safe_int(row.get("_song_best_lift"))) + margin
    if name == "global_constant":
        return lambda row: margin
    if name == "breakpoint_weighted":
        return lambda row: int(round(_best_weighted(row) * scale)) + margin
    if name == "timeline_weighted":
        return lambda row: int(round(_timeline_weighted(row) * scale)) + margin
    if name == "score_floor_weighted":
        return lambda row: int(round(_score_floor_weighted(row) * scale)) + margin
    raise ValueError(f"unknown bound: {name}")


def _annotate_song_best_lift(records: list[dict[str, Any]]) -> None:
    best_by_song: dict[str, int] = defaultdict(int)
    for row in records:
        song = str(row.get("song") or "")
        best_by_song[song] = max(best_by_song[song], max(0, _safe_int(row.get("fg_lift"))))
    for row in records:
        row["_song_best_lift"] = int(best_by_song.get(str(row.get("song") or ""), 0))


def _summarize_frontier(records: list[dict[str, Any]], *, bound_name: str, margin: int, scale: float) -> dict[str, Any]:
    bound = _make_bound(bound_name, margin, scale)
    checked = len(records)
    kept = 0
    missed_overall = 0
    total_overall = 0
    total_improving = 0
    missed_examples: list[dict[str, Any]] = []
    kept_deficits: list[int] = []
    missed_gaps: list[int] = []
    by_bucket: dict[str, dict[str, int]] = defaultdict(
        lambda: {"checked": 0, "kept": 0, "fg_overall": 0, "missed_overall": 0}
    )

    for row in records:
        possible_lift = max(0, int(bound(row)))
        deficit = max(0, _safe_int(row.get("base_deficit")))
        in_frontier = deficit <= possible_lift
        fg_overall = bool(row.get("fg_overall"))
        fg_improving = _safe_int(row.get("fg_lift")) > 0
        bucket = str(row.get("bucket") or "unknown")

        kept += int(in_frontier)
        total_overall += int(fg_overall)
        total_improving += int(fg_improving)
        kept_deficits.append(deficit) if in_frontier else None

        bucket_counts = by_bucket[bucket]
        bucket_counts["checked"] += 1
        bucket_counts["kept"] += int(in_frontier)
        bucket_counts["fg_overall"] += int(fg_overall)
        bucket_counts["missed_overall"] += int(fg_overall and not in_frontier)

        if fg_overall and not in_frontier:
            missed_overall += 1
            missed_gaps.append(deficit - possible_lift)
            if len(missed_examples) < 10:
                missed_examples.append(
                    {
                        "song": row.get("song"),
                        "bucket": bucket,
                        "rank": row.get("rank"),
                        "score": row.get("score"),
                        "fg_score": row.get("fg_score"),
                        "fg_lift": row.get("fg_lift"),
                        "base_deficit": deficit,
                        "possible_lift": possible_lift,
                        "gap": deficit - possible_lift,
                    }
                )

    reduction = 1.0 - (float(kept) / float(checked)) if checked else 0.0
    return {
        "bound": bound_name,
        "margin": int(margin),
        "scale": float(scale),
        "checked": checked,
        "kept_frontier": kept,
        "outside_frontier": checked - kept,
        "outside_rate": round(reduction, 4),
        "fg_improving_rows": total_improving,
        "fg_overall_rows": total_overall,
        "missed_fg_overall": missed_overall,
        "miss_rate_overall": round(float(missed_overall) / float(total_overall), 4) if total_overall else 0.0,
        "avg_kept_deficit": round(mean(kept_deficits), 3) if kept_deficits else 0,
        "max_missed_gap": max(missed_gaps) if missed_gaps else 0,
        "by_bucket": dict(sorted(by_bucket.items())),
        "missed_examples": missed_examples,
    }


def run_validation(
    *,
    db_path: Path,
    team_buff: str,
    songs: list[str],
    per_bucket: int,
    max_rows_per_song: int,
    max_delta: int,
    margins: list[int],
    scales: list[int],
) -> dict[str, Any]:
    analyzer = Analyzer(db_path=db_path, team_buff=team_buff, max_delta=max_delta)
    report = analyzer.analyze(
        songs=songs,
        per_bucket=per_bucket,
        max_rows_per_song=max_rows_per_song,
        include_records=True,
    )
    records = list(report.get("records") or [])
    _annotate_song_best_lift(records)

    results: list[dict[str, Any]] = []
    for bound_name in (
        "oracle_actual_lift",
        "observed_song_best_lift",
        "global_constant",
        "breakpoint_weighted",
        "timeline_weighted",
        "score_floor_weighted",
    ):
        for margin in margins:
            if bound_name in {"breakpoint_weighted", "timeline_weighted", "score_floor_weighted"}:
                for scale in scales:
                    results.append(_summarize_frontier(records, bound_name=bound_name, margin=margin, scale=scale))
            else:
                results.append(_summarize_frontier(records, bound_name=bound_name, margin=margin, scale=1.0))

    return {
        "db": str(db_path),
        "team_buff": str(team_buff),
        "records": len(records),
        "songs": len({str(row.get("song") or "") for row in records}),
        "max_rows_per_song": int(max_rows_per_song),
        "max_delta": int(max_delta),
        "margins": margins,
        "scales": scales,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Near-Winner Frontier bound candidates.")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "evolution.db"))
    parser.add_argument("--team-buff", default="T5")
    parser.add_argument("--song", action="append", default=[], help="Specific song name; can be repeated.")
    parser.add_argument("--per-bucket", type=int, default=20)
    parser.add_argument("--max-rows-per-song", type=int, default=30)
    parser.add_argument("--max-delta", type=int, default=30)
    parser.add_argument("--margins", default="0,50000,100000,200000,500000")
    parser.add_argument("--scales", default="1,2,4,8")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_validation(
        db_path=Path(args.db),
        team_buff=str(args.team_buff or "T5"),
        songs=list(args.song or []),
        per_bucket=max(1, int(args.per_bucket)),
        max_rows_per_song=max(1, int(args.max_rows_per_song)),
        max_delta=max(1, int(args.max_delta)),
        margins=_parse_ints(args.margins),
        scales=[max(1, v) for v in _parse_ints(args.scales)],
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    print("=" * 78)
    print("Near-Winner Frontier Validation")
    print("=" * 78)
    print(f"DB: {result['db']}  TeamBuff: {result['team_buff']}")
    print(f"Checked {result['records']:,} rows across {result['songs']:,} songs")
    print()
    for row in result["results"]:
        print(
            f"{row['bound']:<24} margin={row['margin']:<8} scale={row['scale']:<4} "
            f"kept={row['kept_frontier']:<5}/{row['checked']:<5} "
            f"outside={row['outside_rate']:<6} "
            f"overall={row['fg_overall_rows']:<4} missed={row['missed_fg_overall']:<4} "
            f"max_gap={row['max_missed_gap']}"
        )
        if row["missed_examples"]:
            for ex in row["missed_examples"][:3]:
                print(
                    f"  miss {str(ex['song'])[:58]} | def={ex['base_deficit']:,} "
                    f"lift={ex['fg_lift']:,} bound={ex['possible_lift']:,}"
                )
    print()
    print("Note: only bounds with missed=0 are empirically safe for this sample;")
    print("      empirical safety is not a proof unless the bound is proven conservative.")


if __name__ == "__main__":
    main()
