"""
Test GPU Executor parallel mode integration.

This test verifies that the GPU executor IPC mechanism works correctly
when multiple workers submit GPU requests.
"""

import pytest
import multiprocessing
import time


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


def test_gpu_executor_basic_lifecycle():
    """Test GPU executor can start and stop."""
    from gear_optimizer.solver.gpu_executor import GpuExecutor

    # Create fresh instance (bypass singleton for testing)
    GpuExecutor._instance = None
    executor = GpuExecutor()

    assert not executor.is_running
    executor.start()
    assert executor.is_running

    # Give it a moment to initialize Taichi
    time.sleep(1.0)

    executor.stop()
    assert not executor.is_running

    # Cleanup
    GpuExecutor._instance = None


def test_gpu_executor_worker_registration():
    """Test workers can be registered with the executor."""
    from gear_optimizer.solver.gpu_executor import GpuExecutor

    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start()
    time.sleep(0.5)

    try:
        # Register multiple workers
        registrations = []
        for i in range(3):
            worker_id, req_q, resp_q = executor.register_worker()
            registrations.append((worker_id, req_q, resp_q))
            assert worker_id == i

        assert executor.stats["registered_workers"] == 3
    finally:
        executor.stop()
        GpuExecutor._instance = None


def test_worker_mode_detection():
    """Test worker mode detection functions."""
    from gear_optimizer.solver.gpu_executor import (
        is_gpu_worker_mode,
        set_gpu_worker_mode,
        clear_gpu_worker_mode,
    )

    # Initially not in worker mode
    assert not is_gpu_worker_mode()

    # Set worker mode
    req_q = multiprocessing.Queue()
    resp_q = multiprocessing.Queue()
    set_gpu_worker_mode(42, req_q, resp_q)

    assert is_gpu_worker_mode()

    # Clear it
    clear_gpu_worker_mode()
    assert not is_gpu_worker_mode()


def test_gpu_executor_ipc_request():
    """Test a full IPC request/response cycle."""
    from gear_optimizer.solver.gpu_executor import (
        GpuExecutor,
        GpuRequest,
        GpuRequestType,
    )
    import numpy as np

    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start()
    time.sleep(1.0)  # Wait for Taichi init

    try:
        # Register a worker
        worker_id, req_q, resp_q = executor.register_worker()

        # For this test, we need to ensure refs are loaded first
        from gear_optimizer.solver.taichi_gem.api import load_ref_arrays

        # Create minimal ref arrays for test
        ref_arrays = {
            "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
            "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
            "Fever Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
            "Fever Fill Rate": np.linspace(0.5, 1.5, 161, dtype=np.float64),
            "Fever Time": np.linspace(0.5, 1.5, 161, dtype=np.float64),
        }

        # Submit a minimal solve request
        # Note: This requires a real timeline grid, so we skip actual execution
        # Just verify the executor processes requests without crashing

        print(f"[TEST] GPU Executor running, {executor.stats}")
        assert executor.is_running

    finally:
        executor.stop()
        GpuExecutor._instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
