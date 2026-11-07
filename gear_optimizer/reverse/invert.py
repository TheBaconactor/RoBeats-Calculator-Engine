"""The stat lines whose exact all-Perfect score is a shown score.

For a surface, a line's score is at most base x its bound shape (gem_search._surface_shape, the combo and fever
multipliers bilinear over its notes) and over it by less than one point a note, so a (CM, FM) pair leaves at most a
couple of whole base values, and the loadout ceiling leaves only those a released loadout can reach. Pairs are visited in
TILE x TILE blocks whose best corner bounds them all.

Cost: O(U (B + J b + p)) for U surfaces, B = 400 blocks, J ceiling vertices, b blocks that survive and p pairs in them:
the 161 x 161 (CM, FM) square is walked only where the ceiling can still reach the score, ~0.1% of it near a song's top,
all of it far below. An exact score is one gem_search._surface_score, O(100), for the ~7% of walked pairs that hold a
whole base value.
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.gem_search import _surface_score

_AXIS = MAX_STAT + 1
_TILE = 8


@jit(nopython=True, cache=True)
def _ceiling_at(values, prices, relief, u, cm, fm, floor):
    """The lowest vertex bound on a surface's base value at this CM and FM, or the first under floor."""
    best = 1.0e18
    for j in range(values.shape[0]):
        bound = values[j] - prices[j, 1] * cm - prices[j, 2] * fm + relief[u, j]
        if bound < best:
            best = bound
            if best < floor:
                return best
    return best


@jit(nopython=True, cache=True)
def _shape_terms(coeffs, body_fever, body_total, spare):
    """A surface's bound shape (gem_search._surface_shape) with `spare` body notes moved into fever."""
    n_hn, n_hf, sigma_hn, sigma_hf = coeffs[0], coeffs[1], coeffs[2], coeffs[3]
    ramp_fever, ramp_normal = sigma_hf * 0.01, sigma_hn * 0.01
    return body_fever + spare + ramp_fever, body_total - body_fever - spare + ramp_normal, n_hf - ramp_fever, n_hn - ramp_normal


@jit(nopython=True, cache=True)
def perfect_lines(score, surfaces, multipliers, notes, ceiling, out):
    """Every (surface, CM, FM, base) with exactly this score under the ceiling, into out; returns how many there are, or
    out's rows + 1 where they stop fitting."""
    words, coeffs, pattern, body_fever = surfaces
    combo, ramp, fever = multipliers
    head_len, body_total = notes
    values, prices, relief = ceiling
    wanted = float(score)
    width_per_base = float(head_len + body_total) / wanted
    found = 0
    for u in range(body_fever.shape[0]):
        p = pattern[u]
        bf = int(body_fever[u])
        a, e, f, g = _shape_terms(coeffs[p], bf, body_total, 0.0)
        for cm_block in range(0, _AXIS, _TILE):
            cm_top = min(cm_block + _TILE - 1, MAX_STAT)
            alpha_top, beta_top = a * combo[cm_top] + f, e * combo[cm_top] + g
            for fm_block in range(0, _AXIS, _TILE):
                fm_top = min(fm_block + _TILE - 1, MAX_STAT)
                shape = alpha_top * fever[fm_top] + beta_top
                if _ceiling_at(values, prices, relief, u, cm_block, fm_block, wanted / shape) * shape < wanted:
                    continue
                for cm in range(cm_block, cm_top + 1):
                    alpha, beta = a * combo[cm] + f, e * combo[cm] + g
                    for fm in range(fm_block, fm_top + 1):
                        lowest = wanted / (alpha * fever[fm] + beta)
                        base = int(np.ceil(lowest))
                        while base <= lowest * (1.0 + width_per_base):
                            if base <= _ceiling_at(values, prices, relief, u, cm, fm, float(base)):
                                exact = _surface_score(words[p], (bf, 0, 0), notes, 0, base, 0.0, (combo[cm], ramp[cm], fever[fm]), 0)
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
    _head_len, body_total = notes
    values, prices, relief = ceiling
    best = 0.0
    line = (0, 0, 0, 0.0)
    for u in range(body_fever.shape[0]):
        a, e, f, g = _shape_terms(coeffs[pattern[u]], int(body_fever[u]), body_total, spare)
        for cm_block in range(0, _AXIS, _TILE):
            cm_top = min(cm_block + _TILE - 1, MAX_STAT)
            alpha_top, beta_top = a * combo[cm_top] + f, e * combo[cm_top] + g
            for fm_block in range(0, _AXIS, _TILE):
                fm_top = min(fm_block + _TILE - 1, MAX_STAT)
                shape = alpha_top * fever[fm_top] + beta_top
                if _ceiling_at(values, prices, relief, u, cm_block, fm_block, best / shape) * shape <= best:
                    continue
                for cm in range(cm_block, cm_top + 1):
                    alpha, beta = a * combo[cm] + f, e * combo[cm] + g
                    for fm in range(fm_block, fm_top + 1):
                        shape = alpha * fever[fm] + beta
                        bound = _ceiling_at(values, prices, relief, u, cm, fm, best / shape)
                        if bound * shape > best:
                            best = bound * shape
                            line = (u, cm, fm, bound)
    return best, line


@jit(nopython=True, cache=True)
def line_targets(lines, cell_start, cells, ceiling, power_terms, power, out):
    """Each line (surface, CM, FM, base) on each of its cells under the vertices and, when power is not negative, at that
    Gear Power: into out as rows (surface, CM, FM, FT, FF, base, slack in 1/1024 points); returns how many there are, or
    out's rows + 1 where they stop fitting. power_terms: 5 x PP - 2 x its points per PP, sorted."""
    values, prices, _relief = ceiling
    found = 0
    for line in range(lines.shape[0]):
        u, cm, fm, base = lines[line]
        for k in range(cell_start[u], cell_start[u + 1]):
            ft, ff = cells[k] // _AXIS, cells[k] % _AXIS
            if power >= 0:
                wanted = power - 5.0 * (cm + fm + ft + ff) - 2.0 * base
                at = np.searchsorted(power_terms, wanted)
                if at >= power_terms.shape[0] or power_terms[at] != wanted:
                    continue
            bound = 1.0e18
            for j in range(values.shape[0]):
                bound = min(bound, values[j] - prices[j, 1] * cm - prices[j, 2] * fm - prices[j, 3] * ft - prices[j, 4] * ff)
                if bound < base:
                    break
            if bound >= base:
                if found == out.shape[0]:
                    return found + 1
                row = out[found]
                row[0], row[1], row[2], row[3], row[4], row[5] = u, cm, fm, ft, ff, base
                row[6] = int((bound - base) * 1024.0)
                found += 1
    return found
