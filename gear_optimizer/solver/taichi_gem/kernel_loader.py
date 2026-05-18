"""Kernel loader for the Vulkan Taichi kernels."""

from __future__ import annotations

def get_kernels():
    """Return the production Vulkan kernel module."""
    from . import kernels as base_kernels

    return base_kernels
