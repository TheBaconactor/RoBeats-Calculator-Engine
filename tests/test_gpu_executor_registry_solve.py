from gear_optimizer.solver.gpu_executor_registry_solve import handle_solve_genomes_from_registry, request_song_slot
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
