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

import copy

import numpy as np
import pytest

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.solver import genetic_pipeline_decode as genetic_decode
from gear_optimizer.solver.genetic_pipeline_decode import decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.force_greats_common import (
    FG_BASE_STATS7_KEY,
    response_frontier_base_components_row,
)
from gear_optimizer.solver.genetic_pipeline import (
    run_gpu_native_ga_runs_payload_prebuilt,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK

pytestmark = pytest.mark.gpu

_PRIMARY_COLOR = "Beat"
_SECONDARY_COLOR = "Flow"
_SELECTED_COLOR = "Rush"


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


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
            _item(
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


def _ref_arrays() -> dict[str, np.ndarray]:
    rows = 161
    return {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(2.0, 2.7, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(3.0, 5.4, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def _calc_song(*, n_notes: int = 400) -> dict:
    timestamps = np.linspace(0, 90, int(n_notes), dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "Slice3 fused owner continuation song",
            "Difficulty": "Hard",
            "Primary Color": _PRIMARY_COLOR,
            "Secondary Color": _SECONDARY_COLOR,
            "Total Notes": int(n_notes),
            "Long Notes": 10,
            "Last Note Time": float(timestamps[-1]),
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {"timestamps": timestamps},
    }


@pytest.fixture(scope="module")
def real_ga_run():
    if not _has_taichi():
        pytest.skip("Taichi not available")
    if not getattr(genetic_decode, "_GPU_NATIVE_AVAILABLE", False):
        pytest.skip("GPU-native GA modules not available")

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
    cfg_data = {
        "selected_color": _SELECTED_COLOR,
        "primary_color": _PRIMARY_COLOR,
        "secondary_color": _SECONDARY_COLOR,
        "TotalBudget": 90,
        "GemScaleFever": 3,
        "fg_candidate_limit": 51,
    }
    base_fixed_stats_arr, _sel = build_base_fixed_stats_array(base_stats_fixed, cfg_data)
    base_fixed_stats_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32)

    gear_name_rank, mini_sig_id = effective_tables_for_context(
        registry,
        primary_color=_PRIMARY_COLOR,
        secondary_color=_SECONDARY_COLOR,
        selected_color=_SELECTED_COLOR,
    )

    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    color_flags = build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR)

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)

        selected_payload = run_gpu_native_ga_runs_payload_prebuilt(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=0,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            n_generations=6,
            initial_populations=None,
            num_runs=2,
            n_genomes=64,
            color_flags=color_flags,
            cfg_data=cfg_data,
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
        cfg_data=cfg_data,
        base_stats_fixed=base_stats_fixed,
        fg_candidate_limit=51,
    )
    return decoded, calc_song, ref_arrays


def test_fused_owner_continuation_matches_prefusion_route(real_ga_run) -> None:
    """Fused owner SCORE + driver materialize == pre-fusion plan/score/reduce route.

    Both routes consume the SAME decoded GA candidates (device base_stats7 + full
    BaseStats dicts). We compare at the RAW per-candidate FgResponseFrontierSolveResult
    level (before the winner-emit gate, so the proof is non-vacuous even when no
    candidate's FG beats its base on this synthetic song): the solved best_score, the
    chosen FT/FF, the resolved final stats, AND the exact surface rescore
    (score_force_greats_response_surface_exact == the value that becomes best_fg_score).
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner
    from gear_optimizer.solver.scoring.exact_rescore import (
        score_force_greats_response_surface_exact,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        load_response_frontier_scoring_bundle,
        all_response_stat_keys,
        reset_fg_response_frontier_payload_cache,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        build_fused_owner_solve_result_from_score_row,
        score_fused_owner_base_components_on_gpu_owner,
    )

    decoded, calc_song, ref_arrays = real_ga_run
    assert decoded, "no GA candidates decoded"

    def _entry_key(entry: dict) -> tuple[int, ...]:
        ids = entry.get("ga_genome_ids") or entry.get("GenomeIDs")
        assert ids is not None, "FG plan entry is missing genome ids for the parity key"
        return tuple(int(x) for x in ids)

    def _result_signature(result, base_stats) -> tuple:
        exact = score_force_greats_response_surface_exact(result.stats, calc_song, ref_arrays, result.surface)
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
            calc_song,
            ref_arrays,
            stat_keys=tuple((ft, ff) for ft in range(TOTAL_ROWS + 1) for ff in range(TOTAL_ROWS + 1)),
        )
        scoring_bundle = load_response_frontier_scoring_bundle(
            calc_song, ref_arrays, stat_keys=all_response_stat_keys()
        )

        # --- Pre-fusion route: build plan, score via the sync (owner) SCORE path to
        # RAW per-batch solve results, map back to each candidate by cache_key. ---
        prefusion_candidates = [copy.deepcopy(c) for c in decoded]
        prefusion_plan = FgPlanner.plan_many(prefusion_candidates, calc_song, ref_arrays, _PRIMARY_COLOR)
        prefusion_results, _timings = GpuScoreEngine.score_plan(prefusion_plan, gpu_client=None)
        prefusion_result_by_cache_key: dict = {}
        for prepared, results in zip(prefusion_plan.prepared_batches, prefusion_results, strict=True):
            for (cache_key, _bs), result in zip(prepared.rows, results, strict=True):
                prefusion_result_by_cache_key[cache_key] = result
        prefusion_by_key: dict = {}
        for entry, _ed, _sel, base_stats, _pbs, cache_key in prefusion_plan.pending_jobs:
            prefusion_by_key[_entry_key(entry)] = _result_signature(
                prefusion_result_by_cache_key[cache_key], base_stats
            )

        # --- Fused route: derive base_components from device base_stats7, score on
        # the owner, then materialize each plan candidate from the owner map. ---
        fused_candidates = [copy.deepcopy(c) for c in decoded]
        fused_plan = FgPlanner.plan_many(fused_candidates, calc_song, ref_arrays, _PRIMARY_COLOR)
        base_components = np.concatenate(
            [np.asarray(p.batch.base_components, dtype=np.int32) for p in fused_plan.prepared_batches]
        )
        owner_map = score_fused_owner_base_components_on_gpu_owner(
            base_components=base_components,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            selected_color=_SELECTED_COLOR,
            scoring_bundle=scoring_bundle,
        )
        fused_by_key: dict = {}
        for entry, eval_data, selected, base_stats, _pbs, _cache_key in fused_plan.pending_jobs:
            bc = tuple(
                int(v)
                for v in response_frontier_base_components_row(
                    base_stats,
                    eval_data.get(FG_BASE_STATS7_KEY),
                    primary_color=_PRIMARY_COLOR,
                    secondary_color=_SECONDARY_COLOR,
                )
            )
            score_row = owner_map.get(bc)
            assert score_row is not None, f"owner map missing base_components {bc}"
            solve_result = build_fused_owner_solve_result_from_score_row(
                score_row=score_row,
                base_stats=base_stats,
                selected_color=selected,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                scoring_bundle=scoring_bundle,
            )
            fused_by_key[_entry_key(entry)] = _result_signature(solve_result, base_stats)

    assert prefusion_by_key, "pre-fusion route produced no candidate results to compare"
    assert set(prefusion_by_key) == set(fused_by_key), "fused and pre-fusion routes scored different candidate sets"
    mismatches: list[str] = []
    for entry_key, pre_sig in prefusion_by_key.items():
        fused_sig = fused_by_key.get(entry_key)
        if fused_sig != pre_sig:
            mismatches.append(f"ids={entry_key}:\n  prefusion={pre_sig}\n  fused    ={fused_sig}")
    assert not mismatches, (
        "fused owner continuation FG results differ from the pre-fusion route — NOT bit-exact:\n"
        + "\n".join(mismatches[:10])
    )
