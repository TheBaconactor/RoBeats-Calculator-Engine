"""Numba JIT with its disk cache in <engine>/bin/numba_cache/nogil, unless NUMBA_CACHE_DIR is set.

Numba's cache key ignores decorator flags such as nogil, so a build cached before the kernels released the GIL would
keep holding it: builds with other flags live elsewhere. The kernels release the GIL (nopython code touches no Python
objects), so a long kernel on one thread does not stall the process's other threads.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., object])

_CACHE_DIR = os.environ.get("NUMBA_CACHE_DIR", "").strip()
if not _CACHE_DIR:
    _default = Path(__file__).resolve().parents[2] / "bin" / "numba_cache" / "nogil"
    _default.mkdir(parents=True, exist_ok=True)
    _CACHE_DIR = os.environ["NUMBA_CACHE_DIR"] = str(_default)

import numba  # noqa: E402  (reads NUMBA_CACHE_DIR when first imported)

numba.config.CACHE_DIR = _CACHE_DIR  # numba may have been imported before this module


def jit(nopython: bool = True, cache: bool = True, nogil: bool = True) -> Callable[[_F], _F]:
    return numba.jit(nopython=nopython, cache=cache, nogil=nogil)


__all__ = ["jit"]
