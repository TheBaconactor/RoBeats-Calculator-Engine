from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse


@dataclass(frozen=True)
class RegistrySolveResult:
    response: GpuResponse
    last_ref_arrays_sig: bytes | None


def request_song_slot(request: GpuRequest) -> int:
    payload = request.payload if isinstance(getattr(request, "payload", None), dict) else {}
    try:
        return int(payload.get("song_slot", 0) or 0)
    except (ValueError, TypeError):
        return 0


def handle_solve_genomes_from_registry(
    request: GpuRequest,
    *,
    execute_fn: Callable[[GpuRequest, int], GpuResponse],
) -> GpuResponse:
    return execute_fn(request, request_song_slot(request))


def execute_solve_genomes_from_registry(
    request: GpuRequest,
    *,
    song_slot: int,
    in_process_queues: bool,
    last_ref_arrays_sig: bytes | None,
    resolve_payload_fn: Callable[[GpuRequest], tuple[dict[str, Any], str | None]],
    ref_arrays_sig_fn: Callable[[Any], bytes | None],
    default_song_slot_for_worker_fn: Callable[[int], int],
    load_ref_arrays_fn: Callable[[dict[str, Any]], Any],
    ga_upload_item_stats_fn: Callable[..., Any],
    ga_upload_base_fixed_stats_fn: Callable[..., Any],
    solve_genomes_from_registry_fn: Callable[..., Any],
) -> RegistrySolveResult:
    payload, resolve_err = resolve_payload_fn(request)
    if resolve_err:
        return RegistrySolveResult(
            response=GpuResponse(
                request_id=request.request_id,
                success=False,
                error=resolve_err,
            ),
            last_ref_arrays_sig=last_ref_arrays_sig,
        )

    current_ref_arrays_sig = last_ref_arrays_sig
    if "ref_arrays" in payload:
        ref_arrays = payload["ref_arrays"]
        sig = ref_arrays_sig_fn(ref_arrays)
        if sig is None or sig != current_ref_arrays_sig:
            load_ref_arrays_fn(ref_arrays)
            current_ref_arrays_sig = sig

    if "item_stats" in payload and "slot_start" in payload and "slot_count" in payload:
        ga_upload_item_stats_fn(payload["item_stats"], payload["slot_start"], payload["slot_count"])

    if "base_fixed_stats" in payload:
        ga_upload_base_fixed_stats_fn(payload["base_fixed_stats"])

    resolved_song_slot = int(payload.get("song_slot", song_slot) or 0)
    if (
        resolved_song_slot == 0
        and (not in_process_queues)
        and request.worker_id is not None
        and isinstance(payload.get("timeline_grid"), dict)
    ):
        resolved_song_slot = int(default_song_slot_for_worker_fn(int(request.worker_id)))

    results = solve_genomes_from_registry_fn(
        population_indices=payload["population_indices"],
        timeline_grid=payload["timeline_grid"],
        is_p_ft=payload["is_p_ft"],
        is_s_ft=payload["is_s_ft"],
        is_p_ff=payload["is_p_ff"],
        is_s_ff=payload["is_s_ff"],
        is_p_pp=payload["is_p_pp"],
        is_s_pp=payload["is_s_pp"],
        is_p_cm=payload["is_p_cm"],
        is_s_cm=payload["is_s_cm"],
        is_p_fm=payload["is_p_fm"],
        is_s_fm=payload["is_s_fm"],
        is_p_ov=payload["is_p_ov"],
        is_s_ov=payload["is_s_ov"],
        ref_arrays=payload["ref_arrays"],
        total_budget=payload.get("total_budget", 90),
        gem_scale_fever=payload.get("gem_scale_fever", 3),
        song_slot=resolved_song_slot,
        use_exact_inner_solver=bool(payload.get("use_exact_inner_solver", 1)),
    )

    return RegistrySolveResult(
        response=GpuResponse(
            request_id=request.request_id,
            success=True,
            result=results,
        ),
        last_ref_arrays_sig=current_ref_arrays_sig,
    )
