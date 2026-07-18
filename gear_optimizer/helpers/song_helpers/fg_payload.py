from __future__ import annotations

from typing import Any

from ...solver.taichi_gem.force_greats.response_types import FgResponseSurface


_RETIRED_FORCE_META_FIELDS = frozenset({"config", "variant_applied", "enabled"})
_RETIRED_FIELDS = frozenset({"forced_counts", "forced_prefix_count"})


def _payload(container: Any) -> dict[str, Any]:
    if not isinstance(container, dict):
        return {}
    for key in ("data", "force"):
        nested = container.get(key)
        if isinstance(nested, dict):
            return nested
    return container


def require_response_surface(container: Any) -> FgResponseSurface:
    """Return the canonical persisted Force Greats replay surface."""
    payload = _payload(container)
    surface = payload.get("response_surface")
    if surface is None:
        force_meta = payload.get("ForceGreats")
        surface = force_meta.get("response_surface") if isinstance(force_meta, dict) else None
    field_count = len(FgResponseSurface._fields)
    if not isinstance(surface, (list, tuple)) or len(surface) != field_count:
        raise ValueError(
            f"FG payload requires a persisted {field_count}-value response_surface; got {surface!r}."
        )
    return FgResponseSurface(*[int(value) for value in surface])


def has_valid_fg_payload(container: Any) -> bool:
    try:
        require_response_surface(container)
    except (TypeError, ValueError):
        return False
    return True


def strip_retired_fg_fields(value: Any, *, parent_key: str = "") -> tuple[Any, int]:
    """Remove fields retired with the legacy Force Greats configuration model."""
    if isinstance(value, list):
        cleaned: list[Any] = []
        removed = 0
        for item in value:
            next_item, count = strip_retired_fg_fields(item)
            cleaned.append(next_item)
            removed += count
        return cleaned, removed
    if not isinstance(value, dict):
        return value, 0

    cleaned: dict[str, Any] = {}
    removed = 0
    for key, item in value.items():
        if key in _RETIRED_FIELDS or (
            parent_key == "ForceGreats" and key in _RETIRED_FORCE_META_FIELDS
        ):
            removed += 1
            continue
        next_item, count = strip_retired_fg_fields(item, parent_key=str(key))
        cleaned[str(key)] = next_item
        removed += count
    return cleaned, removed
