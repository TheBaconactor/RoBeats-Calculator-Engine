"""
Compare exact FG DP against the current GPU finder on representative real songs.

This uses the same GA-produced candidate funnel for both FG paths and records:
  - best FG score
  - improved-variant count
  - focused FG runtime

Exit code is non-zero if exact FG DP returns a lower best FG score than the
current finder on any sampled song.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.core.config import (
    load_config,
    load_paths_cache,
    read_fg_candidate_limit,
    read_fg_search_radius,
)
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT, TOTAL_ROWS
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.helpers.song_helpers import setup_song_config
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
from gear_optimizer.solver.fg_exact_dp_pipeline import process_fg_exact_dp
from gear_optimizer.solver.genetic import solve_coevolution_genetic
from gear_optimizer.solver.gpu_executor import GpuExecutor, get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.solver_common import prepare_solver_context


DEFAULT_SONG_MATCHERS: tuple[tuple[str, str], ...] = (
    ("Easy", "Red  Room"),
    ("Normal", "#include signal.h"),
    ("Hard", "You & I"),
)


@dataclass
class FGSongResult:
    difficulty: str
    song_path: str
    candidate_count: int
    finder_runtime_s: float
    exact_dp_runtime_s: float
    finder_best_fg_score: int
    exact_dp_best_fg_score: int
    finder_improved_count: int
    exact_dp_improved_count: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate exact FG DP against the current finder on real songs.")
    parser.add_argument("--seed", type=int, default=20260408, help="Deterministic GA seed.")
    parser.add_argument("--output", type=str, default="", help="Optional JSON output path.")
    parser.add_argument(
        "--songs",
        nargs="*",
        default=[],
        help="Optional explicit song paths. When omitted, uses built-in Easy/Normal/Hard representatives.",
    )
    return parser.parse_args()


def _build_ref_arrays(paths: dict[str, Any]) -> dict[str, np.ndarray]:
    stats_path = str((paths.get("Stats", "") or "").strip())
    stats_table = read_table(stats_path)
    if not stats_table:
        raise RuntimeError(f"Stats table missing or empty: {stats_path}")

    names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays: dict[str, np.ndarray] = {}
    for col_idx, name in enumerate(names):
        values: list[float] = []
        for stat_idx in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(stat_idx)
            try:
                value = float(stats_table[lookup_index][col_idx])
            except Exception:
                value = 0.0
            values.append(value)
        ref_arrays[name] = np.asarray(values, dtype=np.float32)
    return ref_arrays


def _force_gpu(cfg: Any) -> None:
    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", "true")


def _resolve_default_song_paths(paths: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for difficulty, needle in DEFAULT_SONG_MATCHERS:
        diff_dir = Path(str(paths.get(difficulty, "") or ""))
        if not diff_dir.exists():
            raise FileNotFoundError(f"Difficulty directory not found: {difficulty}")
        matches = sorted(fp for fp in diff_dir.glob("*.txt") if needle.lower() in fp.name.lower())
        if not matches:
            raise FileNotFoundError(f"No song matching '{needle}' in {difficulty}")
        out.append(str(matches[0]))
    return out


def _best_fg_score(base_data: dict[str, Any] | None, fg_variants: list[dict[str, Any]]) -> int:
    base_score = int((base_data or {}).get("BaseScore") or (base_data or {}).get("Score") or 0)
    best = base_score
    for row in fg_variants or []:
        try:
            fg_score = int(row.get("fg_score", row.get("score", 0)) or 0)
        except Exception:
            fg_score = 0
        if fg_score > best:
            best = fg_score
    return int(best)


def _build_outer_candidates(
    *,
    best_data: dict[str, Any] | None,
    best_gear: list[dict],
    best_minis: list[dict],
    all_evaluated: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out = list(all_evaluated or [])
    if best_data and best_gear and best_minis:
        base_score = best_data.get("BaseScore")
        if base_score is None:
            base_score = best_data.get("Score", 0)
        out.append(
            {
                "Score": int(base_score or 0),
                "BaseScore": int(base_score or 0),
                "Gear": list(best_gear or []),
                "Minis": list(best_minis or []),
                "Data": dict(best_data),
            }
        )
    return out


def _run_song(
    *,
    cfg: Any,
    song_path: str,
    ref_arrays: dict[str, np.ndarray],
    paths: dict[str, Any],
    all_gears: list[dict],
    all_minis: list[dict],
    gears_by_name: dict[str, dict],
    minis_by_name: dict[str, dict],
    gpu_client: GpuServiceClient,
    ga_seed: int,
) -> FGSongResult:
    cfg_dict = cfg_to_dict(cfg)
    calc_song = clone_calc_song(get_base_calc_song(song_path, cfg_dict))
    auto_buff = cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False)
    (
        ga_settings,
        fixed_stats,
        _current_gear_stats,
        current_gear_list,
        _current_mini_stats,
        current_mini_list,
        _meta_finder,
        _enable_fever,
        enable_mini,
        enable_gear,
        _force_greats_mode,
        _force_greats_finder,
        _force_greats_config,
        _manual_force_greats,
    ) = setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)

    ctx = prepare_solver_context(
        cfg,
        fixed_stats,
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        optimize_gear=bool(enable_gear),
        optimize_minis=bool(enable_mini),
        fixed_gear=current_gear_list,
        fixed_minis=current_mini_list,
        pre_prune_mode="none",
        status_cb=lambda _message: None,
        song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
    )
    if ctx is None:
        raise RuntimeError(f"prepare_solver_context failed for {song_path}")

    best_data, best_gear, best_minis, _, _, _, all_evaluated = solve_coevolution_genetic(
        cfg,
        fixed_stats,
        paths,
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        optimize_gear=bool(enable_gear),
        optimize_minis=bool(enable_mini),
        fixed_gear=current_gear_list,
        fixed_minis=current_mini_list,
        ga_depth=1,
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=lambda _message: None,
        executor=None,
        known_loadouts=None,
        song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
        ga_seed=int(ga_seed),
        solver_ctx=ctx,
    )

    primary_color = str((calc_song.get("metadata", {}) or {}).get("Primary Color", "") or "")
    secondary_color = str((calc_song.get("metadata", {}) or {}).get("Secondary Color", "") or "")
    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    fg_candidates = select_fg_candidates(
        _build_outer_candidates(
            best_data=best_data,
            best_gear=list(best_gear or []),
            best_minis=list(best_minis or []),
            all_evaluated=list(all_evaluated or []),
        ),
        limit=fg_candidate_limit,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )

    build_details = make_build_details_fn(primary_color, secondary_color, str(Path(song_path).parent.name))
    fg_search_radius = read_fg_search_radius(cfg)

    t0 = time.perf_counter()
    finder_variants = process_force_greats(
        {},
        False,
        True,
        [],
        calc_song,
        ref_arrays,
        primary_color,
        build_details,
        use_gpu=True,
        fg_search_radius=fg_search_radius,
        perf_timing=False,
        gpu_client=gpu_client,
        ga_candidates=fg_candidates,
        ga_registry=ctx.registry,
    )
    finder_runtime_s = float(time.perf_counter() - t0)

    t0 = time.perf_counter()
    exact_variants = process_fg_exact_dp(
        fg_candidates,
        calc_song,
        ref_arrays,
        use_gpu=True,
        gpu_client=gpu_client,
        song_slot=int(ctx.song_slot or 0),
        loadout_entries={},
        manual_force_greats=False,
        force_greats_finder=True,
        force_greats_config=[],
        meta_primary_color=primary_color,
        build_details_fn=build_details,
        fg_search_radius=fg_search_radius,
        finder_ga_candidates=fg_candidates,
        ga_registry=ctx.registry,
    )
    exact_runtime_s = float(time.perf_counter() - t0)

    return FGSongResult(
        difficulty=str(Path(song_path).parent.name),
        song_path=str(song_path),
        candidate_count=int(len(fg_candidates)),
        finder_runtime_s=finder_runtime_s,
        exact_dp_runtime_s=exact_runtime_s,
        finder_best_fg_score=_best_fg_score(best_data, finder_variants),
        exact_dp_best_fg_score=_best_fg_score(best_data, exact_variants),
        finder_improved_count=int(len([row for row in finder_variants or [] if int(row.get("fg_score", 0) or 0) > int(row.get("score", 0) or 0)])),
        exact_dp_improved_count=int(len([row for row in exact_variants or [] if int(row.get("fg_score", 0) or 0) > int(row.get("score", 0) or 0)])),
    )


def main() -> int:
    args = _parse_args()
    cfg = load_config()
    _force_gpu(cfg)
    paths = load_paths_cache()
    if not paths:
        raise RuntimeError("load_paths_cache failed")
    ref_arrays = _build_ref_arrays(paths)
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {str(item.get("Name", "") or ""): item for item in list(all_gears or [])}
    minis_by_name = {str(item.get("Name", "") or ""): item for item in list(all_minis or [])}
    song_paths = [str(Path(song).resolve()) for song in list(args.songs or [])]
    if not song_paths:
        song_paths = _resolve_default_song_paths(paths)

    GpuExecutor._instance = None
    executor = get_gpu_executor()
    executor.start(in_process=True)
    gpu_client = GpuServiceClient(executor)
    gpu_client.start(start_executor=False)

    try:
        results = [
            _run_song(
                cfg=cfg,
                song_path=str(song_path),
                ref_arrays=ref_arrays,
                paths=paths,
                all_gears=all_gears,
                all_minis=all_minis,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
                gpu_client=gpu_client,
                ga_seed=int(args.seed),
            )
            for song_path in song_paths
        ]
    finally:
        try:
            gpu_client.close()
        except Exception:
            pass
        try:
            executor.stop()
        finally:
            GpuExecutor._instance = None

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps([asdict(row) for row in results], indent=2), encoding="utf-8")

    print("=== FG Exact DP Real-Song Validation ===")
    bad = False
    for row in results:
        print(
            f"{row.difficulty}: {Path(row.song_path).name} | n={row.candidate_count} | "
            f"finder={row.finder_runtime_s:.3f}s best={row.finder_best_fg_score:,} improved={row.finder_improved_count} | "
            f"exact_dp={row.exact_dp_runtime_s:.3f}s best={row.exact_dp_best_fg_score:,} improved={row.exact_dp_improved_count}"
        )
        if int(row.exact_dp_best_fg_score) < int(row.finder_best_fg_score):
            bad = True

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
