"""Compare canonical score/time trajectories: production GA, #180, adaptive Base core.

Every seed is independent; preparation is shared and reported separately. No
result is called an optimum without a certificate. No production DB is written.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

import numpy as np


class Curve:
    def __init__(self):
        self.start = time.perf_counter()
        self.events = []
        self.best = 0

    def record(self, score):
        if score > self.best:
            self.best = int(score)
            self.events.append({"s": time.perf_counter() - self.start, "score": self.best})

    def report(self):
        return {"events": self.events, "score": self.best, "total_s": time.perf_counter() - self.start}


def legacy_modules(root, ref, folder):
    """Run the actual #180 fitter/refiner/enumerator, not a renamed approximation."""
    modules = {}
    for name in ("fit", "regions", "search"):
        source = subprocess.check_output(["git", "show", f"{ref}:tools/research/_core_bound_{name}.py"],
                                         cwd=root, text=True)
        path = folder / f"legacy_{name}.py"
        path.write_text(source)
        spec = importlib.util.spec_from_file_location(f"legacy_{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    modules["regions"].fit_bounds = modules["fit"].fit_bounds
    return modules


def run_core(chart, *, curve, seed, portfolio, regions, legacy, members,
             max_nodes, max_witnesses, time_budget):
    from tools.research._core_bound_benchmark import run_ga, score_core
    from tools.research._core_bound_domain import base_fever_counts, project
    from tools.research._core_bound_regions import refine_regions
    from tools.research._core_bound_search import enumerate_core
    from tools.research._core_adaptive_score import score_adaptive
    incumbent = run_ga(chart, generations=10, population=64, runs=portfolio, seed=seed,
                       on_improvement=curve.record)
    meta = chart.song["metadata"]
    stats = project(incumbent["stats"], meta["Primary Color"], meta["Secondary Color"])
    anchor = stats[5] + chart.refs["Perfect Points"][np.clip(stats[0], 0, len(chart.refs["Perfect Points"]) - 1)]
    start = time.perf_counter()
    region_fn = legacy["regions"].refine_regions if legacy else refine_regions
    enum_fn = legacy["search"].enumerate_core if legacy else enumerate_core
    options = {} if legacy else {"members": members}
    _, leaves, counts = region_fn(chart.domain, refs=chart.refs,
        notes=len(chart.song["song_data"]["timestamps"]), fever_counts=base_fever_counts(chart.timeline),
        anchor_base=anchor, incumbent=incumbent["score"], max_leaves=regions, **options)
    bound_seconds = time.perf_counter() - start
    start = time.perf_counter()
    core = enum_fn(chart.domain, leaves, incumbent=incumbent["score"],
                   max_nodes=max_nodes, max_witnesses=max_witnesses)
    enum_seconds = time.perf_counter() - start
    print(f"Core: {len(core.witnesses)} candidates, bounds={bound_seconds:.3f}s, enumeration={enum_seconds:.3f}s, complete={core.complete}", flush=True)
    if legacy:
        inner = score_core(chart, core, on_improvement=curve.record, deadline=curve.start + time_budget) if core.complete else None
    else:
        inner = score_adaptive(chart, core, incumbent=incumbent,
                               on_improvement=curve.record, deadline=curve.start + time_budget)
    return {**curve.report(), "seed_result": incumbent, "bounds_s": bound_seconds, "enumeration_s": enum_seconds,
            "regions": counts, "core_complete": core.complete, "core_candidates": len(core.witnesses),
            "core_nodes": core.nodes, "inner": inner}


def measure(args, folder):
    import numba
    import scipy
    from gear_optimizer.core.constants import GA_POPULATION_SIZE, GA_MULTI_RUNS_DEFAULT
    from gear_optimizer.data.csv_parser import load_csv_db, read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from tools.research._core_bound_benchmark import prepare_chart, run_ga
    from tools.research._core_region_gpu import solve_regions
    root = Path(__file__).resolve().parents[2]
    legacy = legacy_modules(root, args.baseline_ref, folder)
    refs = build_ref_arrays_from_stats(read_table(str(root / "Data/Gear/Stats.txt")))
    gears = list(load_csv_db(str(root / "Data/Gear/Gears.csv"), "gear").values())
    minis = list(load_csv_db(str(root / "Data/Gear/Minis.csv"), "mini").values())
    report = {"baseline_commit": subprocess.check_output(["git", "rev-parse", args.baseline_ref], cwd=root, text=True).strip(),
              "platform": platform.platform(), "python": platform.python_version(),
              "numpy": np.__version__, "numba": numba.__version__, "scipy": scipy.__version__,
              "hardware_role": args.hardware_role, "optimality_certified": False,
              "fg": "not measured; Base results give no FG coverage or speed claim",
              "settings": {k: v for k, v in vars(args).items() if k not in {"output", "song"}},
              "results": []}
    for filename in args.song:
        path = Path(filename).resolve()
        start = time.perf_counter()
        chart = prepare_chart(path, refs, gears, minis)
        prepare_seconds = time.perf_counter() - start
        print(f"Prepared {path.name}: {prepare_seconds:.3f}s", flush=True)
        # Time warmup separately; it is not part of the warmed search curves.
        warm_start = time.perf_counter()
        warm = run_ga(chart, generations=10, population=64, runs=args.portfolio, seed=args.seeds[0], on_improvement=lambda _: None)
        if "legacy" in args.arms and args.portfolio != 1:
            run_ga(chart, generations=10, population=64, runs=1, seed=args.seeds[0], on_improvement=lambda _: None)
        if "ga" in args.arms:
            run_ga(chart, generations=125, population=GA_POPULATION_SIZE, runs=GA_MULTI_RUNS_DEFAULT,
                   seed=args.seeds[0], on_improvement=lambda _: None)
        ids = np.array([warm["ids"]], dtype=np.int32)
        low = np.zeros((1, 6), dtype=np.int64)
        high = np.zeros((1, 6), dtype=np.int64)
        solve_regions(chart, chart.arrays, ids, low, high)
        item = {"chart": str(path.relative_to(root)), "split": args.split,
                "notes": len(chart.song["song_data"]["timestamps"]),
                "primary": chart.song["metadata"]["Primary Color"],
                "secondary": chart.song["metadata"]["Secondary Color"],
                "prepare_s": prepare_seconds, "warmup_s": time.perf_counter() - warm_start, "runs": []}
        report["results"].append(item)
        for i, seed in enumerate(args.seeds):
            order = args.arms[i % len(args.arms):] + args.arms[:i % len(args.arms)]
            for arm in order:
                print(f"Running {path.name} seed={seed} arm={arm}", flush=True)
                curve = Curve()
                if arm == "ga":
                    result = run_ga(chart, generations=125, population=GA_POPULATION_SIZE,
                                    runs=GA_MULTI_RUNS_DEFAULT, seed=seed, on_improvement=curve.record)
                    result = {**curve.report(), "ga": result}
                else:
                    result = run_core(chart, curve=curve, seed=seed,
                        portfolio=1 if arm == "legacy" else args.portfolio,
                        regions=args.regions, legacy=legacy if arm == "legacy" else None,
                        members=args.members, max_nodes=args.max_nodes,
                        max_witnesses=args.max_witnesses,
                        time_budget=args.time_budget)
                result.update(arm=arm, seed=seed)
                item["runs"].append(result)
                print(json.dumps({k: result[k] for k in ("arm", "seed", "score", "total_s")}), flush=True)
                args.output.write_text(json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--song", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1337, 2027, 9041])
    parser.add_argument("--arms", nargs="+", choices=["ga", "legacy", "adaptive"], default=["ga", "legacy", "adaptive"])
    parser.add_argument("--baseline-ref", default="7b46703b")
    parser.add_argument("--hardware-role", choices=["production", "development"], required=True)
    parser.add_argument("--split", choices=["development", "held-out"], required=True)
    parser.add_argument("--time-budget", type=float, default=60.)
    parser.add_argument("--portfolio", type=int, default=4)
    parser.add_argument("--regions", type=int, default=64)
    parser.add_argument("--members", type=int, default=9)
    parser.add_argument("--max-nodes", type=int, default=1_000_000)
    parser.add_argument("--max-witnesses", type=int, default=100_000)
    args = parser.parse_args()
    if min(args.portfolio, args.regions, args.members, args.max_nodes, args.max_witnesses, args.time_budget) < 1:
        parser.error("budgets must be positive")
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="robeats-adaptive-core-") as temporary:
        folder = Path(temporary)
        for key, name in {"ROBEATSMETA_OPTIMIZER_BIN_DIR": "bin", "EVOLUTION_DB_PATH": "evolution.db",
                          "TIMELINE_FRONTIER_CACHE_DIR": "timeline", "FG_RESPONSE_FRONTIER_CACHE_DIR": "fg",
                          "NUMBA_CACHE_DIR": "numba"}.items():
            os.environ[key] = str(folder / name)
        measure(args, folder)


if __name__ == "__main__":
    main()
