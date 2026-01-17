from __future__ import annotations

from typing import Dict, Tuple

STAT_KEYS: Tuple[str, ...] = ("PP", "CM", "FM", "FT", "FF", "OV")
OV_INDEX: int = STAT_KEYS.index("OV")

ELEMENTS: Tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")
ELEMENT_TO_ID: Dict[str, int] = {name: idx + 1 for idx, name in enumerate(ELEMENTS)}
ID_TO_ELEMENT: Dict[int, str] = {idx + 1: name for idx, name in enumerate(ELEMENTS)}

_GEM_CODE_WEIGHTS: Tuple[int, ...] = tuple(16**idx for idx in range(len(STAT_KEYS)))


def decode_gem_code(code: int) -> Tuple[int, ...]:
    vals = []
    for _ in range(len(STAT_KEYS)):
        vals.append(int(code & 0xF))
        code >>= 4
    return tuple(vals)


def encode_gem_vec(vec: Tuple[int, ...]) -> int:
    return int(sum(int(vec[idx]) * _GEM_CODE_WEIGHTS[idx] for idx in range(len(STAT_KEYS))))


def variant_key(gear_id: int, gem_code: int, ov_color: int) -> int:
    # Pack into a stable small-ish int:
    # - gear_id (<=4095) in low bits
    # - ov_color (<=7) next
    # - gem_code (< 2^24) in high bits
    return int(int(gear_id) | (int(ov_color) << 12) | (int(gem_code) << 15))


def unpack_variant_key(key: int) -> Tuple[int, int, int]:
    gear_id = int(key & 0xFFF)
    ov_color = int((key >> 12) & 0x7)
    gem_code = int(key >> 15)
    return gear_id, gem_code, ov_color
