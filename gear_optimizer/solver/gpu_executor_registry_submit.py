from __future__ import annotations

from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuResponse

REGISTRY_STATIC_PAYLOAD_KEYS = (
    "item_stats",
    "slot_start",
    "slot_count",
    "base_fixed_stats",
    "timeline_grid",
    "ref_arrays",
)


def build_registry_solve_request_payload(
    base_payload: dict[str, Any],
    entry: dict[str, Any],
    *,
    inline_static: bool,
    static_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(base_payload or {})
    payload["registry_payload_handle"] = int(entry.get("handle", 0) or 0)
    payload["registry_payload_inline"] = bool(inline_static)
    if inline_static:
        if static_payload:
            payload.update(static_payload)
    else:
        for key in REGISTRY_STATIC_PAYLOAD_KEYS:
            payload.pop(key, None)
    return payload


def should_retry_unknown_registry_handle(response: GpuResponse, *, inline_static: bool) -> bool:
    if inline_static or bool(getattr(response, "success", False)):
        return False
    err_text = str(getattr(response, "error", "") or "")
    return "Unknown registry payload handle" in err_text


def expected_registry_result_count(population_indices: Any) -> int:
    try:
        return int(getattr(population_indices, "shape", [len(population_indices)])[0])
    except (ValueError, TypeError, AttributeError):
        return 0
