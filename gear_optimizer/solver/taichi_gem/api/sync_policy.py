from __future__ import annotations

from collections.abc import Callable


def maybe_sync(
    *,
    sync_fn: Callable[[], None],
    force_sync: bool,
    sync_for_timing: bool,
    for_timing: bool = False,
) -> None:
    if force_sync or (for_timing and sync_for_timing):
        sync_fn()
