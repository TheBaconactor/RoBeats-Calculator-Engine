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
    from gear_optimizer.solver.gpu_executor import GpuExecutor
    from gear_optimizer.solver.gpu_executor_types import GpuRequestType
    from gear_optimizer.solver.gpu_service import GpuServiceClient

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

        # FG solve requests can route through multiple request types depending on
        # batching/fused policy and in-process coalescing behavior.
        req_types = (
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        )
        before = sum(int(executor._req_type_counts.get(rt, 0)) for rt in req_types)

        _ = process_force_greats(
            entries,
            False,  # manual_force_greats
            [],  # force_greats_config
            calc_song,
            ref_arrays,
            "Rush",
            lambda d: d,
            use_gpu=True,
            fg_search_radius=int(fg_search_radius),
            perf_timing=False,
            gpu_client=gpu_client,
        )

        after = sum(int(executor._req_type_counts.get(rt, 0)) for rt in req_types)
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
    Default behavior should submit at least one FG solve request.
    """
    # Radius 35 => 36*36=1296 FT/FF pairs (budget constraint doesn't bind here),
    # which can be emitted as one coalesced request or multiple smaller requests
    # depending on active in-process batching/fused policy.
    n = _run_fg_once(monkeypatch=monkeypatch, tasks_per_request_env=2, fg_search_radius=35)
    assert n >= 1


def test_fg_inprocess_auto_assign_slot_allows_multi_request(monkeypatch):
    n, calc_song = _run_fg_once(
        monkeypatch=monkeypatch,
        tasks_per_request_env=2,
        fg_search_radius=35,
        song_slot=0,
        return_calc_song=True,
    )
    assert n >= 1
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
