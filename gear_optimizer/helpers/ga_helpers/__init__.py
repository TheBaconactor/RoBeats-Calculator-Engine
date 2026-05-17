"""
GA helper utilities.

Production runs are GPU-native; this package only keeps the small CPU helpers that remain
useful for pool construction and reference-only tuning logic.
"""

from .pool_initialization import initialize_pools

__all__ = ["initialize_pools"]
