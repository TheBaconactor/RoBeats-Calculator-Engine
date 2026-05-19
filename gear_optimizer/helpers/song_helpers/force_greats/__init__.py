"""
Keep the package import light; GPU dispatch is loaded only when the public
entrypoint is actually called.
"""

from __future__ import annotations

__all__ = ["process_force_greats"]


def process_force_greats(*args, **kwargs):
    from .core import process_force_greats as _process_force_greats

    return _process_force_greats(*args, **kwargs)
