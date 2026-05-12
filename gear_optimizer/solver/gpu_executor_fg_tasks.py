from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.solver.gpu_executor_types import GpuRequest


@dataclass(frozen=True)
class FgTaskOnlyRequest:
    request: GpuRequest
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    fg_tasks: list[Any]


def load_fg_task_budget(
    *,
    in_process_queues: bool,
    env_get_fn: Callable[..., Any] = env_get,
    env_flag_fn: Callable[..., bool] = env_flag,
) -> int:
    task_budget: int | None = None
    try:
        raw_budget = env_get_fn("FG_TASK_BUDGET")
        if raw_budget is not None and str(raw_budget).strip() != "":
            task_budget = int(str(raw_budget).strip())
    except (ValueError, TypeError):
        task_budget = None

    if task_budget is None:
        inflight_v3 = env_flag_fn("INFLIGHT_V3")
        inflight_v4 = env_flag_fn("INFLIGHT_V4")
        task_budget = 256 if (inflight_v3 or inflight_v4 or in_process_queues) else 0

    return max(0, int(task_budget))


def extract_fg_task_only_request(req: GpuRequest, payload: dict[str, Any]) -> FgTaskOnlyRequest | None:
    args = payload.get("args", ())
    kwargs = payload.get("kwargs", {})
    if not isinstance(args, (list, tuple)) or len(args) != 7 or not isinstance(kwargs, dict):
        return None

    fg_tasks = kwargs.get("fg_tasks")
    if not isinstance(fg_tasks, (list, tuple)) or not fg_tasks:
        return None
    if bool(kwargs.get("fg_reset_before", False)) or bool(kwargs.get("fg_download_after", False)):
        return None

    return FgTaskOnlyRequest(
        request=req,
        args=tuple(args),
        kwargs=dict(kwargs),
        fg_tasks=list(fg_tasks),
    )


def fg_task_only_group_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...] | None:
    try:
        genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, _, _ = args
    except (ValueError, TypeError, IndexError):
        return None

    return (
        id(genome_stats_list),
        id(timestamps_np),
        id(great_candidate_timestamps_np),
        int(kwargs.get("n_sections", 0) or 0),
        int(kwargs.get("song_slot", 0) or 0),
        int(kwargs.get("total_budget", 90) or 90),
        int(kwargs.get("gem_scale_fever", 3) or 3),
        bool(kwargs.get("pair_caps_from_timeline", False)),
        id(kwargs.get("pair_caps_grid")),
        id(kwargs.get("ref_arrays")),
        int(kwargs.get("is_p_ft", 0) or 0),
        int(kwargs.get("is_s_ft", 0) or 0),
        int(kwargs.get("is_p_ff", 0) or 0),
        int(kwargs.get("is_s_ff", 0) or 0),
        int(kwargs.get("is_p_pp", 0) or 0),
        int(kwargs.get("is_s_pp", 0) or 0),
        int(kwargs.get("is_p_cm", 0) or 0),
        int(kwargs.get("is_s_cm", 0) or 0),
        int(kwargs.get("is_p_fm", 0) or 0),
        int(kwargs.get("is_s_fm", 0) or 0),
        int(kwargs.get("is_p_ov", 0) or 0),
        int(kwargs.get("is_s_ov", 0) or 0),
        int(kwargs.get("base_cfg_offset", 0) or 0),
        kwargs.get("cfg_chunk"),
        int(long_notes or 0),
        float(last_note_time or 0.0),
    )


def build_merged_fg_task_kwargs(source: dict[str, Any], *, upload_genome_stats: bool) -> dict[str, Any]:
    merged = dict(source)
    merged.pop("fg_tasks", None)
    merged["accumulate_global"] = True
    merged["return_raw"] = True
    merged["upload_genome_stats"] = bool(upload_genome_stats)
    merged.pop("fg_reset_before", None)
    merged.pop("fg_download_after", None)
    merged.pop("fg_download_topk", None)
    merged.pop("fg_download_base_scores", None)
    merged.pop("fg_download_keep_mask", None)
    merged.pop("n_genomes_override", None)
    return merged


def iter_fg_task_chunks(fg_tasks: Sequence[Any], task_budget: int) -> list[list[Any]]:
    tasks = list(fg_tasks)
    if int(task_budget) <= 0 or len(tasks) <= int(task_budget):
        return [tasks]
    return [tasks[j : j + int(task_budget)] for j in range(0, len(tasks), int(task_budget))]
