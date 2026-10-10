"""FG gem scoring reads a bundle's surfaces from its in-memory (session-pruned) pool or gathers them from its tables;
both give the same winners. CPU-only (numba), no GPU."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import (
    pack_surface_patterns,
    surface_head_coeffs,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import score_fg_base_components

_IDX = np.arange(MAX_STAT + 1, dtype=np.float64)
_CURVES = StatCurves.from_mapping({
    "Perfect Points": _IDX * 0.5 + 0.3, "Combo Multiplier": 1.0 + _IDX * 0.011, "Fever Multiplier": 1.0 + _IDX * 0.017,
    "Fever Time": np.ones(MAX_STAT + 1) * 0.15, "Fever Fill Rate": np.ones(MAX_STAT + 1) * 0.333,
})


def _bundles(rng: np.random.Generator) -> tuple[SimpleNamespace, SimpleNamespace]:
    """One random bundle twice: as an in-memory pool and as on-disk tables. Twenty surface segments with pattern IDs
    that skip part of the table; three more frontiers share earlier segments."""
    words = np.zeros((60, 8), dtype=np.uint32)
    for row in range(60):
        start = int(rng.integers(0, 98))
        fever = sum(1 << note for note in range(start, int(rng.integers(start + 1, 101))))
        greats = sum(1 << note for note in range(100) if rng.random() < 0.2)
        for word in range(4):
            words[row, word] = (fever >> (32 * word)) & 0xFFFFFFFF
            words[row, 4 + word] = (greats >> (32 * word)) & 0xFFFFFFFF
    coeffs = surface_head_coeffs(words, head_len=100)
    lengths = rng.integers(3, 51, size=20)
    offsets = np.concatenate(([0], np.cumsum(lengths)[:-1]))
    rows = int(lengths.sum())
    pattern_ids = rng.integers(0, 45, size=rows).astype(np.int32)
    counts = np.empty((rows, 3), dtype=np.int32)
    counts[:, 0] = rng.integers(0, 41, size=rows)
    counts[:, 2] = rng.integers(0, 6, size=rows)
    counts[:, 1] = counts[:, 2] + rng.integers(0, 9, size=rows)
    segments = [*range(20), 3, 3, 11]
    frontiers = {
        "frontier_idx_by_stat": rng.integers(0, len(segments), size=(MAX_STAT + 1, MAX_STAT + 1)).astype(np.int32),
        "frontier_offsets": offsets[segments].astype(np.int32),
        "frontier_lengths": lengths[segments].astype(np.int32),
    }
    in_memory = SimpleNamespace(
        **frontiers,
        surface_pattern_ids=pattern_ids,
        surface_pattern_words=words,
        surface_counts=counts,
        surface_pattern_head_coeffs=coeffs,
    )
    tables = SimpleNamespace(
        **frontiers,
        surface_pattern_ids=np.empty((0,), dtype=np.int32),
        surface_rows=np.vstack((pattern_ids, counts.T)).astype(np.uint32),
        surface_patterns=pack_surface_patterns(words, coeffs).T,
    )
    return in_memory, tables


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("colors", [("Chill", "Flow"), ("Rush", "Beat"), ("Vibe", "Vibe")])
def test_fg_scoring_reads_in_memory_pools_and_bundle_tables_alike(seed: int, colors: tuple[str, str]) -> None:
    rng = np.random.default_rng(seed)
    in_memory, tables = _bundles(rng)
    components = np.column_stack([
        rng.integers(0, 60, size=24),
        rng.integers(0, 60, size=24),
        rng.integers(0, 60, size=24),
        rng.integers(20, 120, size=24),
        rng.integers(20, 120, size=24),
        rng.integers(0, MAX_STAT + 1, size=24),
        rng.integers(0, MAX_STAT + 1, size=24),
    ]).astype(np.int32)
    song = SimpleNamespace(fg_inputs=SimpleNamespace(primary_color=colors[0], secondary_color=colors[1], total_notes=140))
    in_memory_winners, table_winners = (
        score_fg_base_components(base_components=components, song=song, curves=_CURVES, selected_color=colors[0],
                                 scoring_bundle=bundle, total_budget=12)
        for bundle in (in_memory, tables)
    )
    assert in_memory_winners == table_winners
    assert all(winner.inner_row[0] > 0 for winner in in_memory_winners.values())
