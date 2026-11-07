"""What the stat lines under the ceiling can score: a song's top.

For a surface, a line's score is at most base x its bound shape (the combo and fever multipliers bilinear over its notes) and
over it by less than one point a note. Pairs are visited in TILE x TILE blocks whose best corner bounds them all.

Cost: O(U (B + J b + p)) for U surfaces, B = 400 blocks, J ceiling vertices, b blocks that survive and p pairs in them.
"""

from __future__ import annotations


from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import MAX_STAT

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
def _surface_best(u, shape_terms, combo, fever, ceiling, best, enough):
    """The most surface u's lines under the ceiling score past `best`, base x shape: (score, CM, FM, base), CM -1 when none
    does; the first past `enough` ends the search."""
    a, e, f, g = shape_terms
    values, prices, relief = ceiling
    line = (-1, 0, 0.0)
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
                        line = (cm, fm, bound)
                        if best >= enough:
                            return best, line
    return best, line


@jit(nopython=True, cache=True)
def score_ceiling(surfaces, multipliers, notes, ceiling, spare, enough):
    """The most any line under the ceiling can score, base x shape with `spare` body notes moved into fever, and its
    (surface, CM, FM, base); the first line past `enough` ends the search."""
    coeffs, pattern, body_fever = surfaces
    combo, fever = multipliers
    best = 0.0
    line = (0, 0, 0, 0.0)
    for u in range(body_fever.shape[0]):
        terms = _shape_terms(coeffs[pattern[u]], int(body_fever[u]), notes[1], spare)
        best, (cm, fm, base) = _surface_best(u, terms, combo, fever, ceiling, best, enough)
        if cm >= 0:
            line = (u, cm, fm, base)
            if best >= enough:
                break
    return best, line
