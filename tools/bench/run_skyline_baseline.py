"""Run one full exact-Skyline solve on a real song and report a profiled baseline.

This is the EXACT outer search (tests/parity/exact_skyline.solve_exact_skyline) -- the
self-contained, cold path: it builds its own complete candidate frontier from the static
gear/mini pools + the chart, with NO dependency on GA results, the DB, or any cached
candidate set. It runs in-process under _GPU_LOCK (dispatch_registry_solve's gpu_client=None
direct path), single GPU owner thread.

Reports: total wall-clock, the per-phase breakdown (skyline_phase_seconds) and candidate-count
funnel (skyline_phase_counts), and the resulting base/FG scores -- the "before" picture the
speedup work is measured against.

Usage (from repo root):
  python tools/bench/run_skyline_baseline.py --difficulty Easy
  python tools/bench/run_skyline_baseline.py --difficulty Easy --song "Aether"
  python tools/bench/run_skyline_baseline.py --song-fp "Data/Easy/Aether (Easy) by Geoxor.txt" --runs 2
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load_ref_arrays() -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.csv_parser import read_table

    stats_table = read_table(os.path.join(REPO_ROOT, "Data", "Gear", "Stats.txt"))
    rows = int(TOTAL_ROWS) + 1
    names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref: dict[str, np.ndarray] = {}
    for i, name in enumerate(names):
        temp = []
        for v in range(rows):
            li = int(TOTAL_ROWS) - v
            try:
                val = stats_table[li][i] if stats_table else 0
            except Exception:
                val = 0
            temp.append(val)
        ref[name] = np.array(temp, dtype=np.float64)
    return ref


def _pick_song(difficulty: str, song_fp: str, song: str) -> str:
    if song_fp:
        return song_fp if os.path.isabs(song_fp) else os.path.join(REPO_ROOT, song_fp)
    folder = os.path.join(REPO_ROOT, "Data", difficulty)
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".txt"))
    if not files:
        raise SystemExit(f"No charts in {folder}")
    if song:
        for f in files:
            if song.lower() in f.lower():
                return os.path.join(folder, f)
        raise SystemExit(f"No chart matching {song!r} in {folder}")
    return os.path.join(folder, files[0])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--difficulty", default="Easy")
    ap.add_argument("--song-fp", default="")
    ap.add_argument("--song", default="", help="substring match within the difficulty folder")
    ap.add_argument("--runs", type=int, default=2, help="timed repeats (run 1 is cold = includes kernel compile)")
    ap.add_argument("--verbose", action="store_true", help="print skyline status callbacks")
    args = ap.parse_args()

    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )
    from tests.parity.exact_skyline import solve_exact_skyline

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)

    fp = _pick_song(args.difficulty, args.song_fp, args.song)
    calc_song = get_base_calc_song(fp, cfg_dict)
    meta = (calc_song or {}).get("metadata", {}) or {}
    ref_arrays = _load_ref_arrays()
    all_gears = list(get_gears_by_name_cached().values())
    all_minis = list(get_minis_by_name_cached().values())

    print(f"[song] {os.path.basename(fp)}")
    print(f"       diff={meta.get('Difficulty')} colors={meta.get('Primary Color')}/{meta.get('Secondary Color')} "
          f"notes={meta.get('Total Notes')} gears={len(all_gears)} minis={len(all_minis)}")

    status_cb = (lambda m: print(f"   . {m}")) if args.verbose else None

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)

        last_summary = None
        for r in range(max(1, int(args.runs))):
            t0 = time.perf_counter()
            best_data, _bg, _bm, native_fg_summary, _r, _e, all_eval = solve_exact_skyline(
                cfg, {}, {}, calc_song, ref_arrays, all_gears, all_minis, {}, {},
                status_cb=status_cb, song_slot=0, gpu_client=None,
            )
            dt = time.perf_counter() - t0
            cold = " (cold: incl kernel compile)" if r == 0 else ""
            best_base = int((best_data or {}).get("Score", (best_data or {}).get("BaseScore", 0)) or 0)
            best_fg = int((native_fg_summary or {}).get("best_fg_score", 0) or 0)
            print(f"\n[run {r + 1}/{args.runs}] wall={dt:.3f}s{cold}  base_score={best_base:,}  fg_score={best_fg:,}  "
                  f"candidates_evaluated={len(all_eval)}")
            last_summary = native_fg_summary

    if last_summary:
        phase_sec = last_summary.get("skyline_phase_seconds", {}) or {}
        phase_cnt = last_summary.get("skyline_phase_counts", {}) or {}
        print("\n=== PHASE BREAKDOWN (warm run) ===")
        print("phase_seconds (top 15 by time):")
        for name, sec in sorted(phase_sec.items(), key=lambda kv: float(kv[1]), reverse=True)[:15]:
            print(f"   {float(sec):8.3f}s  {name}")
        print("\nphase_counts (candidate funnel):")
        for key in ("gear_dp_pairs", "gear_global_skyline_in", "gear_global_skyline_out",
                    "combined_skyline_candidates", "combined_fixed_timing_candidates",
                    "candidate_payloads"):
            if key in phase_cnt:
                print(f"   {int(phase_cnt[key]):>12,}  {key}")
        print("\nNativeFG summary:")
        for key in ("mode", "candidate_scope", "base_keep_top_k", "combined_skyline_candidates",
                    "exact_calls", "fg_gains", "best_fg_score", "skyline_certification_status"):
            if key in last_summary:
                print(f"   {key} = {last_summary[key]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
