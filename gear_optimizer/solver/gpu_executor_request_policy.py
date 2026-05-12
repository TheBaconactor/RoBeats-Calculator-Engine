from __future__ import annotations

from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequestType


FG_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_RESET_GLOBAL_BEST,
        GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
        GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH,
        GpuRequestType.FG_COMPUTE_BREAKPOINTS,
    }
)

# Downstream FG service work must not stay buried behind unrelated full-song GA turns.
GA_RECOVERY_REQUEST_TYPES = frozenset(FG_REQUEST_TYPES)

COALESCABLE_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
    }
)

# Full-song native GA requests unlock downstream decode/FG work for the same song.
# Keep them as one-request owner turns; the per-request kernels still batch internally.
NO_BATCH_REQUEST_TYPES = frozenset({GpuRequestType.GPU_NATIVE_GA_RUN})

NO_BATCH_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in NO_BATCH_REQUEST_TYPES})
GA_RECOVERY_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in GA_RECOVERY_REQUEST_TYPES})


def request_type_in(request_type: Any, request_types: frozenset[GpuRequestType], request_type_values: frozenset[str]) -> bool:
    if request_type in request_types:
        return True
    try:
        value = str(getattr(request_type, "value", request_type))
    except (AttributeError, TypeError):
        value = ""
    return value in request_type_values


def is_no_batch_request_type(request_type: Any) -> bool:
    return request_type_in(request_type, NO_BATCH_REQUEST_TYPES, NO_BATCH_REQUEST_TYPE_VALUES)


def is_ga_recovery_request_type(request_type: Any) -> bool:
    return request_type_in(request_type, GA_RECOVERY_REQUEST_TYPES, GA_RECOVERY_REQUEST_TYPE_VALUES)
