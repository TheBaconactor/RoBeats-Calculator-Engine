from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class GemKey(str, Enum):
    PP = "Perfect Points"
    CM = "Combo Multiplier"
    FM = "Fever Multiplier"
    FT = "Fever Time"
    FF = "Fever Fill Rate"
    ELEMENT = "Element"


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


def extract_gem_totals(details: Mapping[str, Any]) -> GemTotals:
    """The gem allocation in a stored row's details, as the store writes it: GemCounts by stat name (PP, CM, FM,
    Element) and the fever gems as FT/FF; missing counts are 0."""
    gem_counts = details.get("GemCounts") or {}
    return GemTotals(
        pp=gem_counts.get(GemKey.PP.value, 0),
        cm=gem_counts.get(GemKey.CM.value, 0),
        fm=gem_counts.get(GemKey.FM.value, 0),
        ft=details.get("FT", 0),
        ff=details.get("FF", 0),
        element=gem_counts.get(GemKey.ELEMENT.value, 0),
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
