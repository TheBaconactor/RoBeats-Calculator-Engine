"""FG worker contract for the fused GA->FG owner continuation (Slice 3).

The GPU owner scores FG in the GA turn and hands back an owner score map
(base_components_7tuple -> FgFusedOwnerScoreRow). ``run_fg_job_sync`` no longer
submits BUILD/SCORE owner requests; it materializes the prepared plan against the
owner map off the owner's critical path. These tests pin that contract with fakes
(no GPU).
"""

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.native_inflight_config import make_native_song


def _calc_song():
    timestamps = np.asarray([0.0, 1.0], dtype=np.float32)
    return {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 1.0,
        },
        "song_data": {
            "timestamps": timestamps,
            "fg_timestamps": timestamps,
            "fg_perfect_candidate_timestamps": timestamps,
            "fg_great_candidate_timestamps": timestamps,
            "fg_perfect_floor_timestamps": timestamps,
            "fg_great_floor_timestamps": timestamps,
        },
    }


def _ref_arrays():
    base = np.linspace(1.0, 2.0, 161, dtype=np.float32)
    return {
        "Perfect Points": base,
        "Combo Multiplier": base + np.float32(0.1),
        "Fever Multiplier": base + np.float32(0.2),
        "Fever Time": base + np.float32(0.3),
        "Fever Fill Rate": base + np.float32(0.4),
    }


def _prepared_batch(base_components, rows):
    # Minimal SURFACES_PACKED-stage stand-in carrying the fields the fused
    # materializer reads: base_components (keys the owner-map lookup) + the
    # per-candidate rows + the song-level batch context.
    return SimpleNamespace(
        base_components=np.asarray(base_components, dtype=np.int32),
        selected_color="Rush",
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        scoring_bundle=object(),
        started=0.0,
    )


def _prepared_plan(base_components, base_stats=None):
    planner_key = ("ck0",)
    stats = dict(base_stats or {"Perfect Points": 1})
    entry = {"loadout_hash": "ck0"}
    eval_data = {"BaseStats": dict(stats), "Selected Element": "Rush"}
    return SimpleNamespace(
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        pending_jobs=((entry, eval_data, "Rush", stats, 100, planner_key),),
        prepared_batches=[
            SimpleNamespace(
                batch=_prepared_batch(base_components, rows=[(planner_key, stats)]),
                rows=((planner_key, stats),),
            )
        ],
    )


def _owner_row(fg_score):
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgFusedOwnerScoreRow

    # The inner_row[0] is the solved best_score; the fused materializer / fake
    # solve-result builder below reads it as the fg score signal.
    return FgFusedOwnerScoreRow(
        ft=1,
        ff=2,
        ft_stat=3,
        ff_stat=6,
        inner_row=(int(fg_score), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        surface=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    )


def _make_fg_song(plan, owner_score_map, **overrides):
    kwargs = dict(
        fg_prep_future=None,
        fg_response_frontier_plan=plan,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        ga_candidates=[],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        prev_record=None,
        db_best_fg_score=0,
        song_name="Fused FG (Hard) by pytest",
        db_key="fused-fg-hard",
        fp="Data/Hard/Fused FG (Hard) by pytest.txt",
        cfg_dict={},
        fg_variants=[],
    )
    kwargs.update(overrides)
    song = make_native_song(**kwargs)
    song.runtime.fg.fg_owner_score_map = owner_score_map
    return song


def test_run_fg_job_sync_materializes_from_owner_score_map(tmp_path, monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    base_components = [(10, 11, 12, 13, 14, 15, 16)]
    owner_map = {(10, 11, 12, 13, 14, 15, 16): _owner_row(130)}
    plan = _prepared_plan(base_components)

    seen: dict[str, object] = {}

    # The fused materializer builds a solve result per batch row from the owner row;
    # fake it to surface the inner_row[0] as the fg score so we can assert wiring.
    def _fake_build(*, score_row, **_kwargs):
        return SimpleNamespace(best_score=int(score_row.inner_row[0]))

    monkeypatch.setattr(response_frontier, "build_fused_owner_solve_result_from_score_row", _fake_build)

    def _fake_materialize(plan_arg, prepared_results, **_kwargs):
        seen["plan"] = plan_arg
        result_cache = dict(_kwargs.get("result_cache_override") or {})
        if result_cache:
            prepared_results = [[next(iter(result_cache.values()))]]
        seen["results"] = prepared_results
        return [{"fg_score": int(prepared_results[0][0].best_score)}]

    monkeypatch.setattr(FgResultReducer, "materialize", staticmethod(_fake_materialize))

    song = _make_fg_song(plan, owner_map)
    fg_pipeline.run_fg_job_sync(song, gpu_client=None)

    assert seen["plan"] is plan
    assert int(seen["results"][0][0].best_score) == 130
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 130


def test_run_fg_job_sync_requires_owner_score_map():
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline

    plan = SimpleNamespace(
        prepared_batches=[
            SimpleNamespace(
                batch=_prepared_batch([(1, 2, 3, 4, 5, 6, 7)], rows=[("ck0", {"Perfect Points": 1})]),
                rows=(("ck0", {"Perfect Points": 1}),),
            )
        ]
    )
    song = _make_fg_song(plan, owner_score_map=None)

    try:
        fg_pipeline.run_fg_job_sync(song, gpu_client=None)
    except RuntimeError as exc:
        assert "owner fg score map" in str(exc).lower()
    else:
        raise AssertionError("expected a missing owner FG score map to fail loudly")


def test_materialize_from_owner_score_map_fails_on_missing_base_components(tmp_path):
    from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService

    base_components = [(1, 2, 3, 4, 5, 6, 7)]
    plan = _prepared_plan(base_components)
    # Owner map does NOT contain the batch's base_components -> must fail loudly.
    try:
        FgResponseScoringService.materialize_from_owner_score_map(plan, {(9, 9, 9, 9, 9, 9, 9): _owner_row(1)})
    except RuntimeError as exc:
        assert "missing base_components" in str(exc).lower()
    else:
        raise AssertionError("expected a missing owner-map base_components row to fail loudly")


def test_native_fg_pipeline_does_not_expose_direct_force_greats_route():
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline

    assert not hasattr(fg_pipeline, "run_force_greats_response_frontier_for_ga_candidates")


def test_prepare_fg_job_builds_plan_without_owner_round_trip(monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    plan = SimpleNamespace(prepared_batches=[SimpleNamespace(batch=SimpleNamespace())])

    monkeypatch.setattr(
        fg_pipeline,
        "prepare_ga_candidate_surface_for_fg",
        lambda _song, *, fg_candidate_limit: ([{"candidate": 1}], 1, False),
    )
    monkeypatch.setattr(FgPlanner, "plan_many", staticmethod(lambda *_args, **_kwargs: plan))

    song = make_native_song(
        fg_prep_future=None,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        ga_candidates=[],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {"timestamps": [1.0]}},
        prev_record=None,
        db_best_fg_score=0,
        song_name="Prep No RoundTrip (Hard) by pytest",
        db_key="prep-no-roundtrip-hard",
        fp="Data/Hard/Prep No RoundTrip (Hard) by pytest.txt",
        cfg_dict={},
        fg_variants=[],
    )

    # gpu_client is accepted but unused: the fused handoff prefetches NO owner
    # BUILD/SCORE during prep (the owner already scored in the GA turn).
    fg_pipeline.prepare_fg_job_sync(song, gpu_client=object())

    assert song.runtime.fg.fg_response_frontier_plan is plan
    assert song.runtime.fg.cpu_fg_prep_s >= 0.0
