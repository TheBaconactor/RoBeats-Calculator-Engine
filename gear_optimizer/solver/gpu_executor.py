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
import time
from collections import defaultdict
from time import perf_counter
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
from enum import Enum

from gear_optimizer.core.env_config import ENV


class GpuRequestType(Enum):
    """Types of GPU requests that can be submitted."""
    SOLVE_GENOMES_PARALLEL = "solve_genomes_parallel"
    OPTIMIZE_GEMS_BATCH = "optimize_gems_batch_gpu"
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
_PENDING_RESPONSES: Dict[int, "GpuResponse"] = {}


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
    global _WORKER_MODE, _WORKER_ID, _REQUEST_QUEUE, _RESPONSE_QUEUE, _PENDING_RESPONSES
    _WORKER_MODE = False
    _WORKER_ID = None
    _REQUEST_QUEUE = None
    _RESPONSE_QUEUE = None
    _PENDING_RESPONSES = {}


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
        from gear_optimizer.core.env_config import ENV
        self._profile_enabled = ENV.gpu_executor_profile
        self._wait_sec = 0.0
        self._exec_sec = 0.0
        self._req_type_counts = defaultdict(int)
        self._req_type_exec_sec = defaultdict(float)
    
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
        if self._profile_enabled:
            total = self._wait_sec + self._exec_sec
            util = (self._exec_sec / total * 100.0) if total > 0 else 0.0
            avg = (self._exec_sec / self._requests_processed) if self._requests_processed else 0.0
            top_types = sorted(
                self._req_type_exec_sec.items(), key=lambda kv: kv[1], reverse=True
            )[:6]
            top_types_str = ", ".join(
                f"{t.value}:{self._req_type_counts[t]} ({sec:.2f}s)"
                for t, sec in top_types
            )
            print(
                "[GpuExecutor][PROFILE] "
                f"wait={self._wait_sec:.2f}s exec={self._exec_sec:.2f}s util={util:.1f}% "
                f"avg_exec_per_req={avg:.3f}s types=[{top_types_str}]"
            )
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
        """Main GPU execution loop with batch coalescing."""
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
                # Gather batch of pending requests (wait up to 10ms for more)
                t_wait0 = perf_counter()
                batch = self._gather_batch(max_wait_ms=10, max_batch_size=8)
                self._wait_sec += perf_counter() - t_wait0
                
                if not batch:
                    continue
                
                # Check for shutdown
                if any(r.request_type == GpuRequestType.SHUTDOWN for r in batch):
                    break
                
                # Group by request type
                solve_requests = [r for r in batch if r.request_type == GpuRequestType.SOLVE_GENOMES_PARALLEL]
                other_requests = [r for r in batch if r.request_type != GpuRequestType.SOLVE_GENOMES_PARALLEL]
                
                # Execute solve_genomes requests (true batched kernel execution when possible)
                if solve_requests:
                    if len(solve_requests) > 1:
                        t_exec0 = perf_counter()
                        responses = self._execute_solve_batch(solve_requests)
                        dt_exec = perf_counter() - t_exec0
                        # Attribute exec time proportionally (for profiling only)
                        per_req = dt_exec / max(1, len(solve_requests))
                        self._exec_sec += dt_exec
                        for _ in solve_requests:
                            self._req_type_counts[GpuRequestType.SOLVE_GENOMES_PARALLEL] += 1
                            self._req_type_exec_sec[GpuRequestType.SOLVE_GENOMES_PARALLEL] += per_req

                        # Dispatch responses back to originating workers
                        for req, resp in zip(solve_requests, responses):
                            if req.worker_id in self._response_queues:
                                self._response_queues[req.worker_id].put(resp)
                            self._requests_processed += 1
                    else:
                        req = solve_requests[0]
                        t_exec0 = perf_counter()
                        response = self._execute_request(req)
                        dt_exec = perf_counter() - t_exec0
                        self._exec_sec += dt_exec
                        self._req_type_counts[req.request_type] += 1
                        self._req_type_exec_sec[req.request_type] += dt_exec

                        if req.worker_id in self._response_queues:
                            self._response_queues[req.worker_id].put(response)
                        self._requests_processed += 1

                
                # Process other request types individually
                for req in other_requests:
                    t_exec0 = perf_counter()
                    response = self._execute_request(req)
                    dt_exec = perf_counter() - t_exec0
                    self._exec_sec += dt_exec
                    self._req_type_counts[req.request_type] += 1
                    self._req_type_exec_sec[req.request_type] += dt_exec
                    
                    if req.worker_id in self._response_queues:
                        self._response_queues[req.worker_id].put(response)
                    self._requests_processed += 1
                
            except Exception as e:
                print(f"[GpuExecutor] Error: {e}")
                traceback.print_exc()
    
    def _gather_batch(self, max_wait_ms: int = 10, max_batch_size: int = 8) -> list:
        """
        Gather pending requests into a batch for coalesced execution.
        
        Args:
            max_wait_ms: Max time to wait for additional requests (ms)
            max_batch_size: Max requests per batch
            
        Returns:
            List of GpuRequest objects
        """
        batch = []
        deadline = perf_counter() + (max_wait_ms / 1000.0)
        
        while len(batch) < max_batch_size:
            remaining = deadline - perf_counter()
            if remaining <= 0 and len(batch) > 0:
                break  # Deadline passed, return what we have
            
            try:
                timeout = max(0.001, remaining) if len(batch) > 0 else 0.1
                request = self._request_queue.get(timeout=timeout)
                batch.append(request)
                
                # If shutdown, return immediately
                if request.request_type == GpuRequestType.SHUTDOWN:
                    return batch
                    
            except queue.Empty:
                break  # No more pending requests
        
        return batch
    
    def _execute_solve_batch(self, requests: list) -> list:
        """
        Execute multiple SOLVE_GENOMES_PARALLEL requests in a single batched kernel.
        
        Each request gets assigned a song_slot (0-7) for its grid data.
        All requests' genomes are combined into a mega-batch.
        
        Args:
            requests: List of GpuRequest objects (all SOLVE_GENOMES_PARALLEL)
            
        Returns:
            List of GpuResponse objects, one per request
        """
        from .taichi_gem.api import solve_genomes_parallel_merged

        # Partition into compatible batches (same budget/scales; ref arrays are checked by content in merged solver).
        groups: dict[tuple[int, int], list[GpuRequest]] = {}
        for req in requests:
            p = req.payload
            key = (int(p.get("total_budget", 90)), int(p.get("gem_scale_fever", 3)))
            groups.setdefault(key, []).append(req)

        out: list[GpuResponse] = []
        log_batches = ENV.gpu_batch_log
        for key, group in groups.items():
            # If group is too large for available slots, split further.
            max_slots = 8
            for start in range(0, len(group), max_slots):
                sub = group[start : start + max_slots]
                try:
                    if log_batches and len(sub) > 1:
                        print(f"[GpuExecutor][BATCH] requests={len(sub)} budget={int(sub[0].payload.get('total_budget', 90))} scale={int(sub[0].payload.get('gem_scale_fever', 3))}")
                    # Require calc_song dict inputs for true batching; otherwise fall back.
                    if any(not isinstance(r.payload.get("timeline_grid"), dict) for r in sub):
                        raise ValueError("non-dict timeline_grid in batch")

                    total_budget = int(sub[0].payload.get("total_budget", 90))
                    gem_scale_fever = int(sub[0].payload.get("gem_scale_fever", 3))
                    merged_results = solve_genomes_parallel_merged(
                        [r.payload for r in sub],
                        total_budget=total_budget,
                        gem_scale_fever=gem_scale_fever,
                    )
                    for req, res in zip(sub, merged_results):
                        out.append(GpuResponse(
                            request_id=req.request_id,
                            success=True,
                            result=res,
                        ))
                except Exception as e:
                    # Conservative fallback: process each request individually.
                    for req in sub:
                        try:
                            out.append(self._execute_solve_genomes(req, song_slot=0))
                        except Exception as e2:
                            out.append(GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error=f"{type(e2).__name__}: {e2}",
                            ))

        # Preserve original request order for caller.
        by_id = {r.request_id: r for r in out}
        return [by_id.get(req.request_id) for req in requests]

    
    def _execute_request(self, request: GpuRequest) -> GpuResponse:
        """Execute a single GPU request."""
        try:
            if request.request_type == GpuRequestType.SOLVE_GENOMES_PARALLEL:
                return self._execute_solve_genomes(request)
            elif request.request_type == GpuRequestType.OPTIMIZE_GEMS_BATCH:
                return self._execute_optimize_gems_batch(request)
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
    
    def _execute_solve_genomes(self, request: GpuRequest, song_slot: int = 0) -> GpuResponse:
        """Execute solve_genomes_parallel on GPU.
        
        Args:
            request: The GPU request
            song_slot: Grid slot to use for this song (0-7, default 0)
        """
        from .taichi_gem.api import solve_genomes_parallel, load_ref_arrays
        
        payload = request.payload
        
        # Load ref arrays if provided
        if "ref_arrays" in payload:
            load_ref_arrays(payload["ref_arrays"])
        
        # Run the solver with song_slot
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
            song_slot=song_slot,  # Pass song slot for batch coalescing
        )
        
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=results,
        )

    def _execute_optimize_gems_batch(self, request: GpuRequest) -> GpuResponse:
        """Execute optimize_gems_batch_gpu on GPU."""
        from .taichi_gem.api import optimize_gems_batch_gpu

        payload = request.payload
        results = optimize_gems_batch_gpu(
            payload["batch_input"],
            payload["cur_pp"],
            payload["cur_cm"],
            payload["cur_fm"],
            payload["base_p_val"],
            payload["base_s_val"],
            payload["is_p_ft"],
            payload["is_s_ft"],
            payload["is_p_ff"],
            payload["is_s_ff"],
            payload["is_p_pp"],
            payload["is_s_pp"],
            payload["is_p_cm"],
            payload["is_s_cm"],
            payload["is_p_fm"],
            payload["is_s_fm"],
            payload["is_p_ov"],
            payload["is_s_ov"],
            payload["ref_arrays"],
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
        out = {
            "requests_processed": self._requests_processed,
            "registered_workers": len(self._response_queues),
        }
        if self._profile_enabled:
            total = self._wait_sec + self._exec_sec
            out["profile"] = {
                "wait_sec": self._wait_sec,
                "exec_sec": self._exec_sec,
                "utilization_pct": (self._exec_sec / total * 100.0) if total > 0 else 0.0,
            }
        return out


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
        Same as solve_genomes_parallel. `timeline_grid` may be either:
        - a `SongTimelineGrid` instance (sequential mode), or
        - a lightweight `calc_song` dict with `metadata`/`song_data` (parallel/IPC mode),
          which will be used to precompute the full 161×161 grid on GPU.
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
    start = time.monotonic()
    while True:
        if request_id in _PENDING_RESPONSES:
            response = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            # Can happen if an earlier request timed out and its response arrived late.
            _PENDING_RESPONSES[response.request_id] = response
            continue
        break
    
    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")
    
    result = response.result
    if isinstance(result, list) and len(result) != len(genome_stats_list):
        raise RuntimeError(
            f"GPU executor returned {len(result)} results for {len(genome_stats_list)} genomes"
        )
    return result


def submit_gpu_optimize_gems_batch(
    batch_input: list,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    base_p_val: int,
    base_s_val: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    timeout: float = 60.0,
) -> list:
    """
    Submit optimize_gems_batch_gpu request via IPC (for worker processes).

    Mirrors `gear_optimizer.solver.taichi_gem.api.optimize_gems_batch_gpu`.
    """
    global _REQUEST_COUNTER

    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_optimize_gems_batch called but not in worker mode")

    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER

    request = GpuRequest(
        request_type=GpuRequestType.OPTIMIZE_GEMS_BATCH,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={
            "batch_input": batch_input,
            "cur_pp": int(cur_pp),
            "cur_cm": int(cur_cm),
            "cur_fm": int(cur_fm),
            "base_p_val": int(base_p_val),
            "base_s_val": int(base_s_val),
            "is_p_ft": int(is_p_ft),
            "is_s_ft": int(is_s_ft),
            "is_p_ff": int(is_p_ff),
            "is_s_ff": int(is_s_ff),
            "is_p_pp": int(is_p_pp),
            "is_s_pp": int(is_s_pp),
            "is_p_cm": int(is_p_cm),
            "is_s_cm": int(is_s_cm),
            "is_p_fm": int(is_p_fm),
            "is_s_fm": int(is_s_fm),
            "is_p_ov": int(is_p_ov),
            "is_s_ov": int(is_s_ov),
            "ref_arrays": ref_arrays,
        },
    )

    _REQUEST_QUEUE.put(request)

    start = time.monotonic()
    while True:
        if request_id in _PENDING_RESPONSES:
            response = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            _PENDING_RESPONSES[response.request_id] = response
            continue
        break

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")

    result = response.result
    if isinstance(result, list) and len(result) != len(batch_input):
        raise RuntimeError(
            f"GPU executor returned {len(result)} results for {len(batch_input)} items"
        )
    return result


def submit_gpu_load_ref_arrays(ref_arrays: dict, timeout: float = 30.0) -> None:
    """Submit load_ref_arrays request via IPC (for worker processes)."""
    global _REQUEST_COUNTER

    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_load_ref_arrays called but not in worker mode")

    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER

    request = GpuRequest(
        request_type=GpuRequestType.LOAD_REF_ARRAYS,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={"ref_arrays": ref_arrays},
    )

    _REQUEST_QUEUE.put(request)

    start = time.monotonic()
    while True:
        if request_id in _PENDING_RESPONSES:
            response = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            _PENDING_RESPONSES[response.request_id] = response
            continue
        break

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")
