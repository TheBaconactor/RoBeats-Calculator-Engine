from __future__ import annotations

__all__ = [
    "GpuFullSolution",
    "GpuRepairResult",
    "_GpuFullIslandsState",
    "_GpuFullState",
    "_get_or_build_islands_state",
    "_get_or_build_state",
    "_solve_coverage_gpu_full_alns_islands",
    "_stripe_idx",
    "_xorshift32",
    "build_witness_offsets_gpu",
    "repair_uncovered_with_inventory_gpu",
    "solve_coverage_gpu_full",
]


def __getattr__(name: str):
    if name in {"GpuFullSolution", "_GpuFullIslandsState", "_GpuFullState", "_get_or_build_islands_state", "_get_or_build_state"}:
        from .fields import GpuFullSolution, _GpuFullIslandsState, _GpuFullState, _get_or_build_islands_state, _get_or_build_state

        return {
            "GpuFullSolution": GpuFullSolution,
            "_GpuFullIslandsState": _GpuFullIslandsState,
            "_GpuFullState": _GpuFullState,
            "_get_or_build_islands_state": _get_or_build_islands_state,
            "_get_or_build_state": _get_or_build_state,
        }[name]
    if name in {"_stripe_idx", "_xorshift32"}:
        from .primitives import _stripe_idx, _xorshift32

        return {"_stripe_idx": _stripe_idx, "_xorshift32": _xorshift32}[name]
    if name == "solve_coverage_gpu_full":
        from .solver_single import solve_coverage_gpu_full

        return solve_coverage_gpu_full
    if name == "_solve_coverage_gpu_full_alns_islands":
        from .solver_islands import _solve_coverage_gpu_full_alns_islands

        return _solve_coverage_gpu_full_alns_islands
    if name == "build_witness_offsets_gpu":
        from .witness_kernels import build_witness_offsets_gpu

        return build_witness_offsets_gpu
    if name == "repair_uncovered_with_inventory_gpu":
        from .repair_kernels import repair_uncovered_with_inventory_gpu

        return repair_uncovered_with_inventory_gpu
    if name == "GpuRepairResult":
        from .repair import GpuRepairResult

        return GpuRepairResult
    raise AttributeError(name)
