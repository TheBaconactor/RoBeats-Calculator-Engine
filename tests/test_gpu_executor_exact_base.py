from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.exact_base_domains import ExactBaseDomains
from gear_optimizer.solver.exact_base_song_context import ExactBaseSongContext
from gear_optimizer.solver.gpu_executor_batching import execute_exact_base_search
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType
from gear_optimizer.solver.native_fg_owner import ExactBaseOwnerResult
from gear_optimizer.solver.solver_common import SolverContext
from gear_optimizer.solver.taichi_gem.api.timeline import TimelineFrontierPrewarmResult


def _uninitialized(cls):
    return object.__new__(cls)


def _payload() -> dict:
    return {
        "context": _uninitialized(SolverContext),
        "domains": _uninitialized(ExactBaseDomains),
        "song_context": _uninitialized(ExactBaseSongContext),
        "timeline_frontier": _uninitialized(TimelineFrontierPrewarmResult),
        "candidate_limit": 51,
        "fg_scoring_bundle": object(),
        "fg_calc_song": {"notes": []},
    }


def _request(payload: dict | None = None) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.EXACT_BASE_SEARCH,
        request_id=17,
        worker_id=3,
        payload=payload or {},
    )


def test_execute_exact_base_search_requires_in_process_queues():
    response = execute_exact_base_search(
        _request(),
        in_process_queues=False,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
    )

    assert response.request_id == 17
    assert response.success is False
    assert response.error == (
        "EXACT_BASE_SEARCH requires in-process queues (typed payload is not IPC-safe)"
    )


def test_execute_exact_base_search_validates_typed_payload():
    response = execute_exact_base_search(
        _request({}),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
    )

    assert response.success is False
    assert response.error == (
        "Invalid payload for EXACT_BASE_SEARCH: context, domains, song_context, "
        "timeline_frontier, fg_scoring_bundle, fg_calc_song, candidate_limit"
    )


def test_execute_exact_base_search_runs_base_then_native_fg_with_typed_surface():
    payload = _payload()
    base_stats7 = np.arange(14, dtype=np.int32).reshape(2, 7)
    base = SimpleNamespace(candidate_surface=SimpleNamespace(base_stats7=base_stats7))
    calls: list[tuple[str, dict]] = []
    fg_map = {(1, 2, 3, 4, 5, 6, 7): object()}

    def _run(context, **kwargs):
        calls.append(("base", {"context": context, **kwargs}))
        return base

    def _score_fg(**kwargs):
        calls.append(("fg", kwargs))
        return fg_map

    response = execute_exact_base_search(
        _request(payload),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_pipeline_fn=_run,
        score_fg_fn=_score_fg,
    )

    assert response.success is True
    assert isinstance(response.result, ExactBaseOwnerResult)
    assert response.result.base_result is base
    assert response.result.fg_owner_score is fg_map
    assert [name for name, _kwargs in calls] == ["base", "fg"]
    assert calls[0][1]["context"] is payload["context"]
    assert calls[0][1]["domains"] is payload["domains"]
    assert calls[0][1]["song_context"] is payload["song_context"]
    assert calls[0][1]["timeline_frontier"] is payload["timeline_frontier"]
    assert calls[0][1]["candidate_limit"] == 51
    assert calls[0][1]["abort_requested"]() is False
    np.testing.assert_array_equal(calls[1][1]["base_stats7"], base_stats7)
    assert calls[1][1]["context"] is payload["context"]
    assert calls[1][1]["scoring_bundle"] is payload["fg_scoring_bundle"]
    assert calls[1][1]["calc_song"] is payload["fg_calc_song"]


def test_execute_exact_base_search_surfaces_pipeline_exception():
    response = execute_exact_base_search(
        _request(_payload()),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_pipeline_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("kernel failed")
        ),
    )

    assert response.success is False
    assert response.error == "RuntimeError: kernel failed"
