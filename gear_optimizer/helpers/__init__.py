"""
Helper modules for breaking down monolithic functions.

This package contains extracted helper functions to improve modularity:
- song_helpers: Song processing workflow helpers
- pool_initialization: Exact-safe per-song gear and mini pools

Placement hint:
- If logic can be shared by both pipeline and solver layers, prefer adding it here
  instead of duplicating behavior across orchestrators.
"""
