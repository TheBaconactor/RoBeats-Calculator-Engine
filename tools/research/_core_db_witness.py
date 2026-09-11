"""Decode stored witnesses strictly and reconstruct their actual scoring inputs."""

from itertools import product
import json

import numpy as np

from gear_optimizer.core.gem_defs import BASE_STAT_KEYS, GEM_KEYS, STAT_KEYS
from gear_optimizer.data.database_codecs import _decode_uvarints, _unpack_stats_after_load
from gear_optimizer.solver.base_stats import build_stats_dict
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.solver_common import GEAR_SLOTS


def decode_details(text):
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("details must be an object")
    # Check packed shapes before the production reader can supply default values.
    if "st" in raw and (len(raw["st"]) != len(STAT_KEYS)
                        or any(type(v) is not int for v in raw["st"])):
        raise ValueError("invalid packed stat row")
    if "gc" in raw and (len(raw["gc"]) != len(GEM_KEYS)
                        or any(type(v) is not int for v in raw["gc"])):
        raise ValueError("invalid packed gem row")
    details = _unpack_stats_after_load(raw)
    stats = details["Stats"]
    if any(type(stats[k]) is not int for k in BASE_STAT_KEYS):
        raise ValueError("all ten visible stats must be integers")
    return details


def allocation(details):
    gems = [details["FT"], details["FF"], *(details["GemCounts"][k] for k in GEM_KEYS)]
    if any(type(v) is not int or v < 0 for v in gems) or sum(gems) != 90:
        raise ValueError("stored allocation violates the 90-gem budget")
    return gems


class WitnessCatalog:
    def __init__(self, chart, gear_names, mini_names):
        self.chart, self.gear_names, self.mini_names = chart, gear_names, mini_names
        domain = chart.domain
        self.registry = ItemRegistry(dict(zip(GEAR_SLOTS, domain.gear_items)),
                                     list(domain.mini_items), list(GEAR_SLOTS))
        self.arrays = self.registry.to_gpu_arrays()
        self.gear_slot = {item["Name"]: slot for slot, rows in enumerate(domain.gear_items) for item in rows}
        self.identity = [{item["Name"]: i for i, item in enumerate(rows)}
                         for rows in (*domain.gear_items, domain.mini_items)]

    def reconstruct(self, row, details):
        primary, secondary = (self.chart.song["metadata"][k] for k in ("Primary Color", "Secondary Color"))
        selected = details["SelectedElement"] if "SelectedElement" in details else details["Selected Element"]
        if selected != primary:
            raise ValueError("stored selected element differs from Base core's primary element")
        if row["team_buff"] != "T5":
            raise ValueError("this catalog is the T5 domain")
        names = [self.gear_names[i] for i in _decode_uvarints(row["gear_ids_blob"])]
        slots = [self.gear_slot[n] for n in names]
        if sorted(slots) != list(range(6)):
            raise ValueError("stored gear must contain each slot exactly once")
        names = [name for _, name in sorted(zip(slots, names))]
        values = _decode_uvarints(row["minis_ids_blob"])
        if not values or values[-1] != 0:
            raise ValueError("Mini groups must end with a separator")
        groups, group = [], []
        for value in values:
            if value:
                group.append(self.mini_names[value])
            else:
                if not group:
                    raise ValueError("empty Mini group")
                groups.append(group)
                group = []
        if len(groups) != 3:
            raise ValueError("three Mini groups required")
        gems = allocation(details)
        relevant = list(BASE_STAT_KEYS[:5]) + list(dict.fromkeys((primary, secondary)))
        target = details["Stats"]
        for minis in product(*groups):
            if len(set(minis)) != 3:
                continue
            ids = [self.registry.item_to_id[(min(slot, 6), name)] for slot, name in enumerate([*names, *minis])]
            base = build_stats_dict(self.chart.base + self.arrays["item_stats"][ids].sum(axis=0))
            rebuilt = apply_gems_to_base_stats(base, selected, *gems)
            if all(rebuilt[k] == target[k] for k in relevant):
                identity = tuple(self.identity[min(slot, 6)][name] for slot, name in enumerate([*names, *minis]))
                identity = identity[:6] + tuple(sorted(identity[6:]))
                return np.array(ids, dtype=np.int32), identity, gems, base
        raise ValueError("stored scoring stats cannot be reconstructed from any distinct Mini representatives")
