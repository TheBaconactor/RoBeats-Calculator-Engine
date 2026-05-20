"""JIT (Just-In-Time) compilation setup for performance-critical functions."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Callable, TypeVar
from .env_config import ENV
from .parsing import env_flag
_F = TypeVar("_F", bound=Callable[..., object])
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
    except OSError:
        return None
_NUMBA_DISK_CACHE_ENABLED = env_flag("NUMBA_DISK_CACHE", "1")
if _NUMBA_DISK_CACHE_ENABLED and "NUMBA_CACHE_DIR" not in os.environ:
    _cache_dir = _default_numba_cache_dir()
    if _cache_dir:
        os.environ["NUMBA_CACHE_DIR"] = _cache_dir
from numba import jit as _numba_jit
import numba as _numba
HAS_NUMBA = True
_effective_cache_dir = str(ENV.numba_cache_dir or "").strip()
if not _effective_cache_dir:
    try:
        _effective_cache_dir = str(os.environ["NUMBA_CACHE_DIR"]).strip()
    except KeyError:
        _effective_cache_dir = ""
if _NUMBA_DISK_CACHE_ENABLED and _effective_cache_dir:
    try:
        _numba.config.CACHE_DIR = _effective_cache_dir
    except (AttributeError, OSError, ValueError):
        pass
def jit(nopython: bool = True, cache: bool = True) -> Callable[[_F], _F]:
    """
    Create a JIT decorator.
    Disk caching is enabled by default (respects the `cache=` argument) and is
    redirected to `bin/numba_cache/` unless `NUMBA_CACHE_DIR` is already set.
    Disable globally via `NUMBA_DISK_CACHE=0`.
    """
    disk_cache_enabled = env_flag("NUMBA_DISK_CACHE", "1")
    use_cache = bool(cache) and disk_cache_enabled
    if use_cache:
        cache_dir = str(ENV.numba_cache_dir or "").strip()
        if not cache_dir:
            try:
                cache_dir = str(os.environ["NUMBA_CACHE_DIR"]).strip()
            except KeyError:
                cache_dir = ""
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
    return _numba_jit(nopython=nopython, cache=use_cache)
__all__ = ["jit", "HAS_NUMBA"]
