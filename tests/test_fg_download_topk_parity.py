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
def test_fg_global_best_topk_selection_matches_cpu_sort(monkeypatch: pytest.MonkeyPatch):
    """
    Strong parity: GPU-side top-K global_best selection must match CPU sorting/filtering.

    Selection rules:
    - keep_mask indices are always included first (ascending index)
    - remaining candidates are sorted by final_score desc, tie-break by lower genome index
    - eligibility: final_score > base_scores AND fill_penalty > 0
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )

    # Keep this test stable regardless of user env defaults.
    monkeypatch.setenv("FG_IMPLICIT_CONFIGS", "1")

    # Deterministic synthetic song
    timestamps = np.linspace(0.0, 120.0, 180, dtype=np.float32)
    long_notes = 0
    last_note_time = float(timestamps[-1])

    # Random-ish but deterministic genomes (shape: (n_genomes, 7))
    n_genomes = 32
    rng = np.random.default_rng(1234)
    genome_stats_arr = np.zeros((n_genomes, 7), dtype=np.int32)
    genome_stats_arr[:, 0] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 1] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 2] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 3] = rng.integers(150, 240, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 4] = rng.integers(100, 160, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 5] = rng.integers(60, 100, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 6] = rng.integers(60, 100, size=n_genomes, dtype=np.int32)

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

    # Small-ish task: enough to produce a meaningful distribution of scores.
    counts_list = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
    ftff_pairs = [(0, 0), (1, 0), (0, 1), (2, 0)]
    task = {"counts_list": counts_list, "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}

    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        long_notes,
        last_note_time,
        fg_tasks=[task],
        n_sections=3,
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )

    full = fg_download_global_best(n_genomes)
    full_final = np.asarray(full["final_score"], dtype=np.int32)
    full_fill = np.asarray(full["fill_penalty"], dtype=np.int32)

    # Construct base_scores/keep_mask to exercise all branches.
    base_scores = np.asarray(full["base_score"], dtype=np.int32).copy()
    base_scores[::3] = full_final[::3]  # force some ineligible by score

    keep_mask = np.zeros((n_genomes,), dtype=np.int32)
    keep_mask[0] = 1
    keep_mask[5] = 1

    topk = 8

    # Expected CPU selection
    keep_idx = [i for i in range(n_genomes) if int(keep_mask[i]) != 0]
    eligible = [
        i
        for i in range(n_genomes)
        if int(keep_mask[i]) == 0 and int(full_final[i]) > int(base_scores[i]) and int(full_fill[i]) > 0
    ]
    eligible_sorted = sorted(eligible, key=lambda i: (-int(full_final[i]), int(i)))
    expected = keep_idx + eligible_sorted[:topk]

    selected = fg_download_global_best(n_genomes, topk=topk, base_scores=base_scores, keep_mask=keep_mask)
    sel_idx = np.asarray(selected["selected_indices"], dtype=np.int32)

    assert sel_idx.tolist() == expected

    # Packed fields must match the full download at selected indices.
    for k in (
        "final_score",
        "base_score",
        "cfg_idx",
        "FT",
        "FF",
        "g_pp",
        "g_cm",
        "g_fm",
        "g_ov",
        "score_penalty",
        "fill_penalty",
    ):
        got = np.asarray(selected[k])
        exp = np.asarray(full[k])[sel_idx]
        assert np.array_equal(got, exp), f"Mismatch for key={k}"
