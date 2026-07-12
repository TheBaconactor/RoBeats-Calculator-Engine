"""Build one complete isolated FG response-frontier song bundle with phase telemetry."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
TOOLS_DEV = Path(__file__).resolve().parent
if str(TOOLS_DEV) not in sys.path:
    sys.path.insert(0, str(TOOLS_DEV))


def _isolated_root(path: Path) -> Path:
    root = path.expanduser().absolute()
    if not str(root).lower().startswith("c:\\mfbench\\"):
        raise SystemExit(f"refusing complete build root outside C:\\mfbench: {root}")
    fg = root / "fg"
    if root.exists() and any(fg.glob("*")):
        raise SystemExit(f"isolated FG cache root is not empty: {fg}")
    fg.mkdir(parents=True, exist_ok=True)
    (root / "timeline").mkdir(parents=True, exist_ok=True)
    return root


def _load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--song", required=True)
    parser.add_argument("--diff", default="Normal", choices=("Easy", "Normal", "Hard"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--reducer-threads", required=True, type=int)
    parser.add_argument("--production-prebuild", action="store_true")
    args = parser.parse_args()
    if int(args.reducer_threads) < 1:
        raise SystemExit("reducer threads must be positive")
    root = _isolated_root(args.root)
    events_path = root / "profile_events.jsonl"
    os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(root / "fg")
    os.environ["TIMELINE_FRONTIER_CACHE_DIR"] = str(root / "timeline")
    os.environ["METAFINDER_PROFILE_EVENTS_PATH"] = str(events_path)

    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.constants import PATHS
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import (
        build_fg_response_frontier_cache_for_path,
        run_fg_response_frontier_cache_prebuild,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (
        configure_force_greats_response_first_frontier_threads,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
        all_response_stat_keys,
    )
    from issue116_amdahl_probe import _find_chart

    paths_cache = load_paths_cache() or {}
    stats_path = str((paths_cache.get("Stats") or PATHS.stats_csv) or "").strip()
    if not stats_path or not os.path.exists(stats_path):
        raise SystemExit(f"cannot find Stats table at {stats_path!r}")
    ref_arrays = build_ref_arrays_from_stats(read_table(stats_path), dtype=np.float32)
    chart = _find_chart(args.song, args.diff)
    started = time.perf_counter()
    if args.production_prebuild:
        summary = run_fg_response_frontier_cache_prebuild(
            cfg=None,
            song_queue=((chart, os.path.basename(chart), args.diff),),
            ref_arrays=ref_arrays,
            data_root=None,
        )
        result_payload = {
            "source": "production_prebuild",
            "result_build_ms": float(summary.elapsed_ms),
            "cache_file": "",
            "summary": {
                "total": int(summary.total),
                "completed": int(summary.completed),
                "failures": int(summary.failures),
                "built": int(summary.built),
                "disk": int(summary.disk),
            },
        }
    else:
        previous = configure_force_greats_response_first_frontier_threads(int(args.reducer_threads))
        try:
            result = build_fg_response_frontier_cache_for_path(
                chart,
                ref_arrays,
                stat_keys=all_response_stat_keys(),
            )
        finally:
            configure_force_greats_response_first_frontier_threads(int(previous))
        result_payload = {
            "source": result.source,
            "result_build_ms": float(result.build_ms),
            "cache_file": result.cache_file,
        }
    elapsed = time.perf_counter() - started
    events = _load_events(events_path)
    phase_events = {
        str(event.get("event")): event.get("metrics", {})
        for event in events
        if event.get("event")
        in {"prebuild_admit", "frontier_build", "payload_materialize", "prebuild_song_done"}
    }
    print(
        json.dumps(
            {
                "song": os.path.basename(chart),
                "reducer_threads_requested": int(args.reducer_threads),
                **result_payload,
                "wall_seconds": float(elapsed),
                "phases": phase_events,
            },
            indent=2,
            sort_keys=True,
        )
    )
    if args.production_prebuild:
        if int(summary.failures) != 0 or int(summary.built) != 1:
            raise SystemExit(f"production prebuild failed: {summary}")
    elif result.source != "built":
        raise SystemExit(f"expected isolated cold build, got source={result.source!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
