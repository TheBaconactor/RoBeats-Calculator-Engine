"""
Core package for shared runtime foundations.

Placement guidance:
- Put env/config/constants/path concerns here.
- Avoid placing algorithm-specific logic here (belongs in solver/helpers).
"""

from .code_placement import PLACEMENT_HINTS, find_hints, iter_placement_hints, owner_for_path

__all__ = ["PLACEMENT_HINTS", "find_hints", "iter_placement_hints", "owner_for_path"]
