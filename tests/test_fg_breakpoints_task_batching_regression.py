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
def test_fg_gpu_tasks_batching_allows_counts_max_fp_without_counts_list():
    """
    Regression: when batching fg_tasks, some tasks provide only counts_max_fp (implicit configs)
    and omit counts_list. The batching submit must still run and allow a global download.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )

    # Small deterministic song
    timestamps = np.linspace(0.0, 10.0, 40, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

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

    ftff_pairs = [(0, 0), (1, 0)]
    ftff_pairs_np = np.asarray(ftff_pairs, dtype=np.int32)

    # Intentionally omit counts_list; this used to break batching submit logic.
    task_list = {"counts_max_fp": [0, 0, 0], "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}
    task_np = {"counts_max_fp": [0, 0, 0], "ftff_pairs": ftff_pairs_np, "base_cfg_offset": 0}

    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        long_notes,
        last_note_time,
        fg_tasks=[task_list, task_np],
        n_sections=3,
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )

    out = fg_download_global_best(n_genomes)
    assert isinstance(out, dict)
    assert "final_score" in out
    assert np.asarray(out["final_score"]).shape == (n_genomes,)
