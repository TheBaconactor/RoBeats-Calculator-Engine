"""The GA's CPU-side helpers: a song's item pools (pool_initialization) and the exact-duplicate collapse of the GA's
selected rows (unique_eval)."""

from .pool_initialization import initialize_pools

__all__ = ["initialize_pools"]
