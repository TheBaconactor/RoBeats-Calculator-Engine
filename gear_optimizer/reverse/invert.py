"""The stat lines whose exact all-Perfect score is a shown score.

For a surface, a line's score is at most base x its bound shape (gem_search._surface_shape, the combo and fever
multipliers bilinear over its notes) and over it by less than one point a note, so a (CM, FM) pair leaves at most a
couple of whole base values, and the loadout ceiling leaves only those a released loadout can reach. Pairs are visited in
TILE x TILE blocks whose best corner bounds them all.

Cost: O(u (B + J b + p)) for the u of U surfaces whose top reaches the score, B = 400 blocks, J ceiling vertices, b blocks
that survive and p pairs in them: the 161 x 161 (CM, FM) square is walked only where the ceiling can still reach the
score, ~0.1% of it near a song's top, all of it far below. A base is first tested at O(1) on the body's exact value, then
summed over the head, O(100), for ~head / notes of the ~7% of walked pairs that hold a whole base value.
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
def _shows_power(cm, fm, cell, base, power_query):
    """Whether some Perfect Points stat gives this line the Gear Power, if one is known."""
    power_terms, power = power_query
    if power < 0:
        return True
    wanted = power - 5.0 * (cm + fm + cell // _AXIS + cell % _AXIS) - 2.0 * base
    at = np.searchsorted(power_terms, wanted)
    return at < power_terms.shape[0] and power_terms[at] == wanted


@jit(nopython=True, cache=True)
def _any_shows_power(cm, fm, cells, base, power_query):
    for k in range(cells.shape[0]):
        if _shows_power(cm, fm, cells[k], base, power_query):
            return True
    return False


@jit(nopython=True, cache=True)
def _write_cells(line, cells, ceiling, power_query, out, found):
    """A line (surface, CM, FM, base) on these cells of its surface, under the vertices and at the Gear Power: rows into
    out from `found` on; returns the new count, or out's rows + 1 where they stop fitting."""
    u, cm, fm, base = line
    values, prices = ceiling
    for k in range(cells.shape[0]):
        ft, ff = cells[k] // _AXIS, cells[k] % _AXIS
        if not _shows_power(cm, fm, cells[k], base, power_query):
            continue
        bound = 1.0e18
        vertex = 0
        for j in range(values.shape[0]):
            value = values[j] - prices[j, 1] * cm - prices[j, 2] * fm - prices[j, 3] * ft - prices[j, 4] * ff
            if value < bound:
                bound, vertex = value, j
                if bound < base:
                    break
        if bound >= base:
            if found == out.shape[0]:
                return found + 1
            row = out[found]
            row[0], row[1], row[2], row[3], row[4], row[5], row[6] = u, cm, fm, ft, ff, base, vertex
            row[7] = int((bound - base) * 1024.0)
            found += 1
    return found


@jit(nopython=True, cache=True)
def perfect_targets(score, surfaces, multipliers, notes, ceiling, power_query, pairs, out):
    """Every stat line with exactly this score under the ceiling and, a Gear Power given, at it, into out as rows (surface,
    CM, FM, FT, FF, base, lowest vertex, slack in 1/1024 points), until out is full or `pairs` (CM, FM) pairs are walked;
    returns how many rows, and whether every line is among them.
    surfaces: (words, coeffs, pattern, body fever, cell_start, cells, the surfaces to walk). power_query: 5 x PP - 2 x its
    points per PP, sorted; and the Gear Power, negative when unknown. What a base leaves of the score past the body's
    exact value must fit the head's floors before the head is summed."""
    words, coeffs, pattern, body_fever, cell_start, cells, order = surfaces
    combo, ramp, fever = multipliers
    head_len, body_total = notes
    values, prices, relief = ceiling
    wanted = float(score)
    width_per_base = float(head_len + body_total) / wanted
    found = walked = 0
    for u in order:
        if walked > pairs:
            return found, False
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
                walked += (cm_top + 1 - cm_block) * (fm_top + 1 - fm_block)
                for cm in range(cm_block, cm_top + 1):
                    alpha, beta = a * combo[cm] + f, e * combo[cm] + g
                    for fm in range(fm_block, fm_top + 1):
                        shape = alpha * fever[fm] + beta
                        lowest = wanted / shape
                        base = int(np.ceil(lowest))
                        head_shape = shape - (bf * fever[fm] + body_total - bf) * combo[cm]
                        while base <= lowest * (1.0 + width_per_base):
                            normal = float(base) * combo[cm]
                            left = wanted - bf * np.floor(normal * fever[fm]) - (body_total - bf) * np.floor(normal)
                            head = base * head_shape
                            if head - head_len - 1.0 <= left <= head + 1.0 and base <= _ceiling_at(values, prices, relief, u, cm, fm, float(base)):
                                on_cells = cells[cell_start[u] : cell_start[u + 1]]
                                if _any_shows_power(cm, fm, on_cells, base, power_query):
                                    exact = _surface_score(words[p], (bf, 0, 0), notes, 0, base, 0.0, (combo[cm], ramp[cm], fever[fm]), 0)
                                    if exact == score:
                                        found = _write_cells((u, cm, fm, base), on_cells, (values, prices), power_query, out, found)
                                        if found > out.shape[0]:
                                            return out.shape[0], False
                            base += 1
    return found, True


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


@jit(nopython=True, cache=True)
def surface_tops(surfaces, multipliers, notes, ceiling, floor):
    """The most each surface's lines under the ceiling can score, or `floor` if that is more: no score past a surface's
    top lies on it, and only scores near the song's top have surfaces to skip."""
    coeffs, pattern, body_fever = surfaces
    combo, fever = multipliers
    tops = np.empty(body_fever.shape[0])
    for u in range(tops.shape[0]):
        terms = _shape_terms(coeffs[pattern[u]], int(body_fever[u]), notes[1], 0.0)
        tops[u] = _surface_best(u, terms, combo, fever, ceiling, floor, np.inf)[0]
    return tops
