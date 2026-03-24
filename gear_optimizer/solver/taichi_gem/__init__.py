"""
Taichi Gem Solver - Internal subpackage.

This package contains the GPU-accelerated gem optimization implementation.
The supported public entrypoints live in `gear_optimizer.solver.taichi_gem.api`.
"""

# Import runtime eagerly so Taichi's import-time banner can be suppressed before any
# submodules do `import taichi as ti`.
from . import runtime as _runtime  # noqa: F401

__all__: list[str] = []
