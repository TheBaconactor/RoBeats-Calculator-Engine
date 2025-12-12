"""
Population indexing helpers (host-side).

Phase 3 groundwork for the GPU-native GA:
- Assign a stable integer item_id to each candidate gear/mini item
- Build a dense item_stats table: item_stats[item_id, stat_id]
- Encode genomes/populations as integer indices: population_indices[genome_id, slot_id] = item_id

This file is intentionally dependency-light so it can be used from both GA and scoring code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np


# Fixed schema: only the stats required by scoring/gem optimization / FG.
STAT_KEYS: Tuple[str, ...] = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Time",
    "Fever Fill Rate",
    "Beat",
    "Vibe",
    "Rush",
    "Flow",
    "Chill",
)


@dataclass(frozen=True)
class PopulationIndex:
    """
    Host-side dense representation of the item pool + population.

    - **key_to_id** maps (type, Name) -> item_id (0 reserved for empty).
    - **item_stats** is a dense int32 array indexed by item_id.
    - **id_to_item** is best-effort for decoding (may contain None entries if items were missing).
    """

    key_to_id: Dict[Tuple[str, str], int]
    item_stats: np.ndarray
    id_to_item: List[dict | None]


def item_key(item) -> Tuple[str, str]:
    """
    Derive a stable identity key for an item.

    We use (type, Name) to avoid collisions across slots.
    Missing/empty items map to ("", "").
    """
    if not isinstance(item, dict):
        return ("", "")
    return (str(item.get("type", "") or ""), str(item.get("Name", "") or ""))


def build_item_index(items: Iterable[dict]) -> Tuple[Dict[Tuple[str, str], int], np.ndarray]:
    """
    Build a stable mapping (type,Name) -> item_id and a dense stats table.

    Returns:
      - key_to_id: dict mapping (type,Name) to item_id
      - item_stats: int32 array of shape (n_items, len(STAT_KEYS))
                   Row 0 is reserved as the zero-item.
    """
    keys = set()
    for it in items:
        k = item_key(it)
        if k == ("", ""):
            continue
        keys.add(k)

    sorted_keys = sorted(keys)

    key_to_id: Dict[Tuple[str, str], int] = {("", ""): 0}
    for idx, k in enumerate(sorted_keys, start=1):
        key_to_id[k] = idx

    n_items = len(key_to_id)
    item_stats = np.zeros((n_items, len(STAT_KEYS)), dtype=np.int32)

    # Fill stats rows
    for it in items:
        k = item_key(it)
        item_id = key_to_id.get(k)
        if item_id is None or item_id == 0:
            continue
        for s_idx, s_key in enumerate(STAT_KEYS):
            try:
                item_stats[item_id, s_idx] = int(it.get(s_key, 0) or 0)
            except Exception:
                item_stats[item_id, s_idx] = 0

    return key_to_id, item_stats


def build_population_index(items: Iterable[dict]) -> PopulationIndex:
    """
    Build a PopulationIndex from an iterable of item dicts.

    The mapping is deterministic (sorted by (type,Name)).
    """
    # Materialize because we iterate multiple times.
    items_list = list(items)
    key_to_id, item_stats = build_item_index(items_list)

    # Best-effort reverse mapping for decoding.
    id_to_item: List[dict | None] = [None] * int(item_stats.shape[0])
    for it in items_list:
        k = item_key(it)
        item_id = int(key_to_id.get(k, 0))
        if item_id <= 0:
            continue
        if id_to_item[item_id] is None:
            id_to_item[item_id] = it

    return PopulationIndex(key_to_id=key_to_id, item_stats=item_stats, id_to_item=id_to_item)


def encode_genome(genome: Sequence[dict], key_to_id: Dict[Tuple[str, str], int], *, slots: int = 9) -> np.ndarray:
    """
    Encode a single genome into a fixed-length array of item_ids.
    """
    out = np.zeros((slots,), dtype=np.int32)
    n = min(slots, len(genome))
    for i in range(n):
        out[i] = key_to_id.get(item_key(genome[i]), 0)
    return out


def encode_population(population: Sequence[Sequence[dict]], key_to_id: Dict[Tuple[str, str], int], *, slots: int = 9) -> np.ndarray:
    """
    Encode a population into (n_genomes, slots) item_id indices.
    """
    n = len(population)
    out = np.zeros((n, slots), dtype=np.int32)
    for i, genome in enumerate(population):
        out[i, :] = encode_genome(genome, key_to_id, slots=slots)
    return out


def decode_genome(indices: Sequence[int], id_to_item: Sequence[dict | None], *, slots: int = 9) -> List[dict]:
    """
    Decode a fixed-length genome of item_ids back to item dicts.

    Unknown/empty items decode to {}.
    """
    out: List[dict] = []
    n = min(int(slots), len(indices))
    for i in range(n):
        item_id = int(indices[i])
        if 0 <= item_id < len(id_to_item):
            it = id_to_item[item_id]
            out.append(it if isinstance(it, dict) else {})
        else:
            out.append({})
    while len(out) < int(slots):
        out.append({})
    return out


