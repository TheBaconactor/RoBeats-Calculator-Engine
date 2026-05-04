"""
JIT (Just-In-Time) compilation setup for performance-critical functions.
Falls back gracefully if Numba is not available.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, TypeVar

from .parsing import truthy

_F = TypeVar("_F", bound=Callable[..., object])


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return truthy(val, extra_truthy=("y",))


def _default_numba_cache_dir() -> str | None:
    """
    Return a stable cache dir for Numba, scoped to this repo.

    Using `bin/numba_cache/` keeps artifacts out of user profile dirs and
    makes cleanup straightforward.
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]
        cache_dir = repo_root / "bin" / "numba_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir)
    except Exception:
        return None


def _fallback_jit(nopython: bool = True, cache: bool = True) -> Callable[[_F], _F]:
    """
    Fallback decorator when Numba is not available.
    Returns the function unchanged (no optimization).
    """

    def decorator(func: _F) -> _F:
        return func

    return decorator


HAS_NUMBA = False
jit = _fallback_jit

# Numba reads some config from env at import time; set our cache dir early so
# disk caching (when enabled) doesn't leak into user profile dirs.
_NUMBA_DISK_CACHE_ENABLED = _env_bool("NUMBA_DISK_CACHE", True)
if _NUMBA_DISK_CACHE_ENABLED and "NUMBA_CACHE_DIR" not in os.environ:
    _cache_dir = _default_numba_cache_dir()
    if _cache_dir:
        os.environ["NUMBA_CACHE_DIR"] = _cache_dir

try:
    from numba import jit as _numba_jit
except ImportError:
    pass
else:
    HAS_NUMBA = True
    try:
        import numba as _numba

        _effective_cache_dir = str(os.environ.get("NUMBA_CACHE_DIR", "") or "").strip()
        if _NUMBA_DISK_CACHE_ENABLED and _effective_cache_dir:
            _numba.config.CACHE_DIR = _effective_cache_dir
    except Exception:
        pass

    def _numba_jit_wrapper(nopython: bool = True, cache: bool = True) -> Callable[[_F], _F]:
        """
        Create a JIT decorator.

        Disk caching is enabled by default (respects the `cache=` argument) and
        is redirected to `bin/numba_cache/` unless `NUMBA_CACHE_DIR` is already
        set. Disable globally via `NUMBA_DISK_CACHE=0`.
        """
        disk_cache_enabled = _env_bool("NUMBA_DISK_CACHE", True)
        use_cache = bool(cache) and disk_cache_enabled
        if use_cache:
            cache_dir = str(os.environ.get("NUMBA_CACHE_DIR", "") or "").strip()
            if not cache_dir:
                cache_dir = _default_numba_cache_dir() or ""
                if cache_dir:
                    os.environ["NUMBA_CACHE_DIR"] = cache_dir
            if not cache_dir:
                use_cache = False
            else:
                try:
                    import numba as _numba

                    _numba.config.CACHE_DIR = str(cache_dir)
                except Exception:
                    pass
        return _numba_jit(nopython=nopython, cache=use_cache)

    jit = _numba_jit_wrapper


__all__ = ["jit", "HAS_NUMBA"]
