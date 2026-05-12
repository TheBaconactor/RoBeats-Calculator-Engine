from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_request_policy import (
    COALESCABLE_REQUEST_TYPES,
    FG_REQUEST_TYPES,
    GA_RECOVERY_REQUEST_TYPES,
    NO_BATCH_REQUEST_TYPES,
    is_ga_recovery_request_type,
    is_no_batch_request_type,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequestType


def test_fused_ga_fg_request_is_fg_recovery_and_coalescable():
    request_type = GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS

    assert request_type in FG_REQUEST_TYPES
    assert request_type in GA_RECOVERY_REQUEST_TYPES
    assert request_type in COALESCABLE_REQUEST_TYPES
    assert is_ga_recovery_request_type(request_type)
    assert is_ga_recovery_request_type(request_type.value)


def test_gpu_native_ga_is_the_only_no_batch_owner_turn():
    assert NO_BATCH_REQUEST_TYPES == frozenset({GpuRequestType.GPU_NATIVE_GA_RUN})
    assert is_no_batch_request_type(GpuRequestType.GPU_NATIVE_GA_RUN)
    assert is_no_batch_request_type(GpuRequestType.GPU_NATIVE_GA_RUN.value)
    assert not is_no_batch_request_type(GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS)


def test_gpu_executor_keeps_policy_aliases_for_compatibility():
    assert GpuExecutor._FG_REQUEST_TYPES is FG_REQUEST_TYPES
    assert GpuExecutor._GA_RECOVERY_REQUEST_TYPES is GA_RECOVERY_REQUEST_TYPES
    assert GpuExecutor._COALESCABLE_REQUEST_TYPES is COALESCABLE_REQUEST_TYPES
    assert GpuExecutor._NO_BATCH_REQUEST_TYPES is NO_BATCH_REQUEST_TYPES
    assert GpuExecutor._is_ga_recovery_request_type(GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS.value)
    assert GpuExecutor._is_no_batch_request_type(GpuRequestType.GPU_NATIVE_GA_RUN.value)
    assert GpuExecutor._is_ga_recovery_request_type(
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS.value
    ) == is_ga_recovery_request_type(GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS.value)
    assert GpuExecutor._is_no_batch_request_type(GpuRequestType.GPU_NATIVE_GA_RUN.value) == is_no_batch_request_type(
        GpuRequestType.GPU_NATIVE_GA_RUN.value
    )
