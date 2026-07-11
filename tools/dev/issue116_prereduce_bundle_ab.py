"""Bundle-level A/B for the region2 same-mask pre-reduction (Issue #116).

Runs the REAL FG response-frontier prebuild (plus the base timeline prebuild it
expects) for a fixed two-song queue into an isolated cache root under C:/mfbench,
then compares every persisted FG cache artifact between two such roots array by
array. Byte-identical persisted frontiers imply identical served best_fg_score for
these songs by construction.

Usage:
    python tools/dev/issue116_prereduce_bundle_ab.py build --root C:/mfbench/issue116-prereduce-baseline/cacheA
    python tools/dev/issue116_prereduce_bundle_ab.py build --root C:/mfbench/issue116-prereduce-baseline/cacheB
    python tools/dev/issue116_prereduce_bundle_ab.py compare --root C:/mfbench/issue116-prereduce-baseline/cacheA --other C:/mfbench/issue116-prereduce-baseline/cacheB
"""

from __future__ import annotations

import argparse

import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_SONGS = (
    ("Normal", "Stars by James Landino.txt"),
    ("Normal", "Calamity Fortune [EXTENDED CUT] by LeaF (7eaF) [Anniversary].txt"),
)


def _build(root: Path) -> int:
    if not str(root).lower().startswith("c:\\mfbench") and not str(root).lower().startswith("c:/mfbench"):
        raise SystemExit(f"refusing cache root outside C:/mfbench: {root}")
    (root / "timeline").mkdir(parents=True, exist_ok=True)
    (root / "fg").mkdir(parents=True, exist_ok=True)
    os.environ["TIMELINE_FRONTIER_CACHE_DIR"] = str(root / "timeline")
    os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(root / "fg")

    from gear_optimizer.core.config import get_config_path, load_config, load_paths_cache
    from gear_optimizer.core.constants import PATHS
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import (
        run_fg_response_frontier_cache_prebuild,
    )
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import (
        run_timeline_frontier_cache_prebuild,
    )

    try:
        cfg = load_config(get_config_path("config.ini"))
    except Exception:
        cfg = None
    paths_cache = load_paths_cache() or {}
    stats_path = str((paths_cache.get("Stats") or PATHS.stats_csv) or "").strip()
    if not stats_path or not os.path.exists(stats_path):
        raise SystemExit(f"cannot find Stats table at {stats_path!r}")
    ref_arrays = build_ref_arrays_from_stats(read_table(stats_path), dtype=np.float32)

    queue = []
    for diff, name in _SONGS:
        chart_path = REPO / "Data" / diff / name
        if not chart_path.exists():
            raise SystemExit(f"chart not found: {chart_path}")
        queue.append((str(chart_path), name, diff))

    t0 = time.perf_counter()
    tl = run_timeline_frontier_cache_prebuild(cfg=cfg, song_queue=queue, ref_arrays=ref_arrays, data_root=None)
    fg = run_fg_response_frontier_cache_prebuild(cfg=cfg, song_queue=queue, ref_arrays=ref_arrays, data_root=None)
    elapsed = time.perf_counter() - t0
    print(
        f"built into {root}: timeline built={tl.built} fail={tl.failures} "
        f"FG built={fg.built} fail={fg.failures} in {elapsed:.1f}s"
    )
    if int(tl.failures) or int(fg.failures):
        raise SystemExit("prebuild reported failures")
    return 0


def _compare(root_a: Path, root_b: Path) -> int:
    files_a = sorted(p.name for p in (root_a / "fg").glob("*.npz"))
    files_b = sorted(p.name for p in (root_b / "fg").glob("*.npz"))
    if not files_a:
        raise SystemExit(f"no FG cache files under {root_a}")
    if files_a != files_b:
        raise SystemExit(
            f"cache file sets differ:\n  only A: {sorted(set(files_a) - set(files_b))}\n"
            f"  only B: {sorted(set(files_b) - set(files_a))}"
        )
    mismatches = 0
    for name in files_a:
        with np.load(root_a / "fg" / name, allow_pickle=True) as za, np.load(
            root_b / "fg" / name, allow_pickle=True
        ) as zb:
            keys_a = sorted(za.files)
            keys_b = sorted(zb.files)
            if keys_a != keys_b:
                mismatches += 1
                print(f"  !! {name}: array key sets differ")
                continue
            for key in keys_a:
                arr_a = za[key]
                arr_b = zb[key]
                if arr_a.shape != arr_b.shape or arr_a.dtype != arr_b.dtype or not np.array_equal(
                    arr_a, arr_b
                ):
                    mismatches += 1
                    print(f"  !! {name}[{key}]: content differs")
    if mismatches:
        raise SystemExit(f"{mismatches} artifact mismatches -- bundles are NOT identical")
    print(f"BUNDLES IDENTICAL: {len(files_a)} FG cache files, every array equal")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("build", "compare"))
    ap.add_argument("--root", required=True)
    ap.add_argument("--other", default=None)
    args = ap.parse_args()
    root = Path(args.root)
    if args.mode == "build":
        return _build(root)
    if not args.other:
        raise SystemExit("compare requires --other")
    return _compare(root, Path(args.other))


if __name__ == "__main__":
    raise SystemExit(main())
