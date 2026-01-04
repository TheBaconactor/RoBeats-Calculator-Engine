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
def test_fg_gpu_tasks_handles_more_than_4096_configs_without_overflow():
    """
    Regression: packed-task FG path must handle counts_list > 4096.

    Historical failure:
      IndexError: index 4096 is out of bounds for axis 0 with size 4096

    This guards the chunked upload logic in solve_force_greats_finder_gpu_tasks().
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu,
        solve_force_greats_finder_gpu_tasks,
    )

    # Deterministic synthetic song (small to keep runtime reasonable)
    timestamps = np.linspace(0.0, 45.0, 90, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    genome_stats_arr = np.array(
        [
            [100, 100, 100, 200, 120, 80, 80],
            [120, 90, 110, 180, 140, 75, 85],
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

    # Force config list over the 4096 staging row cap.
    # Values are small "fill penalty target" integers; duplicates are fine for this regression.
    cfg_len = 5000
    counts_list = [((i % 16), ((i // 16) % 16)) for i in range(cfg_len)]
    ftff_pairs = [(0, 0)]

    # Sequential baseline (single task, accumulate_global)
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu(
        genome_stats_arr,
        timestamps,
        None,
        long_notes,
        last_note_time,
        counts_list,
        ftff_pairs,
        n_sections=2,
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        base_cfg_offset=0,
        **flags,
    )
    seq = fg_download_global_best(n_genomes)

    # Packed-task path must match and must not overflow staging buffers.
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        long_notes,
        last_note_time,
        fg_tasks=[{"counts_list": counts_list, "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}],
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
