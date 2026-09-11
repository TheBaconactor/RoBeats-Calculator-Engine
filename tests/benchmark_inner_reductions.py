"""Warm before/after FG evaluation on real charts; never touches production caches.

Run as ``python -m tests.benchmark_inner_reductions --baseline-ref 7119c0c1``.
Times the complete CPU FG candidate path and the GPU inner host dispatch separately.
This is not a full GA benchmark. GPU precision follows the local hardware gate.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

import numpy as np


def _load_revision_module(directory, revision, package, stem):
    source = subprocess.run(
        ["git", "show", f"{revision}:{package.replace('.', '/')}/{stem}.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    path = directory / f"{stem}.py"
    path.write_text(source)
    name = f"{package}._benchmark_baseline_{stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_baseline(directory, revision):
    package = "gear_optimizer.solver.taichi_gem.force_greats"
    kernels = _load_revision_module(directory, revision, package, "response_inner_kernels")
    host = _load_revision_module(directory, revision, package, "response_inner_host")
    host._fg_response_inner_group_kernel = kernels._fg_response_inner_group_kernel
    host._fg_response_inner_batch_kernel = kernels._fg_response_inner_batch_kernel
    return host


def _measure_pair(before, after, signature, repeats):
    for _ in range(2):
        expected = signature(before())
        assert signature(after()) == expected
    samples = [[], []]
    for repeat in range(repeats):
        for idx in [0, 1] if repeat % 2 == 0 else [1, 0]:
            start = time.perf_counter()
            result = (before, after)[idx]()
            samples[idx].append((time.perf_counter() - start) * 1000)
            assert signature(result) == expected
    return {
        "before_ms": statistics.median(samples[0]),
        "after_ms": statistics.median(samples[1]),
        "before_samples_ms": samples[0],
        "after_samples_ms": samples[1],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path, default=Path("/tmp/robeats-inner-reductions-benchmark.json"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="robeats-inner-bench-") as temporary:
        directory = Path(temporary)
        os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(directory / "fg-cache")
        os.environ["TIMELINE_FRONTIER_CACHE_DIR"] = str(directory / "timeline-cache")
        os.environ["EVOLUTION_DB_PATH"] = str(directory / "evolution.db")
        from gear_optimizer.data.song_io import get_base_calc_song
        from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached
        from gear_optimizer.solver.taichi_gem.force_greats import response_frontier as frontier
        from gear_optimizer.solver.taichi_gem.force_greats import response_inner_host as current
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
            build_or_load_response_frontier_payload,
            load_response_frontier_scoring_bundle,
        )
        from gear_optimizer.solver.timing_envelope import apply_timing_envelope

        baseline = _load_baseline(directory, args.baseline_ref)
        refs = get_exact_replay_ref_arrays_cached()
        reports = []
        cases = [
            ("All Right There (Hard) by BSlick feat CG5.txt", [25, 55, 70, 43, 58, 34, 768, 35, 0, 100], "Vibe"),
            ("Aurora (Hard) by Creo.txt", [29, 57, 68, 55, 58, 35, 36, 62, 16, 754], "Chill"),
        ]
        names = [
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Time",
            "Fever Fill Rate",
            "Beat",
            "Vibe",
            "Rush",
            "Flow",
            "Chill",
        ]
        for filename, values, selected in cases:
            song = get_base_calc_song(str(Path("Data/Hard") / filename), {})
            apply_timing_envelope(song, mode="perfect_window")
            stats = dict(zip(names, values))
            budget = 9
            keys = frontier.required_response_stat_keys_for_scoring_batch(base_stats_list=[stats], total_budget=budget)
            print(f"Preparing {filename}: {len(keys)} FT/FF cells", flush=True)
            build_or_load_response_frontier_payload(song, refs, stat_keys=keys)
            bundle = load_response_frontier_scoring_bundle(song, refs, stat_keys=keys)

            def prepare():
                return frontier.prepare_force_greats_response_frontier_scoring_batch(
                    base_stats_list=[stats],
                    calc_song=song,
                    ref_arrays=refs,
                    selected_color=selected,
                    total_budget=budget,
                    scoring_bundle=bundle,
                )

            def evaluate(module):
                frontier._score_response_group_meta_cpu = module._score_response_group_meta_cpu
                try:
                    return frontier.score_prepared_force_greats_response_frontier_batch_cpu_sync(prepare())
                finally:
                    frontier._score_response_group_meta_cpu = current._score_response_group_meta_cpu

            def result_signature(results):
                return [
                    (
                        r.best_score,
                        r.ft,
                        r.ff,
                        tuple(sorted(r.gem_counts.items())),
                        tuple(r.surface),
                        tuple(sorted(r.stats.items())),
                    )
                    for r in results
                ]

            cpu = _measure_pair(lambda: evaluate(baseline), lambda: evaluate(current), result_signature, args.repeats)
            packed = frontier.build_prepared_force_greats_response_frontier_group_arrays_on_owner(prepare())
            kwargs = dict(
                group_meta=packed.group_meta,
                group_offsets=packed.scoring_group_offsets,
                group_lengths=packed.scoring_group_lengths,
                primary_color=packed.primary_color,
                secondary_color=packed.secondary_color,
                selected_color=selected,
                ref_arrays=refs,
                surface_pattern_ids=packed.scoring_surface_pattern_ids,
                surface_pattern_words=packed.scoring_surface_pattern_words,
                surface_counts=packed.scoring_surface_counts,
                surface_pattern_head_coeffs=packed.scoring_surface_pattern_head_coeffs,
            )
            gpu = _measure_pair(
                lambda: baseline._score_response_group_meta_gpu(**kwargs),
                lambda: current._score_response_group_meta_gpu(**kwargs),
                lambda pair: (pair[0].tobytes(), pair[1]),
                args.repeats,
            )
            report = {
                "chart": filename,
                "notes": packed.head_len + packed.body_total,
                "budget": budget,
                "groups": len(packed.group_meta),
                "logical_surfaces": int(packed.scoring_group_lengths.sum()),
                "cpu_complete_candidate": cpu,
                "gpu_inner_host": gpu,
            }
            if selected == "Chill":
                heavy = dict(kwargs)
                heavy["group_meta"] = packed.group_meta[:1].copy()
                heavy["group_meta"][0, 0] = 90
                heavy["group_offsets"] = packed.scoring_group_offsets[:1]
                heavy["group_lengths"] = packed.scoring_group_lengths[:1]
                def signature(pair):
                    return pair[0].tobytes(), pair[1]
                report["fixed_cell_budget_90"] = {
                    "logical_surfaces": int(heavy["group_lengths"].sum()),
                    "cpu_inner_host": _measure_pair(
                        lambda: baseline._score_response_group_meta_cpu(**heavy),
                        lambda: current._score_response_group_meta_cpu(**heavy),
                        signature,
                        args.repeats,
                    ),
                    "gpu_inner_host": _measure_pair(
                        lambda: baseline._score_response_group_meta_gpu(**heavy),
                        lambda: current._score_response_group_meta_gpu(**heavy),
                        signature,
                        args.repeats,
                    ),
                }
            reports.append(report)
            print(json.dumps(report), flush=True)
        result = {
            "platform": sys.platform,
            "gpu_dtype": np.dtype(current.SOLVER_NP_FP).name,
            "baseline_ref": args.baseline_ref,
            "repeats": args.repeats,
            "results": reports,
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
