from gear_optimizer.solver.gpu_executor_timeline import execute_precompute_timeline
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.PRECOMPUTE_TIMELINE,
        request_id=20,
        worker_id=0,
        payload=payload,
    )


def test_execute_precompute_timeline_validates_calc_song_and_ref_arrays():
    response = execute_precompute_timeline(
        _request({"ref_arrays": {"x": 1}, "song_slot": 2}),
        precompute_fn=lambda _calc_song, _ref_arrays, _song_slot: None,
    )

    assert response.success is False
    assert "calc_song/ref_arrays dicts" in str(response.error)

    response = execute_precompute_timeline(
        _request({"calc_song": {"metadata": {}}, "ref_arrays": [], "song_slot": 2}),
        precompute_fn=lambda _calc_song, _ref_arrays, _song_slot: None,
    )

    assert response.success is False
    assert "calc_song/ref_arrays dicts" in str(response.error)


def test_execute_precompute_timeline_forwards_payload_to_callback():
    calls = []
    calc_song = {"metadata": {"Song Name": "x"}}
    ref_arrays = {"Perfect Points": [1.0]}

    def precompute_fn(calc_song_arg, ref_arrays_arg, song_slot):
        calls.append((calc_song_arg, ref_arrays_arg, song_slot))

    response = execute_precompute_timeline(
        _request({"calc_song": calc_song, "ref_arrays": ref_arrays, "song_slot": "7"}),
        precompute_fn=precompute_fn,
    )

    assert response.success is True
    assert response.result is None
    assert calls == [(calc_song, ref_arrays, 7)]
