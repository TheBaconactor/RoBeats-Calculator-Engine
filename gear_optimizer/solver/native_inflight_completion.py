from __future__ import annotations

import concurrent.futures
import threading
import time
from dataclasses import dataclass, field

from gear_optimizer.solver.inflight_wait import wait_for_completion_event


@dataclass
class CompletionTracker:
    event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    ids: set[int] = field(default_factory=set)

    def register(self, fut: concurrent.futures.Future | None) -> bool:
        if fut is None:
            return False
        fut_id = int(id(fut))

        with self.lock:
            if fut_id in self.ids:
                return False
            self.ids.add(fut_id)

        def _on_done(_fut: concurrent.futures.Future, *, _fut_id: int = fut_id) -> None:
            self.unregister(_fut_id)
            self.event.set()

        try:
            fut.add_done_callback(_on_done)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self.unregister(fut_id)
            self.event.set()
            return False
        return True

    def unregister(self, fut_id: int) -> None:
        with self.lock:
            self.ids.discard(int(fut_id))

    def is_set(self) -> bool:
        return bool(self.event.is_set())

    def wait(self, timeout_s: float, *, short_spin_s: float = 0.0) -> bool:
        return bool(
            wait_for_completion_event(
                self.event,
                timeout_s=float(timeout_s),
                short_spin_s=float(short_spin_s),
                perf_counter=time.perf_counter,
                sleep=time.sleep,
            )
        )

    def clear(self) -> None:
        self.event.clear()
