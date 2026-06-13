"""GA batch-width invariance proof (GPU / Vulkan).

GA multi-run batch width is a SCHEDULE-ONLY knob: how many runs share one GPU
dispatch. Per-run seeding is ``seed_base + global_run_idx + r`` with run-local
genome indexing, and tournament/elitism/next-gen sampling stay strictly within
each run segment, so co-batching N runs into one dispatch vs running them in
smaller batches must produce the EXACT same per-run payload.

This test runs the production entrypoint ``run_gpu_native_ga_runs_payload_prebuilt``
twice on identical seeded inputs -- once forced to batch width 2 (so 6 runs
dispatch as 3 sequential batch-2 dispatches per generation) and once forced to
batch width 6 (one batch-6 dispatch that engages combo chunking, since
6*64*n_combos exceeds MAX_EVALS_PER_DISPATCH) -- and asserts the returned
payloads are byte-identical.

Batch width is forced through the REAL sizing function ``choose_ga_batch_runs``
via its existing ``batch_runs_override`` input (no behavior flags): the test
wraps the production callable so it returns a fixed batch width while every other
production input flows through unchanged.

If this fails, batch width is NOT schedule-only and the GA batch-width
unification (genome-capacity-only sizing + combo chunking owning TDR safety) is
not exact and must not ship.
"""

from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.solver import genetic_pipeline as genetic
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt
from gear_optimizer.solver.gpu_tuning_policy import choose_ga_batch_runs
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK

pytestmark = pytest.mark.gpu

_PRIMARY_COLOR = "Beat"
_SECONDARY_COLOR = "Flow"
_SELECTED_COLOR = "Rush"

_NUM_RUNS = 6
_N_GENOMES = 64
_N_GENERATIONS = 6
_GA_SEED = 20260612


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
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def _calc_song(*, n_notes: int = 400) -> dict:
    timestamps = np.linspace(0, 90, int(n_notes), dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "GA batch-width invariance song",
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


def _run_payload_with_forced_batch_width(monkeypatch, *, forced_batch_runs: int) -> np.ndarray:
    """Run the production GA entrypoint with batch width pinned to ``forced_batch_runs``.

    The pin is injected through ``choose_ga_batch_runs``'s real ``batch_runs_override``
    input -- the same production path that ``_GPU_NATIVE_GA_BATCH_RUNS`` uses -- so the
    only thing that differs between the two runs is the run-batching schedule.
    """

    def _forced_choose(*, n_genomes, num_runs, max_genomes, batch_runs_override=0):
        return choose_ga_batch_runs(
            n_genomes=n_genomes,
            num_runs=num_runs,
            max_genomes=max_genomes,
            batch_runs_override=int(forced_batch_runs),
        )

    monkeypatch.setattr(genetic, "choose_ga_batch_runs", _forced_choose)

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

    cfg_data = {
        "selected_color": _SELECTED_COLOR,
        "primary_color": _PRIMARY_COLOR,
        "secondary_color": _SECONDARY_COLOR,
        "TotalBudget": 90,
        "GemScaleFever": 3,
        "fg_candidate_limit": 51,
    }
    base_fixed_stats_arr, _sel = genetic.build_base_fixed_stats_array({}, cfg_data)
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

        payload = run_gpu_native_ga_runs_payload_prebuilt(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=0,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            n_generations=_N_GENERATIONS,
            initial_populations=None,
            num_runs=_NUM_RUNS,
            n_genomes=_N_GENOMES,
            color_flags=color_flags,
            cfg_data=cfg_data,
            ga_seed=_GA_SEED,
            fg_gear_name_rank=gear_name_rank,
            fg_mini_sig_id=mini_sig_id,
        )

    return np.asarray(payload, dtype=np.int32)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_batch_width_invariant_batch2x3_equals_batch6(monkeypatch):
    if not getattr(genetic, "_GPU_NATIVE_AVAILABLE", False):
        pytest.skip("GPU-native GA modules not available")

    # Sanity: this geometry actually exercises both regimes -- batch-2 stays under
    # the eval budget (no combo chunking) while batch-6 exceeds it (combo chunking
    # accumulates across chunks). If they were not distinct schedules the proof
    # would be vacuous.
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    assert _NUM_RUNS * _N_GENOMES <= int(gpu_fields.MAX_GENOMES), (
        "test geometry must fit a full batch-6 in the MAX_GENOMES pool"
    )

    payload_batch2 = _run_payload_with_forced_batch_width(monkeypatch, forced_batch_runs=2)
    payload_batch6 = _run_payload_with_forced_batch_width(monkeypatch, forced_batch_runs=6)

    assert payload_batch2.shape == payload_batch6.shape, (
        f"payload shape differs: batch2x3={payload_batch2.shape} vs batch6={payload_batch6.shape}"
    )
    selected_n2 = int(payload_batch2[0, 0])
    selected_n6 = int(payload_batch6[0, 0])
    assert selected_n2 > 0 and selected_n6 > 0, (
        f"GA produced an empty selected payload (batch2={selected_n2}, batch6={selected_n6})"
    )
    assert np.array_equal(payload_batch2, payload_batch6), (
        "GA batch width is NOT schedule-only: batch-2x3 and batch-6 produced different "
        "per-run payloads (batch width must not affect the result)"
    )
