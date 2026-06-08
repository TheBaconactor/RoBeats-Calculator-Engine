from concurrent.futures import Future
from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_config import make_native_song


def _owner_result(batch, inner_rows):
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseFrontierOwnerResult

    return FgResponseFrontierOwnerResult(batch=batch, inner_rows=inner_rows)


class _FakeFGGpuClient:
    def __init__(self, result):
        self.payloads = []
        self._result = result

    def submit_force_greats_response_frontier_score_batch(self, payload):
        self.payloads.append(payload)
        future = Future()
        future.set_result(_owner_result(payload["batch"], self._result))
        return SimpleNamespace(future=future)


def test_run_fg_job_sync_forwards_direct_ga_candidates(monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    registry = object()
    gpu_client = _FakeFGGpuClient(
        [
            {
                "score": 100,
                "base_score": 100,
                "fg_score": 130,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ]
    )

    seen_adapter: dict[str, object] = {}

    def _fake_materialize_response_frontier_plan_results(plan, prepared_results):
        seen_adapter["plan"] = plan
        return prepared_results[0]

    monkeypatch.setattr(
        response_frontier_adapter,
        "materialize_force_greats_response_frontier_plan_results",
        _fake_materialize_response_frontier_plan_results,
    )
    monkeypatch.setattr(
        response_frontier,
        "materialize_prepared_force_greats_response_frontier_batch_results",
        lambda _batch, inner_rows, **_kwargs: inner_rows,
    )

    song = make_native_song(
        fg_prep_future=None,
        fg_response_frontier_plan=SimpleNamespace(prepared_batches=[SimpleNamespace(batch="prepared-batch")]),
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        ga_candidates=[
            {
                "BaseScore": 99,
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        registry=registry,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        prev_record=None,
        db_best_fg_score=0,
        song_name="AfterLife (Hard) by KepoWorld",
        db_key="afterlife-hard",
        fp="Data/Hard/AfterLife (Hard) by KepoWorld.txt",
        cfg_dict={},
        fg_variants=[],
    )

    fg_pipeline.run_fg_job_sync(song, gpu_client=gpu_client)

    assert seen_adapter["plan"] is song.runtime.fg.fg_response_frontier_plan
    assert len(gpu_client.payloads) == 1
    assert gpu_client.payloads[0]["batch"] == "prepared-batch"
    assert gpu_client.payloads[0]["include_forced_counts"] is False
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 130


def test_native_fg_pipeline_does_not_expose_direct_force_greats_route():
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline

    assert not hasattr(fg_pipeline, "run_force_greats_response_frontier_for_ga_candidates")


def test_prepare_fg_job_accepts_owner_deferred_group_arrays(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline

    batch = SimpleNamespace(
        group_meta=None,
        scoring_surface_words=None,
        scoring_group_lengths=None,
        scoring_unique_frontiers=0,
        scoring_surface_compact_ms=0.0,
        scoring_surface_head_coeff_ms=0.0,
        scoring_bundle_ms=0.0,
        scoring_setup_ms=0.0,
        scoring_geometry_ms=0.0,
        scoring_group_build_ms=0.0,
        scoring_concat_ms=0.0,
    )
    plan = SimpleNamespace(prepared_batches=[SimpleNamespace(batch=batch)])

    monkeypatch.setattr(
        fg_pipeline,
        "prepare_ga_candidate_surface_for_fg",
        lambda _song, *, fg_candidate_limit: ([{"candidate": 1}], 1, False),
    )
    monkeypatch.setattr(
        response_frontier_adapter,
        "prepare_force_greats_response_frontier_plan_for_ga_candidates",
        lambda *_args, **_kwargs: plan,
    )

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
        song_name="Deferred Owner Batch (Hard) by pytest",
        db_key="deferred-owner-batch-hard",
        fp="Data/Hard/Deferred Owner Batch (Hard) by pytest.txt",
        cfg_dict={},
        fg_variants=[],
    )

    fg_pipeline.prepare_fg_job_sync(song, gpu_client=None)

    assert song.runtime.fg.fg_response_frontier_plan is plan
    assert song.runtime.fg.cpu_fg_prep_s >= 0.0


def test_run_fg_job_sync_submits_all_prepared_batches_before_waiting(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    class _AssertAllSubmittedFuture:
        def __init__(self, client, batch, result):
            self.client = client
            self.batch = batch
            self.result_rows = result

        def result(self):
            assert len(self.client.payloads) == 2
            return _owner_result(self.batch, self.result_rows)

    class _AssertAllSubmittedGpuClient:
        def __init__(self):
            self.payloads = []

        def submit_force_greats_response_frontier_score_batch(self, payload):
            self.payloads.append(payload)
            result = [
                {
                    "score": 100,
                    "base_score": 100,
                    "fg_score": 120 + len(self.payloads),
                    "gear": ["G1"],
                    "minis": ["M1"],
                    "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
                }
            ]
            return SimpleNamespace(future=_AssertAllSubmittedFuture(self, payload["batch"], result))

    gpu_client = _AssertAllSubmittedGpuClient()

    monkeypatch.setattr(
        response_frontier,
        "materialize_prepared_force_greats_response_frontier_batch_results",
        lambda _batch, inner_rows, **_kwargs: inner_rows,
    )
    monkeypatch.setattr(
        response_frontier_adapter,
        "materialize_force_greats_response_frontier_plan_results",
        lambda _plan, prepared_results: [row for rows in prepared_results for row in rows],
    )

    song = make_native_song(
        fg_prep_future=None,
        fg_response_frontier_plan=SimpleNamespace(
            prepared_batches=[
                SimpleNamespace(batch="prepared-batch-a"),
                SimpleNamespace(batch="prepared-batch-b"),
            ]
        ),
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
        song_name="Two Batch FG (Hard) by pytest",
        db_key="two-batch-fg-hard",
        fp="Data/Hard/Two Batch FG (Hard) by pytest.txt",
        cfg_dict={},
        fg_variants=[],
    )

    fg_pipeline.run_fg_job_sync(song, gpu_client=gpu_client)

    assert [payload["batch"] for payload in gpu_client.payloads] == [
        "prepared-batch-a",
        "prepared-batch-b",
    ]
    assert [int(variant["fg_score"]) for variant in song.runtime.fg.fg_variants] == [121, 122]


def test_run_fg_job_sync_rejects_invalid_owner_result(monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline

    class _InvalidOwnerGpuClient:
        def submit_force_greats_response_frontier_score_batch(self, payload):
            future = Future()
            future.set_result([{"fg_score": 1}])
            return SimpleNamespace(future=future)

    song = make_native_song(
        fg_prep_future=None,
        fg_response_frontier_plan=SimpleNamespace(prepared_batches=[SimpleNamespace(batch="prepared-batch")]),
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
        song_name="Invalid Owner Result (Hard) by pytest",
        db_key="invalid-owner-result-hard",
        fp="Data/Hard/Invalid Owner Result (Hard) by pytest.txt",
        cfg_dict={},
        fg_variants=[],
    )

    try:
        fg_pipeline.run_fg_job_sync(song, gpu_client=_InvalidOwnerGpuClient())
    except RuntimeError as exc:
        assert "invalid owner result" in str(exc).lower()
    else:
        raise AssertionError("expected invalid owner result to fail loudly")


def test_run_fg_job_sync_records_owner_exec_time_not_service_queue_wait(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    class _TimedGpuClient:
        def submit_force_greats_response_frontier_score_batch(self, payload):
            payload["timing"]["owner_queue_s"] = 12.0
            payload["timing"]["owner_exec_s"] = 0.25
            future = Future()
            future.set_result(
                _owner_result(payload["batch"], [{"fg_score": 150, "data": {"ForceGreats": {"config": {"NonFever1": 1}}}}])
            )
            return SimpleNamespace(future=future)

    monkeypatch.setattr(
        response_frontier,
        "materialize_prepared_force_greats_response_frontier_batch_results",
        lambda _batch, inner_rows, **_kwargs: inner_rows,
    )
    monkeypatch.setattr(
        response_frontier_adapter,
        "materialize_force_greats_response_frontier_plan_results",
        lambda _plan, prepared_results: prepared_results[0],
    )

    song = make_native_song(
        fg_prep_future=None,
        fg_response_frontier_plan=SimpleNamespace(prepared_batches=[SimpleNamespace(batch="prepared-batch")]),
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
        song_name="Timed FG (Hard) by pytest",
        db_key="timed-fg-hard",
        fp="Data/Hard/Timed FG (Hard) by pytest.txt",
        cfg_dict={},
        fg_variants=[],
    )

    fg_pipeline.run_fg_job_sync(song, gpu_client=_TimedGpuClient())

    assert 0.25 <= song.runtime.fg.fg_run_wall_s < 1.0


def test_run_fg_job_sync_forces_response_frontier_direct_ga_candidates(monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    gpu_client = _FakeFGGpuClient(
        [
            {
                "score": 100,
                "base_score": 100,
                "fg_score": 140,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {"ForceGreats": {"config": {"NonFever1": 2}}},
            }
        ]
    )

    seen_adapter: dict[str, object] = {}

    def _fake_materialize_response_frontier_plan_results(plan, prepared_results):
        seen_adapter["plan"] = plan
        return prepared_results[0]

    monkeypatch.setattr(
        response_frontier_adapter,
        "materialize_force_greats_response_frontier_plan_results",
        _fake_materialize_response_frontier_plan_results,
    )
    monkeypatch.setattr(
        response_frontier,
        "materialize_prepared_force_greats_response_frontier_batch_results",
        lambda _batch, inner_rows, **_kwargs: inner_rows,
    )

    song = make_native_song(
        fg_prep_future=None,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        ga_candidates=[{"BaseScore": 100, "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        fg_response_frontier_plan=SimpleNamespace(prepared_batches=[SimpleNamespace(batch="prepared-batch")]),
        prev_record=None,
        db_best_fg_score=0,
        song_name="AfterLife (Hard) by KepoWorld",
        db_key="afterlife-hard",
        fp="Data/Hard/AfterLife (Hard) by KepoWorld.txt",
        cfg_dict={},
        fg_variants=[],
        song_slot=9,
    )

    fg_pipeline.run_fg_job_sync(song, gpu_client=gpu_client)

    assert seen_adapter["plan"] is song.runtime.fg.fg_response_frontier_plan
    assert len(gpu_client.payloads) == 1
    assert gpu_client.payloads[0]["batch"] == "prepared-batch"
    assert gpu_client.payloads[0]["include_forced_counts"] is False
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 140
