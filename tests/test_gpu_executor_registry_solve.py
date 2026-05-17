from gear_optimizer.solver.gpu_executor_registry import (
    execute_solve_genomes_from_registry,
    handle_solve_genomes_from_registry,
    request_song_slot,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _request(payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=10,
        worker_id=0,
        payload=payload,
    )


def test_request_song_slot_normalizes_payload_value():
    assert request_song_slot(_request({"song_slot": "7"})) == 7
    assert request_song_slot(_request({"song_slot": None})) == 0
    assert request_song_slot(_request({"song_slot": "bad"})) == 0
    assert request_song_slot(_request(None)) == 0


def test_handle_solve_genomes_from_registry_forwards_normalized_song_slot():
    seen = []

    def execute_fn(request, song_slot):
        seen.append((request.request_id, song_slot))
        return GpuResponse(request_id=request.request_id, success=True, result={"song_slot": song_slot})

    response = handle_solve_genomes_from_registry(_request({"song_slot": "5"}), execute_fn=execute_fn)

    assert response.success is True
    assert response.result == {"song_slot": 5}
    assert seen == [(10, 5)]


def _payload() -> dict:
    return {
        "population_indices": [[1, 2, 3, 4, 5, 6, 7, 8, 9]],
        "timeline_grid": {"song_data": {}},
        "ref_arrays": {"Perfect Points": [1.0]},
        "item_stats": "items",
        "slot_start": "starts",
        "slot_count": "counts",
        "base_fixed_stats": "fixed",
        "is_p_ft": 0,
        "is_s_ft": 0,
        "is_p_ff": 0,
        "is_s_ff": 0,
        "is_p_pp": 0,
        "is_s_pp": 0,
        "is_p_cm": 0,
        "is_s_cm": 0,
        "is_p_fm": 0,
        "is_s_fm": 0,
        "is_p_ov": 0,
        "is_s_ov": 0,
    }


def test_execute_solve_genomes_from_registry_uploads_inputs_and_updates_ref_sig():
    payload = _payload()
    calls = []

    result = execute_solve_genomes_from_registry(
        _request(payload),
        song_slot=0,
        in_process_queues=False,
        last_ref_arrays_sig=None,
        resolve_payload_fn=lambda request: (request.payload, None),
        ref_arrays_sig_fn=lambda _ref_arrays: b"sig",
        default_song_slot_for_worker_fn=lambda worker_id: 40 + int(worker_id),
        load_ref_arrays_fn=lambda ref_arrays: calls.append(("refs", ref_arrays)),
        ga_upload_item_stats_fn=lambda *args: calls.append(("items", args)),
        ga_upload_base_fixed_stats_fn=lambda base_fixed_stats: calls.append(("fixed", base_fixed_stats)),
        solve_genomes_from_registry_fn=lambda **kwargs: calls.append(("solve", kwargs)) or ["ok"],
    )

    assert result.response.success is True
    assert result.response.result == ["ok"]
    assert result.last_ref_arrays_sig == b"sig"
    assert calls[0] == ("refs", payload["ref_arrays"])
    assert calls[1] == ("items", ("items", "starts", "counts"))
    assert calls[2] == ("fixed", "fixed")
    assert calls[3][0] == "solve"
    assert calls[3][1]["song_slot"] == 40


def test_execute_solve_genomes_from_registry_returns_resolve_error_without_uploads():
    calls = []

    result = execute_solve_genomes_from_registry(
        _request({}),
        song_slot=0,
        in_process_queues=True,
        last_ref_arrays_sig=b"old",
        resolve_payload_fn=lambda _request: ({}, "bad payload"),
        ref_arrays_sig_fn=lambda _ref_arrays: b"new",
        default_song_slot_for_worker_fn=lambda _worker_id: 1,
        load_ref_arrays_fn=lambda _ref_arrays: calls.append("refs"),
        ga_upload_item_stats_fn=lambda *args: calls.append("items"),
        ga_upload_base_fixed_stats_fn=lambda _base_fixed_stats: calls.append("fixed"),
        solve_genomes_from_registry_fn=lambda **_kwargs: calls.append("solve"),
    )

    assert result.response.success is False
    assert result.response.error == "bad payload"
    assert result.last_ref_arrays_sig == b"old"
    assert calls == []
