from __future__ import annotations

from tests.curves_support import synthetic_curves
from tests.songs_support import make_song
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
        _request({"timed_song": [], "curves": {}}),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda **_kwargs: {},
    )

    assert response.success is False
    assert response.error == "Invalid payload for GPU_NATIVE_GA_RUN (expected a TimedSong and StatCurves)"


def test_execute_gpu_native_ga_run_forwards_typed_payload_to_runner():
    calls = []
    fused_calls = []
    curves = synthetic_curves({})
    song = make_song([0.0, 0.5])

    def _run_payload(**kwargs):
        calls.append(kwargs)
        return {"ok": True}

    def _fused_fg(**kwargs):
        # Fused GA->FG owner step (Slice 3): receives the runs_payload + song-level
        # FG inputs and returns the per-base_components owner score map.
        fused_calls.append(kwargs)
        return {"owner_map": True}

    response = execute_gpu_native_ga_run(
        _request(
            {
                "timed_song": song,
                "curves": curves,
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
                "fg_scoring_bundle": object(),
            }
        ),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=_run_payload,
        fused_fg_fn=_fused_fg,
    )

    assert response.success is True
    # Slice 3: the GA response is the fused {runs_payload, fg_owner_score} dict.
    assert response.result == {"runs_payload": {"ok": True}, "fg_owner_score": {"owner_map": True}}
    assert fused_calls[0]["runs_payload"] == {"ok": True}
    assert fused_calls[0]["cfg_data"] == {"selected_color": "rush"}
    assert fused_calls[0]["song"] is song
    assert calls[0]["song"] is song
    assert calls[0]["curves"] is curves
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
        _request({"timed_song": make_song([0.0, 0.5]), "curves": synthetic_curves({})}),
        in_process_queues=True,
        abort_requested=lambda: False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("kernel failed")),
    )

    assert response.success is False
    assert response.error == "RuntimeError: kernel failed"
