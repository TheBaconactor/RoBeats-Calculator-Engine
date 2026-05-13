"""
Validate the exact bounded inner solver on representative real songs.

This bench compares the current registry solve with:
  - greedy/refined inner solver (`use_exact_inner_solver=False`)
  - exact bounded inner solver (`use_exact_inner_solver=True`)

It uses the same encoded population batch for both modes and records score deltas
plus focused runtime. Exit code is non-zero if the exact bounded solver ever
returns a lower score than the greedy path on the sampled populations.
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

from gear_optimizer.core.config import load_config, load_paths_cache
from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_GEM_BUDGET, TOTAL_ROWS
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.helpers.song_helpers import setup_song_config
from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
from gear_optimizer.solver.registry_solve_request import RegistrySolveRequest, dispatch_registry_solve
from gear_optimizer.solver.solver_common import SolverContext, prepare_solver_context


DEFAULT_SONG_MATCHERS: tuple[tuple[str, str], ...] = (
    ("Easy", "Red  Room"),
    ("Normal", "#include signal.h"),
    ("Hard", "You & I"),
)


@dataclass
class SongValidationResult:
    difficulty: str
    song_path: str
    candidate_count: int
    greedy_runtime_s: float
    exact_runtime_s: float
    greedy_best_score: int
    exact_best_score: int
    exact_better_count: int
    equal_count: int
    exact_worse_count: int
    max_exact_uplift: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the exact bounded inner solver on representative real songs.")
    parser.add_argument("--samples", type=int, default=96, help="Population samples per song.")
    parser.add_argument("--seed", type=int, default=20260408, help="Deterministic RNG seed.")
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


def _prepare_context(
    *,
    cfg: Any,
    song_path: str,
    ref_arrays: dict[str, np.ndarray],
    all_gears: list[dict],
    all_minis: list[dict],
    gears_by_name: dict[str, dict],
    minis_by_name: dict[str, dict],
) -> SolverContext:
    cfg_dict = cfg_to_dict(cfg)
    calc_song = clone_calc_song(get_base_calc_song(song_path, cfg_dict))
    auto_buff = True
    (
        _ga_settings,
        fixed_stats,
        _current_gear_stats,
        current_gear_list,
        _current_mini_stats,
        current_mini_list,
        _force_greats_finder,
        _force_greats_config,
        _manual_force_greats,
    ) = setup_song_config(cfg, calc_song, auto_buff, load_paths_cache(), gears_by_name, minis_by_name)

    ctx = prepare_solver_context(
        cfg,
        fixed_stats,
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        optimize_gear=True,
        optimize_minis=True,
        fixed_gear=current_gear_list,
        fixed_minis=current_mini_list,
        pre_prune_mode="none",
        status_cb=lambda _message: None,
        song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
    )
    if ctx is None:
        raise RuntimeError(f"prepare_solver_context failed for {song_path}")
    return ctx


def _sample_population_indices(ctx: SolverContext, *, count: int, rng: np.random.Generator) -> np.ndarray:
    out = np.zeros((int(count), 9), dtype=np.int32)
    gear_ids = [np.asarray(ids, dtype=np.int32) for ids in list(ctx.slot_item_ids or [])[:6]]
    mini_ids = np.asarray(ctx.mini_item_ids, dtype=np.int32)
    if len(gear_ids) != 6 or any(arr.size <= 0 for arr in gear_ids) or mini_ids.size < 3:
        raise RuntimeError("SolverContext registry pools are too small for population sampling")

    for row in range(int(count)):
        for slot_idx, ids in enumerate(gear_ids):
            out[row, slot_idx] = int(ids[int(rng.integers(0, ids.size))])
        chosen_minis = rng.choice(mini_ids, size=3, replace=False)
        out[row, 6:9] = np.asarray(chosen_minis, dtype=np.int32)
    return out


def _dispatch_batch(ctx: SolverContext, population_indices: np.ndarray, *, use_exact_inner_solver: bool) -> tuple[float, list]:
    req = RegistrySolveRequest(
        population_indices=np.asarray(population_indices, dtype=np.int32),
        item_stats=ctx.gpu_arrays["item_stats"],
        slot_start=ctx.gpu_arrays["slot_start"],
        slot_count=ctx.gpu_arrays["slot_count"],
        base_fixed_stats=ctx.base_fixed_stats_arr,
        timeline_grid=ctx.calc_song,
        ref_arrays=ctx.ref_arrays,
        flags={k: int(v) for k, v in (ctx.color_flags or {}).items()},
        total_budget=int(TOTAL_GEM_BUDGET),
        gem_scale_fever=int(GEM_SCALE_FEVER),
        song_slot=int(ctx.song_slot or 0),
        use_exact_inner_solver=bool(use_exact_inner_solver),
    )
    t0 = time.perf_counter()
    results = dispatch_registry_solve(req, gpu_client=ctx.gpu_client)
    return float(time.perf_counter() - t0), list(results or [])


def _score_list(results: list) -> list[int]:
    out: list[int] = []
    for row in results:
        try:
            out.append(int(row[0] or 0))
        except Exception:
            out.append(0)
    return out


def _validate_song(ctx: SolverContext, *, song_path: str, sample_count: int, rng: np.random.Generator) -> SongValidationResult:
    population_indices = _sample_population_indices(ctx, count=int(sample_count), rng=rng)

    warm = population_indices[:1].copy()
    _dispatch_batch(ctx, warm, use_exact_inner_solver=False)
    _dispatch_batch(ctx, warm, use_exact_inner_solver=True)

    greedy_runtime_s, greedy_results = _dispatch_batch(ctx, population_indices, use_exact_inner_solver=False)
    exact_runtime_s, exact_results = _dispatch_batch(ctx, population_indices, use_exact_inner_solver=True)

    greedy_scores = _score_list(greedy_results)
    exact_scores = _score_list(exact_results)
    if len(greedy_scores) != len(exact_scores):
        raise RuntimeError(f"Result length mismatch for {song_path}: {len(greedy_scores)} != {len(exact_scores)}")

    exact_better_count = 0
    equal_count = 0
    exact_worse_count = 0
    max_exact_uplift = 0
    for greedy_score, exact_score in zip(greedy_scores, exact_scores, strict=True):
        delta = int(exact_score) - int(greedy_score)
        if delta > 0:
            exact_better_count += 1
            if delta > max_exact_uplift:
                max_exact_uplift = int(delta)
        elif delta == 0:
            equal_count += 1
        else:
            exact_worse_count += 1

    return SongValidationResult(
        difficulty=str(Path(song_path).parent.name),
        song_path=str(song_path),
        candidate_count=int(len(population_indices)),
        greedy_runtime_s=float(greedy_runtime_s),
        exact_runtime_s=float(exact_runtime_s),
        greedy_best_score=max(greedy_scores) if greedy_scores else 0,
        exact_best_score=max(exact_scores) if exact_scores else 0,
        exact_better_count=int(exact_better_count),
        equal_count=int(equal_count),
        exact_worse_count=int(exact_worse_count),
        max_exact_uplift=int(max_exact_uplift),
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

    rng = np.random.default_rng(int(args.seed))
    results: list[SongValidationResult] = []
    for song_path in song_paths:
        ctx = _prepare_context(
            cfg=cfg,
            song_path=str(song_path),
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
        )
        results.append(_validate_song(ctx, song_path=str(song_path), sample_count=int(args.samples), rng=rng))

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps([asdict(row) for row in results], indent=2), encoding="utf-8")

    print("=== Exact Inner Real-Song Validation ===")
    bad = False
    for row in results:
        print(
            f"{row.difficulty}: {Path(row.song_path).name} | n={row.candidate_count} | "
            f"greedy={row.greedy_runtime_s:.3f}s best={row.greedy_best_score:,} | "
            f"exact={row.exact_runtime_s:.3f}s best={row.exact_best_score:,} | "
            f"better={row.exact_better_count} tie={row.equal_count} worse={row.exact_worse_count} "
            f"max_uplift={row.max_exact_uplift:,}"
        )
        if int(row.exact_worse_count) > 0:
            bad = True

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
