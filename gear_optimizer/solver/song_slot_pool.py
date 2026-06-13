from __future__ import annotations

from collections import deque


class NoFreeSongSlotError(RuntimeError):
    """Raised when all nonzero GPU song slots are reserved."""


class SongSlotPool:
    def __init__(self, max_song_slots: int):
        # Slot 0 is reserved; allocate 1..N-1.
        n = max(2, int(max_song_slots))
        self._free = deque(range(1, n))

    def acquire(self) -> int:
        if not self._free:
            raise NoFreeSongSlotError("No free GPU song slots")
        return int(self._free.popleft())

    def release(self, slot_id: int) -> None:
        slot_id = int(slot_id)
        if slot_id <= 0:
            return
        if slot_id not in self._free:
            self._free.append(slot_id)
