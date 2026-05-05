"""
Song Helpers - Force Greats.

This package hosts the Force Greats helper logic. The public entrypoint is:
- `process_force_greats(...)`
"""

from .core import process_force_greats
from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows

__all__ = ["process_force_greats", "decode_cfg_counts_from_windows"]
