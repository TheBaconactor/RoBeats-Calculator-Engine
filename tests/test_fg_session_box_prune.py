"""Session-box serve-time frontier prune (record 16.37): the GA-path bundle prune must keep the
exact per-cell winners for every stat cell inside the SESSION box while dropping rows only a
wider (global-box) audience could need.

Winner-parity oracle: a surface's exact unfloored cell score is the 16-corner multilinear form
evaluated AT the cell -- obtained by building the session basis with a degenerate combo box
(c_lo == c_hi == the cell's c), where the corner formula collapses to the cell value. The
envelope's per-pair floor margin then carries unfloored parity to floored parity, exactly as the
build-side filter's proof does.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
    _HEAD_DOM_C,
    _HEAD_DOM_F,
    _HEAD_DOM_G,
    _HEAD_DOM_V,
    _numba_head_basis_corner_score,
    _numba_session_box_keep_mask,
    _numba_session_surface_basis,
)


def _cell_score(words_row: np.ndarray, counts_row: np.ndarray, head_len: int, v: float, c: float, f: float, g: float) -> float:
    fl = np.uint64(words_row[0]) | (np.uint64(words_row[1]) << np.uint64(32))
    fh = np.uint64(words_row[2]) | (np.uint64(words_row[3]) << np.uint64(32))
    gl = np.uint64(words_row[4]) | (np.uint64(words_row[5]) << np.uint64(32))
    gh = np.uint64(words_row[6]) | (np.uint64(words_row[7]) << np.uint64(32))
    basis = _numba_session_surface_basis(
        fl, fh, gl, gh,
        np.uint64(counts_row[0]), np.uint64(counts_row[1]), np.uint64(counts_row[2]),
        0, int(head_len), float(c), float(c),
    )
    return float(_numba_head_basis_corner_score(basis, float(v), float(c), float(f), float(g), 0))


def _random_packed_frontier(rng: np.random.Generator, rows: int, head_len: int) -> tuple[np.ndarray, np.ndarray]:
    words = np.zeros((rows, 8), dtype=np.uint32)
    counts = np.zeros((rows, 3), dtype=np.int32)
    for i in range(rows):
        start = int(rng.integers(0, max(1, head_len - 2)))
        end = int(rng.integers(start + 1, head_len + 1))
        fever = 0
        for pos in range(start, end):
            fever |= 1 << pos
        greats = 0
        for pos in range(head_len):
            if rng.random() < 0.2:
                greats |= 1 << pos
        words[i, 0] = fever & 0xFFFFFFFF
        words[i, 1] = (fever >> 32) & 0xFFFFFFFF
        words[i, 4] = greats & 0xFFFFFFFF
        words[i, 5] = (greats >> 32) & 0xFFFFFFFF
        counts[i, 0] = int(rng.integers(0, 40))
        counts[i, 2] = int(rng.integers(0, 5))
        counts[i, 1] = int(counts[i, 2]) + int(rng.integers(0, 8))
    return words, counts


def test_session_box_prune_keeps_every_session_cell_winner():
    rng = np.random.default_rng(20260709)
    head_len = 40
    frontiers = [
        _random_packed_frontier(rng, 60, head_len),
        _random_packed_frontier(rng, 25, head_len),
        _random_packed_frontier(rng, 1, head_len),
    ]
    words = np.ascontiguousarray(np.concatenate([w for w, _ in frontiers]), dtype=np.uint32)
    counts = np.ascontiguousarray(np.concatenate([c for _, c in frontiers]), dtype=np.int32)
    lengths = np.asarray([w.shape[0] for w, _ in frontiers], dtype=np.int32)
    offsets = np.asarray([0, *np.cumsum(lengths[:-1])], dtype=np.int32)

    # A realistically tight session box, strictly inside the global one.
    v_lo, v_hi = 2000.0, 6400.0
    c_lo, c_hi = 2.45, 2.72
    f_lo, f_hi = 4.60, 5.48
    g_lo, g_hi = 1200.0, 4200.0
    keep = np.asarray(
        _numba_session_box_keep_mask(
            words, counts, offsets, lengths, 0, head_len,
            v_lo, v_hi, c_lo, c_hi, f_lo, f_hi, g_lo, g_hi,
        ),
        dtype=bool,
    )
    assert keep.shape == (int(words.shape[0]),)

    grid = [
        (v, c, f, min(g, v))
        for v in np.linspace(v_lo, v_hi, 4)
        for c in np.linspace(c_lo, c_hi, 4)
        for f in np.linspace(f_lo, f_hi, 4)
        for g in np.linspace(g_lo, g_hi, 4)
    ]
    pruned_any = False
    for frontier_idx in range(int(lengths.shape[0])):
        start = int(offsets[frontier_idx])
        length = int(lengths[frontier_idx])
        kept_rows = [start + i for i in range(length) if keep[start + i]]
        assert kept_rows, "the greedy filter must keep at least one row per frontier"
        if len(kept_rows) < length:
            pruned_any = True
        for v, c, f, g in grid:
            full_best = max(_cell_score(words[start + i], counts[start + i], head_len, v, c, f, g) for i in range(length))
            kept_best = max(_cell_score(words[r], counts[r], head_len, v, c, f, g) for r in kept_rows)
            assert kept_best >= full_best - 1e-9, (frontier_idx, v, c, f, g)
    assert pruned_any, "the tight session box should prune something on random frontiers"


def test_session_box_prune_is_keep_all_when_box_equals_global():
    # With the box at the global corners the serve filter may only drop rows the build-side
    # filter would also have dropped (small frontiers skip the build prune via min_surfaces), so
    # winner parity must hold over the FULL global box grid too.
    rng = np.random.default_rng(7)
    head_len = 24
    words, counts = _random_packed_frontier(rng, 30, head_len)
    lengths = np.asarray([30], dtype=np.int32)
    offsets = np.asarray([0], dtype=np.int32)
    keep = np.asarray(
        _numba_session_box_keep_mask(
            np.ascontiguousarray(words), np.ascontiguousarray(counts), offsets, lengths, 0, head_len,
            float(_HEAD_DOM_V[0]), float(_HEAD_DOM_V[1]),
            float(_HEAD_DOM_C[0]), float(_HEAD_DOM_C[1]),
            float(_HEAD_DOM_F[0]), float(_HEAD_DOM_F[1]),
            float(_HEAD_DOM_G[0]), float(_HEAD_DOM_G[1]),
        ),
        dtype=bool,
    )
    grid = [
        (v, c, f, min(g, v))
        for v in np.linspace(float(_HEAD_DOM_V[0]), float(_HEAD_DOM_V[1]), 5)
        for c in np.linspace(float(_HEAD_DOM_C[0]), float(_HEAD_DOM_C[1]), 3)
        for f in np.linspace(float(_HEAD_DOM_F[0]), float(_HEAD_DOM_F[1]), 3)
        for g in np.linspace(float(_HEAD_DOM_G[0]), float(_HEAD_DOM_G[1]), 5)
    ]
    kept_rows = [i for i in range(30) if keep[i]]
    for v, c, f, g in grid:
        full_best = max(_cell_score(words[i], counts[i], head_len, v, c, f, g) for i in range(30))
        kept_best = max(_cell_score(words[r], counts[r], head_len, v, c, f, g) for r in kept_rows)
        assert kept_best >= full_best - 1e-9


def test_session_head_dominance_box_reads_luts_and_fails_loud():
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import session_head_dominance_box

    box = session_head_dominance_box({
        "Combo Multiplier": np.asarray([2.4, 2.5, 2.7]),
        "Fever Multiplier": np.asarray([4.4, 5.0]),
    })
    assert box[2] == pytest.approx(2.4) and box[3] == pytest.approx(2.7)
    assert box[4] == pytest.approx(4.4) and box[5] == pytest.approx(5.0)
    assert box[0] == float(_HEAD_DOM_V[0]) and box[7] == float(_HEAD_DOM_G[1])
    with pytest.raises(ValueError):
        session_head_dominance_box({"Combo Multiplier": np.asarray([2.4])})
    with pytest.raises(ValueError):
        # escapes the global box the payload envelope was built against
        session_head_dominance_box({
            "Combo Multiplier": np.asarray([1.0, 2.7]),
            "Fever Multiplier": np.asarray([4.4, 5.0]),
        })


def test_issue116_v30_compact_session_prune_preserves_ids_offsets_and_pattern_table(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
        FgResponseFrontierScoringBundle,
    )

    rng = np.random.default_rng(11)
    head_len = 20
    w0, c0 = _random_packed_frontier(rng, 40, head_len)
    w1, c1 = _random_packed_frontier(rng, 15, head_len)
    words = np.ascontiguousarray(np.concatenate([w0, w1]), dtype=np.uint32)
    counts = np.ascontiguousarray(np.concatenate([c0, c1]), dtype=np.int32)
    pattern_words, pattern_ids = np.unique(words, axis=0, return_inverse=True)
    pattern_words = np.ascontiguousarray(pattern_words, dtype=np.uint32)
    pattern_ids = np.ascontiguousarray(pattern_ids, dtype=np.int32)
    pattern_coeffs = rng.integers(0, 100, size=(int(pattern_words.shape[0]), 4)).astype(np.int32)

    def _load_compact(_key, ranges):
        assert tuple(ranges) == ((0, 55),)
        return pattern_ids, counts, pattern_words, pattern_coeffs

    def _expanded_loader_must_not_run(*_args, **_kwargs):
        raise AssertionError("session prune must not expand V30 logical rows")

    monkeypatch.setattr(response_cache, "load_first_surface_scoring_patterns", _load_compact)
    monkeypatch.setattr(response_cache, "load_first_surface_scoring_rows", _expanded_loader_must_not_run)
    bundle = FgResponseFrontierScoringBundle(
        cache_key=("test",),
        frontier_idx_by_key={(0, 0): 0, (0, 1): 1, (1, 0): 2},
        frontier_idx_by_stat=np.zeros((2, 2), dtype=np.int32),
        raw_fill_by_ff=np.zeros(1),
        non_fever_base_by_ff=np.zeros(1, dtype=np.int32),
        real_time_by_ft=np.zeros(1),
        frontier_meta=np.zeros((3, 1), dtype=np.int32),
        surface_pattern_ids=np.empty((0,), dtype=np.int32),
        surface_pattern_words=np.empty((0, 8), dtype=np.uint32),
        surface_counts=np.empty((0, 3), dtype=np.int32),
        surface_pattern_head_coeffs=np.empty((0, 4), dtype=np.int32),
        frontier_offsets=np.asarray([0, 0, 40], dtype=np.int32),
        frontier_lengths=np.asarray([40, 40, 15], dtype=np.int32),
        surface_row_count=55,
        total_notes=head_len,
        long_notes=0,
        use_forced_great_timing=True,
    )
    ref_arrays = {
        "Combo Multiplier": np.asarray([2.45, 2.72]),
        "Fever Multiplier": np.asarray([4.6, 5.48]),
    }
    v_lo, v_hi, c_lo, c_hi, f_lo, f_hi, g_lo, g_hi = response_cache.session_head_dominance_box(ref_arrays)
    original_offsets = np.asarray(bundle.frontier_offsets, dtype=np.int32)
    original_lengths = np.asarray(bundle.frontier_lengths, dtype=np.int32)
    expected_keep = np.asarray(
        _numba_session_box_keep_mask(
            words,
            counts,
            original_offsets,
            original_lengths,
            0,
            head_len,
            v_lo,
            v_hi,
            c_lo,
            c_hi,
            f_lo,
            f_hi,
            g_lo,
            g_hi,
        ),
        dtype=bool,
    )
    expected_used_patterns, expected_pattern_ids = np.unique(pattern_ids[expected_keep], return_inverse=True)
    pruned = response_cache.session_prune_scoring_bundle(bundle, ref_arrays)
    assert int(pruned.surface_row_count) == int(pruned.surface_pattern_ids.shape[0])
    assert int(pruned.surface_pattern_ids.shape[0]) <= 55
    assert pruned.surface_counts.shape == (int(pruned.surface_row_count), 3)
    assert np.array_equal(pruned.surface_pattern_ids, expected_pattern_ids.astype(np.int32))
    assert np.array_equal(pruned.surface_counts, counts[expected_keep])
    assert np.array_equal(pruned.surface_pattern_words, pattern_words[expected_used_patterns])
    assert np.array_equal(pruned.surface_pattern_head_coeffs, pattern_coeffs[expected_used_patterns])
    lengths = np.asarray(pruned.frontier_lengths, dtype=np.int64)
    offsets = np.asarray(pruned.frontier_offsets, dtype=np.int64)
    assert bool(np.all(lengths >= 1))
    assert int(offsets[0]) == int(offsets[1]) == 0
    assert int(lengths[0]) == int(lengths[1])
    assert int(offsets[2]) == int(lengths[0])
    assert int(lengths[0] + lengths[2]) == int(pruned.surface_row_count)
    # unchanged metadata carried through
    assert pruned.total_notes == head_len and pruned.cache_key == ("test",)
    assert dataclasses.is_dataclass(pruned)
