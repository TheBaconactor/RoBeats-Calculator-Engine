"""frame_robust: plans whose judgments and fever hold at every frame timing (frame_mode/FRAME_TIMING_SPEC.md).

The game reads inputs once per frame and its server floors event times to whole ms, so a planned press is judged up to
FRAME_MARGIN_MS late: frame_robust ends every judgment band that much earlier and keeps every note at least that far
from a fever end. These tests pin the bands, the fever times and the cache identity, and replay a real chart's plans
through the frame-based game simulator at many frame phases and rates.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.chart import load_chart
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_song_cache_key
from gear_optimizer.solver.timing_envelope import (
    FRAME_MARGIN_MS,
    HELD_TAIL_WINDOW_SCALE,
    fever_window_times,
    judgment_bounds,
    time_song,
)

REPO = Path(__file__).resolve().parents[1]


def test_bands_end_one_frame_margin_earlier() -> None:
    # (earliest, latest) planned offsets in ms: (Perfect, early Great, late Great) for a tap and a held tail.
    assert judgment_bounds(1, "perfect_window") == ((-19, 40), (-94, -20), (41, 190))
    assert judgment_bounds(HELD_TAIL_WINDOW_SCALE, "perfect_window") == ((-39, 80), (-189, -40), (81, 200))
    assert judgment_bounds(1, "frame_robust") == ((-19, 22), (-94, -38), (41, 172))
    assert judgment_bounds(HELD_TAIL_WINDOW_SCALE, "frame_robust") == ((-39, 62), (-189, -58), (81, 182))
    for scale in (1, HELD_TAIL_WINDOW_SCALE):
        bounds = judgment_bounds(scale, "frame_robust")
        # Differently judged presses of one chart time are never within a frame of each other.
        assert bounds.early_great.latest + FRAME_MARGIN_MS < bounds.perfect.earliest
        assert bounds.perfect.latest + FRAME_MARGIN_MS < bounds.late_great.earliest


def test_fever_windows_end_one_frame_margin_early() -> None:
    factors = np.asarray([0.0, 0.5, 1.0, 1.7], dtype=np.float32)
    real = fever_window_times(120.0, factors, "perfect_window")
    assert np.array_equal(real, (120.0 * 0.15 + 0.15) * factors.astype(np.float64))
    assert np.array_equal(fever_window_times(120.0, factors, "frame_robust"), np.maximum(real - FRAME_MARGIN_MS / 1000.0, 0.0))


def test_song_has_its_own_envelopes_and_cache_identity() -> None:
    chart = load_chart(REPO / "Data" / "Normal" / "Surface by Dimrain47.txt")
    window, robust = time_song(chart, "perfect_window"), time_song(chart, "frame_robust")
    assert robust.mode == "frame_robust"
    tail = chart.note_types == 3
    latest_perfect_ms = np.rint((robust.perfect_candidates.astype(np.float64) - chart.timestamps) * 1000.0)
    assert set(latest_perfect_ms[~tail].tolist()) <= {22.0} and set(latest_perfect_ms[tail].tolist()) <= {62.0}
    assert np.array_equal(robust.perfect_floor, window.perfect_floor)  # early edges do not move
    assert robust.timeline_key != window.timeline_key
    assert fg_response_frontier_song_cache_key(robust) != fg_response_frontier_song_cache_key(window)


def _base_plans(chart, mode: str, ft: int, ff: int):
    """The producer's Base plans for one FT/FF cell, as validated note graphs."""
    from gear_optimizer.gamedata import load_stat_curves
    from gear_optimizer.rules import FEVER_FILL_PER_NOTE
    from gear_optimizer.solver.fg_response_scoring.note_graph import timeline_frontier_note_graph
    from gear_optimizer.solver.fg_response_scoring.physical_replay import validate_base_physical_replay
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from gear_optimizer.solver.timeline_exact_frontier import reconstruct_timeline_physical_trace

    curves = load_stat_curves(REPO / "Data" / "Gear" / "Stats.txt")
    song = time_song(chart, mode)
    fi = song.fg_inputs
    n = int(chart.total_notes)
    raw_fill = float(max(0, n - chart.long_notes)) * FEVER_FILL_PER_NOTE * float(curves.f32["Fever Fill Rate"][ff])
    fill = max(1, int(np.ceil(raw_fill)))
    window_time = float(fever_window_times(chart.last_note_time, curves.f32["Fever Time"], mode)[ft])
    (frontier,) = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=fi.timestamps, perfect_candidate_timestamps=fi.perfect_candidates,
        great_candidate_timestamps=fi.perfect_candidates, perfect_floor_timestamps=fi.perfect_floor,
        great_floor_timestamps=fi.perfect_floor, lanes=fi.lanes, geometries=((float(fill), 0, window_time),),
        use_forced_great_timing=False,
    )
    graphs = []
    for row in frontier.first_frontier:
        words = (int(row.fever0), int(row.fever1), int(row.fever2), int(row.fever3))
        trace = reconstruct_timeline_physical_trace(
            head_bits=words, body_fever=int(row.body_fever), timestamps=fi.timestamps,
            perfect_candidate_timestamps=fi.perfect_candidates, great_candidate_timestamps=fi.great_candidates,
            perfect_floor_timestamps=fi.perfect_floor, great_floor_timestamps=fi.great_floor, lanes=fi.lanes,
            raw_fever_fill=raw_fill, real_fever_time=window_time,
        )
        validate_base_physical_replay(
            frontier_trace=trace, response_surface=[*words, int(row.body_fever), max(0, n - 100) - int(row.body_fever)],
            timestamps=chart.timestamps, note_types=chart.note_types, lanes=chart.lanes, fill_count=fill,
            fever_duration_ms=window_time * 1000.0, timing_mode=mode,
        )
        graphs.append(timeline_frontier_note_graph(
            frontier_trace=trace, total_notes=n, timestamps=chart.timestamps, note_types=chart.note_types,
            lanes=chart.lanes, timing_mode=mode,
        ))
    return graphs


def _fever_sets_per_frame_timing(chart, graph, ft: int, ff: int) -> set[tuple[int, ...]]:
    """The fever notes the frame-based game simulator registers for one plan, over frame phases at 60 and 144 fps."""
    from tools.verify.game_sim import IntendedNote, NoteChart, presses_from_intended, simulate

    nt, lanes = chart.note_types, chart.lanes
    sim_chart = NoteChart([float(t) * 1000.0 for t in chart.timestamps.tolist()], [int(x) for x in lanes.tolist()],
                          [int(x) for x in nt.tolist()])
    config = {"hitCount": int(chart.total_notes), "hitObjectsCount": int(((nt == 1) | (nt == 2)).sum()),
              "lastNoteTimeSec": (chart.last_note_time * 1000.0 + 1000.0) / 1000.0}
    statsdict = {"PerfectPoints": 80, "ComboMultiplier": 80, "FeverMultiplier": 80, "FeverTime": ft,
                 "FeverFillRate": ff, "ColorGreen": 600, "ColorOrange": 300}
    presses = presses_from_intended(sim_chart, [
        IntendedNote(i, float(node["hit_time_ms"]), "perfect", int(nt[i]), int(lanes[i]), float(node["delta_ms"]))
        for i, node in enumerate(graph)
    ])
    seen = set()
    for rate in (60.0, 144.0):
        dt = 1000.0 / rate
        for k in range(9):
            sim = simulate(sim_chart, statsdict, ["ColorGreen", "ColorOrange"], presses, config, frame_dt_ms=dt,
                           frame_phase_ms=k * dt / 9)
            assert all(hit.result == "perfect" for hit in sim.registered if hit.kind == "note")
            seen.add(tuple(sorted(hit.note_index for hit in sim.registered if hit.kind == "note" and hit.fever)))
    return seen


@pytest.mark.slow
def test_base_plans_hold_at_every_frame_timing() -> None:
    """Surface's FT/FF 0 perfect_window plan claims a fever note frames decide (found by T1); frame_robust's plans
    keep their claimed fever set at every phase and rate."""
    chart = load_chart(REPO / "Data" / "Normal" / "Surface by Dimrain47.txt")
    assert (chart.primary, chart.secondary) == ("Vibe", "Beat")
    window_sets = [_fever_sets_per_frame_timing(chart, g, 0, 0) for g in _base_plans(chart, "perfect_window", 0, 0)]
    assert any(len(sets) > 1 for sets in window_sets)
    for graph in _base_plans(chart, "frame_robust", 0, 0):
        claimed = tuple(i for i, node in enumerate(graph) if node["fever"])
        assert _fever_sets_per_frame_timing(chart, graph, 0, 0) == {claimed}


def test_tier_replay_drops_only_the_loadout_whose_plan_is_unplayable(monkeypatch) -> None:
    """A loadout whose plan no hit timing plays gets no FG result; the rest of the batch is served."""
    from types import SimpleNamespace

    from gear_optimizer.solver.fg_response_scoring import fixed_timing, reducer
    from gear_optimizer.solver.fg_response_scoring.note_graph import UnplayableTrace
    from gear_optimizer.solver.scoring import exact_rescore

    results = [SimpleNamespace(surface=f"surface-{i}", stats={}) for i in range(3)]
    monkeypatch.setattr(fixed_timing, "_solve_fixed_timing_response_results", lambda *a, **k: results)
    monkeypatch.setattr(exact_rescore, "score_base_exact_batch", lambda rows, song, curves: [1] * len(rows))

    def materialize(*, result, **_kwargs):
        if result is results[1]:
            raise UnplayableTrace("order decided by the frame timing")
        return {"Score": 7}

    monkeypatch.setattr(reducer, "materialize_force_payload_from_response_frontier", materialize)
    song = SimpleNamespace(chart=SimpleNamespace(name="Test Song"))
    monkeypatch.setattr(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys.fg_response_frontier_bundle_cache_key",
        lambda song, curves: ("bundle",),
    )
    replays = fixed_timing.build_fixed_timing_fg_replays(
        fg_stats_list=[{}, {}, {}], base_stats_list=[{}, {}, {}], song=song, curves=None, selected_color="Rush"
    )
    assert [replay["force"] for replay in replays] == [{"Score": 7}, None, {"Score": 7}]
