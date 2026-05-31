"""Taichi Kernels - skyline migration operations."""

from __future__ import annotations

from ._from_ga import install_from_ga_source


install_from_ga_source(globals(), "migration.py", ())
