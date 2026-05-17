from gear_optimizer.solver.gpu_executor_fg import (
    execute_fg_download_global_best,
    execute_fg_reset_global_best,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_type: GpuRequestType, payload: dict | None) -> GpuRequest:
    return GpuRequest(request_type=request_type, request_id=30, worker_id=0, payload=payload)


def test_execute_fg_reset_global_best_requires_in_process_queues():
    response = execute_fg_reset_global_best(
        _request(GpuRequestType.FG_RESET_GLOBAL_BEST, {"n_genomes": 10}),
        in_process_queues=False,
        reset_fn=lambda *_args, **_kwargs: None,
    )

    assert response.success is False
    assert "requires in-process queues" in str(response.error)


def test_execute_fg_reset_global_best_forwards_normalized_values():
    calls = []

    response = execute_fg_reset_global_best(
        _request(GpuRequestType.FG_RESET_GLOBAL_BEST, {"n_genomes": "12", "song_slot": "3"}),
        in_process_queues=True,
        reset_fn=lambda n_genomes, *, session_slot: calls.append((n_genomes, session_slot)),
    )

    assert response.success is True
    assert response.result is None
    assert calls == [(12, 3)]


def test_execute_fg_download_global_best_requires_in_process_queues():
    response = execute_fg_download_global_best(
        _request(GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST, {"n_genomes": 10}),
        in_process_queues=False,
        download_fn=lambda *_args, **_kwargs: None,
    )

    assert response.success is False
    assert "requires in-process queues" in str(response.error)


def test_execute_fg_download_global_best_forwards_basic_download():
    calls = []

    def download_fn(n_genomes, *, session_slot):
        calls.append((n_genomes, session_slot))
        return {"ok": True}

    response = execute_fg_download_global_best(
        _request(GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST, {"n_genomes": "bad", "song_slot": "2"}),
        in_process_queues=True,
        download_fn=download_fn,
    )

    assert response.success is True
    assert response.result == {"ok": True}
    assert calls == [(0, 2)]


def test_execute_fg_download_global_best_forwards_topk_download():
    calls = []
    base_scores = [100, 90]
    keep_mask = [True, False]

    def download_fn(n_genomes, **kwargs):
        calls.append((n_genomes, kwargs))
        return {"topk": kwargs.get("topk")}

    response = execute_fg_download_global_best(
        _request(
            GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
            {
                "n_genomes": "8",
                "song_slot": "4",
                "topk": "2",
                "base_scores": base_scores,
                "keep_mask": keep_mask,
            },
        ),
        in_process_queues=True,
        download_fn=download_fn,
    )

    assert response.success is True
    assert response.result == {"topk": 2}
    assert calls == [
        (
            8,
            {
                "session_slot": 4,
                "topk": 2,
                "base_scores": base_scores,
                "keep_mask": keep_mask,
            },
        )
    ]
