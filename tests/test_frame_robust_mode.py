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
from gear_optimizer.rules import FEVER_FILL_PER_NOTE, MAX_STAT
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_song_cache_key
from gear_optimizer.solver.timing_envelope import (
    FRAME_MARGIN_MS,
    HELD_TAIL_WINDOW_SCALE,
    fever_fill_is_order_sensitive,
    fever_fill_raw,
    fever_window_times,
    judgment_bounds,
    precise_envelopes,
    time_song,
)

REPO = Path(__file__).resolve().parents[1]


def test_bands_end_one_frame_margin_earlier() -> None:
    # (earliest, latest) planned offsets in ms: (Perfect, early Great, late Great) for a tap and a held tail.
    assert judgment_bounds(1, "precise") == ((-19, 40), (-94, -20), (41, 190))
    assert judgment_bounds(HELD_TAIL_WINDOW_SCALE, "precise") == ((-39, 80), (-189, -40), (81, 200))
    assert judgment_bounds(1, "frame_robust") == ((-19, 22), (-94, -38), (41, 172))
    assert judgment_bounds(HELD_TAIL_WINDOW_SCALE, "frame_robust") == ((-39, 62), (-189, -58), (81, 182))
    for scale in (1, HELD_TAIL_WINDOW_SCALE):
        bounds = judgment_bounds(scale, "frame_robust")
        # Differently judged presses of one chart time are never within a frame of each other.
        assert bounds.early_great.latest + FRAME_MARGIN_MS < bounds.perfect.earliest
        assert bounds.perfect.latest + FRAME_MARGIN_MS < bounds.late_great.earliest


def test_fever_windows_end_one_frame_margin_early() -> None:
    factors = np.asarray([0.0, 0.5, 1.0, 1.7], dtype=np.float32)
    real = fever_window_times(120.0, factors, "precise")
    assert np.array_equal(real, (120.0 * 0.15 + 0.15) * factors.astype(np.float64))
    assert np.array_equal(fever_window_times(120.0, factors, "frame_robust"), np.maximum(real - FRAME_MARGIN_MS / 1000.0, 0.0))


def test_song_has_its_own_envelopes_and_cache_identity() -> None:
    chart = load_chart(REPO / "Data" / "Normal" / "Surface by Dimrain47.txt")
    window, robust = time_song(chart, "precise"), time_song(chart, "frame_robust")
    assert robust.mode == "frame_robust"
    tail = chart.note_types == 3
    latest_perfect_ms = np.rint((robust.perfect_candidates.astype(np.float64) - chart.timestamps) * 1000.0)
    assert set(latest_perfect_ms[~tail].tolist()) <= {22.0} and set(latest_perfect_ms[tail].tolist()) <= {62.0}
    assert np.all(robust.perfect_floor >= window.perfect_floor)  # same-lane spacing may delay an early hit
    assert robust.timeline_key != window.timeline_key
    assert fg_response_frontier_song_cache_key(robust) != fg_response_frontier_song_cache_key(window)


def test_late_great_floor_starts_at_the_band() -> None:
    # precise plans a late Great from 1 ms past its latest Perfect. frame_robust's latest Perfect ends a margin
    # early and a hit in between is Perfect or Great by the frame, so its late Greats start at the band itself.
    ts = np.asarray([1.0, 2.0, 3.0], dtype=np.float32)
    types = np.asarray([1, 3, 2], dtype=np.int16)
    window, robust = precise_envelopes(ts, types), precise_envelopes(ts, types, "frame_robust", lanes=np.arange(len(ts)))
    assert np.array_equal(window.late_great_floor, window.perfect_candidates + np.float32(0.001))
    assert np.rint((robust.late_great_floor.astype(np.float64) - ts) * 1000.0).tolist() == [41.0, 81.0, 41.0]


def test_exit_ceiling_keeps_out_notes_past_the_fever_at_every_frame() -> None:
    # A fever may end before notes charted inside it if those notes are hit at or past its end. precise's
    # ceiling is the latest Perfect of a note and every later one; frame_robust's is a full exit gap (2 margins)
    # earlier, since a note is out at every frame timing only from the end + the margin and the end itself moves by a
    # margin.
    ts = np.asarray([1.0, 2.0, 2.0, 3.0], dtype=np.float32)
    types = np.asarray([1, 3, 1, 2], dtype=np.int16)
    window, robust = precise_envelopes(ts, types), precise_envelopes(ts, types, "frame_robust", lanes=np.arange(len(ts)))
    assert np.array_equal(window.exit_ceiling, np.minimum.accumulate(window.perfect_candidates[::-1])[::-1])
    target = np.minimum.accumulate(
        (robust.perfect_candidates.astype(np.float64) - 2.0 * FRAME_MARGIN_MS / 1000.0)[::-1]
    )[::-1]
    assert np.all(robust.exit_ceiling.astype(np.float64) <= target)  # rounded down to float32
    assert np.all(np.nextafter(robust.exit_ceiling, np.float32(np.inf)).astype(np.float64) > target)
    # Every note can still be in a fever that ends at its ceiling: the reachable ends of an activation form one run.
    assert np.all(robust.exit_ceiling[1:] > robust.perfect_floor[:-1])


def test_fill_curve_is_the_games() -> None:
    from gear_optimizer.solver.timing_envelope import _game_fever_fill_factor
    from tools.verify import game_sim

    for points in range(MAX_STAT + 1):
        assert _game_fever_fill_factor(points) == game_sim._fN(0.6, 0.5, 0.333, 0.166, 0.1, points), points


def test_fever_fill_counts_perfects_as_the_game_does() -> None:
    # T6: at Fever Fill 80 the game's denominator is hit objects x 0.1 exactly; 280 x (1 / 28) sums to one ulp under 1, so
    # the game needs 29 Perfects where the exported (truncated) factor gives 28.
    from gear_optimizer.gamedata import load_stat_curves

    factors = load_stat_curves(REPO / "Data" / "Gear" / "Stats.txt").f32["Fever Fill Rate"]
    window = fever_fill_raw(280, factors, "precise")
    assert np.array_equal(window, 280 * FEVER_FILL_PER_NOTE * factors.astype(np.float64))
    robust = fever_fill_raw(280, factors, "frame_robust")
    assert int(np.ceil(robust[80])) == 29 and fever_fill_is_order_sensitive(float(robust[80]))
    assert int(np.ceil(robust[79])) == 29 and not fever_fill_is_order_sensitive(float(robust[79]))
    # A curve that no longer matches Stats.txt fails loudly instead of forking the two.
    with pytest.raises(ValueError, match="no longer matches"):
        fever_fill_raw(280, factors * np.float32(1.01), "frame_robust")


def test_late_great_activation_is_never_planned_in_the_frame_judged_gap() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_build_prefix_activation_hit_tables,
    )

    # A Perfect 10 ms after the activation must come after it: the activation's latest hit is that Perfect's latest
    # (+32 ms here under frame_robust), short of the late-Great band (+41), so no late-Great activation exists.
    ts = np.asarray([1.0, 1.010], dtype=np.float32)
    types = np.asarray([1, 1], dtype=np.int16)
    for mode, late_valid in (("precise", 1), ("frame_robust", 0)):
        env = precise_envelopes(ts, types, mode, lanes=np.arange(len(ts)))
        _hit, _valid, late_hit, valid = _numba_build_prefix_activation_hit_tables(
            2, ts, env.perfect_candidates, env.great_candidates, env.late_great_floor, env.lane_bounds
        )
        assert int(valid[0]) == late_valid, mode
        if late_valid:
            assert late_hit[0] >= env.late_great_floor[0]


def _base_plans(chart, mode: str, ft: int, ff: int, *, early_exits: bool = True):
    """The producer's Base plans for one FT/FF cell, as validated note graphs (without early fever exits: no note's
    exit ceiling reaches any fever end)."""
    from gear_optimizer.gamedata import load_stat_curves
    from gear_optimizer.solver.fg_response_scoring.note_graph import timeline_frontier_note_graph
    from gear_optimizer.solver.fg_response_scoring.physical_replay import validate_base_physical_replay
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from gear_optimizer.solver.timeline_exact_frontier import reconstruct_timeline_physical_trace

    curves = load_stat_curves(REPO / "Data" / "Gear" / "Stats.txt")
    song = time_song(chart, mode)
    fi = song.fg_inputs
    exit_ceiling = fi.exit_ceiling if early_exits else np.full_like(fi.exit_ceiling, -np.inf)
    n = int(chart.total_notes)
    raw_fill = float(fever_fill_raw(max(0, n - chart.long_notes), curves.f32["Fever Fill Rate"], mode)[ff])
    fill = max(1, int(np.ceil(raw_fill)))
    window_time = float(fever_window_times(chart.last_note_time, curves.f32["Fever Time"], mode)[ft])
    (frontier,) = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=fi.timestamps, perfect_candidate_timestamps=fi.perfect_candidates,
        great_candidate_timestamps=fi.perfect_candidates, perfect_floor_timestamps=fi.perfect_floor,
        great_floor_timestamps=fi.perfect_floor, lanes=fi.lanes, geometries=((float(fill), 0, window_time),),
        use_forced_great_timing=False, exit_ceiling_timestamps=exit_ceiling, lane_bounds=fi.lane_bounds,
    )
    graphs = []
    for row in frontier.first_frontier:
        words = (int(row.fever0), int(row.fever1), int(row.fever2), int(row.fever3))
        trace = reconstruct_timeline_physical_trace(
            head_bits=words, body_fever=int(row.body_fever), timestamps=fi.timestamps,
            perfect_candidate_timestamps=fi.perfect_candidates, great_candidate_timestamps=fi.great_candidates,
            perfect_floor_timestamps=fi.perfect_floor, great_floor_timestamps=fi.great_floor, lanes=fi.lanes,
            raw_fever_fill=raw_fill, real_fever_time=window_time, exit_ceiling_timestamps=exit_ceiling, lane_bounds=fi.lane_bounds,
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
    """Surface's FT/FF 0 precise plan claims a fever note frames decide (found by T1); frame_robust's plans
    keep their claimed fever set at every phase and rate."""
    chart = load_chart(REPO / "Data" / "Normal" / "Surface by Dimrain47.txt")
    assert (chart.primary, chart.secondary) == ("Vibe", "Beat")
    window_sets = [_fever_sets_per_frame_timing(chart, g, 0, 0) for g in _base_plans(chart, "precise", 0, 0)]
    assert any(len(sets) > 1 for sets in window_sets)
    for graph in _base_plans(chart, "frame_robust", 0, 0):
        claimed = tuple(i for i, node in enumerate(graph) if node["fever"])
        assert _fever_sets_per_frame_timing(chart, graph, 0, 0) == {claimed}


@pytest.mark.slow
def test_early_fever_exits_hold_at_every_frame_timing() -> None:
    """A fever that ends early lets the next one start sooner: [@_@]'s FT/FF 40 Frame-Safe plans gain fever sets that
    only an early exit reaches (a note hit past the fever's end that could have been inside it), and every plan keeps
    its claimed fever set at every phase and rate."""
    chart = load_chart(REPO / "Data" / "Easy" / "[@_@] (Easy) by Chroma.txt")

    def fever_sets(graphs):
        return {tuple(i for i, node in enumerate(graph) if node["fever"]) for graph in graphs}

    graphs = _base_plans(chart, "frame_robust", 40, 40)
    assert fever_sets(graphs) - fever_sets(_base_plans(chart, "frame_robust", 40, 40, early_exits=False))
    for graph in graphs:
        claimed = tuple(i for i, node in enumerate(graph) if node["fever"])
        assert _fever_sets_per_frame_timing(chart, graph, 40, 40) == {claimed}


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


def _synthetic_play(extra_preactivation_ms: float | None):
    """130 single-lane-alternating notes 100 ms apart; a late-Great activation at note 110 tied with its Perfect
    follower 111 (another lane); fever over 110..115, the rest a margin past the end."""
    n = 130
    notes = []
    for j in range(n):
        notes.append({"note_index": j, "hit_time_ms": 1000.0 + 100.0 * j, "delta_ms": 0.0, "note_result": "Perfect",
                      "fever": 110 <= j <= 115, "input_order": j})
    notes[110]["note_result"] = "Great"
    notes[110]["delta_ms"] = 100.0  # tied with note 111's press
    lanes = np.asarray([j % 4 for j in range(n)], dtype=np.int32)
    lanes[110], lanes[111] = 1, 2
    if extra_preactivation_ms is not None:
        notes[109]["delta_ms"] = 200.0 - extra_preactivation_ms  # pressed just before the tie, on lane 1 != 2
        lanes[109] = 3
    trace = [{"activation_index": 110, "fever_duration_ms": 450.0}]
    return notes, trace, np.ones(n, dtype=np.int16), lanes


def test_late_great_activation_follower_may_share_its_frame() -> None:
    from gear_optimizer.solver.fg_response_scoring.note_graph import _require_frame_robust_play

    notes, trace, note_types, lanes = _synthetic_play(None)
    _require_frame_robust_play(notes, frontier_trace=trace, note_types=note_types, lanes=lanes)


def test_follower_with_an_earlier_input_in_its_frame_is_order_sensitive() -> None:
    from gear_optimizer.solver.fg_response_scoring.note_graph import UnplayableTrace, _require_frame_robust_play

    notes, trace, note_types, lanes = _synthetic_play(5.0)
    with pytest.raises(UnplayableTrace, match="order changes the score"):
        _require_frame_robust_play(notes, frontier_trace=trace, note_types=note_types, lanes=lanes)
