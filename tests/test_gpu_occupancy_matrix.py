from tools.bench.bench_gpu_occupancy_matrix import (
    build_fg_sweep_cases,
    build_ga_sweep_cases,
    parse_csv_ints,
    parse_csv_strings,
    rank_fg_results,
    rank_ga_results,
)


def test_parse_csv_ints_parses_and_strips_values():
    assert parse_csv_ints("128, 256,0") == [128, 256, 0]


def test_parse_csv_strings_normalizes_and_strips_values():
    assert parse_csv_strings("none, Results ,update_global") == ["none", "results", "update_global"]


def test_build_ga_sweep_cases_cross_products_env_matrix():
    cases = build_ga_sweep_cases(
        taichi_block_dims=[128, 256],
        reduce_block_dims=[128],
        batch_runs=[0, 2],
        materialize_modes=["none", "update_global"],
    )

    assert [case["label"] for case in cases] == [
        "taichi128_reduce128_batch0_mode_none",
        "taichi128_reduce128_batch0_mode_update_global",
        "taichi128_reduce128_batch2_mode_none",
        "taichi128_reduce128_batch2_mode_update_global",
        "taichi256_reduce128_batch0_mode_none",
        "taichi256_reduce128_batch0_mode_update_global",
        "taichi256_reduce128_batch2_mode_none",
        "taichi256_reduce128_batch2_mode_update_global",
    ]
    assert cases[0]["env"] == {
        "TAICHI_BLOCK_DIM": 128,
        "GA_FTFF_REDUCE_BLOCK_DIM": 128,
        "GPU_NATIVE_GA_BATCH_RUNS": 0,
    }
    assert cases[1]["materialize_mode"] == "update_global"


def test_build_fg_sweep_cases_cross_products_env_matrix():
    cases = build_fg_sweep_cases(stage1_block_dims=[64, 128], target_threads=[2_000_000])

    assert [case["label"] for case in cases] == [
        "stage1_64_threads_2000000",
        "stage1_128_threads_2000000",
    ]
    assert cases[1]["env"] == {
        "FG_STAGE1_BLOCK_DIM": 128,
        "FG_TARGET_THREADS_PER_KERNEL": 2_000_000,
    }


def test_rank_ga_results_prefers_higher_iters_per_sec():
    ranked = rank_ga_results(
        [
            {"label": "slow", "iters_per_sec": 100.0},
            {"label": "fast", "iters_per_sec": 150.0},
        ]
    )

    assert [item["label"] for item in ranked] == ["fast", "slow"]


def test_rank_fg_results_prefers_higher_steady_iters_per_sec():
    ranked = rank_fg_results(
        [
            {"label": "slow", "steady_iters_per_sec": 0.20},
            {"label": "fast", "steady_iters_per_sec": 0.25},
        ]
    )

    assert [item["label"] for item in ranked] == ["fast", "slow"]
