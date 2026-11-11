"""The GPU's exact scores against the game's float64, here numpy's and score.py's: the notes float32 cannot settle above
all, the integers a value lands next to."""

import numpy as np
import pytest
import taichi as ti

from gear_optimizer.gamedata import COMBO_RAMP_NOTES, stat_curves
from gear_optimizer.gpu import device, fields, ga
from gear_optimizer.gpu.scoring import (
    GpuColorFlags,
    float64_floor,
    float64_of,
    float64_product,
    _note_score,
    _surface_score,
    gpu_color_flags,
    pair_bound,
    pair_floor,
    pair_score,
    search_context,
)
from gear_optimizer.score import Factors, TimelineCell, best_timeline_score
from tests.gpu_support import ga_inputs, song

pytestmark = pytest.mark.gpu


_I32 = ti.types.ndarray(dtype=ti.i32, ndim=1)
_U64 = ti.types.ndarray(dtype=ti.u64, ndim=1)


@ti.kernel
def _products(a: _U64, b: _U64, out: _U64):
    for i in range(a.shape[0]):
        out[i] = float64_product(a[i], b[i])


def _run_products(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    device.ensure_ready()
    words = np.zeros(len(a), dtype=np.uint64)
    _products(a.view(np.uint64), b.view(np.uint64), words)
    ti.sync()
    return words


def test_a_product_rounds_as_ieee_float64():
    rng = np.random.default_rng(1)
    n = 400_000
    a = rng.uniform(1.0, 8192.0, n)
    b = rng.uniform(1.0, 6.0, n)
    # Few mantissa bits make exact halves of the last place: round half to even.
    a[: n // 2] = np.ldexp(np.round(np.ldexp(a[: n // 2], 20)), -20)
    b[: n // 2] = np.ldexp(np.round(np.ldexp(b[: n // 2], 32)) + 1, -32)
    np.testing.assert_array_equal(_run_products(a, b), (a * b).view(np.uint64))


@ti.kernel
def _integers(values: _I32, out: _U64, floors: _I32):
    for i in range(values.shape[0]):
        bits = float64_of(values[i])
        out[i] = bits
        floors[i] = float64_floor(bits)


def test_an_integer_converts_and_floors_back():
    device.ensure_ready()
    values = np.arange(1, 1 << 16, dtype=np.int32)
    bits, floors = np.zeros(len(values), dtype=np.uint64), np.zeros(len(values), dtype=np.int32)
    _integers(values, bits, floors)
    ti.sync()
    np.testing.assert_array_equal(bits, values.astype(np.float64).view(np.uint64))
    np.testing.assert_array_equal(floors, values)


@ti.kernel
def _note_scores(base: _I32, combo_stat: _I32, note: _I32, fever_stat: _I32, in_fever: _I32, out: _I32):
    for i in range(base.shape[0]):
        out[i] = _note_score(base[i], combo_stat[i], note[i], fever_stat[i], ti.cast(in_fever[i], ti.u32))


def _game_note_values(base, combo_stat, note, fever_stat, in_fever) -> np.ndarray:
    """A note's value before its floor, in score.py's float64 and operation order."""
    curves = stat_curves()
    combos = np.column_stack((curves.combo_ramp, curves.f64["Combo Multiplier"]))
    value = base.astype(np.float64) * combos[combo_stat, note]
    value = np.where(in_fever != 0, value * curves.f64["Fever Multiplier"][fever_stat], value)
    return value


def test_a_note_scores_the_games_floor_where_float32_cannot_tell():
    device.ensure_ready()
    rng = np.random.default_rng(2)
    n = 4_000_000
    base = rng.integers(200, 4000, n).astype(np.int32)
    combo_stat = rng.integers(0, 161, n).astype(np.int32)
    note = rng.integers(0, COMBO_RAMP_NOTES + 1, n).astype(np.int32)
    fever_stat = rng.integers(0, 161, n).astype(np.int32)
    in_fever = rng.integers(0, 2, n).astype(np.int32)
    value = _game_note_values(base, combo_stat, note, fever_stat, in_fever)
    nearest = np.abs(value - np.round(value))
    # The draws closest to an integer, and some others.
    close = np.argsort(nearest)[: 500_000]
    keep = np.concatenate((close, rng.integers(0, n, 100_000)))
    columns = [column[keep] for column in (base, combo_stat, note, fever_stat, in_fever)]
    assert nearest[close[1000]] < 3e-5
    out = np.zeros(len(keep), dtype=np.int32)
    _note_scores(*columns, out)
    ti.sync()
    np.testing.assert_array_equal(out, np.floor(value[keep]).astype(np.int32))


@ti.kernel
def _pair_columns(
    stats: ti.types.vector(7, ti.i32), budget: ti.i32, base_init: ti.i32, flags: GpuColorFlags, n_surfaces: ti.i32,
    out: ti.types.ndarray(dtype=ti.i32, ndim=4),
):
    """Per surface and (CM, FM) pair: its score, its bound, the score it is sure of, and the score a floor of its own, or
    of one above it, returns."""
    for pool_idx, g_cm, g_fm in ti.ndrange(n_surfaces, 21, 21):
        ctx = search_context(budget, stats, base_init, flags, pool_idx)
        score = pair_score(ctx, g_cm * 3, g_fm * 3, 0)
        out[pool_idx, g_cm, g_fm, 0] = score
        out[pool_idx, g_cm, g_fm, 1] = ti.cast(pair_bound(ctx, g_cm * 3, g_fm * 3), ti.i32)
        out[pool_idx, g_cm, g_fm, 2] = pair_floor(ctx, g_cm * 3, g_fm * 3)
        out[pool_idx, g_cm, g_fm, 3] = pair_score(ctx, g_cm * 3, g_fm * 3, score)
        out[pool_idx, g_cm, g_fm, 4] = pair_score(ctx, g_cm * 3, g_fm * 3, score + 100_000)


def test_a_pairs_bound_and_floor_hold_its_score_and_a_floor_keeps_it():
    inputs = ga_inputs(song(n_notes=400, name="Pairs"))
    device.ensure_ready()
    device.upload_timeline(inputs.timed_song.timeline_key, ga.build_or_load_timeline_frontier_payload(inputs.timed_song, inputs.curves).payload)
    stats = ti.Vector([60, 60, 60, 80, 60, 60, 60], dt=ti.i32)
    n_surfaces = 64
    out = np.zeros((n_surfaces, 21, 21, 5), dtype=np.int32)
    _pair_columns(stats, 60, 220, gpu_color_flags(inputs.color_flags), n_surfaces, out)
    ti.sync()
    scores = out[..., 0]
    assert np.all(scores > 0)
    assert np.all(out[..., 1] >= scores)
    assert np.all(out[..., 2] <= scores)
    np.testing.assert_array_equal(out[..., 3], scores)
    assert np.all(out[..., 4] == -1)


@ti.kernel
def _surface_scores(
    stats: ti.types.vector(7, ti.i32), flags: GpuColorFlags, pools: _I32, bases: _I32, combo_stats: _I32, fever_stats: _I32,
    out: _I32,
):
    for i in range(pools.shape[0]):
        out[i] = _surface_score(search_context(60, stats, 220, flags, pools[i]), bases[i], combo_stats[i], fever_stats[i], 0)


def test_a_surface_scores_as_score_py():
    curves = stat_curves()
    inputs = ga_inputs(song(n_notes=400, name="Surfaces"))
    device.ensure_ready()
    payload = ga.build_or_load_timeline_frontier_payload(inputs.timed_song, inputs.curves).payload
    device.upload_timeline(inputs.timed_song.timeline_key, payload)
    rng = np.random.default_rng(3)
    n = 20_000
    pools = rng.integers(0, int(payload.frontier_pool_used), n).astype(np.int32)
    bases = rng.integers(300, 4000, n).astype(np.int32)
    combo_stats = rng.integers(0, 161, n).astype(np.int32)
    fever_stats = rng.integers(0, 161, n).astype(np.int32)
    out = np.zeros(n, dtype=np.int32)
    stats = ti.Vector([60, 60, 60, 80, 60, 60, 60], dt=ti.i32)
    _surface_scores(stats, gpu_color_flags(inputs.color_flags), pools, bases, combo_stats, fever_stats, out)
    ti.sync()
    for i in range(n):
        pool = pools[i]
        cell = TimelineCell(
            head_words=np.asarray(payload.grid_frontier_masks_bits_pool[0, pool : pool + 1, :4], dtype=np.uint64),
            body_fever=np.asarray(payload.grid_frontier_body_fever_pool[0, pool : pool + 1], dtype=np.int64),
            body_normal=np.asarray(payload.grid_frontier_body_normal_pool[0, pool : pool + 1], dtype=np.int64),
        )
        factors = Factors(
            float(bases[i]), curves.factor("Combo Multiplier", int(combo_stats[i])), curves.ramp(int(combo_stats[i])),
            curves.factor("Fever Multiplier", int(fever_stats[i])), 0, 0, 0,
        )
        assert int(out[i]) == best_timeline_score(factors, cell, 400)[0]
