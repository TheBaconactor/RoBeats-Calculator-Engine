from __future__ import annotations

from typing import Any, cast

import numpy as np

from gear_optimizer.gamedata import SongMini

from .item_utils import names_list



def canonicalize_genome_ids(genome_ids: Any) -> tuple[int, ...] | None:
    if genome_ids is None:
        return None
    ids = [int(x) for x in list(genome_ids)[:9]]
    if len(ids) < 9:
        return None
    gear_ids = ids[:6]
    mini_ids = sorted(ids[6:9])
    return tuple(gear_ids + mini_ids)


def ga_candidate_key(genome_ids: Any) -> str | None:
    canon = canonicalize_genome_ids(genome_ids)
    if canon is None:
        return None
    return "ga:" + ",".join(str(x) for x in canon)


def candidate_genome_ids(candidate: Any) -> tuple[int, ...] | None:
    if not isinstance(candidate, dict):
        return None
    return canonicalize_genome_ids(candidate.get("GenomeIDs"))


def _decode_names_from_registry(registry: Any, genome_ids: tuple[int, ...]) -> list[str]:
    ids_arr = np.asarray(genome_ids, dtype=np.int32)
    decode_names = getattr(registry, "decode_names", None)
    if callable(decode_names):
        decoded = cast(Any, decode_names)(ids_arr)
        return [str(x if x is not None else "None") for x in list(decoded)]
    decode_genome = getattr(registry, "decode_genome", None)
    if callable(decode_genome):
        return names_list(decode_genome(ids_arr))
    return []


def materialize_candidate_names(
    candidate: Any,
    *,
    registry: Any = None,
    mutate: bool = True,
) -> tuple[list[str], list[str]]:
    if not isinstance(candidate, dict):
        return [], []

    raw_gear = candidate.get("Gear") or []
    raw_minis = candidate.get("Minis") or []
    if raw_gear or raw_minis:
        return names_list(raw_gear), names_list(raw_minis)

    genome_ids = candidate_genome_ids(candidate)
    if genome_ids is None:
        return [], []

    registry_obj = registry if registry is not None else candidate.get("_ga_registry")
    if registry_obj is None:
        return [], []

    names = _decode_names_from_registry(registry_obj, genome_ids)
    if len(names) < 9:
        return [], []

    gear_names = list(names[:6])
    mini_names = list(names[6:9])
    if mutate:
        candidate["Gear"] = list(gear_names)
        candidate["Minis"] = list(mini_names)
    return gear_names, mini_names


def candidate_loadout_hash(
    candidate: Any,
    *,
    registry: Any = None,
    minis_by_name: dict[str, SongMini] | None = None,
    primary_color: str = "",
    secondary_color: str = "",
    selected_color: str = "",
    mutate: bool = True,
) -> str | None:
    """Resolve a candidate to the same song-context hash used by DB persistence."""
    if not isinstance(candidate, dict):
        return None

    explicit = candidate.get("loadout_hash")
    if explicit:
        return str(explicit)

    def _remember(loadout_hash: str) -> str:
        loadout_hash = str(loadout_hash)
        if mutate and loadout_hash:
            candidate["loadout_hash"] = loadout_hash
            candidate["_resolved_loadout_hash"] = loadout_hash
        return loadout_hash

    gear_names, mini_names = materialize_candidate_names(candidate, registry=registry, mutate=mutate)
    if not gear_names and not mini_names:
        return ga_candidate_key(candidate.get("GenomeIDs"))

    primary_color = str(primary_color or "")
    secondary_color = str(secondary_color or "")
    selected_color = str(selected_color or "")
    if not selected_color:
        selected_color = primary_color or secondary_color

    if (primary_color or secondary_color) and isinstance(minis_by_name, dict):
        from ...data.loadout_equivalence import (
            effective_loadout_hash_from_names,
            effective_mini_signature_for_name,
        )

        mini_sigs = [
            effective_mini_signature_for_name(str(name), minis_by_name, primary_color, secondary_color, selected_color)
            for name in mini_names
        ]
        return _remember(effective_loadout_hash_from_names(list(gear_names), mini_sigs))

    from .loadout_hashing import resolve_loadout_hash

    return _remember(resolve_loadout_hash(gear_names, mini_names))
