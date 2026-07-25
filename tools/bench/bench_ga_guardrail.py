from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.utils import safe_float as _safe_float, safe_int as _safe_int
from tools.bench.bench_ga_winner_stability import run_benchmark


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _depth_keys(payload: dict[str, Any]) -> list[str]:
    summary = payload.get("summary_by_depth") or {}
    return sorted(summary.keys(), key=lambda v: int(v))


def _metric_mean(summary: dict[str, Any], key: str) -> float:
    value = summary.get(key, 0.0)
    if isinstance(value, dict):
        return _safe_float(value.get("mean", 0.0), 0.0)
    return _safe_float(value, 0.0)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Compare GA stability benchmark outputs against a saved baseline.")
    ap.add_argument("--baseline", required=True, help="Baseline JSON produced by bench_ga_winner_stability.")
    ap.add_argument(
        "--candidate", default="", help="Existing candidate JSON. If omitted, a fresh candidate run is executed."
    )
    ap.add_argument("--config", default="config.ini")
    ap.add_argument("--song-name", default="")
    ap.add_argument("--difficulty", default="")
    ap.add_argument("--depths", default="")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--ga-multi-start", type=int, default=0)
    ap.add_argument("--fg-candidate-limit", type=int, default=0)
    ap.add_argument("--db-path", default="")
    ap.add_argument(
        "--candidate-out",
        default=str(Path("artifacts") / "runcheck" / "ga_guardrail_candidate.json"),
        help="Where to write the generated candidate JSON when --candidate is omitted.",
    )
    ap.add_argument(
        "--out",
        default=str(Path("artifacts") / "runcheck" / "ga_guardrail_report.json"),
        help="Where to write the comparison report.",
    )
    ap.add_argument("--max-base-score-drop", type=float, default=0.0)
    ap.add_argument("--max-fg-score-drop", type=float, default=0.0)
    ap.add_argument("--max-duplicate-ratio-increase", type=float, default=0.0)
    ap.add_argument("--max-error-run-increase", type=int, default=0)
    ap.add_argument("--max-elapsed-increase-pct", type=float, default=0.10)
    return ap


def compare_payloads(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    max_base_score_drop: float,
    max_fg_score_drop: float,
    max_duplicate_ratio_increase: float,
    max_error_run_increase: int,
    max_elapsed_increase_pct: float,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    for key in ("song_name", "difficulty"):
        if str(baseline.get(key, "") or "") != str(candidate.get(key, "") or ""):
            findings.append(
                {
                    "kind": "metadata_mismatch",
                    "metric": key,
                    "baseline": baseline.get(key),
                    "candidate": candidate.get(key),
                    "message": f"{key} does not match baseline.",
                }
            )

    baseline_depths = _depth_keys(baseline)
    candidate_depths = _depth_keys(candidate)
    if baseline_depths != candidate_depths:
        findings.append(
            {
                "kind": "metadata_mismatch",
                "metric": "depths",
                "baseline": baseline_depths,
                "candidate": candidate_depths,
                "message": "Depth keys do not match baseline.",
            }
        )
        return {"pass": False, "findings": findings}

    for depth in baseline_depths:
        base_summary = (baseline.get("summary_by_depth") or {}).get(depth) or {}
        cand_summary = (candidate.get("summary_by_depth") or {}).get(depth) or {}

        base_score_mean = _metric_mean(base_summary, "base_score")
        cand_score_mean = _metric_mean(cand_summary, "base_score")
        if cand_score_mean < base_score_mean - float(max_base_score_drop):
            findings.append(
                {
                    "kind": "regression",
                    "depth": int(depth),
                    "metric": "base_score.mean",
                    "baseline": base_score_mean,
                    "candidate": cand_score_mean,
                    "allowed_drop": float(max_base_score_drop),
                    "message": "Candidate base-score mean regressed beyond threshold.",
                }
            )

        base_fg_mean = _metric_mean(base_summary, "fg_score")
        cand_fg_mean = _metric_mean(cand_summary, "fg_score")
        if cand_fg_mean < base_fg_mean - float(max_fg_score_drop):
            findings.append(
                {
                    "kind": "regression",
                    "depth": int(depth),
                    "metric": "fg_score.mean",
                    "baseline": base_fg_mean,
                    "candidate": cand_fg_mean,
                    "allowed_drop": float(max_fg_score_drop),
                    "message": "Candidate FG-score mean regressed beyond threshold.",
                }
            )

        base_dup_mean = _metric_mean(base_summary, "duplicate_genome_ratio")
        cand_dup_mean = _metric_mean(cand_summary, "duplicate_genome_ratio")
        if cand_dup_mean > base_dup_mean + float(max_duplicate_ratio_increase):
            findings.append(
                {
                    "kind": "regression",
                    "depth": int(depth),
                    "metric": "duplicate_genome_ratio.mean",
                    "baseline": base_dup_mean,
                    "candidate": cand_dup_mean,
                    "allowed_increase": float(max_duplicate_ratio_increase),
                    "message": "Candidate duplicate-genome ratio increased beyond threshold.",
                }
            )

        base_error_runs = _safe_int(base_summary.get("error_runs", 0), 0)
        cand_error_runs = _safe_int(cand_summary.get("error_runs", 0), 0)
        if cand_error_runs > base_error_runs + int(max_error_run_increase):
            findings.append(
                {
                    "kind": "regression",
                    "depth": int(depth),
                    "metric": "error_runs",
                    "baseline": base_error_runs,
                    "candidate": cand_error_runs,
                    "allowed_increase": int(max_error_run_increase),
                    "message": "Candidate error-run count increased beyond threshold.",
                }
            )

        base_elapsed_mean = _metric_mean(base_summary, "elapsed_wall_sec")
        cand_elapsed_mean = _metric_mean(cand_summary, "elapsed_wall_sec")
        allowed_elapsed = base_elapsed_mean * (1.0 + float(max_elapsed_increase_pct))
        if cand_elapsed_mean > allowed_elapsed:
            findings.append(
                {
                    "kind": "regression",
                    "depth": int(depth),
                    "metric": "elapsed_wall_sec.mean",
                    "baseline": base_elapsed_mean,
                    "candidate": cand_elapsed_mean,
                    "allowed_max": allowed_elapsed,
                    "message": "Candidate elapsed mean increased beyond threshold.",
                }
            )

    return {"pass": not findings, "findings": findings}


def _resolve_candidate_payload(args: argparse.Namespace, baseline: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if str(args.candidate or "").strip():
        path = Path(str(args.candidate))
        return _load_payload(path), str(path)

    song_name = str(args.song_name or baseline.get("song_name") or "")
    difficulty = str(args.difficulty or baseline.get("difficulty") or "")
    config_path = Path(str(args.config or baseline.get("config_path") or "config.ini"))
    depths = (
        [int(part.strip()) for part in str(args.depths or "").split(",") if part.strip()]
        if str(args.depths or "").strip()
        else [int(v) for v in baseline.get("depths") or []]
    )
    seeds = (
        [int(part.strip()) for part in str(args.seeds or "").split(",") if part.strip()]
        if str(args.seeds or "").strip()
        else [int(v) for v in baseline.get("seeds") or []]
    )
    payload = run_benchmark(
        song_name=song_name,
        difficulty=difficulty,
        config_path=config_path,
        depths=depths,
        seeds=seeds,
        ga_multi_start=int(args.ga_multi_start or baseline.get("ga_multi_start") or 3),
        fg_candidate_limit=int(args.fg_candidate_limit or baseline.get("fg_candidate_limit") or 51),
        db_path=str(args.db_path or baseline.get("db_source_path") or ""),
    )
    candidate_path = Path(str(args.candidate_out))
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload, str(candidate_path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    baseline_path = Path(str(args.baseline))
    baseline = _load_payload(baseline_path)
    candidate, candidate_path = _resolve_candidate_payload(args, baseline)
    report = compare_payloads(
        baseline,
        candidate,
        max_base_score_drop=float(args.max_base_score_drop),
        max_fg_score_drop=float(args.max_fg_score_drop),
        max_duplicate_ratio_increase=float(args.max_duplicate_ratio_increase),
        max_error_run_increase=int(args.max_error_run_increase),
        max_elapsed_increase_pct=float(args.max_elapsed_increase_pct),
    )

    payload = {
        "pass": bool(report.get("pass", False)),
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "thresholds": {
            "max_base_score_drop": float(args.max_base_score_drop),
            "max_fg_score_drop": float(args.max_fg_score_drop),
            "max_duplicate_ratio_increase": float(args.max_duplicate_ratio_increase),
            "max_error_run_increase": int(args.max_error_run_increase),
            "max_elapsed_increase_pct": float(args.max_elapsed_increase_pct),
        },
        "findings": report.get("findings", []),
    }

    out_path = Path(str(args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    verdict = "PASS" if payload["pass"] else "FAIL"
    print(f"[guardrail] {verdict} baseline={baseline_path} candidate={candidate_path}")
    for finding in payload["findings"]:
        depth = finding.get("depth")
        depth_label = "" if depth is None else f" depth={depth}"
        print(f"[guardrail]{depth_label} {finding.get('metric')}: {finding.get('message')}")
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
