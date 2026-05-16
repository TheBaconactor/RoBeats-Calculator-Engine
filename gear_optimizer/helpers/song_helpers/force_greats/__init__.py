"""
Keep the package import light; GPU dispatch is loaded only when the public
entrypoint is actually called.
"""

from __future__ import annotations

from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows

__all__ = ["process_force_greats", "decode_cfg_counts_from_windows"]


def process_force_greats(*args, **kwargs):
    from .core import process_force_greats as _process_force_greats

    return _process_force_greats(*args, **kwargs)
