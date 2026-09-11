"""Real GPU regional coverage and canonical feedback integration."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from tools.research._core_bound_gems import gem_limits
from tools.research._core_bound_math import BoundBank, log_interval
from tools.research._core_bound_search import Candidate, CoreEnumeration


@pytest.mark.gpu
def test_regional_gpu_returns_restricted_allocations_with_distinct_row_domains(tmp_path, monkeypatch):
    # Real catalog and production inner solver; no mocked GPU or score values.
    from pathlib import Path
    from gear_optimizer.data.csv_parser import load_csv_db, read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from tools.research._core_bound_benchmark import prepare_chart, replay_results, run_ga
    from tools.research._core_region_gpu import solve_regions
    root = Path(__file__).resolve().parents[1]
    for key in ("TIMELINE_FRONTIER_CACHE_DIR", "FG_RESPONSE_FRONTIER_CACHE_DIR", "NUMBA_CACHE_DIR"):
        monkeypatch.setenv(key, str(tmp_path / key))
    refs = build_ref_arrays_from_stats(read_table(str(root / "Data/Gear/Stats.txt")))
    gears = list(load_csv_db(str(root / "Data/Gear/Gears.csv"), "gear").values())
    minis = list(load_csv_db(str(root / "Data/Gear/Minis.csv"), "mini").values())
    song = next((root / "Data/Easy").glob('Comfort Zone *'))
    chart = prepare_chart(song, refs, gears, minis)
    observations = []
    seed = run_ga(chart, generations=2, population=32, runs=1, seed=1337, on_improvement=observations.append)
    assert observations and all(s > 0 for s in observations)
    ids = np.tile(seed["ids"], (2, 1)).astype(np.int32)
    lows = np.zeros((2, 6), dtype=np.int64)
    highs = np.full((2, 6), 90, dtype=np.int64)
    # Same stat input, different timing masks: neither row may reuse the other.
    lows[1, :2] = seed["gems"][:2]
    highs[0, :2] = 0
    highs[1, :2] = seed["gems"][:2]
    missing_flags = dict(chart.ga_kwargs["color_flags"])
    del missing_flags["is_p_ft"]
    invalid = replace(chart, ga_kwargs={**chart.ga_kwargs, "color_flags": missing_flags})
    with pytest.raises(KeyError, match="is_p_ft"):
        solve_regions(invalid, chart.arrays, ids, lows, highs)
    result = solve_regions(chart, chart.arrays, ids, lows, highs)
    assert result[0, 1:3].tolist() == [0, 0]
    assert result[1, 1:3].tolist() == seed["gems"][:2]
    scores, _ = replay_results(chart, chart.arrays, ids, result)
    assert scores[1] == seed["score"]
    assert min(scores) > 0

    from gear_optimizer.solver.registry_solve_request import RegistrySolveRequest, dispatch_registry_solve
    from tools.research._core_bound_domain import project
    from gear_optimizer.solver.base_stats import build_stats_dict
    base = build_stats_dict(chart.base + chart.arrays["item_stats"][ids[0]].sum(axis=0))
    primary, secondary = (chart.song["metadata"][k] for k in ("Primary Color", "Secondary Color"))
    _, caps, _ = gem_limits(np.array(project(base, primary, secondary)), chart.domain.intervals, 90)
    split = int(caps[0] // 2)
    lo = np.zeros((2, 6), dtype=np.int64)
    hi = np.tile(caps, (2, 1))
    hi[0, 0], lo[1, 0] = split, split + 1
    n = 2 if lo[1, 0] <= hi[1, 0] else 1
    regional = solve_regions(chart, chart.arrays, ids[:n], lo[:n], hi[:n])
    full = np.array(dispatch_registry_solve(RegistrySolveRequest(
        population_indices=ids[:1], item_stats=chart.arrays["item_stats"],
        slot_start=chart.arrays["slot_start"], slot_count=chart.arrays["slot_count"],
        base_fixed_stats=chart.base, timeline_grid=chart.song, ref_arrays=chart.refs,
        flags=chart.ga_kwargs["color_flags"])))
    assert regional[:, 0].max() == full[0, 0]
    regional_scores, _ = replay_results(chart, chart.arrays, ids[:n], regional)
    full_scores, _ = replay_results(chart, chart.arrays, ids[:1], full)
    assert max(regional_scores) >= full_scores[0]

    from tools.research._core_adaptive_score import score_adaptive
    identity = []
    for slot, item_id in enumerate(seed["ids"]):
        name = chart.registry.id_to_item[item_id]["Name"]
        items = chart.domain.gear_items[slot] if slot < 6 else chart.domain.mini_items
        identity.append(next(i for i, item in enumerate(items) if item["Name"] == name))
    # A deliberately loose but valid bound keeps the entire legal timing domain.
    upper = log_interval(2**31)[1]
    region = SimpleNamespace(intervals=chart.domain.intervals,
                             bank=BoundBank(np.zeros((1, 6), dtype=np.int64), np.array([upper])))
    core = CoreEnumeration((Candidate(tuple(identity), ((0, upper),)),), (region,), 1, True)
    adaptive = score_adaptive(chart, core, incumbent=seed)
    assert adaptive["best"]["score"] >= seed["score"]
    assert adaptive["scored_regions"] == 1
    assert adaptive["queue_exhausted"]
    stopped = score_adaptive(chart, core, incumbent=seed, deadline=0)
    assert stopped["best"]["score"] == seed["score"]
    assert stopped["best"]["loadout"] == [chart.registry.id_to_item[i]["Name"] for i in seed["ids"]]
    assert not stopped["queue_exhausted"]
    assert not stopped["optimality_certified"]

