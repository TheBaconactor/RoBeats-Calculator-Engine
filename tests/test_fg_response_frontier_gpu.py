from tests.curves_support import synthetic_curves
from pathlib import Path

import numpy as np
import pytest
from tests.songs_support import make_song

pytestmark = pytest.mark.gpu
ROOT = Path(__file__).resolve().parents[1]


def _curves():
    # The first 161 entries (stat values 0..160) of 1001-point ramps.
    size = 1001
    return synthetic_curves({
        "Perfect Points": np.linspace(0.0, 2.0, size, dtype=np.float32)[:161],
        "Combo Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32)[:161],
        "Fever Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32)[:161],
    })


def _prepare_and_score_sync(
    *,
    base_stats_list,
    song,
    curves,
    selected_color,
    total_budget: int,
):
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier as rf
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import load_response_frontier_scoring_bundle
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys

    bundle = load_response_frontier_scoring_bundle(song, curves, stat_keys=all_response_stat_keys())
    return rf.fg_solve_results(base_stats_list, song=song, curves=curves, selected_color=selected_color,
                               scoring_bundle=bundle, total_budget=int(total_budget))


def _solve_one_batch(
    *,
    base_stats,
    song,
    curves,
    selected_color,
    total_budget: int,
):
    results = _prepare_and_score_sync(
        base_stats_list=[base_stats],
        song=song,
        curves=curves,
        selected_color=selected_color,
        total_budget=int(total_budget),
    )
    if not results:
        raise ValueError("response frontier exact GPU batch produced no pair result")
    return results[0]


def _prebuild_response_bundle(song, curves, base_stats_list, *, total_budget: int) -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import build_or_load_response_frontier_payload
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import reset_fg_response_frontier_payload_cache

    _ = base_stats_list, total_budget
    reset_fg_response_frontier_payload_cache()
    full_stat_grid = tuple((ft, ff) for ft in range(MAX_STAT + 1) for ff in range(MAX_STAT + 1))
    build_or_load_response_frontier_payload(song, curves, stat_keys=full_stat_grid)


def _replay_response_result_through_input_engine(*, song, final_stats, selected_color, result):
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        force_greats_note_graph,
        reconcile_force_greats_note_graph,
    )
    from gear_optimizer.solver.taichi_gem.force_greats import reconstruct_force_greats_response_trace
    from tools.verify.game_sim import IntendedNote, NoteChart, presses_from_intended, simulate

    song_inputs = song.fg_inputs
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=int(result.frontier.non_fever_base),
        target_surface=result.surface,
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        lanes=song_inputs.lanes,
        raw_fever_fill=float(result.raw_fever_fill),
        real_fever_time=float(result.real_fever_time),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )

    ts = song.chart.timestamps
    note_types = song.chart.note_types
    lanes = song.chart.lanes
    total_notes = int(len(ts))
    graph = force_greats_note_graph(
        frontier_trace=trace,
        total_notes=total_notes,
        timestamps=ts,
        note_types=note_types,
        lanes=lanes,
        timing_mode="precise",
    )
    surface = tuple(map(int, result.surface))
    reconcile_force_greats_note_graph(
        graph,
        total_notes=total_notes,
        fever_words=list(surface[0:4]),
        great_words=list(surface[4:8]),
        body_fever=surface[8],
        body_great=surface[9],
        body_fever_great=surface[10],
    )

    chart = NoteChart(
        timestamps_ms=[float(value) * 1000.0 for value in ts.tolist()],
        lanes=[int(value) for value in lanes.tolist()],
        note_types=[int(value) for value in note_types.tolist()],
    )
    intended = [
        IntendedNote(
            note_index=int(node["note_index"]),
            hit_time_ms=float(node["hit_time_ms"]),
            result="great" if node["note_result"] == "Great" else "perfect",
            note_type=int(note_types[int(node["note_index"])]),
            lane=int(lanes[int(node["note_index"])]),
            delta_ms=(float(node["delta_ms"]) if node.get("delta_ms") is not None else None),
        )
        for node in graph
    ]
    statsdict = {
        "PerfectPoints": final_stats["Perfect Points"],
        "ComboMultiplier": final_stats["Combo Multiplier"],
        "FeverMultiplier": final_stats["Fever Multiplier"],
        "FeverTime": final_stats["Fever Time"],
        "FeverFillRate": final_stats["Fever Fill Rate"],
        "ColorBlue": final_stats[selected_color],
    }
    taps = int((note_types == 1).sum())
    heads = int((note_types == 2).sum())
    last_note_time_ms = song.chart.last_note_time * 1000.0
    config = {
        "hitCount": total_notes,
        "hitObjectsCount": taps + heads,
        "lastNoteTimeSec": (last_note_time_ms + 1000.0) / 1000.0,
    }
    presses = presses_from_intended(chart, intended)
    assert song_inputs.primary_color == selected_color
    assert song_inputs.secondary_color == selected_color
    return simulate(
        chart,
        statsdict,
        ["ColorBlue"],
        presses,
        config,
        frame_dt_ms=1000.0 / 60.0,
    )


def test_response_frontier_best_score_matches_exact_replay_final_score(tmp_path, monkeypatch):
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact

    rows = 161
    curves = synthetic_curves({
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    })
    timestamps = np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32)
    song = make_song(timestamps, mode="non-precise")
    base_stats = {
        "Perfect Points": 1,
        "Combo Multiplier": 2,
        "Fever Multiplier": 3,
        "Fever Fill Rate": 1,
        "Fever Time": 2,
        "Rush": 20,
        "Flow": 15,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(song, curves, [base_stats], total_budget=3)
    result = _solve_one_batch(
        base_stats=base_stats,
        song=song,
        curves=curves,
        selected_color="Rush",
        total_budget=3,
    )
    exact_score = score_force_greats_response_surface_exact(result.stats, song, curves, result.surface)

    assert int(exact_score) == int(result.best_score)


def test_all_right_there_current_duration_fixed_cell_replays_bit_exact(tmp_path, monkeypatch):
    """Pin the current event-time fever duration, not the retired extra-1/60 duration."""
    from gear_optimizer.chart import load_chart
    from gear_optimizer.gamedata import load_stat_curves
    from gear_optimizer.solver.timing_envelope import time_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        load_response_frontier_scoring_bundle,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import fg_solve_results

    song = time_song(load_chart(ROOT / "Data" / "Hard" / "All Right There (Hard) by BSlick feat CG5.txt"), "precise")
    curves = load_stat_curves(ROOT / "Data" / "Gear" / "Stats.txt")
    final_stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 55,
        "Fever Multiplier": 70,
        "Fever Time": 43,
        "Fever Fill Rate": 58,
        "Beat": 34,
        "Vibe": 768,
        "Rush": 35,
        "Flow": 0,
        "Chill": 100,
    }
    stat_key = (final_stats["Fever Time"], final_stats["Fever Fill Rate"])

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    build_or_load_response_frontier_payload(song, curves, stat_keys=(stat_key,))
    scoring_bundle = load_response_frontier_scoring_bundle(song, curves, stat_keys=(stat_key,))

    result = fg_solve_results([final_stats], song=song, curves=curves, selected_color="Vibe",
                              scoring_bundle=scoring_bundle, total_budget=0)[0]

    assert int(result.best_score) == 29_340_273
    assert tuple(map(int, result.surface)) == (0, 0, 0, 0, 0, 0, 0, 0, 835, 6, 6)
    replay = _replay_response_result_through_input_engine(
        song=song,
        final_stats=final_stats,
        selected_color="Vibe",
        result=result,
    )
    assert int(replay.score) == int(result.best_score)
    assert replay.tally == {"perfect": 1042, "great": 6, "okay": 0, "miss": 0}
    assert int(replay.max_combo) == 1048


def test_response_frontier_many_matches_individual_exact_solves(tmp_path, monkeypatch):
    rows = 161
    curves = synthetic_curves({
        "Perfect Points": np.linspace(0.0, 5.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.6, dtype=np.float64),
        "Fever Time": np.full(rows, 0.4, dtype=np.float64),
    })
    timestamps = np.asarray([0.0, 0.3, 0.7, 1.4, 2.2, 3.0, 3.2, 3.4, 4.0], dtype=np.float32)
    song = make_song(timestamps, mode="non-precise")
    base_a = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 20,
        "Flow": 15,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    base_b = {**base_a, "Rush": 25, "Flow": 10, "Combo Multiplier": 3}

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(song, curves, [base_a, base_b], total_budget=3)
    many = _prepare_and_score_sync(
        base_stats_list=[base_a, base_b],
        song=song,
        curves=curves,
        selected_color="Rush",
        total_budget=3,
    )
    singles = [
        _solve_one_batch(
            base_stats=base,
            song=song,
            curves=curves,
            selected_color="Rush",
            total_budget=3,
        )
        for base in (base_a, base_b)
    ]

    assert [
        (result.best_score, result.ft, result.ff, result.gem_counts, result.forced_counts)
        for result in many
    ] == [
        (result.best_score, result.ft, result.ff, result.gem_counts, result.forced_counts)
        for result in singles
    ]


def test_aurora_served_fixed_cell_beats_phantom_and_replays_bit_exact(tmp_path, monkeypatch):
    """Aurora (Hard) by Creo, served #1 loadout cell (FT=55, FF=58) -- the motivating over-report.

    The served DB row carried 47,476,966, which the input engine cannot play (chord-activation
    phantom). The input-engine-aware producer instead finds the HIGHER legal 47,502,676: a
    12-Great prefix run, a late-Great activation centered within its complete score-parity window,
    the same-time sibling bundled Great, and the cross-lane chord partners delayed within their
    Perfect windows so the activation's own fill crosses the fever bar. The materialized witness must
    replay BIT-EXACT through the faithful input-engine simulator (earliest-hittable-first
    matching, +200ms despawn, frame-granular fever) -- exact == physical is the definitive gate
    for every surface this producer emits.
    """
    from gear_optimizer.chart import load_chart
    from gear_optimizer.gamedata import load_stat_curves
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        load_response_frontier_scoring_bundle,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import fg_solve_results
    from gear_optimizer.solver.timing_envelope import time_song

    song = time_song(load_chart(ROOT / "Data" / "Hard" / "Aurora (Hard) by Creo.txt"), "precise")
    curves = load_stat_curves(ROOT / "Data" / "Gear" / "Stats.txt")
    final_stats = {
        "Perfect Points": 29,
        "Combo Multiplier": 57,
        "Fever Multiplier": 68,
        "Fever Time": 55,
        "Fever Fill Rate": 58,
        "Beat": 35,
        "Vibe": 36,
        "Rush": 62,
        "Flow": 16,
        "Chill": 754,
    }
    stat_key = (final_stats["Fever Time"], final_stats["Fever Fill Rate"])

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    build_or_load_response_frontier_payload(song, curves, stat_keys=(stat_key,))
    scoring_bundle = load_response_frontier_scoring_bundle(song, curves, stat_keys=(stat_key,))
    result = fg_solve_results([final_stats], song=song, curves=curves, selected_color="Chill",
                              scoring_bundle=scoring_bundle, total_budget=0)[0]

    assert int(result.best_score) == 47_502_676  # legal max; > the unreachable served 47,476,966
    assert tuple(map(int, result.surface)) == (0, 0, 0, 0, 4095, 0, 0, 0, 1361, 5, 5)

    replay = _replay_response_result_through_input_engine(
        song=song,
        final_stats=final_stats,
        selected_color="Chill",
        result=result,
    )

    assert int(replay.score) == 47_502_676  # physical == exact, full combo, no okays/misses
    assert replay.tally == {"perfect": 1692, "great": 17, "okay": 0, "miss": 0}
    assert int(replay.max_combo) == 1709
