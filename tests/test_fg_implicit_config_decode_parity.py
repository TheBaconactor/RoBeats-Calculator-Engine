import os
import sys
import itertools

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
@pytest.mark.parametrize(
    ("n_sections", "max_fp"),
    [
        (3, (2, 1, 1)),  # hits the <=3-sections fast path
        (4, (1, 1, 1, 1)),  # hits the general kernel path
    ],
)
def test_fg_counts_max_fp_implicit_toggle_invariant(
    monkeypatch: pytest.MonkeyPatch, n_sections: int, max_fp: tuple[int, ...]
):
    """
    Strong parity: counts_max_fp tasks must produce identical results with and without implicit config decode.

    - FG_IMPLICIT_CONFIGS=0: configs are generated into fg_forced_counts and read by Stage 1.
    - FG_IMPLICIT_CONFIGS=1: Stage 1 decodes FP targets implicitly (no cfg table writes/reads).
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )

    # Deterministic synthetic song
    timestamps = np.linspace(0.0, 120.0, 180, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    # A few distinct genomes (shape: (n_genomes, 7))
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

    ftff_pairs = [(0, 0), (1, 0), (0, 1)]
    task = {"counts_max_fp": list(max_fp), "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}

    # Table-backed counts_max_fp (explicit cfg generation + read)
    monkeypatch.setenv("FG_IMPLICIT_CONFIGS", "0")
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,  # great_candidate_timestamps_np
        long_notes,
        last_note_time,
        fg_tasks=[task],
        n_sections=int(n_sections),
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )
    explicit = fg_download_global_best(n_genomes)

    # Implicit counts_max_fp (no cfg table writes/reads)
    monkeypatch.setenv("FG_IMPLICIT_CONFIGS", "1")
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,  # great_candidate_timestamps_np
        long_notes,
        last_note_time,
        fg_tasks=[task],
        n_sections=int(n_sections),
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )
    implicit = fg_download_global_best(n_genomes)

    assert set(explicit.keys()) == set(implicit.keys())
    for k in explicit:
        a = explicit[k]
        b = implicit[k]
        assert isinstance(a, np.ndarray)
        assert isinstance(b, np.ndarray)
        assert a.shape == b.shape
        assert np.array_equal(a, b), f"Mismatch for key={k}"


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
@pytest.mark.parametrize(
    ("n_sections", "max_fp"),
    [
        (3, (2, 1, 1)),
        (4, (1, 1, 1, 1)),
    ],
)
def test_fg_counts_max_fp_implicit_matches_explicit_counts_list(
    monkeypatch: pytest.MonkeyPatch, n_sections: int, max_fp: tuple[int, ...]
):
    """
    Strong parity: implicit mixed-radix decode must match explicit itertools.product ordering.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )

    timestamps = np.linspace(0.0, 120.0, 180, dtype=np.float32)
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

    ftff_pairs = [(0, 0), (1, 0)]

    ranges = [range(0, int(v) + 1) for v in max_fp[: int(n_sections)]]
    counts_list = list(itertools.product(*ranges))

    explicit_task = {"counts_list": counts_list, "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}
    implicit_task = {"counts_max_fp": list(max_fp), "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}

    # Explicit config table (counts_list)
    monkeypatch.setenv("FG_IMPLICIT_CONFIGS", "1")
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        long_notes,
        last_note_time,
        fg_tasks=[explicit_task],
        n_sections=int(n_sections),
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )
    explicit = fg_download_global_best(n_genomes)

    # Implicit decode (counts_max_fp)
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        long_notes,
        last_note_time,
        fg_tasks=[implicit_task],
        n_sections=int(n_sections),
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )
    implicit = fg_download_global_best(n_genomes)

    assert set(explicit.keys()) == set(implicit.keys())
    for k in explicit:
        a = explicit[k]
        b = implicit[k]
        assert isinstance(a, np.ndarray)
        assert isinstance(b, np.ndarray)
        assert a.shape == b.shape
        assert np.array_equal(a, b), f"Mismatch for key={k}"
