from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class GemKey(str, Enum):
    PP = "Perfect Points"
    CM = "Combo Multiplier"
    FM = "Fever Multiplier"
    FT = "Fever Time"
    FF = "Fever Fill Rate"
    ELEMENT = "Element"


ELEMENT_STAT_KEYS: tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")

# DB packed-order keys used by serialization.
STAT_KEYS: tuple[str, ...] = (
    GemKey.PP.value,
    GemKey.CM.value,
    GemKey.FM.value,
    GemKey.FF.value,
    GemKey.FT.value,
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
)

# Base solver array order.
BASE_STAT_KEYS: tuple[str, ...] = (
    GemKey.PP.value,
    GemKey.CM.value,
    GemKey.FM.value,
    GemKey.FT.value,
    GemKey.FF.value,
    "Beat",
    "Vibe",
    "Rush",
    "Flow",
    "Chill",
)

GEM_KEYS: tuple[str, ...] = (
    GemKey.PP.value,
    GemKey.CM.value,
    GemKey.FM.value,
    GemKey.ELEMENT.value,
)


def build_gem_counts(g_pp: int, g_cm: int, g_fm: int, g_ov: int) -> dict[str, int]:
    return {
        GemKey.PP.value: int(g_pp),
        GemKey.CM.value: int(g_cm),
        GemKey.FM.value: int(g_fm),
        GemKey.ELEMENT.value: int(g_ov),
    }


def element_gem_count(gem_counts: Mapping[str, Any] | None) -> int:
    """Single canonical reader for the elemental/overflow gem count.

    Production gem dicts come from ``build_gem_counts``, which keys this under the
    canonical ``GemKey.ELEMENT.value``. This is the one authoritative INTERNAL reader;
    legacy spellings ("Overflow"/"Element Overflow"/"ElementOverflow"/"OV") are NOT
    tolerated here — normalize them to the canonical key at the explicit external
    DB-decode boundary instead (issue #56 Category A: kill the alias soup that produced
    the issue #46 F1 parity bug).
    """
    if not isinstance(gem_counts, Mapping):
        return 0
    return int(gem_counts.get(GemKey.ELEMENT.value, 0) or 0)
