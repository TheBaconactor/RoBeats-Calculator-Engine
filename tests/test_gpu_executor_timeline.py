from gear_optimizer.solver.gpu_executor_types import GpuRequestType


def test_precompute_timeline_request_type_removed_from_executor_api_surface():
    assert not hasattr(GpuRequestType, "PRECOMPUTE_TIMELINE")
    assert "precompute_timeline_gpu" not in {str(rt.value) for rt in GpuRequestType}
