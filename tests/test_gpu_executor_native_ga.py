from __future__ import annotations

from gear_optimizer.solver.gpu_executor_batching import execute_gpu_native_ga_run
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(payload: dict | None = None) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
        request_id=17,
        worker_id=3,
        payload=payload or {},
    )


def test_execute_gpu_native_ga_run_requires_in_process_queues():
    response = execute_gpu_native_ga_run(
        _request(),
        in_process_queues=False,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda **_kwargs: {},
    )

    assert response.request_id == 17
    assert response.success is False
    assert response.error == "GPU_NATIVE_GA_RUN requires in-process queues (avoid IPC pickling)"


def test_execute_gpu_native_ga_run_validates_required_payload_dicts():
    response = execute_gpu_native_ga_run(
        _request({"calc_song": [], "ref_arrays": {}}),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda **_kwargs: {},
    )

    assert response.success is False
    assert response.error == "Invalid payload for GPU_NATIVE_GA_RUN (expected calc_song/ref_arrays dicts)"


def test_execute_gpu_native_ga_run_forwards_typed_payload_to_runner():
    calls = []

    def _run_payload(**kwargs):
        calls.append(kwargs)
        return {"ok": True}

    response = execute_gpu_native_ga_run(
        _request(
            {
                "calc_song": {"notes": []},
                "ref_arrays": {"x": 1},
                "song_slot": "2",
                "n_generations": "4",
                "elite_count": "3",
                "mutation_rate": "0.25",
                "immigrant_rate": "0.05",
                "tournament_k": "5",
                "num_runs": "7",
                "n_genomes": "128",
                "init_heuristic_k": "9",
                "init_heuristic_copies": "11",
                "color_flags": {"rush": True},
                "cfg_data": {"selected_color": "rush"},
                "ga_seed": "123",
            }
        ),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=_run_payload,
    )

    assert response.success is True
    assert response.result == {"ok": True}
    assert calls[0]["calc_song"] == {"notes": []}
    assert calls[0]["ref_arrays"] == {"x": 1}
    assert calls[0]["song_slot"] == 2
    assert calls[0]["n_generations"] == 4
    assert calls[0]["elite_count"] == 3
    assert calls[0]["mutation_rate"] == 0.25
    assert calls[0]["immigrant_rate"] == 0.05
    assert calls[0]["tournament_k"] == 5
    assert calls[0]["num_runs"] == 7
    assert calls[0]["n_genomes"] == 128
    assert calls[0]["init_heuristic_k"] == 9
    assert calls[0]["init_heuristic_copies"] == 11
    assert calls[0]["color_flags"] == {"rush": True}
    assert calls[0]["cfg_data"] == {"selected_color": "rush"}
    assert calls[0]["ga_seed"] == 123
    assert calls[0]["abort_requested"]() is False


def test_execute_gpu_native_ga_run_surfaces_runner_exception():
    response = execute_gpu_native_ga_run(
        _request({"calc_song": {}, "ref_arrays": {}}),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("kernel failed")),
    )

    assert response.success is False
    assert response.error == "RuntimeError: kernel failed"
