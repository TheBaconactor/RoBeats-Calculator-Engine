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


def _explicit_plateau_rows(max_fp: tuple[int, ...], n_sections: int) -> list[tuple[int, ...]]:
    ranges = [range(0, int(v) + 1) for v in max_fp[: int(n_sections)]]
    return [tuple(int(v) for v in base) for base in itertools.product(*ranges)]


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
@pytest.mark.parametrize(
    ("n_sections", "max_fp"),
    [
        (3, (2, 1, 1)),
        (4, (1, 1, 1, 1)),
    ],
)
def test_fg_counts_max_fp_rectangles_are_rejected(n_sections: int, max_fp: tuple[int, ...]):
    """
    Max-FP rectangles were replaced by the cap-free GPU prefix frontier descriptor.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import solve_force_greats_finder_gpu_tasks

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

    implicit_task = {"counts_max_fp": list(max_fp), "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}

    with pytest.raises(ValueError, match="counts_max_fp rectangles were removed"):
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


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_gpu_config_signature_dedupe_is_lossless_and_reduces_reps():
    """
    The exact timeline-signature reducer must preserve the winner and compact
    live representatives so Stage 1 cannot score dominated/dead surfaces.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats import api as fg_api
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields

    timestamps = np.linspace(0.0, 10.0, 24, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    genome_stats_arr = np.array([[100, 100, 100, 200, 120, 80, 80]], dtype=np.int32)
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

    max_fp = (8, 8)
    cfg_len = 1
    for v in max_fp:
        cfg_len *= int(v) + 1
    counts_list = _explicit_plateau_rows(max_fp, len(max_fp))
    baseline_task = {"counts_list": counts_list, "ftff_pairs": [(0, 0)], "base_cfg_offset": 0}

    fg_api.fg_reset_global_best(n_genomes)
    fg_api.solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        long_notes,
        last_note_time,
        fg_tasks=[baseline_task],
        n_sections=len(max_fp),
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )
    baseline = fg_api.fg_download_global_best(n_genomes)

    rep_count = int(fg_fields.fg_cfg_dedupe_rep_count.to_numpy()[0])
    active = int(fg_fields.fg_cfg_dedupe_active.to_numpy()[0])
    dedupe_slots = max(1, int(cfg_len))
    rep_idx = fg_fields.fg_cfg_dedupe_rep_cfg_idx.to_numpy()[0, :dedupe_slots]
    rep_hash = fg_fields.fg_cfg_dedupe_hash.to_numpy()[0, :dedupe_slots]

    assert active == 1
    assert 0 < rep_count < cfg_len
    assert np.all(rep_idx[:rep_count] >= 0)
    assert np.all(rep_idx[rep_count:] == -1)
    assert int(np.count_nonzero(rep_hash[:rep_count])) == rep_count
    assert int(np.count_nonzero(rep_hash[rep_count:])) == 0
    assert "final_score" in baseline
