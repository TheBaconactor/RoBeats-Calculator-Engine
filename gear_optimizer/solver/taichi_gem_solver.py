"""
Taichi Gem Solver - stable facade.

This module intentionally keeps the historical import surface:
    from gear_optimizer.solver.taichi_gem_solver import ...

The implementation for the gem solver lives in the modular subpackage:
    gear_optimizer.solver.taichi_gem

ForceGreatsFinder GPU support lives in the modular subpackage:
    gear_optimizer.solver.taichi_gem.force_greats
"""

from __future__ import annotations

# NOTE: This facade is intentionally *lazy*.
#
# Importing Taichi can be slow and, in some environments, appear "hung" while the
# Vulkan runtime/driver initializes. To keep `import gear_optimizer.solver.taichi_gem_solver`
# lightweight and IDE-friendly, we avoid importing the heavy implementation modules
# at import time and instead import them only when the functions are actually called.


def init_taichi_vulkan(*args, **kwargs):
    from .gpu_executor import is_gpu_worker_mode

    if is_gpu_worker_mode():
        # In worker mode, GPU ownership is centralized in GpuExecutor (main process).
        return None
    from .taichi_gem.runtime import init_taichi_vulkan as _impl

    return _impl(*args, **kwargs)


def load_ref_arrays(*args, **kwargs):
    from .gpu_executor import is_gpu_worker_mode, submit_gpu_load_ref_arrays

    if is_gpu_worker_mode():
        # Keep signature compatibility: allow positional or keyword `ref_arrays`.
        if args:
            ref_arrays = args[0]
        else:
            ref_arrays = kwargs.get("ref_arrays")
        if ref_arrays is None:
            raise TypeError("load_ref_arrays missing required argument: ref_arrays")
        return submit_gpu_load_ref_arrays(ref_arrays)
    from .taichi_gem.api import load_ref_arrays as _impl

    return _impl(*args, **kwargs)


def solve_genomes_with_ftff(*args, **kwargs):
    from .gpu_executor import is_gpu_worker_mode

    if is_gpu_worker_mode():
        raise RuntimeError("solve_genomes_with_ftff is not supported in GPU worker mode")
    from .taichi_gem.api import solve_genomes_with_ftff as _impl

    return _impl(*args, **kwargs)


def solve_genomes_parallel(*args, **kwargs):
    from .gpu_executor import is_gpu_worker_mode, submit_gpu_solve_genomes

    if is_gpu_worker_mode():
        return submit_gpu_solve_genomes(*args, **kwargs)
    from .taichi_gem.api import solve_genomes_parallel as _impl

    return _impl(*args, **kwargs)


# Compatibility convenience: some code may have imported FG solver from the facade.
# We intentionally keep it out of __all__ (since it's not part of the stable surface),
# but it remains available as an attribute.
def solve_force_greats_finder_gpu(*args, **kwargs):
    from .gpu_executor import (
        is_gpu_worker_mode,
        is_in_process_gpu_request_queue,
        submit_gpu_solve_force_greats_finder,
    )

    if is_gpu_worker_mode() and is_in_process_gpu_request_queue():
        return submit_gpu_solve_force_greats_finder(*args, **kwargs)
    from .taichi_gem.force_greats.api import solve_force_greats_finder_gpu as _impl

    return _impl(*args, **kwargs)


__all__ = [
    "init_taichi_vulkan",
    "load_ref_arrays",
    "solve_genomes_with_ftff",
    "solve_genomes_parallel",
]
