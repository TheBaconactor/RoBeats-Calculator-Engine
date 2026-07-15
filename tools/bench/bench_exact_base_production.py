"""Measure the canonical exact Base pipeline on a real catalog and song.

Cold timeline/song-context construction is reported separately.  Measured runs
execute the same request-scoped domain reduction, Vulkan semiring, exact inner
scoring, and ranked 51-row materialization used by production.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import statistics
import sys
import time

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from gear_optimizer.core.config import get_config_path, load_config, load_paths_cache
from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import get_fixed_stats, read_table
from gear_optimizer.data.loadout_equivalence import (
    get_gears_by_name_cached,
    get_minis_by_name_cached,
)
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
from gear_optimizer.helpers.song_helpers.song_config import (
    apply_baseline_team_buff_config,
    assert_fixed_stats_include_baseline_team_buff,
)
from gear_optimizer.solver.exact_base_domains import build_exact_base_domains
from gear_optimizer.solver.exact_base_search import run_exact_base_pipeline
from gear_optimizer.solver.exact_base_song_context import (
    ExactBaseSongContextInputs,
    build_exact_base_song_context,
)
from gear_optimizer.solver.solver_common import prepare_solver_context
from gear_optimizer.solver.taichi_gem.api.timeline import (
    build_or_load_timeline_frontier_payload,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


def _song_path(*, difficulty: str, song: str, explicit_path: str) -> Path:
    if explicit_path:
        path = Path(explicit_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    paths = load_paths_cache()
    root = Path(paths.get(str(difficulty), "") or PATHS.data_path(str(difficulty)))
    matches = sorted(root.glob(f"{song}* ({difficulty})*.txt")) if song else sorted(root.glob("*.txt"))
    if not matches:
        raise FileNotFoundError(
            f"No {difficulty} song matched {song!r} under {root}"
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--difficulty", default="Hard")
    parser.add_argument("--song", default="00")
    parser.add_argument("--song-fp", default="")
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.warmups < 0 or args.runs <= 0:
        raise ValueError("--warmups must be nonnegative and --runs must be positive")

    config_path = get_config_path()
    cfg = load_config(config_path)
    path = _song_path(
        difficulty=str(args.difficulty),
        song=str(args.song),
        explicit_path=str(args.song_fp),
    )
    calc_song = get_base_calc_song(str(path), cfg_to_dict(cfg))
    apply_timing_envelope(calc_song)
    team_buff, team_color = apply_baseline_team_buff_config(cfg, calc_song)
    fixed_stats = get_fixed_stats(cfg)
    assert_fixed_stats_include_baseline_team_buff(
        fixed_stats,
        team_buff=team_buff,
        team_color=team_color,
    )
    paths = load_paths_cache()
    stats_path = paths.get("Stats", "") or PATHS.stats_csv
    refs = build_ref_arrays_from_stats(read_table(stats_path), dtype=np.float32)
    gears = list(get_gears_by_name_cached().values())
    minis = list(get_minis_by_name_cached().values())

    started = time.perf_counter()
    timeline = build_or_load_timeline_frontier_payload(calc_song, refs)
    timeline_seconds = time.perf_counter() - started
    started = time.perf_counter()
    context = prepare_solver_context(
        cfg,
        fixed_stats,
        calc_song,
        refs,
        gears,
        minis,
        song_slot=0,
    )
    if context is None:
        raise RuntimeError("Exact Base benchmark could not build the production solver context")
    domains = build_exact_base_domains(context)
    catalog_seconds = time.perf_counter() - started
    started = time.perf_counter()
    song_context = build_exact_base_song_context(
        ExactBaseSongContextInputs.from_solver_context(context),
        timeline.payload,
    )
    song_context_seconds = time.perf_counter() - started

    metadata = calc_song.get("metadata", {})
    print(
        f"song={path.name} colors={context.p_color}/{context.s_color} "
        f"notes={metadata.get('Total Notes')}"
    )
    print(
        f"cold timeline={timeline_seconds:.3f}s catalog={catalog_seconds:.3f}s "
        f"song_context={song_context_seconds:.3f}s source={timeline.cache_source}"
    )
    print(
        "domains "
        f"left={domains.left_stats.shape[0]:,} right={domains.right_stats.shape[0]:,} "
        f"minis={domains.mini_stats.shape[0]:,} "
        f"programs={song_context.program_map.program_count:,}"
    )

    for warmup in range(int(args.warmups)):
        started = time.perf_counter()
        result = run_exact_base_pipeline(
            context,
            domains=domains,
            song_context=song_context,
            timeline_frontier=timeline,
            candidate_limit=51,
        )
        elapsed = time.perf_counter() - started
        print(
            f"warmup={warmup + 1} seconds={elapsed:.3f} "
            f"score={result.candidate_surface.best_score:,} "
            f"scored={result.scored_pool.candidate_ids.shape[0]:,}"
        )

    times: list[float] = []
    measured = None
    for run in range(int(args.runs)):
        started = time.perf_counter()
        measured = run_exact_base_pipeline(
            context,
            domains=domains,
            song_context=song_context,
            timeline_frontier=timeline,
            candidate_limit=51,
        )
        elapsed = time.perf_counter() - started
        times.append(elapsed)
        print(
            f"run={run + 1} seconds={elapsed:.3f} "
            f"score={measured.candidate_surface.best_score:,} "
            f"surface={measured.candidate_surface.count} "
            f"scored={measured.scored_pool.candidate_ids.shape[0]:,}"
        )
    if measured is None:
        raise AssertionError("No measured exact Base run completed")
    print(
        f"median={statistics.median(times):.3f}s min={min(times):.3f}s "
        f"max={max(times):.3f}s score={measured.candidate_surface.best_score:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
