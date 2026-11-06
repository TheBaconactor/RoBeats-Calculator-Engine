from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gear_optimizer.solver.timing_envelope import TimedSong, fever_fill_denominators
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.frontier.types import FgResponseFrontierSolveResult
from gear_optimizer.trace.reconstruct import FgTraceEdgeOptionsCache, reconstruct_force_greats_response_trace


from .physical_replay import validate_force_greats_physical_replay


@dataclass(slots=True)
class FgTraceMaterializationCache:
    """One song's validated traces and section options."""

    traces: dict[Any, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    edge_options: FgTraceEdgeOptionsCache = field(default_factory=FgTraceEdgeOptionsCache)


def materialize_force_payload_from_response_frontier(
    *,
    base_stats: dict[str, Any],
    paired_base_score: int,
    selected_element: str,
    result: FgResponseFrontierSolveResult,
    song: TimedSong,
    curves: StatCurves,
    trace_cache: FgTraceMaterializationCache,
    perfect_time: int,
) -> dict[str, Any]:
    if paired_base_score <= 0:
        raise ValueError("ForceGreats response frontier is missing paired source base score.")
    frontier = result.frontier
    song_inputs = song.fg_inputs
    surface = result.surface
    # The frontier plans against the fill threshold (result.raw_fever_fill); the replay and the persisted trace use the
    # game's own fill denominator for the final Fever Fill stat, so the stored plan is checked against the game's
    # float64 bar.
    fever_fill_denominator = float(
        fever_fill_denominators(
            int(song_inputs.total_notes) - int(song_inputs.long_notes),
            curves.f64["Fever Fill Rate"][min(int(result.stats["Fever Fill Rate"]), MAX_STAT)],
        )
    )
    # The trace is a pure function of the surface and the fever geometry, and rebuilding it is the dominant post-score
    # host cost, so the loadouts of one song share it. The key MUST include the fill denominator and non_fever_base: they
    # fix the action table and the replay, and Perfect Time: it fixes the hit windows the replay plays. A trace is validated
    # once, before it enters the cache: a repeat would add no independent check.
    trace_key = (
        frontier.non_fever_base,
        tuple(surface),
        fever_fill_denominator,
        result.real_fever_time,
        bool(song_inputs.use_forced_great_timing),
        perfect_time,
    )
    base_trace = trace_cache.traces.get(trace_key)
    if base_trace is None:
        base_trace = reconstruct_force_greats_response_trace(
            inputs=song_inputs,
            non_fever_base=frontier.non_fever_base,
            target_surface=surface,
            raw_fever_fill=result.raw_fever_fill,
            real_fever_time=result.real_fever_time,
            edge_options_cache=trace_cache.edge_options,
        )
        validate_force_greats_physical_replay(
            frontier_trace=base_trace,
            surface=surface,
            timestamps=song_inputs.timestamps,
            note_types=song.chart.note_types,
            lanes=song_inputs.lanes,
            fever_fill_denominator=fever_fill_denominator,
            real_fever_time=result.real_fever_time,
            timing_mode=song.mode,
            perfect_time=perfect_time,
        )
        trace_cache.traces[trace_key] = base_trace
    final_score = int(score_force_greats_response_surface_exact(result.stats, song, curves, surface))
    return {
        "BaseStats": dict(base_stats),
        "Stats": dict(result.stats),
        "BaseScore": int(paired_base_score),
        "Score": final_score,
        "Selected Element": selected_element,
        "GemCounts": dict(result.gem_counts),
        "FT": int(result.ft),
        "FF": int(result.ff),
        "response_surface": list(surface),
        "ForceGreats": {
            "final_score": final_score,
            # Fever-window parameters of this surface (the server's feverFillDenom and the fever duration in seconds):
            # the legality audit re-derives the fill crossing and drain from them without re-solving, and the frontend
            # timing graph places the fever window.
            "raw_fever_fill": fever_fill_denominator,
            "real_fever_time": result.real_fever_time,
            "frontier_trace": [dict(row) for row in base_trace],
            "frontier_first_surfaces": frontier.first_surfaces,
            "frontier_states": frontier.states_evaluated,
            "frontier_max_state": frontier.max_state_frontier,
            "frontier_transitions": frontier.transitions_evaluated,
            "non_fever_base": frontier.non_fever_base,
        },
    }
