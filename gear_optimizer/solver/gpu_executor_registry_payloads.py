from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequest


STATIC_REGISTRY_PAYLOAD_KEYS = (
    "item_stats",
    "slot_start",
    "slot_count",
    "base_fixed_stats",
    "timeline_grid",
    "ref_arrays",
)


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
        """
        Resolve registry-solve payloads that optionally use worker-side static handles.

        Workers may send only dynamic fields (population indices + flags) plus
        `registry_payload_handle` after first registration to avoid repeated IPC
        transfer of immutable arrays/dicts.
        """
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
