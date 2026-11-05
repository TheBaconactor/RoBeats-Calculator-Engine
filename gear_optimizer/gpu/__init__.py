"""The GPU: Taichi fields, kernels and the GA's uploads (public entry points in `gear_optimizer.gpu.api`)."""

# Import runtime eagerly so Taichi's import-time banner is suppressed before GPU
# submodules do `import taichi as ti`.
from . import runtime as _runtime

__all__: list[str] = []
