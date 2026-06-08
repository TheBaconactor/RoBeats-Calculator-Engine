from __future__ import annotations

import inspect

from gear_optimizer.solver import gpu_executor_batching
from gear_optimizer.solver.gpu_executor_batching import execute_force_greats_response_frontier_score_batch
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(payload: dict | None = None) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH,
        request_id=23,
        worker_id=3,
        payload=payload or {},
    )


def test_execute_force_greats_response_frontier_score_batch_defaults_to_gpu_owner_runner():
    src = inspect.getsource(gpu_executor_batching.execute_force_greats_response_frontier_score_batch)
    assert "score_prepared_force_greats_response_frontier_batch_on_gpu_owner as run_payload_fn" in src
    assert "score_prepared_force_greats_response_frontier_batch_raw_gpu as run_payload_fn" not in src


def test_execute_force_greats_response_frontier_score_batch_requires_in_process_queues():
    response = execute_force_greats_response_frontier_score_batch(
        _request(),
        in_process_queues=False,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda *_args, **_kwargs: [],
    )

    assert response.request_id == 23
    assert response.success is False
    assert response.error == "FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH requires in-process queues (avoid IPC pickling)"


def test_execute_force_greats_response_frontier_score_batch_validates_required_payload():
    response = execute_force_greats_response_frontier_score_batch(
        _request({}),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda *_args, **_kwargs: [],
    )

    assert response.success is False
    assert response.error == "Invalid payload for FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH (expected prepared batch)"


def test_execute_force_greats_response_frontier_score_batch_forwards_payload_to_runner():
    calls: list[object] = []

    def _run_payload(batch):
        calls.append(batch)
        return [{"fg_score": 777}]

    batch = object()
    response = execute_force_greats_response_frontier_score_batch(
        _request(
            {
                "batch": batch,
            }
        ),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=_run_payload,
    )

    assert response.success is True
    assert response.result == [{"fg_score": 777}]
    assert calls == [batch]


def test_execute_force_greats_response_frontier_score_batch_records_owner_timing():
    timing: dict[str, float] = {}

    response = execute_force_greats_response_frontier_score_batch(
        _request(
            {
                "batch": object(),
                "timing": timing,
            }
        ),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda *_args, **_kwargs: [],
    )

    assert response.success is True
    assert timing["owner_exec_s"] >= 0.0
    assert timing["owner_queue_s"] >= 0.0


def test_execute_force_greats_response_frontier_score_batch_surfaces_runner_exception():
    response = execute_force_greats_response_frontier_score_batch(
        _request({"batch": object()}),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("kernel failed")),
    )

    assert response.success is False
    assert response.error == "RuntimeError: kernel failed"
