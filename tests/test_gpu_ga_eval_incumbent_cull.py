"""GA eval incumbent UB-culling: exhaustive-equivalence proof (GPU / Vulkan).

The production eval kernel (ga_find_best_combo_warmstart_kernel) skips the exact
inner solve for combos whose RELAXED UPPER BOUND cannot reach the best exact
score already found for the genome (lane-local + cross-lane shared incumbent).
The cull threshold is the incumbent score itself (never incumbent+1), so any
combo that could tie the incumbent is still solved and the winning combo
identity — including the packed-key tie-break on combo_idx — is unchanged.

Proof here: on real uploaded device state, the production (culled) evaluation
produces BIT-IDENTICAL per-genome winners (packed key AND result quadruple) to
a test-local exhaustive reference that runs the identical loop with the cull
threshold hardwired to 0. Any invalid cull (an upper bound that under-estimates
a true score) breaks this equality.

Also: the culled evaluation is deterministic across repeat runs (the shared
incumbent is updated via atomic_max, whose ordering varies — the final argmax
must not).

NOTE: no `from __future__ import annotations` here — this module defines a
Taichi kernel and stringified annotations break ti.kernel argument parsing.
"""

import numpy as np
import pytest

from gear_optimizer.core.color_flags import build_color_flags, normalize_color_flags
from gear_optimizer.solver import genetic_pipeline as genetic
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK

pytestmark = pytest.mark.gpu

_PRIMARY_COLOR = "Beat"
_SECONDARY_COLOR = "Flow"
_SELECTED_COLOR = "Rush"
_N_GENOMES = 64
_N_SLOTS = 9
_TOTAL_BUDGET = 90
_GEM_SCALE_FEVER = 3
_SONG_SLOT = 0


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
            "Song Name": "GA eval incumbent cull parity song",
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


def _make_exhaustive_reference_kernel():
    """Test-local exhaustive oracle: the production eval loop with cull threshold 0.

    Single pass over ALL combos (no chunking), identical lane striding, identical
    plateau-prune template value, writing the same lane fields so the production
    finalize kernel performs the same reduction.
    """
    import taichi as ti

    from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers
    from gear_optimizer.solver.taichi_gem.kernels.warmstart_common import (
        MAX_STAT,
        solve_combo_warmstart_preloaded,
    )

    @ti.kernel
    def _exhaustive_eval_kernel(
        n_genomes: ti.i32,
        n_combos: ti.i32,
        total_budget: ti.i32,
        gem_scale_fever: ti.i32,
        is_p_ft: ti.i32,
        is_s_ft: ti.i32,
        is_p_ff: ti.i32,
        is_s_ff: ti.i32,
        is_p_pp: ti.i32,
        is_s_pp: ti.i32,
        is_p_cm: ti.i32,
        is_s_cm: ti.i32,
        is_p_fm: ti.i32,
        is_s_fm: ti.i32,
        is_p_ov: ti.i32,
        is_s_ov: ti.i32,
        song_slot: ti.i32,
        prune_plateaus: ti.template(),
    ):
        GEM_STAT_TO_ELEMENT: ti.i32 = 3
        w_ft: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ft << 1) + is_s_ft)
        w_ff: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ff << 1) + is_s_ff)
        block_dim = ti.cast(kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM, ti.i32)
        total_threads = n_genomes * block_dim
        ti.loop_config(block_dim=kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)
        for tid in range(total_threads):
            genome_idx = tid // block_dim
            lane = tid - genome_idx * block_dim
            kernels_helpers.ga_warmstart_lane_best_key[genome_idx, lane] = ti.u64(0)
            for i in ti.static(range(4)):
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, i] = 0
            stats = kernels_helpers.genome_base_stats[genome_idx]
            base_pp: ti.i32 = stats[0]
            base_cm: ti.i32 = stats[1]
            base_fm: ti.i32 = stats[2]
            base_p_val: ti.i32 = stats[3]
            base_s_val: ti.i32 = stats[4]
            base_ft_stat: ti.i32 = stats[5]
            base_ff_stat: ti.i32 = stats[6]
            remaining_ft: ti.i32 = MAX_STAT - base_ft_stat
            remaining_ff: ti.i32 = MAX_STAT - base_ff_stat
            max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
            max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
            if max_ft_gems > total_budget:
                max_ft_gems = total_budget
            if max_ff_gems > total_budget:
                max_ff_gems = total_budget
            local_best_key = ti.u64(0)
            local_best_pp: ti.i32 = 0
            local_best_cm: ti.i32 = 0
            local_best_fm: ti.i32 = 0
            local_best_ov: ti.i32 = 0
            local_c: ti.i32 = lane
            while local_c < n_combos:
                combo_idx: ti.i32 = local_c
                res_vec = solve_combo_warmstart_preloaded(
                    genome_idx,
                    combo_idx,
                    total_budget,
                    gem_scale_fever,
                    is_p_ft,
                    is_s_ft,
                    is_p_ff,
                    is_s_ff,
                    is_p_pp,
                    is_s_pp,
                    is_p_cm,
                    is_s_cm,
                    is_p_fm,
                    is_s_fm,
                    is_p_ov,
                    is_s_ov,
                    song_slot,
                    w_ft,
                    w_ff,
                    base_pp,
                    base_cm,
                    base_fm,
                    base_p_val,
                    base_s_val,
                    base_ft_stat,
                    base_ff_stat,
                    max_ft_gems,
                    max_ff_gems,
                    prune_plateaus,
                    True,
                    False,
                    0,
                )
                score = res_vec[0]
                if score >= 0:
                    key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                    if key > local_best_key:
                        local_best_key = key
                        local_best_pp = res_vec[1]
                        local_best_cm = res_vec[2]
                        local_best_fm = res_vec[3]
                        local_best_ov = res_vec[4]
                local_c += block_dim
            if local_best_key != ti.u64(0):
                kernels_helpers.ga_warmstart_lane_best_key[genome_idx, lane] = local_best_key
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 0] = local_best_pp
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 1] = local_best_cm
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 2] = local_best_fm
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 3] = local_best_ov

    return _exhaustive_eval_kernel


@pytest.fixture(scope="module")
def eval_device_state():
    """Upload real GA device state (timeline, items, seeded population) once."""
    if not _has_taichi():
        pytest.skip("Taichi not available")
    if not getattr(genetic, "_GPU_NATIVE_AVAILABLE", False):
        pytest.skip("GPU-native GA modules not available")

    import importlib

    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")

    registry = _build_registry()
    gpu_arrays = registry.to_gpu_arrays()
    item_stats = np.asarray(gpu_arrays["item_stats"], dtype=np.int32)
    slot_start = np.asarray(gpu_arrays["slot_start"], dtype=np.int32)
    slot_count = np.asarray(gpu_arrays["slot_count"], dtype=np.int32)
    base_fixed_stats_arr, _sel = genetic.build_base_fixed_stats_array(
        {}, {"selected_color": _SELECTED_COLOR, "primary_color": _PRIMARY_COLOR, "secondary_color": _SECONDARY_COLOR}
    )
    base_fixed_stats_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32)

    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    flags = normalize_color_flags(build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR)).as_tuple()

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=_SONG_SLOT, prebuilt_frontier=prebuilt)
        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
        gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
        gpu_api.ga_generate_initial_populations(
            run_idx_start=0,
            n_runs=1,
            n_genomes=_N_GENOMES,
            n_slots=_N_SLOTS,
            seed=20260612,
            heuristic_prob=0.0,
            heuristic_k=0,
            heuristic_copies=0,
        )
        gpu_api.ga_load_initial_populations_batch(
            run_idx_start=0,
            n_runs=1,
            n_genomes_per_run=_N_GENOMES,
            n_slots=_N_SLOTS,
        )
        gpu_api.ga_seed_rng_runs_indexed(
            n_runs=1,
            n_genomes_per_run=_N_GENOMES,
            seed_base=20260612,
            run_idx_start=0,
        )
    return flags


def _run_production_eval(flags) -> tuple[np.ndarray, np.ndarray]:
    import importlib

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers

    (
        is_p_ft,
        is_s_ft,
        is_p_ff,
        is_s_ff,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
    ) = flags
    gpu_api.ga_prepare_population_base_stats(
        _N_GENOMES,
        _N_SLOTS,
        is_p_ft=is_p_ft,
        is_s_ft=is_s_ft,
        is_p_ff=is_p_ff,
        is_s_ff=is_s_ff,
        is_p_pp=is_p_pp,
        is_s_pp=is_s_pp,
        is_p_cm=is_p_cm,
        is_s_cm=is_s_cm,
        is_p_fm=is_p_fm,
        is_s_fm=is_s_fm,
        is_p_ov=is_p_ov,
        is_s_ov=is_s_ov,
    )
    gpu_api.ga_evaluate_prepared_population(
        _N_GENOMES,
        _N_SLOTS,
        total_budget=_TOTAL_BUDGET,
        gem_scale_fever=_GEM_SCALE_FEVER,
        song_slot=_SONG_SLOT,
        is_p_ft=is_p_ft,
        is_s_ft=is_s_ft,
        is_p_ff=is_p_ff,
        is_s_ff=is_s_ff,
        is_p_pp=is_p_pp,
        is_s_pp=is_s_pp,
        is_p_cm=is_p_cm,
        is_s_cm=is_s_cm,
        is_p_fm=is_p_fm,
        is_s_fm=is_s_fm,
        is_p_ov=is_p_ov,
        is_s_ov=is_s_ov,
    )
    keys = kernels_helpers.chunk_best_key.to_numpy()[:_N_GENOMES].copy()
    results = kernels_helpers.chunk_best_results.to_numpy()[:_N_GENOMES].copy()
    return keys, results


def test_culled_eval_equals_exhaustive_reference(eval_device_state) -> None:
    flags = eval_device_state
    import importlib

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    from gear_optimizer.solver.taichi_gem.api.ga_operations import (
        _GA_PLATEAU_PRUNE_ENABLED,
        _ensure_ftff_combo_tables,
    )
    from gear_optimizer.solver.taichi_gem.kernels import (
        ga_finalize_warmstart_lane_best_kernel,
    )

    with _GPU_LOCK:
        prod_keys, prod_results = _run_production_eval(flags)

        # The proof is vacuous unless the fixture actually finds winners.
        assert int(np.count_nonzero(prod_keys)) == _N_GENOMES, (
            "fixture produced genomes without any valid combo; the parity proof would be vacuous"
        )

        # Exhaustive reference on the SAME device state: re-run prepare (which
        # re-aggregates the identical population and re-zeroes chunk_best + the
        # shared incumbent), then evaluate every combo with cull threshold 0.
        n_combos = _ensure_ftff_combo_tables(
            _TOTAL_BUDGET, max_ft_gems=_TOTAL_BUDGET, max_ff_gems=_TOTAL_BUDGET
        )
        assert int(n_combos) > 0
        (
            is_p_ft,
            is_s_ft,
            is_p_ff,
            is_s_ff,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
        ) = flags
        gpu_api.ga_prepare_population_base_stats(
            _N_GENOMES,
            _N_SLOTS,
            is_p_ft=is_p_ft,
            is_s_ft=is_s_ft,
            is_p_ff=is_p_ff,
            is_s_ff=is_s_ff,
            is_p_pp=is_p_pp,
            is_s_pp=is_s_pp,
            is_p_cm=is_p_cm,
            is_s_cm=is_s_cm,
            is_p_fm=is_p_fm,
            is_s_fm=is_s_fm,
            is_p_ov=is_p_ov,
            is_s_ov=is_s_ov,
        )
        exhaustive = _make_exhaustive_reference_kernel()
        exhaustive(
            _N_GENOMES,
            int(n_combos),
            _TOTAL_BUDGET,
            _GEM_SCALE_FEVER,
            is_p_ft,
            is_s_ft,
            is_p_ff,
            is_s_ff,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            _SONG_SLOT,
            _GA_PLATEAU_PRUNE_ENABLED,
        )
        ga_finalize_warmstart_lane_best_kernel(_N_GENOMES)

        from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers

        ref_keys = kernels_helpers.chunk_best_key.to_numpy()[:_N_GENOMES].copy()
        ref_results = kernels_helpers.chunk_best_results.to_numpy()[:_N_GENOMES].copy()

    key_mismatch = np.nonzero(prod_keys != ref_keys)[0]
    assert key_mismatch.size == 0, (
        "culled eval winner keys differ from the exhaustive reference at genomes "
        f"{key_mismatch[:10].tolist()}: prod={prod_keys[key_mismatch[:10]].tolist()} "
        f"ref={ref_keys[key_mismatch[:10]].tolist()} — an upper-bound cull dropped a true winner"
    )
    assert np.array_equal(prod_results, ref_results), (
        "culled eval winner results differ from the exhaustive reference"
    )


def test_culled_eval_is_deterministic_across_runs(eval_device_state) -> None:
    flags = eval_device_state
    with _GPU_LOCK:
        keys_a, results_a = _run_production_eval(flags)
        keys_b, results_b = _run_production_eval(flags)
    assert np.array_equal(keys_a, keys_b), (
        "culled eval winner keys differ between identical runs — atomic incumbent ordering leaked "
        "into the final argmax"
    )
    assert np.array_equal(results_a, results_b)
