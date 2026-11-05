from __future__ import annotations

from typing import Any

from gear_optimizer.frontier.types import FgResponseSurface


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
