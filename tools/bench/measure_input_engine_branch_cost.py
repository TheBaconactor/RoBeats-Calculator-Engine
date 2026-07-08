"""Measure FG response-frontier prebuild and one direct native optimization.

This is intentionally a thin harness around production owners:
`build_fg_response_frontier_cache_for_path` for the all-FT/FF response frontier,
then `NativeOptimizationEngine` for a single-song solve into an isolated DB.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import shutil
import sys
import time
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--bench-root", default=r"C:\mfbench\input-engine-aware-ab")
    parser.add_argument(
        "--song-path",
        default=r"Data\Hard\All Right There (Hard) by BSlick feat CG5.txt",
    )
    parser.add_argument("--song-name", default="All Right There")
    parser.add_argument("--difficulty", default="Hard")
    return parser.parse_args()


def _start_post_processor(total_tasks: int):
    from gear_optimizer.pipeline.post_processor import run_post_processor

    post_queue: multiprocessing.Queue = multiprocessing.Queue()
    post_proc = multiprocessing.Process(
        target=run_post_processor,
        args=(post_queue, int(total_tasks)),
        daemon=True,
        name="InputEngineCostPostProcessor",
    )
    post_proc.start()
    return post_queue, post_proc


def _stop_post_processor(post_queue, post_proc) -> None:
    try:
        post_queue.put(None, block=True, timeout=5.0)
    except Exception:
        pass
    try:
        post_proc.join(timeout=120.0)
    except Exception:
        pass
    try:
        if post_proc.is_alive():
            post_proc.terminate()
            post_proc.join(timeout=5.0)
    except Exception:
        pass


def _load_run_scores(db_path: Path, song_name: str) -> tuple[int, int]:
    import sqlite3

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        base_row = conn.execute(
            """
            SELECT MAX(score)
            FROM team_buff_loadouts
            WHERE song_name = ? AND team_buff = 'T5'
            """,
            (str(song_name),),
        ).fetchone()
        fg_row = conn.execute(
            """
            SELECT MAX(fg_score)
            FROM team_buff_fg_loadouts
            WHERE song_name = ? AND team_buff = 'T5'
            """,
            (str(song_name),),
        ).fetchone()
    finally:
        conn.close()
    base_score = int(base_row[0] or 0) if base_row is not None and base_row[0] is not None else 0
    fg_score = int(fg_row[0] or 0) if fg_row is not None and fg_row[0] is not None else 0
    return base_score, fg_score


def _run_native_inflight_song(
    *,
    fp: str,
    song_name: str,
    difficulty: str,
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    ga_depth: int,
    run_db_path: Path,
) -> tuple[int, int]:
    from gear_optimizer.data.database import init_db
    from gear_optimizer.domain.jobs import SharedRunContext, SongJob, task_tuple_from_job_context
    from gear_optimizer.engine.native import NativeOptimizationEngine, NativeOptimizationRequest

    context = SharedRunContext(
        cfg_dict=cfg_dict,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        ga_depth=int(ga_depth),
        parallel_workers=1,
        fg_debug=False,
    )
    job = SongJob(
        file_path=fp,
        song_name=str(song_name),
        difficulty=str(difficulty),
        repeat_index=1,
        repeat_total=1,
        ga_seed=int(os.environ.get("GA_SEED", "1337") or 1337),
        queue_source="measure_input_engine_branch_cost",
    )
    task = task_tuple_from_job_context(
        job,
        context,
        {"repeat_index": 1, "repeat_total": 1, "ga_seed": int(os.environ.get("GA_SEED", "1337") or 1337)},
    )

    old_db_path = os.environ.get("EVOLUTION_DB_PATH")
    os.environ["EVOLUTION_DB_PATH"] = str(run_db_path)
    try:
        init_db()
        post_queue, post_proc = _start_post_processor(total_tasks=1)
        try:
            NativeOptimizationEngine().run(
                NativeOptimizationRequest(
                    tasks=[task],
                    in_flight_songs=1,
                    completed_songs=set(),
                    memory_resume_tracker=None,
                    post_queue=post_queue,
                    stop_requested=None,
                    progress_cb=None,
                    bundle_completed_cb=None,
                )
            )
        finally:
            _stop_post_processor(post_queue, post_proc)
        return _load_run_scores(run_db_path, song_name)
    finally:
        if old_db_path is None:
            os.environ.pop("EVOLUTION_DB_PATH", None)
        else:
            os.environ["EVOLUTION_DB_PATH"] = old_db_path


def main() -> int:
    multiprocessing.freeze_support()
    args = _parse_args()
    label = str(args.label)
    repo_root = Path(args.repo_root).resolve()
    bench_root = Path(args.bench_root).resolve()
    run_root = bench_root / label
    run_root.mkdir(parents=True, exist_ok=True)

    os.environ["ROBEATSMETA_OPTIMIZER_BIN_DIR"] = str(run_root / "bin")
    os.environ.setdefault("GA_SEED", "1337")
    os.environ.setdefault("PYTHONHASHSEED", "0")
    sys.path.insert(0, str(repo_root))

    from gear_optimizer.core.config import load_config, load_paths_cache
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import (
        load_all_gears_list,
        load_all_minis_list,
        load_csv_db,
        read_table,
        resolve_stats_csv,
    )
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.timeline_frontier_cache_prebuild import build_timeline_frontier_cache_for_path
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import build_fg_response_frontier_cache_for_path
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys

    raw_song_path = Path(args.song_path)
    song_path = raw_song_path if raw_song_path.is_absolute() else repo_root / raw_song_path
    if not song_path.exists():
        raise FileNotFoundError(song_path)

    ref_arrays = build_ref_arrays_from_stats(read_table(str(repo_root / "Data" / "Gear" / "Stats.txt")), dtype=float)
    stat_keys = all_response_stat_keys()
    calc_song = get_base_calc_song(str(song_path), {})
    meta = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}

    warm_dir = run_root / "fg-cache-warm"
    measured_dir = run_root / "fg-cache-measured"
    timeline_dir = run_root / "timeline-cache"
    for path in (warm_dir, measured_dir, timeline_dir):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(warm_dir)
    start = time.perf_counter()
    warm_result = build_fg_response_frontier_cache_for_path(str(song_path), ref_arrays, stat_keys=stat_keys)
    warm_wall_s = time.perf_counter() - start

    os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(measured_dir)
    start = time.perf_counter()
    prebuild_result = build_fg_response_frontier_cache_for_path(str(song_path), ref_arrays, stat_keys=stat_keys)
    prebuild_wall_s = time.perf_counter() - start

    os.environ["TIMELINE_FRONTIER_CACHE_DIR"] = str(timeline_dir)
    start = time.perf_counter()
    timeline_result = build_timeline_frontier_cache_for_path(str(song_path), ref_arrays)
    timeline_wall_s = time.perf_counter() - start

    cfg = load_config(str(repo_root / "config.ini"))
    cfg_dict = cfg_to_dict(cfg)
    try:
        ga_depth = int(cfg.get("IterationEngine", "GA_SearchDepth", fallback="50") or 50)
    except Exception:
        ga_depth = 50
    paths = load_paths_cache()
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = load_csv_db(resolve_stats_csv(paths, "Gears.csv"), "gear")
    minis_by_name = load_csv_db(resolve_stats_csv(paths, "Minis.csv"), "mini")
    run_db_path = run_root / "direct_optimization.db"
    if run_db_path.exists():
        run_db_path.unlink()

    start = time.perf_counter()
    base_score, fg_score = _run_native_inflight_song(
        fp=str(song_path),
        song_name=str(args.song_name),
        difficulty=str(args.difficulty),
        cfg_dict=cfg_dict,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        ga_depth=ga_depth,
        run_db_path=run_db_path,
    )
    direct_wall_s = time.perf_counter() - start

    out = {
        "label": label,
        "repo": str(repo_root),
        "git_rev": os.popen("git rev-parse HEAD").read().strip(),
        "git_branch": os.popen("git branch --show-current").read().strip(),
        "song_path": str(song_path),
        "metadata_song_name": str(meta.get("Song Name") or ""),
        "song_name": str(args.song_name),
        "difficulty": str(args.difficulty),
        "notes": int(meta.get("Total Notes") or 0),
        "stat_keys": len(stat_keys),
        "ga_depth": int(ga_depth),
        "warm_frontier_wall_s": float(warm_wall_s),
        "warm_frontier_source": str(warm_result.source),
        "warm_frontier_build_ms": float(warm_result.build_ms),
        "prebuild_frontier_wall_s": float(prebuild_wall_s),
        "prebuild_frontier_source": str(prebuild_result.source),
        "prebuild_frontier_build_ms": float(prebuild_result.build_ms),
        "prebuild_cache_file": str(prebuild_result.cache_file),
        "timeline_frontier_wall_s": float(timeline_wall_s),
        "timeline_frontier_source": str(timeline_result.source),
        "timeline_frontier_build_ms": float(timeline_result.build_ms),
        "timeline_cache_file": str(timeline_result.cache_file),
        "direct_optimization_wall_s": float(direct_wall_s),
        "direct_base_score": int(base_score),
        "direct_fg_score": int(fg_score),
    }
    print("BENCH_RESULT_JSON=" + json.dumps(out, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
