"""Canonical FG response-frontier scoring surface (plan → score → reduce)."""

__all__ = [
    "FgPlanner",
    "FgResponseFrontierPreparedBatch",
    "FgResponseFrontierPreparedPlan",
    "FgResponseScoringService",
    "FgResultReducer",
    "GpuResponseKernelRunner",
    "GpuScoreEngine",
    "ResponseFrontierStore",
    "materialize_force_payload_from_response_frontier",
]

_EXPORT_MODULES = {
    "FgPlanner": "gear_optimizer.solver.fg_response_scoring.planner",
    "FgResponseFrontierPreparedBatch": "gear_optimizer.solver.fg_response_scoring.planner",
    "FgResponseFrontierPreparedPlan": "gear_optimizer.solver.fg_response_scoring.planner",
    "FgResponseScoringService": "gear_optimizer.solver.fg_response_scoring.service",
    "FgResultReducer": "gear_optimizer.solver.fg_response_scoring.reducer",
    "GpuResponseKernelRunner": "gear_optimizer.solver.fg_response_scoring.gpu_kernel_runner",
    "GpuScoreEngine": "gear_optimizer.solver.fg_response_scoring.gpu_engine",
    "ResponseFrontierStore": "gear_optimizer.solver.fg_response_scoring.store",
    "materialize_force_payload_from_response_frontier": "gear_optimizer.solver.fg_response_scoring.reducer",
}


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module_name), name)
