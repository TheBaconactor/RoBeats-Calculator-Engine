"""
Benchmark: Pure FG (batch) throughput + transfer breakdown.

This runs the packed-task ForceGreatsFinder GPU path (no GA) with synthetic data.

Examples:
  python tools/bench/bench_fg_batch_throughput.py --mode executor --genomes 4096 --ftff 1024 --tasks 64 --max-fp 15,15,15
  python tools/bench/bench_fg_batch_throughput.py --mode direct --genomes 2048 --ftff 512 --tasks 16 --max-fp 8,8,8 --iters 10

Notes:
  - Defaults enable GPU profiler hooks (GPU_PROFILER=1). Set --no-profiler to opt out.
  - Set --reuse-genome-stats to measure the "upload_genome_stats=False" fast path across iterations.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.bench._bench_reporting import emit_bench_result, snapshot_env


def _make_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    rows = int(TOTAL_ROWS) + 1
    x = np.linspace(0.0, 1.0, rows, dtype=np.float64)
    return {
        "Perfect Points": 1.0 + 0.5 * x,
        "Combo Multiplier": 1.0 + 2.0 * x,
        "Fever Multiplier": 1.0 + 4.0 * x,
        "Fever Fill Rate": 1.0 + 0.8 * x,
        "Fever Time": 1.0 + 1.2 * x,
    }


def _parse_int_list(s: str, *, min_len: int = 0) -> list[int]:
    out: list[int] = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception:
            continue
    while len(out) < int(min_len):
        out.append(0)
    return out


def _cfg_len_from_max_fp(max_fp: list[int]) -> int:
    out = 1
    for v in max_fp:
        out *= int(v) + 1
    return int(out)


def _make_ftff_pairs(n: int, *, seed: int, max_ft: int, max_ff: int) -> list[tuple[int, int]]:
    n = int(n)
    if n <= 0:
        return []
    rng = np.random.default_rng(int(seed))
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    # Prefer unique pairs for better cache realism.
    attempts = 0
    while len(out) < n and attempts < n * 20:
        attempts += 1
        ft = int(rng.integers(0, max(1, int(max_ft) + 1)))
        ff = int(rng.integers(0, max(1, int(max_ff) + 1)))
        pair = (ft, ff)
        if pair in seen:
            continue
        seen.add(pair)
        out.append(pair)
    # Fill remainder deterministically if needed.
    ft = 0
    ff = 0
    while len(out) < n:
        out.append((int(ft), int(ff)))
        ft += 1
        if ft > int(max_ft):
            ft = 0
            ff = (ff + 1) % max(1, int(max_ff) + 1)
    return out


def _make_genome_stats(n: int, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    n = int(n)
    arr = np.zeros((n, 7), dtype=np.int32)
    # [pp, cm, fm, p_val, s_val, ft, ff] -> must fit i16 on upload.
    arr[:, 0] = rng.integers(80, 140, size=n, dtype=np.int32)
    arr[:, 1] = rng.integers(80, 140, size=n, dtype=np.int32)
    arr[:, 2] = rng.integers(80, 160, size=n, dtype=np.int32)
    arr[:, 3] = rng.integers(140, 280, size=n, dtype=np.int32)
    arr[:, 4] = rng.integers(140, 280, size=n, dtype=np.int32)
    arr[:, 5] = rng.integers(0, 60, size=n, dtype=np.int32)
    arr[:, 6] = rng.integers(0, 60, size=n, dtype=np.int32)
    return arr


def _print_measurement_breakdown(song_timing) -> None:
    try:
        measurements = getattr(song_timing, "measurements", None) or []
    except Exception:
        measurements = []
    if not measurements:
        return

    agg_sec: dict[str, float] = defaultdict(float)
    for m in measurements:
        try:
            agg_sec[str(m.name)] += float(m.duration_sec or 0.0)
        except Exception:
            continue
    items = sorted(agg_sec.items(), key=lambda kv: kv[1], reverse=True)[:12]
    if not items:
        return
    print("[bench] top measurements:")
    for name, sec in items:
        print(f"  - {name}: {sec * 1000:.2f}ms")


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _steady(values: list[float]) -> list[float]:
    if len(values) <= 1:
        return list(values)
    return list(values[1:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("executor", "direct"), default="executor")
    ap.add_argument("--genomes", type=int, default=1024)
    ap.add_argument("--sections", type=int, default=3)
    ap.add_argument("--max-fp", default="5,5,5", help="Comma-separated max FP per section (implicit configs).")
    ap.add_argument("--tasks", type=int, default=16)
    ap.add_argument("--ftff", type=int, default=256, help="FT/FF pairs per task.")
    ap.add_argument("--notes", type=int, default=1200)
    ap.add_argument("--seconds", type=float, default=160.0)
    ap.add_argument("--long-notes", type=int, default=25)
    ap.add_argument("--budget", type=int, default=90)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--iters", type=int, default=5)
    ap.add_argument("--reuse-genome-stats", action="store_true")
    ap.add_argument("--no-profiler", action="store_true")
    ap.add_argument("--sync-for-timing", action="store_true")
    ap.add_argument("--transfer-trace", action="store_true")
    ap.add_argument("--json", action="store_true", help="Emit final metrics as machine-readable JSON on stdout.")
    ap.add_argument("--json-out", type=str, default="", help="Write final metrics JSON to this path.")
    args = ap.parse_args()

    if not args.no_profiler:
        os.environ.setdefault("GPU_PROFILER", "1")
    os.environ.setdefault("FG_IMPLICIT_CONFIGS", "1")
    if args.sync_for_timing:
        os.environ["GPU_SYNC_FOR_TIMING"] = "1"
    if args.transfer_trace:
        os.environ["FG_TRANSFER_TRACE"] = "1"

    from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

    prof = get_gpu_profiler()
    if not args.no_profiler:
        try:
            prof.enable()
        except Exception:
            pass

    ref_arrays = _make_ref_arrays()
    timestamps = np.linspace(0.0, float(args.seconds), int(args.notes), dtype=np.float32)
    last_note_time = float(timestamps[-1]) if int(timestamps.shape[0]) > 0 else float(args.seconds)
    genome_stats = _make_genome_stats(int(args.genomes), seed=int(args.seed))

    n_sections = max(1, int(args.sections))
    max_fp = _parse_int_list(str(args.max_fp), min_len=n_sections)[:n_sections]
    cfg_len = _cfg_len_from_max_fp(max_fp[:n_sections])

    ftff_per_task = max(1, int(args.ftff))
    tasks: list[dict] = []
    cfg_base = 0
    for i in range(max(1, int(args.tasks))):
        ftff_pairs = _make_ftff_pairs(
            ftff_per_task,
            seed=int(args.seed) + 1000 + i,
            max_ft=15,
            max_ff=15,
        )
        tasks.append(
            {
                "counts_max_fp": list(max_fp),
                "ftff_pairs": ftff_pairs,
                "base_cfg_offset": int(cfg_base),
            }
        )
        cfg_base += int(cfg_len)

    flags = dict(
        is_p_ft=0,
        is_s_ft=0,
        is_p_ff=0,
        is_s_ff=0,
        is_p_pp=0,
        is_s_pp=0,
        is_p_cm=0,
        is_s_cm=0,
        is_p_fm=0,
        is_s_fm=0,
        is_p_ov=1,
        is_s_ov=0,
    )

    gpu_executor = None
    gpu_client = None
    if args.mode == "executor":
        from gear_optimizer.solver.gpu_executor import get_gpu_executor
        from gear_optimizer.solver.gpu_service import GpuServiceClient

        gpu_executor = get_gpu_executor()
        gpu_executor.start(in_process=True)
        gpu_client = GpuServiceClient(gpu_executor)
        gpu_client.start(start_executor=False)

    def _run_once(*, upload_genome_stats: bool) -> dict:
        name = f"FG_Batch_{args.mode}_gen{args.genomes}_tasks{args.tasks}"
        prof.start_song(name)
        t0 = time.perf_counter()
        try:
            if args.mode == "direct":
                from gear_optimizer.solver.taichi_gem.force_greats.api import (
                    fg_download_global_best,
                    fg_reset_global_best,
                    solve_force_greats_finder_gpu_tasks,
                )

                fg_reset_global_best(int(args.genomes))
                solve_force_greats_finder_gpu_tasks(
                    genome_stats,
                    timestamps,
                    None,
                    int(args.long_notes),
                    float(last_note_time),
                    fg_tasks=tasks,
                    n_sections=int(n_sections),
                    ref_arrays=ref_arrays,
                    total_budget=int(args.budget),
                    gem_scale_fever=3,
                    pair_caps_grid=None,
                    pair_caps_from_timeline=False,
                    song_slot=0,
                    upload_genome_stats=bool(upload_genome_stats),
                    **flags,
                )
                result = fg_download_global_best(int(args.genomes))
            else:
                from gear_optimizer.solver.gpu_executor import GpuRequestType

                if gpu_client is None:
                    raise RuntimeError("executor mode requires gpu_client")
                payload = {
                    "args": (
                        genome_stats,
                        timestamps,
                        None,
                        int(args.long_notes),
                        float(last_note_time),
                        None,
                        None,
                    ),
                    "kwargs": {
                        "fg_tasks": tasks,
                        "fg_reset_before": True,
                        "fg_download_after": True,
                        "n_sections": int(n_sections),
                        "ref_arrays": ref_arrays,
                        "total_budget": int(args.budget),
                        "gem_scale_fever": 3,
                        "pair_caps_grid": None,
                        "pair_caps_from_timeline": False,
                        "song_slot": 0,
                        "upload_genome_stats": bool(upload_genome_stats),
                        **flags,
                    },
                }
                result = gpu_client.submit(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, payload).future.result()
            return result
        finally:
            wall = time.perf_counter() - t0
            song = prof.end_song()
            if song is None:
                print(f"[bench] wall={wall * 1000:.2f}ms (no profiler song context)")
                return {
                    "wall_sec": float(wall),
                    "kernel_sec": 0.0,
                    "upload_sec": 0.0,
                    "download_sec": 0.0,
                    "util_pct": 0.0,
                    "upload_bytes": 0,
                    "download_bytes": 0,
                }
            util = 0.0
            try:
                util = (float(song.kernel_sec) + float(song.upload_sec) + float(song.download_sec)) / max(1e-9, wall)
            except Exception:
                util = 0.0
            print(
                f"[bench] wall={wall * 1000:.2f}ms kernel={song.kernel_sec * 1000:.2f}ms "
                f"upload={song.upload_sec * 1000:.2f}ms download={song.download_sec * 1000:.2f}ms "
                f"util~={util * 100:.1f}% up={song.upload_bytes / (1024**2):.2f}MiB dl={song.download_bytes / (1024**2):.2f}MiB"
            )
            _print_measurement_breakdown(song)
            return {
                "wall_sec": float(wall),
                "kernel_sec": float(song.kernel_sec),
                "upload_sec": float(song.upload_sec),
                "download_sec": float(song.download_sec),
                "util_pct": float(util * 100.0),
                "upload_bytes": int(song.upload_bytes),
                "download_bytes": int(song.download_bytes),
            }

    print(
        "[bench] FG packed-tasks config: "
        f"mode={args.mode} genomes={args.genomes} tasks={args.tasks} ftff/task={ftff_per_task} "
        f"sections={n_sections} max_fp={max_fp} cfg_len/task={cfg_len} notes={args.notes}"
    )

    try:
        # Warmup (Taichi compile + cache)
        for _ in range(max(0, int(args.warmup))):
            _run_once(upload_genome_stats=True)

        # If we're testing reuse, ensure one upload happened (and clear profiler totals).
        if args.reuse_genome_stats:
            prof.reset()
            _run_once(upload_genome_stats=True)

        prof.reset()
        iteration_records: list[dict] = []
        for i in range(max(1, int(args.iters))):
            print(f"[bench] iter {i + 1}/{int(args.iters)}")
            iteration_records.append(_run_once(upload_genome_stats=bool(not args.reuse_genome_stats)))

        print(prof.report(verbose=False))
        wall_values = [float(record.get("wall_sec", 0.0)) for record in iteration_records]
        kernel_values = [float(record.get("kernel_sec", 0.0)) for record in iteration_records]
        upload_values = [float(record.get("upload_sec", 0.0)) for record in iteration_records]
        download_values = [float(record.get("download_sec", 0.0)) for record in iteration_records]
        util_values = [float(record.get("util_pct", 0.0)) for record in iteration_records]
        steady_wall_values = _steady(wall_values)
        mean_wall = _mean(wall_values)
        steady_mean_wall = _mean(steady_wall_values)
        emit_bench_result(
            {
                "bench": "fg_batch_throughput",
                "mode": str(args.mode),
                "genomes": int(args.genomes),
                "sections": int(n_sections),
                "tasks": int(args.tasks),
                "ftff_per_task": int(ftff_per_task),
                "cfg_len_per_task": int(cfg_len),
                "max_fp": [int(v) for v in max_fp],
                "notes": int(args.notes),
                "seconds": float(args.seconds),
                "long_notes": int(args.long_notes),
                "budget": int(args.budget),
                "warmup": int(args.warmup),
                "iters": int(args.iters),
                "reuse_genome_stats": bool(args.reuse_genome_stats),
                "profiler_enabled": bool(not args.no_profiler),
                "iteration_wall_sec": wall_values,
                "iteration_kernel_sec": kernel_values,
                "iteration_upload_sec": upload_values,
                "iteration_download_sec": download_values,
                "iteration_util_pct": util_values,
                "mean_wall_sec": float(mean_wall),
                "steady_mean_wall_sec": float(steady_mean_wall),
                "iters_per_sec": float((1.0 / mean_wall) if mean_wall > 0.0 else 0.0),
                "steady_iters_per_sec": float((1.0 / steady_mean_wall) if steady_mean_wall > 0.0 else 0.0),
                "env": snapshot_env(
                    [
                        "FG_STAGE1_BLOCK_DIM",
                        "FG_TARGET_THREADS_PER_KERNEL",
                        "FG_SMALL_WORK_SINGLE_BAND",
                        "FG_SMALL_WORK_MAX_WORK_ITEMS",
                        "FG_SMALL_WORK_MAX_CFG_LEN",
                        "FG_STAGE1_SMALL_SECTIONS_FASTPATH",
                    ]
                ),
            },
            json_stdout=bool(args.json),
            json_out=str(args.json_out or ""),
        )
    finally:
        if gpu_client is not None:
            try:
                gpu_client.close()
            except Exception:
                pass
        if gpu_executor is not None:
            try:
                gpu_executor.stop()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
