"""
Centralized fallback diagnostics.

This module provides:
- `warn_fallback(...)`: emit a visible warning every time a fallback path is used.
- `FallbackAwareConfigParser`: ConfigParser drop-in that warns when fallback values are used.
"""

from __future__ import annotations

import configparser
import os
import sys
import threading
from typing import Any


_TRUTHY = frozenset({"1", "true", "yes", "on"})
_COUNTS_LOCK = threading.Lock()
_COUNTS_BY_SITE: dict[str, int] = {}
_UNSET = configparser._UNSET


def _is_test_runtime() -> bool:
    # Auto-enable fallback warnings in pytest runs without requiring env setup.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return "pytest" in sys.modules


def _is_enabled() -> bool:
    raw = os.environ.get("METAFINDER_FALLBACK_WARN")
    if raw is not None:
        return str(raw).strip().lower() in _TRUTHY
    return _is_test_runtime()


def _include_count() -> bool:
    raw = str(os.environ.get("METAFINDER_FALLBACK_WARN_COUNT", "1") or "").strip().lower()
    return raw in _TRUTHY


def warn_fallback(site: str, reason: str, *, context: dict[str, Any] | None = None, exc: BaseException | None = None) -> None:
    """
    Emit a runtime warning for a fallback path.

    Notes:
    - Warnings are intentionally emitted on every fallback event (no de-dup),
      so callers can detect "constant fallback" behavior from logs.
    - Outside tests, warnings are disabled by default unless explicitly enabled.
    - Set `METAFINDER_FALLBACK_WARN=1` to force-enable or `=0` to disable.
    """
    if not _is_enabled():
        return

    site_key = str(site or "unknown")
    with _COUNTS_LOCK:
        count = int(_COUNTS_BY_SITE.get(site_key, 0)) + 1
        _COUNTS_BY_SITE[site_key] = count

    parts = [f"[FALLBACK][{site_key}] {reason}"]
    if context:
        try:
            ctx = ", ".join(f"{k}={context[k]!r}" for k in sorted(context))
        except Exception:
            ctx = repr(context)
        if ctx:
            parts.append(f"context: {ctx}")
    if exc is not None:
        parts.append(f"exc={type(exc).__name__}: {exc}")
    if _include_count():
        parts.append(f"count={count}")

    msg = " | ".join(parts)
    try:
        print(msg, file=sys.stderr, flush=True)
    except Exception:
        pass


class FallbackAwareConfigParser(configparser.ConfigParser):
    """
    ConfigParser variant that warns when fallback values are used.

    It preserves existing call signatures and remains a drop-in replacement.
    """

    def _warn_missing(self, method: str, section: str, option: str, fallback: Any) -> None:
        warn_fallback(
            f"config.{method}.missing",
            "config option missing, using fallback",
            context={"section": section, "option": option, "fallback": fallback},
        )

    def _warn_invalid(self, method: str, section: str, option: str, fallback: Any, exc: BaseException) -> None:
        warn_fallback(
            f"config.{method}.invalid",
            "invalid config value, using fallback",
            context={"section": section, "option": option, "fallback": fallback},
            exc=exc,
        )

    def get(self, section, option, *, raw=False, vars=None, fallback=_UNSET):  # noqa: A003
        if fallback is not _UNSET:
            has_val = self.has_section(section) and self.has_option(section, option)
            if not has_val:
                self._warn_missing("get", str(section), str(option), fallback)
        return super().get(section, option, raw=raw, vars=vars, fallback=fallback)

    def getint(self, section, option, *, raw=False, vars=None, fallback=_UNSET):  # noqa: A003
        if fallback is not _UNSET:
            has_val = self.has_section(section) and self.has_option(section, option)
            if not has_val:
                self._warn_missing("getint", str(section), str(option), fallback)
                return int(fallback)
        try:
            return super().getint(section, option, raw=raw, vars=vars, fallback=fallback)
        except Exception as exc:
            if fallback is _UNSET:
                raise
            self._warn_invalid("getint", str(section), str(option), fallback, exc)
            return int(fallback)

    def getfloat(self, section, option, *, raw=False, vars=None, fallback=_UNSET):  # noqa: A003
        if fallback is not _UNSET:
            has_val = self.has_section(section) and self.has_option(section, option)
            if not has_val:
                self._warn_missing("getfloat", str(section), str(option), fallback)
                return float(fallback)
        try:
            return super().getfloat(section, option, raw=raw, vars=vars, fallback=fallback)
        except Exception as exc:
            if fallback is _UNSET:
                raise
            self._warn_invalid("getfloat", str(section), str(option), fallback, exc)
            return float(fallback)

    def getboolean(self, section, option, *, raw=False, vars=None, fallback=_UNSET):  # noqa: A003
        if fallback is not _UNSET:
            has_val = self.has_section(section) and self.has_option(section, option)
            if not has_val:
                self._warn_missing("getboolean", str(section), str(option), fallback)
                return bool(fallback)
        try:
            return super().getboolean(section, option, raw=raw, vars=vars, fallback=fallback)
        except Exception as exc:
            if fallback is _UNSET:
                raise
            self._warn_invalid("getboolean", str(section), str(option), fallback, exc)
            return bool(fallback)
