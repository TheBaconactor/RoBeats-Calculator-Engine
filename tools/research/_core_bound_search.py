"""Lazy family enumeration after regional proofs, with explicit work limits."""

from dataclasses import dataclass

import numpy as np

from tools.research._core_bound_math import log_interval


@dataclass(frozen=True)
class CoreEnumeration:
    witnesses: frozenset
    nodes: int
    complete: bool


def enumerate_core(domain, regions, *, incumbent, max_nodes=1_000_000, max_witnesses=100_000):
    """Enumerate only unresolved 6-gear/distinct-3-Mini witnesses.

    A witness can occur in multiple timing regions; dedupe its identity before
    an inner solve. Work limits leave ``complete=False``; they never certify.
    """
    if max_nodes < 1 or max_witnesses < 1:
        raise ValueError("positive enumeration limits required")
    threshold = log_interval(int(incumbent))[0]
    witnesses, nodes = set(), 0
    for region in regions:
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
                return CoreEnumeration(frozenset(witnesses), nodes, False)
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
                for offset in np.flatnonzero(upper.min(axis=1) >= threshold):
                    choice = start + int(offset)
                    stack.append((gear_ids, mini_ids + (int(order[choice]),), choice + 1, values[offset]))
            else:
                witnesses.add(gear_ids + tuple(sorted(mini_ids)))
                if len(witnesses) >= max_witnesses:
                    return CoreEnumeration(frozenset(witnesses), nodes, False)
    return CoreEnumeration(frozenset(witnesses), nodes, True)
