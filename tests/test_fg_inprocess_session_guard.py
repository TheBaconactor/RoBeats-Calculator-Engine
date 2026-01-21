import os
import time
import threading

import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


def _make_minimal_song(*, song_name: str, song_slot: int) -> tuple[dict, dict]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    timestamps = np.linspace(0.0, 120.0, 200, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": song_name,
            "Difficulty": "Easy",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
        "_gpu_song_slot": int(song_slot),
    }

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }
    return calc_song, ref_arrays


def _make_minimal_entries() -> dict:
    # Keep stats deterministic. FT/FF here are gem *counts* (center for search window),
    # not the "Fever Time/Fever Fill Rate" stat values.
    base_stats = {
        "Perfect Points": 60,
        "Combo Multiplier": 60,
        "Fever Multiplier": 60,
        "Fever Fill Rate": 30,
        "Fever Time": 30,
        "Rush": 60,
        "Flow": 60,
        "Beat": 30,
        "Vibe": 30,
        "Chill": 30,
    }
    details = {
        "Stats": dict(base_stats),
        "Selected Element": "Rush",
        "FT": 0,
        "FF": 0,
        "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Element": 0,
        },
    }
    return {
        "h0": {
            "score": 12345,
            "base_score": 12345,
            "fg_score": 0,
            "gear": [],
            "minis": [],
            "details": details,
            "_source": "ga",
        }
    }


def _run_fg_once(
    *,
    monkeypatch,
    allow_multi_request_session: bool,
    tasks_per_request_env: int,
    fg_search_radius: int,
) -> int:
    from gear_optimizer.helpers.song_helpers.force_greats.core import process_force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch as _gpu_dispatch
    from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequestType
    from gear_optimizer.solver.gpu_service import GpuServiceClient

    # IMPORTANT: `_FG_FUSE_BREAKPOINTS_SOLVE` is read at module import time.
    # Patch the module-level flag so this test actually exercises the multi-request
    # `SOLVE_FORCE_GREATS_FINDER` (fg_tasks) path we are guarding.
    _gpu_dispatch._FG_FUSE_BREAKPOINTS_SOLVE = False

    monkeypatch.setenv("FG_ALLOW_MULTI_REQUEST_SESSION", "1" if allow_multi_request_session else "0")
    monkeypatch.setenv("FG_ASYNC_TASKS_PER_REQUEST", str(int(tasks_per_request_env)))
    monkeypatch.setenv("FG_ASYNC_MAX_INFLIGHT", "16")

    # Fresh GPU executor singleton per test run.
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start(in_process=True)
    time.sleep(0.2)

    gpu_client = GpuServiceClient(executor)
    gpu_client.start(start_executor=False)

    try:
        calc_song, ref_arrays = _make_minimal_song(song_name="FG session guard", song_slot=1)
        entries = _make_minimal_entries()

        before = int(executor._req_type_counts.get(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 0))

        _ = process_force_greats(
            entries,
            False,  # manual_force_greats
            True,  # force_greats_finder
            [],  # force_greats_config
            calc_song,
            ref_arrays,
            "Rush",
            lambda d: d,
            0,
            use_gpu=True,
            fg_search_radius=int(fg_search_radius),
            perf_timing=False,
            gpu_client=gpu_client,
        )

        after = int(executor._req_type_counts.get(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 0))
        return max(0, after - before)
    finally:
        try:
            gpu_client.close()
        except Exception:
            pass
        try:
            executor.stop()
        finally:
            GpuExecutor._instance = None


def test_fg_inprocess_session_guard_forces_single_request(monkeypatch):
    """
    Regression test for the in-process FG "session guard".

    We intentionally set a tiny `FG_ASYNC_TASKS_PER_REQUEST` (which would normally split
    a single song across multiple executor requests) and verify the default guard
    forces a single SOLVE_FORCE_GREATS_FINDER request, eliminating cross-request
    global-best mixing risk.
    """
    # Radius 35 => 36*36=1296 FT/FF pairs (budget constraint doesn't bind here),
    # which requires multiple FT/FF chunks internally.
    n = _run_fg_once(
        monkeypatch=monkeypatch,
        allow_multi_request_session=False,
        tasks_per_request_env=2,
        fg_search_radius=35,
    )
    assert n == 1


def test_fg_inprocess_session_guard_optout_allows_multiple_requests(monkeypatch):
    """
    Sanity check: when `FG_ALLOW_MULTI_REQUEST_SESSION=1`, the same workload can
    split into multiple SOLVE_FORCE_GREATS_FINDER requests.

    This doesn't prove mixing occurs, but it confirms the guard is what prevents
    multi-request sessions by default.
    """
    n = _run_fg_once(
        monkeypatch=monkeypatch,
        allow_multi_request_session=True,
        tasks_per_request_env=2,
        fg_search_radius=35,
    )
    assert n >= 2
