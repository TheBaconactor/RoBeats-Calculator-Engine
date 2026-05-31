import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _ref_arrays():
    size = 1001
    return {
        "Perfect Points": np.linspace(0.0, 2.0, size, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, size, dtype=np.float32),
    }


def _prebuild_response_bundle(calc_song, ref_arrays, base_stats_list, *, total_budget: int) -> None:
    from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_ROWS
    from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )

    reset_fg_response_frontier_payload_cache()
    ft_values, ff_values, _remaining = ftff_combo_arrays(int(total_budget))
    keys = set()
    for base_stats in base_stats_list:
        base_ft = int(base_stats.get("Fever Time", 0) or 0)
        base_ff = int(base_stats.get("Fever Fill Rate", 0) or 0)
        ft_stats = np.clip(base_ft + (ft_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
        ff_stats = np.clip(base_ff + (ff_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
        keys.update((int(ft), int(ff)) for ft, ff in zip(ft_stats.tolist(), ff_stats.tolist(), strict=True))
    build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=tuple(sorted(keys)))


def test_ftff_projection_matches_canonical_stats_for_consumed_fields():
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import _stats_after_ftff_for_inner

    def _score_elements(stats: dict, primary: str, secondary: str) -> tuple[int, int]:
        return (
            int(stats.get(primary, 0) or 0),
            int(stats.get(secondary, 0) or 0),
        )

    base_stats = {
        "Perfect Points": 11,
        "Combo Multiplier": 22,
        "Fever Multiplier": 33,
        "Fever Fill Rate": 44,
        "Fever Time": 55,
        "Chill": 1,
        "Flow": 2,
        "Rush": 3,
        "Beat": 4,
        "Vibe": 5,
    }
    colors = ("Chill", "Flow", "Rush", "Beat", "Vibe")

    for primary in colors:
        for secondary in colors:
            projected = _stats_after_ftff_for_inner(
                base_stats,
                ft=7,
                ff=9,
                primary_color=primary,
                secondary_color=secondary,
            )
            canonical = apply_gems_to_base_stats(base_stats, "Chill", 7, 9, 0, 0, 0, 0)

            for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"):
                assert projected[key] == canonical[key]
            assert _score_elements(projected, primary, secondary) == _score_elements(canonical, primary, secondary)


def test_response_frontier_gpu_inner_matches_reference_inner_with_overlap():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from tests.parity.fg_response_frontier_cpu import (
        optimize_response_frontier_inner_exact,
        optimize_response_frontier_inner_exact_gpu,
    )

    surfaces = (
        FgResponseSurface(0b111, 0, 0, 0, 0b001, 0, 0, 0, 2, 1),
        FgResponseSurface(0b011, 0, 0, 0, 0b000, 0, 0, 0, 1, 0),
    )
    kwargs = {
        "total_notes": 105,
        "residual_budget": 3,
        "stats_after_ftff": {
            "Perfect Points": 10,
            "Combo Multiplier": 20,
            "Fever Multiplier": 30,
            "Power": 40,
            "Rush": 50,
        },
        "primary_color": "Power",
        "secondary_color": "Rush",
        "selected_color": "Power",
        "ref_arrays": _ref_arrays(),
    }

    reference = optimize_response_frontier_inner_exact(surfaces, **kwargs)
    gpu = optimize_response_frontier_inner_exact_gpu(surfaces, **kwargs)

    assert gpu == reference


def test_response_frontier_gpu_inner_scores_same_color_greats_as_single_color():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from tests.parity.fg_response_frontier_cpu import (
        optimize_response_frontier_inner_exact,
        optimize_response_frontier_inner_exact_gpu,
    )

    surfaces = (FgResponseSurface(0, 0, 0, 0, 0b1111, 0, 0, 0, 0, 0),)
    kwargs = {
        "total_notes": 4,
        "residual_budget": 0,
        "stats_after_ftff": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Chill": 812,
        },
        "primary_color": "Chill",
        "secondary_color": "Chill",
        "selected_color": "Chill",
        "ref_arrays": _ref_arrays(),
    }

    reference = optimize_response_frontier_inner_exact(surfaces, **kwargs)
    gpu = optimize_response_frontier_inner_exact_gpu(surfaces, **kwargs)

    assert reference.best_score == 4 * 1774
    assert gpu == reference


def test_response_frontier_gpu_batch_pack_matches_reference_groups():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner import _optimize_response_surfaces_gpu
    from tests.parity.fg_response_frontier_cpu import optimize_response_frontier_inner_exact

    surfaces_a = (
        FgResponseSurface(0b1111, 0, 0, 0, 0b0010, 0, 0, 0, 4, 1),
        FgResponseSurface(0b0111, 0, 0, 0, 0b0000, 0, 0, 0, 2, 0),
        FgResponseSurface(0b1110, 0, 0, 0, 0b0100, 0, 0, 0, 5, 2),
    )
    surfaces_b = (
        FgResponseSurface(0b101, 0, 0, 0, 0b001, 0, 0, 0, 1, 1),
        FgResponseSurface(0b111, 0, 0, 0, 0b011, 0, 0, 0, 3, 2),
    )
    shared = {
        "total_notes": 108,
        "primary_color": "Power",
        "secondary_color": "Rush",
        "selected_color": "Power",
        "ref_arrays": _ref_arrays(),
    }
    stats_a = {
        "Perfect Points": 10,
        "Combo Multiplier": 20,
        "Fever Multiplier": 30,
        "Power": 40,
        "Rush": 50,
    }
    stats_b = {
        "Perfect Points": 30,
        "Combo Multiplier": 15,
        "Fever Multiplier": 25,
        "Power": 20,
        "Rush": 80,
    }

    rows, surface_rows = _optimize_response_surfaces_gpu(
        [(5, stats_a, surfaces_a), (4, stats_b, surfaces_b), (3, stats_b, surfaces_a)],
        **shared,
    )

    ref_a = optimize_response_frontier_inner_exact(
        surfaces_a,
        residual_budget=5,
        stats_after_ftff=stats_a,
        **shared,
    )
    ref_b = optimize_response_frontier_inner_exact(
        surfaces_b,
        residual_budget=4,
        stats_after_ftff=stats_b,
        **shared,
    )
    ref_c = optimize_response_frontier_inner_exact(
        surfaces_a,
        residual_budget=3,
        stats_after_ftff=stats_b,
        **shared,
    )

    assert surface_rows == len(surfaces_a) + len(surfaces_b) + len(surfaces_a)
    assert rows == [
        (
            ref_a.best_score,
            ref_a.surface_index,
            ref_a.g_pp,
            ref_a.g_cm,
            ref_a.g_fm,
            ref_a.g_ov,
            ref_a.final_pp,
            ref_a.final_cm,
            ref_a.final_fm,
            ref_a.final_primary,
            ref_a.final_secondary,
        ),
        (
            ref_b.best_score,
            ref_b.surface_index,
            ref_b.g_pp,
            ref_b.g_cm,
            ref_b.g_fm,
            ref_b.g_ov,
            ref_b.final_pp,
            ref_b.final_cm,
            ref_b.final_fm,
            ref_b.final_primary,
            ref_b.final_secondary,
        ),
        (
            ref_c.best_score,
            ref_c.surface_index,
            ref_c.g_pp,
            ref_c.g_cm,
            ref_c.g_fm,
            ref_c.g_ov,
            ref_c.final_pp,
            ref_c.final_cm,
            ref_c.final_fm,
            ref_c.final_primary,
            ref_c.final_secondary,
        ),
    ]


def test_response_frontier_gpu_preserves_exact_best_on_high_surface_mixed_colors_regression():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseSurface
    from tests.parity.fg_response_frontier_cpu import (
        optimize_response_frontier_inner_exact,
        optimize_response_frontier_inner_exact_gpu,
    )

    surfaces = (
        FgResponseSurface(3891411679, 3574856976, 3773757219, 1, 403555616, 720110319, 521210076, 14, 51, 5),
        FgResponseSurface(2721674337, 3070680269, 3611881923, 14, 0, 0, 327680, 0, 122, 2),
        FgResponseSurface(575176664, 3487862049, 3702577455, 12, 3719790631, 807105246, 592389840, 3, 84, 36),
        FgResponseSurface(3601089371, 3643850265, 2374545082, 10, 555465764, 642335206, 1920422149, 4, 109, 6),
        FgResponseSurface(2790863878, 2438334081, 1839177138, 4, 0, 0, 1, 0, 111, 3),
        FgResponseSurface(2245692434, 3544458849, 2717638093, 9, 405078720, 605573150, 1308631090, 0, 63, 27),
        FgResponseSurface(3466214601, 779693237, 2435483384, 1, 828752694, 3515274058, 1859483911, 14, 49, 82),
        FgResponseSurface(1358034363, 3210050518, 977655363, 13, 621019648, 524296, 77072408, 2, 67, 21),
        FgResponseSurface(27450701, 2000810147, 1294574002, 1, 168362000, 132612, 538069060, 2, 116, 12),
        FgResponseSurface(1302787120, 1853818885, 106666315, 9, 537461380, 2415952130, 279568, 6, 121, 3),
        FgResponseSurface(912726739, 3089068564, 3279260528, 5, 3382240556, 1205898731, 1015706767, 10, 3, 119),
    )
    kwargs = {
        "total_notes": 232,
        "residual_budget": 23,
        "stats_after_ftff": {
            "Perfect Points": 138,
            "Combo Multiplier": 14,
            "Fever Multiplier": 195,
            "Power": 269,
            "Rush": 266,
            "Flow": 13,
            "Beat": 111,
            "Vibe": 299,
            "Chill": 294,
        },
        "primary_color": "Vibe",
        "secondary_color": "Chill",
        "selected_color": "Beat",
        "ref_arrays": _ref_arrays(),
    }

    reference = optimize_response_frontier_inner_exact(surfaces, **kwargs)
    gpu = optimize_response_frontier_inner_exact_gpu(surfaces, **kwargs)

    assert gpu == reference
    assert gpu.best_score == 246965
    assert (gpu.surface_index, gpu.g_pp, gpu.g_cm, gpu.g_fm, gpu.g_ov) == (1, 11, 12, 0, 0)


def _strip_trailing_zero_counts(counts):
    out = tuple(int(v) for v in counts)
    while out and out[-1] == 0:
        out = out[:-1]
    return out


def test_response_frontier_exact_uses_natural_forced_great_cap_above_legacy_cap(tmp_path, monkeypatch):
    from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        solve_force_greats_response_frontier_batch_gpu,
    )

    rows = 161
    ref_arrays = {
        "Perfect Points": np.zeros(rows, dtype=np.float64),
        "Combo Multiplier": np.ones(rows, dtype=np.float64),
        "Fever Multiplier": np.full(rows, 4.0, dtype=np.float64),
        "Fever Fill Rate": np.ones(rows, dtype=np.float64),
        "Fever Time": np.ones(rows, dtype=np.float64),
    }
    timestamps = np.asarray(
        list(np.arange(28, dtype=float)) + [50.0 + i * 0.1 for i in range(32)],
        dtype=np.float32,
    )
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 10,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }

    baseline = evaluate_force_greats(base_stats, calc_song, ref_arrays, [0, 0])
    legacy_cap_best = max(
        int(evaluate_force_greats(base_stats, calc_song, ref_arrays, [forced, 0])["final_score"])
        for forced in range(16)
    )
    natural_best = int(evaluate_force_greats(base_stats, calc_song, ref_arrays, [17, 0])["final_score"])

    assert baseline["non_fever_base"] == 20
    assert natural_best > legacy_cap_best

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_stats], total_budget=0)
    result = solve_force_greats_response_frontier_batch_gpu(
        base_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=0,
    )

    assert result.best_score == natural_best
    assert _strip_trailing_zero_counts(result.forced_counts) == (17,)


def test_response_frontier_exact_reoptimizes_gems_against_bruteforce_reference(tmp_path, monkeypatch):
    import itertools

    from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        solve_force_greats_response_frontier_batch_gpu,
    )

    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 4.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    }
    timestamps = np.asarray(
        [0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6, 5.0, 5.1, 5.2],
        dtype=np.float32,
    )
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 20,
        "Flow": 15,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    selected_color = "Chill"
    budget = 4

    best_score = -1
    best_gems = None
    best_counts = ()
    for ft in range(budget + 1):
        for ff in range(budget - ft + 1):
            for pp in range(budget - ft - ff + 1):
                for cm in range(budget - ft - ff - pp + 1):
                    for fm in range(budget - ft - ff - pp - cm + 1):
                        ov = budget - ft - ff - pp - cm - fm
                        stats = apply_gems_to_base_stats(base_stats, selected_color, ft, ff, pp, cm, fm, ov)
                        zero = evaluate_force_greats(stats, calc_song, ref_arrays, [0] * 10)
                        sections = int(zero["num_non_fever_sections"])
                        cap = int(zero["non_fever_base"])
                        for counts in itertools.product(range(cap + 1), repeat=sections):
                            score = int(evaluate_force_greats(stats, calc_song, ref_arrays, counts)["final_score"])
                            if score > best_score:
                                best_score = score
                                best_gems = (ft, ff, pp, cm, fm, ov)
                                best_counts = counts

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_stats], total_budget=budget)
    result = solve_force_greats_response_frontier_batch_gpu(
        base_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        total_budget=budget,
    )

    assert result.best_score == best_score
    assert (result.ft, result.ff, result.inner.g_pp, result.inner.g_cm, result.inner.g_fm, result.inner.g_ov) == best_gems
    assert result.inner.g_fm == budget
    assert _strip_trailing_zero_counts(result.forced_counts) == _strip_trailing_zero_counts(best_counts)


def test_response_frontier_best_score_matches_exact_replay_final_score(tmp_path, monkeypatch):
    from gear_optimizer.solver.scoring.exact_rescore import (
        evaluate_force_greats_exact,
        score_force_greats_surface_base_exact,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        solve_force_greats_response_frontier_batch_gpu,
    )

    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 4.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    }
    timestamps = np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_stats = {
        "Perfect Points": 1,
        "Combo Multiplier": 2,
        "Fever Multiplier": 3,
        "Fever Fill Rate": 1,
        "Fever Time": 2,
        "Rush": 20,
        "Flow": 15,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_stats], total_budget=3)
    result = solve_force_greats_response_frontier_batch_gpu(
        base_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=3,
    )
    exact = evaluate_force_greats_exact(result.stats, calc_song, ref_arrays, list(result.forced_counts))
    base_score = score_force_greats_surface_base_exact(result.stats, calc_song, ref_arrays, result.surface)

    assert int(exact["final_score"]) == int(result.best_score)
    assert int(exact["base_score"]) == int(base_score)


def test_response_frontier_many_matches_individual_exact_solves(tmp_path, monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        solve_force_greats_response_frontier_batch_gpu,
        solve_force_greats_response_frontier_many_gpu,
    )

    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 5.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.6, dtype=np.float64),
        "Fever Time": np.full(rows, 0.4, dtype=np.float64),
    }
    timestamps = np.asarray([0.0, 0.3, 0.7, 1.4, 2.2, 3.0, 3.2, 3.4, 4.0], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_a = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 20,
        "Flow": 15,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    base_b = {**base_a, "Rush": 25, "Flow": 10, "Combo Multiplier": 3}

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_a, base_b], total_budget=3)
    many = solve_force_greats_response_frontier_many_gpu(
        base_stats_list=[base_a, base_b],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=3,
    )
    singles = [
        solve_force_greats_response_frontier_batch_gpu(
            base_stats=base,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            selected_color="Rush",
            total_budget=3,
        )
        for base in (base_a, base_b)
    ]

    assert [
        (result.best_score, result.ft, result.ff, result.gem_counts, result.forced_counts)
        for result in many
    ] == [
        (result.best_score, result.ft, result.ff, result.gem_counts, result.forced_counts)
        for result in singles
    ]


def test_response_frontier_many_fast_path_matches_individual_exact_solves_with_ft_element_overlap(tmp_path, monkeypatch):
    import itertools

    from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        solve_force_greats_response_frontier_many_gpu,
    )

    rows = 161
    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 5.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.6, dtype=np.float64),
        "Fever Time": np.full(rows, 0.4, dtype=np.float64),
    }
    timestamps = np.asarray([0.0, 0.3, 0.7, 1.4, 2.2, 3.0, 3.2, 3.4, 4.0], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    base_a = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 0,
        "Flow": 15,
        "Chill": 0,
        "Beat": 20,
        "Vibe": 0,
    }
    base_b = {**base_a, "Beat": 23, "Flow": 12, "Combo Multiplier": 3}

    budget = 3

    def brute_best_score(base_stats):
        best = -1
        for ft in range(budget + 1):
            for ff in range(budget - ft + 1):
                for pp in range(budget - ft - ff + 1):
                    for cm in range(budget - ft - ff - pp + 1):
                        for fm in range(budget - ft - ff - pp - cm + 1):
                            ov = budget - ft - ff - pp - cm - fm
                            stats = apply_gems_to_base_stats(base_stats, "Rush", ft, ff, pp, cm, fm, ov)
                            zero = evaluate_force_greats(stats, calc_song, ref_arrays, [0] * 10)
                            sections = int(zero["num_non_fever_sections"])
                            cap = int(zero["non_fever_base"])
                            for counts in itertools.product(range(cap + 1), repeat=sections):
                                score = int(evaluate_force_greats(stats, calc_song, ref_arrays, counts)["final_score"])
                                if score > best:
                                    best = score
        return int(best)

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_response_cache"))
    _prebuild_response_bundle(calc_song, ref_arrays, [base_a, base_b], total_budget=budget)
    results = solve_force_greats_response_frontier_many_gpu(
        base_stats_list=[base_a, base_b],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Rush",
        total_budget=budget,
        include_forced_counts=False,
    )

    assert [result.best_score for result in results] == [brute_best_score(base) for base in (base_a, base_b)]
