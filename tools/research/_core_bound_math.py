"""Integer log-affine certificates for the outer-search research probe.

Fitting is deliberately separate: any finite coefficients are valid after the
lookup intercepts have been checked here. No floating log/exp decides a prune.
Coordinates are raw additive (PP, CM, FM, FT, FF, 2*primary + secondary).
"""

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import math

import numpy as np

SCALE = 1 << 36


def _log_enclosures(x):
    """Successive rational enclosures of log(x), 1 <= x <= 2."""
    z = (x - 1) / (x + 1)
    square = z * z
    power = z
    lower = Fraction(0)
    for k in range(32):
        lower += 2 * power / (2 * k + 1)
        power *= square
        yield lower, lower + 2 * power / ((2 * k + 3) * (1 - square))


_LOG_TWO = tuple(_log_enclosures(Fraction(2)))[-1]


@lru_cache(maxsize=4096)
def log_interval(value):
    """Return integers lo, hi with lo/SCALE <= log(value) <= hi/SCALE."""
    value = Fraction(value)
    if value <= 0:
        raise ValueError("log certificate requires a positive value")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    mantissa = value / Fraction(2) ** exponent
    if mantissa < 1:
        exponent -= 1
        mantissa *= 2
    lo2, hi2 = _LOG_TWO
    shift_lo = exponent * (lo2 if exponent >= 0 else hi2)
    shift_hi = exponent * (hi2 if exponent >= 0 else lo2)
    for lower, upper in _log_enclosures(mantissa):
        lo = math.floor((lower + shift_lo) * SCALE)
        hi = math.ceil((upper + shift_hi) * SCALE)
        # The remaining positive series tail is already enclosed. Once these
        # outward integers are adjacent, more terms cannot tighten this bound.
        if hi - lo <= 1:
            break
    return lo, hi


def lookup_domain(interval, table):
    """Include both raw tails; only the lookup, never a partial sum, is capped."""
    lo, hi = map(int, interval)
    if lo > hi:
        raise ValueError("empty raw stat interval")
    x = np.unique([lo, *range(max(0, lo), min(len(table) - 1, hi) + 1), hi])
    return x, np.asarray(table, dtype=np.float64)[np.clip(x, 0, len(table) - 1)]


def fever_coefficients(notes, fever_notes, minimum_combo):
    """Head-aware upper counts after factoring out CM.

    Fever is optimistically assigned to the latest (largest combo ramp) notes.
    Substituting a lower bound on CM in the remaining 1/CM terms is optimistic.
    """
    head = min(100, notes)
    body = notes - head
    ramp = body + Fraction(head * (head + 1), 200)
    fever_head = max(0, fever_notes - body)
    fever_ramp = min(fever_notes, body) + Fraction(fever_head * (2 * head - fever_head + 1), 200)
    deficit = fever_notes - fever_ramp
    minimum_combo = Fraction(float(minimum_combo))
    return ((notes - ramp - deficit) / minimum_combo + ramp - fever_ramp,
            fever_ramp + deficit / minimum_combo)


@dataclass(frozen=True)
class BoundBank:
    weights: np.ndarray
    intercepts: np.ndarray

    def values(self, stats):
        """Upper logs for each row and each bound; integer arithmetic throughout."""
        stats = np.asarray(stats)
        if stats.ndim != 2 or not len(stats) or stats.dtype.kind not in "iu" or stats.shape[-1] != 6:
            raise ValueError("bounds require six raw integer coordinates")
        # Prevent overflow before entering the vectorized exact-integer path.
        worst = max(sum(abs(int(w)) * int(v) for w, v in zip(row, np.max(np.abs(stats), axis=0)))
                    + abs(int(k)) for row, k in zip(self.weights, self.intercepts))
        if worst >= 2**63:
            raise OverflowError("bound evaluation exceeds int64")
        return stats @ self.weights.T + self.intercepts


def certify_bounds(coefficients, *, intervals, refs, notes, fever_notes):
    """Validate a bank fitted as (lambda, wPP, wCM, wFM, wFT, wFF).

    The caller owns the fever-count coverage proof. With F=N it covers Base and
    FG without any timing assumptions. A Base frontier's F must not certify FG.
    A 32-operation float32 error allowance also covers the shorter f64 canonical
    score expressions (including conversion of reference values). Scores must
    be nonnegative, finite, normal, and fit the scorer's integer accumulator.
    """
    if not 0 <= fever_notes <= notes or notes <= 0:
        raise ValueError("invalid scoring-note/fever-note counts")
    tables = [np.asarray(refs[name], dtype=np.float64) for name in
              ("Perfect Points", "Combo Multiplier", "Fever Multiplier")]
    if any(t.ndim != 1 or not len(t) or not np.all(np.isfinite(t)) for t in tables):
        raise ValueError("finite nonempty lookup tables are required")
    if np.min(tables[0]) <= 0 or min(np.min(tables[1]), np.min(tables[2])) < 1:
        raise ValueError("positive PP and multipliers >= 1 are required")
    if intervals[5][0] < 0:
        raise ValueError("the full-combo relaxation requires nonnegative elemental score")
    # Scope the numerical proof to the production scorer's normal, non-overflow
    # domain. A different arithmetic domain requires a new error analysis.
    maximum_score = (notes * (Fraction(int(intervals[5][1])) + Fraction(float(tables[0].max())))
                     * Fraction(float(tables[1].max())) * Fraction(float(tables[2].max())))
    if (tables[0].min() < 2**-20 or intervals[5][1] >= 2**24
            or maximum_score / (1 - Fraction(32, 2**24)) >= 2**31):
        raise ValueError("score domain exceeds the float32/int32 numerical certificate")
    domains = [lookup_domain(intervals[i], t) for i, t in enumerate(tables)]
    cm_logs = [log_interval(float(v))[1] for v in domains[1][1]]
    normal, fever = fever_coefficients(notes, fever_notes, min(domains[1][1]))
    fm_logs = [log_interval(normal + fever * Fraction(float(v)))[1]
               for v in domains[2][1]]
    # gamma_32: a conservative relative allowance for all pre-floor FP operations.
    numerical_allowance = log_interval(Fraction(1, 1) / (1 - Fraction(32, 2**24)))[1]
    weights, intercepts = [], []
    for coefficients_row in coefficients:
        if len(coefficients_row) != 6 or not np.all(np.isfinite(coefficients_row)):
            raise ValueError("six finite fitting coefficients are required")
        lam, pp, cm, fm, ft, ff = [round(float(v) * SCALE) for v in coefficients_row]
        if lam <= 0:
            raise ValueError("lambda must remain positive after quantization")
        # lambda*B - log(lambda) - 1 >= log(B). PP is another finite lookup envelope.
        k = -log_interval(Fraction(lam, SCALE))[0] - SCALE + numerical_allowance
        k += max(math.ceil(lam * Fraction(float(v))) - pp * int(x)
                 for x, v in zip(*domains[0]))
        k += max(v - cm * int(x) for x, v in zip(domains[1][0], cm_logs))
        k += max(v - fm * int(x) for x, v in zip(domains[2][0], fm_logs))
        # w*z - min(w*l, w*h) is nonnegative on the timing region.
        k -= min(ft * int(x) for x in intervals[3])
        k -= min(ff * int(x) for x in intervals[4])
        row = [pp, cm, fm, ft, ff, lam]
        worst = abs(k) + sum(abs(w) * max(abs(int(a)), abs(int(b)))
                             for w, (a, b) in zip(row, intervals))
        if worst >= 2**63:
            raise OverflowError("certificate exceeds int64")
        weights.append(row)
        intercepts.append(k)
    if not weights:
        raise ValueError("at least one bound is required")
    return BoundBank(np.array(weights, dtype=np.int64), np.array(intercepts, dtype=np.int64))


def family_terms(bank, *, fixed, gear, minis, gems, budget):
    """Six independent slots, three DISTINCT Minis, and ONE shared gem budget."""
    if budget < 0 or len(gear) != 6 or len(minis) < 3 or any(not len(g) for g in gear):
        raise ValueError("expected six nonempty gear slots, >=3 Minis, and a nonnegative budget")
    gear_values = [g @ bank.weights.T for g in gear]
    mini_values = minis @ bank.weights.T
    gem_values = gems @ bank.weights.T
    gem_support = budget * np.maximum(0, gem_values.max(axis=0))
    root = (bank.intercepts + fixed @ bank.weights.T + gem_support
            + sum(v.max(axis=0) for v in gear_values)
            + np.sort(mini_values, axis=0)[-3:].sum(axis=0))
    losses = [v.max(axis=0) - v for v in gear_values]
    return root, losses


def prefix_census(root, losses, *, incumbent, depth=3):
    """Count unresolved gear prefixes exactly, without constructing stat frontiers.

    Every prefix includes the support of all three distinct Minis and all gems.
    Equality is retained so this filter does not discard tied witnesses.
    """
    if incumbent <= 0 or not 0 <= depth <= len(losses):
        raise ValueError("positive incumbent and valid prefix depth required")
    threshold = log_interval(int(incumbent))[0]
    states = root.reshape(1, -1)
    rows = []
    for slot in range(depth):
        children = states[:, None, :] - losses[slot][None, :, :]
        children = children.reshape(-1, len(root))
        states = children[np.min(children, axis=1) >= threshold]
        rows.append({"depth": slot + 1, "visited": len(children), "surviving": len(states)})
    return rows
