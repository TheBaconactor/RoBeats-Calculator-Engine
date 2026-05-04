"""Side-effect-free parsing helpers shared across runtime modules."""

from __future__ import annotations

import os
import configparser
from collections.abc import Mapping
from typing import Any

TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})
TRUTHY_ENV_VALUES = TRUTHY_VALUES


def truthy(value: Any, *, extra_truthy: tuple[str, ...] = ()) -> bool:
    """Return True when a raw config/env value is a recognized truthy token."""
    token = str(value or "").strip().lower()
    return token in TRUTHY_VALUES or token in extra_truthy


def env_flag(name: str, default: str = "0", *, environ: Mapping[str, str] | None = None) -> bool:
    """Read a boolean environment flag without importing the env singleton."""
    source = os.environ if environ is None else environ
    return truthy(source.get(name, default))


def env_get(name: str, default: Any = None, *, environ: Mapping[str, str] | None = None) -> Any:
    """Read an environment value with the same semantics as `os.environ.get`."""
    source = os.environ if environ is None else environ
    return source.get(name, default)


def env_int(name: str, default: int, *, environ: Mapping[str, str] | None = None) -> int:
    """Read an integer environment value, returning the default on missing/invalid input."""
    source = os.environ if environ is None else environ
    raw = source.get(name, str(default))
    try:
        return int(str(raw or str(default)).strip())
    except (TypeError, ValueError):
        return int(default)


def env_str(name: str, default: str = "", *, environ: Mapping[str, str] | None = None) -> str:
    """Read a string environment value, returning the default on missing input."""
    source = os.environ if environ is None else environ
    raw = source.get(name, default)
    return str(raw if raw is not None else default).strip()


def env_float(name: str, default: float, *, environ: Mapping[str, str] | None = None) -> float:
    """Read a float environment value, returning the default on missing/invalid input."""
    source = os.environ if environ is None else environ
    raw = source.get(name, str(default))
    try:
        text = str(raw).strip()
        if not text:
            return float(default)
        return float(text)
    except (TypeError, ValueError):
        return float(default)


def config_bool(cfg: Any, section: str, key: str, *, default: bool = False) -> bool:
    """Read a boolean config value while tolerating ConfigParser variants."""
    try:
        return bool(cfg.getboolean(section, key, fallback=default))
    except (AttributeError, TypeError, ValueError, configparser.Error):
        try:
            raw = cfg.get(section, key, fallback=str(int(bool(default))))
        except (AttributeError, TypeError, ValueError, configparser.Error):
            return bool(default)
        return truthy(raw)
