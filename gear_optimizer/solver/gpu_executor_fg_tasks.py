from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.solver.gpu_executor_dispatch import order_responses_for_requests
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


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
        inflight_v4 = env_flag_fn("INFLIGHT_V4")
        task_budget = 256 if (inflight_v4 or in_process_queues) else 0

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


def coalesce_fg_task_requests(
    requests: list[GpuRequest],
    *,
    in_process_queues: bool,
    execute_request: Callable[[GpuRequest], GpuResponse],
    payload_dict_fn: Callable[[GpuRequest], dict[str, Any]],
    solve_force_greats_finder_gpu_tasks_fn: Callable[..., Any],
    record_fg_tasks_batch: Callable[[int], None],
    record_pack: Callable[[GpuRequestType, float], None],
    perf_counter_fn: Callable[[], float],
    env_get_fn: Callable[..., Any] = env_get,
) -> list[GpuResponse]:
    task_budget = load_fg_task_budget(
        in_process_queues=bool(in_process_queues),
        env_get_fn=env_get_fn,
    )

    def _flush_task_only_segment(seg: list[FgTaskOnlyRequest]) -> dict[int, GpuResponse]:
        if not seg:
            return {}

        groups: dict[tuple[Any, ...], list[FgTaskOnlyRequest]] = {}
        out_by_id: dict[int, GpuResponse] = {}

        for item in seg:
            key = fg_task_only_group_key(item.args, item.kwargs)
            if key is None:
                out_by_id[int(item.request.request_id)] = execute_request(item.request)
                continue
            groups.setdefault(key, []).append(item)

        for _key, items in groups.items():
            if not items:
                continue
            if len(items) == 1:
                req0 = items[0].request
                out_by_id[int(req0.request_id)] = execute_request(req0)
                continue

            req0 = items[0].request
            args0 = items[0].args
            kwargs0 = items[0].kwargs
            genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, _, _ = args0

            merged_tasks: list[Any] = []
            upload_any = False
            for item in items:
                merged_tasks.extend(list(item.fg_tasks))
                upload_any = upload_any or bool(item.kwargs.get("upload_genome_stats", True))
                record_fg_tasks_batch(len(item.fg_tasks))

            kwargs_local = build_merged_fg_task_kwargs(kwargs0, upload_genome_stats=upload_any)

            t_pack0 = perf_counter_fn()
            try:
                upload_this = bool(kwargs_local.get("upload_genome_stats", True))
                for fg_task_chunk in iter_fg_task_chunks(merged_tasks, task_budget):
                    kwargs_local["upload_genome_stats"] = bool(upload_this)
                    solve_force_greats_finder_gpu_tasks_fn(
                        genome_stats_list,
                        timestamps_np,
                        great_candidate_timestamps_np,
                        int(long_notes),
                        float(last_note_time),
                        fg_tasks=fg_task_chunk,
                        **kwargs_local,
                    )
                    upload_this = False
                record_pack(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, perf_counter_fn() - t_pack0)
                for item in items:
                    req = item.request
                    out_by_id[int(req.request_id)] = GpuResponse(request_id=req.request_id, success=True, result=None)
            except Exception as exc:
                record_pack(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, perf_counter_fn() - t_pack0)
                err = f"{type(exc).__name__}: {exc}"
                for item in items:
                    req = item.request
                    out_by_id[int(req.request_id)] = GpuResponse(request_id=req.request_id, success=False, error=err)

        return out_by_id

    responses_by_id: dict[int, GpuResponse] = {}
    segment: list[FgTaskOnlyRequest] = []

    def _flush_segment() -> None:
        nonlocal segment
        if not segment:
            return
        seg_resps = _flush_task_only_segment(segment)
        responses_by_id.update({int(k): v for k, v in seg_resps.items() if v is not None})
        segment = []

    for req in requests:
        extracted = extract_fg_task_only_request(req, payload_dict_fn(req))
        if extracted is not None:
            segment.append(extracted)
            continue

        _flush_segment()
        resp = execute_request(req)
        responses_by_id[int(req.request_id)] = resp

    _flush_segment()
    return order_responses_for_requests(requests, responses_by_id.values())
