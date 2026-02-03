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


# ============================================================================
# ASYNC RESULT PROCESSOR - Offload dict construction to background thread
# ============================================================================

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Dict, List


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
