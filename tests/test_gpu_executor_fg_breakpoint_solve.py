from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.gpu_executor_fg import (
    execute_fg_solve_with_breakpoints,
    execute_fg_solve_with_breakpoints_batch,
    run_fg_solve_with_breakpoints_payload,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_type, payload) -> GpuRequest:
    return GpuRequest(
        request_type=request_type,
        request_id=80,
        worker_id=0,
        payload=payload,
    )


def _batch_request(payload) -> GpuRequest:
    return _request(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH, payload)


def _batch_execute(request, **overrides):
    funcs = {
        "in_process_queues": True,
        "raise_if_abort_requested": lambda: None,
        "run_payload_fn": lambda payload, **_kwargs: payload,
        "decode_cfg_counts_from_windows_fn": lambda *_args: np.asarray([[2]], dtype=np.int32),
        "download_packed_topk_batch_fn": lambda n: [{} for _ in range(int(n))],
        "download_batch_max_fn": lambda: 8,
    }
    funcs.update(overrides)
    return execute_fg_solve_with_breakpoints_batch(request, **funcs)


def test_execute_fg_solve_with_breakpoints_requires_in_process_queues():
    response = execute_fg_solve_with_breakpoints(
        _request(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS, {}),
        in_process_queues=False,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda _payload: "unused",
    )

    assert response.success is False
    assert "requires in-process queues" in str(response.error)


def test_execute_fg_solve_with_breakpoints_returns_payload_result():
    response = execute_fg_solve_with_breakpoints(
        _request(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS, {"x": 1}),
        in_process_queues=True,
        raise_if_abort_requested=lambda: None,
        run_payload_fn=lambda payload: {"seen": payload},
    )

    assert response.success is True
    assert response.result == {"seen": {"x": 1}}


def test_execute_fg_solve_with_breakpoints_batch_requires_payloads_list():
    response = _batch_execute(_batch_request({"payloads": object()}))

    assert response.success is False
    assert "payloads: list[dict]" in str(response.error)


def test_execute_fg_solve_with_breakpoints_batch_falls_back_to_per_payload(monkeypatch):
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "2")
    calls = []

    response = _batch_execute(
        _batch_request({"payloads": [{"x": 1}, {"x": 2}]}),
        run_payload_fn=lambda payload, **_kwargs: calls.append(payload) or payload["x"],
    )

    assert response.success is True
    assert response.result == [1, 2]
    assert calls == [{"x": 1}, {"x": 2}]


def test_execute_fg_solve_with_breakpoints_batch_reuses_selection_upload(monkeypatch):
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "1")
    preupload_flags = []

    def run_payload(payload, *, batch_pack_idx=None):
        preupload_flags.append(bool(payload.get("fg_selection_inputs_preuploaded", False)))
        return {"_packed_batch": True, "n_sections": 1, "implicit_cfgs": True}

    base_scores = np.asarray([100, 200], dtype=np.int32)
    keep_mask = np.asarray([1, 0], dtype=np.int32)
    payloads = [
        {
            "genome_stats_list": [0, 1],
            "fg_download_topk": 1,
            "fg_download_base_scores": base_scores,
            "fg_download_keep_mask": keep_mask,
        },
        {
            "genome_stats_list": [0, 1],
            "fg_download_topk": 1,
            "fg_download_base_scores": base_scores.copy(),
            "fg_download_keep_mask": keep_mask.copy(),
        },
    ]

    response = _batch_execute(
        _batch_request({"payloads": payloads}),
        run_payload_fn=run_payload,
        download_packed_topk_batch_fn=lambda n: [{"cfg_counts": np.zeros((1, 1), dtype=np.int32)}] * int(n),
    )

    assert response.success is True
    assert len(response.result) == 2
    assert preupload_flags == [False, True]


def test_execute_fg_solve_with_breakpoints_batch_decodes_missing_cfg_counts(monkeypatch):
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "1")

    def run_payload(_payload, *, batch_pack_idx=None):
        return {
            "_packed_batch": True,
            "n_sections": 1,
            "implicit_cfgs": True,
            "base_ft": np.asarray([0], dtype=np.int32),
            "base_ff": np.asarray([0], dtype=np.int32),
        }

    response = _batch_execute(
        _batch_request(
            {
                "payloads": [
                    {
                        "genome_stats_list": [0],
                        "fg_download_topk": 1,
                        "fg_download_base_scores": np.asarray([10], dtype=np.int32),
                    }
                ]
            }
        ),
        run_payload_fn=run_payload,
        download_packed_topk_batch_fn=lambda _n: [
            {
                "FT": np.asarray([1], dtype=np.int32),
                "FF": np.asarray([2], dtype=np.int32),
                "cfg_idx": np.asarray([0], dtype=np.int32),
            }
        ],
    )

    assert response.success is True
    assert "cfg_counts" not in response.result[0]


def test_run_fg_solve_with_breakpoints_payload_orchestrates_task_solve(monkeypatch):
    import gear_optimizer.solver.gpu_executor_fg as solve_mod

    calls = []
    prepared = SimpleNamespace(
        n_sections=1,
        base_ft=np.asarray([0], dtype=np.int32),
        base_ff=np.asarray([0], dtype=np.int32),
        song_slot=3,
        gem_scale_fever=3,
        solve_kwargs_payload={"song_slot": 3},
        implicit_cfgs=True,
    )
    task_plan = SimpleNamespace(
        fg_tasks=[{"task": 1}],
        cfg_windows=[[(0, 0)]],
        surface_pair_drops=2,
        surface_pair_reduce_sec=0.5,
    )
    submission = SimpleNamespace(
        genome_stats_list=["g"],
        timestamps_np=np.asarray([1.0], dtype=np.float32),
        great_candidate_timestamps_np=np.asarray([1.0], dtype=np.float32),
        long_notes=0,
        last_note_time=1.0,
        kwargs_local={"song_slot": 3},
        n_genomes=1,
    )

    monkeypatch.setattr(solve_mod, "prepare_fg_breakpoint_payload_inputs", lambda payload, env_get: prepared)
    monkeypatch.setattr(
        solve_mod,
        "maybe_precompute_fg_breakpoint_timeline",
        lambda payload, precompute_timeline_fn: calls.append("precompute"),
    )
    monkeypatch.setattr(solve_mod, "build_fg_breakpoint_tasks", lambda _prepared: task_plan)
    monkeypatch.setattr(
        solve_mod,
        "prepare_fg_breakpoint_solve_submission",
        lambda payload, solve_kwargs_payload: submission,
    )
    monkeypatch.setattr(solve_mod, "pack_or_download_fg_breakpoint_result", lambda *args, **kwargs: {"raw": True})
    monkeypatch.setattr(
        solve_mod,
        "finalize_fg_breakpoint_result",
        lambda result, **kwargs: {"final": result, "kwargs": kwargs},
    )

    out = run_fg_solve_with_breakpoints_payload(
        {"fg_reset_before": True},
        raise_if_abort_requested=lambda: calls.append("abort_check"),
        env_get_fn=lambda _key, default=None: default,
        precompute_timeline_fn=lambda *_args, **_kwargs: None,
        solve_force_greats_finder_gpu_tasks_fn=lambda *args, **kwargs: calls.append(("solve", args, kwargs)),
        reset_global_best_fn=lambda n_genomes, session_slot: calls.append(("reset", n_genomes, session_slot)),
        download_global_best_fn=lambda *_args, **_kwargs: {"downloaded": True},
        pack_global_best_topk_to_batch_fn=lambda *_args, **_kwargs: {"packed": True},
        decode_cfg_counts_from_windows_fn=lambda *_args: np.asarray([[2]], dtype=np.int32),
    )

    assert calls[0:3] == ["abort_check", "precompute", ("reset", 1, 3)]
    assert calls[3][0] == "solve"
    assert calls[3][2]["fg_tasks"] == [{"task": 1}]
    assert out["final"] == {"raw": True}
    assert out["kwargs"]["fused_surface_pair_drops"] == 2
