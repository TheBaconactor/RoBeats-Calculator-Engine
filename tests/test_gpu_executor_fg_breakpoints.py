from gear_optimizer.solver.gpu_executor_fg import execute_fg_compute_breakpoints
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.FG_COMPUTE_BREAKPOINTS,
        request_id=50,
        worker_id=0,
        payload=payload,
    )


def test_execute_fg_compute_breakpoints_is_removed():
    calls = []

    response = execute_fg_compute_breakpoints(
        _request(
            {
                "ensure_timeline_precompute": True,
                "calc_song": {"song_data": {}},
                "ref_arrays": {"ok": True},
                "song_slot": 4,
                "n_sections": 1,
            }
        ),
        precompute_timeline_fn=lambda *_args, **_kwargs: calls.append(True),
        compute_matrix_fn=lambda **_kwargs: None,
    )

    assert response.success is False
    assert "cap-free prefix frontier" in str(response.error)
    assert calls == []
