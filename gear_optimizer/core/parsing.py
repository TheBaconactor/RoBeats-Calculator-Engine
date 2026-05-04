"""Side-effect-free parsing helpers shared across runtime modules."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})
TRUTHY_ENV_VALUES = TRUTHY_VALUES


def normalized_token(value: Any) -> str:
    """Normalize config/env tokens for comparisons."""
    return str(value or "").strip().lower()


def truthy(value: Any, *, extra_truthy: tuple[str, ...] = ()) -> bool:
    """Return True when a raw config/env value is a recognized truthy token."""
    token = normalized_token(value)
    return token in TRUTHY_VALUES or token in extra_truthy


def env_flag(name: str, default: str = "0", *, environ: Mapping[str, str] | None = None) -> bool:
    """Read a boolean environment flag without importing the env singleton."""
    source = os.environ if environ is None else environ
    return truthy(source.get(name, default))


def env_int(name: str, default: int, *, environ: Mapping[str, str] | None = None) -> int:
    """Read an integer environment value, returning the default on missing/invalid input."""
    source = os.environ if environ is None else environ
    raw = source.get(name, str(default))
    try:
        return int(str(raw or str(default)).strip())
    except Exception:
        return int(default)


def env_float(name: str, default: float, *, environ: Mapping[str, str] | None = None) -> float:
    """Read a float environment value, returning the default on missing/invalid input."""
    source = os.environ if environ is None else environ
    raw = source.get(name, str(default))
    try:
        return float(str(raw or str(default)).strip())
    except Exception:
        return float(default)


def config_bool(cfg: Any, section: str, key: str, *, default: bool = False) -> bool:
    """Read a boolean config value while tolerating ConfigParser variants."""
    try:
        return bool(cfg.getboolean(section, key, fallback=default))
    except Exception:
        try:
            raw = cfg.get(section, key, fallback=str(int(bool(default))))
        except Exception:
            return bool(default)
        return truthy(raw)
