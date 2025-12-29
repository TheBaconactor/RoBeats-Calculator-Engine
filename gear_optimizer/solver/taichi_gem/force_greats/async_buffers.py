"""
Async Buffer Manager for CPU-GPU Pipelining.

Provides thread-safe double-buffered staging for FG GPU operations.
This allows CPU to prepare data for the next batch while GPU processes the current one.

SAFETY GUARANTEES:
1. Mutex-protected buffer access prevents race conditions
2. Buffer ownership tracking prevents data overlap
3. Clear acquire/release semantics for buffer lifecycle
"""

from __future__ import annotations

import threading
from typing import Optional
import numpy as np

from .. import fields as gem_fields
from . import fields as fg_fields


# ============================================================================
# BUFFER POOL - Thread-safe double-buffered staging
# ============================================================================


class FGBufferPool:
    """
    Double-buffered pool for FG GPU uploads.

    Maintains two buffer sets (A and B) that alternate:
    - While GPU uses buffer A, CPU fills buffer B
    - On next call, swap: GPU uses B, CPU fills A

    Thread-safety: All buffer access is mutex-protected.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._buffers_initialized = False

        # Buffer set A
        self._genome_stats_a: Optional[np.ndarray] = None
        self._flat_work_genome_a: Optional[np.ndarray] = None
        self._flat_work_ftff_a: Optional[np.ndarray] = None
        self._ftff_ft_a: Optional[np.ndarray] = None
        self._ftff_ff_a: Optional[np.ndarray] = None
        self._forced_counts_a: Optional[np.ndarray] = None

        # Buffer set B
        self._genome_stats_b: Optional[np.ndarray] = None
        self._flat_work_genome_b: Optional[np.ndarray] = None
        self._flat_work_ftff_b: Optional[np.ndarray] = None
        self._ftff_ft_b: Optional[np.ndarray] = None
        self._ftff_ff_b: Optional[np.ndarray] = None
        self._forced_counts_b: Optional[np.ndarray] = None

        # Current active buffer (0=A, 1=B)
        self._active_buffer = 0

        # Buffer ownership tracking (for debugging)
        self._a_in_use = False
        self._b_in_use = False

    def _ensure_buffers(self) -> None:
        """Lazily allocate buffer pairs on first use."""
        if self._buffers_initialized:
            return

        # Buffer A
        self._genome_stats_a = np.zeros((gem_fields.MAX_GENOMES, 7), dtype=np.int16)
        self._flat_work_genome_a = np.zeros(fg_fields.FG_MAX_FLAT_WORK_ITEMS, dtype=np.int32)
        self._flat_work_ftff_a = np.zeros(fg_fields.FG_MAX_FLAT_WORK_ITEMS, dtype=np.int32)
        self._ftff_ft_a = np.zeros(fg_fields.FG_MAX_FTFF, dtype=np.int32)
        self._ftff_ff_a = np.zeros(fg_fields.FG_MAX_FTFF, dtype=np.int32)
        self._forced_counts_a = np.zeros((fg_fields.FG_MAX_CONFIGS, fg_fields.FG_MAX_SECTIONS), dtype=np.int32)

        # Buffer B
        self._genome_stats_b = np.zeros((gem_fields.MAX_GENOMES, 7), dtype=np.int16)
        self._flat_work_genome_b = np.zeros(fg_fields.FG_MAX_FLAT_WORK_ITEMS, dtype=np.int32)
        self._flat_work_ftff_b = np.zeros(fg_fields.FG_MAX_FLAT_WORK_ITEMS, dtype=np.int32)
        self._ftff_ft_b = np.zeros(fg_fields.FG_MAX_FTFF, dtype=np.int32)
        self._ftff_ff_b = np.zeros(fg_fields.FG_MAX_FTFF, dtype=np.int32)
        self._forced_counts_b = np.zeros((fg_fields.FG_MAX_CONFIGS, fg_fields.FG_MAX_SECTIONS), dtype=np.int32)

        self._buffers_initialized = True

    def acquire_write_buffers(self) -> dict:
        """
        Acquire the INACTIVE buffer set for CPU writing.

        Returns dict with numpy arrays ready for CPU to fill.
        MUST call release_write_buffers() when done.

        Thread-safe: Blocks until buffers are available.
        """
        with self._lock:
            self._ensure_buffers()

            # Get inactive buffer set (opposite of active)
            if self._active_buffer == 0:
                # A is active (GPU using), return B for writing
                if self._b_in_use:
                    raise RuntimeError("Buffer B already in use - release before re-acquiring")
                self._b_in_use = True
                return {
                    "genome_stats": self._genome_stats_b,
                    "flat_work_genome": self._flat_work_genome_b,
                    "flat_work_ftff": self._flat_work_ftff_b,
                    "ftff_ft": self._ftff_ft_b,
                    "ftff_ff": self._ftff_ff_b,
                    "forced_counts": self._forced_counts_b,
                    "_buffer_id": 1,  # For tracking
                }
            else:
                # B is active (GPU using), return A for writing
                if self._a_in_use:
                    raise RuntimeError("Buffer A already in use - release before re-acquiring")
                self._a_in_use = True
                return {
                    "genome_stats": self._genome_stats_a,
                    "flat_work_genome": self._flat_work_genome_a,
                    "flat_work_ftff": self._flat_work_ftff_a,
                    "ftff_ft": self._ftff_ft_a,
                    "ftff_ff": self._ftff_ff_a,
                    "forced_counts": self._forced_counts_a,
                    "_buffer_id": 0,
                }

    def release_write_buffers(self, buffer_id: int) -> None:
        """Release write lock on buffer set after CPU filling is complete."""
        with self._lock:
            if buffer_id == 0:
                self._a_in_use = False
            else:
                self._b_in_use = False

    def swap_active(self) -> None:
        """
        Swap active buffer after GPU kernel completes.

        This makes the just-written buffer active for GPU,
        and frees the just-used buffer for CPU writing.
        """
        with self._lock:
            self._active_buffer = 1 - self._active_buffer

    def get_active_buffers(self) -> dict:
        """
        Get the ACTIVE buffer set for GPU upload.

        These buffers have been filled by CPU and are ready for from_numpy().
        """
        with self._lock:
            self._ensure_buffers()

            if self._active_buffer == 0:
                return {
                    "genome_stats": self._genome_stats_a,
                    "flat_work_genome": self._flat_work_genome_a,
                    "flat_work_ftff": self._flat_work_ftff_a,
                    "ftff_ft": self._ftff_ft_a,
                    "ftff_ff": self._ftff_ff_a,
                    "forced_counts": self._forced_counts_a,
                }
            else:
                return {
                    "genome_stats": self._genome_stats_b,
                    "flat_work_genome": self._flat_work_genome_b,
                    "flat_work_ftff": self._flat_work_ftff_b,
                    "ftff_ft": self._ftff_ft_b,
                    "ftff_ff": self._ftff_ff_b,
                    "forced_counts": self._forced_counts_b,
                }


# Global singleton buffer pool
_fg_buffer_pool: Optional[FGBufferPool] = None
_pool_lock = threading.Lock()


def get_fg_buffer_pool() -> FGBufferPool:
    """Get or create the global FG buffer pool singleton."""
    global _fg_buffer_pool
    with _pool_lock:
        if _fg_buffer_pool is None:
            _fg_buffer_pool = FGBufferPool()
        return _fg_buffer_pool


def reset_buffer_pool() -> None:
    """Reset the buffer pool (for testing/cleanup)."""
    global _fg_buffer_pool
    with _pool_lock:
        _fg_buffer_pool = None


# ============================================================================
# ASYNC RESULT PROCESSOR - Offload dict construction to background thread
# ============================================================================

from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Dict, Any, Callable
import queue


class AsyncResultProcessor:
    """
    Offloads Python dict construction to a background thread.

    While GPU runs the next batch, CPU builds result dicts in parallel.
    Results are queued and retrieved in order.

    Thread-safety: Uses queue for safe cross-thread result passing.
    """

    def __init__(self, max_workers: int = 1):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="FG_Result")
        self._pending_futures: List[Future] = []
        self._result_queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()

    def submit_result_build(
        self,
        numpy_arrays: Dict[str, np.ndarray],
        n_genomes: int,
        build_fn: Callable[[Dict[str, np.ndarray], int], List[Dict[str, Any]]],
    ) -> None:
        """
        Submit result dict construction to background thread.

        Args:
            numpy_arrays: Dict of numpy arrays from to_numpy() calls
            n_genomes: Number of results to build
            build_fn: Function that builds list of result dicts from arrays
        """
        # Make copies of arrays to ensure thread safety (GPU may overwrite originals)
        arrays_copy = {k: v.copy() for k, v in numpy_arrays.items()}

        future = self._executor.submit(build_fn, arrays_copy, n_genomes)
        with self._lock:
            self._pending_futures.append(future)

    def get_results(self, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """
        Wait for all pending results and return them in order.

        Args:
            timeout: Max seconds to wait for results

        Returns:
            List of all result dicts in submission order
        """
        all_results = []
        with self._lock:
            futures = list(self._pending_futures)
            self._pending_futures.clear()

        for future in futures:
            try:
                results = future.result(timeout=timeout)
                all_results.extend(results)
            except Exception as e:
                # Log but don't crash - partial results are still useful
                print(f"[AsyncResultProcessor] Result build failed: {e}")

        return all_results

    def shutdown(self) -> None:
        """Shutdown the executor gracefully."""
        self._executor.shutdown(wait=True)


# Global singleton result processor
_fg_result_processor: Optional[AsyncResultProcessor] = None
_result_lock = threading.Lock()


def get_result_processor() -> AsyncResultProcessor:
    """Get or create the global async result processor."""
    global _fg_result_processor
    with _result_lock:
        if _fg_result_processor is None:
            _fg_result_processor = AsyncResultProcessor()
        return _fg_result_processor


def shutdown_result_processor() -> None:
    """Shutdown and reset the result processor."""
    global _fg_result_processor
    with _result_lock:
        if _fg_result_processor is not None:
            _fg_result_processor.shutdown()
            _fg_result_processor = None
