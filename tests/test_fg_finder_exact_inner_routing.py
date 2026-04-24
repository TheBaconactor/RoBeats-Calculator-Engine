from pathlib import Path


def test_fg_finder_kernel_routes_timelines_through_exact_inner_solver() -> None:
    src = Path("gear_optimizer/solver/taichi_gem/force_greats/kernels.py").read_text(encoding="utf-8")

    assert "optimize_core_device_exact_bound_preloaded_bits" in src
    assert "optimize_core_device_preloaded_bits" not in src


def test_base_and_fg_share_exact_inner_after_timeline_selection() -> None:
    scoring_src = Path("gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py").read_text(encoding="utf-8")
    ga_src = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("gear_optimizer/solver/taichi_gem/kernels/ga_eval").glob("*.py")
    )
    fg_src = Path("gear_optimizer/solver/taichi_gem/force_greats/kernels.py").read_text(encoding="utf-8")
    timeline_src = Path("gear_optimizer/solver/taichi_gem/api/timeline.py").read_text(encoding="utf-8")

    assert "def optimize_core_device_exact_bound(" in scoring_src
    assert "def optimize_core_device_exact_bound_preloaded_bits(" in scoring_src
    assert "optimize_core_device_exact_bound(" in ga_src
    assert "optimize_core_device_exact_bound_preloaded_bits" in fg_src

    assert "solve_timeline_signature_exact_scoremax_from_grouped_windows" in timeline_src
    assert "_upload_exact_timeline_overrides_kernel" in timeline_src
