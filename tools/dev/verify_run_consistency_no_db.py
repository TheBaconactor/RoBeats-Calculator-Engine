"""
Verify optimizer output consistency without touching DB persistence.

What this checks (per processed song):
- `best_data["Score"]` matches a fresh `evaluate_stats_score(best_data["Stats"], calc_song, ref_arrays)`.
- Every generated persistence entry's `score` matches evaluation of its persisted `details["Stats"]`.
- For entries with ForceGreats payload, `fg_score` is consistent with the payload's embedded score.

This is a sanity check for "console output vs optimizer result" and catches cases where the
Stats payload used by frontend/export diverges from the scoring pipeline (e.g., missing TeamBuff).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v if v is not None else default)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return int(default)


def _fg_score_from_force(force: Any) -> int:
    if not isinstance(force, dict) or not force:
        return 0
    # Wrapper score
    s = _safe_int(force.get("score", 0), 0)
    if s <= 0:
        s = _safe_int(force.get("Score", 0), 0)
    if s > 0:
        return s

    # Nested score
    det = force.get("details") if isinstance(force.get("details"), dict) else force
    fg = det.get("ForceGreats") if isinstance(det, dict) else None
    if isinstance(fg, dict):
        s2 = _safe_int(fg.get("final_score", 0), 0)
        if s2 > 0:
            return s2
        return max(_safe_int(fg.get("finalScore", 0), 0), _safe_int(fg.get("score", 0), 0))
    return 0


def _score_from_stats_grid(stats: dict, calc_song: dict, ref_arrays: dict) -> int:
    """
    Score a fixed stats snapshot using the SongTimelineGrid path.

    This mirrors the fast scoring core and is useful to debug divergences between
    different fever timeline implementations.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.fever_timeline import get_song_timeline_grid
    from gear_optimizer.solver.scoring_core import fast_calculate_score, lookup_reference_py

    meta = calc_song.get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color", "") or "")
    s_color = str(meta.get("Secondary Color", "") or "")

    grid = get_song_timeline_grid(calc_song, ref_arrays)
    ft_idx = max(0, min(int(TOTAL_ROWS), int(float(stats.get("Fever Time", 0) or 0))))
    ff_idx = max(0, min(int(TOTAL_ROWS), int(float(stats.get("Fever Fill Rate", 0) or 0))))
    fever_mask_head, count_body_fever, count_body_normal, *_ = grid.get_timeline(ft_idx, ff_idx)

    base_pp = lookup_reference_py(float(stats.get("Perfect Points", 0) or 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(
        float(stats.get("Combo Multiplier", 0) or 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS
    )
    fever_mul = lookup_reference_py(
        float(stats.get("Fever Multiplier", 0) or 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS
    )

    primary_val = float(stats.get(p_color, 0) or 0)
    secondary_val = float(stats.get(s_color, 0) or 0)
    total_base = (primary_val * 2.0) + secondary_val + float(base_pp)

    return int(
        fast_calculate_score(
            float(total_base),
            float(combo_mul),
            float(fever_mul),
            fever_mask_head,
            int(count_body_fever),
            int(count_body_normal),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify run consistency without DB persistence.")
    parser.add_argument("--limit", type=int, default=30, help="Number of songs to process (default: 30).")
    parser.add_argument("--ga-depth", type=int, default=60, help="Override GA_SearchDepth for a faster check.")
    parser.add_argument("--ga-multistart", type=int, default=3, help="Override GA_MultiStart for a faster check.")
    parser.add_argument(
        "--song-filter",
        type=str,
        default="",
        help="Override CalculateSong.Song_Name (default: empty => no filter; matches '30 song queue' intent).",
    )
    parser.add_argument(
        "--score-tolerance",
        type=int,
        default=2,
        help="Allow +/- tolerance when comparing recomputed score to stored score (default: 2).",
    )
    parser.add_argument(
        "--disable-human-hitsim",
        action="store_true",
        help="Disable HumanHitSim (recommended for deterministic verification).",
    )
    parser.add_argument(
        "--respect-user-gems",
        action="store_true",
        help="Do NOT apply Auto-Mode gem-taint prevention (main.py normally zeros [UserInputStatsGems]/[ElementalGems]).",
    )
    parser.add_argument("--debug", action="store_true", help="Print extra debugging for mismatches.")
    args = parser.parse_args()

    # Deterministic + no resume artifacts.
    os.environ.setdefault("METAFINDER_IGNORE_RESUME_QUEUE", "1")
    os.environ["SONG_QUEUE_LIMIT"] = str(max(1, int(args.limit)))
    os.environ["SONG_REPEATS"] = "1"

    from gear_optimizer.app import GearOptimizerApp
    from gear_optimizer.core.config import load_config, load_paths_cache, read_iteration_engine_settings
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.core.constants import PATHS
    from gear_optimizer.pipeline.song_processor import _build_base_calc_song_from_file, safe_process_song_task
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score

    app = GearOptimizerApp()
    cfg = load_config()

    # In-memory overrides (no disk changes).
    if args.song_filter is not None:
        if not cfg.has_section("CalculateSong"):
            cfg.add_section("CalculateSong")
        cfg.set("CalculateSong", "Song_Name", str(args.song_filter or ""))

    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "UseEvolutionDB", "false")
    cfg.set("IterationEngine", "GA_SearchDepth", str(max(1, int(args.ga_depth))))
    cfg.set("IterationEngine", "GA_MultiStart", str(max(1, int(args.ga_multistart))))

    if args.disable_human_hitsim:
        if not cfg.has_section("HumanHitSim"):
            cfg.add_section("HumanHitSim")
        cfg.set("HumanHitSim", "Enabled", "false")

    paths = load_paths_cache()
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    ref_arrays = app._preload_ref_arrays(stats_table)

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    ie = read_iteration_engine_settings(cfg)
    # Match main.py behavior: in Auto-Mode (MetaFinder), ignore user gems so DB/meta isn't user-specific.
    if bool(getattr(ie, "meta_finder", False)) and not args.respect_user_gems:
        try:
            app._disable_inputs_to_prevent_taint(cfg)
        except Exception:
            pass

    auto_buff = bool(ie.auto_select_buff_and_color)
    fg_debug = bool(ie.force_greats_debug)
    ga_depth = max(1, int(cfg.get("IterationEngine", "GA_SearchDepth", fallback="60") or 60))

    song_queue = app._build_song_queue(cfg, paths, use_evo_db=False)
    tasks = app._prepare_tasks(
        song_queue,
        cfg,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        False,  # use_evo_db
        auto_buff,
        ga_depth,
        None,  # status_queue
        fg_debug,
    )

    total_songs = 0
    total_entries = 0
    mismatches: list[dict[str, Any]] = []

    for task in tasks:
        # task tuple format: see GearOptimizerApp._prepare_tasks
        fp, song_name = task[0], task[1]
        total_songs += 1
        print("\n" + "=" * 72)
        print(f"[VERIFY] SONG {total_songs}/{len(tasks)}: {song_name}")
        print("=" * 72)

        res = safe_process_song_task(task)

        calc_song = _build_base_calc_song_from_file(fp)
        best_data = res.get("best_data") or {}
        best_stats = best_data.get("Stats") if isinstance(best_data, dict) else None
        best_score = _safe_int(best_data.get("Score", best_data.get("BaseScore", 0)), 0) if isinstance(best_data, dict) else 0

        if isinstance(best_stats, dict) and best_stats:
            try:
                recomputed = int(evaluate_stats_score(best_stats, calc_song, ref_arrays))
            except Exception as e:
                mismatches.append(
                    {"song": song_name, "kind": "best_eval_error", "error": f"{type(e).__name__}: {e}"}
                )
                recomputed = None

            tol = max(0, int(args.score_tolerance))
            if recomputed is None or abs(int(recomputed) - int(best_score)) > tol:
                mismatches.append(
                    {
                        "song": song_name,
                        "kind": "best_score_mismatch",
                        "best_score": best_score,
                        "recomputed": recomputed,
                    }
                )
                print(f"[VERIFY][FAIL] best Score mismatch: best={best_score} recomputed={recomputed}")
                if args.debug and isinstance(best_stats, dict):
                    try:
                        p = str(calc_song.get("metadata", {}).get("Primary Color", "") or "")
                        s = str(calc_song.get("metadata", {}).get("Secondary Color", "") or "")
                        print(f"[VERIFY][DEBUG] colors: primary={p!r} secondary={s!r}")
                        for k in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate", p, s):
                            if k and k in best_stats:
                                print(f"[VERIFY][DEBUG] Stats[{k!r}]={best_stats.get(k)!r}")
                        try:
                            grid_score = _score_from_stats_grid(best_stats, calc_song, ref_arrays)
                            print(f"[VERIFY][DEBUG] score_from_grid={grid_score}")
                        except Exception as e:
                            print(f"[VERIFY][DEBUG] grid_score_error={type(e).__name__}: {e}")
                    except Exception:
                        pass
            else:
                print(f"[VERIFY][OK] best Score matches Stats: {best_score}")
        else:
            mismatches.append({"song": song_name, "kind": "best_stats_missing"})
            print("[VERIFY][FAIL] best Stats missing/empty")

        # Verify every persistence entry (what would be saved).
        persist_entries = res.get("persist_entries") or []
        if not isinstance(persist_entries, list):
            persist_entries = []

        checked = 0
        bad = 0
        for ent in persist_entries:
            if not isinstance(ent, dict):
                continue
            details = ent.get("details") if isinstance(ent.get("details"), dict) else {}
            stats = details.get("Stats") if isinstance(details, dict) else None
            score = _safe_int(ent.get("score", 0), 0)
            fg_score = _safe_int(ent.get("fg_score", 0), 0)
            force = ent.get("force")

            if not isinstance(stats, dict) or not stats:
                bad += 1
                mismatches.append({"song": song_name, "kind": "entry_stats_missing", "score": score})
                continue

            try:
                s2 = int(evaluate_stats_score(stats, calc_song, ref_arrays))
            except Exception as e:
                bad += 1
                mismatches.append(
                    {"song": song_name, "kind": "entry_eval_error", "score": score, "error": f"{type(e).__name__}: {e}"}
                )
                continue

            checked += 1
            tol = max(0, int(args.score_tolerance))
            if abs(int(s2) - int(score)) > tol:
                bad += 1
                mismatches.append(
                    {
                        "song": song_name,
                        "kind": "entry_score_mismatch",
                        "score": score,
                        "recomputed": s2,
                    }
                )

            if force is not None and fg_score > 0:
                fg_from_force = _fg_score_from_force(force)
                if fg_from_force and fg_from_force != fg_score:
                    bad += 1
                    mismatches.append(
                        {
                            "song": song_name,
                            "kind": "entry_fg_score_mismatch",
                            "fg_score": fg_score,
                            "fg_from_force": fg_from_force,
                        }
                    )

        total_entries += len(persist_entries)
        if checked:
            print(f"[VERIFY] persistence entries checked={checked} bad={bad} (total_emitted={len(persist_entries)})")
        else:
            print(f"[VERIFY] no persistence entries to validate (emitted={len(persist_entries)})")

    out_path = PROJECT_ROOT / "artifacts" / "verify_run_consistency_no_db.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"songs": total_songs, "entries": total_entries, "mismatches": mismatches}, indent=2))

    print("\n" + "=" * 72)
    print("[VERIFY] COMPLETE")
    print("=" * 72)
    print(f"songs: {total_songs}")
    print(f"entries_emitted: {total_entries}")
    print(f"mismatches: {len(mismatches)}")
    print(f"report: {out_path}")

    return 0 if not mismatches else 2


if __name__ == "__main__":
    raise SystemExit(main())
