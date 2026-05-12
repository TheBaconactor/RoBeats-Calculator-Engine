import numpy as np

from gear_optimizer.solver.gpu_executor_fg_breakpoints import execute_fg_compute_breakpoints
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.FG_COMPUTE_BREAKPOINTS,
        request_id=50,
        worker_id=0,
        payload=payload,
    )


def test_execute_fg_compute_breakpoints_precomputes_timeline_before_empty_result():
    calls = []

    def precompute_fn(calc_song, ref_arrays, *, song_slot=0):
        calls.append((calc_song, ref_arrays, song_slot))

    response = execute_fg_compute_breakpoints(
        _request(
            {
                "ensure_timeline_precompute": True,
                "calc_song": {"song_data": {}},
                "ref_arrays": {"ok": True},
                "song_slot": 4,
                "n_sections": 0,
            }
        ),
        precompute_timeline_fn=precompute_fn,
        compute_matrix_fn=lambda **_kwargs: np.zeros((0, 0), dtype=np.int16),
    )

    assert response.success is True
    assert response.result.shape == (0, 0)
    assert calls == [({"song_data": {}}, {"ok": True}, 4)]


def test_execute_fg_compute_breakpoints_requires_calc_song_and_ref_arrays_for_precompute():
    response = execute_fg_compute_breakpoints(
        _request({"ensure_timeline_precompute": True, "song_slot": 1, "n_sections": 0}),
        precompute_timeline_fn=lambda *_args, **_kwargs: None,
        compute_matrix_fn=lambda **_kwargs: np.zeros((0, 0), dtype=np.int16),
    )

    assert response.success is False
    assert "calc_song/ref_arrays" in str(response.error)


def test_execute_fg_compute_breakpoints_validates_required_tables():
    response = execute_fg_compute_breakpoints(
        _request({"ftff_pairs": [(1, 2)], "base_stats_pairs": [(3, 4)], "n_sections": 1}),
        precompute_timeline_fn=lambda *_args, **_kwargs: None,
        compute_matrix_fn=lambda **_kwargs: np.zeros((1, 1), dtype=np.int16),
    )

    assert response.success is False
    assert "missing non_fever_base_by_ff/fp_cap_table" in str(response.error)


def test_execute_fg_compute_breakpoints_forwards_normalized_arrays_to_kernel():
    calls = []
    expected = np.asarray([[7, 8]], dtype=np.int16)

    def compute_matrix_fn(**kwargs):
        calls.append(kwargs)
        return expected

    response = execute_fg_compute_breakpoints(
        _request(
            {
                "ftff_pairs": [(10, 20)],
                "base_stats_pairs": np.asarray([[30, 40]], dtype=np.int64),
                "n_sections": 2,
                "song_slot": 3,
                "gem_scale_fever": 5,
                "non_fever_base_by_ff": np.zeros(161, dtype=np.int16),
                "fp_cap_table": np.zeros((161, 51), dtype=np.int16),
            }
        ),
        precompute_timeline_fn=lambda *_args, **_kwargs: None,
        compute_matrix_fn=compute_matrix_fn,
    )

    assert response.success is True
    assert response.result is expected
    assert len(calls) == 1
    call = calls[0]
    assert call["song_slot"] == 3
    assert call["gem_scale_fever"] == 5
    assert call["n_sections"] == 2
    np.testing.assert_array_equal(call["pair_ft"], np.asarray([10], dtype=np.int32))
    np.testing.assert_array_equal(call["pair_ff"], np.asarray([20], dtype=np.int32))
    np.testing.assert_array_equal(call["base_ft"], np.asarray([30], dtype=np.int32))
    np.testing.assert_array_equal(call["base_ff"], np.asarray([40], dtype=np.int32))
