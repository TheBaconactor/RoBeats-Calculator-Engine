from types import SimpleNamespace

from gear_optimizer.gamedata import stat_curves

from tests.curves_support import synthetic_curves
from tests.native_song_factory import make_native_song
from tests.songs_support import make_chart, make_song

import pytest
import numpy as np

from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row


def _engine_envelopes(timestamps):
    from gear_optimizer.solver.timing_envelope import precise_envelopes

    ts = np.asarray(timestamps, dtype=np.float32)
    env = precise_envelopes(ts, np.ones(int(ts.shape[0]), dtype=np.int16))
    return env.perfect_candidates, env.great_candidates, env.perfect_floor, env.great_floor


def _trace_row(forced_count: int) -> dict[str, object]:
    return {
        "forced_count": int(forced_count),
        "activation_index": 0,
        "activation_judgment": "perfect",
        "forced_start_index": 0,
        "forced_run_start_index": 0,
        "forced_run_count": 0,
        "activation_hit_window_upper_ms": 0.0,
    }


def _minimal_fg_song(note_count: int = 4):
    return make_song(np.linspace(0.0, 1.0, int(note_count)), mode="non-precise")


def _stub_song(note_count: int):
    """A song reduced to what the FG planner/reducer read: its timing mode, FG inputs and chart note types."""
    ts = [float(i) for i in range(int(note_count))]
    return SimpleNamespace(
        mode="precise",
        fg_inputs=SimpleNamespace(
            total_notes=int(note_count),
            long_notes=0,
            timestamps=ts,
            perfect_candidates=ts,
            great_candidates=ts,
            perfect_floor=ts,
            great_floor=ts,
            late_great_floor=None,
            exit_ceiling=None,
            lanes=list(range(int(note_count))),
            use_forced_great_timing=True,
        ),
        chart=SimpleNamespace(note_types=[1] * int(note_count)),
    )


def _minimal_fg_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.rules import MAX_STAT

    return synthetic_curves({
        "Perfect Points": np.linspace(1.0, 2.0, MAX_STAT + 1, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, MAX_STAT + 1, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, MAX_STAT + 1, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.0, MAX_STAT + 1, dtype=np.float32) * 0.15,
        "Fever Fill Rate": np.linspace(1.0, 2.0, MAX_STAT + 1, dtype=np.float32) * 0.333,
    })


def _all_stats(**stats: int) -> dict[str, int]:
    from gear_optimizer.gamedata import STATS

    return {**{s: 0 for s in STATS}, **stats}


def test_ftff_response_position_prune_matches_pair_prune_with_canonical_frontier_keys():
    from tests.parity.response_ftff_prune import (
        prune_dominated_ftff_response_pairs,
        prune_dominated_ftff_response_positions,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult

    frontiers = tuple(FgResponseFrontierResult((), {}, 0, 0, 0, 0, 0, 0, 0, 0.0) for _ in range(4))
    frontier_classes = (0, 0, 1, 2)
    class_by_frontier_id = {id(frontier): int(frontier_classes[idx]) for idx, frontier in enumerate(frontiers)}
    rows = [
        (0, 5, 10, 10),
        (1, 6, 9, 10),
        (1, 6, 11, 10),
        (2, 2, 5, 5),
        (2, 4, 5, 5),
        (3, 7, 12, 8),
        (3, 6, 8, 12),
        (3, 5, 7, 7),
    ]
    pairs = [
        (
            int(idx),
            0,
            int(residual),
            (0, 0, 0, int(primary), int(secondary), 0, 0),
            frontiers[int(frontier_idx)],
            0.0,
            0.0,
        )
        for idx, (frontier_idx, residual, primary, secondary) in enumerate(rows)
    ]

    expected = prune_dominated_ftff_response_pairs(
        pairs,
        primary_color="Beat",
        secondary_color="Vibe",
        frontier_key_of=lambda pair: class_by_frontier_id[id(pair[4])],
    )
    positions = np.arange(len(rows), dtype=np.int32)
    got = prune_dominated_ftff_response_positions(
        positions=positions,
        frontier_ids=np.asarray([frontier_classes[frontier_idx] for frontier_idx, *_rest in rows], dtype=np.int32),
        residuals=np.asarray([residual for _frontier_idx, residual, _primary, _secondary in rows], dtype=np.int32),
        primary_values=np.asarray([primary for _frontier_idx, _residual, primary, _secondary in rows], dtype=np.int32),
        secondary_values=np.asarray(
            [secondary for _frontier_idx, _residual, _primary, secondary in rows], dtype=np.int32
        ),
    )

    assert got.tolist() == [int(pair[0]) for pair in expected]


def test_ftff_response_position_prune_matches_bruteforce_randomized():
    from tests.parity.response_ftff_prune import (
        prune_dominated_ftff_response_positions,
    )

    rng = np.random.default_rng(20260531)
    for row_count in (1, 2, 8, 32, 96):
        for _case in range(20):
            positions = np.arange(row_count, dtype=np.int32)
            frontier_ids = rng.integers(0, max(1, row_count // 3), size=row_count, dtype=np.int32)
            residuals = rng.integers(0, 12, size=row_count, dtype=np.int32)
            primary_values = rng.integers(0, 16, size=row_count, dtype=np.int32)
            secondary_values = rng.integers(0, 16, size=row_count, dtype=np.int32)
            got = prune_dominated_ftff_response_positions(
                positions=positions,
                frontier_ids=frontier_ids,
                residuals=residuals,
                primary_values=primary_values,
                secondary_values=secondary_values,
            )

            expected: list[int] = []
            for frontier in dict.fromkeys(int(v) for v in frontier_ids.tolist()):
                bucket = [idx for idx, value in enumerate(frontier_ids.tolist()) if int(value) == int(frontier)]
                for idx in bucket:
                    dominated = False
                    for other in bucket:
                        if other == idx:
                            continue
                        if (
                            int(residuals[other]) >= int(residuals[idx])
                            and int(primary_values[other]) >= int(primary_values[idx])
                            and int(secondary_values[other]) >= int(secondary_values[idx])
                            and (
                                int(residuals[other]) > int(residuals[idx])
                                or int(primary_values[other]) > int(primary_values[idx])
                                or int(secondary_values[other]) > int(secondary_values[idx])
                                or int(other) < int(idx)
                            )
                        ):
                            dominated = True
                            break
                    if not dominated:
                        expected.append(int(idx))

            assert got.tolist() == expected


def test_force_payload_trace_cache_reuses_the_validated_trace(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.solver.fg_response_scoring.reducer import (
        FgTraceMaterializationCache,
        materialize_force_payload_from_response_frontier,
    )
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    scoring_frontier = FgResponseFrontierResult((surface,), {}, 1, 1, 1, 1, 1, 1, 7, 0.0)
    result = FgResponseFrontierSolveResult(
        best_score=1234,
        ft=1,
        ff=2,
        gem_counts={"Perfect Points": 0},
        stats={"Fever Time": 12, "Fever Fill Rate": 34},
        surface=surface,
        frontier=scoring_frontier,
        inner=FgResponseInnerResult(1234, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        seconds=0.0,
        forced_counts=(),
        raw_fever_fill=1.0,
        real_fever_time=2.0,
    )
    seen = {"reconstruct_calls": 0, "validate_calls": 0}

    def _fake_reconstruct_trace(**kwargs):
        seen["reconstruct_calls"] += 1
        seen["non_fever_base"] = kwargs["non_fever_base"]
        return (_trace_row(1), _trace_row(0), _trace_row(1))

    monkeypatch.setattr(reducer_mod, "reconstruct_force_greats_response_trace", _fake_reconstruct_trace)
    monkeypatch.setattr(
        reducer_mod,
        "_assert_trace_hit_time_reachable",
        lambda *_args, **_kwargs: seen.__setitem__("validate_calls", seen["validate_calls"] + 1),
    )
    monkeypatch.setattr(
        reducer_mod,
        "validate_force_greats_physical_replay",
        lambda **_kwargs: seen.__setitem__("physical_calls", seen.get("physical_calls", 0) + 1),
    )
    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 1230)

    trace_cache = FgTraceMaterializationCache()
    song = _stub_song(1)
    payload = materialize_force_payload_from_response_frontier(
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        song=song,
        curves=stat_curves(),
        trace_cache=trace_cache,
    )
    second_payload = materialize_force_payload_from_response_frontier(
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        song=song,
        curves=stat_curves(),
        trace_cache=trace_cache,
    )

    assert seen["non_fever_base"] == scoring_frontier.non_fever_base
    assert payload["BaseScore"] == 1000
    assert [row["forced_count"] for row in payload["ForceGreats"]["frontier_trace"]] == [1, 0, 1]
    assert payload["Score"] == 1230
    assert payload["ForceGreats"]["final_score"] == 1230
    assert payload["ForceGreats"]["frontier_states"] == 1
    assert payload["ForceGreats"]["non_fever_base"] == 7
    assert second_payload["ForceGreats"]["frontier_trace"] == payload["ForceGreats"]["frontier_trace"]
    assert seen["reconstruct_calls"] == 1
    assert seen["validate_calls"] == 1
    assert seen["physical_calls"] == 1
    with pytest.raises(ValueError, match="cannot be reused across song owners"):
        materialize_force_payload_from_response_frontier(
            base_stats={"Perfect Points": 1},
            paired_base_score=1000,
            selected_element="Rush",
            result=result,
            song=_stub_song(1),
            curves=stat_curves(),
            trace_cache=trace_cache,
        )


def test_force_payload_reconstructs_counts_without_state_frontiers(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.solver.fg_response_scoring.reducer import materialize_force_payload_from_response_frontier
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    result = FgResponseFrontierSolveResult(
        best_score=1234,
        ft=1,
        ff=2,
        gem_counts={"Perfect Points": 0},
        stats={"Fever Time": 12, "Fever Fill Rate": 34},
        surface=surface,
        frontier=FgResponseFrontierResult((surface,), {}, 1, 1, 1, 1, 1, 1, 7, 0.0),
        inner=FgResponseInnerResult(1234, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        seconds=0.0,
        forced_counts=(),
        raw_fever_fill=1.0,
        real_fever_time=2.0,
    )

    monkeypatch.setattr(
        reducer_mod,
        "reconstruct_force_greats_response_trace",
        lambda **_kwargs: (_trace_row(1), _trace_row(0), _trace_row(1)),
    )
    monkeypatch.setattr(
        reducer_mod,
        "validate_force_greats_physical_replay",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(reducer_mod, "_assert_trace_hit_time_reachable", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 1230)

    payload = materialize_force_payload_from_response_frontier(
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        song=_stub_song(1),
        curves=stat_curves(),
    )

    assert payload["BaseScore"] == 1000
    assert [row["forced_count"] for row in payload["ForceGreats"]["frontier_trace"]] == [1, 0, 1]
    assert payload["Score"] == 1230


def test_force_payload_emits_compact_trace_from_slim_frontier(monkeypatch):
    from gear_optimizer.solver.fg_response_scoring.reducer import materialize_force_payload_from_response_frontier
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table
    from tests.fg_response_frontier_oracles import edge_surface_option_details
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
    )

    timestamps = np.asarray([0.0, 0.18, 0.41, 0.64, 0.95, 1.21, 1.5], dtype=np.float32)
    perfect_candidates, great_candidates, perfect_floor, great_floor = _engine_envelopes(timestamps)
    raw_fever_fill = 2.25
    non_fever_base = 7
    real_fever_time = 0.55
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=non_fever_base,
        use_forced_great_timing=True,
    )
    target_option = next(
        row
        for row in edge_surface_option_details(
            i=0,
            first=True,
            n=int(timestamps.shape[0]),
            actions=actions,
            later_fill=later_fill,
            first_fill=first_fill,
            later_forced=later_forced,
            first_forced=first_forced,
            real_fever_time=real_fever_time,
        use_forced_great_timing=True,
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
            lanes=np.arange(int(timestamps.shape[0]), dtype=np.int32),
            raw_fever_fill=raw_fever_fill,
        )
        if row["activation_judgment"] == "late_great"
    )
    surface = target_option["surface"]
    frontier = FgResponseFrontierResult(
        first_frontier=(surface,),
        state_frontiers={},
        states_evaluated=1,
        actions=len(actions),
        transitions_evaluated=1,
        generated_surfaces=1,
        retained_surfaces_total=1,
        max_state_frontier=1,
        non_fever_base=non_fever_base,
        seconds=0.0,
    )
    result = FgResponseFrontierSolveResult(
        best_score=4321,
        ft=1,
        ff=2,
        gem_counts={"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
        stats={"Perfect Points": 1, "Rush": 10, "Fever Time": 3, "Fever Fill Rate": 4},
        surface=surface,
        frontier=frontier,
        inner=FgResponseInnerResult(4321, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
        seconds=0.0,
        forced_counts=(),
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
    )
    from gear_optimizer.solver.timing_envelope import TimedSong

    chart = make_chart(timestamps)
    song = TimedSong(
        chart=chart,
        mode="precise",
        baseline_hash="",
        hit_timestamps=chart.timestamps,
        perfect_candidates=perfect_candidates,
        perfect_floor=perfect_floor,
        great_floor=great_floor,
        great_candidates=great_candidates,
    )

    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 4321)

    payload = materialize_force_payload_from_response_frontier(
        base_stats={"Perfect Points": 1, "Rush": 9},
        paired_base_score=4000,
        selected_element="Rush",
        result=result,
        song=song,
        curves=stat_curves(),
    )

    assert payload["BaseScore"] == 4000
    trace = payload["ForceGreats"]["frontier_trace"]
    assert not frontier.state_frontiers
    assert [row["forced_count"] for row in trace] == [int(target_option["k"])]
    assert len(trace) == 1
    assert trace[0]["activation_judgment"] == "late_great"
    assert trace[0]["activation_index"] == int(target_option["activation_index"])
    assert trace[0]["activation_hit_ms"] == pytest.approx(float(target_option["activation_hit_ms"]))
    assert trace[0]["activation_hit_offset_ms"] == pytest.approx(float(target_option["activation_hit_offset_ms"]))
    assert trace[0]["fever_end_index"] == int(target_option["fever_end_index"])
    assert trace[0]["forced_count"] == int(target_option["k"])


def test_response_frontier_prunes_duplicate_constant_ftff_frontiers_by_best_residual():
    from tests.parity.response_ftff_prune import prune_best_positions_by_frontier

    positions = np.asarray([0, 1, 2, 3], dtype=np.int32)
    frontier_ids = np.asarray([5, 5, 7, 5], dtype=np.int32)
    residuals = np.asarray([1, 3, 2, 2], dtype=np.int32)

    kept_positions = prune_best_positions_by_frontier(
        positions=positions,
        frontier_ids=frontier_ids,
        residuals=residuals,
    )

    np.testing.assert_array_equal(kept_positions, np.asarray([1, 2], dtype=np.int32))


def test_response_frontier_best_position_prune_matches_sort_reference_randomized():
    from tests.parity.response_ftff_prune import prune_best_positions_by_frontier

    rng = np.random.default_rng(20260531)
    for row_count in (1, 2, 8, 64, 512):
        for _case in range(20):
            positions = np.arange(row_count, dtype=np.int32)
            frontier_ids = rng.integers(0, max(1, row_count // 2), size=row_count, dtype=np.int32)
            residuals = rng.integers(0, 100, size=row_count, dtype=np.int32)
            got = prune_best_positions_by_frontier(
                positions=positions,
                frontier_ids=frontier_ids,
                residuals=residuals,
            )

            expected: list[int] = []
            for frontier in dict.fromkeys(int(v) for v in frontier_ids.tolist()):
                bucket = [idx for idx, value in enumerate(frontier_ids.tolist()) if int(value) == int(frontier)]
                best = max(bucket, key=lambda idx: (int(residuals[idx]), -int(positions[idx])))
                expected.append(int(positions[best]))
            np.testing.assert_array_equal(got, np.asarray(expected, dtype=np.int32))


def test_response_frontier_group_builder_matches_prune_reference():
    from gear_optimizer.rules import MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER
    from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
    from gear_optimizer.solver.taichi_gem.force_greats.response_gem_search import build_response_group_rows
    from tests.fg_group_build_reference import build_response_group_rows_reference

    ft_values, ff_values, residual_values = ftff_combo_arrays(3)
    base_components = np.asarray(
        [
            [1, 2, 3, 10, 20, 0, 0],
            [4, 5, 6, 13, 17, 2, 1],
            [7, 8, 9, 11, 23, 4, 3],
        ],
        dtype=np.int32,
    )
    frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    for base in base_components:
        for ft, ff in zip(ft_values, ff_values, strict=True):
            ft_stat = int(np.clip(int(base[5]) + int(ft) * STAT_GEM_GAIN_FEVER, 0, MAX_STAT))
            ff_stat = int(np.clip(int(base[6]) + int(ff) * STAT_GEM_GAIN_FEVER, 0, MAX_STAT))
            frontier_idx_by_stat[ft_stat, ff_stat] = int((ft_stat // STAT_GEM_GAIN_FEVER + ff_stat // STAT_GEM_GAIN_FEVER) % 3)

    cases = (
        (np.zeros_like(ft_values, dtype=np.int32), np.zeros_like(ff_values, dtype=np.int32), True),
        (
            np.asarray(ft_values * STAT_GEM_ELEMENT_GAIN, dtype=np.int32),
            np.asarray(ff_values * STAT_GEM_ELEMENT_GAIN, dtype=np.int32),
            False,
        ),
    )
    for primary_delta, secondary_delta, constant in cases:
        args = (
            base_components,
            np.ascontiguousarray(ft_values, dtype=np.int32),
            np.ascontiguousarray(ff_values, dtype=np.int32),
            np.ascontiguousarray(residual_values, dtype=np.int32),
            np.ascontiguousarray(frontier_idx_by_stat, dtype=np.int32),
            np.ascontiguousarray(primary_delta, dtype=np.int32),
            np.ascontiguousarray(secondary_delta, dtype=np.int32),
            constant,
            4,
            9,
        )
        got = build_response_group_rows(*args)
        expected = build_response_group_rows_reference(*args)
        for got_arr, expected_arr in zip(got, expected, strict=True):
            np.testing.assert_array_equal(got_arr, expected_arr)


def test_response_frontier_ftff_antichain_prunes_only_same_pack_dominance():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )
    from tests.parity.response_ftff_prune import (
        prune_dominated_ftff_response_pairs,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def frontier():
        return FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )

    pack_a = frontier()
    pack_b = frontier()
    dominated_same_pack = (1, 2, 10, {"Rush": 50, "Flow": 20}, pack_a, 0.0, 0.0)
    dominator_same_pack = (0, 2, 11, {"Rush": 50, "Flow": 21}, pack_a, 0.0, 0.0)
    same_stats_other_pack = (1, 2, 10, {"Rush": 50, "Flow": 20}, pack_b, 0.0, 0.0)

    kept = prune_dominated_ftff_response_pairs(
        [dominated_same_pack, dominator_same_pack, same_stats_other_pack],
        primary_color="Rush",
        secondary_color="Flow",
    )

    assert any(pair is dominator_same_pack for pair in kept)
    assert any(pair is same_stats_other_pack for pair in kept)
    assert not any(pair is dominated_same_pack for pair in kept)


def test_response_frontier_ftff_antichain_matches_naive_dominance():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )
    from tests.parity.response_ftff_prune import (
        prune_dominated_ftff_response_pairs,
        response_pair_dominates,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def frontier():
        return FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )

    pack_a = frontier()
    pack_b = frontier()
    pairs = []
    for frontier_obj in (pack_a, pack_b):
        for residual in (7, 8, 9):
            for rush in (10, 12, 12):
                for flow in (4, 5, 7):
                    pairs.append((0, 0, residual, {"Rush": rush, "Flow": flow}, frontier_obj, 0.0, 0.0))

    naive = []
    for pair in pairs:
        if any(response_pair_dominates(other, pair, primary_color="Rush", secondary_color="Flow") for other in naive):
            continue
        naive = [
            other
            for other in naive
            if not response_pair_dominates(pair, other, primary_color="Rush", secondary_color="Flow")
        ]
        naive.append(pair)

    kept = prune_dominated_ftff_response_pairs(pairs, primary_color="Rush", secondary_color="Flow")

    assert kept == naive

