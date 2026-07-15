from __future__ import annotations

from dataclasses import fields
from typing import Any

from gear_optimizer.solver.native_inflight_config import (
    NativeSong,
    NativeSongBundleState,
    NativeSongConfig,
    NativeSongDBState,
    NativeSongDecodeState,
    NativeSongFGState,
    NativeSongBaseState,
    NativeSongGPUInputs,
    NativeSongPostState,
    NativeSongPrepState,
    NativeSongRuntimeState,
)


def _field_names(cls: type) -> tuple[str, ...]:
    return tuple(field.name for field in fields(cls))


_FIELD_PATH_BY_NAME = {
    **{name: ("config",) for name in _field_names(NativeSongConfig)},
    **{name: ("gpu_inputs",) for name in _field_names(NativeSongGPUInputs)},
    "song_slot": ("runtime",),
    **{name: ("runtime", "prep") for name in _field_names(NativeSongPrepState)},
    **{name: ("runtime", "base") for name in _field_names(NativeSongBaseState)},
    **{name: ("runtime", "decode") for name in _field_names(NativeSongDecodeState)},
    **{name: ("runtime", "fg") for name in _field_names(NativeSongFGState)},
    **{name: ("runtime", "db") for name in _field_names(NativeSongDBState)},
    **{name: ("runtime", "bundle") for name in _field_names(NativeSongBundleState)},
    **{name: ("runtime", "post") for name in _field_names(NativeSongPostState)},
}


def _resolve_owner(root: object | None, path: tuple[str, ...]) -> object | None:
    current = root
    for segment in path:
        if current is None:
            return None
        current = getattr(current, segment, None)
    return current


def make_native_song(**kwargs: Any) -> NativeSong:
    """Build a NativeSong test fixture from flat keyword arguments."""
    config = NativeSongConfig()
    gpu_inputs = NativeSongGPUInputs()
    runtime = NativeSongRuntimeState()
    roots = {"config": config, "gpu_inputs": gpu_inputs, "runtime": runtime}
    assignments: list[tuple[object, str, Any]] = []
    unknown_fields: list[str] = []
    for key_raw, value in kwargs.items():
        key = str(key_raw)
        if hasattr(config, key):
            assignments.append((config, key, value))
            continue
        if hasattr(gpu_inputs, key):
            assignments.append((gpu_inputs, key, value))
            continue
        path = _FIELD_PATH_BY_NAME.get(key)
        owner = _resolve_owner(roots.get(path[0]), path[1:]) if path else None
        if owner is None:
            unknown_fields.append(key)
        else:
            assignments.append((owner, key, value))
    if unknown_fields:
        raise TypeError("Unexpected native song field(s): " + ", ".join(sorted(dict.fromkeys(unknown_fields))))
    for owner, key, value in assignments:
        setattr(owner, key, value)
    return NativeSong(config=config, gpu_inputs=gpu_inputs, runtime=runtime)
