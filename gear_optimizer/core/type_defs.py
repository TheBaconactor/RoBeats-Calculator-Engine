"""
Central type aliases for commonly used shapes and dicts.

This keeps signatures readable without forcing a hard dependency on a type checker.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

GenomeArray = np.ndarray
StatsDict = Dict[str, float]

