from __future__ import annotations

from .fields import GpuFullSolution, _GpuFullIslandsState, _GpuFullState, _get_or_build_islands_state, _get_or_build_state
from .primitives import _stripe_idx, _xorshift32

__all__ = [
    "GpuFullSolution",
    "_GpuFullIslandsState",
    "_GpuFullState",
    "_get_or_build_islands_state",
    "_get_or_build_state",
    "_solve_coverage_gpu_full_alns_islands",
    "_stripe_idx",
    "_xorshift32",
    "solve_coverage_gpu_full",
]


def __getattr__(name: str):
    if name == "solve_coverage_gpu_full":
        from .solver_single import solve_coverage_gpu_full

        return solve_coverage_gpu_full
    if name == "_solve_coverage_gpu_full_alns_islands":
        from .solver_islands import _solve_coverage_gpu_full_alns_islands

        return _solve_coverage_gpu_full_alns_islands
    raise AttributeError(name)


def solve_coverage_gpu_full(*args, **kwargs):
    from .solver_single import solve_coverage_gpu_full as _solve

    return _solve(*args, **kwargs)


def _solve_coverage_gpu_full_alns_islands(*args, **kwargs):
    from .solver_islands import _solve_coverage_gpu_full_alns_islands as _solve

    return _solve(*args, **kwargs)
