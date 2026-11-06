"""ftff_shortlist against its definition: every reachable key's options compared pair by pair."""

from types import SimpleNamespace

import numpy as np
import pytest
from numba import njit

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.rules import ELEMENT_GEM_GAIN, GEM_BUDGET, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays, ftff_shortlist

SIDE = MAX_STAT + 1


def _payload(rng: np.random.Generator, n_surfaces: int, stacked_cells: float) -> SimpleNamespace:
    """A frontier of surfaces that grow with the stats, as real ones do: a random walk of head bits and body fever, one
    surface per cell by a noisy level of (FT, FF), a second one on some cells."""
    surfaces = np.zeros((n_surfaces, 5), dtype=np.int64)
    for s in range(1, n_surfaces):
        parent = surfaces[rng.integers(max(0, s - 4), s)]
        surfaces[s] = parent
        surfaces[s, rng.integers(0, 4)] |= 1 << int(rng.integers(0, 32))
        surfaces[s, 4] += rng.integers(0, 3)
    tilt = rng.uniform(0.3, 1.0, size=2)
    levels = np.add.outer(tilt[0] * np.arange(SIDE), tilt[1] * np.arange(SIDE))
    levels += rng.normal(0.0, 4.0, size=levels.shape)
    cells = np.clip((levels / levels.max() * n_surfaces).astype(np.int64), 0, n_surfaces - 1)
    counts = 1 + (rng.random((SIDE, SIDE)) < stacked_cells).astype(np.int32)
    offsets = (np.cumsum(counts.ravel()) - counts.ravel()).reshape(SIDE, SIDE).astype(np.int32)
    pool = np.empty(int(counts.sum()), dtype=np.int64)
    pool[offsets.ravel()] = cells.ravel()
    stacked = counts.ravel() == 2
    pool[offsets.ravel()[stacked] + 1] = rng.integers(0, n_surfaces, size=int(stacked.sum()))
    rows = surfaces[pool]
    return SimpleNamespace(
        frontier_pool_used=len(rows),
        grid_frontier_masks_bits_pool=rows[:, :4][None],
        grid_frontier_body_fever_pool=rows[:, 4][None],
        grid_frontier_offset=offsets[None],
        grid_frontier_count=counts[None],
    )


@njit
def _kept_bitmap(key, frontier, combos, gains):
    """Per combo of the table, whether an option of `key` on it stays, by the definition in ftff_shortlist: all pairs,
    each option's possible beaters in order of residual gems, so that most options stop at their first beater."""
    offsets, counts, masks, body = frontier
    combo_ft, combo_ff, combo_left, by_residual = combos
    kept = np.zeros(len(combo_ft), dtype=np.bool_)
    n = 0
    option_combo = np.empty(2 * len(combo_ft), dtype=np.int64)
    option_row = np.empty(2 * len(combo_ft), dtype=np.int64)
    for c in by_residual:
        x, y = key[0] + STAT_GEM_GAIN_FEVER * combo_ft[c], key[1] + STAT_GEM_GAIN_FEVER * combo_ff[c]
        if x <= MAX_STAT and y <= MAX_STAT:
            for row in range(offsets[x, y], offsets[x, y] + counts[x, y]):
                option_combo[n], option_row[n] = c, row
                n += 1
    value = np.empty(n, dtype=np.int64)
    for o in range(n):
        c = option_combo[o]
        value[o] = gains[0] * combo_ft[c] + gains[1] * combo_ff[c] + gains[2] * combo_left[c]
    for o in range(n):
        co, ro = option_combo[o], option_row[o]
        beaten = False
        for p in range(n):
            cp, rp = option_combo[p], option_row[p]
            if combo_left[cp] < combo_left[co]:
                break
            if p == o or value[p] < value[o] or body[rp] < body[ro] or (masks[ro] & ~masks[rp]).any():
                continue
            identical = combo_left[cp] == combo_left[co] and value[p] == value[o] and body[rp] == body[ro] and (
                masks[rp] == masks[ro]).all()
            if not identical or cp > co:
                beaten = True
                break
        if not beaten:
            kept[co] = True
    return kept


@pytest.mark.parametrize(
    "primary, secondary, seed, stacked_cells",
    [
        ("Rush", "Flow", 1, 0.0),  # equal FT and FF weights: every option on a diagonal ties
        ("Rush", "Rush", 2, 0.02),
        ("Beat", "Vibe", 3, 0.0),
        ("Vibe", "Beat", 4, 0.3),
        ("Beat", "Beat", 5, 0.02),
        ("Vibe", "Vibe", 6, 0.0),
        ("Flow", "Vibe", 7, 0.02),
        ("Chill", "Beat", 8, 0.0),
    ],
)
def test_shortlist_keeps_what_the_definition_keeps(primary, secondary, seed, stacked_cells):
    rng = np.random.default_rng(seed)
    payload = _payload(rng, n_surfaces=int(rng.integers(3, 200)), stacked_cells=stacked_cells)
    reach = rng.random((SIDE, SIDE)) < 0.12
    flags = build_color_flags(primary, secondary, primary)
    shortlist = ftff_shortlist(payload, reach=reach, color_flags=flags)

    assert not shortlist.count[~reach.ravel()].any()
    assert shortlist.start.dtype == shortlist.count.dtype == shortlist.combos.dtype == np.int32
    assert np.array_equal(shortlist.start[1:], (shortlist.start + shortlist.count)[:-1])
    element = ELEMENT_GEM_GAIN * (2 * flags["is_p_ov"] + flags["is_s_ov"])
    gains = (STAT_GEM_ELEMENT_GAIN * (2 * flags["is_p_ft"] + flags["is_s_ft"]),
             STAT_GEM_ELEMENT_GAIN * (2 * flags["is_p_ff"] + flags["is_s_ff"]), element)
    combo_ft, combo_ff, combo_left = ftff_combo_arrays(GEM_BUDGET)
    combos = combo_ft, combo_ff, combo_left, np.argsort(-combo_left, kind="stable")
    frontier = (payload.grid_frontier_offset[0], payload.grid_frontier_count[0],
                payload.grid_frontier_masks_bits_pool[0], payload.grid_frontier_body_fever_pool[0])
    for key in np.argwhere(reach):
        index = key[0] * SIDE + key[1]
        got = shortlist.combos[shortlist.start[index] : shortlist.start[index] + shortlist.count[index]]
        assert np.array_equal(got, np.flatnonzero(_kept_bitmap(key, frontier, combos, gains))), key
