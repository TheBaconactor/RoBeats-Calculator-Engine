"""
Data integrity tests for async FG processing.

Verifies:
1. Array copy isolation (no cross-contamination)
2. Result ordering preserved
3. No data loss under concurrent access
"""

import numpy as np
import threading
import time

from gear_optimizer.solver.taichi_gem.force_greats.async_buffers import AsyncResultProcessor

def test_array_copy_isolation():
    """Test that arrays are copied, preventing cross-contamination."""
    print("Test 1: Array copy isolation...")
    proc = AsyncResultProcessor()

    def build_fn(arrays, n):
        time.sleep(0.1)  # Simulate work
        return [{"val": int(arrays["data"][i])} for i in range(n)]

    # Submit first batch
    arr1 = {"data": np.array([1, 2, 3])}
    proc.submit_result_build(arr1, 3, build_fn)

    # Modify source array BEFORE results are fetched
    arr1["data"][0] = 999  # This should NOT affect the submitted result

    results = proc.get_results()
    print(f"  Source modified to 999, but result should be 1: {results[0]}")
    assert results[0]["val"] == 1, "FAIL: Array was not copied!"
    print("  PASS: Arrays are properly copied")
    proc.shutdown()


def test_result_ordering():
    """Test that results are returned in submission order."""
    print("Test 2: Result ordering...")
    proc = AsyncResultProcessor()

    def ordered_build(arrays, n):
        batch_id = arrays["id"][0]
        return [{"batch": int(batch_id), "idx": i} for i in range(n)]

    for batch in range(5):
        proc.submit_result_build({"id": np.array([batch])}, 2, ordered_build)

    all_results = proc.get_results()
    batches = [r["batch"] for r in all_results]
    print(f"  Results: {batches}")
    expected = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
    assert batches == expected, f"FAIL: Order wrong! Expected {expected}, got {batches}"
    print("  PASS: Results in correct order")
    proc.shutdown()


def test_concurrent_access():
    """Test no data loss under concurrent submit."""
    print("Test 3: Concurrent access safety...")
    proc = AsyncResultProcessor()
    errors = []

    def concurrent_submit(batch_id):
        try:
            proc.submit_result_build(
                {"id": np.array([batch_id])}, 
                1, 
                lambda a, n: [{"batch": int(a["id"][0])}]
            )
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=concurrent_submit, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors during concurrent access: {errors}"
    
    all_results = proc.get_results()
    print(f"  Got {len(all_results)} results from 10 concurrent submits")
    assert len(all_results) == 10, f"FAIL: Lost data! Got {len(all_results)}"
    print("  PASS: No data loss under concurrency")
    proc.shutdown()


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v", "-s"]))
