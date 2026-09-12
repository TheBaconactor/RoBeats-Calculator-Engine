"""Lazy family enumeration after regional proofs, with explicit work limits."""

from dataclasses import dataclass

import numpy as np

from tools.research._core_bound_math import log_interval


@dataclass(frozen=True)
class Candidate:
    identity: tuple
    # (index into CoreEnumeration.regions, validated upper log)
    region_bounds: tuple


@dataclass(frozen=True)
class CoreEnumeration:
    candidates: tuple
    regions: tuple
    nodes: int
    complete: bool
    unresolved_regions: tuple = ()

    @property
    def witnesses(self):
        return frozenset(c.identity for c in self.candidates)


def enumerate_core(domain, regions, *, incumbent, max_nodes=1_000_000, max_witnesses=100_000):
    """Enumerate only unresolved 6-gear/distinct-3-Mini witnesses.

    A witness can occur in multiple timing regions; retain their separate bounds
    under one identity. Work limits leave ``complete=False``; they never certify.
    """
    if max_nodes < 1 or max_witnesses < 1:
        raise ValueError("positive enumeration limits required")
    threshold = log_interval(int(incumbent))[0]
    witnesses, nodes = {}, 0
    regions = tuple(regions)

    def finish(complete, unresolved=()):
        return CoreEnumeration(tuple(Candidate(k, tuple(v.items())) for k, v in witnesses.items()),
                               regions, nodes, complete, unresolved)

    for region_id, region in enumerate(regions):
        bank = region.bank
        # Visit high-support items first; ordering only, never a candidate quota.
        gear_values = [g @ bank.weights.T for g in domain.gear]
        suffix = np.zeros((7, len(bank.intercepts)), dtype=np.int64)
        for slot in range(5, -1, -1):
            suffix[slot] = suffix[slot + 1] + gear_values[slot].max(axis=0)
        mini_values = domain.minis @ bank.weights.T
        order = np.argsort(-mini_values[:, int(np.argmin(region.root))], kind="stable")
        mini_values = mini_values[order]
        # Top-r DISTINCT contributions in each remaining suffix, per bound.
        mini_suffix = np.zeros((len(mini_values) + 1, 4, len(bank.intercepts)), dtype=np.int64)
        top = np.empty((0, len(bank.intercepts)), dtype=np.int64)
        for start in range(len(mini_values) - 1, -1, -1):
            top = np.sort(np.vstack([top, mini_values[start]]), axis=0)[-3:]
            for k in range(1, len(top) + 1):
                mini_suffix[start, k] = top[-k:].sum(axis=0)
        gem_support = domain.budget * np.maximum(0, (domain.gems @ bank.weights.T).max(axis=0))
        constant = bank.intercepts + domain.fixed @ bank.weights.T + gem_support
        stack = [((), (), 0, constant)]
        while stack:
            if nodes >= max_nodes:
                return finish(False, tuple(range(region_id, len(regions))))
            gear_ids, mini_ids, start, value = stack.pop()
            nodes += 1
            if len(gear_ids) < 6:
                slot = len(gear_ids)
                values = value + gear_values[slot]
                upper = values + suffix[slot + 1] + mini_suffix[0, 3]
                for choice in np.flatnonzero(upper.min(axis=1) >= threshold):
                    stack.append((gear_ids + (int(choice),), (), 0, values[choice]))
            elif len(mini_ids) < 3:
                remaining = 3 - len(mini_ids)
                stop = len(mini_values) - remaining + 1
                if start >= stop:
                    continue
                values = value + mini_values[start:stop]
                upper = values + mini_suffix[start + 1:stop + 1, remaining - 1]
                # Push lower-priority children first so LIFO visits the stable
                # descending-support Mini order, including under work limits.
                for offset in reversed(np.flatnonzero(upper.min(axis=1) >= threshold)):
                    choice = start + int(offset)
                    stack.append((gear_ids, mini_ids + (int(order[choice]),), choice + 1, values[offset]))
            else:
                identity = gear_ids + tuple(sorted(mini_ids))
                upper = int(value.min())
                if upper < threshold:
                    continue
                witnesses.setdefault(identity, {})[region_id] = upper
                if len(witnesses) >= max_witnesses:
                    return finish(False, tuple(range(region_id, len(regions))))
    return finish(True)
