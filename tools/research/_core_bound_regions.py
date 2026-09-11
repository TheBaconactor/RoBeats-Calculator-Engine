"""Bounded timing-region refinement for the go/no-go probe, not a solver."""

from dataclasses import dataclass
import heapq

import numpy as np

from tools.research._core_bound_fit import fit_bounds
from tools.research._core_bound_math import certify_bounds, family_terms, log_interval


@dataclass(frozen=True)
class Region:
    intervals: np.ndarray
    fever_notes: int
    bank: object
    root: np.ndarray
    losses: list


def refine_regions(domain, *, refs, notes, fever_counts, anchor_base, incumbent, max_leaves=64, members=9):
    """Split the unresolved region with the highest bound, covering raw cap tails.

    All leaves together cover the original timing domain. A limit only stops
    refinement; it never turns an unresolved region into an optimality claim.
    """
    if members < 1:
        raise ValueError("positive member count required")
    if max_leaves < 1:
        raise ValueError("max_leaves must be positive")
    threshold = log_interval(int(incumbent))[0]
    queue, terminal = [], []
    built, excluded = 0, 0

    def build(intervals):
        nonlocal built, excluded
        ft, ff = np.clip(intervals[3:5], 0, np.array(fever_counts.shape)[:, None] - 1)
        fever = int(fever_counts[ft[0]:ft[1] + 1, ff[0]:ff[1] + 1].max())
        coefficients = fit_bounds(domain, refs=refs, notes=notes, fever_notes=fever,
                                  anchor_base=anchor_base, intervals=intervals, members=members)
        bank = certify_bounds(coefficients, intervals=intervals, refs=refs, notes=notes, fever_notes=fever)
        root, losses = family_terms(bank, fixed=domain.fixed, gear=domain.gear, minis=domain.minis,
                                   gems=domain.gems, budget=domain.budget)
        built += 1
        region = Region(intervals, fever, bank, root, losses)
        upper = int(root.min())
        if upper < threshold:
            excluded += 1
        else:
            heapq.heappush(queue, (-upper, built, region))
        return region

    broad = build(domain.intervals.copy())
    while queue and built < 2 * max_leaves - 1:
        _, _, region = heapq.heappop(queue)
        clipped = np.clip(region.intervals[3:5], 0, np.array(fever_counts.shape)[:, None] - 1)
        widths = clipped[:, 1] - clipped[:, 0]
        if not np.any(widths):
            terminal.append(region)
            continue
        axis = 3 + int(np.argmax(widths))
        split = int(clipped[axis - 3].sum() // 2)
        left, right = region.intervals.copy(), region.intervals.copy()
        left[axis, 1], right[axis, 0] = split, split + 1
        build(left)
        build(right)
    leaves = terminal + [entry[2] for entry in queue]
    return broad, leaves, {"regions_built": built, "regions_excluded": excluded,
                           "lps": built * members,
                           "unresolved_regions": len(leaves), "certified": not leaves}
