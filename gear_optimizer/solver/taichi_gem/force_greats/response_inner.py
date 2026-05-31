"""FG response-inner scoring: thin re-exports for callers and tests."""

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem import api as gem_api

_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK = 1_000_000_000
_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK = 100_000
_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS = 262_144
_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS = 262_144
_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK = 16_000_000_000

from .response_inner_kernels import (
    _fg_response_inner_batch_kernel,
    _fg_response_inner_group_kernel,
)
from .response_inner_host import (
    _optimize_response_surfaces_gpu,
    _precompute_surface_head_coeffs,
    _response_group_logical_surface_plan,
    _response_inner_combo_count,
    _response_inner_combo_counts,
    _score_response_group_meta_gpu,
    optimize_response_frontier_inner_exact_gpu,
)
from .response_inner_reference import optimize_response_frontier_inner_exact

__all__ = [
    "_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS",
    "_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK",
    "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS",
    "_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK",
    "_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK",
    "_fg_response_inner_batch_kernel",
    "_fg_response_inner_group_kernel",
    "_optimize_response_surfaces_gpu",
    "_precompute_surface_head_coeffs",
    "_response_group_logical_surface_plan",
    "_response_inner_combo_count",
    "_response_inner_combo_counts",
    "_score_response_group_meta_gpu",
    "gem_api",
    "np",
    "optimize_response_frontier_inner_exact",
    "optimize_response_frontier_inner_exact_gpu",
    "ti",
]
