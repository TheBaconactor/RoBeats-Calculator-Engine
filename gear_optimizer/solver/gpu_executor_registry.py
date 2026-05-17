from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)

REGISTRY_STATIC_PAYLOAD_KEYS = (
    "item_stats",
    "slot_start",
    "slot_count",
    "base_fixed_stats",
    "timeline_grid",
    "ref_arrays",
)

STATIC_REGISTRY_PAYLOAD_KEYS = REGISTRY_STATIC_PAYLOAD_KEYS


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


@dataclass(frozen=True)
class RegistryPayloadCacheSettings:
    max_entries: int


def load_registry_payload_cache_settings(env_get_fn: Callable[[str, str], Any]) -> RegistryPayloadCacheSettings:
    try:
        max_entries = int(env_get_fn("GPU_EXECUTOR_REGISTRY_PAYLOAD_CACHE_MAX", "1024") or "1024")
    except (ValueError, TypeError):
        max_entries = 1024
    return RegistryPayloadCacheSettings(max_entries=max(64, int(max_entries)))


class RegistryPayloadCache:
    def __init__(self, *, max_entries: int) -> None:
        self.max_entries = max(1, int(max_entries))
        self._cache: OrderedDict[tuple[int, int], dict[str, Any]] = OrderedDict()

    def clear(self) -> None:
        self._cache.clear()

    def cache_static(self, worker_id: int, handle: int, static_payload: dict[str, Any]) -> None:
        key = (int(worker_id), int(handle))
        self._cache[key] = dict(static_payload)
        self._cache.move_to_end(key)
        while len(self._cache) > int(self.max_entries):
            self._cache.popitem(last=False)

    def resolve(
        self,
        request: GpuRequest,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        handle_raw = payload.get("registry_payload_handle")
        if handle_raw is None:
            return payload, None

        try:
            handle = int(handle_raw)
        except (ValueError, TypeError):
            return payload, f"Invalid registry payload handle: {handle_raw!r}"

        worker_id = int(getattr(request, "worker_id", 0) or 0)
        cache_key = (worker_id, handle)
        inline = bool(payload.get("registry_payload_inline", False))

        static_payload: dict[str, Any] | None = None
        if inline:
            missing = [k for k in STATIC_REGISTRY_PAYLOAD_KEYS if k not in payload]
            if missing:
                return payload, f"Invalid inline registry payload (missing {','.join(missing)})"
            static_payload = {k: payload[k] for k in STATIC_REGISTRY_PAYLOAD_KEYS}
            self.cache_static(worker_id, handle, static_payload)
        else:
            static_payload = self._cache.get(cache_key)
            if static_payload is None:
                return payload, f"Unknown registry payload handle={handle} for worker_id={worker_id}"
            self._cache.move_to_end(cache_key)

        resolved = dict(payload)
        for key in STATIC_REGISTRY_PAYLOAD_KEYS:
            if key not in resolved and static_payload is not None:
                resolved[key] = static_payload[key]
        return resolved, None


@dataclass(frozen=True)
class LoadRefsOutcome:
    response: GpuResponse
    last_ref_arrays_sig: bytes | None


def execute_load_refs(
    request: GpuRequest,
    *,
    last_ref_arrays_sig: bytes | None,
    load_ref_arrays_fn,
    ref_arrays_sig_fn,
) -> LoadRefsOutcome:
    ref_arrays = request.payload["ref_arrays"]
    sig = ref_arrays_sig_fn(ref_arrays)
    if sig is None or sig != last_ref_arrays_sig:
        load_ref_arrays_fn(ref_arrays)
        last_ref_arrays_sig = sig

    return LoadRefsOutcome(
        response=GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        ),
        last_ref_arrays_sig=last_ref_arrays_sig,
    )


def ref_arrays_sig(ref_arrays: Any) -> bytes | None:
    try:
        from .taichi_gem.api.initialization import _ref_arrays_sig as _taichi_ref_arrays_sig
    except Exception as e:
        logger.debug(f"gpu_executor_registry:ref_arrays_sig: {e}")
        return None
    try:
        return _taichi_ref_arrays_sig(ref_arrays)
    except Exception as e:
        logger.debug(f"gpu_executor_registry:ref_arrays_sig: {e}")
        return None
