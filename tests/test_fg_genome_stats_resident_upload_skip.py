import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_tasks_can_skip_genome_stats_upload_when_resident():
    """
    Ensure `solve_force_greats_finder_gpu_tasks(..., upload_genome_stats=False)` preserves behavior
    when reusing the same numpy genome_stats buffer pointer.
    """
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )

    # Synthetic tiny chart (exact f32).
    n_notes = 3000
    ts = (np.arange(n_notes, dtype=np.float32) * np.float32(0.125)).astype(np.float32)
    calc_last = float(ts[-1])

    ref_arrays = {
        "Fever Time": np.linspace(0.8, 1.2, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.8, 1.8, 161, dtype=np.float32),
        "Perfect Points": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }

    # One genome, reused numpy buffer pointer.
    genome = np.zeros((1, 7), dtype=np.int32)
    genome[0, :] = [100, 100, 100, 100, 100, 80, 80]

    # Minimal FG tasks (rectangular).
    task = {"counts_max_fp": [2, 2], "ftff_pairs": [(0, 0), (5, 0)], "base_cfg_offset": 0}

    # Run once with upload.
    fg_reset_global_best(1)
    solve_force_greats_finder_gpu_tasks(
        genome,
        ts,
        None,
        0,
        calc_last,
        fg_tasks=[task],
        n_sections=2,
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
        is_p_ov=0,
        is_s_ov=0,
        ref_arrays=ref_arrays,
        song_slot=0,
        accumulate_global=True,
        return_raw=True,
        upload_genome_stats=True,
    )
    r1 = fg_download_global_best(1)

    # Run again, skipping upload (should be identical).
    fg_reset_global_best(1)
    solve_force_greats_finder_gpu_tasks(
        genome,
        ts,
        None,
        0,
        calc_last,
        fg_tasks=[task],
        n_sections=2,
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
        is_p_ov=0,
        is_s_ov=0,
        ref_arrays=ref_arrays,
        song_slot=0,
        accumulate_global=True,
        return_raw=True,
        upload_genome_stats=False,
    )
    r2 = fg_download_global_best(1)

    assert int(r1["final_score"][0]) == int(r2["final_score"][0])
    assert int(r1["cfg_idx"][0]) == int(r2["cfg_idx"][0])

