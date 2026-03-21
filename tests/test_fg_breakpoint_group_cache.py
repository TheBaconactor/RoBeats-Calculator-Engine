import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch


def _base_calc_song() -> dict:
    return {
        "metadata": {
            "Song Name": "FG Cache Song",
            "Difficulty": "Hard",
        },
        "song_data": {},
    }


def test_breakpoint_group_cache_reuses_identical_group_plan():
    with gpu_dispatch._FG_BREAKPOINT_GROUPS_LOCK:
        gpu_dispatch._FG_BREAKPOINT_GROUPS_CACHE.clear()

    calls = {"n": 0}

    def _compute():
        calls["n"] += 1
        return [
            {
                "ftff_pairs": [(0, 0), (1, 0)],
                "counts_list": [(0,), (1,)],
                "counts_max_fp": [],
                "section_breakpoints": ((0, 1),),
            }
        ]

    kwargs = dict(
        calc_song=_base_calc_song(),
        n_sections=1,
        ftff_pairs=[(0, 0), (1, 0)],
        base_stats_pairs=[(100, 100)],
        merge_threshold_cfgs=5000,
        merge_threshold_threads=20000000,
        n_genomes=8,
        gem_scale_fever=3,
        mode="cpu",
        compute_fn=_compute,
    )

    groups_1, hit_1 = gpu_dispatch._get_cached_breakpoint_groups(**kwargs)
    groups_2, hit_2 = gpu_dispatch._get_cached_breakpoint_groups(**kwargs)

    assert hit_1 is False
    assert hit_2 is True
    assert calls["n"] == 1
    assert groups_1 == groups_2
    assert groups_2[0]["ftff_pairs"] == [(0, 0), (1, 0)]


def test_breakpoint_group_cache_is_partitioned_by_hitsim_timing_context():
    with gpu_dispatch._FG_BREAKPOINT_GROUPS_LOCK:
        gpu_dispatch._FG_BREAKPOINT_GROUPS_CACHE.clear()

    calls = {"n": 0}

    def _compute():
        calls["n"] += 1
        return [
            {
                "ftff_pairs": [(0, 0)],
                "counts_list": [(0,)],
                "counts_max_fp": [],
                "section_breakpoints": ((0,),),
            }
        ]

    calc_song_a = _base_calc_song()
    calc_song_a["metadata"].update(
        {
            "HumanHitSimApplied": True,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimSeed": 11111,
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
        }
    )
    calc_song_b = _base_calc_song()
    calc_song_b["metadata"].update(
        {
            "HumanHitSimApplied": True,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimSeed": 11111,
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "late",
        }
    )

    common = dict(
        n_sections=1,
        ftff_pairs=[(0, 0)],
        base_stats_pairs=[(100, 100)],
        merge_threshold_cfgs=5000,
        merge_threshold_threads=20000000,
        n_genomes=8,
        gem_scale_fever=3,
        mode="cpu",
        compute_fn=_compute,
    )

    _groups_a, hit_a = gpu_dispatch._get_cached_breakpoint_groups(calc_song=calc_song_a, **common)
    _groups_b, hit_b = gpu_dispatch._get_cached_breakpoint_groups(calc_song=calc_song_b, **common)

    assert hit_a is False
    assert hit_b is False
    assert calls["n"] == 2


def test_max_fp_matrix_cache_reuses_identical_matrix():
    with gpu_dispatch._FG_MAX_FP_MATRIX_LOCK:
        gpu_dispatch._FG_MAX_FP_MATRIX_CACHE.clear()

    calls = {"n": 0}

    def _compute():
        calls["n"] += 1
        return np.asarray([[1, 2], [3, 4]], dtype=np.int16)

    kwargs = dict(
        calc_song=_base_calc_song(),
        n_sections=2,
        ftff_pairs=[(0, 0), (1, 0)],
        base_stats_pairs=[(100, 100)],
        gem_scale_fever=3,
        compute_fn=_compute,
    )

    matrix_1, hit_1 = gpu_dispatch._get_cached_max_fp_matrix(**kwargs)
    matrix_2, hit_2 = gpu_dispatch._get_cached_max_fp_matrix(**kwargs)

    assert hit_1 is False
    assert hit_2 is True
    assert calls["n"] == 1
    assert np.array_equal(matrix_1, matrix_2)

    matrix_1[0, 0] = 99
    matrix_3, hit_3 = gpu_dispatch._get_cached_max_fp_matrix(**kwargs)

    assert hit_3 is True
    assert int(matrix_3[0, 0]) == 1


def test_max_fp_matrix_cache_is_partitioned_by_hitsim_timing_context():
    with gpu_dispatch._FG_MAX_FP_MATRIX_LOCK:
        gpu_dispatch._FG_MAX_FP_MATRIX_CACHE.clear()

    calls = {"n": 0}

    def _compute():
        calls["n"] += 1
        return np.asarray([[5]], dtype=np.int16)

    calc_song_a = _base_calc_song()
    calc_song_a["metadata"].update(
        {
            "HumanHitSimApplied": True,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimSeed": 22222,
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
        }
    )
    calc_song_b = _base_calc_song()
    calc_song_b["metadata"].update(
        {
            "HumanHitSimApplied": True,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimSeed": 22222,
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "late",
        }
    )

    common = dict(
        n_sections=1,
        ftff_pairs=[(0, 0)],
        base_stats_pairs=[(100, 100)],
        gem_scale_fever=3,
        compute_fn=_compute,
    )

    _matrix_a, hit_a = gpu_dispatch._get_cached_max_fp_matrix(calc_song=calc_song_a, **common)
    _matrix_b, hit_b = gpu_dispatch._get_cached_max_fp_matrix(calc_song=calc_song_b, **common)

    assert hit_a is False
    assert hit_b is False
    assert calls["n"] == 2
