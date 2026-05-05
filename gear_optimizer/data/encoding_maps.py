from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EncodingMaps:
    gear_name_to_id: dict[str, int]
    gear_id_to_name: dict[int, str]
    mini_name_to_id: dict[str, int]
    mini_id_to_name: dict[int, str]
    gear_count: int
    mini_count: int
