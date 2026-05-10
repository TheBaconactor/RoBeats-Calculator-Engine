"""Compare GA and exact skyline through the normal song processor path.

This intentionally does not call solver internals directly. The goal is to
exercise the same DB baseline, known-loadout, config, and payload assembly path
used by the frontend/app runner while still allowing GA and skyline to be
compared side by side.

Usage:
  python tools/verify/verify_exact_skyline_vs_ga.py \
    --song "Data/Hard/00 (Hard) by garlagan.txt" \
    --db evolutionref4.db \
    --ga-depth 25 --ga-seed 123
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _disable_inputs_to_match_app_meta_mode(cfg) -> None:
    if not cfg.has_section("UserInputStatsGems"):
        cfg.add_section("UserInputStatsGems")
    for key in ["perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"]:
        cfg.set("UserInputStatsGems", key, "0")

    if not cfg.has_section("ElementalGems"):
        cfg.add_section("ElementalGems")
    for key in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
        cfg.set("ElementalGems", key, "0")


def _build_ref_arrays(stats_table: list[list[float]]) -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays: dict[str, np.ndarray] = {}
    for i, name in enumerate(stat_names):
        vals: list[float] = []
        for v in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(v)
            try:
                val = float(stats_table[lookup_index][i]) if stats_table else 0.0
            except (IndexError, TypeError, ValueError):
                val = 0.0
            vals.append(val)
        ref_arrays[name] = np.asarray(vals, dtype=np.float32)
    return ref_arrays


def _result_scores(payload: dict[str, Any]) -> tuple[int, int]:
    best_data = payload.get("best_data") if isinstance(payload, dict) else None
    if not isinstance(best_data, dict):
        best_data = {}
    base = int(best_data.get("BaseScore") or best_data.get("Score") or payload.get("best_score") or 0)
    fg = int(
        best_data.get("FGScore")
        or best_data.get("ForceGreatsScore")
        or payload.get("best_fg_score")
        or payload.get("best_force_greats_score")
        or 0
    )
    return base, fg


def _result_loadout(payload: dict[str, Any]) -> tuple[Any, Any]:
    best_data = payload.get("best_data") if isinstance(payload, dict) else None
    if not isinstance(best_data, dict):
        best_data = {}
    gear = best_data.get("GearNames") or best_data.get("Gear") or payload.get("best_gear")
    minis = best_data.get("MiniNames") or best_data.get("Minis") or payload.get("best_minis")
    return gear, minis


def _native_fg_from_candidates(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not isinstance(payload, dict):
        return 0, {}
    best = 0
    would_skip = 0
    candidates = payload.get("ga_candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            try:
                best = max(int(best), int(candidate.get("FGScore", 0) or 0))
            except (TypeError, ValueError):
                pass
            if bool(candidate.get("NativeFGWouldSkipByCeiling", False)):
                would_skip += 1
    best_data = payload.get("best_data")
    summary = {}
    if isinstance(best_data, dict) and isinstance(best_data.get("NativeFG"), dict):
        summary = dict(best_data.get("NativeFG") or {})
    if would_skip and "hypothetical_skipped_by_ceiling" not in summary:
        summary["hypothetical_skipped_by_ceiling"] = int(would_skip)
    return int(best), summary


def _materialize_items(items: Any, lookup: dict[str, dict]) -> list[dict]:
    out: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            out.append(item)
            continue
        name = str(item or "")
        if name and name in lookup:
            out.append(lookup[name])
    return out


def _frontend_replay_scores(
    *,
    payload: dict[str, Any],
    calc_song: dict,
    ref_arrays: dict[str, np.ndarray],
    cfg_dict: dict[str, Any],
    difficulty: str,
    gears_by_name: dict[str, dict],
    minis_by_name: dict[str, dict],
) -> tuple[int, int]:
    if not isinstance(payload, dict):
        return 0, 0
    from gear_optimizer.helpers.song_helpers import build_db_payload
    from gear_optimizer.helpers.song_helpers.persistence import ReplayContext, canonicalize_and_assemble
    from gear_optimizer.helpers.song_helpers.persistence_payload import make_build_details_fn

    best_data = payload.get("best_data")
    if not isinstance(best_data, dict):
        return 0, 0

    gear = best_data.get("Gear") or payload.get("best_gear") or []
    minis = best_data.get("Minis") or payload.get("best_minis") or []
    gear_items = _materialize_items(gear, gears_by_name)
    mini_items = _materialize_items(minis, minis_by_name)
    if not gear_items or not mini_items:
        return 0, 0

    primary = str((calc_song.get("metadata") or {}).get("Primary Color") or "")
    secondary = str((calc_song.get("metadata") or {}).get("Secondary Color") or "")
    build_details = make_build_details_fn(primary, secondary, str(difficulty))
    db_payload = build_db_payload(
        best_data,
        gear_items,
        mini_items,
        None,
        0,
        1,
        [],
        build_details,
        db_best_fg_score=0,
    )
    rows = canonicalize_and_assemble(
        db_payload=db_payload,
        ga_candidates=[],
        loadout_entries=None,
        build_details_fn=build_details,
        replay_ctx=ReplayContext(calc_song=calc_song, ref_arrays=ref_arrays, cfg_dict=cfg_dict),
    )
    if not rows:
        return 0, 0
    best = max(rows, key=lambda row: int(row.get("score") or 0))
    return int(best.get("score") or 0), int(best.get("fg_score") or 0)


def _copy_db_for_read_context(db_path: str | None) -> str | None:
    if not db_path:
        return None
    src = Path(db_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"DB path does not exist: {src}")
    out_dir = Path("artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{src.stem}.verify-copy{src.suffix}"
    shutil.copy2(src, dst)
    return str(dst.resolve())


def _run_engine(
    *,
    engine: str,
    cfg,
    cfg_to_dict,
    song_path: str,
    song_name: str,
    difficulty: str,
    paths: dict[str, Any],
    ref_arrays: dict[str, np.ndarray],
    all_gears: list[dict],
    all_minis: list[dict],
    gears_by_name: dict[str, dict],
    minis_by_name: dict[str, dict],
    ga_depth: int,
    ga_seed: int | None,
    base_calc_song: dict,
) -> dict[str, Any]:
    from gear_optimizer.pipeline.song_processor import clone_calc_song, process_song_task

    run_cfg = cfg_to_dict(cfg)
    run_cfg.setdefault("IterationEngine", {})
    run_cfg["IterationEngine"]["OuterSearchEngine"] = str(engine)
    run_cfg["IterationEngine"]["GPU_Mode"] = "true"
    run_cfg["IterationEngine"]["GPU_Native_GA"] = "true"
    if ga_seed is not None:
        run_cfg["IterationEngine"]["GA_FixedSeed"] = str(int(ga_seed))

    calc_song = clone_calc_song(base_calc_song)
    song_data = calc_song.get("song_data", {}) or {}
    if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
        song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float32)

    try:
        auto_buff = bool(cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False))
    except (AttributeError, TypeError, ValueError):
        auto_buff = False
    if auto_buff:
        run_cfg.setdefault("TeamContributionBuffConstant", {})
        run_cfg["TeamContributionBuffConstant"]["TeamBuff"] = "T5"
        run_cfg["TeamContributionBuffConstant"]["TeamColor"] = str(
            (calc_song.get("metadata") or {}).get("Primary Color") or "Rush"
        )

    task = (
        str(song_path),
        str(song_name),
        str(difficulty),
        run_cfg,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        True,
        auto_buff,
        int(ga_depth),
        None,
        0,
        False,
        calc_song,
        True,
    )

    t0 = time.perf_counter()
    payload = process_song_task(task)
    elapsed = float(time.perf_counter() - t0)
    base, fg = _result_scores(payload)
    raw_fg = int(fg)
    native_fg, native_fg_summary = _native_fg_from_candidates(payload)
    if int(native_fg) > int(fg):
        fg = int(native_fg)
    gear, minis = _result_loadout(payload)
    frontend_base, frontend_fg = _frontend_replay_scores(
        payload=payload,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=run_cfg,
        difficulty=difficulty,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
    )
    return {
        "engine": str(engine),
        "base_score": int(frontend_base or base),
        "fg_score": int(frontend_fg or fg),
        "raw_base_score": int(base),
        "raw_fg_score": int(raw_fg),
        "native_fg": native_fg_summary,
        "elapsed_s": elapsed,
        "gear": gear,
        "minis": minis,
        "payload_error": payload.get("error") if isinstance(payload, dict) else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--song", default="Data/Hard/00 (Hard) by garlagan.txt")
    parser.add_argument("--song-name", default="")
    parser.add_argument("--difficulty", default="Hard")
    parser.add_argument("--db", default="", help="Evolution DB to read as frontend context; copied before use.")
    parser.add_argument("--ga-depth", type=int, default=25)
    parser.add_argument("--ga-seed", type=int, default=123)
    parser.add_argument(
        "--preserve-manual-inputs",
        action="store_true",
        help="Do not mirror app MetaFinder input-zeroing behavior.",
    )
    args = parser.parse_args()

    from gear_optimizer.core.config import load_config, load_paths_cache
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song

    cfg = load_config("config.ini")
    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", "true")
    cfg.set("IterationEngine", "UseEvolutionDB", "true")

    if cfg.getboolean("IterationEngine", "MetaFinder", fallback=False) and not args.preserve_manual_inputs:
        _disable_inputs_to_match_app_meta_mode(cfg)

    db_copy = _copy_db_for_read_context(args.db.strip() or None)
    old_db = os.environ.get("EVOLUTION_DB_PATH")
    if db_copy:
        os.environ["EVOLUTION_DB_PATH"] = db_copy

    try:
        paths = load_paths_cache() or {}
        all_gears = load_all_gears_list(paths)
        all_minis = load_all_minis_list(paths)
        gears_by_name = {str(g.get("Name", "")): g for g in all_gears if g.get("Name")}
        minis_by_name = {str(m.get("Name", "")): m for m in all_minis if m.get("Name")}
        stats_table = read_table(str(paths.get("Stats", "") or ""))
        ref_arrays = _build_ref_arrays(stats_table)

        song_path = str(args.song)
        song_name = str(args.song_name or Path(song_path).stem)
        base_calc_song = clone_calc_song(get_base_calc_song(song_path, cfg_to_dict(cfg)))

        ga = _run_engine(
            engine="ga",
            cfg=cfg,
            cfg_to_dict=cfg_to_dict,
            song_path=song_path,
            song_name=song_name,
            difficulty=args.difficulty,
            paths=paths,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            ga_depth=int(args.ga_depth),
            ga_seed=int(args.ga_seed),
            base_calc_song=base_calc_song,
        )
        skyline = _run_engine(
            engine="exact",
            cfg=cfg,
            cfg_to_dict=cfg_to_dict,
            song_path=song_path,
            song_name=song_name,
            difficulty=args.difficulty,
            paths=paths,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            ga_depth=int(args.ga_depth),
            ga_seed=int(args.ga_seed),
            base_calc_song=base_calc_song,
        )
    finally:
        if old_db is None:
            os.environ.pop("EVOLUTION_DB_PATH", None)
        else:
            os.environ["EVOLUTION_DB_PATH"] = old_db

    out = {
        "song": str(args.song),
        "song_name": str(args.song_name or Path(str(args.song)).stem),
        "difficulty": str(args.difficulty),
        "db_source": str(Path(args.db).resolve()) if args.db else None,
        "db_used": db_copy,
        "ga_depth": int(args.ga_depth),
        "ga_seed": int(args.ga_seed),
        "ga": ga,
        "skyline": skyline,
    }

    Path("artifacts").mkdir(exist_ok=True)
    out_path = Path("artifacts") / "verify_exact_skyline_vs_ga.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")

    if ga.get("payload_error") or skyline.get("payload_error"):
        return 2
    if int(skyline.get("base_score") or 0) < int(ga.get("base_score") or 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
