"""GPU executor handler for native GA requests."""

from __future__ import annotations

from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse


def execute_gpu_native_ga_run(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    abort_requested: Callable[[], bool],
    raise_if_abort_requested: Callable[[], None],
    run_payload_fn: Callable[..., Any] | None = None,
) -> GpuResponse:
    if not bool(in_process_queues):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="GPU_NATIVE_GA_RUN requires in-process queues (avoid IPC pickling)",
        )

    try:
        raise_if_abort_requested()
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=str(e),
        )

    payload = request.payload or {}
    calc_song = payload.get("calc_song")
    ref_arrays = payload.get("ref_arrays")
    item_stats = payload.get("item_stats")
    slot_start = payload.get("slot_start")
    slot_count = payload.get("slot_count")
    base_fixed_stats_arr = payload.get("base_fixed_stats_arr")
    initial_populations = payload.get("initial_populations")
    num_runs = payload.get("num_runs")
    n_genomes = payload.get("n_genomes")
    init_heuristic_topk = payload.get("init_heuristic_topk")
    init_heuristic_k = payload.get("init_heuristic_k", 0)
    init_heuristic_copies = payload.get("init_heuristic_copies", 25)
    song_slot = int(payload.get("song_slot", 0) or 0)
    n_generations = int(payload.get("n_generations", 1) or 1)
    elite_count = int(payload.get("elite_count", 2) or 2)
    mutation_rate = float(payload.get("mutation_rate", 0.02) or 0.02)
    immigrant_rate = float(payload.get("immigrant_rate", 0.0) or 0.0)
    tournament_k = int(payload.get("tournament_k", 3) or 3)
    color_flags = payload.get("color_flags") or {}
    cfg_data = payload.get("cfg_data") or {}
    ga_seed = payload.get("ga_seed")

    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="Invalid payload for GPU_NATIVE_GA_RUN (expected calc_song/ref_arrays dicts)",
        )

    try:
        if run_payload_fn is None:
            from gear_optimizer.solver.genetic import run_gpu_native_ga_runs_payload_prebuilt as run_payload_fn

        kwargs = dict(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=song_slot,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            n_generations=n_generations,
            initial_populations=initial_populations,
            num_runs=int(num_runs) if num_runs is not None else None,
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_k=int(init_heuristic_k or 0),
            init_heuristic_copies=int(init_heuristic_copies or 0),
            elite_count=elite_count,
            mutation_rate=mutation_rate,
            immigrant_rate=immigrant_rate,
            tournament_k=tournament_k,
            color_flags=dict(color_flags),
            cfg_data=dict(cfg_data),
            ga_seed=int(ga_seed) if ga_seed is not None else None,
            abort_requested=abort_requested,
        )
        if n_genomes is not None:
            kwargs["n_genomes"] = int(n_genomes)
        runs_payload = run_payload_fn(**kwargs)
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=f"{type(e).__name__}: {e}",
        )

    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=runs_payload,
    )
