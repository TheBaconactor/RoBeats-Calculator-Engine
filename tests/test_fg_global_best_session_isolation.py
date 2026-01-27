import numpy as np
import pytest


@pytest.mark.gpu
def test_fg_global_best_isolated_by_session_slot() -> None:
    """
    Regression guard: FG "global best" accumulation must not mix across in-flight sessions.

    We intentionally write different best buffers into two different session/song slots and
    verify downloads return the per-slot values.
    """
    from gear_optimizer.solver.taichi_gem import fields as gem_fields
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels
    from gear_optimizer.solver.taichi_gem.force_greats.api import fg_download_global_best, fg_reset_global_best

    fg_fields.ensure_ready_with_warmup()

    if int(getattr(gem_fields, "MAX_SONG_SLOTS", 0) or 0) < 2:
        pytest.skip("MAX_SONG_SLOTS < 2; cannot validate multi-slot global-best isolation")

    n = 8
    max_g = int(getattr(gem_fields, "MAX_GENOMES", 0) or 0)
    assert max_g >= n

    def _upload_best(scores: np.ndarray, base: np.ndarray, fill_penalty: np.ndarray) -> None:
        # Fields are (MAX_GENOMES,) and must be uploaded as padded arrays.
        fg_fields.fg_best_final_score.from_numpy(scores)
        fg_fields.fg_best_base_score.from_numpy(base)
        fg_fields.fg_best_cfg_idx.from_numpy(np.arange(max_g, dtype=np.int32))
        fg_fields.fg_best_ft.from_numpy(np.zeros((max_g,), dtype=np.int32))
        fg_fields.fg_best_ff.from_numpy(np.zeros((max_g,), dtype=np.int32))
        fg_fields.fg_best_g_pp.from_numpy(np.zeros((max_g,), dtype=np.int32))
        fg_fields.fg_best_g_cm.from_numpy(np.zeros((max_g,), dtype=np.int32))
        fg_fields.fg_best_g_fm.from_numpy(np.zeros((max_g,), dtype=np.int32))
        fg_fields.fg_best_g_ov.from_numpy(np.zeros((max_g,), dtype=np.int32))
        fg_fields.fg_best_score_penalty.from_numpy(np.zeros((max_g,), dtype=np.int32))
        fg_fields.fg_best_fill_penalty.from_numpy(fill_penalty)

    # Slot 0: scores 100..107
    scores0 = np.full((max_g,), -1, dtype=np.int32)
    base0 = np.zeros((max_g,), dtype=np.int32)
    fill0 = np.zeros((max_g,), dtype=np.int32)
    scores0[:n] = np.arange(100, 100 + n, dtype=np.int32)
    base0[:n] = 1
    fill0[:n] = 1

    fg_reset_global_best(n, session_slot=0)
    _upload_best(scores0, base0, fill0)
    fg_kernels.fg_update_global_best_kernel(0, n)

    # Slot 1: scores 200..207 (distinct)
    scores1 = np.full((max_g,), -1, dtype=np.int32)
    base1 = np.zeros((max_g,), dtype=np.int32)
    fill1 = np.zeros((max_g,), dtype=np.int32)
    scores1[:n] = np.arange(200, 200 + n, dtype=np.int32)
    base1[:n] = 1
    fill1[:n] = 1

    fg_reset_global_best(n, session_slot=1)
    _upload_best(scores1, base1, fill1)
    fg_kernels.fg_update_global_best_kernel(1, n)

    out0 = fg_download_global_best(n, session_slot=0)
    out1 = fg_download_global_best(n, session_slot=1)

    np.testing.assert_array_equal(out0["final_score"][:n], scores0[:n])
    np.testing.assert_array_equal(out1["final_score"][:n], scores1[:n])

