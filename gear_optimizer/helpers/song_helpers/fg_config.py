from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import logging

from ...solver.taichi_gem.force_greats.response_types import FgResponseSurface


logger = logging.getLogger(__name__)
def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def extract_fg_config(container: Any) -> dict[str, Any]:
    """
    Extract the ForceGreats `config` mapping from known payload shapes.

    Supported shapes:
    - result entry: {"data": {"ForceGreats": {"config": {...}}}}
    - persisted force payload: {"ForceGreats": {"config": {...}}}
    - retained entry row: {"force": {"ForceGreats": {"config": {...}}}}
    """
    payload = _coerce_dict(container)
    if not payload:
        return {}

    data_obj = _coerce_dict(payload.get("data"))
    cfg = _coerce_dict(_coerce_dict(data_obj.get("ForceGreats")).get("config"))
    if cfg:
        return cfg

    force_obj = _coerce_dict(payload.get("force"))
    cfg = _coerce_dict(_coerce_dict(force_obj.get("ForceGreats")).get("config"))
    if cfg:
        return cfg

    return _coerce_dict(_coerce_dict(payload.get("ForceGreats")).get("config"))


def is_nonzero_fg_config(config: Mapping[str, Any] | None) -> bool:
    cfg = _coerce_dict(config)
    if not cfg:
        return False
    total = 0
    for value in cfg.values():
        try:
            total += int(value or 0)
        except Exception as e:
            logger.debug(f"fg_config:is_nonzero_fg_config: {e}")
            continue
    return bool(total > 0)


def has_valid_fg_config(container: Any) -> bool:
    """
    Validate that a payload (or config dict) carries a non-zero FG config.
    """
    if isinstance(container, dict) and ("ForceGreats" in container or "data" in container or "force" in container):
        return is_nonzero_fg_config(extract_fg_config(container))
    if isinstance(container, dict):
        return is_nonzero_fg_config(container)
    return False


def require_response_surface(force_obj: Any) -> FgResponseSurface:
    """
    Return the persisted FG response surface from a force payload.

    The response surface is the canonical exact FG representation (it encodes
    Fever+Great overlap; forced-count configs cannot). Every persisted FG payload
    carries one, so a valid FG payload without it is invalid state.
    """
    payload = _coerce_dict(force_obj)
    surface_obj = payload.get("response_surface")
    if surface_obj is None:
        surface_obj = _coerce_dict(payload.get("ForceGreats")).get("response_surface")
    field_count = len(FgResponseSurface._fields)
    if not isinstance(surface_obj, (list, tuple)) or len(surface_obj) != field_count:
        raise ValueError(
            f"FG payload requires a persisted {field_count}-value response_surface; got {surface_obj!r}."
        )
    return FgResponseSurface(*[int(value) for value in surface_obj])
