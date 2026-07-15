#!/usr/bin/env python3
"""Measure COLD production cache build time (timeline + exact Base context + native FG) on a
stratified sample and extrapolate to the full pool.

Builds into fresh temp cache dirs (timeline/context/FG cache roots set
to throwaway paths) so it never disturbs the warm bin/ caches. A small warmup
build pays the one-time Numba JIT + process-pool spawn first, so the measured
per-song rate is steady-state (the JIT is amortized once over the real pool, not
multiplied per song).

Usage:
    python tools/dev/measure_pool_build.py                 # 40/difficulty, strided
    python tools/dev/measure_pool_build.py --per 60
    python tools/dev/measure_pool_build.py --per 3 --no-warmup   # quick smoke
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

DIFFS = ("Easy", "Normal", "Hard")


def _strided(files: list[str], n: int) -> list[str]:
    if n <= 0 or len(files) <= n:
        return list(files)
    step = len(files) / float(n)
    return [files[int(i * step)] for i in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure cold production cache build time and extrapolate to the pool.")
    ap.add_argument("--per", type=int, default=40, help="songs sampled per difficulty (default 40)")
    ap.add_argument("--first", action="store_true", help="sample first-N (alphabetical) instead of strided")
    ap.add_argument("--no-warmup", action="store_true", help="skip JIT warmup (rate will include one-time JIT)")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="coldbuild_"))
    os.environ["TIMELINE_FRONTIER_CACHE_DIR"] = str(tmp / "timeline")
    os.environ["EXACT_BASE_SONG_CONTEXT_CACHE_DIR"] = str(tmp / "exact_base_context")
    os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(tmp / "fg")
    (tmp / "timeline").mkdir(parents=True, exist_ok=True)
    (tmp / "exact_base_context").mkdir(parents=True, exist_ok=True)
    (tmp / "fg").mkdir(parents=True, exist_ok=True)

    import numpy as np

    from gear_optimizer.core.config import get_config_path, load_config, load_paths_cache
    from gear_optimizer.core.constants import PATHS
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.exact_base_song_context_cache_prebuild import (
        run_exact_base_song_context_cache_prebuild,
    )
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import run_fg_response_frontier_cache_prebuild
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import run_timeline_frontier_cache_prebuild

    try:
        cfg = load_config(get_config_path("config.ini"))
    except Exception:
        cfg = None

    paths_cache = load_paths_cache() or {}
    stats_path = str((paths_cache.get("Stats") or PATHS.stats_csv) or "").strip()
    if not stats_path or not os.path.exists(stats_path):
        raise SystemExit(f"[measure] cannot find Stats table at {stats_path!r}")
    ref_arrays = build_ref_arrays_from_stats(read_table(stats_path), dtype=np.float32)  # matches production

    pool_counts = {d: len(glob.glob(str(REPO / "Data" / d / "*.txt"))) for d in DIFFS}
    total_pool = sum(pool_counts.values())
    print(f"pool: {pool_counts}  total={total_pool}")
    print(f"sample: {args.per}/difficulty  ({'first-N' if args.first else 'strided'})  temp={tmp}")

    def _build(queue: list[tuple], label: str) -> tuple[float, float, float, object, object, object]:
        t0 = time.perf_counter()
        tl = run_timeline_frontier_cache_prebuild(cfg=cfg, song_queue=queue, ref_arrays=ref_arrays, data_root=None)
        tl_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        context = run_exact_base_song_context_cache_prebuild(
            cfg=cfg,
            song_queue=queue,
            ref_arrays=ref_arrays,
            data_root=None,
        )
        context_s = time.perf_counter() - t1
        t2 = time.perf_counter()
        fg = run_fg_response_frontier_cache_prebuild(cfg=cfg, song_queue=queue, ref_arrays=ref_arrays, data_root=None)
        fg_s = time.perf_counter() - t2
        print(
            f"  [{label}] timeline built={tl.built} disk={tl.disk} fail={tl.failures} {tl_s:.1f}s   "
            f"context built={context.built} disk={context.disk} fail={context.failures} {context_s:.1f}s   "
            f"FG built={fg.built} disk={fg.disk} fail={fg.failures} {fg_s:.1f}s"
        )
        return tl_s, context_s, fg_s, tl, context, fg

    if not args.no_warmup:
        warm = []
        for d in DIFFS:
            fs = sorted(glob.glob(str(REPO / "Data" / d / "*.txt")))
            warm += [(fp, os.path.basename(fp), d) for fp in fs[-2:]]  # tail 2/diff, disjoint from strided/first-N
        print("warmup (JIT + pool spawn; not counted):")
        _build(warm, "warmup")

    tl_total = context_total = fg_total = 0.0
    n_total = 0
    rows = []
    for d in DIFFS:
        fs = sorted(glob.glob(str(REPO / "Data" / d / "*.txt")))
        pick = (fs[: args.per] if args.first else _strided(fs, args.per))
        queue = [(fp, os.path.basename(fp), d) for fp in pick]
        tl_s, context_s, fg_s, tl, context, fg = _build(queue, d)
        n = max(1, int(tl.built) or len(queue))
        rows.append((d, n, tl_s, context_s, fg_s, pool_counts[d]))
        tl_total += tl_s
        context_total += context_s
        fg_total += fg_s
        n_total += n

    print("\n--- per-difficulty cold rates + extrapolation ---")
    tl_pool = context_pool = fg_pool = 0.0
    for d, n, tl_s, context_s, fg_s, pc in rows:
        tl_rate, context_rate, fg_rate = tl_s / n, context_s / n, fg_s / n
        tl_pool += tl_rate * pc
        context_pool += context_rate * pc
        fg_pool += fg_rate * pc
        print(
            f"  {d:6s} n={n:3d}  timeline {tl_rate*1000:5.0f} ms/song  "
            f"context {context_rate*1000:6.0f} ms/song  FG {fg_rate*1000:6.0f} ms/song"
            f"   -> pool {pc}: timeline {tl_rate*pc:5.0f}s  "
            f"context {context_rate*pc:6.0f}s  FG {fg_rate*pc:6.0f}s"
        )

    print(f"\n=== FULL POOL ({total_pool} songs) COLD BUILD ESTIMATE ===")
    print(f"  base timeline : ~{tl_pool:6.0f}s  (~{tl_pool/60:.1f} min)")
    print(f"  exact context : ~{context_pool:6.0f}s  (~{context_pool/60:.1f} min)")
    print(f"  FG frontier   : ~{fg_pool:6.0f}s  (~{fg_pool/60:.1f} min)")
    total_build = tl_pool + context_pool + fg_pool
    print(f"  TOTAL         : ~{total_build:6.0f}s  (~{total_build/60:.1f} min)")
    print("  (parallel prebuild; excludes one-time JIT warmup; FG cone-dominance lossless prune included)")

    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
