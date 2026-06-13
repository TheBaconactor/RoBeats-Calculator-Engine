"""
Benchmark: FG bundle (real song) wall-time + GPU executor gaps.

Goal: isolate ForceGreatsFinder GPU bundle behavior (no GA) and measure the
time *between* FG GPU jobs when many FG jobs are queued.

This script:
  - Loads a real song .txt chart (calc_song) + ref arrays.
  - Pulls FG seed loadouts from the DB (team_buff_* tables when present).
  - Runs the GPU `run_force_greats_response_frontier_for_ga_candidates(...)` route for N jobs.
  - Optionally runs jobs concurrently to stress the GPU request queue and coalescing.

Examples:
  python tools/bench/bench_fg_bundle_real_song.py --song-fp "Data/Normal/Insight by Haywyre.txt" --jobs 100 --workers 12
"""

from __future__ import annotations

import argparse
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song-fp", default="", help="Chart .txt path (defaults from config.ini if resolvable).")
    ap.add_argument("--jobs", type=int, default=100, help="Number of FG jobs to run.")
    ap.add_argument("--workers", type=int, default=12, help="CPU worker threads (FG jobs in flight).")
    ap.add_argument("--candidate-limit", type=int, default=0, help="Override FG_CandidateLimit (0=use config).")
    ap.add_argument("--team-buff", default="", help="Override TeamBuff tier (e.g., NONE/T1/T5/T10/T20/T50/T51).")
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

    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT, TOTAL_ROWS
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.data.database import get_best_loadouts
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.helpers.song_helpers.force_greats import run_force_greats_response_frontier_for_ga_candidates
    from gear_optimizer.data.song_io import get_base_calc_song

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

    limit_cfg = int(LOADOUTS_PER_SONG_LIMIT)
    limit = int(args.candidate_limit) if int(args.candidate_limit or 0) > 0 else int(limit_cfg)

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
        raise SystemExit(f"No persisted loadouts for {found_name!r}. Run optimizer first or point EVOLUTION_DB_PATH.")

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

    def _make_ga_candidates(entries: dict) -> list[dict]:
        candidates = []
        for key, entry in entries.items():
            eval_data = entry.get("Data") or entry.get("eval_data") or entry.get("details") or {}
            if not isinstance(eval_data, dict) or not eval_data:
                raise ValueError(f"FG benchmark seed {key!r} is missing eval data")
            base_score = int(
                entry.get("BaseScore")
                or entry.get("base_score")
                or entry.get("score")
                or eval_data.get("BaseScore")
                or eval_data.get("Score")
                or 0
            )
            if base_score <= 0:
                raise ValueError(f"FG benchmark seed {key!r} is missing a positive base score")
            candidates.append(
                {
                    "BaseScore": int(base_score),
                    "Gear": list(entry.get("Gear") or entry.get("gear") or []),
                    "Minis": list(entry.get("Minis") or entry.get("minis") or []),
                    "Data": dict(eval_data),
                    "loadout_hash": str(entry.get("loadout_hash") or key),
                }
            )
        return candidates

    def _run_one() -> float:
        entries = _make_entries()
        t0 = time.perf_counter()
        run_force_greats_response_frontier_for_ga_candidates(
            _make_ga_candidates(entries),
            calc_song,
            ref_arrays,
            p_color,
        )
        return time.perf_counter() - t0

    jobs = max(1, int(args.jobs))
    workers = max(1, int(args.workers))
    print(
        "[fg-bundle] "
        f"song={found_name!r} diff={difficulty!r} fp={song_fp!r} "
        f"jobs={jobs} workers={workers} candidate_limit={limit} team_buff={team_buff}"
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

    if durs:
        durs_sorted = sorted(durs)
        p50 = durs_sorted[len(durs_sorted) // 2]
        p95 = durs_sorted[int(0.95 * (len(durs_sorted) - 1))]
        print(
            f"[fg-bundle] wall={wall:.3f}s jobs={len(durs)} jobs/s={len(durs)/max(0.001,wall):.2f} "
            f"p50={p50:.3f}s p95={p95:.3f}s max={max(durs_sorted):.3f}s"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
