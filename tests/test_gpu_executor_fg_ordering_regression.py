import os
import time

import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


def _make_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    rows = int(TOTAL_ROWS) + 1
    x = np.linspace(0.0, 1.0, rows, dtype=np.float64)
    return {
        "Perfect Points": 1.0 + 0.5 * x,
        "Combo Multiplier": 1.0 + 2.0 * x,
        "Fever Multiplier": 1.0 + 4.0 * x,
        "Fever Fill Rate": 1.0 + 0.8 * x,
        "Fever Time": 1.0 + 1.2 * x,
    }


def test_gpu_executor_fg_task_then_download_ordering_regression(monkeypatch):
    """
    Regression test: a SOLVE_FORCE_GREATS_FINDER "download" request must not execute before
    earlier task-only requests in the same executor batch.

    Historically, `_coalesce_fg_task_requests()` executed non-task requests eagerly while
    still scanning the request list, allowing a download to read a partial global-best state.
    """
    from gear_optimizer.solver.gpu_executor import GpuExecutor
    from gear_optimizer.solver.gpu_executor_types import GpuRequestType
    from gear_optimizer.solver.gpu_service import GpuServiceClient

    # Encourage the executor to batch multiple FG requests together.
    monkeypatch.setenv("GPU_EXECUTOR_BATCH_WAIT_MS", "50")
    monkeypatch.setenv("GPU_EXECUTOR_MAX_BATCH", "64")

    # Fresh executor singleton per test.
    GpuExecutor._instance = None
    ex = GpuExecutor()
    ex.start(in_process=True)
    time.sleep(0.2)

    client = GpuServiceClient(ex)
    client.start(start_executor=False)
    try:
        timestamps = np.linspace(0.0, 60.0, 240, dtype=np.float32)
        long_notes = 0
        last_note_time = float(timestamps[-1])

        # Keep deterministic stats.
        rng = np.random.default_rng(1337)
        genome_stats = np.zeros((128, 7), dtype=np.int32)
        genome_stats[:, 0] = rng.integers(80, 140, size=128, dtype=np.int32)
        genome_stats[:, 1] = rng.integers(80, 140, size=128, dtype=np.int32)
        genome_stats[:, 2] = rng.integers(80, 160, size=128, dtype=np.int32)
        genome_stats[:, 3] = rng.integers(140, 280, size=128, dtype=np.int32)
        genome_stats[:, 4] = rng.integers(140, 280, size=128, dtype=np.int32)
        genome_stats[:, 5] = rng.integers(0, 60, size=128, dtype=np.int32)
        genome_stats[:, 6] = rng.integers(0, 60, size=128, dtype=np.int32)

        ref_arrays = _make_ref_arrays()

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

        # Task-only request: should update global-best but not download.
        fg_tasks = [
            {
                "counts_list": [(0, 0), (1, 0), (0, 1), (1, 1)],
                "ftff_pairs": [(0, 0), (1, 0), (0, 1), (1, 1)],
                "base_cfg_offset": 0,
            }
        ]

        base_args = (genome_stats, timestamps, None, int(long_notes), float(last_note_time), None, None)
        n_genomes = int(genome_stats.shape[0])

        def _reset_payload() -> dict:
            return {
                "args": base_args,
                "kwargs": {
                    "fg_tasks": [],
                    "fg_reset_before": True,
                    "fg_download_after": False,
                    "n_genomes_override": n_genomes,
                    "n_sections": 2,
                    "ref_arrays": ref_arrays,
                    "return_raw": True,
                    "accumulate_global": True,
                    "upload_genome_stats": True,
                    **flags,
                },
            }

        def _task_only_payload() -> dict:
            return {
                "args": base_args,
                "kwargs": {
                    "fg_tasks": fg_tasks,
                    "fg_reset_before": False,
                    "fg_download_after": False,
                    "n_genomes_override": n_genomes,
                    "n_sections": 2,
                    "ref_arrays": ref_arrays,
                    "return_raw": True,
                    "accumulate_global": True,
                    "upload_genome_stats": True,
                    **flags,
                },
            }

        def _download_payload() -> dict:
            # Empty fg_tasks: trigger download-after without adding new work.
            return {
                "args": base_args,
                "kwargs": {
                    "fg_tasks": [],
                    "fg_reset_before": False,
                    "fg_download_after": True,
                    "n_genomes_override": n_genomes,
                    "n_sections": 2,
                    "ref_arrays": ref_arrays,
                    "return_raw": True,
                    "accumulate_global": True,
                    "upload_genome_stats": False,
                    **flags,
                },
            }

        # Reference: sequential ordering.
        client.submit(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, _reset_payload()).future.result()
        client.submit(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, _task_only_payload()).future.result()
        expected = client.submit(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, _download_payload()).future.result()
        assert isinstance(expected, dict)

        # Now recreate the hazard: submit task-only + download without waiting in-between.
        client.submit(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, _reset_payload()).future.result()
        fut_task = client.submit(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, _task_only_payload()).future
        fut_dl = client.submit(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, _download_payload()).future
        _ = fut_task.result()
        got = fut_dl.result()
        assert isinstance(got, dict)

        # If the download executed early, we'd read a stale global-best and differ.
        for k in ("final_score", "base_score", "cfg_idx", "FT", "FF"):
            assert np.array_equal(np.asarray(expected[k]), np.asarray(got[k])), f"Mismatch for key={k}"
    finally:
        try:
            client.close()
        except Exception:
            pass
        try:
            ex.stop()
        finally:
            GpuExecutor._instance = None
