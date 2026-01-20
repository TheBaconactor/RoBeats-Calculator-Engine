from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

from .keys import ELEMENT_TO_ID, OV_INDEX, STAT_KEYS
from .variant_space import build_variant_offset_tables

UPGRADE_ID_TO_STAT = {
    16: "PP",
    11: "CM",
    18: "FM",
    20: "FT",
    14: "FF",
}

UPGRADE_ID_TO_ELEMENT = {
    6: "Chill",
    9: "Vibe",
    12: "Flow",
    22: "Rush",
    21: "Beat",
}

ALLOWED_UPGRADE_IDS = frozenset(set(UPGRADE_ID_TO_STAT) | set(UPGRADE_ID_TO_ELEMENT))


def normalize_for_lookup(value: str) -> str:
    cleaned = (
        str(value or "")
        .lower()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\\'", "'")
        .replace('\\"', '"')
        .replace("\t", " ")
        .replace("\n", " ")
        .strip()
    )
    return " ".join(cleaned.split())


@lru_cache(maxsize=1)
def _offset_lookup() -> Dict[Tuple[int, ...], int]:
    gems, colors = build_variant_offset_tables()
    lookup: Dict[Tuple[int, ...], int] = {}
    for idx in range(int(gems.shape[0])):
        vec = gems[idx]
        key = (
            int(vec[0]),
            int(vec[1]),
            int(vec[2]),
            int(vec[3]),
            int(vec[4]),
            int(vec[5]),
            int(colors[idx]),
        )
        lookup[key] = int(idx)
    return lookup


@dataclass(frozen=True)
class SeedInventoryResult:
    raw_variant_ids: np.ndarray
    diagnostics: Dict[str, Any]


def _extract_upgrade_ids(entry: Any) -> List[int]:
    upgrades_raw = entry.get("upgrades") if isinstance(entry, dict) else None
    if not isinstance(upgrades_raw, list):
        return []
    upgrade_ids: List[int] = []
    for upgrade in upgrades_raw:
        upgrade_id = None
        if isinstance(upgrade, dict):
            upgrade_id = upgrade.get("upgradeId")
        elif isinstance(upgrade, int):
            upgrade_id = upgrade
        if upgrade_id is None:
            continue
        try:
            upgrade_id = int(upgrade_id)
        except Exception:
            continue
        if upgrade_id in ALLOWED_UPGRADE_IDS:
            upgrade_ids.append(upgrade_id)
    return upgrade_ids


def build_seeded_inventory_variants(
    inventory_gear: Iterable[Dict[str, Any]],
    gear_id_map: Dict[str, int],
) -> SeedInventoryResult:
    gear_id_by_norm = {normalize_for_lookup(name): gid for name, gid in gear_id_map.items()}

    raw_vids: set[int] = set()
    unknown_gear: List[str] = []
    partial_upgrades: List[str] = []
    mixed_elements: List[str] = []
    invalid_offsets: List[str] = []

    total_entries = 0
    for entry in inventory_gear:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        total_entries += 1
        gid = gear_id_by_norm.get(normalize_for_lookup(name))
        if gid is None:
            unknown_gear.append(name)
            continue

        upgrade_ids = _extract_upgrade_ids(entry)
        if not upgrade_ids:
            partial_upgrades.append(f"{name} (0/15)")
            continue

        counts = [0] * len(STAT_KEYS)
        element_name = None
        mixed_element = False
        for upgrade_id in upgrade_ids:
            stat = UPGRADE_ID_TO_STAT.get(upgrade_id)
            if stat:
                counts[STAT_KEYS.index(stat)] += 1
                continue
            element = UPGRADE_ID_TO_ELEMENT.get(upgrade_id)
            if element:
                counts[OV_INDEX] += 1
                if element_name is None:
                    element_name = element
                elif element_name != element:
                    mixed_element = True
                continue

        total_gems = sum(counts)
        if mixed_element:
            mixed_elements.append(name)
            continue
        if total_gems != 15:
            partial_upgrades.append(f"{name} ({total_gems}/15)")
            continue

        ov = counts[OV_INDEX]
        if ov > 0 and not element_name:
            invalid_offsets.append(f"{name} (missing element)")
            continue
        color_id = ELEMENT_TO_ID.get(element_name or "", 0) if ov > 0 else 0
        key = (counts[0], counts[1], counts[2], counts[3], counts[4], counts[5], int(color_id))
        offset = _offset_lookup().get(key)
        if offset is None:
            invalid_offsets.append(name)
            continue

        raw_vids.add((int(gid) << 16) | int(offset))

    diagnostics = {
        "total_entries": int(total_entries),
        "seeded_variants": int(len(raw_vids)),
        "skipped": {
            "unknown_gear": unknown_gear[:25],
            "partial_upgrades": partial_upgrades[:25],
            "mixed_elements": mixed_elements[:25],
            "invalid_offsets": invalid_offsets[:25],
        },
    }

    raw_vids_np = np.asarray(sorted(raw_vids), dtype=np.int32)
    return SeedInventoryResult(raw_variant_ids=raw_vids_np, diagnostics=diagnostics)


__all__ = ["SeedInventoryResult", "build_seeded_inventory_variants"]
