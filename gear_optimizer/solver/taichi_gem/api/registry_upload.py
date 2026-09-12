"""One upload/cache owner for the registry fields shared by GA and skyline."""

import numpy as np

_items = None
_base = None


def reset_registry_upload_cache() -> None:
    global _items, _base
    _items = _base = None


def upload_item_stats(item_stats: np.ndarray, slot_start: np.ndarray, slot_count: np.ndarray) -> int:
    from .. import fields
    from ..kernel_loader import get_kernels
    from .initialization import ensure_ready
    global _items
    ensure_ready()
    n = len(item_stats)
    if n > fields.MAX_ITEMS:
        raise ValueError(f"Too many items: {n} > {fields.MAX_ITEMS}")
    stats = np.ascontiguousarray(item_stats[:, :fields.ITEM_STAT_DIM], dtype=np.int32)
    starts = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    counts = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    count = min(fields.MAX_SLOTS, np.size(slot_start), np.size(slot_count))
    starts[:count] = np.asarray(slot_start, dtype=np.int32).reshape(-1)[:count]
    counts[:count] = np.asarray(slot_count, dtype=np.int32).reshape(-1)[:count]
    values = (stats, starts, counts)
    if _items is not None and all(np.array_equal(a, b) for a, b in zip(_items, values)):
        return n
    get_kernels().skyline_upload_item_stats_and_slots_kernel(stats, n, starts, counts)
    # Content snapshots also handle in-place mutation and recycled Python ids.
    _items = tuple(value.copy() for value in values)
    return n


def upload_base_fixed_stats(base_stats: np.ndarray) -> None:
    from .. import fields
    from .initialization import ensure_ready
    global _base
    ensure_ready()
    values = np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32)
    values[:len(base_stats)] = np.asarray(base_stats, dtype=np.int32)
    if _base is None or not np.array_equal(_base, values):
        fields.base_fixed_stats.from_numpy(values)
        _base = values.copy()
