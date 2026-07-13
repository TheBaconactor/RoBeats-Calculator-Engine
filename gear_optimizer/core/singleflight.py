"""Exact-key single-flight coordination for cold cache builders."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from threading import Lock
from typing import Generic, TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")


class SingleFlight(Generic[_K, _V]):
    """Run at most one builder per key while concurrent callers share its outcome."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._inflight: dict[_K, Future[_V]] = {}

    def run(self, key: _K, builder: Callable[[], _V]) -> _V:
        with self._lock:
            future = self._inflight.get(key)
            owner = future is None
            if owner:
                future = Future()
                self._inflight[key] = future

        if not owner:
            return future.result()

        try:
            value = builder()
        except BaseException as exc:
            future.set_exception(exc)
            raise
        else:
            future.set_result(value)
            return value
        finally:
            with self._lock:
                removed = self._inflight.pop(key, None)
                if removed is not future:
                    raise RuntimeError("single-flight ownership changed while a builder was active")
