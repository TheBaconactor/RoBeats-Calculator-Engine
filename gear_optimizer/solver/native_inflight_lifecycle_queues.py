"""Queue and tracker helpers for native in-flight song preparation and posting."""
from __future__ import annotations

import queue
import threading
from typing import Any



class PostSender:
    def __init__(self, post_queue, *, stop_requested=None) -> None:
        self._post_queue = post_queue
        self._stop_requested = stop_requested
        backlog = 0
        self._q: queue.Queue[Any] = queue.Queue(maxsize=backlog)
        self._sentinel = object()
        self._thread = threading.Thread(target=self._run, name="PostQueueSender", daemon=True)
        self._thread.start()

    def send(self, item: Any) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(item, block=False)
        except queue.Full:
            self._q.put(item, block=True)

    def close(self, *, timeout: float = 30.0) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(self._sentinel, block=True, timeout=max(0.0, float(timeout)))
        except queue.Full:
            return
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            while True:
                if self._stop_requested is not None and self._stop_requested():
                    return
                try:
                    self._post_queue.put(item, block=True, timeout=0.5)
                    break
                except queue.Full:
                    continue


