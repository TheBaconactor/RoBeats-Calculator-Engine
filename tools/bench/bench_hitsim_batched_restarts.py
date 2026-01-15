import argparse
import configparser
import copy
import json
import os
import secrets
import sys
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import gc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _truthy(v: object) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def _rm_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _rm_sqlite_triple(db_path: Path) -> None:
    _rm_if_exists(db_path)
    _rm_if_exists(db_path.with_suffix(db_path.suffix + "-wal"))
    _rm_if_exists(db_path.with_suffix(db_path.suffix + "-shm"))


def _load_cfg_dict(config_path: Path) -> dict:
    from gear_optimizer.core.utils import cfg_to_dict

    cfg = configparser.ConfigParser()
    cfg.read(str(config_path), encoding="utf-8-sig")
    return cfg_to_dict(cfg)


def _force_autozero_manual_inputs(cfg_dict: dict) -> None:
    cfg_dict.setdefault("UserInputStatsGems", {})
    cfg_dict.setdefault("ElementalGems", {})
    for k in ("perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"):
        cfg_dict["UserInputStatsGems"][k] = "0"
    for k in ("Chill", "Flow", "Rush", "Beat", "Vibe"):
        cfg_dict["ElementalGems"][k] = "0"


def _get_song_keys(song: str, artist: str) -> dict[str, str]:
    return {
        "Easy": f"{song} (Easy) by {artist}",
        "Normal": f"{song} by {artist}",
        "Hard": f"{song} (Hard) by {artist}",
    }


def _resolve_song_file(paths: dict, difficulty: str, song_key: str) -> str:
    # Default layout: Data/<Difficulty>/<SongKey>.txt
    data_dir = Path(paths.get("Data", "Data") or "Data")
    diff_dir = data_dir / difficulty
    fp = diff_dir / f"{song_key}.txt"
    if fp.exists():
        return str(fp)
    # Fallback: scan difficulty folder for exact basename match
    try:
        for cand in diff_dir.glob("*.txt"):
            if cand.stem == song_key:
                return str(cand)
    except Exception:
        pass
    raise FileNotFoundError(f"Song file not found for {difficulty}: {song_key}")


def _load_runtime_inputs():
    import numpy as np

    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.solver.scoring_core import lookup_reference_py

    paths = load_paths_cache()

    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays: dict[str, object] = {}
    for i, name in enumerate(stat_names):
        temp_list: list[float] = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    return paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name


def _run_one_task(
    *,
    fp: str,
    song_key: str,
    difficulty: str,
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    use_evo_db: bool,
    ga_depth: int,
    ga_seed: int,
) -> dict:
    from gear_optimizer.pipeline.song_processor import process_song_task

    repeat_ctx = {"repeat_index": 1, "repeat_total": 1, "ga_seed": int(ga_seed)}
    args = (
        fp,
        song_key,
        difficulty,
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        bool(use_evo_db),
        True,  # auto_buff
        int(ga_depth),
        None,  # status_queue
        1,  # parallel_workers
        False,  # fg_debug
        repeat_ctx,
    )

    # Silence the giant per-run print spam; we measure via returned payload.
    with redirect_stdout(StringIO()):
        return process_song_task(args)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--song", default="Aether")
    parser.add_argument("--artist", default="Geoxor")
    parser.add_argument("--config", default="config.ini", help="Config ini path (read; overridden per-mode/per-run).")
    parser.add_argument("--iters", type=int, default=150, help="Number of 'macro runs' per difficulty per mode.")
    parser.add_argument("--restarts", type=int, default=4, help="GA restarts per macro run (same HitSim seed).")
    parser.add_argument(
        "--difficulties",
        default="Easy,Normal,Hard",
        help="Comma-separated list from {Easy,Normal,Hard}. Example: Hard",
    )
    parser.add_argument("--out", default=str(Path("artifacts") / "bench" / "hitsim_batched_restarts.json"))
    parser.add_argument("--base-ga-seed", type=int, default=7070000, help="GA seed base (kept consistent across modes).")
    parser.add_argument("--checkpoint-every", type=int, default=10, help="Write partial results every N macro runs.")
    parser.add_argument(
        "--fixed-hitsim-seed",
        type=int,
        default=0,
        help="0 = random HitSim seed per macro run; non-zero forces a fixed seed (debug).",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 2

    iters = max(1, int(args.iters))
    restarts = max(1, int(args.restarts))
    base_ga_seed = int(args.base_ga_seed)
    difficulties = [d.strip() for d in str(args.difficulties or "").split(",") if d.strip()]
    allowed = {"Easy", "Normal", "Hard"}
    difficulties = [d for d in difficulties if d in allowed]
    if not difficulties:
        raise SystemExit(f"--difficulties must include one of {sorted(allowed)}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Load runtime inputs once.
    paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name = _load_runtime_inputs()

    base_cfg_dict = _load_cfg_dict(config_path)
    _force_autozero_manual_inputs(base_cfg_dict)

    _ = _truthy((base_cfg_dict.get("IterationEngine") or {}).get("useevolutiondb", "true"))
    ga_depth_default = _safe_int((base_cfg_dict.get("IterationEngine") or {}).get("ga_searchdepth", 0), 0) or 0

    if not _truthy((base_cfg_dict.get("HumanHitSim") or {}).get("enabled", "false")):
        print("[WARN] HumanHitSim.Enabled is false in config; this benchmark targets HitSim reuse across restarts.")

    # Pre-generate HitSim seeds so all modes see the same timelines (still random).
    if int(args.fixed_hitsim_seed) > 0:
        hitsim_seeds = [int(args.fixed_hitsim_seed)] * iters
    else:
        hitsim_seeds = [secrets.randbits(32) for _ in range(iters)]

    modes = [
        {"mode": "db_on_seed_on", "use_db": True, "seed_prob": None, "fresh_each": False},
        {"mode": "db_on_seed_off", "use_db": True, "seed_prob": 0.0, "fresh_each": False},
        {"mode": "db_off", "use_db": False, "seed_prob": None, "fresh_each": False},
        {"mode": "db_on_fresh_each", "use_db": True, "seed_prob": None, "fresh_each": True},
    ]

    song_keys = _get_song_keys(str(args.song), str(args.artist))
    per_mode_results: list[dict] = []
    errors: list[dict] = []

    def _checkpoint(*, in_progress: bool) -> None:
        payload = {
            "song": str(args.song),
            "artist": str(args.artist),
            "config": str(config_path),
            "iters": iters,
            "restarts": restarts,
            "base_ga_seed": base_ga_seed,
            "hitsim_seed_mode": "fixed" if int(args.fixed_hitsim_seed) > 0 else "random",
            "hitsim_seed_fixed": int(args.fixed_hitsim_seed) if int(args.fixed_hitsim_seed) > 0 else None,
            "modes": per_mode_results,
            "errors": errors,
            "_in_progress": bool(in_progress),
        }
        try:
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    for mode in modes:
        mode_name = str(mode["mode"])
        use_db = bool(mode["use_db"])
        seed_prob = mode["seed_prob"]
        fresh_each = bool(mode["fresh_each"])

        db_path = None
        if use_db:
            db_path = Path("artifacts") / "bench" / f"bench_hitsim_batched_{mode_name}.db"
            os.environ["EVOLUTION_DB_PATH"] = str(db_path)
            if fresh_each:
                _rm_sqlite_triple(db_path)
        else:
            os.environ.pop("EVOLUTION_DB_PATH", None)

        # Bound memory growth: timeline grids are keyed by (song, timestamps signature, HitSim params).
        # For this benchmark we do not need to reuse grids across modes.
        try:
            from gear_optimizer.solver import fever_timeline

            fever_timeline.SONG_TIMELINE_GRIDS.clear()
        except Exception:
            pass
        gc.collect()

        mode_t0 = time.perf_counter()
        totals = {"macro_runs": 0, "micro_runs": 0}

        results_by_diff: dict[str, dict] = {}
        for difficulty in difficulties:
            song_key = song_keys[difficulty]
            fp = _resolve_song_file(paths, difficulty, song_key)

            best_base_overall = 0
            best_fg_overall = 0
            base_scores: list[int] = []
            fg_scores: list[int] = []
            stage_wall_sum = 0.0

            for i in range(iters):
                hitsim_seed = int(hitsim_seeds[i])
                macro_best_base = 0
                macro_best_fg = 0
                macro_wall = 0.0

                if use_db and fresh_each and db_path is not None:
                    _rm_sqlite_triple(db_path)

                for r in range(restarts):
                    ga_seed = base_ga_seed + (i * restarts) + r

                    cfg_dict = copy.deepcopy(base_cfg_dict)
                    if seed_prob is not None:
                        cfg_dict.setdefault("IterationEngine", {})
                        cfg_dict["IterationEngine"]["ga_dbseedprobability"] = str(float(seed_prob))

                    cfg_dict.setdefault("HumanHitSim", {})
                    cfg_dict["HumanHitSim"]["seed"] = str(int(hitsim_seed))

                    try:
                        res = _run_one_task(
                            fp=fp,
                            song_key=song_key,
                            difficulty=difficulty,
                            cfg_dict=cfg_dict,
                            paths=paths,
                            ref_arrays=ref_arrays,
                            all_gears=all_gears,
                            all_minis=all_minis,
                            gears_by_name=gears_by_name,
                            minis_by_name=minis_by_name,
                            use_evo_db=use_db,
                            ga_depth=ga_depth_default,
                            ga_seed=ga_seed,
                        )
                    except Exception as e:
                        errors.append(
                            {
                                "mode": mode_name,
                                "difficulty": difficulty,
                                "macro_i": int(i),
                                "restart_i": int(r),
                                "ga_seed": int(ga_seed),
                                "hitsim_seed": int(hitsim_seed),
                                "error": repr(e),
                            }
                        )
                        _checkpoint(in_progress=True)
                        raise
                    totals["micro_runs"] += 1

                    db_payload = res.get("db_payload") or {}
                    base_score = int(db_payload.get("score", 0) or 0)
                    fg_score = int(db_payload.get("fg_score", 0) or 0)
                    macro_best_base = max(macro_best_base, base_score)
                    macro_best_fg = max(macro_best_fg, fg_score)

                    st = res.get("_stage_timing") or {}
                    macro_wall += float(st.get("song_wall_sec", 0.0) or 0.0)

                totals["macro_runs"] += 1
                base_scores.append(int(macro_best_base))
                fg_scores.append(int(macro_best_fg))
                best_base_overall = max(best_base_overall, int(macro_best_base))
                best_fg_overall = max(best_fg_overall, int(macro_best_fg))
                stage_wall_sum += float(macro_wall)

                if int(args.checkpoint_every) > 0 and ((i + 1) % int(args.checkpoint_every) == 0):
                    # Keep a lightweight progress snapshot so long runs still produce usable output.
                    results_by_diff[difficulty] = {
                        "song": song_key,
                        "macro_iters": iters,
                        "restarts_per_macro": restarts,
                        "base_max": int(best_base_overall),
                        "fg_max": int(best_fg_overall),
                        "base_hits": None,
                        "fg_hits": None,
                        "macro_wall_sum_s": float(stage_wall_sum),
                        "_progress": {"done": int(i + 1), "total": int(iters)},
                    }
                    # Update last mode entry in place (or create a placeholder).
                    if per_mode_results and per_mode_results[-1].get("mode") == mode_name:
                        per_mode_results[-1]["results"] = dict(results_by_diff)
                        per_mode_results[-1]["totals"] = dict(totals)
                    else:
                        per_mode_results.append(
                            {
                                "mode": mode_name,
                                "use_db": use_db,
                                "seed_prob": seed_prob,
                                "fresh_each": fresh_each,
                                "db_path": str(db_path) if db_path is not None else None,
                                "iters": iters,
                                "restarts": restarts,
                                "results": dict(results_by_diff),
                                "totals": dict(totals),
                                "_partial": True,
                            }
                        )
                    _checkpoint(in_progress=True)

            # Count hits to the observed max (for this difficulty, within this mode).
            base_hits = sum(1 for s in base_scores if s == best_base_overall)
            fg_hits = sum(1 for s in fg_scores if s == best_fg_overall)

            results_by_diff[difficulty] = {
                "song": song_key,
                "macro_iters": iters,
                "restarts_per_macro": restarts,
                "base_max": int(best_base_overall),
                "fg_max": int(best_fg_overall),
                "base_hits": int(base_hits),
                "fg_hits": int(fg_hits),
                "macro_wall_sum_s": float(stage_wall_sum),
            }

        mode_wall = time.perf_counter() - mode_t0
        # "songs/hour" here is macro runs per hour (each macro run does N restarts).
        macro_tasks = iters * len(difficulties)
        micro_tasks = iters * len(difficulties) * restarts
        per_mode_results.append(
            {
                "mode": mode_name,
                "use_db": use_db,
                "seed_prob": seed_prob,
                "fresh_each": fresh_each,
                "db_path": str(db_path) if db_path is not None else None,
                "iters": iters,
                "restarts": restarts,
                "difficulties": list(difficulties),
                "results": results_by_diff,
                "totals": totals,
                "total_wall_s": float(mode_wall),
                "throughput": {
                    "macro_tasks": int(macro_tasks),
                    "micro_tasks": int(micro_tasks),
                    "macro_tasks_per_hour": float(macro_tasks) / (mode_wall / 3600.0) if mode_wall > 0 else 0.0,
                    "micro_tasks_per_hour": float(micro_tasks) / (mode_wall / 3600.0) if mode_wall > 0 else 0.0,
                },
            }
        )
        _checkpoint(in_progress=True)

    _checkpoint(in_progress=False)
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
