"""
Inventory Meta - Auto Tuner (GPU-only).

This module runs:
1) A deterministic real-world benchmark (for comparing algorithm changes).
2) A non-deterministic tuning loop (for finding robust settings under RNG).

Why non-deterministic seeds for tuning?
  Deterministic seeds are ideal for A/B comparisons of algorithm changes (stable baseline).
  Non-deterministic seeds are useful for tuning settings because they expose sensitivity to unlucky
  witness pools / LNS walks, and help choose parameters that perform well "on average".

NOTE: This tuner does NOT enable human mode or relaxed candidate deltas; it stays exact-peak-only.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .real_bench import (
    build_base_kwargs,
    build_benchmark_suite,
    compute_db_song_signature,
    run_inventory_meta_coverage_subprocess,
)


def _atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _default_seed_generator() -> int:
    # Non-deterministic by design (see module docstring).
    return int(secrets.randbelow(2_000_000_000) + 1)


def _score_suite(results_by_label: dict) -> int:
    """
    Scalar objective for tuning.

    Priority order:
    1) Maximize "All" coverage when present.
    2) Then maximize sum coverage across labels.
    """
    if not isinstance(results_by_label, dict):
        return 0
    all_cov = 0
    sum_cov = 0
    for label, row in results_by_label.items():
        if not isinstance(row, dict):
            continue
        cov = int(row.get("songs_covered") or 0)
        sum_cov += cov
        if str(label) == "All":
            all_cov = cov
    return int(all_cov * 10_000 + sum_cov)


def _sample_overrides(space: dict, rng: random.Random) -> dict:
    out: dict[str, Any] = {}
    for key, values in space.items():
        if not isinstance(values, list) or not values:
            continue
        out[str(key)] = values[int(rng.randrange(0, len(values)))]
    return out


RunLabelFn = Callable[[str, Optional[str], dict], dict]


@dataclass(frozen=True)
class TuneTrial:
    seed: int
    overrides: dict
    results_by_label: dict
    score: int
    wall_time_sec: float


@dataclass(frozen=True)
class TuneSummary:
    best_score: int
    best_overrides: dict
    trials: list[TuneTrial]


def run_tuning_loop(
    *,
    repo_root: Path,
    db_path: Path,
    inventory_cap: int,
    mode: str,
    base_seed: int,
    trials: int,
    timeout_sec: float,
    search_space: dict,
    rng: random.Random,
    seed_generator: Callable[[], int],
    run_label: Optional[RunLabelFn] = None,
) -> TuneSummary:
    suite, cfg = build_benchmark_suite(mode)
    base_kwargs = build_base_kwargs(seed=int(base_seed), inventory_cap=int(inventory_cap), cfg=cfg)

    # Safety: force exact-peak-only constraints for tuning runs.
    base_kwargs["gpu_full_human_mode"] = False
    base_kwargs["gpu_full_candidate_score_delta"] = 0
    base_kwargs["gpu_full_candidate_limit_per_song"] = 0

    best_score = -1
    best_overrides: dict = {}
    out_trials: list[TuneTrial] = []

    for _ in range(int(max(1, trials))):
        overrides = _sample_overrides(search_space, rng=rng)
        seed = int(seed_generator())

        # Apply per-trial seed and overrides.
        results_by_label: dict = {}
        t0 = time.perf_counter()
        for label, element in suite:
            kwargs = dict(base_kwargs)
            kwargs["seed"] = int(seed)
            kwargs["element"] = element
            kwargs["restarts"] = int(cfg["element_restarts"]) if element else 1
            kwargs.update(overrides)
            if run_label is not None:
                msg = run_label(str(label), element, kwargs)
            else:
                msg = run_inventory_meta_coverage_subprocess(
                    repo_root=repo_root,
                    db_path=db_path,
                    label=str(label),
                    kwargs=kwargs,
                    timeout_sec=float(timeout_sec),
                )
            st = msg.get("stats") or {}
            results_by_label[str(label)] = {
                "songs_total": int(st.get("songs_total") or 0),
                "songs_covered": int(st.get("songs_covered") or 0),
                "gear_variants_used": int(st.get("gear_variants_used") or 0),
                "gear_variants_cap": int(st.get("gear_variants_cap") or 0),
                "unique_gears_used": int(st.get("unique_gears_used") or 0),
                "time_sec": float(msg.get("time_sec") or 0.0),
                "wall_time_sec": float(msg.get("wall_time_sec") or 0.0),
                "solver_stats": msg.get("solver_stats") or {},
            }

        wall = float(time.perf_counter() - t0)
        score = _score_suite(results_by_label)
        out_trials.append(
            TuneTrial(
                seed=int(seed),
                overrides=dict(overrides),
                results_by_label=results_by_label,
                score=int(score),
                wall_time_sec=float(round(wall, 6)),
            )
        )
        if score > best_score:
            best_score = int(score)
            best_overrides = dict(overrides)

    return TuneSummary(best_score=int(best_score), best_overrides=best_overrides, trials=out_trials)


def run_baseline(
    *,
    repo_root: Path,
    db_path: Path,
    inventory_cap: int,
    mode: str,
    seed: int,
    timeout_sec: float,
    run_label: Optional[RunLabelFn] = None,
) -> dict:
    """
    Run the suite once with the current baseline settings and a deterministic seed.

    This is the "compare algorithm changes" baseline; do not use it as the only signal for tuning.
    """
    suite, cfg = build_benchmark_suite(mode)
    base_kwargs = build_base_kwargs(seed=int(seed), inventory_cap=int(inventory_cap), cfg=cfg)
    base_kwargs["gpu_full_human_mode"] = False
    base_kwargs["gpu_full_candidate_score_delta"] = 0
    base_kwargs["gpu_full_candidate_limit_per_song"] = 0

    results_by_label: dict = {}
    t0 = time.perf_counter()
    for label, element in suite:
        kwargs = dict(base_kwargs)
        kwargs["element"] = element
        kwargs["restarts"] = int(cfg["element_restarts"]) if element else 1
        if run_label is not None:
            msg = run_label(str(label), element, kwargs)
        else:
            msg = run_inventory_meta_coverage_subprocess(
                repo_root=repo_root,
                db_path=db_path,
                label=str(label),
                kwargs=kwargs,
                timeout_sec=float(timeout_sec),
            )
        st = msg.get("stats") or {}
        results_by_label[str(label)] = {
            "songs_total": int(st.get("songs_total") or 0),
            "songs_covered": int(st.get("songs_covered") or 0),
            "gear_variants_used": int(st.get("gear_variants_used") or 0),
            "gear_variants_cap": int(st.get("gear_variants_cap") or 0),
            "unique_gears_used": int(st.get("unique_gears_used") or 0),
            "time_sec": float(msg.get("time_sec") or 0.0),
            "wall_time_sec": float(msg.get("wall_time_sec") or 0.0),
            "solver_stats": msg.get("solver_stats") or {},
        }

    wall = float(time.perf_counter() - t0)
    score = _score_suite(results_by_label)
    return {"seed": int(seed), "score": int(score), "wall_time_sec": float(round(wall, 6)), "results_by_label": results_by_label}


def main() -> None:
    ap = argparse.ArgumentParser(prog="inventory_optimizer.auto_tune")
    ap.add_argument("--db-path", type=str, default="", help="Path to evolution.db (default: EVOLUTION_DB_PATH).")
    ap.add_argument("--mode", type=str, default="fast", choices=["fast", "precise"], help="Suite to tune against.")
    ap.add_argument("--inventory-cap", type=int, default=100, help="Inventory cap (default: 100).")
    ap.add_argument("--baseline-seed", type=int, default=1, help="Deterministic baseline seed (default: 1).")
    ap.add_argument("--trials", type=int, default=12, help="Tuning trials (default: 12).")
    ap.add_argument("--timeout-sec", type=float, default=900.0, help="Per-run timeout (default: 900s).")
    ap.add_argument(
        "--out-path",
        type=str,
        default="",
        help="Where to store tuning output (default: artifacts/inventory_meta_real_bench/tuning.json).",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    db_path_str = str(args.db_path or "").strip() or (os.environ.get("EVOLUTION_DB_PATH") or "").strip()
    if not db_path_str:
        raise SystemExit("Missing --db-path and EVOLUTION_DB_PATH is not set.")
    db_path = Path(db_path_str).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    out_path_str = str(args.out_path or "").strip()
    out_path = (
        Path(out_path_str).expanduser().resolve()
        if out_path_str
        else (repo_root / "artifacts" / "inventory_meta_real_bench" / "tuning.json")
    )

    mode = str(args.mode)
    inventory_cap = int(args.inventory_cap)
    baseline_seed = int(args.baseline_seed)
    trials = int(args.trials)
    timeout_sec = float(args.timeout_sec)

    db_sig = compute_db_song_signature(db_path)

    # Search space (kept small on purpose; we can expand as we learn what matters).
    # These are all exact-peak-only knobs.
    search_space = {
        "gpu_full_witness_anchor_patterns": [0, 24, 48],
        "gpu_full_witness_seed_streams": [1, 2, 4],
        "gpu_full_witness_pattern_profile": [0, 1, 2],
        "gpu_full_witness_palettes": [1, 2, 3],
        "gpu_full_wildcard_palette_size": [0, 64, 256],
        "gpu_full_k_scan_select": [128, 256],
        "gpu_full_k_scan_repack": [64, 128],
    }

    # Deterministic RNG for *config sampling* so you can reproduce a tuning session by reusing the stored overrides.
    # The per-trial evaluation seed remains non-deterministic (seed_generator).
    cfg_rng = random.Random(0xC0FFEE)

    print(f"DB: {db_path}")
    print(f"DB songs: {db_sig.get('songs_total')}  hash={db_sig.get('songs_name_hash')}")
    print(f"Tune mode: {mode}  cap={inventory_cap}  trials={trials}")
    print()

    baseline = run_baseline(
        repo_root=repo_root,
        db_path=db_path,
        inventory_cap=inventory_cap,
        mode=mode,
        seed=baseline_seed,
        timeout_sec=timeout_sec,
    )
    print(f"Baseline score (deterministic seed={baseline_seed}): {baseline.get('score')}")
    print()

    t0 = time.perf_counter()
    summary = run_tuning_loop(
        repo_root=repo_root,
        db_path=db_path,
        inventory_cap=inventory_cap,
        mode=mode,
        base_seed=baseline_seed,
        trials=trials,
        timeout_sec=timeout_sec,
        search_space=search_space,
        rng=cfg_rng,
        seed_generator=_default_seed_generator,
    )
    wall = time.perf_counter() - t0

    out = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "db_path": str(db_path),
        "db_song_signature": dict(db_sig),
        "mode": mode,
        "inventory_cap": int(inventory_cap),
        "baseline": baseline,
        "search_space": search_space,
        "best_score": int(summary.best_score),
        "best_overrides": summary.best_overrides,
        "trials": [
            {
                "seed": int(t.seed),
                "overrides": dict(t.overrides),
                "score": int(t.score),
                "wall_time_sec": float(t.wall_time_sec),
                "results_by_label": t.results_by_label,
            }
            for t in summary.trials
        ],
        "tuning_wall_time_sec": float(round(wall, 6)),
    }
    _atomic_write_json(out_path, out)

    print(f"Best score: {summary.best_score}")
    print(f"Best overrides: {json.dumps(summary.best_overrides, sort_keys=True)}")
    print(f"Saved: {out_path}")


__all__ = ["TuneSummary", "TuneTrial", "run_tuning_loop"]


if __name__ == "__main__":
    main()
