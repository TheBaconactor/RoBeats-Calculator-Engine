"""
Benchmark: FG bundle (real song) wall-time + GPU executor gaps.

Goal: isolate ForceGreatsFinder GPU bundle behavior (no GA) and measure the
time *between* FG GPU jobs when many FG jobs are queued.

This script:
  - Loads a real song .txt chart (calc_song) + ref arrays.
  - Pulls FG seed loadouts from the DB (team_buff_* tables when present).
  - Runs `process_force_greats(..., force_greats_finder=True, use_gpu=True)` for N jobs.
  - Optionally runs jobs concurrently to stress the GPU request queue and coalescing.
  - Writes a GPU executor trace CSV and prints a gap/utilization summary.

Examples:
  python tools/bench/bench_fg_bundle_real_song.py --song-fp "Data/Normal/Insight by Haywyre.txt" --jobs 100 --workers 12
  python tools/bench/bench_fg_bundle_real_song.py --jobs 100 --workers 12 --trace artifacts/bench/fg_bundle/gpu_trace.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _truthy(raw: str) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_song_fp(cfg_dict: dict, song_fp: str | None) -> str:
    if song_fp:
        return str(song_fp)

    calc = cfg_dict.get("CalculateSong", {}) if isinstance(cfg_dict, dict) else {}
    song_name = str(calc.get("Song_Name") or "").strip()
    difficulty = str(calc.get("Difficulty") or "").strip()
    if not song_name or not difficulty:
        raise SystemExit("Missing --song-fp and config.ini CalculateSong.Song_Name/Difficulty not set.")

    folder = os.path.join("Data", difficulty)
    if not os.path.isdir(folder):
        raise SystemExit(f"Could not find difficulty folder: {folder!r}. Pass --song-fp.")

    exact = os.path.join(folder, f"{song_name}.txt")
    if os.path.isfile(exact):
        return exact

    # Fallback: substring search (common for charts named with suffixes).
    matches: list[str] = []
    for fn in os.listdir(folder):
        if not fn.lower().endswith(".txt"):
            continue
        if song_name.lower() in fn.lower():
            matches.append(os.path.join(folder, fn))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"No chart match for {song_name!r} in {folder!r}. Pass --song-fp.")
    raise SystemExit(
        "Multiple chart matches; pass --song-fp:\n" + "\n".join(f"  - {m}" for m in matches[:30])
    )


def _analyze_trace(trace_path: str) -> None:
    if not trace_path or not os.path.isfile(trace_path):
        return

    rows: list[dict] = []
    with open(trace_path, "r", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        for r in rdr:
            try:
                r["rel_ts"] = float(r.get("rel_ts", 0.0) or 0.0)
                r["wait_sec"] = float(r.get("wait_sec", 0.0) or 0.0)
                r["exec_sec"] = float(r.get("exec_sec", 0.0) or 0.0)
            except Exception:
                continue
            rows.append(r)
    if not rows:
        return

    fg_exec = [r for r in rows if r.get("event") == "exec" and "fg_" in str(r.get("types") or "")]
    if not fg_exec:
        print(f"[fg-bundle] trace={trace_path} (no fg exec rows)")
        return

    start = min(float(r["rel_ts"]) - float(r["exec_sec"]) for r in fg_exec)
    end = max(float(r["rel_ts"]) for r in fg_exec)

    window = []
    for r in rows:
        rt = float(r["rel_ts"])
        if rt < start - 0.001 or rt > end + 0.001:
            continue
        window.append(r)

    wait_total = sum(float(r["wait_sec"]) for r in window if r.get("event") == "wait")
    exec_total = sum(float(r["exec_sec"]) for r in window if r.get("event") == "exec")
    busy = exec_total / (exec_total + wait_total) * 100.0 if (exec_total + wait_total) > 0 else 0.0
    print(
        f"[fg-bundle] trace_fg_window={start:.3f}s->{end:.3f}s dur={end-start:.3f}s "
        f"executor_wait={wait_total:.3f}s exec={exec_total:.3f}s busy={busy:.1f}%"
    )

    # Gap analysis between exec intervals.
    intervals = []
    for r in window:
        if r.get("event") != "exec":
            continue
        e = float(r["rel_ts"])
        s = e - float(r["exec_sec"])
        intervals.append((s, e, str(r.get("types") or "")))
    intervals.sort()
    gaps = []
    for (_s0, e0, _t0), (s1, _e1, _t1) in zip(intervals, intervals[1:]):
        gaps.append(max(0.0, s1 - e0))
    if gaps:
        gaps_sorted = sorted(gaps)
        p50 = gaps_sorted[len(gaps_sorted) // 2] * 1000.0
        p95 = gaps_sorted[int(0.95 * (len(gaps_sorted) - 1))] * 1000.0
        mx = max(gaps_sorted) * 1000.0
        sm = sum(gaps_sorted)
        print(f"[fg-bundle] gaps n={len(gaps_sorted)} sum={sm:.3f}s p50={p50:.2f}ms p95={p95:.2f}ms max={mx:.2f}ms")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song-fp", default="", help="Chart .txt path (defaults from config.ini if resolvable).")
    ap.add_argument("--jobs", type=int, default=100, help="Number of FG jobs to run.")
    ap.add_argument("--workers", type=int, default=12, help="CPU worker threads (FG jobs in flight).")
    ap.add_argument("--candidate-limit", type=int, default=0, help="Override FG_CandidateLimit (0=use config).")
    ap.add_argument("--team-buff", default="", help="Override TeamBuff tier (e.g., T1/T5/T10/T15/NONE).")
    ap.add_argument("--trace", default="artifacts/bench/fg_bundle/gpu_executor_trace.csv", help="GPU trace CSV path.")
    ap.add_argument("--no-trace", action="store_true", help="Disable GPU executor trace output.")
    ap.add_argument("--no-profiler", action="store_true", help="Disable GPU_PROFILER (DebugProfile gate still applies).")
    ap.add_argument("--debug-profile", action="store_true", help="Enable METAFINDER_DEBUG_PROFILE=1 for this run.")
    args = ap.parse_args()

    # Must set env vars before importing Taichi modules / ENV config singleton.
    if args.debug_profile:
        os.environ.setdefault("METAFINDER_DEBUG_PROFILE", "1")
    if not args.no_profiler:
        os.environ.setdefault("GPU_PROFILER", "1")
    os.environ.setdefault("GPU_EXECUTOR_PROFILE", "1")
    os.environ.setdefault("GPU_SERVICE_PROFILE", "1")
    os.environ.setdefault("GPU_SERVICE_PROFILE_PRINT", "1")
    if not args.no_trace:
        os.environ["GPU_EXECUTOR_TRACE_PATH"] = str(args.trace)

    from gear_optimizer.core.config import load_config, read_fg_candidate_limit, read_fg_search_radius
    from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, TOTAL_ROWS
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.data.database import get_best_loadouts
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
    from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
    from gear_optimizer.pipeline.song_processor import get_base_calc_song
    from gear_optimizer.solver.gpu_service import GpuServiceClient

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)
    song_fp = _resolve_song_fp(cfg_dict, str(args.song_fp or "").strip() or None)

    # Ref arrays from Stats.txt
    stats_table = read_table("Data/Gear/Stats.txt")
    rows = int(TOTAL_ROWS) + 1
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    import numpy as np

    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp = []
        for v in range(rows):
            lookup_index = int(TOTAL_ROWS) - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp.append(val)
        ref_arrays[name] = np.array(temp, dtype=np.float64)

    calc_song = get_base_calc_song(song_fp, cfg_dict)
    meta = calc_song.get("metadata", {}) or {}
    found_name = str(meta.get("Song Name") or meta.get("Song_Name") or "").strip()
    difficulty = str(meta.get("Difficulty") or "").strip()
    p_color = str(meta.get("Primary Color") or "").strip()
    s_color = str(meta.get("Secondary Color") or "").strip()
    build_details = make_build_details_fn(p_color, s_color, difficulty)

    limit_cfg = int(read_fg_candidate_limit(cfg, default=FG_CANDIDATE_LIMIT, min_limit=1) or FG_CANDIDATE_LIMIT)
    limit = int(args.candidate_limit) if int(args.candidate_limit or 0) > 0 else int(limit_cfg)
    radius = read_fg_search_radius(cfg)
    radius = int(radius) if radius is not None else int(os.environ.get("FG_SEARCH_RADIUS", "5") or "5")

    team_buff = str(args.team_buff or "").strip().upper()
    if not team_buff:
        team_buff = str(cfg_dict.get("TeamContributionBuffConstant", {}).get("TeamBuff", "T5") or "T5").strip().upper()

    if not found_name:
        raise SystemExit(f"Could not read Song Name from chart: {song_fp!r}")

    gears_by_name = get_gears_by_name_cached()
    minis_by_name = get_minis_by_name_cached()
    seeds = get_best_loadouts(
        found_name,
        limit=int(limit),
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        team_buff=str(team_buff),
    )
    if not seeds:
        raise SystemExit(f"No DB seeds for {found_name!r}. Run optimizer first or point EVOLUTION_DB_PATH.")

    force_cfg = cfg_dict.get("ForceGreats", {}) if isinstance(cfg_dict, dict) else {}

    def _make_entries() -> dict:
        out = {}
        for i, row in enumerate(seeds):
            if not isinstance(row, dict):
                continue
            e = dict(row)
            # Force a real recompute (avoid cached force payload short-circuit).
            e["force"] = None
            e["fg_score"] = 0
            if isinstance(e.get("details"), dict):
                e["details"] = dict(e["details"])
            out[f"seed_{i}"] = e
        return out

    gpu_client = GpuServiceClient()
    gpu_client.start(start_executor=True, in_process_queues=True)

    def _run_one() -> float:
        entries = _make_entries()
        t0 = time.perf_counter()
        process_force_greats(
            entries,
            False,
            True,
            force_cfg,
            calc_song,
            ref_arrays,
            p_color,
            build_details,
            db_loadouts_full_count=0,
            use_gpu=True,
            fg_search_radius=int(radius),
            perf_timing=False,
            gpu_client=gpu_client,
        )
        return time.perf_counter() - t0

    jobs = max(1, int(args.jobs))
    workers = max(1, int(args.workers))
    print(
        "[fg-bundle] "
        f"song={found_name!r} diff={difficulty!r} fp={song_fp!r} "
        f"jobs={jobs} workers={workers} candidate_limit={limit} radius={radius} team_buff={team_buff}"
    )

    t0 = time.perf_counter()
    durs: list[float] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_run_one) for _ in range(jobs)]
        for fut in as_completed(futs):
            try:
                durs.append(float(fut.result() or 0.0))
            except Exception:
                durs.append(0.0)
    wall = time.perf_counter() - t0

    try:
        gpu_client.close()
    except Exception:
        pass

    if durs:
        durs_sorted = sorted(durs)
        p50 = durs_sorted[len(durs_sorted) // 2]
        p95 = durs_sorted[int(0.95 * (len(durs_sorted) - 1))]
        print(
            f"[fg-bundle] wall={wall:.3f}s jobs={len(durs)} jobs/s={len(durs)/max(0.001,wall):.2f} "
            f"p50={p50:.3f}s p95={p95:.3f}s max={max(durs_sorted):.3f}s"
        )

    if not args.no_trace:
        _analyze_trace(str(args.trace))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
