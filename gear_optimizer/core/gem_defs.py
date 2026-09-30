from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping
import logging




logger = logging.getLogger(__name__)


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


@dataclass(frozen=True, slots=True)
class GemTotals:
    pp: int = 0
    cm: int = 0
    fm: int = 0
    ft: int = 0
    ff: int = 0
    element: int = 0

    def as_tuple(self) -> tuple[int, int, int, int, int, int]:
        return (self.pp, self.cm, self.fm, self.ft, self.ff, self.element)


def _read_first_int(mapping: Mapping[str, Any], *keys: str) -> int:
    for key in keys:
        if key not in mapping:
            continue
        try:
            return int(mapping.get(key) or 0)
        except (TypeError, ValueError) as e:
            logger.debug(f"gem_defs:_read_first_int: {e}")
            return 0
    return 0


def extract_gem_totals(details: Mapping[str, Any] | None) -> GemTotals:
    src = details if isinstance(details, Mapping) else {}
    gem_counts = src.get("GemCounts")
    if not isinstance(gem_counts, Mapping):
        gem_counts = {}

    return GemTotals(
        pp=_read_first_int(gem_counts, GemKey.PP.value, "PP"),
        cm=_read_first_int(gem_counts, GemKey.CM.value, "CM"),
        fm=_read_first_int(gem_counts, GemKey.FM.value, "FM"),
        ft=_read_first_int(src, "FT", GemKey.FT.value, "FeverGems")
        or _read_first_int(gem_counts, GemKey.FT.value, "FT", "FeverGems"),
        ff=_read_first_int(src, "FF", GemKey.FF.value, "FeverFillGems")
        or _read_first_int(gem_counts, GemKey.FF.value, "FF", "FeverFillGems"),
        element=_read_first_int(gem_counts, GemKey.ELEMENT.value, "OV", "Overflow"),
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
