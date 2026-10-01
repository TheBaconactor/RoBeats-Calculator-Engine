"""FG worker contract for the fused GA->FG owner continuation (Slice 3).

The GPU owner scores FG in the GA turn and hands back an owner score map
(base_components_7tuple -> FgFusedOwnerScoreRow). ``run_fg_job_sync`` no longer
submits BUILD/SCORE owner requests; it materializes the prepared plan against the
owner map off the owner's critical path. These tests pin that contract with fakes
(no GPU).
"""

from types import SimpleNamespace

import numpy as np

from tests.native_song_factory import make_native_song
from tests.curves_support import synthetic_curves
from tests.songs_support import make_song


def _song():
    return make_song([0.0, 1.0], primary="Rush", secondary="Flow")


def _curves():
    base = np.linspace(1.0, 2.0, 161, dtype=np.float32)
    return synthetic_curves({
        "Perfect Points": base,
        "Combo Multiplier": base + np.float32(0.1),
        "Fever Multiplier": base + np.float32(0.2),
        "Fever Time": base + np.float32(0.3),
        "Fever Fill Rate": base + np.float32(0.4),
    })


def _prepared_batch(base_components, rows):
    # Minimal SURFACES_PACKED-stage stand-in carrying the fields the fused
    # materializer reads: base_components (keys the owner-map lookup) + the
    # per-candidate rows + the song-level batch context.
    return SimpleNamespace(
        base_components=np.asarray(base_components, dtype=np.int32),
        selected_color="Rush",
        song=_song(),
        curves=_curves(),
        scoring_bundle=object(),
        started=0.0,
    )


def _prepared_plan(base_components, base_stats=None):
    from gear_optimizer.pipeline.results import SolvedLoadout
    from gear_optimizer.solver.fg_response_scoring.planner import FgJob

    planner_key = ("ck0",)
    stats = dict(base_stats or {"Perfect Points": 1})
    return SimpleNamespace(
        song=_song(),
        curves=_curves(),
        jobs=(FgJob(SolvedLoadout(("Hat",) * 6, ("Mini",) * 3), "Rush", stats, 100, planner_key),),
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
        fg_response_frontier_plan=plan,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        ga_candidates=[],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        curves={"Perfect Points": []},
        timed_song=_song(),
        db_best_fg_score=0,
        song_name="Fused FG (Hard) by pytest",
        db_key="fused-fg-hard",
        fp="Data/Hard/Fused FG (Hard) by pytest.txt",
        fg_results=(),
    )
    kwargs.update(overrides)
    song = make_native_song(**kwargs)
    song.runtime.fg.fg_owner_score_map = owner_score_map
    return song


def test_fg_materialization_reduces_the_owner_score_map(tmp_path, monkeypatch):
    from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer
    from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService
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

    variants = FgResponseScoringService.materialize_from_owner_score_map(plan, owner_map)

    assert seen["plan"] is plan
    assert int(seen["results"][0][0].best_score) == 130
    assert int(variants[0]["fg_score"]) == 130


def test_fg_materialization_requires_the_owner_score_map():
    from gear_optimizer.solver.fg_materialization_worker import build_fg_materialization_request

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
        build_fg_materialization_request(song)
    except RuntimeError as exc:
        assert "owner fg score map" in str(exc).lower()
    else:
        raise AssertionError("expected a missing owner FG score map to fail loudly")


def test_fg_materialization_returns_the_reduced_results_with_its_timings(monkeypatch):
    from gear_optimizer.solver import fg_materialization_worker as worker
    from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService

    reduced = [("loadout", "fg result")]
    seen = []

    def _materialize(plan, owner_score_map):
        seen.append((plan, owner_score_map))
        return reduced

    monkeypatch.setattr(FgResponseScoringService, "materialize_from_owner_score_map", staticmethod(_materialize))
    plan = SimpleNamespace(prepared_batches=())
    request = worker.FgMaterializationRequest(song_key="song", plan=plan, owner_score_map={(1,): "row"})

    result = worker.materialize_fg_request(request)

    assert seen == [(plan, {(1,): "row"})]
    assert result.results == (("loadout", "fg result"),)


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
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        ga_candidates=[],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        curves={"Perfect Points": []},
        timed_song=make_song([1.0]),
        db_best_fg_score=0,
        song_name="Prep No RoundTrip (Hard) by pytest",
        db_key="prep-no-roundtrip-hard",
        fp="Data/Hard/Prep No RoundTrip (Hard) by pytest.txt",
        fg_results=(),
    )

    # The fused handoff prefetches NO owner BUILD/SCORE during prep (the owner already scored in the GA turn).
    fg_pipeline.prepare_fg_job_sync(song)

    assert song.runtime.fg.fg_response_frontier_plan is plan
