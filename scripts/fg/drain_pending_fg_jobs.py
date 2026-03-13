"""
Drain pending ForceGreats jobs saved in `pending_fg_jobs`.

GPU-only: ForceGreats GPU failures now raise directly.
Safe for debugging; uses EVOLUTION_DB_PATH / METAFINDER_CONFIG_PATH if set.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import time
from typing import Dict, List, Tuple

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gear_optimizer.core.config import load_config, read_fg_candidate_limit, read_fg_search_radius, read_iteration_engine_settings
from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.data.database import (
    delete_pending_fg_job,
    get_song_counters,
    list_pending_fg_jobs,
    save_loadouts_batch,
    update_song_counters,
)
from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
from gear_optimizer.helpers.song_helpers import build_loadout_entries, process_force_greats
from gear_optimizer.helpers.song_helpers.database_context import load_database_context
from gear_optimizer.helpers.song_helpers.persistence import build_db_payload, build_persistence_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song, scan_song_header
from gear_optimizer.solver.hit_simulation import apply_human_hit_sim


def _preload_ref_arrays(stats_table: List[List[float]]) -> Dict[str, "numpy.ndarray"]:
    import numpy as np

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays: Dict[str, "numpy.ndarray"] = {}
    for i, name in enumerate(stat_names):
        temp_list: List[float] = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    return ref_arrays


def _build_song_map(data_root: str) -> Dict[str, Tuple[str, str]]:
    """
    Return {song_name: (file_path, difficulty)} by scanning Data/ for .txt song files.
    """
    song_map: Dict[str, Tuple[str, str]] = {}
    if not data_root or not os.path.exists(data_root):
        return song_map

    for root, _, files in os.walk(data_root):
        for f in files:
            if not f.lower().endswith(".txt"):
                continue
            fp = os.path.join(root, f)
            meta = scan_song_header(fp)
            if not meta:
                continue
            name = meta.get("Song Name", "").strip()
            if not name:
                continue
            parent = os.path.basename(root).lower()
            if parent == "hard":
                diff = "Hard"
            elif parent == "normal":
                diff = "Normal"
            elif parent == "easy":
                diff = "Easy"
            else:
                diff = meta.get("Difficulty", "Unknown") or "Unknown"
            song_map.setdefault(name, (fp, diff))
    return song_map


def _best_candidate(ga_candidates: List[dict]) -> dict | None:
    if not ga_candidates:
        return None

    def _score(c: dict) -> int:
        try:
            return int(c.get("BaseScore") or c.get("Score") or 0)
        except Exception:
            return 0

    best = max(ga_candidates, key=_score)
    return best if isinstance(best, dict) else None


def _best_fg_improving(persist_entries: List[dict]) -> int:
    best = 0
    for e in persist_entries or []:
        if not isinstance(e, dict):
            continue
        try:
            score = int(e.get("score", 0) or 0)
        except Exception:
            score = 0
        try:
            fg_score = int(e.get("fg_score", 0) or 0)
        except Exception:
            fg_score = 0
        if fg_score <= score:
            continue
        if not e.get("force"):
            continue
        if fg_score > best:
            best = fg_score
    return int(best)


def _truthy(val: str) -> bool:
    return str(val or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Drain pending FG jobs using GPU-only ForceGreats.")
    parser.add_argument("--limit", type=int, default=0, help="Max pending jobs to process (0 = all)")
    parser.add_argument("--song", type=str, default="", help="Process a single song name")
    parser.add_argument("--dry-run", action="store_true", help="Compute FG but do not save results")
    parser.add_argument("--no-delete", action="store_true", help="Do not delete pending rows")
    parser.add_argument(
        "--log-path",
        type=str,
        default=str(PATHS.bin_path("drain_pending_fg_jobs.log")),
        help="Log file for per-song FG output (default: bin/drain_pending_fg_jobs.log)",
    )
    parser.add_argument("--verbose", action="store_true", help="Do not redirect FG output to log file")
    parser.add_argument("--progress-every", type=int, default=10, help="Print progress every N songs")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first error")
    args = parser.parse_args()

    # Force GPU-only behavior.
    os.environ.setdefault("FG_INPROCESS_EXECUTOR", "1")

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)
    ie = read_iteration_engine_settings(cfg)
    if not ie.force_greats_mode:
        print("[DrainFG] ForceGreatsMode is disabled in config.ini; nothing to do.")
        return 1

    fg_candidate_limit = read_fg_candidate_limit(cfg, default=100, min_limit=51)
    fg_search_radius = read_fg_search_radius(cfg)

    data_root = PATHS.data_dir
    song_map = _build_song_map(data_root)
    if not song_map:
        print(f"[DrainFG] No songs found under {data_root}")
        return 1

    # Match app behavior: prefer discovered Stats.txt path (from paths_cache) and fall back to ./Stats.csv.
    try:
        from gear_optimizer.core.config import load_paths_cache

        paths = load_paths_cache() or {}
    except Exception:
        paths = {}
    stats_fp = str((paths.get("Stats") or PATHS.stats_csv) or "").strip()
    stats_table = read_table(stats_fp)
    ref_arrays = _preload_ref_arrays(stats_table)
    if not ref_arrays:
        print(f"[DrainFG] Failed to build ref_arrays; stats table missing or invalid: {stats_fp}")
        return 1

    gears_by_name = get_gears_by_name_cached()
    minis_by_name = get_minis_by_name_cached()

    pending = list_pending_fg_jobs(limit=args.limit or 0)
    if args.song:
        pending = [p for p in pending if str(p.get("song_name", "")) == args.song]

    if not pending:
        print("[DrainFG] No pending FG jobs found.")
        return 0

    total = len(pending)
    print(f"[DrainFG] Pending jobs: {total} (limit={args.limit or 0})")

    log_fp = str(args.log_path or "").strip()
    if log_fp:
        try:
            os.makedirs(os.path.dirname(log_fp), exist_ok=True)
        except Exception:
            pass

    processed = 0
    started = time.perf_counter()
    for job in pending:
        song_name = str(job.get("song_name", "")).strip()
        if not song_name:
            continue

        fp_diff = song_map.get(song_name)
        if not fp_diff:
            print(f"[DrainFG][WARN] Song not found on disk: {song_name}")
            continue
        fp, diff = fp_diff

        ga_candidates = list(job.get("candidates") or [])
        if not ga_candidates:
            print(f"[DrainFG][WARN] No GA candidates stored for {song_name}")
            continue

        best = _best_candidate(ga_candidates)
        if not best:
            print(f"[DrainFG][WARN] No valid GA candidate for {song_name}")
            continue

        best_data = best.get("Data") or {}
        best_gear = best.get("Gear") or []
        best_minis = best.get("Minis") or []

        base_calc_song = get_base_calc_song(fp, cfg_dict)
        calc_song = clone_calc_song(base_calc_song)
        # Ensure FG timestamps exist if HumanHitSim is enabled.
        apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)

        meta_primary = (calc_song.get("metadata", {}) or {}).get("Primary Color", "")
        meta_secondary = (calc_song.get("metadata", {}) or {}).get("Secondary Color", "")

        build_details_fn = make_build_details_fn(meta_primary, meta_secondary, diff)

        prev_record, _known = load_database_context(song_name, True, gears_by_name, minis_by_name)
        attempt_lifetime = 0
        attempts_first = 0

        # Build union entries (DB + GA candidates) for FG evaluation.
        loadout_entries = build_loadout_entries(
            song_name,
            True,
            ga_candidates,
            fg_candidate_limit,
            gears_by_name,
            minis_by_name,
            build_details_fn,
        )

        try:
            # ForceGreats emits a lot of diagnostic output. For bulk draining, keep stdout readable
            # and write per-song details to a log file unless --verbose is requested.
            if (not args.verbose) and log_fp:
                with open(log_fp, "a", encoding="utf-8", newline="\n") as logf:
                    logf.write(f"\n=== {song_name} ===\n")
                    with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
                        fg_variants = process_force_greats(
                            loadout_entries,
                            ie.manual_force_greats,
                            ie.force_greats_finder,
                            ie.force_greats_config,
                            calc_song,
                            ref_arrays,
                            meta_primary,
                            build_details_fn,
                            use_gpu=True,
                            fg_search_radius=fg_search_radius,
                            perf_timing=_truthy(os.environ.get("PERF_TIMING", "0")),
                        )
            else:
                fg_variants = process_force_greats(
                    loadout_entries,
                    ie.manual_force_greats,
                    ie.force_greats_finder,
                    ie.force_greats_config,
                    calc_song,
                    ref_arrays,
                    meta_primary,
                    build_details_fn,
                    use_gpu=True,
                    fg_search_radius=fg_search_radius,
                    perf_timing=_truthy(os.environ.get("PERF_TIMING", "0")),
                )
        except Exception as exc:
            msg = f"[DrainFG][ERROR] {song_name}: {type(exc).__name__}: {exc}"
            print(msg)
            if log_fp:
                try:
                    with open(log_fp, "a", encoding="utf-8", newline="\n") as logf:
                        logf.write(msg + "\n")
                except Exception:
                    pass
            if args.fail_fast:
                raise
            continue

        _attempt_lifetime, _attempts_first, _best_score, best_fg_prev = get_song_counters(song_name)

        db_payload = build_db_payload(
            best_data,
            best_gear,
            best_minis,
            prev_record,
            attempt_lifetime,
            attempts_first,
            fg_variants,
            build_details_fn,
            db_best_fg_score=best_fg_prev,
        )

        persist_entries = build_persistence_entries(
            db_payload,
            ga_candidates,
            loadout_entries,
            build_details_fn,
        )

        best_fg_improving = _best_fg_improving(persist_entries)
        record_improved = bool(best_fg_improving > int(best_fg_prev or 0))

        if not args.dry_run:
            try:
                save_loadouts_batch(song_name, persist_entries)
                update_song_counters(song_name, processed_run=False, record_improved=record_improved)
                if not args.no_delete:
                    delete_pending_fg_job(song_name)
            except Exception as exc:
                msg = f"[DrainFG][ERROR] Save failed for {song_name}: {type(exc).__name__}: {exc}"
                print(msg)
                if log_fp:
                    try:
                        with open(log_fp, "a", encoding="utf-8", newline="\n") as logf:
                            logf.write(msg + "\n")
                    except Exception:
                        pass
                if args.fail_fast:
                    raise
                continue

        processed += 1

        if int(args.progress_every or 0) > 0 and (processed == 1 or processed % int(args.progress_every) == 0):
            dt = time.perf_counter() - started
            rate = float(processed) / dt if dt > 0 else 0.0
            mode = "DRY" if args.dry_run else "SAVE"
            print(
                f"[DrainFG][{mode}] {processed}/{total} ({rate:.2f} songs/s) "
                f"last={song_name!r} best_fg_improving={best_fg_improving} prev_best_fg={best_fg_prev}"
            )

    print(f"[DrainFG] Done. processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
