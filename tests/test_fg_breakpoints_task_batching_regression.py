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
def test_fg_gpu_tasks_batching_allows_prefix_frontier_without_counts_list(monkeypatch, tmp_path):
    """
    Regression: when batching fg_tasks, some tasks provide only the prefix-frontier descriptor
    and omit counts_list. The batching submit must still run and allow a global download.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.prefix_frontier_prebuild import (
        prebuild_fg_prefix_frontier_cache,
    )

    monkeypatch.setenv("FG_PREFIX_FRONTIER_CACHE_DIR", str(tmp_path))
    # Small deterministic song
    timestamps = np.linspace(0.0, 10.0, 40, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    genome_stats_arr = np.array(
        [
            [100, 100, 100, 200, 120, 0, 0],
            [120, 90, 110, 180, 140, 0, 0],
            [80, 130, 95, 220, 110, 0, 0],
            [95, 105, 115, 210, 125, 0, 0],
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
    descriptor = {"mode": "gpu", "n_sections": 3, "song_slot": 0, "gem_scale_fever": 3}
    task_list = {"counts_max_fp": descriptor, "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}
    task_np = {"counts_max_fp": descriptor, "ftff_pairs": ftff_pairs_np, "base_cfg_offset": 0}

    prebuild_fg_prefix_frontier_cache(
        {
            "metadata": {"Song Name": "fg-task-batching-test", "Long Notes": 0, "Last Note Time": last_note_time},
            "song_data": {"timestamps": timestamps},
        },
        ref_arrays,
        n_sections_values=(3,),
        stat_max=3,
    )

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


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_prefix_frontier_prebuild_disk_cache_skips_live_rebuild(monkeypatch, tmp_path):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import api as fg_api
    from gear_optimizer.solver.taichi_gem.force_greats import prefix_frontier_cache
    from gear_optimizer.solver.taichi_gem.force_greats.prefix_frontier_prebuild import (
        prebuild_fg_prefix_frontier_cache,
    )

    monkeypatch.setenv("FG_PREFIX_FRONTIER_CACHE_DIR", str(tmp_path))
    timestamps = np.linspace(0.0, 10.0, 40, dtype=np.float32)
    genome_stats_arr = np.array([[100, 100, 100, 200, 120, 0, 0]], dtype=np.int32)
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
    task = {
        "counts_max_fp": {"mode": "gpu", "n_sections": 2, "song_slot": 0, "gem_scale_fever": 3},
        "ftff_pairs": [(0, 0)],
        "base_cfg_offset": 0,
    }

    calc_song = {
        "metadata": {"Song Name": "fg-prefix-prebuild-test", "Long Notes": 0, "Last Note Time": float(timestamps[-1])},
        "song_data": {"timestamps": timestamps},
    }

    fg_api.fg_reset_global_best(len(genome_stats_arr))
    prebuild_fg_prefix_frontier_cache(
        calc_song,
        ref_arrays,
        n_sections_values=(2,),
        stat_max=0,
    )
    prebuild_only = fg_api.fg_download_global_best(len(genome_stats_arr))
    np.testing.assert_array_equal(prebuild_only["final_score"], np.asarray([-1], dtype=np.int32))
    assert list(tmp_path.glob("*.sqlite3"))
    assert not list(tmp_path.glob("*.npz"))

    with prefix_frontier_cache._FG_PREFIX_FRONTIER_LOCK:
        prefix_frontier_cache._FG_PREFIX_FRONTIER_CACHE.clear()

    def fail_rebuild(*args, **kwargs):
        raise AssertionError("prefix frontier cache miss rebuilt the frontier")

    monkeypatch.setattr(fg_api.fg_kernels, "fg_stage1_prefix_frontier_kernel", fail_rebuild)
    fg_api.fg_reset_global_best(len(genome_stats_arr))
    fg_api.solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        0,
        float(timestamps[-1]),
        fg_tasks=[task],
        n_sections=2,
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )
    out = fg_api.fg_download_global_best(len(genome_stats_arr))

    assert int(out["final_score"][0]) >= 0
