"""
GPU Executor - Cross-process GPU ownership for parallel song processing.

Architecture:
    Song Workers (CPU) --IPC Queue--> GpuExecutor (GPU owner) --> RX 7900 XTX
    
This ensures only ONE process initializes Taichi/Vulkan, preventing:
- Multiple GPU contexts fighting for resources
- Wasted GPU memory from duplicate Taichi inits
- Potential Vulkan driver conflicts

Usage:
    # In main process before spawning workers:
    executor = get_gpu_executor()
    executor.start()
    
    # In worker processes:
    if is_gpu_worker_mode():
        result = submit_gpu_work(...)
    
    # After workers complete:
    executor.stop()
"""

import multiprocessing
import threading
import queue
import os
import traceback
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
from enum import Enum


class GpuRequestType(Enum):
    """Types of GPU requests that can be submitted."""
    SOLVE_GENOMES_PARALLEL = "solve_genomes_parallel"
    LOAD_REF_ARRAYS = "load_ref_arrays"
    SHUTDOWN = "shutdown"


@dataclass
class GpuRequest:
    """A request to execute on the GPU executor."""
    request_type: GpuRequestType
    request_id: int
    worker_id: int
    payload: Dict[str, Any]


@dataclass
class GpuResponse:
    """Response from GPU executor."""
    request_id: int
    success: bool
    result: Any = None
    error: Optional[str] = None


# Global state for worker processes
_WORKER_MODE = False
_WORKER_ID: Optional[int] = None
_REQUEST_QUEUE: Optional[multiprocessing.Queue] = None
_RESPONSE_QUEUE: Optional[multiprocessing.Queue] = None
_REQUEST_COUNTER = 0


def set_gpu_worker_mode(worker_id: int, request_queue, response_queue):
    """Configure this process as a GPU worker (called after fork/spawn)."""
    global _WORKER_MODE, _WORKER_ID, _REQUEST_QUEUE, _RESPONSE_QUEUE
    _WORKER_MODE = True
    _WORKER_ID = worker_id
    _REQUEST_QUEUE = request_queue
    _RESPONSE_QUEUE = response_queue


def is_gpu_worker_mode() -> bool:
    """Check if running in worker mode (should use IPC for GPU)."""
    return _WORKER_MODE


def clear_gpu_worker_mode():
    """Clear worker mode (for testing or process reuse)."""
    global _WORKER_MODE, _WORKER_ID, _REQUEST_QUEUE, _RESPONSE_QUEUE
    _WORKER_MODE = False
    _WORKER_ID = None
    _REQUEST_QUEUE = None
    _RESPONSE_QUEUE = None


class GpuExecutor:
    """
    Single GPU owner process that handles all Taichi kernel execution.
    
    Song worker processes submit requests via IPC queue, which are executed
    serially on the GPU thread for maximum throughput.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._request_queue: Optional[multiprocessing.Queue] = None
        self._response_queues: Dict[int, multiprocessing.Queue] = {}
        self._executor_thread: Optional[threading.Thread] = None
        self._running = False
        self._next_worker_id = 0
        self._initialized = True
        self._taichi_ready = False
        
        # Stats
        self._requests_processed = 0
    
    def start(self):
        """Start the GPU executor thread in the main process."""
        if self._running:
            return
        
        self._request_queue = multiprocessing.Queue()
        self._running = True
        
        # Run in thread (not process) so we stay in main process
        self._executor_thread = threading.Thread(
            target=self._executor_loop,
            name="GpuExecutorThread",
            daemon=True,
        )
        self._executor_thread.start()
        print("[GpuExecutor] Started")
    
    def stop(self):
        """Stop the GPU executor."""
        if not self._running:
            return
        
        # Send shutdown request
        shutdown_req = GpuRequest(
            request_type=GpuRequestType.SHUTDOWN,
            request_id=-1,
            worker_id=-1,
            payload={},
        )
        self._request_queue.put(shutdown_req)
        
        # Wait for thread to finish
        if self._executor_thread:
            self._executor_thread.join(timeout=10.0)
        
        self._running = False
        print(f"[GpuExecutor] Stopped. Processed {self._requests_processed} requests.")
    
    def register_worker(self) -> tuple:
        """
        Register a new worker and get its communication queues.
        
        Returns:
            (worker_id, request_queue, response_queue)
        """
        worker_id = self._next_worker_id
        self._next_worker_id += 1
        
        response_queue = multiprocessing.Queue()
        self._response_queues[worker_id] = response_queue
        
        return worker_id, self._request_queue, response_queue
    
    def unregister_worker(self, worker_id: int):
        """Unregister a worker (cleanup)."""
        if worker_id in self._response_queues:
            del self._response_queues[worker_id]
    
    def _executor_loop(self):
        """Main GPU execution loop - runs in dedicated thread."""
        # Initialize Taichi ONCE
        try:
            from .taichi_gem.runtime import init_taichi_vulkan
            init_taichi_vulkan()
            self._taichi_ready = True
            print("[GpuExecutor] Taichi initialized")
        except Exception as e:
            print(f"[GpuExecutor] Taichi init failed: {e}")
            return
        
        while self._running:
            try:
                # Get request with timeout
                request = self._request_queue.get(timeout=0.1)
                
                if request.request_type == GpuRequestType.SHUTDOWN:
                    break
                
                # Execute and send response
                response = self._execute_request(request)
                
                # Send response to the worker's queue
                if request.worker_id in self._response_queues:
                    self._response_queues[request.worker_id].put(response)
                
                self._requests_processed += 1
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[GpuExecutor] Error: {e}")
                traceback.print_exc()
    
    def _execute_request(self, request: GpuRequest) -> GpuResponse:
        """Execute a single GPU request."""
        try:
            if request.request_type == GpuRequestType.SOLVE_GENOMES_PARALLEL:
                return self._execute_solve_genomes(request)
            elif request.request_type == GpuRequestType.LOAD_REF_ARRAYS:
                return self._execute_load_refs(request)
            else:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"Unknown request type: {request.request_type}",
                )
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"{type(e).__name__}: {e}",
            )
    
    def _execute_solve_genomes(self, request: GpuRequest) -> GpuResponse:
        """Execute solve_genomes_parallel on GPU."""
        from .taichi_gem.api import solve_genomes_parallel, load_ref_arrays
        
        payload = request.payload
        
        # Load ref arrays if provided
        if "ref_arrays" in payload:
            load_ref_arrays(payload["ref_arrays"])
        
        # Run the solver
        results = solve_genomes_parallel(
            genome_stats_list=payload["genome_stats_list"],
            timeline_grid=payload["timeline_grid"],
            is_p_ft=payload["is_p_ft"],
            is_s_ft=payload["is_s_ft"],
            is_p_ff=payload["is_p_ff"],
            is_s_ff=payload["is_s_ff"],
            is_p_pp=payload["is_p_pp"],
            is_s_pp=payload["is_s_pp"],
            is_p_cm=payload["is_p_cm"],
            is_s_cm=payload["is_s_cm"],
            is_p_fm=payload["is_p_fm"],
            is_s_fm=payload["is_s_fm"],
            is_p_ov=payload["is_p_ov"],
            is_s_ov=payload["is_s_ov"],
            ref_arrays=payload["ref_arrays"],
            total_budget=payload.get("total_budget", 90),
            gem_scale_fever=payload.get("gem_scale_fever", 3),
        )
        
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=results,
        )
    
    def _execute_load_refs(self, request: GpuRequest) -> GpuResponse:
        """Load reference arrays."""
        from .taichi_gem.api import load_ref_arrays
        
        load_ref_arrays(request.payload["ref_arrays"])
        
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        )
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def stats(self) -> dict:
        return {
            "requests_processed": self._requests_processed,
            "registered_workers": len(self._response_queues),
        }


# Global executor instance
_executor: Optional[GpuExecutor] = None


def get_gpu_executor() -> GpuExecutor:
    """Get the global GPU executor instance."""
    global _executor
    if _executor is None:
        _executor = GpuExecutor()
    return _executor


def submit_gpu_solve_genomes(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    timeout: float = 60.0,
) -> list:
    """
    Submit solve_genomes_parallel request via IPC (for worker processes).
    
    This is a blocking call that waits for the GPU executor to return results.
    
    Args:
        Same as solve_genomes_parallel
        timeout: Max seconds to wait for response
        
    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
        
    Raises:
        RuntimeError: If not in worker mode or timeout
    """
    global _REQUEST_COUNTER
    
    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_solve_genomes called but not in worker mode")
    
    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER
    
    request = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_PARALLEL,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={
            "genome_stats_list": genome_stats_list,
            "timeline_grid": timeline_grid,
            "is_p_ft": is_p_ft,
            "is_s_ft": is_s_ft,
            "is_p_ff": is_p_ff,
            "is_s_ff": is_s_ff,
            "is_p_pp": is_p_pp,
            "is_s_pp": is_s_pp,
            "is_p_cm": is_p_cm,
            "is_s_cm": is_s_cm,
            "is_p_fm": is_p_fm,
            "is_s_fm": is_s_fm,
            "is_p_ov": is_p_ov,
            "is_s_ov": is_s_ov,
            "ref_arrays": ref_arrays,
            "total_budget": total_budget,
            "gem_scale_fever": gem_scale_fever,
        },
    )
    
    # Submit request
    _REQUEST_QUEUE.put(request)
    
    # Wait for response
    try:
        response: GpuResponse = _RESPONSE_QUEUE.get(timeout=timeout)
    except queue.Empty:
        raise RuntimeError(f"GPU executor timeout after {timeout}s")
    
    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")
    
    return response.result
