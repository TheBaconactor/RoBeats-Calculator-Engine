from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.solver.gpu_executor_fg_breakpoint_payload import (
    PreparedFgBreakpointPayloadInputs,
    PreparedFgBreakpointSolveSubmission,
)
from gear_optimizer.solver.gpu_executor_fg_breakpoint_tasks import FgBreakpointTaskPlan


def pack_or_download_fg_breakpoint_result(
    payload: dict[str, Any],
    *,
    prepared: PreparedFgBreakpointPayloadInputs,
    task_plan: FgBreakpointTaskPlan,
    submission: PreparedFgBreakpointSolveSubmission,
    batch_pack_idx: int | None,
    pack_topk_fn: Callable[..., Any],
    download_global_best_fn: Callable[..., Any],
) -> Any:
    download_topk = payload.get("fg_download_topk", None)
    download_base_scores = payload.get("fg_download_base_scores", None)
    download_keep_mask = payload.get("fg_download_keep_mask", None)
    if batch_pack_idx is not None and download_topk is not None and download_base_scores is not None:
        skip_selection_upload = bool(payload.get("fg_selection_inputs_preuploaded", False))
        pack_topk_fn(
            int(submission.n_genomes),
            session_slot=int(prepared.song_slot),
            topk=int(download_topk),
            base_scores=download_base_scores,
            keep_mask=download_keep_mask,
            batch_idx=int(batch_pack_idx),
            upload_selection_inputs=not bool(skip_selection_upload),
        )
        return {
            "_packed_batch": True,
            "implicit_cfgs": bool(prepared.implicit_cfgs),
            "cfg_windows": task_plan.cfg_windows,
            "n_sections": int(prepared.n_sections),
            "song_slot": int(prepared.song_slot),
            "gem_scale_fever": int(prepared.gem_scale_fever),
            "base_ft": prepared.base_ft,
            "base_ff": prepared.base_ff,
            "non_fever_base_by_ff": prepared.non_fever_base_by_ff,
            "fp_cap_table": prepared.fp_cap_table,
            "surface_pair_drops": int(task_plan.surface_pair_drops),
            "surface_pair_reduce_ms": int(round(float(task_plan.surface_pair_reduce_sec) * 1000.0)),
        }

    if download_topk is not None and download_base_scores is not None:
        return download_global_best_fn(
            int(submission.n_genomes),
            session_slot=int(prepared.song_slot),
            topk=int(download_topk),
            base_scores=download_base_scores,
            keep_mask=download_keep_mask,
        )
    return download_global_best_fn(int(submission.n_genomes), session_slot=int(prepared.song_slot))
