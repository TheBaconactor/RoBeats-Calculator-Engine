import numpy as np

from gear_optimizer.solver.gpu_executor_fg import pack_or_download_fg_breakpoint_result
from gear_optimizer.solver.gpu_executor_fg_breakpoint_payload import (
    prepare_fg_breakpoint_payload_inputs,
    prepare_fg_breakpoint_solve_submission,
)
from gear_optimizer.solver.gpu_executor_fg_breakpoint_tasks import FgBreakpointTaskPlan


def _prepared():
    payload = {
        "n_sections": 2,
        "ftff_pairs": [[1, 2]],
        "base_stats_pairs": [[10, 20]],
        "non_fever_base_by_ff": np.zeros((161,), dtype=np.int16),
        "fp_cap_table": np.zeros((161, 51), dtype=np.int16),
        "song_slot": 4,
        "gem_scale_fever": 5,
        "solve_kwargs": {"n_genomes_override": 3},
    }
    prepared = prepare_fg_breakpoint_payload_inputs(payload)
    assert prepared is not None
    submission = prepare_fg_breakpoint_solve_submission(payload, prepared.solve_kwargs_payload)
    task_plan = FgBreakpointTaskPlan(
        fg_tasks=[{"ok": True}],
        cfg_windows=[{"base": 0, "len": 1}],
        surface_pair_drops=7,
        surface_pair_reduce_sec=0.012,
    )
    return payload, prepared, submission, task_plan


def test_pack_or_download_fg_breakpoint_result_packs_batch_topk():
    payload, prepared, submission, task_plan = _prepared()
    payload.update(
        {
            "fg_download_topk": 2,
            "fg_download_base_scores": np.asarray([10, 20, 30], dtype=np.int32),
            "fg_download_keep_mask": np.asarray([True, False, True]),
            "fg_selection_inputs_preuploaded": True,
        }
    )
    calls = []

    result = pack_or_download_fg_breakpoint_result(
        payload,
        prepared=prepared,
        task_plan=task_plan,
        submission=submission,
        batch_pack_idx=6,
        pack_topk_fn=lambda *args, **kwargs: calls.append((args, kwargs)),
        download_global_best_fn=lambda *_args, **_kwargs: {"downloaded": True},
    )

    assert result["_packed_batch"] is True
    assert result["cfg_windows"] == [{"base": 0, "len": 1}]
    assert result["surface_pair_drops"] == 7
    assert result["surface_pair_reduce_ms"] == 12
    assert calls[0][0] == (3,)
    assert calls[0][1]["session_slot"] == 4
    assert calls[0][1]["topk"] == 2
    assert calls[0][1]["batch_idx"] == 6
    assert calls[0][1]["upload_selection_inputs"] is False


def test_pack_or_download_fg_breakpoint_result_downloads_topk_when_not_batch_packing():
    payload, prepared, submission, task_plan = _prepared()
    payload.update(
        {
            "fg_download_topk": 1,
            "fg_download_base_scores": np.asarray([10, 20, 30], dtype=np.int32),
            "fg_download_keep_mask": np.asarray([True, False, True]),
        }
    )
    calls = []

    result = pack_or_download_fg_breakpoint_result(
        payload,
        prepared=prepared,
        task_plan=task_plan,
        submission=submission,
        batch_pack_idx=None,
        pack_topk_fn=lambda *_args, **_kwargs: calls.append("pack"),
        download_global_best_fn=lambda *args, **kwargs: {"args": args, "kwargs": kwargs},
    )

    assert calls == []
    assert result["args"] == (3,)
    assert result["kwargs"]["session_slot"] == 4
    assert result["kwargs"]["topk"] == 1


def test_pack_or_download_fg_breakpoint_result_downloads_full_result():
    payload, prepared, submission, task_plan = _prepared()

    result = pack_or_download_fg_breakpoint_result(
        payload,
        prepared=prepared,
        task_plan=task_plan,
        submission=submission,
        batch_pack_idx=None,
        pack_topk_fn=lambda *_args, **_kwargs: None,
        download_global_best_fn=lambda *args, **kwargs: {"args": args, "kwargs": kwargs},
    )

    assert result == {"args": (3,), "kwargs": {"session_slot": 4}}
