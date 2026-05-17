import numpy as np

from gear_optimizer.solver.gpu_executor_fg import execute_solve_force_greats_finder
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        request_id=60,
        worker_id=0,
        payload=payload,
    )


def _execute(request, **overrides):
    funcs = {
        "solve_fn": lambda *args, **kwargs: ("solve", args, kwargs),
        "tasks_fn": lambda *args, **kwargs: ("tasks", args, kwargs),
        "reset_global_best_fn": lambda *args, **kwargs: None,
        "download_global_best_fn": lambda *args, **kwargs: ("download", args, kwargs),
        "precompute_timeline_fn": lambda *args, **kwargs: None,
        "record_tasks_batch_fn": None,
    }
    funcs.update(overrides)
    return execute_solve_force_greats_finder(request, **funcs)


def test_execute_solve_force_greats_finder_rejects_invalid_args():
    response = _execute(_request({"args": object(), "kwargs": {}}))

    assert response.success is False
    assert "expected args list/tuple" in str(response.error)


def test_execute_solve_force_greats_finder_precomputes_and_strips_consumed_keys():
    calls = {"precompute": [], "solve": []}

    def precompute_fn(calc_song, ref_arrays, *, song_slot=0):
        calls["precompute"].append((calc_song, ref_arrays, song_slot))

    def solve_fn(*args, **kwargs):
        calls["solve"].append((args, kwargs))
        return "ok"

    calc_song = {"song_data": {}}
    ref_arrays = {"refs": True}
    response = _execute(
        _request(
            {
                "args": (),
                "kwargs": {
                    "ensure_timeline_precompute": True,
                    "calc_song": calc_song,
                    "ref_arrays": ref_arrays,
                    "song_slot": 2,
                },
            }
        ),
        solve_fn=solve_fn,
        precompute_timeline_fn=precompute_fn,
    )

    assert response.success is True
    assert response.result == "ok"
    assert calls["precompute"] == [(calc_song, ref_arrays, 2)]
    forwarded = calls["solve"][0][1]
    assert "ensure_timeline_precompute" not in forwarded
    assert "calc_song" not in forwarded
    assert forwarded["ref_arrays"] is ref_arrays


def test_execute_solve_force_greats_finder_rejects_removed_ga_stage_coords():
    response = _execute(
        _request({"args": (), "kwargs": {"ga_stage_coords": np.asarray([[0, 1]], dtype=np.int32)}})
    )

    assert response.success is False
    assert "removed" in str(response.error)


def test_execute_solve_force_greats_finder_task_batch_resets_solves_downloads_and_profiles():
    calls = {"reset": [], "tasks": [], "download": [], "profile": []}

    def reset_fn(*args, **kwargs):
        calls["reset"].append((args, kwargs))

    def tasks_fn(*args, **kwargs):
        calls["tasks"].append((args, kwargs))

    def download_fn(*args, **kwargs):
        calls["download"].append((args, kwargs))
        return {"scores": [123]}

    args = ([1, 2], np.asarray([0.0]), np.asarray([0.0]), 0, 1.5, [], [])
    response = _execute(
        _request(
            {
                "args": args,
                "kwargs": {
                    "fg_tasks": [{"cfg": 1}],
                    "fg_reset_before": True,
                    "fg_download_after": True,
                    "fg_download_topk": 1,
                    "fg_download_base_scores": np.asarray([1, 2], dtype=np.int64),
                    "fg_download_keep_mask": np.asarray([True, False]),
                    "song_slot": 7,
                },
            }
        ),
        tasks_fn=tasks_fn,
        reset_global_best_fn=reset_fn,
        download_global_best_fn=download_fn,
        record_tasks_batch_fn=lambda n: calls["profile"].append(n),
    )

    assert response.success is True
    assert response.result == {"scores": [123]}
    assert calls["profile"] == [1]
    assert calls["reset"] == [((2,), {"session_slot": 7})]
    assert calls["download"][0][0] == (2,)
    assert calls["download"][0][1]["session_slot"] == 7
    assert calls["download"][0][1]["topk"] == 1
    assert len(calls["tasks"]) == 1
    task_kwargs = calls["tasks"][0][1]
    assert task_kwargs["fg_tasks"] == [{"cfg": 1}]
    assert task_kwargs["accumulate_global"] is True
    assert task_kwargs["return_raw"] is True
    assert task_kwargs["upload_genome_stats"] is True


def test_execute_solve_force_greats_finder_ftff_chunks_calls_solver_for_each_chunk():
    calls = []

    def solve_fn(*args, **kwargs):
        calls.append((args, kwargs))
        return args[6]

    args = [1, 2, 3, 4, 5, 6, "original"]
    response = _execute(
        _request({"args": args, "kwargs": {"ftff_chunks": ["a", "b"], "marker": True}}),
        solve_fn=solve_fn,
    )

    assert response.success is True
    assert response.result == "b"
    assert [call[0][6] for call in calls] == ["a", "b"]
    assert all(call[1] == {"marker": True} for call in calls)
