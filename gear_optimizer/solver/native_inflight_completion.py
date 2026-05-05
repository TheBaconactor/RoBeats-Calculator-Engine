from __future__ import annotations

import concurrent.futures
import threading
from dataclasses import dataclass, field


@dataclass
class CompletionTracker:
    event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    ids: set[int] = field(default_factory=set)
    registered_attr: str = "_metafinder_completion_registered"

    def register(self, fut: concurrent.futures.Future) -> bool:
        try:
            if bool(getattr(fut, self.registered_attr, False)):
                return False
            setattr(fut, self.registered_attr, True)
        except Exception:
            pass

        try:
            fut_id = int(id(fut))
        except Exception:
            try:
                setattr(fut, self.registered_attr, False)
            except Exception:
                pass
            return False

        try:
            with self.lock:
                if fut_id in self.ids:
                    return False
                self.ids.add(fut_id)
        except Exception:
            try:
                setattr(fut, self.registered_attr, False)
            except Exception:
                pass
            return False

        def _on_done(_fut: concurrent.futures.Future, *, _fut_id: int = fut_id) -> None:
            try:
                self.event.set()
            except Exception:
                pass
            try:
                with self.lock:
                    self.ids.discard(_fut_id)
            except Exception:
                pass

        try:
            fut.add_done_callback(_on_done)
        except Exception:
            try:
                setattr(fut, self.registered_attr, False)
            except Exception:
                pass
            try:
                self.event.set()
            except Exception:
                pass
        return True

    def clear(self) -> None:
        try:
            self.event.clear()
        except Exception:
            pass
