from __future__ import annotations

from dataclasses import dataclass


def effective_owner_batch_max(
    base_batch_max: int,
    *,
    in_process_queues: bool,
    batch_max_overridden: bool,
) -> int:
    batch_max_i = max(1, int(base_batch_max))
    if in_process_queues and not batch_max_overridden:
        # Keep owner turns broad enough to drain local producer bursts without
        # widening the turn so far that same-song downstream readiness gets
        # buried behind unrelated in-process work.
        batch_max_i = max(batch_max_i, 24)
    return int(batch_max_i)


@dataclass(frozen=True)
class BatchPlan:
    """Batch gather decision metadata for one executor loop."""

    wait_ms: int
    max_batch: int
    mode: str
    queue_depth_hint: int
    pressure_hint: float
