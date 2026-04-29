from __future__ import annotations

import argparse
import configparser
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.bench.bench_ga_winner_stability import run_benchmark


def _parse_ints(raw: str) -> list[int]:
    return [int(part.strip()) for part in str(raw or "").split(",") if part.strip()]


def _metric_mean(summary: dict[str, Any], key: str) -> float:
    value = summary.get(key, 0.0)
    if isinstance(value, dict):
        try:
            return float(value.get("mean", 0.0) or 0.0)
        except Exception:
            return 0.0
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _metric_max(summary: dict[str, Any], key: str) -> float:
    value = summary.get(key, 0.0)
    if isinstance(value, dict):
        try:
            return float(value.get("max", 0.0) or 0.0)
        except Exception:
            return 0.0
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def write_mode_config(
    *,
    base_config_path: Path,
    out_dir: Path,
    mode: str,
    cem_tail_replace_frac: float,
    cem_refresh_every: int,
    cem_elite_frac: float,
    cem_smoothing: float,
    cem_min_prob: float,
    trash_suppression: bool,
    breakpoint_mutation_bias: bool,
) -> Path:
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(str(base_config_path), encoding="utf-8-sig")
    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    ie = cfg["IterationEngine"]
    ie["GPU_GA_SearchMode"] = str(mode)
    ie["GPU_GA_CEMEliteFrac"] = f"{float(cem_elite_frac):.6g}"
    ie["GPU_GA_CEMSmoothing"] = f"{float(cem_smoothing):.6g}"
    ie["GPU_GA_CEMMinProb"] = f"{float(cem_min_prob):.6g}"
    ie["GPU_GA_CEMRefreshEvery"] = str(int(cem_refresh_every))
    ie["GPU_GA_CEMTailReplaceFrac"] = f"{float(cem_tail_replace_frac):.6g}"
    ie["GPU_GA_RareItemProtection"] = "true"
    ie["GPU_GA_TrashSuppression"] = "true" if trash_suppression else "false"
    ie["GPU_GA_BreakpointMutationBias"] = "true" if breakpoint_mutation_bias else "false"

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{mode}.ini"
    with path.open("w", encoding="utf-8") as handle:
        cfg.write(handle)
    return path


def compare_payloads(standard: dict[str, Any], cem: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    depths = [int(v) for v in standard.get("depths") or []]
    best_observed_base = max(
        [
            _metric_mean((payload.get("summary_by_depth") or {}).get(str(depth)) or {}, "base_score")
            for payload in (standard, cem)
            for depth in depths
        ]
        or [0.0]
    )
    best_observed_fg = max(
        [
            _metric_mean((payload.get("summary_by_depth") or {}).get(str(depth)) or {}, "fg_score")
            for payload in (standard, cem)
            for depth in depths
        ]
        or [0.0]
    )
    for depth in depths:
        key = str(depth)
        standard_summary = (standard.get("summary_by_depth") or {}).get(key) or {}
        cem_summary = (cem.get("summary_by_depth") or {}).get(key) or {}
        standard_base = _metric_mean(standard_summary, "base_score")
        cem_base = _metric_mean(cem_summary, "base_score")
        standard_fg = _metric_mean(standard_summary, "fg_score")
        cem_fg = _metric_mean(cem_summary, "fg_score")
        standard_dup = _metric_mean(standard_summary, "duplicate_genome_ratio")
        cem_dup = _metric_mean(cem_summary, "duplicate_genome_ratio")
        standard_debt = _metric_max(standard_summary, "pending_fg_jobs_song_delta")
        cem_debt = _metric_max(cem_summary, "pending_fg_jobs_song_delta")
        rows.append(
            {
                "depth": int(depth),
                "standard_base_mean": float(standard_base),
                "cem_base_mean": float(cem_base),
                "base_delta": float(cem_base - standard_base),
                "best_observed_base_mean": float(best_observed_base),
                "standard_base_gap_to_best_observed": float(best_observed_base - standard_base),
                "cem_base_gap_to_best_observed": float(best_observed_base - cem_base),
                "standard_fg_mean": float(standard_fg),
                "cem_fg_mean": float(cem_fg),
                "fg_delta": float(cem_fg - standard_fg),
                "best_observed_fg_mean": float(best_observed_fg),
                "standard_fg_gap_to_best_observed": float(best_observed_fg - standard_fg),
                "cem_fg_gap_to_best_observed": float(best_observed_fg - cem_fg),
                "standard_duplicate_genome_ratio_mean": float(standard_dup),
                "cem_duplicate_genome_ratio_mean": float(cem_dup),
                "duplicate_genome_ratio_delta": float(cem_dup - standard_dup),
                "standard_pending_fg_debt_max": float(standard_debt),
                "cem_pending_fg_debt_max": float(cem_debt),
                "pending_fg_debt_delta": float(cem_debt - standard_debt),
                "base_not_worse": bool(cem_base >= standard_base),
                "cem_closer_to_best_base": bool((best_observed_base - cem_base) < (best_observed_base - standard_base)),
                "fg_not_worse": bool(cem_fg >= standard_fg),
                "cem_closer_to_best_fg": bool((best_observed_fg - cem_fg) < (best_observed_fg - standard_fg)),
                "duplicates_lower": bool(cem_dup < standard_dup),
                "fg_debt_not_worse": bool(cem_debt <= standard_debt),
            }
        )
    return rows


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run a fixed standard-vs-CEM hybrid GA A/B benchmark.")
    ap.add_argument("--song-name", default="2NITE (Hard) by nanobii")
    ap.add_argument("--difficulty", default="Hard")
    ap.add_argument("--config", default="config.ini")
    ap.add_argument("--depths", default="25,50,75")
    ap.add_argument("--seeds", default="1337,1338,1339")
    ap.add_argument("--pipeline", default="direct", choices=["direct", "inflight"])
    ap.add_argument("--ga-multi-start", type=int, default=3)
    ap.add_argument("--fg-candidate-limit", type=int, default=51)
    ap.add_argument("--fg-search-radius", type=int, default=5)
    ap.add_argument("--db-path", default="")
    ap.add_argument("--out-dir", default=str(Path("artifacts") / "runcheck" / "cem_hybrid_ab"))
    ap.add_argument("--cem-tail-replace-frac", type=float, default=0.30)
    ap.add_argument("--cem-refresh-every", type=int, default=5)
    ap.add_argument("--cem-elite-frac", type=float, default=0.10)
    ap.add_argument("--cem-smoothing", type=float, default=0.25)
    ap.add_argument("--cem-min-prob", type=float, default=0.002)
    ap.add_argument("--trash-suppression", action="store_true")
    ap.add_argument("--breakpoint-mutation-bias", action="store_true")
    ap.add_argument(
        "--fail-on-score-regression",
        action="store_true",
        help="Exit nonzero when CEM base or FG mean is below standard at any depth.",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(str(args.config))
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    depths = _parse_ints(str(args.depths))
    seeds = _parse_ints(str(args.seeds))
    if not depths:
        raise SystemExit("--depths must include at least one integer.")
    if not seeds:
        raise SystemExit("--seeds must include at least one integer.")

    out_dir = Path(str(args.out_dir))
    standard_cfg = write_mode_config(
        base_config_path=config_path,
        out_dir=out_dir,
        mode="standard",
        cem_tail_replace_frac=float(args.cem_tail_replace_frac),
        cem_refresh_every=int(args.cem_refresh_every),
        cem_elite_frac=float(args.cem_elite_frac),
        cem_smoothing=float(args.cem_smoothing),
        cem_min_prob=float(args.cem_min_prob),
        trash_suppression=bool(args.trash_suppression),
        breakpoint_mutation_bias=bool(args.breakpoint_mutation_bias),
    )
    cem_cfg = write_mode_config(
        base_config_path=config_path,
        out_dir=out_dir,
        mode="cem_hybrid",
        cem_tail_replace_frac=float(args.cem_tail_replace_frac),
        cem_refresh_every=int(args.cem_refresh_every),
        cem_elite_frac=float(args.cem_elite_frac),
        cem_smoothing=float(args.cem_smoothing),
        cem_min_prob=float(args.cem_min_prob),
        trash_suppression=bool(args.trash_suppression),
        breakpoint_mutation_bias=bool(args.breakpoint_mutation_bias),
    )

    common = {
        "song_name": str(args.song_name),
        "difficulty": str(args.difficulty),
        "depths": depths,
        "seeds": seeds,
        "ga_multi_start": int(args.ga_multi_start),
        "use_db": bool(str(args.db_path or "").strip()),
        "fg_candidate_limit": int(args.fg_candidate_limit),
        "fg_search_radius": int(args.fg_search_radius),
        "pipeline": str(args.pipeline),
        "db_path": str(args.db_path or ""),
    }
    print(f"[cem-ab] standard config: {standard_cfg}")
    standard = run_benchmark(config_path=standard_cfg, **common)
    print(f"[cem-ab] cem_hybrid config: {cem_cfg}")
    cem = run_benchmark(config_path=cem_cfg, **common)

    rows = compare_payloads(standard, cem)
    report = {
        "song_name": str(args.song_name),
        "difficulty": str(args.difficulty),
        "depths": depths,
        "seeds": seeds,
        "standard_config": str(standard_cfg),
        "cem_config": str(cem_cfg),
        "rows": rows,
    }
    (out_dir / "standard_payload.json").write_text(json.dumps(standard, indent=2), encoding="utf-8")
    (out_dir / "cem_hybrid_payload.json").write_text(json.dumps(cem, indent=2), encoding="utf-8")
    report_path = out_dir / "cem_hybrid_ab_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[cem-ab] wrote {report_path}")
    for row in rows:
        print(
            "[cem-ab] depth={depth} base_delta={base_delta:.0f} "
            "base_gap standard={standard_base_gap_to_best_observed:.0f} cem={cem_base_gap_to_best_observed:.0f} "
            "fg_delta={fg_delta:.0f} "
            "dup_delta={duplicate_genome_ratio_delta:+.2%} debt_delta={pending_fg_debt_delta:.0f}".format(**row)
        )

    if bool(args.fail_on_score_regression) and any(not r["base_not_worse"] or not r["fg_not_worse"] for r in rows):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
