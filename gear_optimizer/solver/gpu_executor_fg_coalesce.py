from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.parsing import env_get
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


@dataclass(frozen=True)
class FgBreakpointCoalesceLimits:
    max_payloads: int
    max_pairs: int


@dataclass(frozen=True)
class FgBreakpointPayloadEntry:
    request: GpuRequest
    payload_list: list[dict[str, Any]]
    n_payloads: int
    n_pairs: int


@dataclass(frozen=True)
class FgBreakpointOversizedEntry:
    entry: FgBreakpointPayloadEntry
    chunks: list[list[dict[str, Any]]]


@dataclass(frozen=True)
class FgBreakpointCoalescePlan:
    invalid: list[tuple[GpuRequest, str]]
    oversized: list[FgBreakpointOversizedEntry]
    groups: list[list[FgBreakpointPayloadEntry]]


@dataclass(frozen=True)
class FgBreakpointGroupBundle:
    request: GpuRequest
    slices: list[tuple[GpuRequest, int, int]]
    payload_count: int


@dataclass(frozen=True)
class FgBreakpointSplitRequest:
    request: GpuRequest
    expected_results: int


def load_fg_breakpoint_coalesce_limits(
    *,
    env_get_fn: Callable[[str, Any], Any] = env_get,
) -> FgBreakpointCoalesceLimits:
    try:
        max_payloads = int(env_get_fn("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "64") or "64")
    except (ValueError, TypeError):
        max_payloads = 64
    max_payloads = max(1, min(int(max_payloads), 512))
    try:
        max_pairs = int(env_get_fn("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAIRS", "256") or "256")
    except (ValueError, TypeError):
        max_pairs = 256
    max_pairs = max(0, int(max_pairs))
    return FgBreakpointCoalesceLimits(max_payloads=int(max_payloads), max_pairs=int(max_pairs))


def fg_breakpoint_payload_pair_count(payloads: list[dict[str, Any]], *, max_pairs: int) -> int:
    if max_pairs <= 0:
        return 0

    import numpy as np

    total = 0
    for payload in payloads:
        ftff_pairs = payload.get("ftff_pairs")
        if ftff_pairs is None:
            continue
        try:
            if isinstance(ftff_pairs, np.ndarray):
                total += int(ftff_pairs.shape[0])
            else:
                total += int(len(ftff_pairs))
        except (ValueError, TypeError, AttributeError):
            continue
    return int(total)


def split_fg_breakpoint_payloads_for_coalesce(
    payload_list: list[dict[str, Any]],
    *,
    limits: FgBreakpointCoalesceLimits,
) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    cur_chunk: list[dict[str, Any]] = []
    cur_pairs = 0

    for payload_item in payload_list:
        item_pairs = fg_breakpoint_payload_pair_count([payload_item], max_pairs=int(limits.max_pairs))
        if not cur_chunk:
            cur_chunk = [payload_item]
            cur_pairs = int(item_pairs)
            continue

        exceed_payload_cap = (len(cur_chunk) + 1) > int(limits.max_payloads)
        exceed_pairs_cap = bool(limits.max_pairs > 0 and (cur_pairs + int(item_pairs)) > int(limits.max_pairs))
        if exceed_payload_cap or exceed_pairs_cap:
            chunks.append(cur_chunk)
            cur_chunk = [payload_item]
            cur_pairs = int(item_pairs)
        else:
            cur_chunk.append(payload_item)
            cur_pairs += int(item_pairs)

    if cur_chunk:
        chunks.append(cur_chunk)
    return chunks


def plan_fg_breakpoint_coalescing(
    requests: list[GpuRequest],
    *,
    payload_dict_fn: Callable[[GpuRequest], dict[str, Any]],
    limits: FgBreakpointCoalesceLimits,
) -> FgBreakpointCoalescePlan:
    invalid: list[tuple[GpuRequest, str]] = []
    oversized: list[FgBreakpointOversizedEntry] = []
    groups: list[list[FgBreakpointPayloadEntry]] = []
    cur: list[FgBreakpointPayloadEntry] = []
    cur_payloads = 0
    cur_pairs = 0

    for req in requests:
        payload = payload_dict_fn(req)
        payloads = payload.get("payloads")
        if not isinstance(payloads, (list, tuple)) or not payloads:
            invalid.append((req, "missing/empty payloads list"))
            continue
        ok = True
        for payload_item in payloads:
            if not isinstance(payload_item, dict):
                ok = False
                break
        if not ok:
            invalid.append((req, "payload list contains non-dict item"))
            continue

        payload_list = list(payloads)
        n_payloads = int(len(payload_list))
        if n_payloads <= 0:
            invalid.append((req, "payload list length resolved to zero"))
            continue
        n_pairs = fg_breakpoint_payload_pair_count(payload_list, max_pairs=int(limits.max_pairs))
        entry = FgBreakpointPayloadEntry(
            request=req,
            payload_list=payload_list,
            n_payloads=int(n_payloads),
            n_pairs=int(n_pairs),
        )
        if n_payloads > int(limits.max_payloads) or (limits.max_pairs > 0 and n_pairs > int(limits.max_pairs)):
            oversized.append(
                FgBreakpointOversizedEntry(
                    entry=entry,
                    chunks=split_fg_breakpoint_payloads_for_coalesce(payload_list, limits=limits),
                )
            )
            continue

        if cur and (
            cur_payloads + n_payloads > int(limits.max_payloads)
            or (limits.max_pairs > 0 and cur_pairs + n_pairs > int(limits.max_pairs))
        ):
            groups.append(cur)
            cur = []
            cur_payloads = 0
            cur_pairs = 0

        cur.append(entry)
        cur_payloads += int(n_payloads)
        cur_pairs += int(n_pairs)

    if cur:
        groups.append(cur)

    return FgBreakpointCoalescePlan(
        invalid=invalid,
        oversized=oversized,
        groups=groups,
    )


def build_fg_breakpoint_group_bundle(group: list[FgBreakpointPayloadEntry]) -> FgBreakpointGroupBundle:
    merged_payloads: list[dict[str, Any]] = []
    slices: list[tuple[GpuRequest, int, int]] = []
    for entry in group:
        req = entry.request
        payload_list = entry.payload_list
        n_payloads = int(entry.n_payloads)
        start = len(merged_payloads)
        merged_payloads.extend(payload_list)
        slices.append((req, int(start), int(n_payloads)))

    return FgBreakpointGroupBundle(
        request=GpuRequest(
            request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            request_id=-1,
            worker_id=-1,
            payload={"payloads": merged_payloads},
        ),
        slices=slices,
        payload_count=int(len(merged_payloads)),
    )


def split_fg_breakpoint_group_result(
    bundle: FgBreakpointGroupBundle,
    merged_results: Any,
) -> list[GpuResponse]:
    if not isinstance(merged_results, list):
        raise TypeError("merged FG bundle returned non-list result")
    if int(len(merged_results)) != int(bundle.payload_count):
        raise RuntimeError("merged FG bundle length mismatch")

    responses: list[GpuResponse] = []
    for req, start, n in bundle.slices:
        responses.append(
            GpuResponse(
                request_id=req.request_id,
                success=True,
                result=list(merged_results[int(start) : int(start) + int(n)]),
            )
        )
    return responses


def build_fg_breakpoint_split_requests(oversized: FgBreakpointOversizedEntry) -> list[FgBreakpointSplitRequest]:
    req = oversized.entry.request
    split_requests: list[FgBreakpointSplitRequest] = []
    for payload_chunk in oversized.chunks:
        split_requests.append(
            FgBreakpointSplitRequest(
                request=GpuRequest(
                    request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                    request_id=int(req.request_id),
                    worker_id=int(req.worker_id),
                    payload={"payloads": payload_chunk},
                ),
                expected_results=int(len(payload_chunk)),
            )
        )
    return split_requests


def merge_fg_breakpoint_split_results(
    split_requests: list[FgBreakpointSplitRequest],
    split_results: list[Any],
) -> list[Any]:
    if int(len(split_results)) != int(len(split_requests)):
        raise RuntimeError("split FG request chunk count mismatch")

    merged_results: list[Any] = []
    for split_request, split_result in zip(split_requests, split_results):
        if not isinstance(split_result, list):
            raise TypeError("split FG request returned non-list result")
        if int(len(split_result)) != int(split_request.expected_results):
            raise RuntimeError("split FG request length mismatch")
        merged_results.extend(split_result)
    return merged_results
