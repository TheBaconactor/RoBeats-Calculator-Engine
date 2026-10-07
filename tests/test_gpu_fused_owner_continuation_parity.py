"""Slice 3 fused GA->FG owner-continuation bit-exactness proof (GPU / Vulkan).

The fused handoff scores FG on the GPU owner straight from the device base_stats7
(== base_components) in the same owner turn as the GA, then hands a compact
per-base_components result map back to the driver, which materializes with the
full BaseStats dict off the owner's critical path.

This test proves, deterministically in one process, that the fused route produces
the EXACT same per-candidate FG result as the pre-fusion driver route
(prepare plan -> GpuScoreEngine.score_plan -> reducer materialize) for the SAME
real GA candidates: identical raw solve best_score AND identical exact surface
rescore (the value that becomes best_fg_score). The GA is seeded so the candidate
set is fixed; the comparison isolates the fused scoring/handoff from GA drift.

If this fails the fused owner SCORE is not bit-exact and Slice 3 must not ship.
"""

from __future__ import annotations

from tests.curves_support import synthetic_curves
import copy

import numpy as np
import pytest

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.solver.genetic_pipeline_decode import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.base_stats import build_stats_array
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.force_greats_common import (
    FG_BASE_STATS7_KEY,
    response_frontier_base_components_row,
)
from gear_optimizer.solver.genetic_pipeline import (
    run_gpu_native_ga_runs_payload_prebuilt,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.gamedata import Gear, SongMini
from tests.items_support import make_gear, make_song_mini
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
from tests.songs_support import make_song

pytestmark = pytest.mark.gpu

_PRIMARY_COLOR = "Beat"
_SECONDARY_COLOR = "Flow"
_SELECTED_COLOR = "Rush"


def _item(name: str, **stats: int) -> Gear:
    return make_gear(name, **stats)


def _mini_item(name: str, **stats: int) -> SongMini:
    return make_song_mini(name, **stats)


def _build_registry() -> ItemRegistry:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool: dict[str, list[dict]] = {}
    for s_idx, slot in enumerate(slots):
        items = []
        for i in range(4):
            items.append(
                _item(
                    f"{slot}{i}",
                    **{
                        "Perfect Points": 7 + s_idx + i,
                        "Combo Multiplier": 3 + i,
                        "Fever Multiplier": 2 + s_idx,
                        "Fever Time": 4 + i,
                        "Fever Fill Rate": 5 + s_idx,
                        "Beat": 6 + i,
                        "Vibe": 2 + s_idx,
                        "Rush": 3 + i,
                        "Flow": 4 + s_idx,
                        "Chill": 1 + i,
                    },
                )
            )
        gear_pool[slot] = items

    mini_pool = []
    for i in range(12):
        mini_pool.append(
            _mini_item(
                f"M{i}",
                **{
                    "Perfect Points": 2 + (i % 5),
                    "Combo Multiplier": 1 + (i % 3),
                    "Fever Multiplier": 1 + (i % 4),
                    "Fever Time": 1 + (i % 2),
                    "Fever Fill Rate": 2 + (i % 3),
                    "Beat": 1 + (i % 4),
                    "Vibe": 2 + (i % 2),
                    "Rush": 1 + (i % 5),
                    "Flow": 3 + (i % 2),
                    "Chill": 1 + (i % 3),
                },
            )
        )
    return ItemRegistry(gear_pool, mini_pool, slots)


def _curves() -> dict[str, np.ndarray]:
    rows = 161
    return synthetic_curves({
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.4, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    })


def _song(*, n_notes: int = 400):
    return make_song(
        np.linspace(0, 90, int(n_notes)),
        name="Slice3 fused owner continuation song",
        primary=_PRIMARY_COLOR,
        secondary=_SECONDARY_COLOR,
        long_notes=10,
    )


@pytest.fixture(scope="module")
def real_ga_run():
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )

    registry = _build_registry()
    gpu_arrays = registry.to_gpu_arrays()
    item_stats = np.asarray(gpu_arrays["item_stats"], dtype=np.int32)
    slot_start = np.asarray(gpu_arrays["slot_start"], dtype=np.int32)
    slot_count = np.asarray(gpu_arrays["slot_count"], dtype=np.int32)

    base_stats_fixed: dict[str, int] = {}
    selected_color = _SELECTED_COLOR
    base_fixed_stats_arr = build_stats_array(base_stats_fixed)
    base_fixed_stats_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32)

    gear_name_rank, mini_sig_id = effective_tables_for_context(
        registry,
        primary_color=_PRIMARY_COLOR,
        secondary_color=_SECONDARY_COLOR,
        selected_color=_SELECTED_COLOR,
    )

    song = _song()
    curves = _curves()
    color_flags = build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR)

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(song, curves)
        precompute_timeline_gpu(song, curves, song_slot=0, prebuilt_frontier=prebuilt)

        selected_payload = run_gpu_native_ga_runs_payload_prebuilt(
            song=song,
            curves=curves,
            song_slot=0,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            n_generations=6,
            num_runs=2,
            n_genomes=64,
            color_flags=color_flags,
            ga_seed=20260612,
            fg_gear_name_rank=gear_name_rank,
            fg_mini_sig_id=mini_sig_id,
        )

    selected_payload = np.asarray(selected_payload, dtype=np.int32)
    assert selected_payload.ndim == 2
    selected_n = int(selected_payload[0, 0])
    assert selected_n > 0, "real GA produced an empty selected payload"

    _best_data, _best_gear, _best_minis, decoded = decode_gpu_native_ga_runs_payload(
        runs_payload=selected_payload,
        registry=registry,
        selected_color=selected_color,
        base_stats_fixed=base_stats_fixed,
        fg_candidate_limit=51,
    )
    return decoded, song, curves


def test_fused_owner_continuation_matches_prefusion_route(real_ga_run) -> None:
    """Fused owner SCORE + driver materialize == pre-fusion plan/score/reduce route.

    Both routes consume the SAME decoded GA candidates (device base_stats7 + full
    BaseStats dicts). We compare at the RAW per-candidate FgResponseFrontierSolveResult
    level (before the winner-emit gate, so the proof is non-vacuous even when no
    candidate's FG beats its base on this synthetic song): the solved best_score, the
    chosen FT/FF, the resolved final stats, AND the exact surface rescore
    (score_force_greats_response_surface_exact == the value that becomes best_fg_score).
    """
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner
    from gear_optimizer.solver.scoring.exact_rescore import (
        score_force_greats_response_surface_exact,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        load_response_frontier_scoring_bundle,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import reset_fg_response_frontier_payload_cache
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        build_fused_owner_solve_result_from_score_row,
        score_fg_base_components,
    )

    decoded, song, curves = real_ga_run
    assert decoded, "no GA candidates decoded"

    def _result_signature(result, base_stats) -> tuple:
        exact = score_force_greats_response_surface_exact(result.stats, song, curves, result.surface)
        return (
            int(result.best_score),
            int(result.ft),
            int(result.ff),
            tuple(sorted((str(k), int(v)) for k, v in result.stats.items())),
            int(exact) if exact is not None else None,
        )

    with _GPU_LOCK:
        reset_fg_response_frontier_payload_cache()
        build_or_load_response_frontier_payload(
            song,
            curves,
            stat_keys=tuple((ft, ff) for ft in range(MAX_STAT + 1) for ff in range(MAX_STAT + 1)),
        )
        scoring_bundle = load_response_frontier_scoring_bundle(
            song, curves, stat_keys=all_response_stat_keys()
        )

        # --- Pre-fusion route: build plan, score via the sync (owner) SCORE path to
        # RAW per-batch solve results, map back to each candidate by cache_key. ---
        prefusion_candidates = [copy.deepcopy(c) for c in decoded]
        prefusion_plan = FgPlanner.plan_many(prefusion_candidates, song, curves, _PRIMARY_COLOR)
        prefusion_results = GpuScoreEngine.score_plan(prefusion_plan)
        prefusion_result_by_cache_key: dict = {}
        for prepared, results in zip(prefusion_plan.prepared_batches, prefusion_results, strict=True):
            for (cache_key, _bs), result in zip(prepared.rows, results, strict=True):
                prefusion_result_by_cache_key[cache_key] = result
        # Both plans come from the same candidates in the same order: jobs pair up by position.
        prefusion_by_key: dict = {
            index: _result_signature(prefusion_result_by_cache_key[job.key], job.base_stats)
            for index, job in enumerate(prefusion_plan.jobs)
        }

        # --- Fused route: derive base_components from device base_stats7, score on
        # the owner, then materialize each plan candidate from the owner map. ---
        fused_candidates = [copy.deepcopy(c) for c in decoded]
        fused_plan = FgPlanner.plan_many(fused_candidates, song, curves, _PRIMARY_COLOR)
        base_components = np.concatenate(
            [np.asarray(p.batch.base_components, dtype=np.int32) for p in fused_plan.prepared_batches]
        )
        owner_map = score_fg_base_components(
            base_components=base_components,
            song=song,
            curves=curves,
            selected_color=_SELECTED_COLOR,
            scoring_bundle=scoring_bundle,
        )
        # As the production materializer: a job's owner row is keyed by its batch row's base_components.
        base_components_by_cache_key = {
            cache_key: tuple(int(v) for v in prepared.batch.base_components[row_idx].tolist())
            for prepared in fused_plan.prepared_batches
            for row_idx, (cache_key, _bs) in enumerate(prepared.rows)
        }
        fused_by_key: dict = {}
        for index, job in enumerate(fused_plan.jobs):
            bc = base_components_by_cache_key[job.key]
            score_row = owner_map.get(bc)
            assert score_row is not None, f"owner map missing base_components {bc}"
            solve_result = build_fused_owner_solve_result_from_score_row(
                score_row=score_row,
                base_stats=job.base_stats,
                selected_color=job.selected,
                song=song,
                curves=curves,
                scoring_bundle=scoring_bundle,
            )
            fused_by_key[index] = _result_signature(solve_result, job.base_stats)

    assert prefusion_by_key, "pre-fusion route produced no candidate results to compare"
    assert set(prefusion_by_key) == set(fused_by_key), "fused and pre-fusion routes scored different candidate sets"
    mismatches: list[str] = []
    for entry_key, pre_sig in prefusion_by_key.items():
        fused_sig = fused_by_key.get(entry_key)
        if fused_sig != pre_sig:
            mismatches.append(f"job {entry_key}:\n  prefusion={pre_sig}\n  fused    ={fused_sig}")
    assert not mismatches, (
        "fused owner continuation FG results differ from the pre-fusion route — NOT bit-exact:\n"
        + "\n".join(mismatches[:10])
    )
