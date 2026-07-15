from tests.native_song_factory import make_native_song

import pytest
import numpy as np

from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row


def _engine_envelopes(timestamps):
    from gear_optimizer.solver.timing_envelope import (
        build_great_candidate_envelope_sec,
        build_great_floor_envelope_sec,
        build_perfect_candidate_envelope_sec,
        build_perfect_floor_envelope_sec,
    )

    ts = np.asarray(timestamps, dtype=np.float32)
    note_types = np.ones(int(ts.shape[0]), dtype=np.int16)
    return (
        build_perfect_candidate_envelope_sec(ts, note_types),
        build_great_candidate_envelope_sec(ts, note_types),
        build_perfect_floor_envelope_sec(ts, note_types),
        build_great_floor_envelope_sec(ts, note_types),
    )


def _trace_row(forced_count: int) -> dict[str, object]:
    return {
        "forced_count": int(forced_count),
        "activation_index": 0,
        "activation_judgment": "perfect",
        "forced_start_index": 0,
        "forced_prefix_count": 0,
        "activation_hit_window_upper_ms": 0.0,
    }


def _minimal_fg_calc_song(note_count: int = 4) -> dict:
    timestamps = np.linspace(0.0, 1.0, int(note_count), dtype=np.float32)
    return {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]) if int(timestamps.shape[0]) else 0.0,
        },
        "song_data": {
            "timestamps": timestamps,
            "fg_timestamps": timestamps,
            "lanes": list(range(len(timestamps))),
            "note_types": np.ones(len(timestamps), dtype=np.int16),
        },
    }


def _minimal_fg_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    return {
        "Perfect Points": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
    }


def _fake_fg_prepared_batch(base_stats_list, selected_color: str = "Rush"):
    from types import SimpleNamespace

    rows = [dict(base_stats) for base_stats in base_stats_list]
    base_components = np.asarray(
        [
            response_frontier_base_components_row(
                base_stats,
                None,
                primary_color="Rush",
                secondary_color="Flow",
            )
            for base_stats in rows
        ],
        dtype=np.int32,
    )
    return SimpleNamespace(
        base_stats_list=rows,
        selected_color=str(selected_color or ""),
        base_components=base_components,
    )


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


def test_fixed_stats_score_matches_independent_reference():
    """`evaluate_stats_score` (njit) matches an independent inline f32 replay.

    The reference re-derives the same fever timeline via the canonical
    `calculate_fever_timeline_indices` kernel and applies the same f32 ramp/body
    scoring, computed here independently from the scorer under test.
    """
    from gear_optimizer.core.ref_lookup import resolve_stat_factors
    from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score

    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 1,
            "Last Note Time": 1.5,
        },
        "song_data": {"timestamps": np.asarray([0.0, 0.25, 0.5, 1.0, 1.5], dtype=np.float32)},
    }
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }
    stats = {
        "Perfect Points": 37,
        "Combo Multiplier": 41,
        "Fever Multiplier": 59,
        "Fever Time": 23,
        "Fever Fill Rate": 29,
        "Rush": 101,
        "Flow": 83,
    }

    timestamps = calc_song["song_data"]["timestamps"]
    total_notes = int(len(timestamps))
    mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    factors = resolve_stat_factors(stats, ref_arrays)
    fever_mask_head, count_body_fever, count_body_normal, _, _ = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        float(factors.fever_fill_rate),
        float(factors.fever_time_stat),
        int(calc_song["metadata"]["Long Notes"]),
        float(calc_song["metadata"]["Last Note Time"]),
        mask_buffer,
    )
    total_base = (stats["Rush"] * 2) + stats["Flow"] + float(factors.pp_factor)
    base_f = np.float32(total_base)
    combo_f = np.float32(float(factors.combo_mul))
    fever_f = np.float32(float(factors.fever_mul))
    combo_val = int(base_f * combo_f)
    fever_val = int(base_f * combo_f * fever_f)
    reference = (int(count_body_fever) * fever_val) + (int(count_body_normal) * combo_val)
    factor = (combo_f - np.float32(1.0)) * base_f / np.float32(100.0)
    for idx, in_fever in enumerate(fever_mask_head):
        ramp = base_f + (np.float32(idx + 1) * factor)
        reference += int(ramp * fever_f) if bool(in_fever) else int(ramp)

    assert evaluate_stats_score(stats, calc_song, ref_arrays) == int(reference)


def test_prepare_fg_job_sync_plans_the_exact_base_surface(monkeypatch):
    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    seen = {}
    seen_bundle = object()

    def _fake_prepare_plan(song, candidates):
        seen["scoring_bundle"] = song.runtime.fg.fg_response_scoring_bundle
        seen["candidate_count"] = len(candidates or [])
        seen["registry"] = song.gpu_inputs.registry
        return "prepared-plan"

    monkeypatch.setattr(
        FgPlanner,
        "plan_prepared_base_candidates",
        staticmethod(_fake_prepare_plan),
    )

    song = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [1.0], "lanes": [0]}},
        cfg_dict={},
        base_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "LoadoutIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
    )
    song.runtime.fg.fg_response_scoring_bundle = seen_bundle

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert seen["candidate_count"] == 1
    assert seen["scoring_bundle"] is seen_bundle
    assert seen["registry"] is None
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"
    assert len(song.runtime.decode.base_candidates or []) == 1


def test_prepare_fg_job_sync_builds_plan_without_owner_build_prefetch(monkeypatch):
    # Fused Base-to-FG handoff: the GPU owner scores FG in the exact Base turn, so FG
    # prep only builds the plan -- it does NOT prefetch any owner BUILD/SCORE round
    # trip (the former prefetch_group_builds + finalize_prefetched_group_builds step is
    # deleted). A passed gpu_client is accepted but unused for scoring.
    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner
    from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService

    monkeypatch.setattr(
        FgPlanner,
        "plan_prepared_base_candidates",
        staticmethod(lambda *_args, **_kwargs: "raw-plan"),
    )

    # The owner BUILD/SCORE prefetch is deleted: these methods no longer exist.
    assert not hasattr(FgResponseScoringService, "prefetch_group_builds")
    assert not hasattr(FgResponseScoringService, "finalize_prefetched_group_builds")

    song = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [1.0], "lanes": [0]}},
        cfg_dict={},
        base_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "LoadoutIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=object())

    assert song.runtime.fg.fg_response_frontier_plan == "raw-plan"


def test_prepare_fg_job_sync_rejects_an_oversized_exact_base_surface(monkeypatch):
    import gear_optimizer.solver.native_inflight_pipeline as stages

    duplicate_prefix = [
        {
            "Score": 1000 - i,
            "BaseScore": 1000 - i,
            "Gear": ["DupG1", "DupG2", "DupG3", "DupG4", "DupG5", "DupG6"],
            "Minis": ["DupM1", "DupM2", "DupM3"],
            "Data": {"Selected Element": "Rush"},
        }
        for i in range(60)
    ]
    keeper = {
        "Score": 100,
        "BaseScore": 100,
        "Gear": ["KeepG1", "KeepG2", "KeepG3", "KeepG4", "KeepG5", "KeepG6"],
        "Minis": ["KeepM1", "KeepM2", "KeepM3"],
        "Data": {"Selected Element": "Rush"},
    }

    song = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [1.0], "lanes": [0]}},
        cfg_dict={},
        base_candidates=duplicate_prefix + [keeper],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={},
        song_slot=1,
    )

    with pytest.raises(RuntimeError, match="candidate surface exceeds the FG contract"):
        stages.prepare_fg_job_sync(song, gpu_client=None)


def test_prepare_fg_job_sync_preserves_the_ranked_exact_base_surface(monkeypatch):
    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    monkeypatch.setattr(
        FgPlanner,
        "plan_prepared_base_candidates",
        staticmethod(lambda *_args, **_kwargs: "prepared-plan"),
    )

    base_candidates = [
        {
            "Score": 1000 - i,
            "BaseScore": 1000 - i,
            "Gear": [f"G{i}_{slot}" for slot in range(6)],
            "Minis": [f"M{i}_{slot}" for slot in range(3)],
            "Data": {"Selected Element": "Rush"},
        }
        for i in range(51)
    ]

    song = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [1.0], "lanes": [0]}},
        cfg_dict={},
        base_candidates=base_candidates,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert len(song.runtime.decode.base_candidates or []) == 51
    assert [int(cand["BaseScore"]) for cand in song.runtime.decode.base_candidates or []] == list(range(1000, 949, -1))
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"


def test_prepare_fg_job_sync_requires_materialized_response_frontier_plan(monkeypatch):
    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    monkeypatch.setattr(
        FgPlanner,
        "plan_prepared_base_candidates",
        staticmethod(lambda *_args, **_kwargs: None),
    )

    song = make_native_song(
        calc_song={"metadata": {}, "song_data": {"timestamps": [1.0], "lanes": [0]}},
        cfg_dict={},
        base_candidates=[{"BaseScore": 100, "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
    )

    with pytest.raises(RuntimeError, match="did not materialize the exact response frontier plan"):
        stages.prepare_fg_job_sync(song, gpu_client=None)


def test_prepare_fg_static_sync_loads_and_session_prunes_canonical_scoring_bundle(monkeypatch):
    import configparser

    from types import SimpleNamespace

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache

    seen: dict[str, object] = {"session_prune": 0}
    canonical_keys = ((0, 0), (1, 1))
    bundle = SimpleNamespace(cache_key=("bundle-key",))

    def _fake_load_bundle(_calc_song, _ref_arrays, *, stat_keys):
        seen["stat_keys"] = tuple(stat_keys)
        return bundle

    monkeypatch.setattr(response_cache, "load_response_frontier_scoring_bundle", _fake_load_bundle)
    monkeypatch.setattr(response_cache, "all_response_stat_keys", lambda: canonical_keys)

    def _fake_session_prune(loaded_bundle, ref_arrays):
        assert loaded_bundle is bundle
        assert ref_arrays
        seen["session_prune"] = 1
        return loaded_bundle

    monkeypatch.setattr(response_cache, "session_prune_scoring_bundle", _fake_session_prune)

    cfg = configparser.ConfigParser()
    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {"timestamps": [1.0], "lanes": [0]}},
        cfg_dict={},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        ref_arrays={"Fever Time": object(), "Fever Fill Rate": object()},
    )

    stages.prepare_fg_static_sync(song)

    assert song.runtime.fg.fg_response_scoring_bundle is bundle
    assert song.runtime.fg.fg_static_prep_done is True
    assert seen == {"session_prune": 1, "stat_keys": canonical_keys}


def test_force_payload_uses_supplied_reconstruction_frontier_and_validated_trace_cache(monkeypatch):
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
    full_frontier = FgResponseFrontierResult((surface,), {0: (surface,)}, 9, 3, 17, 5, 8, 4, 11, 0.0)
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

    monkeypatch.setattr(
        reducer_mod,
        "extract_fg_song_inputs",
        lambda calc_song: SimpleNamespace(
            timestamps=[0.0],
            perfect_candidates=[0.0],
            great_candidates=[0.0],
            perfect_floor=[0.0],
            great_floor=[0.0],
            lanes=[0],
            use_forced_great_timing=True,
        ),
    )

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
    calc_song = {
        "metadata": {},
        "song_data": {"timestamps": [1.0], "lanes": [0], "note_types": [1]},
    }
    payload = materialize_force_payload_from_response_frontier(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        calc_song=calc_song,
        ref_arrays={},
        reconstruction_frontier=full_frontier,
        trace_cache=trace_cache,
    )
    second_payload = materialize_force_payload_from_response_frontier(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        calc_song=calc_song,
        ref_arrays={},
        reconstruction_frontier=full_frontier,
        trace_cache=trace_cache,
    )

    # The supplied reconstruction_frontier (non_fever_base=11) is honored over the scoring
    # frontier (non_fever_base=7): the trace primitive receives the override's non_fever_base.
    assert seen["non_fever_base"] == full_frontier.non_fever_base
    assert payload["BaseScore"] == 1000
    assert payload["forced_counts"] == [1, 0, 1]
    assert [row["forced_count"] for row in payload["ForceGreats"]["frontier_trace"]] == [1, 0, 1]
    assert payload["Score"] == 1230
    assert payload["ForceGreats"]["final_score"] == 1230
    assert payload["ForceGreats"]["frontier_states"] == 9
    assert payload["ForceGreats"]["non_fever_base"] == 11
    assert second_payload["ForceGreats"]["frontier_trace"] == payload["ForceGreats"]["frontier_trace"]
    assert seen["reconstruct_calls"] == 1
    assert seen["validate_calls"] == 1
    assert seen["physical_calls"] == 1
    with pytest.raises(ValueError, match="cannot be reused across calc-song owners"):
        materialize_force_payload_from_response_frontier(
            eval_data={"Selected Element": "Rush"},
            base_stats={"Perfect Points": 1},
            paired_base_score=1000,
            selected_element="Rush",
            result=result,
            calc_song=dict(calc_song),
            ref_arrays={},
            reconstruction_frontier=full_frontier,
            trace_cache=trace_cache,
        )

    # Missing lanes is a supported chart-ingest boundary that materializes a fresh fallback tuple
    # on every extraction. Cache ownership is the strong calc-song object, not that transient tuple.
    missing_lanes_song = {
        "metadata": {},
        "song_data": {"timestamps": [1.0], "note_types": [1]},
    }
    missing_lanes_cache = FgTraceMaterializationCache()
    missing_lane_payloads = [
        materialize_force_payload_from_response_frontier(
            eval_data={"Selected Element": "Rush"},
            base_stats={"Perfect Points": 1},
            paired_base_score=1000,
            selected_element="Rush",
            result=result,
            calc_song=missing_lanes_song,
            ref_arrays={},
            reconstruction_frontier=full_frontier,
            trace_cache=missing_lanes_cache,
        )
        for _ in range(2)
    ]
    assert missing_lane_payloads[0]["ForceGreats"]["frontier_trace"] == missing_lane_payloads[1]["ForceGreats"][
        "frontier_trace"
    ]


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
        "extract_fg_song_inputs",
        lambda calc_song: SimpleNamespace(
            total_notes=1,
            timestamps=[0.0],
            perfect_candidates=[0.0],
            great_candidates=[0.0],
            perfect_floor=[0.0],
            great_floor=[0.0],
            lanes=[0],
            use_forced_great_timing=True,
        ),
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
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        calc_song={
            "metadata": {},
            "song_data": {"timestamps": [1.0], "lanes": [0], "note_types": [1]},
        },
        ref_arrays={},
    )

    assert payload["BaseScore"] == 1000
    assert payload["forced_counts"] == [1, 0, 1]
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
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {
            "timestamps": timestamps,
            "fg_timestamps": timestamps,
            "fg_perfect_candidate_timestamps": perfect_candidates,
            "fg_perfect_floor_timestamps": perfect_floor,
            "fg_great_floor_timestamps": great_floor,
            "fg_great_candidate_timestamps": great_candidates,
            "lanes": np.arange(int(timestamps.shape[0]), dtype=np.int32),
            "note_types": np.ones(int(timestamps.shape[0]), dtype=np.int16),
        },
    }

    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 4321)

    payload = materialize_force_payload_from_response_frontier(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1, "Rush": 9},
        paired_base_score=4000,
        selected_element="Rush",
        result=result,
        calc_song=calc_song,
        ref_arrays={},
    )

    assert payload["BaseScore"] == 4000
    trace = payload["ForceGreats"]["frontier_trace"]
    assert not frontier.state_frontiers
    assert payload["forced_counts"] == [int(target_option["k"])]
    assert payload["ForceGreats"]["config"] == {"NonFever1": int(target_option["k"]), "NonFever2": 0}
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


@pytest.mark.gpu
def test_response_frontier_gpu_group_builder_matches_prune_reference():
    from gear_optimizer.core.constants import GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, TOTAL_ROWS
    from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
    from gear_optimizer.solver.taichi_gem.force_greats.response_group_build_kernels import (
        build_response_group_rows_gpu,
    )
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
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for base in base_components:
        for ft, ff in zip(ft_values, ff_values, strict=True):
            ft_stat = int(np.clip(int(base[5]) + int(ft) * GEM_SCALE_FEVER, 0, TOTAL_ROWS))
            ff_stat = int(np.clip(int(base[6]) + int(ff) * GEM_SCALE_FEVER, 0, TOTAL_ROWS))
            frontier_idx_by_stat[ft_stat, ff_stat] = int((ft_stat // GEM_SCALE_FEVER + ff_stat // GEM_SCALE_FEVER) % 3)

    cases = (
        (np.zeros_like(ft_values, dtype=np.int32), np.zeros_like(ff_values, dtype=np.int32), True),
        (
            np.asarray(ft_values * GEM_STAT_TO_ELEMENT_SCALE, dtype=np.int32),
            np.asarray(ff_values * GEM_STAT_TO_ELEMENT_SCALE, dtype=np.int32),
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
        got = build_response_group_rows_gpu(*args)
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


def test_fg_response_scoring_uses_authoritative_paired_base_for_emit_gate(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod

    monkeypatch.setattr(
        reducer_mod,
        "materialize_force_payload_from_response_frontier",
        lambda **kwargs: {
            "BaseScore": kwargs["result"].exact_base,
            "RawBaseScore": kwargs["result"].raw_base,
            "Score": kwargs["result"].exact_fg,
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Overflow": 0},
            "forced_counts": [],
            "response_surface": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "ForceGreats": {},
        },
    )
    keep = {"base_score": 100, "gear": ["RawBaseInflated"], "minis": ["M1"], "fg_score": 0, "_source": "exact-base"}
    drop = {"base_score": 160, "gear": ["BelowSourcePair"], "minis": ["M2"], "fg_score": 0, "_source": "exact-base"}
    keep_stats = {"Perfect Points": 0}
    drop_stats = {"Perfect Points": 1}
    plan = SimpleNamespace(
        calc_song=_minimal_fg_calc_song(),
        ref_arrays=_minimal_fg_ref_arrays(),
        pending_jobs=((keep, {}, "Rush", keep_stats, 100, "keep"), (drop, {}, "Rush", drop_stats, 160, "drop")),
        prepared_batches=(
            SimpleNamespace(
                batch=_fake_fg_prepared_batch([keep_stats, drop_stats], "Rush"),
                rows=(("keep", keep_stats), ("drop", drop_stats)),
            ),
        ),
    )
    results = [
        SimpleNamespace(best_score=150, raw_base=200, exact_base=100, exact_fg=150),
        SimpleNamespace(best_score=150, raw_base=90, exact_base=160, exact_fg=150),
    ]

    out = FgResultReducer.materialize(plan, [results])

    assert [(row["gear"], row["base_score"], row["fg_score"]) for row in out] == [(["RawBaseInflated"], 100, 150)]
    assert keep["fg_base_score"] == 100
    assert out[0]["data"]["BaseScore"] == 100
