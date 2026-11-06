from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong, fever_fill_denominators
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.frontier.types import FgResponseFrontierSolveResult
from gear_optimizer.trace.activation_witness import (
    activation_schedule_witnesses,
    exact_label_hit_intervals,
)
from gear_optimizer.trace.reconstruct import FgTraceEdgeOptionsCache, reconstruct_force_greats_response_trace


from .physical_replay import validate_force_greats_physical_replay


@dataclass(slots=True)
class FgTraceMaterializationCache:
    """Validated trace/edge cache bound to one exact song owner."""

    traces: dict[Any, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    edge_options: FgTraceEdgeOptionsCache = field(default_factory=FgTraceEdgeOptionsCache)
    _song_owner: TimedSong | None = None

    def bind(self, song: TimedSong) -> None:
        if self._song_owner is None:
            self._song_owner = song
        elif self._song_owner is not song:
            raise ValueError("FG trace materialization cache cannot be reused across song owners")


def _assert_trace_hit_time_reachable(frontier_trace, song_inputs, *, raw_fever_fill: float) -> None:
    """FAIL LOUD if a persisted activation is not input-engine reachable.

    This is the persistence-side invariant for the canonical owner: the activation clock and drain
    window must be produced by the same weighted, lane-aware hit-time walk the surface prices. It never
    mutates the surface; a rejection here means the producer emitted a phantom surface and must be fixed.
    """
    ts = np.asarray(song_inputs.timestamps, dtype=np.float32).reshape(-1)
    pc = np.asarray(song_inputs.perfect_candidates, dtype=np.float32).reshape(-1)
    gc = np.asarray(song_inputs.great_candidates, dtype=np.float32).reshape(-1)
    pf = np.asarray(song_inputs.perfect_floor, dtype=np.float32).reshape(-1)
    gf = np.asarray(song_inputs.great_floor, dtype=np.float32).reshape(-1)
    lanes = np.asarray(song_inputs.lanes, dtype=np.int32).reshape(-1)
    n = int(ts.shape[0])
    if any(int(arr.shape[0]) != n for arr in (pc, gc, pf, gf, lanes)):
        raise ValueError("FG persist guard: timing arrays and lanes must match timestamps")

    for row in frontier_trace:
        a = int(row["activation_index"])
        if not (0 <= a < n):
            continue
        section_start = max(0, int(row["forced_start_index"]))
        forced_start = max(0, int(row["forced_run_start_index"]))
        forced_count = max(0, int(row["forced_run_count"]))
        forced_end = min(n, forced_start + forced_count)
        is_great = np.zeros((n,), dtype=np.bool_)
        if forced_end > forced_start:
            is_great[forced_start:forced_end] = True
        if str(row.get("activation_judgment")) == "late_great":
            is_great[a] = True
        labels = exact_label_hit_intervals(
            is_great=is_great,
            timestamps=ts,
            perfect_floor_timestamps=pf,
            perfect_candidate_timestamps=pc,
            great_floor_timestamps=gf,
            great_candidate_timestamps=gc,
        )
        h_a = float(row.get("activation_hit_window_upper_ms", float(labels.primary_high[a]) * 1000.0)) / 1000.0
        if not activation_schedule_witnesses(
            labels=labels,
            lanes=lanes,
            activation_index=a,
            activation_hit_timestamp=h_a,
            fever_fill_denom=float(raw_fever_fill),
            section_start=section_start,
            predecessor_hit_timestamp=(
                None if int(section_start) == 0 else float(pf[int(section_start) - 1])
            ),
        ):
            raise ValueError(
                f"FG persist guard: activation @{a} (section {row.get('section')}, "
                f"judgment={row.get('activation_judgment')}) is not reachable under the weighted, "
                f"lane-aware input-engine owner. The frontier build must foreclose this; a trace "
                f"reaching persistence with it is a producer regression, not a persist fixup."
            )


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
    trace_cache.bind(song)
    frontier = result.frontier
    song_inputs = song.fg_inputs
    trace_cache.edge_options.bind_owner(song, note_count=len(song_inputs.timestamps))
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
        _assert_trace_hit_time_reachable(base_trace, song_inputs, raw_fever_fill=result.raw_fever_fill)
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
