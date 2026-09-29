"""JIT (Just-In-Time) compilation setup for performance-critical functions."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Callable, TypeVar
_F = TypeVar("_F", bound=Callable[..., object])
def _default_numba_cache_dir() -> str | None:
    """
    Return a stable cache dir for Numba, scoped to this repo.
    Using `bin/numba_cache/` keeps artifacts out of user profile dirs and
    makes cleanup straightforward.
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]
        # Numba's cache key ignores decorator flags such as nogil, so a build cached before
        # kernels released the GIL would keep holding it. Builds with other flags live elsewhere.
        cache_dir = repo_root / "bin" / "numba_cache" / "nogil"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir)
    except OSError:
        return None
_NUMBA_DISK_CACHE_ENABLED = True
if _NUMBA_DISK_CACHE_ENABLED and "NUMBA_CACHE_DIR" not in os.environ:
    _cache_dir = _default_numba_cache_dir()
    if _cache_dir:
        os.environ["NUMBA_CACHE_DIR"] = _cache_dir
from numba import jit as _numba_jit
import numba as _numba
_effective_cache_dir = os.environ.get("NUMBA_CACHE_DIR", "").strip()
if _NUMBA_DISK_CACHE_ENABLED and _effective_cache_dir:
    try:
        _numba.config.CACHE_DIR = _effective_cache_dir
    except (AttributeError, OSError, ValueError):
        pass
def jit(nopython: bool = True, cache: bool = True, nogil: bool = True) -> Callable[[_F], _F]:
    """
    Create a JIT decorator.
    Disk caching is enabled by default (respects the `cache=` argument) and is
    redirected to `bin/numba_cache/` unless `NUMBA_CACHE_DIR` is already set.
    Always on (the NUMBA_DISK_CACHE override was removed; the disk cache only
    skips recompilation, so JIT output is bit-identical).

    Kernels release the GIL (nopython code touches no Python objects), so a long kernel on one
    thread no longer stalls every other thread of the process, and independent calls can run on
    several cores at once.
    """
    disk_cache_enabled = True
    use_cache = bool(cache) and disk_cache_enabled
    if use_cache:
        cache_dir = os.environ.get("NUMBA_CACHE_DIR", "").strip()
        if not cache_dir:
            cache_dir = _default_numba_cache_dir() or ""
            if cache_dir:
                os.environ["NUMBA_CACHE_DIR"] = cache_dir
        if not cache_dir:
            use_cache = False
        else:
            try:
                _numba.config.CACHE_DIR = str(cache_dir)
            except (AttributeError, OSError, ValueError):
                pass
    return _numba_jit(nopython=nopython, cache=use_cache, nogil=nogil)
__all__ = ["jit"]
