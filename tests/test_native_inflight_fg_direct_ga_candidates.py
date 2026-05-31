from concurrent.futures import Future
from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_config import make_native_song


class _FakeFGGpuClient:
    def __init__(self, result):
        self.payloads = []
        self._result = result

    def submit_force_greats_response_frontier_score_batch(self, payload):
        self.payloads.append(payload)
        future = Future()
        future.set_result(self._result)
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
        loadout_entries={},
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
        fg_candidate_limit=51,
        fg_direct_ga_candidates=True,
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

    assert not hasattr(fg_pipeline, "process_force_greats")


def test_run_fg_job_sync_submits_all_prepared_batches_before_waiting(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter
    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    class _AssertAllSubmittedFuture:
        def __init__(self, client, result):
            self.client = client
            self.result_rows = result

        def result(self):
            assert len(self.client.payloads) == 2
            return self.result_rows

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
            return SimpleNamespace(future=_AssertAllSubmittedFuture(self, result))

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
        loadout_entries={},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        ga_candidates=[],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        fg_candidate_limit=51,
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
        loadout_entries={},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        effective_difficulty="Hard",
        ga_candidates=[{"BaseScore": 100, "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={"Perfect Points": []},
        calc_song={"metadata": {}, "song_data": {}},
        fg_candidate_limit=51,
        fg_direct_ga_candidates=False,
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
