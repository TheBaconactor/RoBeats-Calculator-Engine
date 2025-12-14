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


def optimize_gems_gpu(*args, **kwargs):
    from .gpu_executor import is_gpu_worker_mode
    if is_gpu_worker_mode():
        from .gpu_executor import submit_gpu_optimize_gems_batch

        # Keep compatibility with the historical positional API.
        if args:
            (
                budget,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
                cur_pp,
                cur_cm,
                cur_fm,
                cur_p_val,
                cur_s_val,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                ref_arrays,
            ) = args
        else:
            budget = kwargs["budget"]
            fever_mask_head = kwargs["fever_mask_head"]
            count_body_fever = kwargs["count_body_fever"]
            count_body_normal = kwargs["count_body_normal"]
            cur_pp = kwargs["cur_pp"]
            cur_cm = kwargs["cur_cm"]
            cur_fm = kwargs["cur_fm"]
            cur_p_val = kwargs["cur_p_val"]
            cur_s_val = kwargs["cur_s_val"]
            is_p_pp = kwargs["is_p_pp"]
            is_s_pp = kwargs["is_s_pp"]
            is_p_cm = kwargs["is_p_cm"]
            is_s_cm = kwargs["is_s_cm"]
            is_p_fm = kwargs["is_p_fm"]
            is_s_fm = kwargs["is_s_fm"]
            is_p_ov = kwargs["is_p_ov"]
            is_s_ov = kwargs["is_s_ov"]
            ref_arrays = kwargs["ref_arrays"]

        batch_input = [
            {
                "budget": int(budget),
                "fever_mask_head": fever_mask_head,
                "count_body_fever": int(count_body_fever),
                "count_body_normal": int(count_body_normal),
                "ft_gems": 0,
                "ff_gems": 0,
            }
        ]

        results = submit_gpu_optimize_gems_batch(
            batch_input,
            int(cur_pp),
            int(cur_cm),
            int(cur_fm),
            base_p_val=int(cur_p_val),
            base_s_val=int(cur_s_val),
            is_p_ft=0,
            is_s_ft=0,
            is_p_ff=0,
            is_s_ff=0,
            is_p_pp=int(is_p_pp),
            is_s_pp=int(is_s_pp),
            is_p_cm=int(is_p_cm),
            is_s_cm=int(is_s_cm),
            is_p_fm=int(is_p_fm),
            is_s_fm=int(is_s_fm),
            is_p_ov=int(is_p_ov),
            is_s_ov=int(is_s_ov),
            ref_arrays=ref_arrays,
        )
        return results[0] if results else None
    from .taichi_gem.api import optimize_gems_gpu as _impl
    return _impl(*args, **kwargs)


def optimize_gems_batch_gpu(*args, **kwargs):
    from .gpu_executor import is_gpu_worker_mode, submit_gpu_optimize_gems_batch
    if is_gpu_worker_mode():
        return submit_gpu_optimize_gems_batch(*args, **kwargs)
    from .taichi_gem.api import optimize_gems_batch_gpu as _impl
    return _impl(*args, **kwargs)


def mega_batch_solve_population(*args, **kwargs):
    from .gpu_executor import is_gpu_worker_mode
    if is_gpu_worker_mode():
        raise RuntimeError("mega_batch_solve_population is not supported in GPU worker mode")
    from .taichi_gem.api import mega_batch_solve_population as _impl
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
    from .taichi_gem.force_greats.api import solve_force_greats_finder_gpu as _impl
    return _impl(*args, **kwargs)

__all__ = [
    "init_taichi_vulkan",
    "load_ref_arrays",
    "optimize_gems_gpu",
    "optimize_gems_batch_gpu",
    "mega_batch_solve_population",
    "solve_genomes_with_ftff",
    "solve_genomes_parallel",
]
