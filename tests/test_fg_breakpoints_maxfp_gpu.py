import inspect


def test_fg_breakpoint_maxfp_kernel_is_removed():
    from gear_optimizer.solver.taichi_gem.kernels import kernels_breakpoints

    assert not hasattr(kernels_breakpoints, "fg_compute_max_fp_by_pair_kernel")


def test_fg_breakpoint_kernel_source_has_no_section_caps_or_fp_table():
    from gear_optimizer.solver.taichi_gem.kernels import kernels_breakpoints

    source = inspect.getsource(kernels_breakpoints)
    assert "MAX_SECTION_CAPS" not in source
    assert "_FG_SECTION_FORCED_CAPS" not in source
    assert "fp_cap_table" not in source
    assert "(161, 51)" not in source
