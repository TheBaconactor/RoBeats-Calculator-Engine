from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["export_general_meta_json", "run_general_meta"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(".app", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
