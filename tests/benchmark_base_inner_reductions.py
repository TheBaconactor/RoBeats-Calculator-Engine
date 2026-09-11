"""Warm full-population Base evaluation against a git revision.

Uses the deterministic 64-genome GA integration fixture (synthetic test loadouts
and chart, real production kernels, 90-gem budget). Not a complete GA run.
Run: python -m tests.benchmark_base_inner_reductions --baseline-ref 7119c0c1
"""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from tests.benchmark_inner_reductions import _load_revision_module, _measure_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="robeats-base-inner-bench-") as temporary:
        directory = Path(temporary)
        os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(directory / "fg-cache")
        os.environ["TIMELINE_FRONTIER_CACHE_DIR"] = str(directory / "timeline-cache")
        os.environ["EVOLUTION_DB_PATH"] = str(directory / "evolution.db")
        from gear_optimizer.solver.taichi_gem.api import ga_operations
        from tests import test_gpu_ga_eval_incumbent_cull as fixture

        package = "gear_optimizer.solver.taichi_gem.kernels"
        scoring = _load_revision_module(directory, args.baseline_ref, package, "kernels_scoring")
        warmstart = _load_revision_module(directory, args.baseline_ref, package, "warmstart_common")
        warmstart.optimize_core_device_exact_bound = scoring.optimize_core_device_exact_bound
        warmstart.score_solution_from_gems_frontier = scoring.score_solution_from_gems_frontier
        baseline = _load_revision_module(directory, args.baseline_ref, package + ".ga_eval", "warmstart")
        baseline.solve_combo_warmstart_preloaded = warmstart.solve_combo_warmstart_preloaded
        flags = fixture.eval_device_state.__wrapped__()
        current_kernel = ga_operations.kernels.ga_find_best_combo_warmstart_kernel

        def run(kernel):
            ga_operations.kernels.ga_find_best_combo_warmstart_kernel = kernel
            try:
                return fixture._run_production_eval(flags)
            finally:
                ga_operations.kernels.ga_find_best_combo_warmstart_kernel = current_kernel

        result = _measure_pair(
            lambda: run(baseline.ga_find_best_combo_warmstart_kernel),
            lambda: run(current_kernel),
            lambda arrays: tuple(array.tobytes() for array in arrays),
            15,
        )
        result.update(platform=sys.platform, baseline_ref=args.baseline_ref, genomes=64, budget=90)
        output = Path("/tmp/robeats-base-inner-reductions-benchmark.json")
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
        print(f"Saved {output}", flush=True)


if __name__ == "__main__":
    main()
