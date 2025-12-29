"""
GPU Prefetch Manager - Main-thread prefetch of song timelines.

Since Taichi requires GPU operations from the same thread that called ti.init(),
this module provides a simple slot-based prefetch manager that:
1. Uses a ring buffer of song slots (1-N, slot 0 reserved)
2. Prefetches timeline grids for upcoming songs on the main thread
3. Returns the prefetched slot when processing starts

The key insight is that Taichi kernel launches are async - so we can queue up
multiple timeline computations and they'll execute in parallel with other Python work.

Usage in main loop:
    prefetch_mgr = GPUPrefetchManager(num_slots=5)

    for i, song in enumerate(songs):
        # Prefetch next songs (main thread, but async on GPU)
        for j in range(i + 1, min(i + 5, len(songs))):
            if not prefetch_mgr.is_prefetched(songs[j].song_name):
                slot = prefetch_mgr.prefetch(songs[j])

        # Get slot for current song (prefetched or compute now)
        slot = prefetch_mgr.get_or_compute(song)

        # Process with this slot
        run_ga(song, song_slot=slot)

        # Release slot after done
        prefetch_mgr.release(slot)
"""

from __future__ import annotations

import time
from typing import Optional
from collections import deque
from dataclasses import dataclass

# Use 5 slots by default (slots 1-5, leaving slot 0 as fallback)
DEFAULT_NUM_SLOTS = 5


@dataclass
class PrefetchedSlot:
    """Tracking info for a prefetched song slot."""

    slot_id: int
    song_key: str  # Unique song identifier (name + difficulty)
    prefetch_time_ms: float


class GPUPrefetchManager:
    """
    Manages GPU slot ring buffer for timeline prefetching.

    This runs on the main thread and uses Taichi's async kernel execution
    to overlap timeline computation with other Python work.
    """

    def __init__(self, num_slots: int = DEFAULT_NUM_SLOTS, *, keep_slots: bool = False):
        """
        Initialize prefetch manager.

        Args:
            num_slots: Number of GPU slots to use (1-based, 0 is fallback)
            keep_slots: If True, `release()` becomes a no-op and slots stay pinned.
        """
        self.num_slots = num_slots
        self._keep_slots = bool(keep_slots)

        # Ring buffer of slot IDs (1 to num_slots)
        self._free_slots: deque[int] = deque(range(1, num_slots + 1))

        # Map song_key -> PrefetchedSlot for cached slots
        self._prefetched: dict[str, PrefetchedSlot] = {}

        # Track slot -> song_key for release
        self._slot_to_key: dict[int, str] = {}

        # Stats
        self._prefetch_count = 0
        self._cache_hits = 0
        self._total_prefetch_ms = 0.0

    def _make_song_key(self, calc_song: dict) -> str:
        """Create a stable key for a song timeline variant.

        Includes lightweight timestamp signature + HumanHitSim parameters so we
        never reuse a prefetched timeline across different simulated timestamp
        streams (ApplyTo=ALL) or different sim configs.
        """
        meta = calc_song.get("metadata", {})
        song_name = str(meta.get("Song Name", ""))
        difficulty = str(meta.get("Difficulty", ""))
        song_data = calc_song.get("song_data", {})
        timestamps = song_data.get("timestamps", ())
        note_count = len(timestamps) if hasattr(timestamps, "__len__") else 0

        first_ms = 0
        last_ms = 0
        try:
            if note_count:
                first_ms = int(float(timestamps[0]) * 1000.0)
                last_ms = int(float(timestamps[note_count - 1]) * 1000.0)
        except Exception:
            first_ms = 0
            last_ms = 0

        try:
            human_seed = int(meta.get("HumanHitSimSeed") or 0)
        except Exception:
            human_seed = 0
        human_apply_to = str(meta.get("HumanHitSimApplyTo", "")).strip().upper()
        human_dist = str(meta.get("HumanHitSimDistribution", "")).strip().lower()
        human_great_mode = str(meta.get("HumanHitSimGreatMode", "")).strip().lower()

        return (
            f"{song_name}|{difficulty}|{note_count}|{first_ms}|{last_ms}|"
            f"{human_seed}|{human_apply_to}|{human_dist}|{human_great_mode}"
        )

    def is_prefetched(self, calc_song: dict) -> bool:
        """Check if a song is already prefetched."""
        key = self._make_song_key(calc_song)
        return key in self._prefetched

    def prefetch(self, calc_song: dict, ref_arrays: dict) -> Optional[int]:
        """
        Prefetch timeline grid for a song.

        This uploads timestamps and launches the timeline kernel.
        The kernel runs async on GPU while Python continues.

        Args:
            calc_song: Song calculation data
            ref_arrays: Reference lookup arrays

        Returns:
            Slot ID if prefetched, None if no slots available
        """
        key = self._make_song_key(calc_song)

        # Already prefetched?
        if key in self._prefetched:
            return self._prefetched[key].slot_id

        # Get a free slot
        if not self._free_slots:
            return None  # No slots available, caller should use slot 0

        slot_id = self._free_slots.popleft()

        # Prefetch timeline to this slot
        t0 = time.perf_counter()
        try:
            from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu

            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=slot_id)
        except Exception as e:
            # On error, return slot to pool and use fallback
            self._free_slots.appendleft(slot_id)
            print(f"[GPU Prefetch] Error prefetching slot {slot_id}: {e}")
            return None

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Track the prefetch
        self._prefetched[key] = PrefetchedSlot(
            slot_id=slot_id,
            song_key=key,
            prefetch_time_ms=elapsed_ms,
        )
        self._slot_to_key[slot_id] = key
        self._prefetch_count += 1
        self._total_prefetch_ms += elapsed_ms

        return slot_id

    def get_slot(self, calc_song: dict, ref_arrays: dict) -> int:
        """
        Get the GPU slot for a song, prefetching if needed.

        Args:
            calc_song: Song calculation data
            ref_arrays: Reference lookup arrays

        Returns:
            Slot ID (1-N) if prefetched, 0 if fallback needed
        """
        key = self._make_song_key(calc_song)

        # Check if already prefetched
        if key in self._prefetched:
            self._cache_hits += 1
            return self._prefetched[key].slot_id

        # Try to prefetch now
        slot = self.prefetch(calc_song, ref_arrays)
        if slot is not None:
            return slot

        # Fallback to slot 0 (on-demand computation)
        return 0

    def release(self, slot_id: int) -> None:
        """
        Release a slot for reuse.

        Args:
            slot_id: Slot to release (0 is ignored)
        """
        if self._keep_slots:
            return
        if slot_id == 0:
            return  # Slot 0 is always available

        if slot_id in self._slot_to_key:
            key = self._slot_to_key.pop(slot_id)
            if key in self._prefetched:
                del self._prefetched[key]

        # Return slot to pool
        if slot_id not in self._free_slots:
            self._free_slots.append(slot_id)

    def stats(self) -> dict:
        """Get prefetch statistics."""
        return {
            "prefetch_count": self._prefetch_count,
            "cache_hits": self._cache_hits,
            "avg_prefetch_ms": self._total_prefetch_ms / max(1, self._prefetch_count),
            "active_slots": len(self._prefetched),
            "free_slots": len(self._free_slots),
        }

    def reset(self) -> None:
        """Reset all slots and caches."""
        self._free_slots = deque(range(1, self.num_slots + 1))
        self._prefetched.clear()
        self._slot_to_key.clear()


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_prefetch_manager: Optional[GPUPrefetchManager] = None


def get_gpu_prefetch_manager(num_slots: int = DEFAULT_NUM_SLOTS, *, keep_slots: bool = False) -> GPUPrefetchManager:
    """Get the global GPU prefetch manager instance."""
    global _prefetch_manager

    # Clamp to allocated grid slots (slot 0 reserved for fallback).
    try:
        from ..fields import MAX_SONG_SLOTS

        max_slots = max(1, int(MAX_SONG_SLOTS) - 1)
        num_slots = max(1, min(int(num_slots), max_slots))
    except Exception:
        num_slots = max(1, int(num_slots))

    if _prefetch_manager is None:
        _prefetch_manager = GPUPrefetchManager(num_slots=num_slots, keep_slots=keep_slots)
        return _prefetch_manager

    # If settings changed, rebuild (avoids subtle mismatch where callers think slots exist).
    if int(getattr(_prefetch_manager, "num_slots", 0)) != int(num_slots) or bool(
        getattr(_prefetch_manager, "_keep_slots", False)
    ) != bool(keep_slots):
        _prefetch_manager = GPUPrefetchManager(num_slots=num_slots, keep_slots=keep_slots)

    return _prefetch_manager


def reset_gpu_prefetch_manager() -> None:
    """Reset the global GPU prefetch manager."""
    global _prefetch_manager

    if _prefetch_manager is not None:
        _prefetch_manager.reset()
        _prefetch_manager = None
