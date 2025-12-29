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
def test_solve_force_greats_finder_gpu_cfg_chunk_invariant():
    """
    Regression test: FG finder GPU result must be invariant to cfg_chunk.

    This specifically guards against a bug where Stage 1 overwrote per-(genome,ftff)
    bests when configs were uploaded in multiple chunks.
    """
    from gear_optimizer.solver.taichi_gem_solver import solve_force_greats_finder_gpu
    from gear_optimizer.core.constants import TOTAL_ROWS

    # Simple deterministic song
    timestamps = np.linspace(0.0, 120.0, 180, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    # One genome is enough to catch the overwrite bug
    genome_stats_list = [
        {
            "base_pp": 100,
            "base_cm": 100,
            "base_fm": 100,
            "base_ft_stat": 80,
            "base_ff_stat": 80,
            "base_p_val": 200,
            "base_s_val": 120,
        }
    ]

    # Keep FT/FF search tiny for speed
    ftff_pairs = [(0, 0)]

    # Build a config list where the best (lowest penalties) is early, and the last chunk is worse.
    # With a broken chunk reduction, the solver can incorrectly pick from the last chunk only.
    fg_configs = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for k in range(6, 16):
        fg_configs.append((k, k))

    # Minimal reference arrays (must include FT/FF)
    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

    # Flags: keep mapping simple/deterministic
    flags = dict(
        is_p_ft=0, is_s_ft=0,
        is_p_ff=0, is_s_ff=0,
        is_p_pp=0, is_s_pp=0,
        is_p_cm=0, is_s_cm=0,
        is_p_fm=0, is_s_fm=0,
        is_p_ov=1, is_s_ov=0,
    )

    # Force chunking (multiple cfg uploads)
    res_small = solve_force_greats_finder_gpu(
        genome_stats_list,
        timestamps,
        None,  # great_candidate_timestamps_np (optional)
        long_notes,
        last_note_time,
        fg_configs,
        ftff_pairs,
        n_sections=2,
        ref_arrays=ref_arrays,
        cfg_chunk=4,
        **flags,
    )

    # Single chunk
    res_large = solve_force_greats_finder_gpu(
        genome_stats_list,
        timestamps,
        None,  # great_candidate_timestamps_np (optional)
        long_notes,
        last_note_time,
        fg_configs,
        ftff_pairs,
        n_sections=2,
        ref_arrays=ref_arrays,
        cfg_chunk=99999,
        **flags,
    )

    assert len(res_small) == len(res_large) == 1
    a = res_small[0]
    b = res_large[0]

    # Exact invariance required
    assert int(a.get("final_score", -1)) == int(b.get("final_score", -2))
    assert int(a.get("base_score", -1)) == int(b.get("base_score", -2))
    assert int(a.get("cfg_idx", -1)) == int(b.get("cfg_idx", -2))
    assert int(a.get("FT", -1)) == int(b.get("FT", -2))
    assert int(a.get("FF", -1)) == int(b.get("FF", -2))
    assert (a.get("gem_counts") or {}) == (b.get("gem_counts") or {})


