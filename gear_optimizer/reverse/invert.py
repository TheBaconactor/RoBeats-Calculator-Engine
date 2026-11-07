"""The stat lines whose exact all-Perfect score is a shown score.

For a surface, the score is at most base x K(combo, fever) and over it by less than one point a note, K the surface's
bound shape (gem_search._surface_shape), so a (CM, FM) pair leaves at most a couple of whole base values, and base
values above the loadout bound leave none. Pairs are visited in TILE x TILE blocks whose corner bounds them all.

Cost: O(U (B + J b + p)) for U surfaces, B = 400 blocks, J bound vertices, b blocks that survive and p pairs in them:
the (CM, FM) square 161^2 is walked only where the loadout bound can still reach the score. The exact score is one
gem_search._surface_score, O(100), for the ~7% of pairs with a whole base value.
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.gem_search import _surface_score

_TILE = 8


@jit(nopython=True, cache=True)
def _vertex_bound(values, prices, relief, u, cm, fm, floor):
    """The lowest vertex bound on a surface's base value at this CM and FM (stopping below floor)."""
    best = 1.0e18
    for j in range(values.shape[0]):
        bound = values[j] - prices[j, 1] * cm - prices[j, 2] * fm + relief[u, j]
        if bound < best:
            best = bound
            if best < floor:
                return best
    return best


@jit(nopython=True, cache=True)
def perfect_lines(score, surfaces, multipliers, notes, ceiling, out):
    """Every (surface, CM, FM, base) with exactly this score under its ceiling, into out; returns how many there are, or
    out's rows + 1 where they stop fitting."""
    words, coeffs, pattern, body_fever = surfaces
    combo, ramp, fever = multipliers
    head_len, body_total = notes
    values, prices, relief = ceiling
    total_notes = head_len + body_total
    wanted = float(score)
    found = 0
    for u in range(body_fever.shape[0]):
        p = pattern[u]
        bf = int(body_fever[u])
        n_hn, n_hf, sigma_hn, sigma_hf = coeffs[p, 0], coeffs[p, 1], coeffs[p, 2], coeffs[p, 3]
        a = bf + sigma_hf * 0.01
        e = body_total - bf + sigma_hn * 0.01
        f = n_hf - sigma_hf * 0.01
        g = n_hn - sigma_hn * 0.01
        for cm_block in range(0, MAX_STAT + 1, _TILE):
            cm_top = min(cm_block + _TILE - 1, MAX_STAT)
            top_combo = combo[cm_top]
            alpha_top, beta_top = a * top_combo + f, e * top_combo + g
            for fm_block in range(0, MAX_STAT + 1, _TILE):
                fm_top = min(fm_block + _TILE - 1, MAX_STAT)
                shape = alpha_top * fever[fm_top] + beta_top
                if _vertex_bound(values, prices, relief, u, cm_block, fm_block, wanted / shape) * shape < wanted:
                    continue
                for cm in range(cm_block, cm_top + 1):
                    alpha, beta = a * combo[cm] + f, e * combo[cm] + g
                    for fm in range(fm_block, fm_top + 1):
                        shape = alpha * fever[fm] + beta
                        base = int(np.ceil(wanted / shape))
                        last = int((wanted + total_notes) / shape)
                        while base <= last:
                            if base <= _vertex_bound(values, prices, relief, u, cm, fm, float(base)):
                                exact = _surface_score(
                                    words[p], (bf, 0, 0), notes, 0, base, 0.0, (combo[cm], ramp[cm], fever[fm]), 0
                                )
                                if exact == score:
                                    if found == out.shape[0]:
                                        return found + 1
                                    row = out[found]
                                    row[0], row[1], row[2], row[3] = u, cm, fm, base
                                    found += 1
                            base += 1
    return found


@jit(nopython=True, cache=True)
def score_ceiling(surfaces, multipliers, notes, ceiling, spare):
    """The most any line under the ceiling can score, base x shape with `spare` body notes moved into fever, and its
    (surface, CM, FM, base)."""
    coeffs, pattern, body_fever = surfaces
    combo, fever = multipliers
    head_len, body_total = notes
    values, prices, relief = ceiling
    best = 0.0
    line = (0, 0, 0, 0.0)
    for u in range(body_fever.shape[0]):
        p = pattern[u]
        bf = int(body_fever[u])
        a = bf + spare + coeffs[p, 3] * 0.01
        e = body_total - bf - spare + coeffs[p, 2] * 0.01
        f = coeffs[p, 1] - coeffs[p, 3] * 0.01
        g = coeffs[p, 0] - coeffs[p, 2] * 0.01
        for cm_block in range(0, MAX_STAT + 1, _TILE):
            cm_top = min(cm_block + _TILE - 1, MAX_STAT)
            alpha_top, beta_top = a * combo[cm_top] + f, e * combo[cm_top] + g
            for fm_block in range(0, MAX_STAT + 1, _TILE):
                fm_top = min(fm_block + _TILE - 1, MAX_STAT)
                shape = alpha_top * fever[fm_top] + beta_top
                if _vertex_bound(values, prices, relief, u, cm_block, fm_block, best / shape) * shape <= best:
                    continue
                for cm in range(cm_block, cm_top + 1):
                    alpha, beta = a * combo[cm] + f, e * combo[cm] + g
                    for fm in range(fm_block, fm_top + 1):
                        shape = alpha * fever[fm] + beta
                        bound = _vertex_bound(values, prices, relief, u, cm, fm, best / shape)
                        if bound * shape > best:
                            best = bound * shape
                            line = (u, cm, fm, bound)
    return best, line


@jit(nopython=True, cache=True)
def band_lines(score, surfaces, multipliers, notes, ceiling, slip, out):
    """Every (surface, CM, FM, lowest base, highest base) whose score can land on this one once a play leaves the surface:
    slip: (body notes that may enter or leave fever, the lowest and highest share of its points a play keeps); into out,
    returning how many there are, or out's rows + 1 where they stop fitting."""
    coeffs, pattern, body_fever = surfaces
    combo, fever = multipliers
    head_len, body_total = notes
    values, prices, relief = ceiling
    spare, keep_low, keep_high = slip
    wanted = float(score) / keep_high
    roof = float(score + head_len + body_total) / keep_low
    found = 0
    for u in range(body_fever.shape[0]):
        p = pattern[u]
        bf = int(body_fever[u])
        a = bf + coeffs[p, 3] * 0.01
        e = body_total - bf + coeffs[p, 2] * 0.01
        f = coeffs[p, 1] - coeffs[p, 3] * 0.01
        g = coeffs[p, 0] - coeffs[p, 2] * 0.01
        for cm_block in range(0, MAX_STAT + 1, _TILE):
            cm_top = min(cm_block + _TILE - 1, MAX_STAT)
            top_combo = combo[cm_top]
            alpha_top, beta_top = (a + spare) * top_combo + f, (e - spare) * top_combo + g
            for fm_block in range(0, MAX_STAT + 1, _TILE):
                fm_top = min(fm_block + _TILE - 1, MAX_STAT)
                shape = alpha_top * fever[fm_top] + beta_top
                if _vertex_bound(values, prices, relief, u, cm_block, fm_block, wanted / shape) * shape < wanted:
                    continue
                for cm in range(cm_block, cm_top + 1):
                    full = combo[cm]
                    alpha, beta = a * full + f, e * full + g
                    for fm in range(fm_block, fm_top + 1):
                        middle = alpha * fever[fm] + beta
                        reach = spare * full * (fever[fm] - 1.0)
                        low = int(np.ceil(wanted / (middle + reach)))
                        limit = _vertex_bound(values, prices, relief, u, cm, fm, float(low))
                        if limit < low:
                            continue
                        high = min(int(limit), int(roof / max(middle - reach, 1.0)))
                        if low <= high:
                            if found == out.shape[0]:
                                return found + 1
                            row = out[found]
                            row[0], row[1], row[2], row[3], row[4] = u, cm, fm, low, high
                            found += 1
    return found


@jit(nopython=True, cache=True)
def line_targets(lines, cell_start, cells, ceiling, power_terms, power, out):
    """Each line (surface, CM, FM, lowest base, highest base) on each of its cells under the vertex bound and, when power
    is not negative, in reach of that Gear Power: into out as rows (surface, CM, FM, FT, FF, lowest, highest, slack in
    points x 1024); returns how many there are. power_terms: 5 x PP - 2 x its points per PP, sorted."""
    values, prices, _relief = ceiling
    found = 0
    for line in range(lines.shape[0]):
        u, cm, fm, lowest, highest = lines[line]
        for k in range(cell_start[u], cell_start[u + 1]):
            ft, ff = cells[k] // (MAX_STAT + 1), cells[k] % (MAX_STAT + 1)
            if power >= 0:
                left = power - 5 * (cm + fm + ft + ff)
                start = np.searchsorted(power_terms, left - 2.0 * highest, side="left")
                if start >= power_terms.shape[0] or power_terms[start] > left - 2.0 * lowest:
                    continue
            bound = 1.0e18
            for j in range(values.shape[0]):
                bound = min(bound, values[j] - prices[j, 1] * cm - prices[j, 2] * fm - prices[j, 3] * ft - prices[j, 4] * ff)
                if bound < lowest:
                    break
            if bound >= lowest:
                if found < out.shape[0]:
                    row = out[found]
                    row[0], row[1], row[2], row[3], row[4], row[5], row[6] = u, cm, fm, ft, ff, lowest, highest
                    row[7] = int((bound - lowest) * 1024.0)
                found += 1
    return found
