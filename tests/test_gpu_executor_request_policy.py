from types import SimpleNamespace

from gear_optimizer.solver.gpu_executor_batching import (
    COALESCABLE_REQUEST_TYPES,
    FG_REQUEST_TYPES,
    GA_RECOVERY_REQUEST_TYPES,
    NO_BATCH_REQUEST_TYPES,
    is_ga_recovery_request,
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
    assert is_ga_recovery_request(SimpleNamespace(request_type=request_type))


def test_gpu_native_ga_is_the_only_no_batch_owner_turn():
    assert NO_BATCH_REQUEST_TYPES == frozenset({GpuRequestType.GPU_NATIVE_GA_RUN})
    assert is_no_batch_request_type(GpuRequestType.GPU_NATIVE_GA_RUN)
    assert is_no_batch_request_type(GpuRequestType.GPU_NATIVE_GA_RUN.value)
    assert not is_no_batch_request_type(GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS)


def test_request_policy_module_owns_policy_sets():
    assert GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS in FG_REQUEST_TYPES
    assert GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS in GA_RECOVERY_REQUEST_TYPES
    assert GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS in COALESCABLE_REQUEST_TYPES
    assert GpuRequestType.GPU_NATIVE_GA_RUN in NO_BATCH_REQUEST_TYPES
