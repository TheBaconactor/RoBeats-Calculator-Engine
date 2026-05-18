import numpy as np

from gear_optimizer.solver.gpu_executor_registry import (
    RegistryCoalesceSignatureBuilder,
    ensure_registry_population_staging_buffer,
    pack_registry_population_chunk,
    plan_registry_coalesce_groups,
    registry_population_indices,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _req(request_id: int, *, payload: dict, worker_id: int = 1) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=int(request_id),
        worker_id=int(worker_id),
        payload=payload,
    )


def _payload(*, population_indices=None, timestamps=None, song_slot: int = 1) -> dict:
    if population_indices is None:
        population_indices = np.arange(9, dtype=np.int32).reshape(1, 9)
    if timestamps is None:
        timestamps = np.array([0.0, 1.0, 2.0], dtype=np.float32)
    return {
        "population_indices": population_indices,
        "timeline_grid": {
            "metadata": {"Song Name": "registry-policy"},
            "song_data": {
                "timestamps": timestamps,
                "chart_timestamps": None,
                "note_types": None,
            },
        },
        "ref_arrays": {"Perfect Points": np.arange(8, dtype=np.float64)},
        "item_stats": np.arange(12, dtype=np.int16).reshape(3, 4),
        "slot_start": np.arange(9, dtype=np.int32),
        "slot_count": np.ones(9, dtype=np.int32),
        "base_fixed_stats": np.arange(10, dtype=np.int32),
        "song_slot": song_slot,
        "total_budget": 90,
        "gem_scale_fever": 3,
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


def _builder() -> RegistryCoalesceSignatureBuilder:
    def _sig16(arr) -> bytes:
        raw = np.ascontiguousarray(np.asarray(arr)).view(np.uint8).tobytes()
        return raw[:16].ljust(16, b"\0")

    return RegistryCoalesceSignatureBuilder(
        ref_arrays_sig_fn=lambda _ref_arrays: b"0123456789abcdef",
        array_sig16_fn=_sig16,
    )


def test_registry_coalesce_array_signature_distinguishes_transposed_views():
    builder = _builder()
    base = np.arange(16, dtype=np.float32).reshape(4, 4)

    assert builder.array_sig(base) != builder.array_sig(base.T)


def test_registry_coalesce_groups_matching_payloads_by_signature():
    builder = _builder()
    timestamps = np.array([0.0, 1.0, 2.0], dtype=np.float32)
    req_a = _req(1, payload=_payload(timestamps=timestamps))
    req_b = _req(2, payload=_payload(timestamps=timestamps.copy()))

    groups = plan_registry_coalesce_groups(
        [req_a, req_b],
        payload_dict_fn=lambda req: req.payload,
        signature_builder=builder,
    )

    assert [[req.request_id for req in group] for group in groups] == [[1, 2]]


def test_registry_coalesce_groups_handle_payloads_by_worker_and_handle():
    builder = _builder()
    payload_a = {**_payload(), "registry_payload_handle": 7}
    payload_b = {**_payload(), "registry_payload_handle": 7}
    payload_c = {**_payload(), "registry_payload_handle": 7}
    req_a = _req(1, payload=payload_a, worker_id=1)
    req_b = _req(2, payload=payload_b, worker_id=1)
    req_c = _req(3, payload=payload_c, worker_id=2)

    groups = plan_registry_coalesce_groups(
        [req_a, req_b, req_c],
        payload_dict_fn=lambda req: req.payload,
        signature_builder=builder,
    )

    assert [[req.request_id for req in group] for group in groups] == [[1, 2], [3]]


def test_registry_coalesce_keeps_missing_population_as_singleton_barrier():
    builder = _builder()
    req_a = _req(1, payload={"song_slot": 1})
    req_b = _req(2, payload=_payload())

    groups = plan_registry_coalesce_groups(
        [req_a, req_b],
        payload_dict_fn=lambda req: req.payload,
        signature_builder=builder,
    )

    assert [[req.request_id for req in group] for group in groups] == [[1], [2]]


def test_registry_population_indices_accepts_only_nonempty_n_by_9_arrays():
    assert registry_population_indices({"population_indices": np.arange(18).reshape(2, 9)}).shape == (2, 9)
    assert registry_population_indices({"population_indices": np.arange(8).reshape(1, 8)}) is None
    assert registry_population_indices({"population_indices": np.empty((0, 9), dtype=np.int32)}) is None


def test_ensure_registry_population_staging_buffer_reuses_or_grows_buffer():
    existing = np.empty((10, 9), dtype=np.int32)

    assert ensure_registry_population_staging_buffer(existing, n_total=5, max_genomes=16) is existing

    grown = ensure_registry_population_staging_buffer(existing, n_total=12, max_genomes=16)

    assert grown.shape == (16, 9)
    assert grown.dtype == np.int32


def test_pack_registry_population_chunk_preserves_spans_and_data():
    req_a = _req(1, payload=_payload(population_indices=np.arange(18, dtype=np.int32).reshape(2, 9)))
    req_b = _req(2, payload=_payload(population_indices=np.arange(18, 27, dtype=np.int32).reshape(1, 9)))
    staging = np.empty((3, 9), dtype=np.int32)

    packed = pack_registry_population_chunk(
        [req_a, req_b],
        staging=staging,
        resolved_payload_fn=lambda req: (req.payload, None),
    )

    assert packed.ok is True
    assert packed.cur == 3
    assert packed.spans == [(0, 2), (2, 3)]
    assert packed.staging[:2, :].tolist() == req_a.payload["population_indices"].tolist()
    assert packed.staging[2:3, :].tolist() == req_b.payload["population_indices"].tolist()


def test_pack_registry_population_chunk_reports_invalid_payload():
    req = _req(1, payload=_payload(population_indices=np.arange(8, dtype=np.int32).reshape(1, 8)))
    staging = np.empty((1, 9), dtype=np.int32)

    packed = pack_registry_population_chunk(
        [req],
        staging=staging,
        resolved_payload_fn=lambda request: (request.payload, None),
    )

    assert packed.ok is False
    assert packed.cur == 0
    assert packed.spans == []
