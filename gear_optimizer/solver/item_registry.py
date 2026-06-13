"""
Item Registry - GPU-optimized item encoding for GPU-native GA.

This module provides the ItemRegistry class which:
1. Assigns contiguous integer IDs to items per slot
2. Encodes/decodes genomes between dict-based and ID-based representations
3. Provides GPU-friendly arrays for item stats and slot pools
"""

import numpy as np
from typing import Optional
import json
import logging



logger = logging.getLogger(__name__)
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

# Cache gear-side registry state (song-invariant). Mini pools are still rebuilt per song.
_GEAR_REGISTRY_CACHE: dict[
    tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, int], ...], tuple[str, ...]],
    tuple[dict[int, dict], dict[tuple[int, str], int], list[dict[str, int]], list[int], list[int], int],
] = {}


def _fixed_gear_key(slots: list[str], fixed_gear: Optional[list[dict]]) -> tuple[str, ...]:
    if not fixed_gear:
        return ()
    out: list[str] = []
    for i, _slot_name in enumerate(slots):
        item = fixed_gear[i] if i < len(fixed_gear) else None
        if isinstance(item, dict):
            out.append(str(item.get("Name", "") or ""))
        elif item:
            out.append(str(item))
        else:
            out.append("")
    return tuple(out)


def _gear_pool_signature(gear_pool: dict[str, list[dict]], slots: list[str]) -> tuple[tuple[str, int], ...]:
    return tuple((str(slot_name), int(len(gear_pool.get(slot_name, []) or []))) for slot_name in slots)


def _stable_item_sort_key(item: object) -> tuple:
    """
    Deterministic ordering for gear/mini pools.

    GPU-native GA is deterministic in *ID-space* (it mutates/samples integer IDs from per-slot pools).
    That determinism only holds end-to-end if the (slot, item) -> item_id mapping is stable across
    processes. Upstream pool construction may iterate dicts/sets; if so, item order can vary with
    PYTHONHASHSEED and make GA results look "lucky" even when GA_SEED is fixed.

    Canonicalizing the pool order fixes that: same pool contents => same IDs => same GA trajectory.
    """

    if not isinstance(item, dict):
        return (1, str(item))

    name = str(item.get("Name", "") or "")
    # Tie-breaker: stable, content-based signature (handles any rare duplicate names safely).
    try:
        sig = json.dumps(item, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    except Exception as e:
        logger.debug(f"item_registry:_stable_item_sort_key: {e}")
        try:
            sig = str(sorted((str(k), str(v)) for k, v in item.items()))
        except Exception as e:
            logger.debug(f"item_registry:_stable_item_sort_key: {e}")
            sig = repr(item)
    return (0, name, sig)


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

    def __init__(
        self,
        gear_pool: dict[str, list[dict]],
        mini_pool: list[dict],
        slots: list[str],
        fixed_gear: Optional[list[dict]] = None,
        fixed_minis: Optional[list[dict]] = None,
    ):
        """
        Build item registry from gear and mini pools.

        Args:
            gear_pool: Dict mapping slot name -> list of gear items
            mini_pool: List of mini items (shared across slots 6-8)
            slots: List of gear slot names (e.g., ["Arms", "BackBling", ...])
            fixed_gear: If provided, only these gear items are valid (for fixed slots)
            fixed_minis: If provided, only these minis are valid (for fixed slots)
        """
        self.slots = list(slots)
        self.n_slots = len(slots) + 3  # 6 gear + 3 mini = 9 total

        # Mappings
        self.id_to_item: dict[int, dict] = {0: {}}  # ID 0 = empty
        self.item_to_id: dict[tuple[int, str], int] = {}  # (slot_idx, name) -> id
        # Fast slot-local lookup tables for hot encoding paths.
        self._slot_name_to_id: list[dict[str, int]] = [{} for _ in range(9)]

        # Per-slot pool boundaries
        self.slot_start = [0] * 9  # First valid ID for each slot
        self.slot_count = [0] * 9  # Number of items in each slot

        # Build/reuse gear-side registry state.
        slots_key = tuple(str(s) for s in slots)
        cache_key = (
            slots_key,
            _fixed_gear_key(slots, fixed_gear),
            _gear_pool_signature(gear_pool, slots),
            (str(id(gear_pool)),),
        )
        cached = _GEAR_REGISTRY_CACHE.get(cache_key)

        if cached is None:
            id_to_item_base: dict[int, dict] = {0: {}}
            item_to_id_base: dict[tuple[int, str], int] = {}
            slot_name_to_id_base: list[dict[str, int]] = [{} for _ in range(9)]
            slot_start_base = [0] * 9
            slot_count_base = [0] * 9
            next_id_base = 1

            for slot_idx, slot_name in enumerate(slots):
                items = gear_pool.get(slot_name, [])
                if fixed_gear is not None and slot_idx < len(fixed_gear):
                    fixed_item = fixed_gear[slot_idx]
                    if fixed_item and fixed_item.get("Name"):
                        items = [fixed_item]

                # IMPORTANT: keep pool ordering stable across runs (see _stable_item_sort_key docstring).
                items = sorted(list(items or []), key=_stable_item_sort_key)

                slot_start_base[slot_idx] = next_id_base
                slot_count_base[slot_idx] = len(items)

                for item in items:
                    name = item.get("Name", "")
                    if not name:
                        continue
                    item_id = next_id_base
                    next_id_base += 1
                    id_to_item_base[item_id] = item
                    item_to_id_base[(slot_idx, name)] = item_id
                    slot_name_to_id_base[slot_idx][str(name)] = item_id

            cached = (
                id_to_item_base,
                item_to_id_base,
                slot_name_to_id_base,
                slot_start_base,
                slot_count_base,
                next_id_base,
            )
            _GEAR_REGISTRY_CACHE[cache_key] = cached
            if len(_GEAR_REGISTRY_CACHE) > 24:
                _GEAR_REGISTRY_CACHE.clear()
                _GEAR_REGISTRY_CACHE[cache_key] = cached

        (
            id_to_item_base,
            item_to_id_base,
            slot_name_to_id_base,
            slot_start_base,
            slot_count_base,
            next_id,
        ) = cached
        self.id_to_item = dict(id_to_item_base)
        self.item_to_id = dict(item_to_id_base)
        self._slot_name_to_id = [dict(m) for m in slot_name_to_id_base]
        self.slot_start = list(slot_start_base)
        self.slot_count = list(slot_count_base)

        # Process mini slots (6-8) - they share the same pool
        mini_items = mini_pool
        if fixed_minis is not None:
            # Only use fixed minis
            mini_items = [m for m in fixed_minis if m and m.get("Name")]

        # Same determinism requirement as gear pools: keep ordering stable across processes.
        mini_items = sorted(list(mini_items or []), key=_stable_item_sort_key)

        mini_start = next_id
        mini_count = len(mini_items)

        for item in mini_items:
            name = item.get("Name", "")
            if not name:
                continue

            item_id = next_id
            next_id += 1

            self.id_to_item[item_id] = item
            # Register for all mini slots (6, 7, 8)
            for mini_slot in MINI_SLOT_INDICES:
                self.item_to_id[(mini_slot, name)] = item_id
                self._slot_name_to_id[mini_slot][str(name)] = item_id

        # Set mini slot boundaries (all share same pool)
        for mini_slot in MINI_SLOT_INDICES:
            self.slot_start[mini_slot] = mini_start
            self.slot_count[mini_slot] = mini_count

        self.n_items = next_id  # Total items including reserved ID 0
        # Lazy caches for GPU upload and fast numpy decoding.
        self._gpu_arrays_cache: Optional[dict[str, np.ndarray]] = None
        # Optional fast decode helpers. These are built lazily and only for small registries
        # to avoid adding O(n_items) work to every song.
        self._id_to_item_list: Optional[list[dict]] = None
        self._id_to_name_list: Optional[list] = None

    def _maybe_build_decode_lists(self) -> None:
        if self._id_to_item_list is not None and self._id_to_name_list is not None:
            return
        n_items = int(self.n_items)
        # Building O(n_items) Python lists can be more expensive than a few dict.get()
        # calls when registries are large. Keep this conservative.
        if n_items > 12000:
            return
        id_to_item = self.id_to_item
        items: list[dict] = [{}] * n_items
        for item_id, item in id_to_item.items():
            try:
                idx = int(item_id)
            except Exception as e:
                logger.debug(f"item_registry:_maybe_build_decode_lists: {e}")
                continue
            if 0 <= idx < n_items:
                items[idx] = item or {}
        self._id_to_item_list = items
        self._id_to_name_list = [d.get("Name", "None") if d else "None" for d in items]

    def encode_genome(self, genome: list[dict]) -> np.ndarray:
        """
        Convert a genome (list of item dicts) to an array of item IDs.

        Args:
            genome: List of 9 item dicts (6 gear + 3 mini)

        Returns:
            np.ndarray: (9,) int32 array of item IDs
        """
        ids = np.zeros(9, dtype=np.int32)
        slot_name_to_id = self._slot_name_to_id

        for slot_idx, item in enumerate(genome[:9]):
            if not item:
                continue

            if isinstance(item, dict):
                name = item.get("Name", "")
                if name:
                    ids[slot_idx] = slot_name_to_id[slot_idx].get(str(name), 0)
            else:
                ids[slot_idx] = slot_name_to_id[slot_idx].get(str(item), 0)

        return ids

    def decode_genome(self, ids: np.ndarray) -> list[dict]:
        """
        Convert an array of item IDs back to a genome (list of item dicts).

        Args:
            ids: (9,) array of item IDs

        Returns:
            list[dict]: List of 9 item dicts
        """
        self._maybe_build_decode_lists()
        id_list = self._id_to_item_list
        if id_list is not None:
            n = len(id_list)
            out: list[dict] = []
            out_append = out.append
            for item_id in ids[:9]:
                idx = int(item_id)
                if idx == 0:
                    out_append({})
                    continue
                if idx < 0 or idx >= n:
                    raise ValueError(f"genome references unknown item id {idx} (registry has {n} ids)")
                out_append(id_list[idx])
            return out
        id_to_item = self.id_to_item
        out_dicts: list[dict] = []
        for item_id in ids[:9]:
            idx = int(item_id)
            if idx == 0:
                out_dicts.append({})
                continue
            item = id_to_item.get(idx)
            if item is None:
                raise ValueError(f"genome references unknown item id {idx}")
            out_dicts.append(item)
        return out_dicts

    def decode_names(self, ids: np.ndarray) -> list[str]:
        """
        Decode item IDs to "Name" strings with the same semantics used elsewhere:
        missing/empty -> "None".
        """
        self._maybe_build_decode_lists()
        name_list = self._id_to_name_list
        if name_list is not None:
            n = len(name_list)
            out: list[str] = []
            out_append = out.append
            for item_id in ids[:9]:
                idx = int(item_id)
                if idx == 0:
                    out_append("None")
                    continue
                if idx < 0 or idx >= n:
                    raise ValueError(f"genome references unknown item id {idx} (registry has {n} ids)")
                out_append(name_list[idx])
            return out
        # Dict-lookup route preserves the same semantics when decode lists are absent.
        id_to_item = self.id_to_item
        out2: list[str] = []
        for item_id in ids[:9]:
            idx = int(item_id)
            if idx == 0:
                out2.append("None")
                continue
            item = id_to_item.get(idx)
            if item is None:
                raise ValueError(f"genome references unknown item id {idx}")
            out2.append(item.get("Name", "None") if item else "None")
        return out2

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
        if isinstance(cached, dict):
            return cached

        # Build item_stats array once; reuse across GPU uploads and CPU decode paths.
        item_stats = np.zeros((self.n_items, 10), dtype=np.int32)
        name_to_idx = STAT_INDICES

        for item_id, item in self.id_to_item.items():
            if item_id == 0 or not item:
                continue
            # Prefer iterating actual keys to avoid scanning all STAT_INDICES for every item.
            for k, v in item.items():
                stat_idx = name_to_idx.get(k)
                if stat_idx is None:
                    continue
                if v:
                    item_stats[item_id, stat_idx] = int(v)

        out = {
            "item_stats": item_stats,
            "slot_start": np.array(self.slot_start, dtype=np.int32),
            "slot_count": np.array(self.slot_count, dtype=np.int32),
        }
        self._gpu_arrays_cache = out
        return out

    def encode_population(self, population: list[list[dict]]) -> np.ndarray:
        """
        Encode an entire population of genomes.

        Args:
            population: List of genomes (each genome is list of 9 item dicts)

        Returns:
            np.ndarray: (n_genomes, 9) int32 array of item IDs
        """
        n_genomes = len(population)
        ids = np.zeros((n_genomes, 9), dtype=np.int32)
        slot_name_to_id = self._slot_name_to_id

        for i, genome in enumerate(population):
            row = ids[i]
            limit = min(9, len(genome))
            for slot_idx in range(limit):
                item = genome[slot_idx]
                if not item:
                    continue

                if isinstance(item, dict):
                    name = item.get("Name", "")
                    if name:
                        row[slot_idx] = slot_name_to_id[slot_idx].get(str(name), 0)
                else:
                    row[slot_idx] = slot_name_to_id[slot_idx].get(str(item), 0)

        return ids
