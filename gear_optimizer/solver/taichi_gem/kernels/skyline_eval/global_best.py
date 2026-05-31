"""Taichi Kernels - skyline global best operations."""

from __future__ import annotations

from ._from_ga import install_from_ga_source


install_from_ga_source(
    globals(),
    "global_best.py",
    (("def skyline_init_global_best_kernel", "def SKYLINE_INIT_global_best_kernel"),),
)
