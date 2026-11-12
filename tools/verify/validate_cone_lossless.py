"""An older FG frontier version and the current one hold the same best score at every sampled stat line.

  python tools/verify/validate_cone_lossless.py OLD_VERSION... [--stride N] [--cells N] [--lines N]

OLD_VERSION...: the old version and the predecessors it ratified, whose files it still serves. Their bundles and the current
version's sit in the FG cache directory (a file's name carries its version). A cone filter may drop any surface
no stat line needs and may never lower a stat line's best, so each sampled (FT, FF) cell of each chart is scored at random
stat lines of the realizable box with the exact per-note floors of gem_search._surface_score. Exit 1 on any difference.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gear_optimizer.chart import load_chart  # noqa: E402
from gear_optimizer.frontier.fg_cache import scoring_bundle  # noqa: E402
from gear_optimizer.frontier.fg_cache_keys import fg_response_frontier_bundle_cache_key  # noqa: E402
from gear_optimizer.frontier.fg_cache_store import FG_RESPONSE_FRONTIER_CACHE, read_bundle  # noqa: E402
from gear_optimizer.gamedata import stat_curves  # noqa: E402
from gear_optimizer.settings import DIFFICULTIES, paths  # noqa: E402
from gear_optimizer.solver.gem_search import _surface_score  # noqa: E402
from gear_optimizer.solver.timing_envelope import TIMING_MODES, time_song  # noqa: E402


@njit(cache=True)
def _best_scores(surfaces, cell, notes, lines, ramps, single):
    """The best score of one cell's surfaces at each stat line (primary, secondary, Perfect Points, combo, fever)."""
    pattern_ids, words, counts = surfaces
    first, length = cell
    best = np.full(lines.shape[0], -1, np.int64)
    for s in range(lines.shape[0]):
        primary, secondary, pp, combo, fever = lines[s]
        for r in range(first, first + length):
            surface = (int(counts[r, 0]), int(counts[r, 1]), int(counts[r, 2]))
            best[s] = max(best[s], _surface_score(
                words[pattern_ids[r]], surface, notes, int(primary), int(secondary), pp, (combo, ramps[s], fever), single
            ))
    return best


def _stat_lines(rng: np.random.Generator, count: int, curves, single: bool) -> tuple[np.ndarray, np.ndarray]:
    stats = rng.integers(0, 161, (count, 3))
    primary = rng.integers(0, 1400, count).astype(np.float64)
    secondary = primary if single else rng.integers(0, 1400, count).astype(np.float64)
    lines = np.column_stack((
        primary, secondary, curves.f64["Perfect Points"][stats[:, 0]], curves.f64["Combo Multiplier"][stats[:, 1]],
        curves.f64["Fever Multiplier"][stats[:, 2]],
    ))
    return lines, np.stack([curves.ramp(int(stat)) for stat in stats[:, 1]])


def _pool(bundle):
    return bundle.pool.pattern_ids, bundle.pool.pattern_words, bundle.pool.counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("old_versions", nargs="+")
    parser.add_argument("--stride", type=int, default=1, help="every Nth chart")
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--lines", type=int, default=64)
    args = parser.parse_args()
    curves = stat_curves()
    rng = np.random.default_rng(20261107)
    charts = [path for name in DIFFICULTIES for path in sorted(paths().chart_dir(name).glob("*.txt"))][:: args.stride]
    compared = different = old_rows = new_rows = 0
    for chart_path in charts:
        chart = load_chart(chart_path)
        single = chart.primary == chart.secondary
        for mode in TIMING_MODES:
            key = fg_response_frontier_bundle_cache_key(time_song(chart, mode), curves)
            old_key = next(
                old_key for old_key in ((version, *key[1:]) for version in args.old_versions)
                if FG_RESPONSE_FRONTIER_CACHE.file_path(old_key).exists()
            )
            old = scoring_bundle(old_key, read_bundle(FG_RESPONSE_FRONTIER_CACHE.file_path(old_key)))
            new = scoring_bundle(key, read_bundle(FG_RESPONSE_FRONTIER_CACHE.file_path(key)))
            old_rows += old.pool.counts.shape[0]
            new_rows += new.pool.counts.shape[0]
            notes = (min(new.total_notes, 100), max(0, new.total_notes - 100))
            for ft, ff in rng.integers(0, 161, (args.cells, 2)).tolist():
                lines, ramps = _stat_lines(rng, args.lines, curves, single)
                best = [
                    _best_scores(_pool(bundle), (
                        int(bundle.pool.frontier_offsets[bundle.frontier_idx_by_stat[ft, ff]]),
                        int(bundle.pool.frontier_lengths[bundle.frontier_idx_by_stat[ft, ff]]),
                    ), notes, lines, ramps, single)
                    for bundle in (old, new)
                ]
                compared += args.lines
                if not np.array_equal(best[0], best[1]):
                    different += int((best[0] != best[1]).sum())
                    print(f"DIFFERENT {chart.name} {mode} ({ft}, {ff})", flush=True)
    print(f"{len(charts)} charts, surfaces {old_rows} -> {new_rows}, {compared} stat lines compared, {different} different")
    return 1 if different else 0


if __name__ == "__main__":
    raise SystemExit(main())
