from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.rules import MAX_STAT
from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats


def _stats_table() -> list[list[float]]:
    return [[float(row + col) for col in range(5)] for row in range(MAX_STAT + 1)]


def test_build_ref_arrays_from_stats_rejects_missing_table() -> None:
    with pytest.raises(ValueError, match="at least 161 rows"):
        build_ref_arrays_from_stats([], dtype=np.float32)


def test_build_ref_arrays_from_stats_rejects_short_rows() -> None:
    table = _stats_table()
    table[MAX_STAT] = [1.0]

    with pytest.raises(ValueError, match="must contain 5 columns"):
        build_ref_arrays_from_stats(table, dtype=np.float32)


def test_build_ref_arrays_from_stats_uses_reversed_lookup_axis() -> None:
    refs = build_ref_arrays_from_stats(_stats_table(), dtype=np.float32)

    assert refs["Perfect Points"][0] == np.float32(MAX_STAT)
    assert refs["Fever Time"][MAX_STAT] == np.float32(4.0)
