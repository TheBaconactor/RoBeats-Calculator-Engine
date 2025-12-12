"""
API Stability Test - Verify taichi_gem_solver exports expected functions.

This test ensures the refactored facade maintains backward compatibility
with existing code that imports from taichi_gem_solver.
"""
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_taichi_gem_solver_exports():
    """Verify all expected functions are exported from the facade."""
    from gear_optimizer.solver import taichi_gem_solver
    
    expected = [
        "init_taichi_vulkan",
        "load_ref_arrays",
        "optimize_gems_gpu",
        "optimize_gems_batch_gpu",
        "mega_batch_solve_population",
        "solve_genomes_with_ftff",
        "solve_genomes_parallel",
    ]
    
    missing = []
    for name in expected:
        if not hasattr(taichi_gem_solver, name):
            missing.append(name)
    
    assert not missing, f"Missing exports: {missing}"


def test_all_list():
    """Verify __all__ contains the expected functions."""
    from gear_optimizer.solver import taichi_gem_solver
    
    expected = {
        "init_taichi_vulkan",
        "load_ref_arrays",
        "optimize_gems_gpu",
        "optimize_gems_batch_gpu",
        "mega_batch_solve_population",
        "solve_genomes_with_ftff",
        "solve_genomes_parallel",
    }
    
    assert hasattr(taichi_gem_solver, "__all__"), "__all__ not defined"
    
    actual = set(taichi_gem_solver.__all__)
    
    assert actual == expected, f"__all__ mismatch. missing={expected-actual}, extra={actual-expected}"


def test_subpackage_structure():
    """Verify internal subpackage structure exists."""
    from gear_optimizer.solver.taichi_gem import runtime, fields, kernels, api
    
    # Check runtime
    assert hasattr(runtime, 'init_taichi_vulkan'), "Missing init_taichi_vulkan in runtime"
    assert hasattr(runtime, 'is_initialized'), "Missing is_initialized in runtime"
    
    # Check fields
    assert hasattr(fields, 'ensure_fields_allocated'), "Missing ensure_fields_allocated in fields"
    assert hasattr(fields, 'bind_fields'), "Missing bind_fields in fields"
    assert hasattr(fields, 'GRID_SIZE'), "Missing GRID_SIZE in fields"
    
    # Check kernels
    assert hasattr(kernels, 'solve_batch_kernel'), "Missing solve_batch_kernel in kernels"
    assert hasattr(kernels, 'solve_genomes_with_ftff_kernel'), "Missing solve_genomes_with_ftff_kernel in kernels"
    
    # Check api
    assert hasattr(api, 'ensure_ready'), "Missing ensure_ready in api"
    assert hasattr(api, 'load_ref_arrays'), "Missing load_ref_arrays in api"
    
    assert True


def main():
    print("=" * 60)
    print("API STABILITY TEST")
    print("=" * 60)
    print()
    
    results = []
    results.append(("Facade Exports", test_taichi_gem_solver_exports()))
    results.append(("__all__ List", test_all_list()))
    results.append(("Subpackage Structure", test_subpackage_structure()))
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("ALL API STABILITY TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
