import os
import sys

import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


def _make_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    rows = int(TOTAL_ROWS) + 1
    x = np.linspace(0.0, 1.0, rows, dtype=np.float64)
    return {
        "Perfect Points": 1.0 + 0.5 * x,
        "Combo Multiplier": 1.0 + 2.0 * x,
        "Fever Multiplier": 1.0 + 4.0 * x,
        "Fever Fill Rate": 1.0 + 0.8 * x,
        "Fever Time": 1.0 + 1.2 * x,
    }


def _make_genome_stats(n: int, seed: int = 1337) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    arr = np.zeros((int(n), 7), dtype=np.int32)
    arr[:, 0] = rng.integers(80, 140, size=n, dtype=np.int32)
    arr[:, 1] = rng.integers(80, 140, size=n, dtype=np.int32)
    arr[:, 2] = rng.integers(80, 160, size=n, dtype=np.int32)
    arr[:, 3] = rng.integers(140, 280, size=n, dtype=np.int32)
    arr[:, 4] = rng.integers(140, 280, size=n, dtype=np.int32)
    arr[:, 5] = rng.integers(0, 60, size=n, dtype=np.int32)
    arr[:, 6] = rng.integers(0, 60, size=n, dtype=np.int32)
    return arr


def _assert_equal_dict_arrays(a: dict[str, np.ndarray], b: dict[str, np.ndarray]) -> None:
    assert set(a.keys()) == set(b.keys())
    for key in a:
        av = a[key]
        bv = b[key]
        assert isinstance(av, np.ndarray)
        assert isinstance(bv, np.ndarray)
        assert av.shape == bv.shape
        assert np.array_equal(av, bv), f"Mismatch for key={key}"


def test_fg_gpu_race_repeatability_batched_vs_sequential():
    """
    Race/determinism check for ForceGreats GPU:
    - Repeated batched runs yield identical global-best outputs.
    - Repeated sequential runs yield identical global-best outputs.
    - Batched == sequential results.
    """
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu,
        solve_force_greats_finder_gpu_tasks,
    )

    timestamps = np.linspace(0.0, 60.0, 120, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    genome_stats_arr = _make_genome_stats(128, seed=1337)
    n_genomes = int(genome_stats_arr.shape[0])

    ref_arrays = _make_ref_arrays()

    flags = dict(
        is_p_ft=0,
        is_s_ft=0,
        is_p_ff=0,
        is_s_ff=0,
        is_p_pp=0,
        is_s_pp=0,
        is_p_cm=0,
        is_s_cm=0,
        is_p_fm=0,
        is_s_fm=0,
        is_p_ov=1,
        is_s_ov=0,
    )

    tasks = [
        {
            "counts_list": [(0, 0), (1, 0), (0, 1), (1, 1)],
            "ftff_pairs": [(0, 0), (1, 0)],
            "base_cfg_offset": 0,
        },
        {
            "counts_list": [(2, 0), (0, 2), (2, 2)],
            "ftff_pairs": [(0, 1), (1, 1)],
            "base_cfg_offset": 4,
        },
        {
            "counts_list": [(3, 1), (1, 3), (3, 3)],
            "ftff_pairs": [(0, 0), (1, 1)],
            "base_cfg_offset": 7,
        },
    ]

    def _run_batched() -> dict[str, np.ndarray]:
        fg_reset_global_best(n_genomes)
        solve_force_greats_finder_gpu_tasks(
            genome_stats_arr,
            timestamps,
            None,
            long_notes,
            last_note_time,
            fg_tasks=tasks,
            n_sections=2,
            ref_arrays=ref_arrays,
            return_raw=True,
            accumulate_global=True,
            **flags,
        )
        return fg_download_global_best(n_genomes)

    def _run_sequential() -> dict[str, np.ndarray]:
        fg_reset_global_best(n_genomes)
        for task in tasks:
            solve_force_greats_finder_gpu(
                genome_stats_arr,
                timestamps,
                None,
                long_notes,
                last_note_time,
                task["counts_list"],
                task["ftff_pairs"],
                n_sections=2,
                ref_arrays=ref_arrays,
                return_raw=True,
                accumulate_global=True,
                base_cfg_offset=int(task["base_cfg_offset"]),
                **flags,
            )
        return fg_download_global_best(n_genomes)

    batched = _run_batched()
    for _ in range(2):
        _assert_equal_dict_arrays(batched, _run_batched())

    sequential = _run_sequential()
    for _ in range(2):
        _assert_equal_dict_arrays(sequential, _run_sequential())

    _assert_equal_dict_arrays(batched, sequential)
