from __future__ import annotations

from typing import Dict, Tuple

STAT_KEYS: Tuple[str, ...] = ("PP", "CM", "FM", "FT", "FF", "OV")
OV_INDEX: int = STAT_KEYS.index("OV")

ELEMENTS: Tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")
ELEMENT_TO_ID: Dict[str, int] = {name: idx + 1 for idx, name in enumerate(ELEMENTS)}
ID_TO_ELEMENT: Dict[int, str] = {idx + 1: name for idx, name in enumerate(ELEMENTS)}
