from pathlib import Path


def test_fg_finder_kernel_routes_timelines_through_exact_inner_solver() -> None:
    src = Path("gear_optimizer/solver/taichi_gem/force_greats/kernels.py").read_text(encoding="utf-8")

    assert "optimize_core_device_exact_bound_preloaded_bits" in src
    assert "optimize_core_device_preloaded_bits" not in src
