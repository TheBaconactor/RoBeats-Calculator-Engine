"""
Item Registry - GPU-optimized item encoding for GPU-native GA.

This module provides the ItemRegistry class which:
1. Assigns contiguous integer IDs to items per slot
2. Encodes/decodes genomes between item-based and ID-based representations
3. Provides GPU-friendly arrays for item stats and slot pools
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.gamedata import Gear, SongMini

# Stat dimension indices (matching fields.ITEM_STAT_DIM = 10)
STAT_INDICES = {
    "Perfect Points": 0,
    "Combo Multiplier": 1,
    "Fever Multiplier": 2,
    "Fever Time": 3,
    "Fever Fill Rate": 4,
    "Beat": 5,
    "Vibe": 6,
    "Rush": 7,
    "Flow": 8,
    "Chill": 9,
}

MINI_SLOT_INDICES = [6, 7, 8]  # Minis occupy slots 6, 7, 8


def _by_name(item: Gear | SongMini) -> str:
    # GPU-native GA is deterministic in ID-space (it samples integer IDs from per-slot pools), so the
    # (slot, item) -> id mapping must not depend on pool construction order. Names are unique.
    return item.name


class ItemRegistry:
    """
    GPU-optimized item encoding for a specific song/pool combination.

    Assigns contiguous integer IDs to items per slot:
      - ID 0 is reserved (empty/invalid)
      - Gear slots 0-5: each has its own ID range
      - Mini slots 6-8: share the same pool (minis are interchangeable)

    This allows GPU mutation to sample from slot pools using simple
    modular arithmetic: new_id = slot_start[slot] + (rand % slot_count[slot])
    """

    def __init__(self, gear_pool: dict[str, list[Gear]], mini_pool: list[SongMini], slots: list[str]):
        """
        Build item registry from gear and mini pools.

        Args:
            gear_pool: Dict mapping slot name -> list of gear
            mini_pool: The song's minis (shared across slots 6-8)
            slots: The six gear slot names, in genome order
        """
        self.slots = list(slots)
        self.n_slots = len(slots) + 3  # 6 gear + 3 mini = 9 total

        self.id_to_item: dict[int, Gear | SongMini] = {}
        self.item_to_id: dict[tuple[int, str], int] = {}  # (slot_idx, name) -> id

        # Per-slot pool boundaries
        self.slot_start = [0] * 9  # First valid ID for each slot
        self.slot_count = [0] * 9  # Number of items in each slot

        next_id = 1
        for slot_idx, slot_name in enumerate(slots):
            items = sorted(gear_pool.get(slot_name, []), key=_by_name)
            self.slot_start[slot_idx] = next_id
            self.slot_count[slot_idx] = len(items)
            for item in items:
                self.id_to_item[next_id] = item
                self.item_to_id[(slot_idx, item.name)] = next_id
                next_id += 1

        mini_items = sorted(mini_pool, key=_by_name)
        mini_start = next_id
        for item in mini_items:
            self.id_to_item[next_id] = item
            for mini_slot in MINI_SLOT_INDICES:
                self.item_to_id[(mini_slot, item.name)] = next_id
            next_id += 1
        for mini_slot in MINI_SLOT_INDICES:
            self.slot_start[mini_slot] = mini_start
            self.slot_count[mini_slot] = len(mini_items)

        self.n_items = next_id  # Total items including reserved ID 0
        self._gpu_arrays_cache: dict[str, np.ndarray] | None = None

    def _item(self, item_id) -> Gear | SongMini | None:
        idx = int(item_id)
        if idx == 0:
            return None
        item = self.id_to_item.get(idx)
        if item is None:
            raise ValueError(f"genome references unknown item id {idx} (registry has {self.n_items} ids)")
        return item

    def decode_genome(self, ids: np.ndarray) -> list[Gear | SongMini | None]:
        """The 9 items of a genome (None for the reserved empty id 0)."""
        return [self._item(item_id) for item_id in ids[:9]]

    def decode_names(self, ids: np.ndarray) -> list[str]:
        """The 9 item names of a genome ("None" for the reserved empty id 0)."""
        return [item.name if item is not None else "None" for item in self.decode_genome(ids)]

    def to_gpu_arrays(self) -> dict[str, np.ndarray]:
        """
        Return numpy arrays for GPU upload.

        Returns:
            dict with keys:
                - "item_stats": (n_items, 10) int32 - stats per item
                - "slot_start": (9,) int32 - first ID per slot
                - "slot_count": (9,) int32 - count per slot
        """
        cached = self._gpu_arrays_cache
        if cached is not None:
            return cached

        item_stats = np.zeros((self.n_items, 10), dtype=np.int32)
        for item_id, item in self.id_to_item.items():
            for stat, stat_idx in STAT_INDICES.items():
                item_stats[item_id, stat_idx] = item.stats[stat]

        out = {
            "item_stats": item_stats,
            "slot_start": np.array(self.slot_start, dtype=np.int32),
            "slot_count": np.array(self.slot_count, dtype=np.int32),
        }
        self._gpu_arrays_cache = out
        return out
