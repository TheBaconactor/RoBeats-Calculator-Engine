"""The FG replay of loadouts at a song's timing: each loadout's gems re-solved on the song's response frontier and the
winner materialized. A loadout's FG plan can differ from its Base play at any timing: forcing Greats changes how fast the
fever bar fills, a count effect independent of hit offsets, so FG at fixed chart timing is not Base at fixed chart timing."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from gear_optimizer.frontier.fg_cache import scoring_bundle_covering
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.solver.fg_scoring import fg_solve_results, required_response_stat_keys
from gear_optimizer.solver.scoring.exact_rescore import score_base_exact_batch
from gear_optimizer.solver.timing_envelope import TimedSong

from .materialize import FgTraceMaterializationCache, materialize_force_payload_from_response_frontier
from .reconstruct import UnplayableTrace

logger = logging.getLogger(__name__)


def build_fixed_timing_fg_replays(
    pre_gem_stats: list[Mapping[str, Any]],
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    trace_cache: FgTraceMaterializationCache,
    perfect_times: list[int],
) -> list[dict[str, Any] | None]:
    """Each row of pre-gem stats' FG `force` payload at the song's timing, in order (the shape of a persisted FG row,
    carrying its frontier trace), or None when no hit timing plays its plan at the row's Perfect Time. Its paired base is
    the non-FG score at the re-solved stats. `trace_cache` is shared by the replays of one song: loadouts commonly reach the same surface, at
    every TeamBuff tier, and the trace rebuild is the dominant cost. The caller releases the song's bundle
    (release_fg_response_song_memory)."""
    rows = [dict(stats) for stats in pre_gem_stats]
    if not rows:
        return []
    bundle = scoring_bundle_covering(song, curves, required_response_stat_keys(rows))
    results = fg_solve_results(rows, song=song, curves=curves, selected_color=selected_color, scoring_bundle=bundle)
    paired_base_scores = score_base_exact_batch([result.stats for result in results], song, curves)
    forces: list[dict[str, Any] | None] = []
    for result, paired_base, perfect_time in zip(results, paired_base_scores, perfect_times, strict=True):
        try:
            forces.append(materialize_force_payload_from_response_frontier(
                base_stats=dict(result.stats),
                paired_base_score=paired_base,
                selected_element=selected_color,
                result=result,
                song=song,
                curves=curves,
                trace_cache=trace_cache,
                perfect_time=perfect_time,
            ))
        except UnplayableTrace as exc:
            # As the solver's materializer: a plan no hit timing plays (non-precise: a held tail's Great between its
            # chord's presses) has no FG result, rather than failing the song.
            logger.warning("%s: no FG result for a loadout, its plan is unplayable: %s", song.chart.name, exc)
            forces.append(None)
    return forces
