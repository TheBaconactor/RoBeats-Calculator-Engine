import sys
import types

import numpy as np

from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType


def _install_fake_taichi_deps_for_executor_managed_fg(monkeypatch):
    calls: dict[str, list] = {"precompute": [], "stage": [], "solve_kwargs": []}

    fake_parent = types.ModuleType("gear_optimizer.solver.taichi_gem")
    fake_parent.__path__ = []

    fake_api = types.ModuleType("gear_optimizer.solver.taichi_gem.api")

    def _fake_stage(*, table_slot: int, coords, n_slots: int = 9) -> int:
        coords_np = np.asarray(coords, dtype=np.int32)
        calls["stage"].append((int(table_slot), coords_np.copy(), int(n_slots)))
        return int(coords_np.shape[0])

    fake_api.ga_stage_genome_base_stats_from_fg_candidates_table = _fake_stage

    fake_timeline = types.ModuleType("gear_optimizer.solver.taichi_gem.api.timeline")

    def _fake_precompute(calc_song: dict, ref_arrays: dict, song_slot: int = 0) -> None:
        calls["precompute"].append((calc_song, ref_arrays, int(song_slot)))

    fake_timeline.precompute_timeline_gpu = _fake_precompute

    fake_force_parent = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats")
    fake_force_parent.__path__ = []
    fake_force_api = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats.api")

    def _fake_solve(*args, **kwargs):
        calls["solve_kwargs"].append(dict(kwargs))
        return "ok"

    fake_force_api.solve_force_greats_finder_gpu = _fake_solve
    fake_force_api.solve_force_greats_finder_gpu_tasks = lambda *a, **k: None
    fake_force_api.fg_reset_global_best = lambda *a, **k: None
    fake_force_api.fg_download_global_best = lambda *a, **k: {"dummy": True}

    fake_parent.api = fake_api
    fake_api.timeline = fake_timeline
    fake_parent.force_greats = fake_force_parent
    fake_force_parent.api = fake_force_api

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem", fake_parent)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", fake_api)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api.timeline", fake_timeline)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats", fake_force_parent)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats.api", fake_force_api)

    return calls


def test_executor_managed_deps_solve_force_greats_finder(monkeypatch):
    calls = _install_fake_taichi_deps_for_executor_managed_fg(monkeypatch)

    ex = GpuExecutor()
    ex._in_process_queues = True

    calc_song = {"metadata": {"Song Name": "X"}, "song_data": {"timestamps": [0.0, 1.0]}}
    ref_arrays = {"dummy": True}
    coords = np.asarray([[0, 1], [2, 3]], dtype=np.int32)

    req = GpuRequest(
        request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        request_id=1,
        worker_id=1,
        payload={
            "args": (),
            "kwargs": {
                "ensure_timeline_precompute": True,
                "calc_song": calc_song,
                "ref_arrays": ref_arrays,
                "song_slot": 3,
                "ga_stage_coords": coords,
                "ga_stage_table_slot": 3,
            },
        },
    )
    resp = ex._execute_solve_force_greats_finder(req)
    assert resp.success
    assert resp.result == "ok"

    assert calls["precompute"] == [(calc_song, ref_arrays, 3)]
    assert len(calls["stage"]) == 1
    assert calls["stage"][0][0] == 3
    assert calls["stage"][0][2] == 9
    assert np.array_equal(calls["stage"][0][1], coords)

    forwarded = calls["solve_kwargs"][0]
    for k in ("ensure_timeline_precompute", "calc_song", "ga_stage_coords", "ga_stage_table_slot", "ga_stage_n_slots"):
        assert k not in forwarded


def test_executor_managed_deps_fg_compute_breakpoints_precomputes_timeline(monkeypatch):
    calls = _install_fake_taichi_deps_for_executor_managed_fg(monkeypatch)

    ex = GpuExecutor()

    calc_song = {"metadata": {"Song Name": "Y"}, "song_data": {"timestamps": [0.0, 1.0]}}
    ref_arrays = {"dummy": True}

    req = GpuRequest(
        request_type=GpuRequestType.FG_COMPUTE_BREAKPOINTS,
        request_id=2,
        worker_id=1,
        payload={
            "ensure_timeline_precompute": True,
            "calc_song": calc_song,
            "ref_arrays": ref_arrays,
            "song_slot": 2,
            "n_sections": 0,
        },
    )
    resp = ex._execute_fg_compute_breakpoints(req)
    assert resp.success
    assert calls["precompute"] == [(calc_song, ref_arrays, 2)]


def test_executor_managed_deps_breakpoints_requires_calc_song_and_ref_arrays(monkeypatch):
    _ = _install_fake_taichi_deps_for_executor_managed_fg(monkeypatch)

    ex = GpuExecutor()
    req = GpuRequest(
        request_type=GpuRequestType.FG_COMPUTE_BREAKPOINTS,
        request_id=3,
        worker_id=1,
        payload={"ensure_timeline_precompute": True, "song_slot": 1, "n_sections": 0},
    )
    resp = ex._execute_fg_compute_breakpoints(req)
    assert not resp.success
    assert "calc_song" in (resp.error or "")
