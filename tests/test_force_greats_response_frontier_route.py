from gear_optimizer.solver.native_inflight_config import make_native_song

import pytest
import numpy as np


def _minimal_fg_calc_song(note_count: int = 4) -> dict:
    timestamps = np.linspace(0.0, 1.0, int(note_count), dtype=np.float32)
    return {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]) if int(timestamps.shape[0]) else 0.0,
        },
        "song_data": {"timestamps": timestamps, "fg_timestamps": timestamps},
    }


def _minimal_fg_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    return {
        "Perfect Points": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
    }


def test_ftff_response_position_prune_matches_pair_prune_with_canonical_frontier_keys():
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import (
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
        secondary_values=np.asarray([secondary for _frontier_idx, _residual, _primary, secondary in rows], dtype=np.int32),
    )

    assert got.tolist() == [int(pair[0]) for pair in expected]


def test_ftff_response_position_prune_matches_bruteforce_randomized():
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import (
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


def test_nojit_fixed_stats_score_matches_jit_score():
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score, evaluate_stats_score_nojit

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

    assert evaluate_stats_score_nojit(stats, calc_song, ref_arrays) == evaluate_stats_score(stats, calc_song, ref_arrays)


def test_process_force_greats_response_frontier_failure_raises_directly(monkeypatch):
    from gear_optimizer.helpers.song_helpers import force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter

    def _boom(*_args, **_kwargs):
        raise RuntimeError("response frontier path failed")

    monkeypatch.setattr(force_greats, "run_force_greats_response_frontier_for_ga_candidates", _boom)

    class _Registry:
        @staticmethod
        def decode_names(ids):
            return [f"I{int(x)}" for x in ids[:9]]

    ga_candidates = [
        {
            "BaseScore": 321,
            "GenomeIDs": [1, 2, 3, 4, 5, 6, 9, 8, 7],
            "Data": {
                "BaseStats": {"Perfect Points": 5, "Rush": 7},
                "GemCounts": {"Perfect Points": 1},
                "FT": 1,
                "FF": 2,
                "Selected Element": "Rush",
            },
        }
    ]

    with pytest.raises(RuntimeError, match="response frontier path failed"):
        force_greats.run_force_greats_response_frontier_for_ga_candidates(
            ga_candidates=ga_candidates,
            calc_song={"metadata": {}, "song_data": {}},
            ref_arrays={},
            meta_primary_color="Rush",
        )


def test_prepare_fg_job_sync_uses_db_only_entries_for_response_frontier_route(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    seen = {}
    seen_bundle = object()

    def _fake_prepare_plan(*_args, **kwargs):
        seen["scoring_bundle"] = kwargs.get("scoring_bundle")
        seen["plan_ga_n"] = len(_args[0] or [])
        seen["plan_registry"] = kwargs.get("ga_registry")
        return "prepared-plan"

    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        FgPlanner,
        "plan_many",
        staticmethod(_fake_prepare_plan),
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
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

    assert seen["plan_ga_n"] == 1
    assert seen["scoring_bundle"] is seen_bundle
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"
    assert len(song.runtime.decode.ga_candidates or []) == 1


def test_prepare_fg_job_sync_canonicalizes_gpu_payload_before_response_frontier(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        FgPlanner,
        "plan_many",
        staticmethod(lambda *_args, **_kwargs: "prepared-plan"),
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    duplicate_prefix = [
        {
            "Score": 1000 - i,
            "BaseScore": 1000 - i,
            "Gear": ["DupG1", "DupG2", "DupG3", "DupG4", "DupG5", "DupG6"],
            "Minis": ["DupM1", "DupM2", "DupM3"],
            "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": i, "Selected Element": "Rush"},
        }
        for i in range(60)
    ]
    keeper = {
        "Score": 100,
        "BaseScore": 100,
        "Gear": ["KeepG1", "KeepG2", "KeepG3", "KeepG4", "KeepG5", "KeepG6"],
        "Minis": ["KeepM1", "KeepM2", "KeepM3"],
        "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": 60, "Selected Element": "Rush"},
    }

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=duplicate_prefix + [keeper],
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

    selected = song.runtime.decode.ga_candidates or []
    assert len(selected) == 2
    assert any((cand.get("Gear") or [None])[0] == "KeepG1" for cand in selected)
    assert sorted(int(cand["BaseScore"]) for cand in selected) == [100, 1000]
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"


def test_prepare_fg_job_sync_processes_configured_top_base_candidate_limit(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    seen: dict[str, int] = {}

    def _top_base_selector(candidates, *, limit, **_kwargs):
        seen["candidate_count"] = len(candidates or [])
        seen["limit"] = int(limit)
        rows = list(candidates or [])
        rows.sort(key=lambda cand: int(cand.get("BaseScore", cand.get("Score", 0)) or 0), reverse=True)
        return rows[: int(limit)]

    monkeypatch.setattr(stages, "select_top_base_ga_candidates", _top_base_selector)
    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        FgPlanner,
        "plan_many",
        staticmethod(lambda *_args, **_kwargs: "prepared-plan"),
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}
    ga_candidates = [
        {
            "Score": 1000 - i,
            "BaseScore": 1000 - i,
            "Gear": [f"G{i}_{slot}" for slot in range(6)],
            "Minis": [f"M{i}_{slot}" for slot in range(3)],
            "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": i, "Selected Element": "Rush"},
        }
        for i in range(77)
    ]

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=ga_candidates,
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

    assert seen == {"candidate_count": 77, "limit": 51}
    assert len(song.runtime.decode.ga_candidates or []) == 51
    assert [int(cand["BaseScore"]) for cand in song.runtime.decode.ga_candidates or []] == list(range(1000, 949, -1))
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"


def test_prepare_fg_job_sync_requires_materialized_response_frontier_plan(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        FgPlanner,
        "plan_many",
        staticmethod(lambda *_args, **_kwargs: None),
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}
    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {"notes": [{"time": 1.0}]}},
        cfg_dict={},
        ga_candidates=[{"BaseScore": 100, "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
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


def test_prepare_fg_static_sync_warms_jit_and_loads_canonical_scoring_bundle(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache, response_frontier, response_ftff_prune

    seen: dict[str, object] = {"frontier": 0, "ftff": 0}
    canonical_keys = ((0, 0), (1, 1))
    bundle = object()

    def _fake_load_bundle(_calc_song, _ref_arrays, *, stat_keys):
        seen["stat_keys"] = tuple(stat_keys)
        return bundle

    monkeypatch.setattr(response_cache, "load_response_frontier_scoring_bundle", _fake_load_bundle)
    monkeypatch.setattr(response_cache, "all_response_stat_keys", lambda: canonical_keys)
    monkeypatch.setattr(response_frontier, "warmup_response_frontier_group_builder", lambda: seen.__setitem__("frontier", 1))
    monkeypatch.setattr(response_ftff_prune, "warmup_response_ftff_prune", lambda: seen.__setitem__("ftff", 1))

    cfg = configparser.ConfigParser()
    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {"notes": [{"time": 1.0}]}},
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
    assert seen == {"frontier": 1, "ftff": 1, "stat_keys": canonical_keys}


def test_process_force_greats_forwards_direct_ga_candidates_to_response_frontier(monkeypatch):
    from gear_optimizer.helpers.song_helpers import force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter

    seen: list[tuple[int, object]] = []
    registry = object()

    def _fake_response_frontier(
        ga_candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        ga_registry=None,
        scoring_bundle=None,
        gpu_client=None,
    ):
        _ = (
            calc_song,
            ref_arrays,
            meta_primary_color,
            scoring_bundle,
            gpu_client,
        )
        seen.append((len(ga_candidates or []), ga_registry))
        return [
            {
                "data": {
                    "Score": 100 + len(seen),
                    "BaseScore": 90,
                    "ForceGreats": {"config": {"NonFever1": 1}},
                },
                "gear": [f"G{len(seen)}"],
                "minis": [f"M{len(seen)}"],
                "score": 90,
                "fg_score": 100 + len(seen),
            }
        ]

    monkeypatch.setattr(force_greats, "run_force_greats_response_frontier_for_ga_candidates", _fake_response_frontier)

    ga_candidates = [
        {
            "Gear": ["A"],
            "Minis": ["B"],
            "BaseScore": 90,
            "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
        }
    ]

    out = force_greats.run_force_greats_response_frontier_for_ga_candidates(
        ga_candidates=ga_candidates,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        meta_primary_color="Rush",
        ga_registry=registry,
    )

    assert seen == [(1, registry)]
    assert len(out) == 1
    assert int(out[0]["fg_score"]) == 101


def test_force_payload_uses_supplied_reconstruction_frontier(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
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
    seen = {}

    monkeypatch.setattr(
        reducer_mod,
        "extract_fg_song_inputs",
        lambda calc_song: SimpleNamespace(
            timestamps=[0.0],
            perfect_candidates=[0.0],
            great_candidates=[0.0],
            use_forced_great_timing=True,
        ),
    )

    def _fake_reconstruct_trace(**kwargs):
        seen["frontier"] = kwargs["frontier"]
        return ({"forced_count": 1}, {"forced_count": 0}, {"forced_count": 1})

    monkeypatch.setattr(reducer_mod, "reconstruct_force_greats_response_trace", _fake_reconstruct_trace)
    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 1230)

    payload = adapter._force_payload_from_response_frontier(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        reconstruction_frontier=full_frontier,
    )

    assert seen["frontier"] is full_frontier
    assert payload["BaseScore"] == 1000
    assert payload["forced_counts"] == [1, 0, 1]
    assert payload["ForceGreats"]["frontier_trace"] == [{"forced_count": 1}, {"forced_count": 0}, {"forced_count": 1}]
    assert payload["Score"] == 1230
    assert payload["ForceGreats"]["final_score"] == 1230
    assert payload["ForceGreats"]["frontier_states"] == 9
    assert payload["ForceGreats"]["non_fever_base"] == 11


def test_force_payload_reconstructs_counts_without_state_frontiers(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
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
            use_forced_great_timing=True,
        ),
    )
    monkeypatch.setattr(
        reducer_mod,
        "reconstruct_force_greats_response_trace",
        lambda **_kwargs: ({"forced_count": 1}, {"forced_count": 0}, {"forced_count": 1}),
    )
    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 1230)

    payload = adapter._force_payload_from_response_frontier(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
    )

    assert payload["BaseScore"] == 1000
    assert payload["forced_counts"] == [1, 0, 1]
    assert payload["ForceGreats"]["frontier_trace"] == [{"forced_count": 1}, {"forced_count": 0}, {"forced_count": 1}]
    assert payload["Score"] == 1230


def test_force_payload_emits_compact_trace_from_slim_frontier(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _action_table,
        _edge_surface_option_details,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
    )

    timestamps = np.asarray([0.0, 0.18, 0.41, 0.64, 0.95, 1.21, 1.5], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0, 0.05, 0.0, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)
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
        for row in _edge_surface_option_details(
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
            great_candidate_timestamps=great_candidates,
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
            "fg_great_candidate_timestamps": great_candidates,
        },
    }

    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 4321)

    payload = adapter._force_payload_from_response_frontier(
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


def test_response_frontier_route_reconstructs_only_top_limit_candidates(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    import gear_optimizer.solver.fg_response_scoring.planner as planner_mod
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    scoring_frontier = FgResponseFrontierResult((surface,), {}, 1, 1, 1, 1, 1, 1, 3, 0.0)

    def _result(best_score: int, ft_stat: int, ff_stat: int):
        return FgResponseFrontierSolveResult(
            best_score=best_score,
            ft=1,
            ff=2,
            gem_counts={"Perfect Points": 0},
            stats={"Fever Time": ft_stat, "Fever Fill Rate": ff_stat},
            surface=surface,
            frontier=scoring_frontier,
            inner=FgResponseInnerResult(best_score, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            seconds=0.0,
            forced_counts=(),
            raw_fever_fill=1.0,
            real_fever_time=2.0,
        )

    monkeypatch.setattr(reducer_mod, "LOADOUTS_PER_SONG_LIMIT", 1)
    monkeypatch.setattr(planner_mod, "eval_data_from_entry", lambda entry, primary: dict(entry["eval_data"]))
    monkeypatch.setattr(planner_mod, "expected_selected_element", lambda entry, primary: str(entry["eval_data"]["Selected Element"]))
    monkeypatch.setattr(
        planner_mod.FgPlanner,
        "base_stats_for_response_frontier",
        staticmethod(lambda eval_data, selected: {"Perfect Points": int(eval_data["pp"])}),
    )
    monkeypatch.setattr(
        reducer_mod,
        "materialize_entry_names",
        lambda entry, mutate=True: (list(entry["gear"]), list(entry["minis"])),
    )
    monkeypatch.setattr(planner_mod, "extract_fg_song_inputs", lambda calc_song: SimpleNamespace(total_notes=1))
    monkeypatch.setattr(
        planner_mod,
        "prepare_force_greats_response_frontier_scoring_batch",
        lambda **kwargs: {"base_stats_list": list(kwargs["base_stats_list"])},
    )

    seen_payloads = []

    def _fake_force_payload(*, result, reconstruction_frontier=None, **kwargs):
        seen_payloads.append((int(result.best_score), reconstruction_frontier))
        return {
            "BaseScore": 60,
            "Score": int(result.best_score),
            "ForceGreats": {"config": {"NonFever1": 1}},
            "forced_counts": [1],
        }

    monkeypatch.setattr(reducer_mod, "materialize_force_payload_from_response_frontier", _fake_force_payload)

    candidates = [
        {
            "Gear": ["G1"],
            "Minis": ["M1"],
            "BaseScore": 50,
            "Data": {"Selected Element": "Rush", "pp": 1},
        },
        {
            "Gear": ["G2"],
            "Minis": ["M2"],
            "BaseScore": 40,
            "Data": {"Selected Element": "Rush", "pp": 2},
        },
    ]

    monkeypatch.setattr(
        GpuScoreEngine,
        "score_plan",
        staticmethod(lambda _plan, **kwargs: ([[_result(100, 10, 20), _result(90, 30, 40)]], [])),
    )
    out = adapter.run_force_greats_response_frontier_for_ga_candidates(
        candidates,
        calc_song=_minimal_fg_calc_song(),
        ref_arrays=_minimal_fg_ref_arrays(),
        meta_primary_color="Rush",
    )

    assert seen_payloads == [(100, None)]
    assert len(out) == 1
    assert int(out[0]["fg_score"]) == 100


def test_response_frontier_prunes_duplicate_constant_ftff_frontiers_by_best_residual():
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import prune_best_positions_by_frontier

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
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import prune_best_positions_by_frontier

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
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import (
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
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import (
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
        if any(
            response_pair_dominates(other, pair, primary_color="Rush", secondary_color="Flow")
            for other in naive
        ):
            continue
        naive = [
            other
            for other in naive
            if not response_pair_dominates(pair, other, primary_color="Rush", secondary_color="Flow")
        ]
        naive.append(pair)

    kept = prune_dominated_ftff_response_pairs(pairs, primary_color="Rush", secondary_color="Flow")

    assert kept == naive


def test_process_force_greats_uses_shared_response_frontier_solver(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    import gear_optimizer.solver.fg_response_scoring.planner as planner_mod
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    calls = []

    def _result(base_stats, selected_color):
        surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        frontier = FgResponseFrontierResult(
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
        inner = FgResponseInnerResult(
            best_score=150,
            surface_index=0,
            g_pp=1,
            g_cm=2,
            g_fm=3,
            g_ov=4,
            final_pp=11,
            final_cm=12,
            final_fm=13,
            final_primary=14,
            final_secondary=15,
        )
        return FgResponseFrontierSolveResult(
            best_score=150,
            ft=6,
            ff=7,
            gem_counts={"Perfect Points": 1, "Combo Multiplier": 2, "Fever Multiplier": 3, "Element": 4},
            stats={**base_stats, "Fever Time": 6, "Fever Fill Rate": 7},
            surface=surface,
            frontier=frontier,
            inner=inner,
            seconds=0.0,
            forced_counts=(5, 0),
        )

    def _fake_prepare_batch(*, base_stats_list, calc_song, ref_arrays, selected_color, **_kwargs):
        calls.append((list(base_stats_list), selected_color, calc_song, ref_arrays))
        return {"base_stats_list": list(base_stats_list), "selected_color": selected_color}

    def _fake_score_batch(batch, **_kwargs):
        return [_result(base_stats, str(batch["selected_color"])) for base_stats in batch["base_stats_list"]]

    monkeypatch.setattr(
        planner_mod,
        "extract_fg_song_inputs",
        lambda _song: SimpleNamespace(total_notes=2),
    )
    monkeypatch.setattr(
        reducer_mod,
        "extract_fg_song_inputs",
        lambda _song: SimpleNamespace(
            timestamps=[0.0, 1.0],
            perfect_candidates=[0.0, 1.0],
            great_candidates=[0.0, 1.0],
            use_forced_great_timing=True,
        ),
    )
    monkeypatch.setattr(planner_mod, "prepare_force_greats_response_frontier_scoring_batch", _fake_prepare_batch)
    monkeypatch.setattr(
        reducer_mod,
        "reconstruct_force_greats_response_trace",
        lambda **_kwargs: ({"forced_count": 5}, {"forced_count": 0}),
    )
    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_args, **_kwargs: 150)

    monkeypatch.setattr(
        GpuScoreEngine,
        "score_plan",
        staticmethod(lambda plan, **kwargs: ([_fake_score_batch(plan.prepared_batches[0].batch)], [])),
    )
    out = adapter.run_force_greats_response_frontier_for_ga_candidates(
        [
            {
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {
                    "BaseStats": {
                        "Perfect Points": 0,
                        "Combo Multiplier": 0,
                        "Fever Multiplier": 0,
                        "Fever Time": 0,
                        "Fever Fill Rate": 0,
                        "Rush": 10,
                    },
                    "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
                    "FT": 0,
                    "FF": 0,
                    "Selected Element": "Rush",
                },
            }
        ],
        _minimal_fg_calc_song(),
        _minimal_fg_ref_arrays(),
        "Rush",
    )

    assert len(calls) == 1
    assert len(calls[0][0]) == 1
    assert calls[0][1] == "Rush"
    assert len(out) == 1
    assert out[0]["fg_score"] == 150
    assert out[0]["base_score"] == 100
    assert out[0]["data"]["BaseScore"] == 100
    assert out[0]["data"]["FT"] == 6
    assert out[0]["data"]["FF"] == 7
    assert out[0]["data"]["GemCounts"]["Element"] == 4
    assert set(out[0]["data"]["ForceGreats"]) == {
        "config",
        "final_score",
        "frontier_trace",
        "frontier_first_surfaces",
        "frontier_states",
        "frontier_max_state",
        "frontier_transitions",
        "non_fever_base",
    }
    assert out[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 5, "NonFever2": 0}
    assert out[0]["gear"] == ["G1"]
    assert out[0]["minis"] == ["M1"]


def test_process_force_greats_uses_authoritative_paired_base_for_emit_gate(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod

    monkeypatch.setattr(
        reducer_mod,
        "materialize_force_payload_from_response_frontier",
        lambda **kwargs: {
            "BaseScore": kwargs["result"].exact_base,
            "RawBaseScore": kwargs["result"].raw_base,
            "Score": kwargs["result"].exact_fg,
        },
    )
    keep = {"base_score": 100, "gear": ["RawBaseInflated"], "minis": ["M1"], "fg_score": 0, "_source": "ga"}
    drop = {"base_score": 160, "gear": ["BelowSourcePair"], "minis": ["M2"], "fg_score": 0, "_source": "ga"}
    plan = SimpleNamespace(
        calc_song={},
        ref_arrays={},
        pending_jobs=((keep, {}, "Rush", {}, 100, "keep"), (drop, {}, "Rush", {}, 160, "drop")),
        prepared_batches=(SimpleNamespace(rows=(("keep", {}), ("drop", {}))),),
    )
    results = [
        SimpleNamespace(best_score=150, raw_base=200, exact_base=100, exact_fg=150),
        SimpleNamespace(best_score=150, raw_base=90, exact_base=160, exact_fg=150),
    ]

    out = adapter.materialize_force_greats_response_frontier_plan_results(plan, [results])

    assert [(row["gear"], row["base_score"], row["fg_score"]) for row in out] == [(["RawBaseInflated"], 100, 150)]
    assert keep["fg_base_score"] == 100
    assert out[0]["data"]["BaseScore"] == 100


def test_process_force_greats_batches_response_frontier_candidates(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    import gear_optimizer.solver.fg_response_scoring.planner as planner_mod
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    calls: list[int] = []

    def _fake_prepare_batch(*, base_stats_list, calc_song, ref_arrays, selected_color, **_kwargs):
        _ = (calc_song, ref_arrays, selected_color)
        calls.append(len(base_stats_list))
        return {"base_stats_list": list(base_stats_list)}

    def _fake_score_batch(batch, **_kwargs):
        out = []
        for idx, base_stats in enumerate(batch["base_stats_list"]):
            surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, idx, 0)
            frontier = FgResponseFrontierResult(
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
            inner = FgResponseInnerResult(
                best_score=200 + idx,
                surface_index=0,
                g_pp=0,
                g_cm=0,
                g_fm=0,
                g_ov=1,
                final_pp=0,
                final_cm=0,
                final_fm=0,
                final_primary=0,
                final_secondary=0,
            )
            out.append(
                FgResponseFrontierSolveResult(
                    best_score=200 + idx,
                    ft=0,
                    ff=0,
                    gem_counts={"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
                    stats={**base_stats, "Rush": int(base_stats.get("Rush", 0) or 0) + 1},
                    surface=surface,
                    frontier=frontier,
                    inner=inner,
                    seconds=0.0,
                    forced_counts=(5, 0),
                )
            )
        return out

    monkeypatch.setattr(
        planner_mod,
        "extract_fg_song_inputs",
        lambda _song: SimpleNamespace(total_notes=2),
    )
    monkeypatch.setattr(
        reducer_mod,
        "extract_fg_song_inputs",
        lambda _song: SimpleNamespace(
            timestamps=[0.0, 1.0],
            perfect_candidates=[0.0, 1.0],
            great_candidates=[0.0, 1.0],
            use_forced_great_timing=True,
        ),
    )
    monkeypatch.setattr(planner_mod, "prepare_force_greats_response_frontier_scoring_batch", _fake_prepare_batch)
    monkeypatch.setattr(
        reducer_mod,
        "reconstruct_force_greats_response_trace",
        lambda **_kwargs: ({"forced_count": 5}, {"forced_count": 0}),
    )
    monkeypatch.setattr(
        reducer_mod,
        "score_force_greats_response_surface_exact",
        lambda stats, *_args, **_kwargs: int(stats["Rush"]) + 189,
    )

    monkeypatch.setattr(
        GpuScoreEngine,
        "score_plan",
        staticmethod(lambda plan, **kwargs: ([_fake_score_batch(plan.prepared_batches[0].batch)], [])),
    )
    out = adapter.run_force_greats_response_frontier_for_ga_candidates(
        [
            {
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"BaseStats": {"Perfect Points": 0, "Rush": 10}, "Selected Element": "Rush"},
            },
            {
                "BaseScore": 101,
                "Gear": ["G2"],
                "Minis": ["M2"],
                "Data": {"BaseStats": {"Perfect Points": 0, "Rush": 11}, "Selected Element": "Rush"},
            },
        ],
        _minimal_fg_calc_song(),
        _minimal_fg_ref_arrays(),
        "Rush",
    )

    assert calls == [2]
    assert [row["fg_score"] for row in out] == [201, 200]
