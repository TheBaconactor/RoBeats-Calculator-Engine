"""Offline candidate-ranking experiment for breakpoint-directed pressure.

This does not change production behavior and does not submit GPU work. It asks:
at the same retained-row budget, does a breakpoint-magnitude ordering capture
more FG-improving / FG-overall rows than the existing score ordering?
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

from tools.verify.analyze_combo_ramp_breakpoints import (  # noqa: E402
    Analyzer,
    _best_marginal,
    _score_floor_marginal,
    _timeline_marginal,
)


Scorer = Callable[[dict[str, Any]], float | int]
Picker = Callable[[list[dict[str, Any]], int], list[dict[str, Any]]]


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def _parse_ints(raw: str) -> list[int]:
    out: list[int] = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(max(1, int(part)))
        except Exception:
            continue
    return out or [3, 5, 10]


def _strategy_scorers() -> dict[str, Scorer]:
    return {
        "score_rank": lambda r: -_safe_int(r.get("rank"), 999999),
        "blended_marginal": _best_marginal,
        "timeline_marginal": _timeline_marginal,
        "score_floor_marginal": _score_floor_marginal,
        "deficit_aware_timeline": lambda r: _timeline_marginal(r) - max(0, _safe_int(r.get("base_deficit"))),
        "deficit_aware_blended": lambda r: _best_marginal(r) - max(0, _safe_int(r.get("base_deficit"))),
        "timeline_then_score": lambda r: (_timeline_marginal(r) * 1_000_000_000) + _safe_int(r.get("score")),
        "blended_then_score": lambda r: (_best_marginal(r) * 1_000_000_000) + _safe_int(r.get("score")),
    }


def _top_k(rows: list[dict[str, Any]], *, scorer: Scorer, k: int) -> list[dict[str, Any]]:
    limit = int(k)
    if limit <= 0:
        return []
    return sorted(rows, key=lambda r: (float(scorer(r)), _safe_int(r.get("score"))), reverse=True)[:limit]


def _merge_preserved_then_ranked(
    rows: list[dict[str, Any]], *, preserve_score_rows: int, scorer: Scorer, k: int
) -> list[dict[str, Any]]:
    limit = max(1, int(k))
    preserved = _top_k(rows, scorer=_strategy_scorers()["score_rank"], k=min(limit, int(preserve_score_rows)))
    seen = {id(row) for row in preserved}
    remaining = [row for row in rows if id(row) not in seen]
    return preserved + _top_k(remaining, scorer=scorer, k=max(0, limit - len(preserved)))


def _strategy_pickers() -> dict[str, Picker]:
    scorers = _strategy_scorers()
    return {
        "score_rank": lambda rows, k: _top_k(rows, scorer=scorers["score_rank"], k=k),
        "blended_marginal": lambda rows, k: _top_k(rows, scorer=scorers["blended_marginal"], k=k),
        "timeline_marginal": lambda rows, k: _top_k(rows, scorer=scorers["timeline_marginal"], k=k),
        "score_floor_marginal": lambda rows, k: _top_k(rows, scorer=scorers["score_floor_marginal"], k=k),
        "deficit_aware_timeline": lambda rows, k: _top_k(rows, scorer=scorers["deficit_aware_timeline"], k=k),
        "deficit_aware_blended": lambda rows, k: _top_k(rows, scorer=scorers["deficit_aware_blended"], k=k),
        "score1_then_timeline": lambda rows, k: _merge_preserved_then_ranked(
            rows, preserve_score_rows=1, scorer=scorers["timeline_marginal"], k=k
        ),
        "score2_then_timeline": lambda rows, k: _merge_preserved_then_ranked(
            rows, preserve_score_rows=2, scorer=scorers["timeline_marginal"], k=k
        ),
        "score1_then_blended": lambda rows, k: _merge_preserved_then_ranked(
            rows, preserve_score_rows=1, scorer=scorers["blended_marginal"], k=k
        ),
        "score2_then_blended": lambda rows, k: _merge_preserved_then_ranked(
            rows, preserve_score_rows=2, scorer=scorers["blended_marginal"], k=k
        ),
        "score2_then_def_timeline": lambda rows, k: _merge_preserved_then_ranked(
            rows, preserve_score_rows=2, scorer=scorers["deficit_aware_timeline"], k=k
        ),
        "score2_then_def_blended": lambda rows, k: _merge_preserved_then_ranked(
            rows, preserve_score_rows=2, scorer=scorers["deficit_aware_blended"], k=k
        ),
    }


def _summarize_picks(song_groups: dict[str, list[dict[str, Any]]], *, picker: Picker, k: int) -> dict[str, Any]:
    picked: list[dict[str, Any]] = []
    songs_with_fg_improve = 0
    songs_with_fg_overall = 0
    for rows in song_groups.values():
        top = picker(rows, int(k))
        picked.extend(top)
        if any(_safe_int(r.get("fg_lift")) > 0 for r in top):
            songs_with_fg_improve += 1
        if any(bool(r.get("fg_overall")) for r in top):
            songs_with_fg_overall += 1

    fg_lifts = [_safe_int(r.get("fg_lift")) for r in picked]
    return {
        "picked_rows": len(picked),
        "fg_improve_rows": sum(1 for r in picked if _safe_int(r.get("fg_lift")) > 0),
        "fg_overall_rows": sum(1 for r in picked if bool(r.get("fg_overall"))),
        "songs_with_fg_improve": songs_with_fg_improve,
        "songs_with_fg_overall": songs_with_fg_overall,
        "avg_fg_lift": round(mean(fg_lifts), 3) if fg_lifts else 0,
    }


def _diff_vs_baseline(summary: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "fg_improve_rows_delta": _safe_int(summary.get("fg_improve_rows")) - _safe_int(baseline.get("fg_improve_rows")),
        "fg_overall_rows_delta": _safe_int(summary.get("fg_overall_rows")) - _safe_int(baseline.get("fg_overall_rows")),
        "songs_with_fg_improve_delta": _safe_int(summary.get("songs_with_fg_improve"))
        - _safe_int(baseline.get("songs_with_fg_improve")),
        "songs_with_fg_overall_delta": _safe_int(summary.get("songs_with_fg_overall"))
        - _safe_int(baseline.get("songs_with_fg_overall")),
        "avg_fg_lift_delta": round(float(summary.get("avg_fg_lift", 0)) - float(baseline.get("avg_fg_lift", 0)), 3),
    }


def run_experiment(
    *,
    db_path: Path,
    team_buff: str,
    songs: list[str],
    per_bucket: int,
    max_rows_per_song: int,
    max_delta: int,
    budgets: list[int],
) -> dict[str, Any]:
    analyzer = Analyzer(db_path=db_path, team_buff=team_buff, max_delta=max_delta)
    report = analyzer.analyze(
        songs=songs,
        per_bucket=per_bucket,
        max_rows_per_song=max_rows_per_song,
        include_records=True,
    )
    records = list(report.get("records") or [])
    by_song: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_bucket_song: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in records:
        song = str(row.get("song") or "")
        bucket = str(row.get("bucket") or "unknown")
        if not song:
            continue
        by_song[song].append(row)
        by_bucket_song[bucket][song].append(row)

    strategies = _strategy_pickers()
    results: dict[str, Any] = {}
    for k in budgets:
        budget_result: dict[str, Any] = {}
        baseline = _summarize_picks(by_song, picker=strategies["score_rank"], k=k)
        for name, picker in strategies.items():
            summary = _summarize_picks(by_song, picker=picker, k=k)
            summary["vs_score_rank"] = _diff_vs_baseline(summary, baseline)
            budget_result[name] = summary
        results[str(k)] = budget_result

    bucket_results: dict[str, Any] = {}
    for bucket, groups in by_bucket_song.items():
        bucket_results[bucket] = {}
        for k in budgets:
            baseline = _summarize_picks(groups, picker=strategies["score_rank"], k=k)
            bucket_results[bucket][str(k)] = {
                name: {
                    **_summarize_picks(groups, picker=picker, k=k),
                    "vs_score_rank": _diff_vs_baseline(_summarize_picks(groups, picker=picker, k=k), baseline),
                }
                for name, picker in strategies.items()
            }

    return {
        "db": str(db_path),
        "team_buff": str(team_buff),
        "records": len(records),
        "songs": len(by_song),
        "max_rows_per_song": int(max_rows_per_song),
        "max_delta": int(max_delta),
        "budgets": budgets,
        "overall": results,
        "by_bucket": bucket_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark breakpoint candidate-ranking capture at equal row budget.")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "evolution.db"))
    parser.add_argument("--team-buff", default="T5")
    parser.add_argument("--song", action="append", default=[], help="Specific song name; can be repeated.")
    parser.add_argument("--per-bucket", type=int, default=20)
    parser.add_argument("--max-rows-per-song", type=int, default=30)
    parser.add_argument("--max-delta", type=int, default=30)
    parser.add_argument("--budgets", default="3,5,10")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_experiment(
        db_path=Path(args.db),
        team_buff=str(args.team_buff or "T5"),
        songs=list(args.song or []),
        per_bucket=max(1, int(args.per_bucket)),
        max_rows_per_song=max(1, int(args.max_rows_per_song)),
        max_delta=max(1, int(args.max_delta)),
        budgets=_parse_ints(args.budgets),
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    print("=" * 78)
    print("Breakpoint Candidate Ranking Experiment")
    print("=" * 78)
    print(f"DB: {result['db']}  TeamBuff: {result['team_buff']}")
    print(f"Checked {result['records']:,} rows across {result['songs']:,} songs")
    for budget in result["budgets"]:
        print(f"\nBudget top-{budget} per song")
        for name, summary in result["overall"][str(budget)].items():
            delta = summary["vs_score_rank"]
            print(
                f"  {name:<21} fg_rows={summary['fg_improve_rows']:<4} "
                f"overall={summary['fg_overall_rows']:<3} "
                f"songs_fg={summary['songs_with_fg_improve']:<3} "
                f"songs_overall={summary['songs_with_fg_overall']:<3} "
                f"avg_lift={summary['avg_fg_lift']:<10} "
                f"delta_fg={delta['fg_improve_rows_delta']:+} "
                f"delta_overall={delta['fg_overall_rows_delta']:+}"
            )


if __name__ == "__main__":
    main()
