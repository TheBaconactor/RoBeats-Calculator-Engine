from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

_CACHE_ROOT: ContextVar[Path | None] = ContextVar("frontier_cache_root", default=None)
_EPHEMERAL: ContextVar[bool] = ContextVar("frontier_cache_ephemeral", default=False)


def scoped_frontier_cache_dir(name: str) -> Path | None:
    root = _CACHE_ROOT.get()
    return root / name if root is not None else None


def frontier_cache_is_ephemeral() -> bool:
    return bool(_EPHEMERAL.get())


@contextmanager
def temporary_frontier_cache_scope(root: str | Path) -> Iterator[None]:
    """Route one custom solve/replay to a caller-owned temporary cache without global env races.

    Context variables isolate concurrent threads and async tasks. Ephemeral callers also bypass
    process-global memory caches, so an uploaded chart cannot survive after this scope is deleted.
    """
    cache_root = Path(root)
    cache_root.mkdir(parents=True, exist_ok=True)
    root_token = _CACHE_ROOT.set(cache_root)
    ephemeral_token = _EPHEMERAL.set(True)
    try:
        yield
    finally:
        _EPHEMERAL.reset(ephemeral_token)
        _CACHE_ROOT.reset(root_token)
