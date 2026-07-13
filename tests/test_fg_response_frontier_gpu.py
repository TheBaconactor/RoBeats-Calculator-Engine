from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.gpu
ROOT = Path(__file__).resolve().parents[1]


def _ref_arrays():
    size = 1001
    return {
        "Perfect Points": np.linspace(0.0, 2.0, size, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32),
    }


def _prepare_and_score_sync(
    *,
    base_stats_list,
    calc_song,
    ref_arrays,
    selected_color,
    total_budget: int,
    include_forced_counts: bool = True,
):
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier as rf

    batch = rf.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=base_stats_list,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        total_budget=int(total_budget),
    )
    return rf.score_prepared_force_greats_response_frontier_batch_sync(
        batch,
        include_forced_counts=bool(include_forced_counts),
    )


def _solve_one_batch(
    *,
    base_stats,
    calc_song,
    ref_arrays,
    selected_color,
    total_budget: int,
    include_forced_counts: bool = True,
):
    results = _prepare_and_score_sync(
        base_stats_list=[base_stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        total_budget=int(total_budget),
        include_forced_counts=bool(include_forced_counts),
    )
    if not results:
        raise ValueError("response frontier exact GPU batch produced no pair result")
    return results[0]


def _prebuild_response_bundle(calc_song, ref_arrays, base_stats_list, *, total_budget: int) -> None:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )

    _ = base_stats_list, total_budget
    reset_fg_response_frontier_payload_cache()
    full_stat_grid = tuple((ft, ff) for ft in range(TOTAL_ROWS + 1) for ff in range(TOTAL_ROWS + 1))
    build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=full_stat_grid)


def _replay_response_result_through_input_engine(*, calc_song, final_stats, selected_color, result):
    from gear_optimizer.solver.fg_response_scoring.note_graph import (
        force_greats_note_graph,
        reconcile_force_greats_note_graph,
    )
    from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
    from gear_optimizer.solver.taichi_gem.force_greats import reconstruct_force_greats_response_trace
    from tools.verify.game_sim import IntendedNote, NoteChart, presses_from_intended, simulate

    song_inputs = extract_fg_song_inputs(calc_song)
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

    song_data = calc_song["song_data"]
    meta = calc_song["metadata"]
    ts = np.asarray(song_data["timestamps"])
    note_types = np.asarray(song_data["note_types"])
    lanes = np.asarray(song_data["lanes"])
    total_notes = int(len(ts))
    graph = force_greats_note_graph(
        frontier_trace=trace,
        total_notes=total_notes,
        timestamps=ts,
        note_types=note_types,
        lanes=lanes,
        timing_mode="perfect_window",
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
    last_note_time_ms = float(meta.get("Last Note Time", ts[-1] * 1000.0))
    if last_note_time_ms < 1000.0:
        last_note_time_ms = float(meta["Last Note Time"]) * 1000.0
    config = {
        "hitCount": total_notes,
        "hitObjectsCount": taps + heads,
        "lastNoteTimeSec": (last_note_time_ms + 1000.0) / 1000.0,
    }
    presses = presses_from_intended(chart, intended)
    return simulate(chart, statsdict, ["ColorBlue"], presses, config, frame_dt_ms=1000.0 / 60.0)


def test_ftff_projection_matches_canonical_stats_for_consumed_fields():
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import _stats_after_ftff_for_inner

    def _score_elements(stats: dict, primary: str, secondary: str) -> tuple[int, int]:
        return (
            int(stats.get(primary, 0) or 0),
            int(stats.get(secondary, 0) or 0),
        )

    base_stats = {
        "Perfect Points": 11,
        "Combo Multiplier": 22,
        "Fever Multiplier": 33,
        "Fever Fill Rate": 44,
        "Fever Time": 55,
        "Chill": 1,
        "Flow": 2,
        "Rush": 3,
        "Beat": 4,
        "Vibe": 5,
    }
    colors = ("Chill", "Flow", "Rush", "Beat", "Vibe")

    for primary in colors:
        for secondary in colors:
            projected = _stats_after_ftff_for_inner(
                base_stats,
                ft=7,
                ff=9,
                primary_color=primary,
                secondary_color=secondary,
            )
            canonical = apply_gems_to_base_stats(base_stats, "Chill", 7, 9, 0, 0, 0, 0)

            for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"):
                assert projected[key] == canonical[key]
            assert _score_elements(projected, primary, secondary) == _score_elements(canonical, primary, secondary)


def test_response_frontier_gpu_inner_matches_reference_inner_with_overlap():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from tests.parity.fg_response_frontier_cpu import optimize_response_frontier_inner_exact_gpu

    surfaces = (
        FgResponseSurface(0b111, 0, 0, 0, 0b001, 0, 0, 0, 2, 1),
        FgResponseSurface(0b011, 0, 0, 0, 0b000, 0, 0, 0, 1, 0),
    )
    kwargs = {
        "total_notes": 105,
        "residual_budget": 3,
        "stats_after_ftff": {
            "Perfect Points": 10,
            "Combo Multiplier": 20,
            "Fever Multiplier": 30,
            "Power": 40,
            "Rush": 50,
        },
        "primary_color": "Power",
        "secondary_color": "Rush",
        "selected_color": "Power",
        "ref_arrays": _ref_arrays(),
    }

    gpu = optimize_response_frontier_inner_exact_gpu(surfaces, **kwargs)

    assert (
        gpu.best_score,
        gpu.surface_index,
        gpu.g_pp,
        gpu.g_cm,
        gpu.g_fm,
        gpu.g_ov,
        gpu.final_pp,
        gpu.final_cm,
        gpu.final_fm,
        gpu.final_primary,
        gpu.final_secondary,
    ) == (17593, 0, 0, 0, 0, 3, 10, 20, 30, 58, 50)


def test_response_frontier_gpu_inner_scores_same_color_greats_as_single_color():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from tests.parity.fg_response_frontier_cpu import optimize_response_frontier_inner_exact_gpu

    surfaces = (FgResponseSurface(0, 0, 0, 0, 0b1111, 0, 0, 0, 0, 0),)
    kwargs = {
        "total_notes": 4,
        "residual_budget": 0,
        "stats_after_ftff": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Chill": 812,
        },
        "primary_color": "Chill",
        "secondary_color": "Chill",
        "selected_color": "Chill",
        "ref_arrays": _ref_arrays(),
    }

    gpu = optimize_response_frontier_inner_exact_gpu(surfaces, **kwargs)

    assert gpu.best_score == 4 * 1774
    assert (
        gpu.surface_index,
        gpu.g_pp,
        gpu.g_cm,
        gpu.g_fm,
        gpu.g_ov,
        gpu.final_pp,
        gpu.final_cm,
        gpu.final_fm,
        gpu.final_primary,
        gpu.final_secondary,
    ) == (0, 0, 0, 0, 0, 0, 0, 0, 812, 812)


def test_response_frontier_gpu_batch_pack_matches_reference_groups():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _optimize_response_surfaces_gpu

    surfaces_a = (
        FgResponseSurface(0b1111, 0, 0, 0, 0b0010, 0, 0, 0, 4, 1),
        FgResponseSurface(0b0111, 0, 0, 0, 0b0000, 0, 0, 0, 2, 0),
        FgResponseSurface(0b1110, 0, 0, 0, 0b0100, 0, 0, 0, 5, 2),
    )
    surfaces_b = (
        FgResponseSurface(0b101, 0, 0, 0, 0b001, 0, 0, 0, 1, 1),
        FgResponseSurface(0b111, 0, 0, 0, 0b011, 0, 0, 0, 3, 2),
    )
    shared = {
        "total_notes": 108,
        "primary_color": "Power",
        "secondary_color": "Rush",
        "selected_color": "Power",
        "ref_arrays": _ref_arrays(),
    }
    stats_a = {
        "Perfect Points": 10,
        "Combo Multiplier": 20,
        "Fever Multiplier": 30,
        "Power": 40,
        "Rush": 50,
    }
    stats_b = {
        "Perfect Points": 30,
        "Combo Multiplier": 15,
        "Fever Multiplier": 25,
        "Power": 20,
        "Rush": 80,
    }

    rows, surface_rows = _optimize_response_surfaces_gpu(
        [(5, stats_a, surfaces_a), (4, stats_b, surfaces_b), (3, stats_b, surfaces_a)],
        **shared,
    )

    assert surface_rows == len(surfaces_a) + len(surfaces_b) + len(surfaces_a)
    assert rows == [
        (20734, 2, 0, 0, 0, 5, 10, 20, 30, 70, 50),
        (18271, 1, 0, 0, 0, 4, 30, 15, 25, 44, 80),
        (16974, 2, 0, 0, 0, 3, 30, 15, 25, 38, 80),
    ]


def test_response_frontier_gpu_preserves_exact_best_on_high_surface_mixed_colors_regression():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from tests.parity.fg_response_frontier_cpu import optimize_response_frontier_inner_exact_gpu

    surfaces = (
        FgResponseSurface(3891411679, 3574856976, 3773757219, 1, 403555616, 720110319, 521210076, 14, 51, 5),
        FgResponseSurface(2721674337, 3070680269, 3611881923, 14, 0, 0, 327680, 0, 122, 2),
        FgResponseSurface(575176664, 3487862049, 3702577455, 12, 3719790631, 807105246, 592389840, 3, 84, 36),
        FgResponseSurface(3601089371, 3643850265, 2374545082, 10, 555465764, 642335206, 1920422149, 4, 109, 6),
        FgResponseSurface(2790863878, 2438334081, 1839177138, 4, 0, 0, 1, 0, 111, 3),
        FgResponseSurface(2245692434, 3544458849, 2717638093, 9, 405078720, 605573150, 1308631090, 0, 63, 27),
        FgResponseSurface(3466214601, 779693237, 2435483384, 1, 828752694, 3515274058, 1859483911, 14, 49, 82),
        FgResponseSurface(1358034363, 3210050518, 977655363, 13, 621019648, 524296, 77072408, 2, 67, 21),
        FgResponseSurface(27450701, 2000810147, 1294574002, 1, 168362000, 132612, 538069060, 2, 116, 12),
        FgResponseSurface(1302787120, 1853818885, 106666315, 9, 537461380, 2415952130, 279568, 6, 121, 3),
        FgResponseSurface(912726739, 3089068564, 3279260528, 5, 3382240556, 1205898731, 1015706767, 10, 3, 119),
    )
    kwargs = {
        "total_notes": 232,
        "residual_budget": 23,
        "stats_after_ftff": {
            "Perfect Points": 138,
            "Combo Multiplier": 14,
            "Fever Multiplier": 195,
            "Power": 269,
            "Rush": 266,
            "Flow": 13,
            "Beat": 111,
            "Vibe": 299,
            "Chill": 294,
        },
        "primary_color": "Vibe",
        "secondary_color": "Chill",
        "selected_color": "Beat",
        "ref_arrays": _ref_arrays(),
    }

    gpu = optimize_response_frontier_inner_exact_gpu(surfaces, **kwargs)

    assert gpu.best_score == 246965
    assert (gpu.surface_index, gpu.g_pp, gpu.g_cm, gpu.g_fm, gpu.g_ov) == (1, 11, 12, 0, 0)
    assert (gpu.final_pp, gpu.final_cm, gpu.final_fm, gpu.final_primary, gpu.final_secondary) == (
        160,
        38,
        195,
        299,
        327,
    )


def test_response_frontier_gpu_inner_matches_exact_replay_on_combo_floor_boundary():
    from pathlib import Path

    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from tests.parity.fg_response_frontier_cpu import optimize_response_frontier_inner_exact_gpu

    refs = build_ref_arrays_from_stats(
        read_table(str(Path.cwd() / "Data" / "Gear" / "Stats.txt")),
        dtype=np.float64,
    )
    surface = FgResponseSurface(0, 0, 0, 0, 255, 0, 0, 0, 1255, 2, 2)
    stats = {
        "Perfect Points": 80,
        "Combo Multiplier": 80,
        "Fever Multiplier": 80,
        "Fever Time": 51,
        "Fever Fill Rate": 67,
        "Beat": 80,
        "Vibe": 80,
    }
    calc_song = {
        "metadata": {"Primary Color": "Beat", "Secondary Color": "Vibe", "Long Notes": 0, "Last Note Time": 1585.0},
        "song_data": {"timestamps": tuple(range(1586)), "fg_timestamps": tuple(range(1586))},
    }

    gpu = optimize_response_frontier_inner_exact_gpu(
        (surface,),
        total_notes=1586,
        residual_budget=0,
        stats_after_ftff=stats,
        primary_color="Beat",
        secondary_color="Vibe",
        selected_color="Beat",
        ref_arrays=refs,
    )
    exact = score_force_greats_response_surface_exact(stats, calc_song, refs, surface)

    assert gpu.best_score == exact == 12345033
    assert (gpu.surface_index, gpu.g_pp, gpu.g_cm, gpu.g_fm, gpu.g_ov) == (0, 0, 0, 0, 0)


def _strip_trailing_zero_counts(counts):
    out = tuple(int(v) for v in counts)
    while out and out[-1] == 0:
        out = out[:-1]
    return out


def test_response_frontier_exact_uses_natural_forced_great_cap_above_legacy_cap(tmp_path, monkeypatch):
    from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact

    rows = 161
    ref_arrays = {
        "Perfect Points": np.zeros(rows, dtype=np.float64),
        "Combo Multiplier": np.full(rows, 2.0, dtype=np.float64),
        "Fever Multiplier": np.full(rows, 4.0, dtype=np.float64),
        "Fever Fill Rate": np.ones(rows, dtype=np.float64),
        "Fever Time": np.ones(rows, dtype=np.float64),
    }
    timestamps = np.asarray(
        list(np.arange(28, dtype=float)) + [50.0 + i * 0.1 for i in range(32)],
        dtype=np.float32,
    )
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 10,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }

    baseline = evaluate_force_greats_exact(base_stats, calc_song, ref_arrays, [0, 0])
    legacy_cap_best = max(
        int(evaluate_force_greats_exact(base_stats, calc_song, ref_arrays, [forced, 0])["final_score"])
        for forced in range(16)
    )
    natural_best = int(evaluate_force_greats_exact(base_stats, calc_song, ref_arrays, [17, 0])["final_score"])

    assert baseline["non_fever_base"] == 20
    assert natural_best > legacy_cap_best

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_stats], total_budget=0)
    result = _solve_one_batch(
        base_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=0,
    )

    assert result.best_score == natural_best
    assert _strip_trailing_zero_counts(result.forced_counts) == (17,)


def test_response_frontier_exact_reoptimizes_gems_against_bruteforce_reference(tmp_path, monkeypatch):
    import itertools

    from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    }
    timestamps = np.asarray(
        [0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6, 5.0, 5.1, 5.2],
        dtype=np.float32,
    )
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_stats = {
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
    selected_color = "Chill"
    budget = 4

    best_score = -1
    best_gems = None
    best_counts = ()
    for ft in range(budget + 1):
        for ff in range(budget - ft + 1):
            for pp in range(budget - ft - ff + 1):
                for cm in range(budget - ft - ff - pp + 1):
                    for fm in range(budget - ft - ff - pp - cm + 1):
                        ov = budget - ft - ff - pp - cm - fm
                        stats = apply_gems_to_base_stats(base_stats, selected_color, ft, ff, pp, cm, fm, ov)
                        zero = evaluate_force_greats_exact(stats, calc_song, ref_arrays, [0] * 10)
                        sections = int(zero["num_non_fever_sections"])
                        cap = int(zero["non_fever_base"])
                        for counts in itertools.product(range(cap + 1), repeat=sections):
                            score = int(evaluate_force_greats_exact(stats, calc_song, ref_arrays, counts)["final_score"])
                            if score > best_score:
                                best_score = score
                                best_gems = (ft, ff, pp, cm, fm, ov)
                                best_counts = counts

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_stats], total_budget=budget)
    result = _solve_one_batch(
        base_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        total_budget=budget,
    )

    assert result.best_score == best_score
    assert (result.ft, result.ff, result.inner.g_pp, result.inner.g_cm, result.inner.g_fm, result.inner.g_ov) == best_gems
    assert result.inner.g_fm == budget
    assert _strip_trailing_zero_counts(result.forced_counts) == _strip_trailing_zero_counts(best_counts)


def test_response_frontier_best_score_matches_exact_replay_final_score(tmp_path, monkeypatch):
    from gear_optimizer.solver.scoring.exact_rescore import (
        score_force_greats_response_surface_exact,
        score_force_greats_surface_base_exact,
    )

    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    }
    timestamps = np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
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
    _prebuild_response_bundle(calc_song, ref_arrays, [base_stats], total_budget=3)
    result = _solve_one_batch(
        base_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=3,
    )
    exact_score = score_force_greats_response_surface_exact(result.stats, calc_song, ref_arrays, result.surface)
    base_score = score_force_greats_surface_base_exact(result.stats, calc_song, ref_arrays, result.surface)

    assert int(exact_score) == int(result.best_score)
    assert int(base_score) >= int(result.best_score)


def test_all_right_there_current_duration_fixed_cell_replays_bit_exact(tmp_path, monkeypatch):
    """Pin the current event-time fever duration, not the retired extra-1/60 duration."""
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        load_response_frontier_scoring_bundle,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        prepare_force_greats_response_frontier_scoring_batch,
        score_prepared_force_greats_response_frontier_batch_cpu_sync,
    )

    calc_song = get_base_calc_song(str(ROOT / "Data" / "Hard" / "All Right There (Hard) by BSlick feat CG5.txt"), {})
    apply_timing_envelope(calc_song, mode="perfect_window")
    ref_arrays = build_ref_arrays_from_stats(read_table(str(ROOT / "Data" / "Gear" / "Stats.txt")), dtype=np.float64)
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
    build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=(stat_key,))
    scoring_bundle = load_response_frontier_scoring_bundle(calc_song, ref_arrays, stat_keys=(stat_key,))
    batch = prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=[final_stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Vibe",
        total_budget=0,
        scoring_bundle=scoring_bundle,
    )

    result = score_prepared_force_greats_response_frontier_batch_cpu_sync(
        batch,
        include_forced_counts=True,
    )[0]

    assert int(result.best_score) == 29_340_273
    assert tuple(map(int, result.surface)) == (0, 0, 0, 0, 0, 0, 0, 0, 835, 6, 6)
    assert tuple(result.forced_counts) == (0, 3)
    replay = _replay_response_result_through_input_engine(
        calc_song=calc_song,
        final_stats=final_stats,
        selected_color="Vibe",
        result=result,
    )
    assert int(replay.score) == int(result.best_score)
    assert replay.tally == {"perfect": 1042, "great": 6, "okay": 0, "miss": 0}
    assert int(replay.max_combo) == 1048


def test_response_frontier_many_matches_individual_exact_solves(tmp_path, monkeypatch):
    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 5.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.6, dtype=np.float64),
        "Fever Time": np.full(rows, 0.4, dtype=np.float64),
    }
    timestamps = np.asarray([0.0, 0.3, 0.7, 1.4, 2.2, 3.0, 3.2, 3.4, 4.0], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
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
    _prebuild_response_bundle(calc_song, ref_arrays, [base_a, base_b], total_budget=3)
    many = _prepare_and_score_sync(
        base_stats_list=[base_a, base_b],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=3,
    )
    singles = [
        _solve_one_batch(
            base_stats=base,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
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


def test_response_frontier_many_fast_path_matches_individual_exact_solves_with_ft_element_overlap(tmp_path, monkeypatch):
    import itertools

    from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 5.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.6, dtype=np.float64),
        "Fever Time": np.full(rows, 0.4, dtype=np.float64),
    }
    timestamps = np.asarray([0.0, 0.3, 0.7, 1.4, 2.2, 3.0, 3.2, 3.4, 4.0], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_a = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 0,
        "Flow": 15,
        "Chill": 0,
        "Beat": 20,
        "Vibe": 0,
    }
    base_b = {**base_a, "Beat": 23, "Flow": 12, "Combo Multiplier": 3}

    budget = 3

    def brute_best_score(base_stats):
        best = -1
        for ft in range(budget + 1):
            for ff in range(budget - ft + 1):
                for pp in range(budget - ft - ff + 1):
                    for cm in range(budget - ft - ff - pp + 1):
                        for fm in range(budget - ft - ff - pp - cm + 1):
                            ov = budget - ft - ff - pp - cm - fm
                            stats = apply_gems_to_base_stats(base_stats, "Rush", ft, ff, pp, cm, fm, ov)
                            zero = evaluate_force_greats_exact(stats, calc_song, ref_arrays, [0] * 10)
                            sections = int(zero["num_non_fever_sections"])
                            cap = int(zero["non_fever_base"])
                            for counts in itertools.product(range(cap + 1), repeat=sections):
                                score = int(evaluate_force_greats_exact(stats, calc_song, ref_arrays, counts)["final_score"])
                                if score > best:
                                    best = score
        return int(best)

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_a, base_b], total_budget=budget)
    results = _prepare_and_score_sync(
        base_stats_list=[base_a, base_b],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=budget,
        include_forced_counts=False,
    )

    assert [result.best_score for result in results] == [brute_best_score(base) for base in (base_a, base_b)]


def test_aurora_served_fixed_cell_beats_phantom_and_replays_bit_exact(tmp_path, monkeypatch):
    """Aurora (Hard) by Creo, served #1 loadout cell (FT=55, FF=58) -- the motivating over-report.

    The served DB row carried 47,476,966, which the input engine cannot play (chord-activation
    phantom). The input-engine-aware producer instead finds the HIGHER legal 47,502,676: a
    12-Great prefix run, a late-Great activation at its capped upper edge, the same-time sibling
    bundled Great, and the cross-lane chord partners at +163ms delayed within their Perfect
    windows so the activation's own fill crosses the fever bar. The materialized witness must
    replay BIT-EXACT through the faithful input-engine simulator (earliest-hittable-first
    matching, +200ms despawn, frame-granular fever) -- exact == physical is the definitive gate
    for every surface this producer emits.
    """
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        load_response_frontier_scoring_bundle,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        prepare_force_greats_response_frontier_scoring_batch,
        score_prepared_force_greats_response_frontier_batch_cpu_sync,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    calc_song = get_base_calc_song(str(ROOT / "Data" / "Hard" / "Aurora (Hard) by Creo.txt"), {})
    apply_timing_envelope(calc_song, mode="perfect_window")
    ref_arrays = build_ref_arrays_from_stats(read_table(str(ROOT / "Data" / "Gear" / "Stats.txt")), dtype=np.float64)
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
    build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=(stat_key,))
    scoring_bundle = load_response_frontier_scoring_bundle(calc_song, ref_arrays, stat_keys=(stat_key,))
    batch = prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=[final_stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Chill",
        total_budget=0,
        scoring_bundle=scoring_bundle,
    )
    result = score_prepared_force_greats_response_frontier_batch_cpu_sync(
        batch,
        include_forced_counts=True,
    )[0]

    assert int(result.best_score) == 47_502_676  # legal max; > the unreachable served 47,476,966
    assert tuple(map(int, result.surface)) == (0, 0, 0, 0, 4095, 0, 0, 0, 1361, 5, 5)
    assert tuple(result.forced_counts) == (13, 2)

    replay = _replay_response_result_through_input_engine(
        calc_song=calc_song,
        final_stats=final_stats,
        selected_color="Chill",
        result=result,
    )

    assert int(replay.score) == 47_502_676  # physical == exact, full combo, no okays/misses
    assert replay.tally == {"perfect": 1692, "great": 17, "okay": 0, "miss": 0}
    assert int(replay.max_combo) == 1709
