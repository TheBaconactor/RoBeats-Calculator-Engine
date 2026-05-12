from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import logging
from typing import Any

import numpy as np

from gear_optimizer.solver.gpu_executor_types import GpuRequest

logger = logging.getLogger(__name__)

REGISTRY_COALESCE_SCALAR_FIELDS = (
    "song_slot",
    "total_budget",
    "gem_scale_fever",
    "use_exact_inner_solver",
    "is_p_ft",
    "is_s_ft",
    "is_p_ff",
    "is_s_ff",
    "is_p_pp",
    "is_s_pp",
    "is_p_cm",
    "is_s_cm",
    "is_p_fm",
    "is_s_fm",
    "is_p_ov",
    "is_s_ov",
)


class RegistryCoalesceSignatureBuilder:
    def __init__(
        self,
        *,
        ref_arrays_sig_fn: Callable[[Any], bytes | None],
        array_sig16_fn: Callable[[Any], bytes] | None = None,
    ) -> None:
        self._ref_arrays_sig_fn = ref_arrays_sig_fn
        self._array_sig_cache: dict[tuple[int, int, tuple[int, ...], tuple[int, ...], str], bytes] = {}
        self._object_sig_cache: dict[int, Any] = {}
        self._array_sig16_fn = array_sig16_fn
        if self._array_sig16_fn is None:
            try:
                from gear_optimizer.core.array_signature import array_sig16

                self._array_sig16_fn = array_sig16
            except Exception as e:
                logger.debug(f"gpu_executor_registry_coalesce:array_sig16: {e}")
                self._array_sig16_fn = None

    def array_sig(self, value: Any) -> tuple[Any, ...]:
        if value is None:
            return ("none",)
        try:
            arr = np.asarray(value)
        except Exception as e:
            logger.debug(f"gpu_executor_registry_coalesce:array_sig: {e}")
            return ("repr", type(value).__name__, repr(value))
        if arr.ndim == 0:
            try:
                return ("scalar", str(arr.dtype), repr(arr.item()))
            except Exception as e:
                logger.debug(f"gpu_executor_registry_coalesce:array_sig: {e}")
                return ("scalar", str(arr.dtype), repr(arr))
        try:
            arr_ptr = int(arr.__array_interface__["data"][0])
        except (ValueError, TypeError, KeyError, AttributeError):
            arr_ptr = int(id(arr))
        try:
            strides = tuple(int(x) for x in (arr.strides or ()))
        except (ValueError, TypeError, AttributeError):
            strides = ()
        key = (int(id(arr)), int(arr_ptr), tuple(int(x) for x in arr.shape), strides, str(arr.dtype))
        digest = self._array_sig_cache.get(key)
        if digest is None:
            try:
                arr_c = arr if arr.flags["C_CONTIGUOUS"] else np.ascontiguousarray(arr)
                h = hashlib.blake2b(digest_size=16)
                h.update(memoryview(arr_c).cast("B"))
                digest = h.digest()
            except Exception as e:
                logger.debug(f"gpu_executor_registry_coalesce:array_sig: {e}")
                digest = bytes(str(id(arr)), "utf-8")
            self._array_sig_cache[key] = digest
        return ("arr", key[2], key[3], key[4], digest)

    def object_sig(self, value: Any) -> Any:
        if value is None or isinstance(value, (int, float, bool, str, bytes)):
            return value
        if isinstance(value, np.ndarray):
            return self.array_sig(value)
        oid = int(id(value))
        cached = self._object_sig_cache.get(oid)
        if cached is not None:
            return cached
        if isinstance(value, dict):
            sig = (
                "dict",
                tuple((str(k), self.object_sig(value.get(k))) for k in sorted(value.keys(), key=lambda x: str(x))),
            )
            self._object_sig_cache[oid] = sig
            return sig
        if isinstance(value, (list, tuple)):
            sig = (type(value).__name__, tuple(self.object_sig(x) for x in value))
            self._object_sig_cache[oid] = sig
            return sig
        sig = ("obj", type(value).__name__, repr(value))
        self._object_sig_cache[oid] = sig
        return sig

    def scalar_key(self, payload: dict[str, Any]) -> tuple[int, ...]:
        vals: list[int] = []
        for field in REGISTRY_COALESCE_SCALAR_FIELDS:
            default = 90 if field == "total_budget" else 3 if field == "gem_scale_fever" else 0
            vals.append(int(payload.get(field, default) or default))
        return tuple(vals)

    def timeline_sig(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return self.object_sig(value)
        song_data = value.get("song_data")
        if not isinstance(song_data, dict):
            return self.object_sig(value)

        def _sig16(key_name: str, arr: Any) -> Any:
            sig = song_data.get(key_name)
            if isinstance(sig, (bytes, bytearray, memoryview)) and len(sig) == 16:
                return ("sig16", bytes(sig))
            if self._array_sig16_fn is not None:
                try:
                    return ("sig16", self._array_sig16_fn(arr))
                except Exception as e:
                    logger.debug(f"gpu_executor_registry_coalesce:sig16: {e}")
            return self.array_sig(arr)

        return (
            "timeline",
            self.object_sig(value.get("metadata")),
            _sig16("_timestamps_sig", song_data.get("timestamps")),
            _sig16("_chart_timestamps_sig", song_data.get("chart_timestamps")),
            _sig16("_note_types_sig", song_data.get("note_types")),
        )

    def ref_sig(self, value: Any) -> Any:
        if isinstance(value, dict):
            sig = self._ref_arrays_sig_fn(value)
            if sig is not None:
                return ("ref", bytes(sig))
        return self.object_sig(value)

    def payload_sig(self, payload: dict[str, Any]) -> tuple[Any, ...]:
        return (
            self.scalar_key(payload),
            self.timeline_sig(payload.get("timeline_grid")),
            self.ref_sig(payload.get("ref_arrays")),
            self.array_sig(payload.get("item_stats")),
            self.array_sig(payload.get("slot_start")),
            self.array_sig(payload.get("slot_count")),
            self.array_sig(payload.get("base_fixed_stats")),
        )


def plan_registry_coalesce_groups(
    requests: list[GpuRequest],
    *,
    payload_dict_fn: Callable[[GpuRequest], dict[str, Any]],
    signature_builder: RegistryCoalesceSignatureBuilder,
) -> list[list[GpuRequest]]:
    groups_by_sig: OrderedDict[tuple[Any, ...], list[GpuRequest]] = OrderedDict()
    groups: list[list[GpuRequest]] = []
    for req in requests:
        payload = payload_dict_fn(req)
        pop = payload.get("population_indices")
        if pop is None:
            groups.append([req])
            continue
        try:
            handle_raw = payload.get("registry_payload_handle")
            if handle_raw is not None:
                sig = (
                    signature_builder.scalar_key(payload),
                    ("handle", int(getattr(req, "worker_id", 0) or 0), int(handle_raw)),
                )
            else:
                sig = signature_builder.payload_sig(payload)
        except (ValueError, TypeError, KeyError, AttributeError):
            groups.append([req])
            continue
        groups_by_sig.setdefault(sig, []).append(req)
    groups.extend(list(groups_by_sig.values()))
    return groups


@dataclass(frozen=True)
class PackedRegistryPopulationChunk:
    staging: np.ndarray
    spans: list[tuple[int, int]]
    cur: int
    ok: bool


def registry_population_indices(payload: dict[str, Any]) -> np.ndarray | None:
    pop_arr = np.asarray(payload.get("population_indices"), dtype=np.int32)
    if pop_arr.ndim != 2 or int(pop_arr.shape[1]) != 9:
        return None
    if int(pop_arr.shape[0]) <= 0:
        return None
    return pop_arr


def ensure_registry_population_staging_buffer(
    existing: Any,
    *,
    n_total: int,
    max_genomes: int,
) -> np.ndarray:
    if (
        isinstance(existing, np.ndarray)
        and existing.ndim == 2
        and int(existing.shape[0]) >= int(n_total)
        and int(existing.shape[1]) == 9
    ):
        return existing
    staging_rows = max(int(n_total), int(max_genomes))
    return np.empty((int(staging_rows), 9), dtype=np.int32)


def pack_registry_population_chunk(
    requests: list[GpuRequest],
    *,
    staging: np.ndarray,
    resolved_payload_fn: Callable[[GpuRequest], tuple[dict[str, Any], str | None]],
) -> PackedRegistryPopulationChunk:
    spans: list[tuple[int, int]] = []
    cur = 0
    ok = True
    for req in requests:
        payload, err = resolved_payload_fn(req)
        if err:
            ok = False
            break
        pop_arr = registry_population_indices(payload)
        if pop_arr is None:
            ok = False
            break
        n = int(pop_arr.shape[0])
        staging[cur : cur + n, :] = pop_arr[:n, :]
        spans.append((cur, cur + n))
        cur += n
    return PackedRegistryPopulationChunk(
        staging=staging,
        spans=spans,
        cur=int(cur),
        ok=bool(ok),
    )
