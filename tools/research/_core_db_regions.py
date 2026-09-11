"""Test the adaptive handoff against every stored Base loadout for one chart.

This is a counterexample audit of bounds and allocation selection, not a search
over unseen loadouts and not an optimality certificate.
"""

import time

import numpy as np

from gear_optimizer.solver.registry_solve_request import RegistrySolveRequest, dispatch_registry_solve
from tools.research._core_adaptive_score import region_queue
from tools.research._core_bound_benchmark import replay_results
from tools.research._core_bound_domain import base_fever_counts, project
from tools.research._core_bound_gems import gem_limits, regional_upper
from tools.research._core_bound_math import log_interval
from tools.research._core_bound_regions import refine_regions
from tools.research._core_bound_search import Candidate, CoreEnumeration
from tools.research._core_region_gpu import solve_regions


def audit_regions(chart, catalog, witnesses, *, issue):
    """witnesses contain (DB row, details, canonical score, reconstructed inputs)."""
    start = time.perf_counter()
    domain = chart.domain
    primary, secondary = (chart.song["metadata"][k] for k in ("Primary Color", "Secondary Color"))
    ids = np.array([w[3][0] for w in witnesses], dtype=np.int32)
    identities = [w[3][1] for w in witnesses]
    gems = np.array([w[3][2] for w in witnesses], dtype=np.int64)
    base = np.array([project(w[3][3], primary, secondary) for w in witnesses], dtype=np.int64)
    final = base + gems @ domain.gems
    scores = np.array([w[2] for w in witnesses], dtype=np.int64)
    thresholds = np.array([log_interval(int(s))[0] for s in scores])
    best = int(scores.max())
    leader = final[int(np.argmax(scores))]
    anchor = leader[5] + chart.refs["Perfect Points"][np.clip(leader[0], 0, 160)]
    broad, regions, counts = refine_regions(domain, refs=chart.refs,
        notes=len(chart.song["song_data"]["timestamps"]), fever_counts=base_fever_counts(chart.timeline),
        anchor_base=anchor, incumbent=best, max_leaves=64)
    fitted_s = time.perf_counter() - start
    for i in np.flatnonzero(broad.bank.values(final).min(axis=1) < thresholds):
        issue("root_bound_below_achieved_score", witnesses[i][0])
    covered = np.zeros(len(witnesses), dtype=bool)
    candidate_bounds = [[] for _ in witnesses]
    inside_checks = 0
    for r, region in enumerate(regions):
        inside = np.all((final[:, 3:5] >= region.intervals[3:5, 0])
                        & (final[:, 3:5] <= region.intervals[3:5, 1]), axis=1)
        covered |= inside
        inside_checks += int(inside.sum())
        upper = regional_upper(base, region, domain.gems, domain.budget)
        low, high, feasible = gem_limits(base, region.intervals, domain.budget)
        admitted = feasible & np.all((gems >= low) & (gems <= high), axis=1)
        affine = region.bank.values(final).min(axis=1)
        for i in np.flatnonzero(inside & (~admitted | (upper < thresholds) | (affine < thresholds))):
            issue("regional_bound_excludes_achieved_allocation", witnesses[i][0], region=r)
        support = domain.budget * np.maximum(0, (domain.gems @ region.bank.weights.T).max(axis=0))
        broad_upper = (region.bank.values(base) + support).min(axis=1)
        for i in np.flatnonzero(broad_upper >= log_interval(best)[0]):
            candidate_bounds[i].append((r, int(broad_upper[i])))
    for i in np.flatnonzero((scores == best) & ~covered):
        issue("best_known_timing_region_excluded", witnesses[i][0])
    core = CoreEnumeration(tuple(Candidate(identity, tuple(bounds))
                                 for identity, bounds in zip(identities, candidate_bounds)),
                           tuple(regions), 0, True)
    queue, queue_counts = region_queue(domain, core, base, best)
    # The full production solve provides a control for the same stored loadouts.
    full = np.asarray(dispatch_registry_solve(RegistrySolveRequest(
        population_indices=ids, item_stats=catalog.arrays["item_stats"],
        slot_start=catalog.arrays["slot_start"], slot_count=catalog.arrays["slot_count"],
        base_fixed_stats=chart.base, timeline_grid=chart.song, ref_arrays=chart.refs,
        flags=chart.ga_kwargs["color_flags"], total_budget=domain.budget)), dtype=np.int64)
    full_scores, _ = replay_results(chart, catalog.arrays, ids, full)
    regional_best = 0
    per_loadout = np.zeros(len(witnesses), dtype=np.int64)
    for offset in range(0, len(queue), 512):
        batch = queue[offset:offset + 512]
        indices = np.array([r[0] for r in batch])
        low, high = np.array([r[3] for r in batch]), np.array([r[4] for r in batch])
        result = solve_regions(chart, catalog.arrays, ids[indices], low, high)
        actual = result[:, 1:7]
        if not np.all((actual >= low) & (actual <= high)):
            raise AssertionError("regional solver returned an allocation outside its timing region")
        replay, _ = replay_results(chart, catalog.arrays, ids[indices], result)
        np.maximum.at(per_loadout, indices, replay)
        regional_best = max(regional_best, max(replay))
    if regional_best < best:
        issue("regional_selection_below_database_best", witnesses[int(np.argmax(scores))][0],
              database=best, regional=regional_best, production_full=max(full_scores))
    if max(full_scores) < best:
        issue("production_selection_below_database_best", witnesses[int(np.argmax(scores))][0],
              database=best, production_full=max(full_scores))
    return {"reference": best, "regional": int(regional_best), "production_full": int(max(full_scores)),
            "stored_loadouts": len(witnesses), "stored_allocations_inside_surviving_regions": inside_checks,
            "regional_rows": len(queue), "fit_s": fitted_s, "total_s": time.perf_counter() - start,
            "regions": counts, "queue": queue_counts,
            "production_per_loadout_deficits": int(np.sum(np.array(full_scores) < scores)),
            "regional_best_loadout_deficits": int(np.sum((scores == best) & (per_loadout < scores)))}
