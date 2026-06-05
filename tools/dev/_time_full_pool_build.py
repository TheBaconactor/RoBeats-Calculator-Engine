"""Focused timing harness for the full-pool cold cache build.

Replays the exact production setup performed in
``gear_optimizer/app.py`` (``_run_single_iteration`` lines ~352-410) up to the
``run_startup_cpu_work(...)`` call, then times that call with a wall-clock
``time.perf_counter()``. Avoids the long GA that would otherwise follow.

This is a measurement-only dev tool. It does NOT modify production code; it
captures the timeline + FG response-frontier prebuild summaries by intercepting
``cpu_work_manager._emit_summary`` (which production already calls with the real
summary objects) so we can print total/built/disk/memory/failures.

Usage:
    python -u tools/dev/_time_full_pool_build.py
"""

from __future__ import annotations

import os
import sys
import time

# Ensure repo root on path when run directly.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np

from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.config import load_config, load_paths_cache
from gear_optimizer.data.database import init_db
from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.app import GearOptimizerApp
import gear_optimizer.solver.cpu_work_manager as cwm


# --- Capture the real summary objects production logs, without touching prod code. ---
_CAPTURED: dict[str, object] = {}
_orig_emit_summary = cwm._emit_summary


def _capturing_emit_summary(*, phase, label, summary, elapsed_ms):  # noqa: ANN001
    _CAPTURED[phase] = summary
    return _orig_emit_summary(phase=phase, label=label, summary=summary, elapsed_ms=elapsed_ms)


cwm._emit_summary = _capturing_emit_summary


def _fmt_summary(tag: str, s) -> str:  # noqa: ANN001
    if s is None:
        return f"  {tag}: <no summary captured>"
    fields = ("total", "built", "disk", "memory", "completed", "failures")
    parts = []
    for f in fields:
        if hasattr(s, f):
            parts.append(f"{f}={int(getattr(s, f))}")
    return f"  {tag}: " + " ".join(parts)


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "RUN"
    print(f"[TimeFullPool] ({label}) METAFINDER_CONFIG_PATH="
          f"{os.environ.get('METAFINDER_CONFIG_PATH', '(unset->default config.ini)')}", flush=True)

    # --- Replicate the production pre-build setup from app.py lines ~352-410. ---
    app = GearOptimizerApp()
    cfg = load_config()
    runtime_settings = app._current_runtime_settings(cfg)
    app._runtime_settings = runtime_settings
    paths = load_paths_cache()
    init_db()
    app._maybe_autoset_gpu_song_slots(cfg)
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    app._disable_inputs_to_prevent_taint(cfg)
    ref_arrays = app._preload_ref_arrays(stats_table)
    song_queue = app._build_song_queue(cfg, paths)

    print(f"[TimeFullPool] ({label}) queued_songs={len(song_queue)}", flush=True)

    # --- Time the cold build wall-clock. ---
    t0 = time.perf_counter()
    cwm.run_startup_cpu_work(
        cfg=cfg,
        song_queue=song_queue,
        ref_arrays=ref_arrays,
        data_root=PATHS.data_dir,
        announce_stream=sys.stdout,
    )
    wall_s = time.perf_counter() - t0

    timeline = _CAPTURED.get("timeline_frontier_cache")
    fg = _CAPTURED.get("fg_response_frontier_cache")

    print("=" * 72, flush=True)
    print(f"[TimeFullPool] ({label}) RESULT", flush=True)
    print(f"  queued_songs    = {len(song_queue)}", flush=True)
    print(f"  WALL_CLOCK      = {wall_s:.1f}s  ({wall_s/60.0:.2f} min)", flush=True)
    print(_fmt_summary("timeline_frontier", timeline), flush=True)
    print(_fmt_summary("fg_response_frontier", fg), flush=True)
    print("=" * 72, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
