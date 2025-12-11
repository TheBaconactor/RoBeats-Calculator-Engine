"""
GPU Scheduler - Dedicated GPU thread with batch coalescing.

Phase 1: Dedicated GPU thread for serialized kernel execution.
Phase 2: Batch coalescing - collect multiple requests and merge into mega-batch.

Architecture:
    Workers --submit--> CoalesceBuffer --timeout/full--> MergeBatch --> Kernel
                    |                                        |
              await future                          set all futures
"""
import threading
import queue
import time
from concurrent.futures import Future
from typing import Any, Callable, List, Dict
import numpy as np


class BatchRequest:
    """A batch gem solve request that can be coalesced with others."""
    
    def __init__(
        self,
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
    ):
        self.batch_input = batch_input
        self.cur_pp = cur_pp
        self.cur_cm = cur_cm
        self.cur_fm = cur_fm
        self.base_p_val = base_p_val
        self.base_s_val = base_s_val
        self.is_p_ft = is_p_ft
        self.is_s_ft = is_s_ft
        self.is_p_ff = is_p_ff
        self.is_s_ff = is_s_ff
        self.is_p_pp = is_p_pp
        self.is_s_pp = is_s_pp
        self.is_p_cm = is_p_cm
        self.is_s_cm = is_s_cm
        self.is_p_fm = is_p_fm
        self.is_s_fm = is_s_fm
        self.is_p_ov = is_p_ov
        self.is_s_ov = is_s_ov
        self.ref_arrays = ref_arrays
        self.future = Future()
        self.batch_size = len(batch_input)
    
    def can_coalesce_with(self, other: 'BatchRequest') -> bool:
        """Check if this request can be merged with another.
        
        Requests can be merged if they share the same configuration flags
        and reference arrays. Only batch_input differs per genome.
        """
        return (
            self.cur_pp == other.cur_pp and
            self.cur_cm == other.cur_cm and
            self.cur_fm == other.cur_fm and
            self.is_p_ft == other.is_p_ft and
            self.is_s_ft == other.is_s_ft and
            self.is_p_ff == other.is_p_ff and
            self.is_s_ff == other.is_s_ff and
            self.is_p_pp == other.is_p_pp and
            self.is_s_pp == other.is_s_pp and
            self.is_p_cm == other.is_p_cm and
            self.is_s_cm == other.is_s_cm and
            self.is_p_fm == other.is_p_fm and
            self.is_s_fm == other.is_s_fm and
            self.is_p_ov == other.is_p_ov and
            self.is_s_ov == other.is_s_ov
            # Note: ref_arrays should be the same for same song
            # base_p_val, base_s_val can differ per genome - handled in kernel
        )


class GpuRequest:
    """A generic request to execute on the GPU thread."""
    
    def __init__(self, func: Callable, args: tuple, kwargs: dict):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.future = Future()
    
    def execute(self):
        """Execute the request and set the future result."""
        try:
            result = self.func(*self.args, **self.kwargs)
            self.future.set_result(result)
        except Exception as e:
            self.future.set_exception(e)


class GpuScheduler:
    """
    GPU Scheduler with dedicated GPU thread and batch coalescing.
    
    Phase 1: Serialized GPU execution via queue
    Phase 2: Batch coalescing - collect requests within time window
    
    Configuration:
        batch_timeout_ms: Max time to wait for more requests (default: 5ms)
        max_batch_size: Max requests to coalesce before forcing execution (default: 64)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - only one GPU scheduler instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, batch_timeout_ms: float = 5.0, max_batch_size: int = 64):
        if self._initialized:
            return
        
        self._request_queue = queue.Queue()
        self._gpu_thread = None
        self._running = False
        self._initialized = True
        self._taichi_initialized = False
        
        # Batch coalescing config
        self._batch_timeout_ms = batch_timeout_ms
        self._max_batch_size = max_batch_size
        
        # Stats
        self._total_requests = 0
        self._coalesced_batches = 0
    
    def start(self):
        """Start the GPU scheduler thread."""
        if self._running:
            return
        
        self._running = True
        self._gpu_thread = threading.Thread(
            target=self._process_loop,
            name="GpuSchedulerThread",
            daemon=True,
        )
        self._gpu_thread.start()
        print("[GPU Scheduler] Started (batch coalescing enabled)")
    
    def stop(self):
        """Stop the GPU scheduler thread."""
        if not self._running:
            return
        
        self._running = False
        self._request_queue.put(None)  # Poison pill
        if self._gpu_thread:
            self._gpu_thread.join(timeout=5.0)
        print(f"[GPU Scheduler] Stopped. Stats: {self._total_requests} requests, {self._coalesced_batches} coalesced batches")
    
    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """Submit a generic GPU function for execution."""
        if not self._running:
            self.start()
        
        request = GpuRequest(func, args, kwargs)
        self._request_queue.put(request)
        self._total_requests += 1
        return request.future
    
    def submit_batch(self, request: BatchRequest) -> Future:
        """Submit a BatchRequest that can be coalesced with others."""
        if not self._running:
            self.start()
        
        self._request_queue.put(request)
        self._total_requests += 1
        return request.future
    
    def _process_loop(self):
        """Main loop - processes requests with batch coalescing."""
        # Initialize Taichi on the GPU thread
        if not self._taichi_initialized:
            try:
                from .taichi_gem_solver import init_taichi_vulkan
                init_taichi_vulkan()
                self._taichi_initialized = True
            except Exception as e:
                print(f"[GPU Scheduler] Taichi init failed: {e}")
        
        while self._running:
            try:
                # Get first request
                first_request = self._request_queue.get(timeout=0.1)
                
                if first_request is None:  # Poison pill
                    break
                
                # If it's a BatchRequest, try to coalesce
                if isinstance(first_request, BatchRequest):
                    self._process_coalesced_batch(first_request)
                else:
                    # Generic request - execute directly
                    first_request.execute()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[GPU Scheduler] Error: {e}")
    
    def _process_coalesced_batch(self, first_request: BatchRequest):
        """Collect and coalesce BatchRequests, then execute as mega-batch.
        
        OPTIMIZATION: Only wait for more requests if queue has pending items.
        If queue is empty, execute immediately to minimize GPU idle time.
        """
        from .taichi_gem_solver import optimize_gems_batch_gpu
        
        requests = [first_request]
        
        # Only coalesce if there are already more requests waiting
        # This prevents GPU idle time when requests trickle in slowly
        while len(requests) < self._max_batch_size:
            # Non-blocking check: is there another request already waiting?
            try:
                next_request = self._request_queue.get_nowait()
            except queue.Empty:
                # No more requests waiting - execute immediately!
                break
            
            if next_request is None:
                self._request_queue.put(None)  # Re-queue poison pill
                break
            
            if isinstance(next_request, BatchRequest):
                if first_request.can_coalesce_with(next_request):
                    requests.append(next_request)
                else:
                    # Different config, can't coalesce - re-queue
                    self._request_queue.put(next_request)
                    break
            else:
                # Non-batch request - re-queue and process current batch
                self._request_queue.put(next_request)
                break
        
        # Execute coalesced batch
        if len(requests) == 1:
            # Single request - execute directly
            req = requests[0]
            try:
                result = optimize_gems_batch_gpu(
                    req.batch_input,
                    req.cur_pp, req.cur_cm, req.cur_fm,
                    base_p_val=req.base_p_val,
                    base_s_val=req.base_s_val,
                    is_p_ft=req.is_p_ft,
                    is_s_ft=req.is_s_ft,
                    is_p_ff=req.is_p_ff,
                    is_s_ff=req.is_s_ff,
                    is_p_pp=req.is_p_pp,
                    is_s_pp=req.is_s_pp,
                    is_p_cm=req.is_p_cm,
                    is_s_cm=req.is_s_cm,
                    is_p_fm=req.is_p_fm,
                    is_s_fm=req.is_s_fm,
                    is_p_ov=req.is_p_ov,
                    is_s_ov=req.is_s_ov,
                    ref_arrays=req.ref_arrays,
                )
                req.future.set_result(result)
            except Exception as e:
                req.future.set_exception(e)
        else:
            # Multiple requests - merge into mega-batch
            self._coalesced_batches += 1
            self._execute_mega_batch(requests)
    
    def _execute_mega_batch(self, requests: List[BatchRequest]):
        """Merge multiple BatchRequests into one GPU kernel call."""
        from .taichi_gem_solver import optimize_gems_batch_gpu
        
        # Merge all batch_inputs into one mega-batch
        mega_batch = []
        request_boundaries = []  # Track where each request's results start/end
        
        offset = 0
        for req in requests:
            # Update batch_input with request-specific base_p_val, base_s_val
            for item in req.batch_input:
                # Create copy with this request's base values
                item_copy = item.copy()
                item_copy["_base_p_val"] = req.base_p_val
                item_copy["_base_s_val"] = req.base_s_val
                mega_batch.append(item_copy)
            
            request_boundaries.append((offset, offset + len(req.batch_input)))
            offset += len(req.batch_input)
        
        # Use first request's config (they're all compatible)
        first = requests[0]
        
        try:
            # Execute single mega-batch kernel
            results = optimize_gems_batch_gpu(
                mega_batch,
                first.cur_pp, first.cur_cm, first.cur_fm,
                base_p_val=0,  # Per-item in batch
                base_s_val=0,
                is_p_ft=first.is_p_ft,
                is_s_ft=first.is_s_ft,
                is_p_ff=first.is_p_ff,
                is_s_ff=first.is_s_ff,
                is_p_pp=first.is_p_pp,
                is_s_pp=first.is_s_pp,
                is_p_cm=first.is_p_cm,
                is_s_cm=first.is_s_cm,
                is_p_fm=first.is_p_fm,
                is_s_fm=first.is_s_fm,
                is_p_ov=first.is_p_ov,
                is_s_ov=first.is_s_ov,
                ref_arrays=first.ref_arrays,
            )
            
            # Split results back to each request
            for i, (start, end) in enumerate(request_boundaries):
                request_results = results[start:end]
                requests[i].future.set_result(request_results)
                
        except Exception as e:
            # Set exception on all futures
            for req in requests:
                req.future.set_exception(e)
    
    @property
    def queue_size(self) -> int:
        """Current number of pending requests."""
        return self._request_queue.qsize()
    
    @property
    def is_running(self) -> bool:
        """Whether the scheduler is running."""
        return self._running
    
    @property
    def stats(self) -> dict:
        """Return scheduler statistics."""
        return {
            "total_requests": self._total_requests,
            "coalesced_batches": self._coalesced_batches,
        }


# Global scheduler instance
_scheduler = None


def get_gpu_scheduler() -> GpuScheduler:
    """Get the global GPU scheduler instance (lazy init)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = GpuScheduler()
    return _scheduler


def submit_gpu_batch(
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
) -> Future:
    """
    Submit a batch gem optimization that can be coalesced with others.
    
    Returns:
        Future containing list of result tuples
    """
    request = BatchRequest(
        batch_input=batch_input,
        cur_pp=cur_pp,
        cur_cm=cur_cm,
        cur_fm=cur_fm,
        base_p_val=base_p_val,
        base_s_val=base_s_val,
        is_p_ft=is_p_ft,
        is_s_ft=is_s_ft,
        is_p_ff=is_p_ff,
        is_s_ff=is_s_ff,
        is_p_pp=is_p_pp,
        is_s_pp=is_s_pp,
        is_p_cm=is_p_cm,
        is_s_cm=is_s_cm,
        is_p_fm=is_p_fm,
        is_s_fm=is_s_fm,
        is_p_ov=is_p_ov,
        is_s_ov=is_s_ov,
        ref_arrays=ref_arrays,
    )
    
    scheduler = get_gpu_scheduler()
    return scheduler.submit_batch(request)
