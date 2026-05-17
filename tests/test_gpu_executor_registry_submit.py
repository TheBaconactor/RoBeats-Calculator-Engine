import numpy as np

from gear_optimizer.solver.gpu_executor_registry import (
    build_registry_solve_request_payload,
    expected_registry_result_count,
    should_retry_unknown_registry_handle,
)
from gear_optimizer.solver.gpu_executor_types import GpuResponse


def test_build_registry_solve_request_payload_inlines_static_payload():
    entry = {"handle": 42}
    payload = build_registry_solve_request_payload(
        {"population_indices": [[0] * 9], "total_budget": 90},
        entry,
        inline_static=True,
        static_payload={
            "item_stats": "items",
            "slot_start": "starts",
            "slot_count": "counts",
            "base_fixed_stats": "fixed",
            "timeline_grid": "timeline",
            "ref_arrays": "refs",
        },
    )

    assert payload["registry_payload_handle"] == 42
    assert payload["registry_payload_inline"] is True
    assert payload["population_indices"] == [[0] * 9]
    assert payload["item_stats"] == "items"
    assert payload["timeline_grid"] == "timeline"


def test_build_registry_solve_request_payload_strips_static_payload_when_handle_registered():
    entry = {"handle": 7}
    payload = build_registry_solve_request_payload(
        {
            "population_indices": [[0] * 9],
            "item_stats": "items",
            "slot_start": "starts",
            "slot_count": "counts",
            "base_fixed_stats": "fixed",
            "timeline_grid": "timeline",
            "ref_arrays": "refs",
        },
        entry,
        inline_static=False,
    )

    assert payload["registry_payload_handle"] == 7
    assert payload["registry_payload_inline"] is False
    assert "population_indices" in payload
    assert "item_stats" not in payload
    assert "slot_start" not in payload
    assert "slot_count" not in payload
    assert "base_fixed_stats" not in payload
    assert "timeline_grid" not in payload
    assert "ref_arrays" not in payload


def test_should_retry_unknown_registry_handle_only_for_registered_handle_failure():
    unknown = GpuResponse(request_id=1, success=False, error="Unknown registry payload handle=7")
    other = GpuResponse(request_id=2, success=False, error="boom")
    ok = GpuResponse(request_id=3, success=True, result=[])

    assert should_retry_unknown_registry_handle(unknown, inline_static=False) is True
    assert should_retry_unknown_registry_handle(unknown, inline_static=True) is False
    assert should_retry_unknown_registry_handle(other, inline_static=False) is False
    assert should_retry_unknown_registry_handle(ok, inline_static=False) is False


def test_expected_registry_result_count_reads_array_or_sequence_length():
    assert expected_registry_result_count(np.zeros((3, 9), dtype=np.int32)) == 3
    assert expected_registry_result_count([[0] * 9, [1] * 9]) == 2
    assert expected_registry_result_count(object()) == 0
