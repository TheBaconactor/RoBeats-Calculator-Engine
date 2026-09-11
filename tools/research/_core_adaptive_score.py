"""Batch-level canonical feedback for a Base global-winner research search."""

import time

import numpy as np

from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.solver_common import GEAR_SLOTS
from tools.research._core_bound_benchmark import replay_results
from tools.research._core_bound_gems import gem_limits, regional_upper, timing_pair_count
from tools.research._core_bound_math import log_interval


def core_inputs(chart, core):
    domain = chart.domain
    registry = ItemRegistry(dict(zip(GEAR_SLOTS, domain.gear_items)), list(domain.mini_items), list(GEAR_SLOTS))
    arrays = registry.to_gpu_arrays()
    identities = [c.identity for c in core.candidates]
    ids = np.empty((len(identities), 9), dtype=np.int32)
    for i, row in enumerate(identities):
        for slot in range(9):
            items = domain.gear_items[slot] if slot < 6 else domain.mini_items
            ids[i, slot] = registry.item_to_id[(min(slot, 6), items[row[slot]]["Name"])]
    raw = chart.base + arrays["item_stats"][ids].sum(axis=1)
    base = np.array([domain.fixed + sum(domain.gear[s][row[s]] for s in range(6))
                     + domain.minis[list(row[6:])].sum(axis=0) for row in identities], dtype=np.int64).reshape(-1, 6)
    return registry, arrays, ids, raw, base


def region_queue(domain, core, base, incumbent):
    """Tighten proved survivors; unvisited regions remain pending, not excluded.

    A partial search may evaluate known live work without expanding every
    unvisited region. Its pending-region ledger and incomplete coverage travel
    with the result; exhausting this queue does not mean exhausting the search.
    """
    by_region = [[] for _ in core.regions]
    for i, candidate in enumerate(core.candidates):
        for r, upper in candidate.region_bounds:
            by_region[r].append((i, upper))
    threshold = log_interval(int(incumbent))[0]
    rows = []
    broad_pairs, survivors = 0, 0
    for r, candidates in enumerate(by_region):
        if not candidates:
            continue
        indices, upper = np.asarray(candidates, dtype=np.int64).T
        region = core.regions[r]
        low, high, feasible = gem_limits(base[indices], region.intervals, domain.budget)
        upper = np.minimum(upper, regional_upper(base[indices], region, domain.gems, domain.budget))
        broad_pairs += sum(timing_pair_count(l, h, domain.budget) for l, h, ok in zip(low, high, feasible) if ok)
        for i, u, l, h in zip(indices[feasible], upper[feasible], low[feasible], high[feasible]):
            if u >= threshold:
                survivors += 1
                rows.append((int(i), r, int(u), l, h))
    return rows, {"broad_region_pairs": sum(map(len, by_region)), "surviving_region_pairs": survivors,
                  "broad_surviving_timing_pairs": broad_pairs,
                  "unvisited_regions": list(core.unresolved_regions)}


def priority_estimates(chart, base, seed):
    """Cheap estimate at a repaired seed allocation; used for ordering ONLY."""
    low, high, _ = gem_limits(base, chart.domain.intervals, chart.domain.budget)
    gems = np.minimum(np.array(seed["gems"]), high)
    gems[:, 5] += chart.domain.budget - gems.sum(axis=1)
    stats = base + gems @ chart.domain.gems
    pp, cm, fm = [np.asarray(chart.refs[name])[np.clip(stats[:, i], 0, len(chart.refs[name]) - 1)]
                  for i, name in enumerate(("Perfect Points", "Combo Multiplier", "Fever Multiplier"))]
    return (stats[:, 5] + pp) * cm * fm


def score_adaptive(chart, core, *, incumbent, batch_size=512,
                   deadline=None, on_improvement=None):
    from tools.research._core_region_gpu import solve_regions
    start = time.perf_counter()
    best = dict(incumbent)
    registry, arrays, ids, raw, base = core_inputs(chart, core)
    # Seed IDs belong to the reduced GA registry; all returned adaptive IDs use
    # the full catalog, regardless of which stage found the winning score.
    best["ids"] = [registry.item_to_id[(min(slot, 6), chart.registry.id_to_item[item_id]["Name"])]
                   for slot, item_id in enumerate(incumbent["ids"])]
    queue, counts = region_queue(chart.domain, core, base, best["score"])
    estimate = priority_estimates(chart, base, incumbent)
    queue.sort(key=lambda row: (-estimate[row[0]], -row[2], row[0], row[1]))
    # Measure complete Base inputs with P and S separate, before building a cache.
    p, s = (chart.song["metadata"][k] for k in ("Primary Color", "Secondary Color"))
    color_indices = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
    signatures = raw[:, [0, 1, 2, 3, 4, color_indices[p], color_indices[s]]]
    counts.update(candidates=len(ids), distinct_base_inputs=len(np.unique(signatures, axis=0)),
                  distinct_regional_inputs=len({(tuple(signatures[i]), r) for i, r, *_ in queue}))
    full_low, full_high, _ = gem_limits(base, chart.domain.intervals, chart.domain.budget)
    counts["full_loadout_timing_pairs"] = sum(timing_pair_count(l, h, chart.domain.budget)
                                            for l, h in zip(full_low, full_high))
    scored, pairs, feedback_pruned = 0, 0, 0
    solve_seconds, replay_seconds = 0., 0.
    cursor = 0
    while cursor < len(queue) and (deadline is None or time.perf_counter() < deadline):
        threshold = log_interval(int(best["score"]))[0]
        batch = []
        while cursor < len(queue) and len(batch) < batch_size:
            row = queue[cursor]
            cursor += 1
            if row[2] < threshold:
                feedback_pruned += 1
            else:
                batch.append(row)
        if not batch:
            continue
        indices = np.array([r[0] for r in batch])
        lows, highs = np.array([r[3] for r in batch]), np.array([r[4] for r in batch])
        t = time.perf_counter()
        result = solve_regions(chart, arrays, ids[indices], lows, highs)
        solve_seconds += time.perf_counter() - t
        t = time.perf_counter()
        scores, stats = replay_results(chart, arrays, ids[indices], result)
        scores = np.asarray(scores, dtype=np.int64)
        winner = int(np.argmax(scores))
        if scores[winner] > best["score"]:
            best = {"score": int(scores[winner]), "stats": stats[winner],
                    "ids": ids[indices[winner]].tolist(), "gems": result[winner, 1:].tolist(),
                    "catalog_indices": core.candidates[indices[winner]].identity}
            if on_improvement:
                on_improvement(best["score"])
        replay_seconds += time.perf_counter() - t
        pairs += sum(timing_pair_count(l, h, chart.domain.budget) for l, h in zip(lows, highs))
        scored += len(batch)
    best["loadout"] = [registry.id_to_item[item_id]["Name"] for item_id in best["ids"]]
    return {"best": best, "scored_regions": scored, "timing_pairs_evaluated": pairs,
            "feedback_pruned_regions": feedback_pruned,
            "queue_exhausted": cursor == len(queue), "enumeration_complete": core.complete,
            "unresolved_queue_rows": len(queue) - cursor, "optimality_certified": False,
            "solve_s": solve_seconds, "replay_s": replay_seconds, "total_s": time.perf_counter() - start, **counts}
