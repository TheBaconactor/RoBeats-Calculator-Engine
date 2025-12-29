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


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_solve_force_greats_finder_gpu_tasks_matches_sequential_accumulation():
    """
    Regression test: batched FG tasks must match sequential accumulate_global calls.

    This guards against performance refactors that change host->device upload behavior
    (e.g., skipping genome_base_stats uploads) and accidentally alter correctness.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu,
        solve_force_greats_finder_gpu_tasks,
    )

    # Deterministic synthetic song
    timestamps = np.linspace(0.0, 120.0, 180, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    # 4 genomes with distinct stats (shape: (n_genomes, 7))
    genome_stats_arr = np.array(
        [
            [100, 100, 100, 200, 120, 80, 80],
            [120, 90, 110, 180, 140, 75, 85],
            [80, 130, 95, 220, 110, 90, 70],
            [95, 105, 115, 210, 125, 82, 78],
        ],
        dtype=np.int32,
    )
    n_genomes = int(genome_stats_arr.shape[0])

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

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

    # Three tasks with different config lists, ftff pairs, and cfg offsets.
    tasks = [
        {
            "counts_list": [(0, 0), (1, 0), (0, 1), (1, 1)],
            "ftff_pairs": [(0, 0)],
            "base_cfg_offset": 0,
        },
        {
            "counts_list": [(2, 0), (0, 2), (2, 2)],
            "ftff_pairs": [(1, 0), (0, 1)],
            "base_cfg_offset": 10,
        },
        {
            "counts_list": [(3, 1), (1, 3), (3, 3)],
            "ftff_pairs": [(0, 0), (1, 1)],
            "base_cfg_offset": 20,
        },
    ]

    # Sequential accumulation baseline
    fg_reset_global_best(n_genomes)
    for t in tasks:
        solve_force_greats_finder_gpu(
            genome_stats_arr,
            timestamps,
            None,  # great_candidate_timestamps_np
            long_notes,
            last_note_time,
            t["counts_list"],
            t["ftff_pairs"],
            n_sections=2,
            ref_arrays=ref_arrays,
            return_raw=True,
            accumulate_global=True,
            base_cfg_offset=int(t["base_cfg_offset"]),
            **flags,
        )
    seq = fg_download_global_best(n_genomes)

    # Batched tasks path
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,  # great_candidate_timestamps_np
        long_notes,
        last_note_time,
        fg_tasks=tasks,
        n_sections=2,
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )
    batched = fg_download_global_best(n_genomes)

    assert set(seq.keys()) == set(batched.keys())
    for k in seq:
        a = seq[k]
        b = batched[k]
        assert isinstance(a, np.ndarray)
        assert isinstance(b, np.ndarray)
        assert a.shape == b.shape
        assert np.array_equal(a, b), f"Mismatch for key={k}"
