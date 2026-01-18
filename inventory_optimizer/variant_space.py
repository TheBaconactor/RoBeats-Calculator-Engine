from __future__ import annotations

from functools import lru_cache
from typing import Tuple

import numpy as np

from .keys import OV_INDEX, STAT_KEYS

SLOT_GEM_BUDGET: int = 15
STAT_COUNT: int = len(STAT_KEYS)

# Per-gear variant space:
# - OV==0 variants (color=0): compositions of 15 into 5 parts => C(19,4)=3876
# - OV>0 compositions: total 6-part compositions minus OV==0 => C(20,5)-C(19,4)=15504-3876=11628
#   Each OV>0 composition has 5 possible element colors => 11628 * 5 = 58140
OV0_VARIANTS: int = 3876
OV_POS_COMPOSITIONS: int = 11628
VARIANTS_PER_GEAR: int = OV0_VARIANTS + (OV_POS_COMPOSITIONS * 5)  # 62016


@lru_cache(maxsize=1)
def build_variant_offset_tables() -> Tuple[np.ndarray, np.ndarray]:
    """
    Build dense tables for the canonical per-gear variant offset space.

    Offsets [0..VARIANTS_PER_GEAR):
    - 0..OV0_VARIANTS-1: OV==0 (ov_color=0)
    - OV0_VARIANTS..end: OV>0, (composition_index * 5 + (ov_color-1))

    Returns:
      (offset_gems, offset_color)
      - offset_gems: int32[VARIANTS_PER_GEAR, 6] (PP,CM,FM,FT,FF,OV) each in [0,15], sum=15
      - offset_color: int32[VARIANTS_PER_GEAR] in {0..5}
    """
    gems = np.zeros((VARIANTS_PER_GEAR, STAT_COUNT), dtype=np.int32)
    colors = np.zeros((VARIANTS_PER_GEAR,), dtype=np.int32)

    idx = 0

    # OV == 0 block (color==0)
    for pp in range(SLOT_GEM_BUDGET + 1):
        for cm in range(SLOT_GEM_BUDGET - pp + 1):
            for fm in range(SLOT_GEM_BUDGET - pp - cm + 1):
                for ft in range(SLOT_GEM_BUDGET - pp - cm - fm + 1):
                    ff = SLOT_GEM_BUDGET - pp - cm - fm - ft
                    gems[idx, :] = (pp, cm, fm, ft, ff, 0)
                    colors[idx] = 0
                    idx += 1

    if idx != OV0_VARIANTS:
        raise AssertionError(f"OV0 variant count mismatch: got {idx}, expected {OV0_VARIANTS}")

    # OV > 0 block (colors 1..5)
    for ov in range(1, SLOT_GEM_BUDGET + 1):
        rem = SLOT_GEM_BUDGET - ov
        for pp in range(rem + 1):
            for cm in range(rem - pp + 1):
                for fm in range(rem - pp - cm + 1):
                    for ft in range(rem - pp - cm - fm + 1):
                        ff = rem - pp - cm - fm - ft
                        base_vec = (pp, cm, fm, ft, ff, ov)
                        for c in range(1, 6):
                            gems[idx, :] = base_vec
                            colors[idx] = c
                            idx += 1

    if idx != VARIANTS_PER_GEAR:
        raise AssertionError(f"variant table size mismatch: got {idx}, expected {VARIANTS_PER_GEAR}")

    # Sanity: colors must be 0 iff OV==0.
    if np.any((colors == 0) != (gems[:, OV_INDEX] == 0)):
        raise AssertionError("offset_color==0 must match OV==0 exactly")

    return gems, colors


__all__ = [
    "OV0_VARIANTS",
    "OV_POS_COMPOSITIONS",
    "SLOT_GEM_BUDGET",
    "STAT_COUNT",
    "VARIANTS_PER_GEAR",
    "build_variant_offset_tables",
]
