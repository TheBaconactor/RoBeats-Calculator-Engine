"""On-device bruteforce-vs-bound soundness sweep for the coupled combo-cull upper bound.

Certifies, on the Vulkan device at real score magnitudes, the hard contract of the tightened
`response_score_upper_bound_relaxed` (design UB_CULL_BOUND_DESIGN.md, Design 1):

    exact_combo(genome, combo)  <=  UB_gate(genome, combo)  <=  old_relaxed_bound(...)

for every (genome, combo) over uploaded device state (timeline frontier, items, seeded
population). The left inequality is the soundness contract — an under-estimating bound would
cull a true winner and corrupt best_score corpus-wide. The right inequality proves the change
only ever tightens: UB_gate = min(old, UB_fm, UB_cm) can never exceed the old bound.

The old bound is recomputed here as a test-local reference @ti.func (`_old_relaxed_bound_ref`)
reproducing the pre-change body verbatim — NOT a retained production route (the production
function now returns the tightened min). The exact score is the production exact solver over
the real frontier (`solve_combo_warmstart_preloaded` with the cull disabled), i.e. the exact
value the cull gate must dominate.

This is the load-bearing certificate the CPU replica (tests/test_ub_cull_hull_dominance.py)
cannot provide: it pins the final ~1-2 ULP of Vulkan f32 rounding order of the folded product
(design section 4 residual). Run it in the GPU window alongside the FG frontier parity suite.

NOTE: no `from __future__ import annotations` — this module defines a Taichi kernel and
stringified annotations break ti.kernel argument parsing.
"""

import numpy as np
import pytest

from gear_optimizer.core.color_flags import build_color_flags, normalize_color_flags
from gear_optimizer.solver import genetic_pipeline as genetic
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
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
    # Concave (diminishing-returns) LUTs matching the real Stats.txt shape so the concave
    # envelopes exercise their multi-segment sweep at real curvature.
    t = np.linspace(0.0, 1.0, rows)
    concave = 2.0 * t - t * t
    return {
        "Perfect Points": (200.0 + 285.0 * concave).astype(np.float64),
        "Combo Multiplier": (2.0 + 0.67 * concave).astype(np.float64),
        "Fever Multiplier": (3.0 + 2.425 * concave).astype(np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def _calc_song(*, n_notes: int = 1200) -> dict:
    timestamps = np.linspace(0, 240, int(n_notes), dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "UB cull bound property song",
            "Difficulty": "Hard",
            "Primary Color": _PRIMARY_COLOR,
            "Secondary Color": _SECONDARY_COLOR,
            "Total Notes": int(n_notes),
            "Long Notes": 20,
            "Last Note Time": float(timestamps[-1]),
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {
            "timestamps": timestamps,
            "note_types": np.ones(int(n_notes), dtype=np.int16),
            "lanes": np.arange(int(n_notes), dtype=np.int32) % np.int32(4),
        },
    }


def _make_bound_vs_exact_kernel():
    """Test-local kernel: for every (genome, combo) compute UB_gate, the old-bound reference,
    and the production exact score, and reduce (a) min(UB_gate - exact), (b) count of soundness
    violations UB_gate < exact, (c) count of UB_gate > old (should be zero)."""
    import taichi as ti

    from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers
    from gear_optimizer.solver.taichi_gem.kernels.kernels_scoring import (
        _semi_exact_upper_bound,
        response_score_upper_bound_relaxed,
    )
    from gear_optimizer.solver.taichi_gem.kernels.warmstart_common import (
        MAX_STAT,
        solve_combo_warmstart_preloaded,
    )

    @ti.func
    def _old_relaxed_bound_ref(
        budget: ti.i32,
        cur_pp: ti.i32,
        cur_cm: ti.i32,
        cur_fm: ti.i32,
        cur_p_val: ti.i32,
        cur_s_val: ti.i32,
        is_p_pp: ti.i32,
        is_s_pp: ti.i32,
        is_p_cm: ti.i32,
        is_s_cm: ti.i32,
        is_p_fm: ti.i32,
        is_s_fm: ti.i32,
        is_p_ov: ti.i32,
        is_s_ov: ti.i32,
        head_len: ti.i32,
        body_total: ti.i32,
    ) -> ti.f32:
        # Verbatim reproduction of the pre-change response_score_upper_bound_relaxed body
        # (current bound only, no coupled arms). Reference-only, never a production route.
        GEM_SCALE_NORMAL: ti.i32 = 2
        GEM_SCALE_FEVER: ti.i32 = 3
        ELEMENTAL_GEM_SCALE: ti.i32 = 6
        GEM_STAT_TO_ELEMENT: ti.i32 = 3
        MAX_STAT_C: ti.i32 = 160

        pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_pp
        pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_pp
        cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_cm
        cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_cm
        fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_p_fm
        fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT * is_s_fm
        ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
        ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

        w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
        w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
        w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
        w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
        w_max: ti.i32 = ti.max(ti.max(w_pp, w_cm), ti.max(w_fm, w_ov))

        pp_stat: ti.i32 = ti.min(MAX_STAT_C, ti.max(0, cur_pp + (budget * GEM_SCALE_NORMAL)))
        cm_stat: ti.i32 = ti.min(MAX_STAT_C, ti.max(0, cur_cm + (budget * GEM_SCALE_NORMAL)))
        fm_stat: ti.i32 = ti.min(MAX_STAT_C, ti.max(0, cur_fm + (budget * GEM_SCALE_FEVER)))

        base_lane: ti.i32 = (cur_p_val << 1) + cur_s_val + (budget * w_max)
        base_value: ti.f32 = ti.cast(base_lane, ti.f32) + kernels_helpers.lookup_ref_pp(pp_stat)
        combo_mul: ti.f32 = kernels_helpers.lookup_ref_cm(cm_stat)
        fever_mul: ti.f32 = kernels_helpers.lookup_ref_fm(fm_stat)

        head_len_c: ti.i32 = ti.max(0, ti.min(head_len, 100))
        sigma_hf: ti.i32 = (head_len_c * (head_len_c + 1)) // 2
        body_total_c: ti.i32 = ti.max(0, body_total)

        return _semi_exact_upper_bound(
            base_value, combo_mul, fever_mul, body_total_c, 0, 0, head_len_c, 0, sigma_hf
        )

    @ti.kernel
    def _kernel(
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
        out_min_slack: ti.template(),
        out_soundness_viol: ti.template(),
        out_tighten_viol: ti.template(),
        out_checked: ti.template(),
    ):
        GEM_STAT_TO_ELEMENT: ti.i32 = 3
        w_ft: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ft << 1) + is_s_ft)
        w_ff: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ff << 1) + is_s_ff)
        for genome_idx in range(n_genomes):
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

            combo_idx: ti.i32 = 0
            while combo_idx < n_combos:
                ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
                ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
                if ft <= max_ft_gems and ff <= max_ff_gems:
                    ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                    ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                    ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                    ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
                    body_total: ti.i32 = (
                        kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
                        + kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
                    )
                    head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]
                    budget: ti.i32 = total_budget - ft - ff
                    p_val: ti.i32 = (
                        base_p_val
                        + (ft * GEM_STAT_TO_ELEMENT * is_p_ft)
                        + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                    )
                    s_val: ti.i32 = (
                        base_s_val
                        + (ft * GEM_STAT_TO_ELEMENT * is_s_ft)
                        + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                    )

                    ub_gate: ti.f32 = response_score_upper_bound_relaxed(
                        budget, base_pp, base_cm, base_fm, p_val, s_val,
                        is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm,
                        is_p_ov, is_s_ov, head_len, body_total,
                    )
                    old_ref: ti.f32 = _old_relaxed_bound_ref(
                        budget, base_pp, base_cm, base_fm, p_val, s_val,
                        is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm,
                        is_p_ov, is_s_ov, head_len, body_total,
                    )

                    # Production exact solve over the real frontier (cull disabled -> exact winner).
                    res = solve_combo_warmstart_preloaded(
                        genome_idx, combo_idx, total_budget, gem_scale_fever,
                        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                        is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm,
                        is_p_ov, is_s_ov, song_slot, w_ft, w_ff,
                        base_pp, base_cm, base_fm, base_p_val, base_s_val,
                        base_ft_stat, base_ff_stat, max_ft_gems, max_ff_gems,
                        True, False, 0,
                    )
                    exact_score: ti.i32 = res[0]
                    if exact_score >= 0:
                        ti.atomic_add(out_checked[0], 1)
                        slack: ti.f32 = ub_gate - ti.cast(exact_score, ti.f32)
                        ti.atomic_min(out_min_slack[0], slack)
                        if ub_gate < ti.cast(exact_score, ti.f32):
                            ti.atomic_add(out_soundness_viol[0], 1)
                        # Allow a tiny epsilon for f32 rounding of the two independent bound chains.
                        if ub_gate > old_ref + ti.f32(1.0):
                            ti.atomic_add(out_tighten_viol[0], 1)
                combo_idx += 1

    return _kernel


@pytest.fixture(scope="module")
def bound_device_state():
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
    base_fixed_stats_arr, _sel = build_base_fixed_stats_array(
        {}, {"selected_color": _SELECTED_COLOR, "primary_color": _PRIMARY_COLOR, "secondary_color": _SECONDARY_COLOR}
    )
    base_fixed_stats_arr = np.asarray(base_fixed_stats_arr, dtype=np.int32)

    calc_song = _calc_song()
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    apply_timing_envelope(calc_song, mode="perfect_window")
    ref_arrays = _ref_arrays()
    flags = normalize_color_flags(build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR)).as_tuple()

    with _GPU_LOCK:
        ensure_ready()
        prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=_SONG_SLOT, prebuilt_frontier=prebuilt)
        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
        gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
        gpu_api.ga_generate_initial_populations(
            run_idx_start=0, n_runs=1, n_genomes=_N_GENOMES, n_slots=_N_SLOTS,
            seed=20260716, heuristic_prob=0.0, heuristic_k=0, heuristic_copies=0,
        )
        gpu_api.ga_load_initial_populations_batch(
            run_idx_start=0, n_runs=1, n_genomes_per_run=_N_GENOMES, n_slots=_N_SLOTS,
        )
        gpu_api.ga_seed_rng_runs_indexed(
            n_runs=1, n_genomes_per_run=_N_GENOMES, seed_base=20260716, run_idx_start=0,
        )
    return flags


def test_bound_dominates_exact_and_tightens_on_device(bound_device_state) -> None:
    import importlib

    import taichi as ti

    gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    from gear_optimizer.solver.taichi_gem.api.ga_operations import _ensure_ftff_combo_tables

    flags = bound_device_state
    (
        is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
        is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    ) = flags

    with _GPU_LOCK:
        # Prepare the population base stats (same aggregation the production eval uses).
        gpu_api.ga_prepare_population_base_stats(
            _N_GENOMES, _N_SLOTS,
            is_p_ft=is_p_ft, is_s_ft=is_s_ft, is_p_ff=is_p_ff, is_s_ff=is_s_ff,
            is_p_pp=is_p_pp, is_s_pp=is_s_pp, is_p_cm=is_p_cm, is_s_cm=is_s_cm,
            is_p_fm=is_p_fm, is_s_fm=is_s_fm, is_p_ov=is_p_ov, is_s_ov=is_s_ov,
        )
        n_combos = _ensure_ftff_combo_tables(_TOTAL_BUDGET, max_ft_gems=_TOTAL_BUDGET, max_ff_gems=_TOTAL_BUDGET)
        assert int(n_combos) > 0

        out_min_slack = ti.field(ti.f32, shape=1)
        out_soundness_viol = ti.field(ti.i32, shape=1)
        out_tighten_viol = ti.field(ti.i32, shape=1)
        out_checked = ti.field(ti.i32, shape=1)
        out_min_slack.from_numpy(np.asarray([1.0e30], dtype=np.float32))
        out_soundness_viol.from_numpy(np.asarray([0], dtype=np.int32))
        out_tighten_viol.from_numpy(np.asarray([0], dtype=np.int32))
        out_checked.from_numpy(np.asarray([0], dtype=np.int32))

        kernel = _make_bound_vs_exact_kernel()
        kernel(
            _N_GENOMES, int(n_combos), _TOTAL_BUDGET, _GEM_SCALE_FEVER,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
            is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
            _SONG_SLOT, out_min_slack, out_soundness_viol, out_tighten_viol, out_checked,
        )
        checked = int(out_checked.to_numpy()[0])
        soundness_viol = int(out_soundness_viol.to_numpy()[0])
        tighten_viol = int(out_tighten_viol.to_numpy()[0])
        min_slack = float(out_min_slack.to_numpy()[0])

    assert checked > 0, "no (genome, combo) produced a valid exact score; proof would be vacuous"
    assert soundness_viol == 0, (
        f"{soundness_viol}/{checked} (genome, combo) pairs had UB_gate < exact_combo on device — "
        "the tightened cull bound under-estimates a reachable score (best_score corruption risk). "
        f"min slack {min_slack}"
    )
    assert tighten_viol == 0, (
        f"{tighten_viol}/{checked} pairs had UB_gate > old bound — the change is not a pure "
        "tightening (min() wiring bug)"
    )
    assert min_slack >= 0.0
