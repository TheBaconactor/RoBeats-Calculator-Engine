"""
Taichi Kernels - Pack skyline snapshots for CPU download.

The skyline payload kernels are mechanically identical to the GA payload kernels
except for the destination field prefix. Keep GA as the canonical source so the
two surfaces cannot drift.
"""

from __future__ import annotations

from ._from_ga import install_from_ga_source


install_from_ga_source(
    globals(),
    "payload.py",
    (
        ("Pack GA snapshots", "Pack skyline snapshots"),
        ("def skyline_init_runs_best_kernel", "def SKYLINE_INIT_runs_best_kernel"),
    ),
)
