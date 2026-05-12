from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
import logging
from typing import Any

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegisteredWorker:
    worker_id: int
    request_queue: Any
    response_queue: Any
    next_worker_id: int

    def as_tuple(self) -> tuple[int, Any, Any]:
        return self.worker_id, self.request_queue, self.response_queue


@dataclass
class WorkerModeState:
    enabled: bool = False
    worker_id: int | None = None
    request_queue: Any | None = None
    response_queue: Any | None = None
    request_counter: int = 0

    def configure(self, worker_id: int, request_queue: Any, response_queue: Any) -> None:
        self.enabled = True
        self.worker_id = int(worker_id)
        self.request_queue = request_queue
        self.response_queue = response_queue

    def clear(self) -> None:
        self.enabled = False
        self.worker_id = None
        self.request_queue = None
        self.response_queue = None

    def next_request_id(self) -> int:
        self.request_counter += 1
        return int(self.request_counter)

    def require_request_queue(self) -> Any:
        if not self.enabled or self.request_queue is None:
            raise RuntimeError("GPU worker mode request queue is not configured")
        return self.request_queue


worker_mode_state = WorkerModeState()


def register_executor_worker(
    *,
    next_worker_id: int,
    request_queue: Any,
    response_queues: MutableMapping[int, Any],
    response_queue_factory: Callable[[], Any],
) -> RegisteredWorker:
    worker_id = int(next_worker_id)
    response_queue = response_queue_factory()
    response_queues[worker_id] = response_queue
    return RegisteredWorker(
        worker_id=worker_id,
        request_queue=request_queue,
        response_queue=response_queue,
        next_worker_id=worker_id + 1,
    )


def unregister_executor_worker(
    *,
    worker_id: int,
    response_queues: MutableMapping[int, Any],
) -> bool:
    return response_queues.pop(int(worker_id), None) is not None


def default_song_slot_for_worker(worker_id: int) -> int:
    """Map a worker id to a stable non-zero song slot for timeline reuse."""
    try:
        from .taichi_gem import fields as gem_fields

        max_slots = int(getattr(gem_fields, "MAX_SONG_SLOTS", 1) or 1)
    except Exception as e:
        logger.debug(f"gpu_executor_worker_state:default_song_slot_for_worker: {e}")
        try:
            max_slots = int(env_get("GPU_SONG_SLOTS", "24") or "24")
        except (ValueError, TypeError):
            max_slots = 24
    max_slots = max(1, int(max_slots))
    if max_slots <= 1:
        return 0
    return 1 + (abs(int(worker_id)) % max(1, int(max_slots) - 1))
