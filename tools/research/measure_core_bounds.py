"""Measure shared-budget core search against the current GA on real charts.

Run from the repository root (requires SciPy for coefficient fitting):
  python -m tools.research.measure_core_bounds --song 'Data/Hard/<chart>.txt' --output report.json

The production scoring path is unchanged. This research tool does not publish
scores, replace the GA, certify the top-51 frontier, or claim f64 inner-search
optimality from f32 GPU results. All runtime files go to a temporary workspace.
"""

import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time


def measure(args):
    import numpy as np
    import numba
    import scipy
    from gear_optimizer.core.constants import GA_MULTI_RUNS_DEFAULT, GA_POPULATION_SIZE
    from gear_optimizer.data.csv_parser import load_csv_db, read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from tools.research._core_bound_benchmark import prepare_chart, run_ga, score_core
    from tools.research._core_bound_domain import base_fever_counts, project
    from tools.research._core_bound_fit import fit_bounds
    from tools.research._core_bound_math import SCALE, certify_bounds, family_terms, prefix_census
    from tools.research._core_bound_regions import refine_regions
    from tools.research._core_bound_search import enumerate_core

    root = Path(__file__).resolve().parents[2]
    baseline = subprocess.check_output(["git", "rev-parse", args.baseline_ref], cwd=root, text=True).strip()
    # This probe's baseline is only a fair comparison while production code is identical.
    changes = subprocess.check_output(["git", "diff", baseline, "--", "gear_optimizer"], cwd=root, text=True)
    if changes:
        raise ValueError("production code differs from the requested GA baseline")
    refs = build_ref_arrays_from_stats(read_table(str(root / "Data/Gear/Stats.txt")))
    gears = list(load_csv_db(str(root / "Data/Gear/Gears.csv"), "gear").values())
    minis = list(load_csv_db(str(root / "Data/Gear/Minis.csv"), "mini").values())
    ensure_ready()
    results = []
    for filename in args.song:
        path = Path(filename).resolve()
        chart_name = str(path.relative_to(root))
        start = time.perf_counter()
        chart = prepare_chart(path, refs, gears, minis)
        prepare_seconds = time.perf_counter() - start
        print(f"Prepared {chart_name}: {prepare_seconds:.3f}s", flush=True)
        settings = [dict(generations=10, population=64, runs=1),
                    dict(generations=125, population=GA_POPULATION_SIZE, runs=GA_MULTI_RUNS_DEFAULT)]
        for setting in settings:
            print(f"Warming GA: {setting}", flush=True)
            run_ga(chart, **setting, seed=args.seed)
        arms = [[], []]
        for repeat in range(args.repeats):
            for arm in [0, 1] if repeat % 2 == 0 else [1, 0]:
                arms[arm].append(run_ga(chart, **settings[arm], seed=args.seed))
                print(f"GA repeat {repeat + 1}, arm {arm}: {arms[arm][-1]['ga_s']:.3f}s", flush=True)
        short, baseline_runs = arms
        incumbent = short[0]
        meta = chart.song["metadata"]
        notes = len(chart.song["song_data"]["timestamps"])
        stats = project(incumbent["stats"], meta["Primary Color"], meta["Secondary Color"])
        anchor = stats[5] + refs["Perfect Points"][np.clip(stats[0], 0, len(refs["Perfect Points"]) - 1)]
        domain = chart.domain
        start = time.perf_counter()
        # F=N covers FG schedules too, but the only incumbent here is an all-Perfect witness.
        fg_coeff = fit_bounds(domain, refs=refs, notes=notes, fever_notes=notes, anchor_base=anchor)
        fg_bank = certify_bounds(fg_coeff, intervals=domain.intervals, refs=refs, notes=notes, fever_notes=notes)
        fg_root, fg_losses = family_terms(fg_bank, fixed=domain.fixed, gear=domain.gear,
                                         minis=domain.minis, gems=domain.gems, budget=domain.budget)
        fg_probe_seconds = time.perf_counter() - start
        start = time.perf_counter()
        broad, regions, region_counts = refine_regions(domain, refs=refs, notes=notes,
            fever_counts=base_fever_counts(chart.timeline), anchor_base=anchor,
            incumbent=incumbent["score"], max_leaves=args.regions)
        bound_seconds = time.perf_counter() - start
        start = time.perf_counter()
        core = enumerate_core(domain, regions, incumbent=incumbent["score"],
                              max_nodes=args.max_nodes, max_witnesses=args.max_witnesses)
        enumerate_seconds = time.perf_counter() - start
        print(f"Core {chart_name}: {len(core.witnesses)} loadouts, complete={core.complete}", flush=True)
        exact = score_core(chart, core) if core.complete else None
        baseline_time = statistics.median(r["ga_s"] + r["replay_s"] for r in baseline_runs)
        short_time = statistics.median(r["ga_s"] + r["replay_s"] for r in short)
        core_time = (short_time + bound_seconds + enumerate_seconds + exact["total_s"]
                     if exact is not None else None)
        base_score = max(r["score"] for r in baseline_runs)
        core_score = max(incumbent["score"], exact["best_score"]) if exact is not None else None
        report = {
            "chart": chart_name, "notes": notes, "prepare_s": prepare_seconds,
            "catalog_loadouts": domain.loadouts, "gear_counts": list(map(len, domain.gear)),
            "mini_count": len(domain.minis), "gem_budget": domain.budget,
            "primary_color": meta["Primary Color"], "secondary_color": meta["Secondary Color"],
            "short_seed": short, "baseline_ga": baseline_runs,
            "fg_count_bound": {"s": fg_probe_seconds, "upper_score_display": float(np.exp(fg_root.min() / SCALE)),
                               "gear_prefixes": prefix_census(fg_root, fg_losses, incumbent=incumbent["score"])},
            "base_bound_s": bound_seconds, "base_broad_upper_display": float(np.exp(broad.root.min() / SCALE)),
            "base_regions": region_counts, "core_enumeration_s": enumerate_seconds,
            "core_complete": core.complete, "core_nodes": core.nodes, "core_loadouts": len(core.witnesses),
            "inner": exact, "baseline_ga_and_replay_s": baseline_time,
            "short_seed_bounds_inner_replay_s": core_time, "baseline_score": base_score, "core_score": core_score,
            "measured_base_improvement": bool(core_time is not None and core_time < baseline_time and core_score >= base_score),
            "optimality_certified": bool(region_counts["certified"]),
        }
        results.append(report)
        print(json.dumps({k: report[k] for k in ("chart", "core_loadouts", "baseline_score", "core_score",
              "baseline_ga_and_replay_s", "short_seed_bounds_inner_replay_s", "measured_base_improvement")}), flush=True)
        args.output.write_text(json.dumps({"baseline_commit": baseline, "platform": platform.platform(),
            "python": platform.python_version(), "numpy": np.__version__, "numba": numba.__version__,
            "scipy": scipy.__version__, "results": results}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--song", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-ref", default="origin/main")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--regions", type=int, default=64)
    parser.add_argument("--max-nodes", type=int, default=1_000_000)
    parser.add_argument("--max-witnesses", type=int, default=100_000)
    args = parser.parse_args()
    if min(args.repeats, args.regions, args.max_nodes, args.max_witnesses) < 1:
        parser.error("repeat, region and enumeration limits must be positive")
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="robeats-core-bound-") as temporary:
        workspace = Path(temporary)
        for key, name in {"ROBEATSMETA_OPTIMIZER_BIN_DIR": "bin", "EVOLUTION_DB_PATH": "evolution.db",
                          "TIMELINE_FRONTIER_CACHE_DIR": "timeline", "FG_RESPONSE_FRONTIER_CACHE_DIR": "fg",
                          "NUMBA_CACHE_DIR": "numba"}.items():
            os.environ[key] = str(workspace / name)
        measure(args)


if __name__ == "__main__":
    main()
