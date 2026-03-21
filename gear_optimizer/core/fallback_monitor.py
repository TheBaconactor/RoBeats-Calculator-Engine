"""
Centralized fallback diagnostics and fail-fast policy.

This module provides:
- `warn_fallback(...)`: emit a warning/log event whenever a fallback path is used.
- `FallbackAwareConfigParser`: ConfigParser drop-in that warns when fallback values are used.

Policy knobs (environment variables):
- `METAFINDER_FALLBACK_WARN`:
    - truthy -> enable warning output to stderr
    - falsy  -> disable warning output to stderr
    - unset  -> defaults to disabled (quiet console; structured logs are opt-in)
- `METAFINDER_FALLBACK_STRICT`:
    - truthy -> raise on fallback sites (except allowlisted prefixes)
    - falsy  -> never raise automatically
    - unset  -> defaults to `GPU_STRICT` (and to true when unset)
- `METAFINDER_FALLBACK_STRICT_ALL`:
    - truthy -> strict mode applies to all sites (ignore allowlist)
- `METAFINDER_FALLBACK_ALLOW`:
    - comma-separated site prefixes exempt from strict raises
    - default: "config.,env." (diagnostic-only defaults for config/env parsing)
- `METAFINDER_FALLBACK_LOG_PATH`:
    - JSONL path for structured fallback events
    - default: disabled (unset/empty)
"""

from __future__ import annotations

import configparser
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any


_TRUTHY = frozenset({"1", "true", "yes", "on"})
_COUNTS_LOCK = threading.Lock()
_COUNTS_BY_SITE: dict[str, int] = {}
# configparser._UNSET is a private sentinel and isn't typed in stdlib stubs.
_UNSET: Any = getattr(configparser, "_UNSET", object())

_LOG_LOCK = threading.Lock()
_LOG_FP = None
_LOG_OPEN_FAILED = False


def _sample_every() -> int:
    raw = str(os.environ.get("METAFINDER_FALLBACK_SAMPLE_EVERY", "256") or "").strip()
    try:
        val = int(raw)
    except Exception:
        val = 256
    return max(1, val)


def _should_sample_event(count: int) -> bool:
    # Always capture the first few occurrences for diagnostics, then sample.
    c = max(1, int(count))
    if c <= 3:
        return True
    return (c % _sample_every()) == 0


class FallbackViolation(RuntimeError):
    """Raised when fallback strict mode disallows continuing on a fallback path."""


def _is_truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def _is_enabled() -> bool:
    raw = os.environ.get("METAFINDER_FALLBACK_WARN")
    if raw is not None:
        return _is_truthy(raw)
    # Default to quiet console output; keep strict mode enforcement separate.
    return False


def _include_count() -> bool:
    raw = str(os.environ.get("METAFINDER_FALLBACK_WARN_COUNT", "1") or "").strip().lower()
    return raw in _TRUTHY


def _strict_enabled() -> bool:
    raw = os.environ.get("METAFINDER_FALLBACK_STRICT")
    if raw is not None:
        return _is_truthy(raw)
    # Default to GPU_STRICT policy and treat unset as strict.
    return _is_truthy(os.environ.get("GPU_STRICT", "1") or "1")


def _strict_all() -> bool:
    return _is_truthy(os.environ.get("METAFINDER_FALLBACK_STRICT_ALL", "0") or "0")


def _allow_prefixes() -> tuple[str, ...]:
    raw = str(os.environ.get("METAFINDER_FALLBACK_ALLOW", "config.,env.") or "")
    prefixes = [p.strip() for p in raw.split(",") if p and p.strip()]
    return tuple(prefixes)


def _is_allowlisted(site: str) -> bool:
    site_s = str(site or "")
    for prefix in _allow_prefixes():
        if site_s.startswith(prefix):
            return True
    return False


def _default_log_path() -> str:
    return str(os.environ.get("METAFINDER_FALLBACK_LOG_PATH", "") or "").strip()


def _ensure_log_fp():
    global _LOG_FP, _LOG_OPEN_FAILED
    if _LOG_FP is not None:
        return _LOG_FP
    if _LOG_OPEN_FAILED:
        return None
    path = _default_log_path()
    if not path:
        return None
    try:
        p = Path(path)
        if p.parent:
            p.parent.mkdir(parents=True, exist_ok=True)
        _LOG_FP = p.open("a", encoding="utf-8", buffering=1)
        return _LOG_FP
    except Exception:
        _LOG_OPEN_FAILED = True
        return None


def _write_event_jsonl(event: dict[str, Any]) -> None:
    fp = _ensure_log_fp()
    if fp is None:
        return
    try:
        line = json.dumps(event, separators=(",", ":"), sort_keys=False)
    except Exception:
        return
    with _LOG_LOCK:
        try:
            fp.write(line + "\n")
        except Exception:
            return


def _caller_location() -> str:
    try:
        stack = traceback.extract_stack()
        # ... -> warn_fallback -> caller
        if len(stack) >= 3:
            fr = stack[-3]
            return f"{fr.filename}:{fr.lineno}"
    except Exception:
        pass
    return ""


def warn_fallback(
    site: str,
    reason: str,
    *,
    context: dict[str, Any] | None = None,
    exc: BaseException | None = None,
    fatal: bool | None = None,
) -> None:
    """
    Emit diagnostics for a fallback path and enforce strict policy when enabled.

    `fatal` can force behavior for a specific call site:
      - `True`: always raise `FallbackViolation`
      - `False`: never raise from policy for this event
      - `None`: apply strict policy (`METAFINDER_FALLBACK_STRICT*`)
    """
    site_key = str(site or "unknown")
    with _COUNTS_LOCK:
        count = int(_COUNTS_BY_SITE.get(site_key, 0)) + 1
        _COUNTS_BY_SITE[site_key] = count

    include_count = _include_count()
    enabled = _is_enabled()
    strict = _strict_enabled()
    strict_all = _strict_all()
    allowlisted = _is_allowlisted(site_key)
    should_raise = bool(fatal) if fatal is not None else bool(strict and (strict_all or not allowlisted))
    sampled = _should_sample_event(count) or bool(should_raise)

    ctx = dict(context or {})
    loc = _caller_location() if sampled else ""
    ts_wall = float(time.time())
    event = {
        "ts_wall": ts_wall,
        "site": site_key,
        "reason": str(reason or ""),
        "context": ctx,
        "exc_type": type(exc).__name__ if exc is not None else None,
        "exc": str(exc) if exc is not None else None,
        "count": int(count),
        "strict": bool(strict),
        "strict_all": bool(strict_all),
        "allowlisted": bool(allowlisted),
        "would_raise": bool(should_raise),
        "pid": int(os.getpid()),
        "thread": threading.current_thread().name,
        "location": loc,
    }

    if enabled and sampled:
        parts = [f"[FALLBACK][{site_key}] {reason}"]
        if ctx:
            try:
                ctx_s = ", ".join(f"{k}={ctx[k]!r}" for k in sorted(ctx))
            except Exception:
                ctx_s = repr(ctx)
            if ctx_s:
                parts.append(f"context: {ctx_s}")
        if exc is not None:
            parts.append(f"exc={type(exc).__name__}: {exc}")
        if include_count:
            parts.append(f"count={count}")
        if loc:
            parts.append(f"at={loc}")
        parts.append(f"strict={int(strict)} allowlisted={int(allowlisted)} raise={int(should_raise)}")
        msg = " | ".join(parts)
        try:
            print(msg, file=sys.stderr, flush=True)
        except Exception:
            pass

    if sampled:
        _write_event_jsonl(event)

        try:
            from .profile_events import emit_profile_event

            emit_profile_event(
                component="fallback",
                event="fallback::event",
                metrics={
                    "site": site_key,
                    "count": int(count),
                    "strict": int(strict),
                    "allowlisted": int(allowlisted),
                    "raise": int(should_raise),
                },
                ts_wall=ts_wall,
            )
        except Exception:
            pass

    if should_raise:
        detail = f"[FALLBACK-STRICT][{site_key}] {reason}"
        if ctx:
            try:
                detail += " | " + ", ".join(f"{k}={ctx[k]!r}" for k in sorted(ctx))
            except Exception:
                pass
        raise FallbackViolation(detail)


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
