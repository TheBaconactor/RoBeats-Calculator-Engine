"""
Taichi Gem Solver - Internal subpackage.

This package contains the GPU-accelerated gem optimization implementation.
The supported public entrypoints live in `gear_optimizer.solver.taichi_gem.api`.
"""

try:
    # Import runtime eagerly when Taichi is installed so its import-time banner is
    # suppressed before GPU submodules do `import taichi as ti`.
    from . import runtime as _runtime  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - exercised in CPU-only test envs
    if exc.name != "taichi":
        raise

__all__: list[str] = []
