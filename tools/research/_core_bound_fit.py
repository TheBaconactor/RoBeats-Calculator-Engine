"""Optional SciPy fitting for the research probe; never the certificate authority.

The LP has six gear maxima, a top-three distinct-Mini support function, and a
single shared-budget gem maximum. It never enumerates their Cartesian product.
"""

import math

import numpy as np
from scipy.optimize import linprog

from tools.research._core_bound_math import fever_coefficients, lookup_domain


def fit_bounds(domain, *, refs, notes, fever_notes, anchor_base, intervals=None, members=9):
    if not math.isfinite(anchor_base) or anchor_base <= 0:
        raise ValueError("positive finite incumbent base value required")
    intervals = domain.intervals if intervals is None else np.asarray(intervals)
    # Variables: five stat weights; three lookup intercepts; six gear maxima;
    # Mini threshold, one positive slack per Mini; gem maximum; two timing intercepts.
    nmini = len(domain.minis)
    tau, slack, gem, timing = 14, 15, 15 + nmini, 16 + nmini
    nvars = 18 + nmini
    objective = np.zeros(nvars)
    objective[:5] = domain.fixed[:5]
    objective[5:14] = 1
    objective[tau] = 3
    objective[slack:gem] = 1
    objective[gem] = domain.budget
    objective[timing:] = 1
    variable_bounds = [(None, None)] * nvars
    # A compact coefficient domain keeps fitting finite even for an empty
    # timing region (whose unconstrained support dual can be unbounded).
    # This restricts only bound quality, never the legal loadout domain.
    variable_bounds[:5] = [(-1.0, 1.0)] * 5
    for i in range(slack, gem + 1):
        variable_bounds[i] = (0, None)
    tables = [refs[name] for name in ("Perfect Points", "Combo Multiplier", "Fever Multiplier")]
    domains = [lookup_domain(intervals[i], t) for i, t in enumerate(tables)]
    normal, fever = fever_coefficients(notes, fever_notes, min(domains[1][1]))
    rows, constant_rhs, lambda_rhs = [], [], []

    def add(entries, constant=0., slope=0.):
        row = np.zeros(nvars)
        for col, coefficient in entries:
            row[col] += coefficient
        rows.append(row)
        constant_rhs.append(constant)
        lambda_rhs.append(slope)

    for x, value in zip(*domains[0]):
        add([(0, -x), (5, -1)], slope=-value)
    for axis, values in ((1, np.log(domains[1][1])),
                         (2, np.log(float(normal) + float(fever) * domains[2][1]))):
        for x, value in zip(domains[axis][0], values):
            add([(axis, -x), (5 + axis, -1)], constant=-value)
    for slot, gear in enumerate(domain.gear):
        for row in gear:
            add([*enumerate(row[:5]), (8 + slot, -1)], slope=-row[5])
    for i, row in enumerate(domain.minis):
        add([*enumerate(row[:5]), (tau, -1), (slack + i, -1)], slope=-row[5])
    for row in domain.gems:
        add([*enumerate(row[:5]), (gem, -1)], slope=-row[5])
    for axis in (3, 4):
        for endpoint in intervals[axis]:
            add([(axis, -endpoint), (timing + axis - 3, -1)])
    matrix = np.array(rows)
    constant_rhs, lambda_rhs = np.array(constant_rhs), np.array(lambda_rhs)
    coefficients = []
    for lam in np.geomspace(0.65 / anchor_base, 1.7 / anchor_base, members):
        fitted = linprog(objective, A_ub=matrix, b_ub=constant_rhs + lam * lambda_rhs, bounds=variable_bounds,
                         method="highs")
        if not fitted.success:
            raise RuntimeError(f"bound coefficient fitting failed: {fitted.message}")
        coefficients.append([lam, *fitted.x[:5]])
    return coefficients
