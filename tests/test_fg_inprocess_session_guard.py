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
    tasks_per_request_env: int,
    fg_search_radius: int,
    song_slot: int = 1,
    return_calc_song: bool = False,
) -> int | tuple[int, dict]:
    from gear_optimizer.helpers.song_helpers.force_greats.core import process_force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch as _gpu_dispatch
    from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequestType
    from gear_optimizer.solver.gpu_service import GpuServiceClient

    # IMPORTANT: `_FG_FUSE_BREAKPOINTS_SOLVE` is read at module import time.
    # Patch the module-level flag so this test actually exercises the multi-request
    # `SOLVE_FORCE_GREATS_FINDER` (fg_tasks) path we are guarding.
    _gpu_dispatch._FG_FUSE_BREAKPOINTS_SOLVE = False

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
        calc_song, ref_arrays = _make_minimal_song(song_name="FG session guard", song_slot=int(song_slot))
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
        count = max(0, after - before)
        if return_calc_song:
            return count, calc_song
        return count
    finally:
        try:
            gpu_client.close()
        except Exception:
            pass
        try:
            executor.stop()
        finally:
            GpuExecutor._instance = None


def test_fg_inprocess_multi_request_default_allows_multiple_requests(monkeypatch):
    """
    Default behavior should allow multiple requests per song when tasks_per_request
    is small enough to split the FT/FF grid.
    """
    # Radius 35 => 36*36=1296 FT/FF pairs (budget constraint doesn't bind here),
    # which requires multiple FT/FF chunks internally.
    n = _run_fg_once(monkeypatch=monkeypatch, tasks_per_request_env=2, fg_search_radius=35)
    assert n >= 2


def test_fg_inprocess_auto_assign_slot_allows_multi_request(monkeypatch):
    n, calc_song = _run_fg_once(
        monkeypatch=monkeypatch,
        tasks_per_request_env=2,
        fg_search_radius=35,
        song_slot=0,
        return_calc_song=True,
    )
    assert n >= 2
    assert int(calc_song.get("_gpu_song_slot", 0) or 0) == 0
    assert "_fg_auto_assigned_slot" not in calc_song


def test_fg_inprocess_auto_assign_failure_forces_single_request(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import core as fg_core

    def _boom():
        raise RuntimeError("slot pool unavailable")

    monkeypatch.setattr(fg_core, "_get_fg_session_slot_pool", _boom)

    n = _run_fg_once(
        monkeypatch=monkeypatch,
        tasks_per_request_env=2,
        fg_search_radius=35,
        song_slot=0,
    )
    assert n == 1
