"""GA->FG effective-dedup equivalence tables + CPU reference selector (Slice 1).

This module is the CPU-side specification for "Slice 1 - GPU effective-dedup"
of the fused GA->FG handoff (docs/research/GA_FG_FUSED_HANDOFF_DESIGN_20260612.md).

The FG stage's host select (``gear_optimizer/pipeline/fg.py``, ``_selected_surface``)
dedups GA candidates by an *effective loadout hash* that folds:

- gear NAME equivalence (two distinct item ids with the same ``Name`` collapse),
- mini song-context signature equivalence (two distinct mini ids whose element
  stats fold to the same effective signature collapse).

The GPU select kernel
(``ga_select_top_base_fg_candidate_coords_kernel``,
``solver/taichi_gem/kernels/ga_eval/payload.py:467``) currently dedups by *raw
item-id* keys, so id-distinct-but-effective-duplicate genomes survive and can
displace loadouts the host would have kept -> ``best_fg_score`` would not be
bit-exact after fusing.

This module builds the two id->effective-rank lookup tables the future GPU
kernel needs, and a pure-numpy reference selector that reproduces the host
selection set exactly. The reference selector is the bit-exact spec the GPU
kernel must match.

Equivalence semantics replicated (file:line of the host source matched):

- gear name equivalence: ``loadout_hashing.effective_loadout_hash_from_names``
  (gear_optimizer/helpers/song_helpers/loadout_hashing.py:23) sorts/joins gear
  NAMES, so name-equality is the gear equivalence relation.
- mini signature: ``loadout_equivalence.effective_mini_signature`` /
  ``effective_mini_signature_for_name``
  (gear_optimizer/data/loadout_equivalence.py:228 / :255):
  ``(pp, cm, fm, ft, ff, p_val, s_val, sel_val)`` where the three element
  values are ``safe_int`` reads of the stat keyed by the song's primary,
  secondary and selected color names. Unknown mini name -> ``("name", name)``;
  empty name -> ``("name", "")``. The signature depends on the color context,
  so ``mini_sig_id`` is built PER (primary, secondary, selected) color combo.
- effective hash assembly: ``effective_loadout_hash_from_names``
  (loadout_hashing.py:23) renders each mini signature with
  ``"|".join(str(x) for x in sig)``, sorts the rendered strings, and MD5s
  ``f"GEAR:{...}::MINIS:{...}"``. The reference selector mirrors this exactly by
  using the dense rank ids as the per-slot tokens (rank ids preserve the
  equivalence partition; the selector hashes ranks, not names, but groups
  candidates identically because the partition is identical).

The selected-set (which candidates survive dedup + top-N) is partition- and
score-driven, so it is invariant to whether the per-slot token is the original
name or its dense rank. The reference selector therefore keys on the dense
ranks (cheap, GPU-friendly) and is proven set-equal to the host in the tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import threading

import numpy as np

from ..core.singleflight import SingleFlight
from ..data.loadout_equivalence import effective_mini_signature
from ..gamedata import Gear, SongMini
from .item_registry import MINI_SLOT_INDICES, ItemRegistry


def _registry_id_to_item(registry: Any) -> dict[int, Gear | SongMini]:
    """Return the registry's ``id -> item`` map, failing loudly if absent."""
    id_to_item = getattr(registry, "id_to_item", None)
    if not isinstance(id_to_item, dict):
        raise TypeError(
            "fg_effective_dedup: registry must expose an id_to_item dict "
            f"(got {type(id_to_item).__name__})"
        )
    return id_to_item


def _gear_id_range(registry: ItemRegistry) -> range:
    """Inclusive id range covering all gear slot ids (slots 0..5).

    Gear ids are contiguous from the first gear slot start to the last mini id
    that precedes the mini pool. We derive the upper bound from the mini slot
    start so name-rank covers exactly the gear ids.
    """
    slot_start = registry.slot_start
    slot_count = registry.slot_count
    mini_start = int(slot_start[MINI_SLOT_INDICES[0]])
    # Gear ids occupy [1, mini_start). id 0 is the reserved empty slot.
    # Validate the gear region is exactly the union of the 6 gear slots.
    gear_hi = 0
    for slot_idx in range(6):
        start = int(slot_start[slot_idx])
        count = int(slot_count[slot_idx])
        if count:
            gear_hi = max(gear_hi, start + count)
    if gear_hi and gear_hi != mini_start:
        raise ValueError(
            "fg_effective_dedup: gear id region is not contiguous up to the "
            f"mini pool (gear end={gear_hi}, mini start={mini_start})"
        )
    return range(1, mini_start)


def build_gear_name_rank(registry: ItemRegistry) -> np.ndarray:
    """Build ``gear_name_rank``: int32 array indexed by gear item id.

    Two gear ids share a rank iff their registry item ``Name`` is identical
    (the exact equivalence the host effective hash uses, which keys on gear
    names directly). Rank ids are dense and assigned in ascending-name order
    for determinism. id 0 (reserved empty) gets rank 0.

    Fails loudly on malformed registry entries (missing/empty ``Name``).
    """
    id_to_item = _registry_id_to_item(registry)
    gear_ids = _gear_id_range(registry)
    n_items = int(registry.n_items)

    # First pass: collect the canonical name per gear id, failing loudly.
    name_by_id: dict[int, str] = {}
    for item_id in gear_ids:
        item = id_to_item.get(item_id)
        if item is None:
            raise ValueError(
                f"fg_effective_dedup: gear id {item_id} missing from registry"
            )
        if not item.name.strip():
            raise ValueError(
                f"fg_effective_dedup: gear id {item_id} has empty/malformed Name"
            )
        name_by_id[item_id] = item.name

    # Dense ranks assigned in ascending name order (deterministic, stable).
    unique_names = sorted(set(name_by_id.values()))
    rank_of_name = {name: rank for rank, name in enumerate(unique_names, start=1)}

    rank = np.zeros(n_items, dtype=np.int32)
    for item_id, name in name_by_id.items():
        rank[item_id] = rank_of_name[name]
    return rank


@dataclass(frozen=True)
class MiniSigTables:
    """Per color-combo mini equivalence table.

    Attributes:
        sig_id: int32 array indexed by mini item id; equal ids iff their minis
            fold to the same effective signature in this color context. id 0 ->
            sig id 0.
        primary_color / secondary_color / selected_color: the color context this
            table was built for (the builder key).
    """

    sig_id: np.ndarray
    primary_color: str
    secondary_color: str
    selected_color: str


def _resolve_selected_color(
    primary_color: str, secondary_color: str, selected_color: str
) -> str:
    """Mirror candidate_loadout_hash's selected-color defaulting (ga_entry_utils.py:138)."""
    selected = str(selected_color or "")
    if not selected:
        selected = str(primary_color or "") or str(secondary_color or "")
    return selected


def build_mini_sig_id(
    registry: ItemRegistry,
    *,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
) -> MiniSigTables:
    """Build ``mini_sig_id`` for one (primary, secondary, selected) color combo.

    Two mini ids share a signature id iff their effective mini signature is
    equal in this color context (``effective_mini_signature``,
    loadout_equivalence.py:228). Signature ids are dense, assigned in sorted
    signature order for determinism. id 0 (reserved empty) gets sig id 0.

    The signature depends on the song's primary/secondary/selected colors, so
    this MUST be rebuilt per color combination and keyed accordingly. The
    selected color defaults to ``primary or secondary`` when empty, exactly as
    ``candidate_loadout_hash`` does (ga_entry_utils.py:138).

    Fails loudly on malformed registry entries (missing/empty ``Name``).
    """
    id_to_item = _registry_id_to_item(registry)
    n_items = int(registry.n_items)
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    selected = _resolve_selected_color(primary, secondary, selected_color)

    mini_slot = MINI_SLOT_INDICES[0]
    mini_start = int(registry.slot_start[mini_slot])
    mini_count = int(registry.slot_count[mini_slot])
    mini_ids = range(mini_start, mini_start + mini_count)

    # Collect the effective signature per mini id, failing loudly on bad entries.
    sig_by_id: dict[int, tuple[Any, ...]] = {}
    for item_id in mini_ids:
        item = id_to_item.get(item_id)
        if item is None:
            raise ValueError(
                f"fg_effective_dedup: mini id {item_id} missing from registry"
            )
        if not item.name.strip():
            raise ValueError(
                f"fg_effective_dedup: mini id {item_id} has empty/malformed Name"
            )
        # This matches the host's known-mini path; the host's unknown-name fallback
        # ("name", name) cannot occur here because every registry id resolves to a
        # concrete item.
        sig_by_id[item_id] = effective_mini_signature(item.stats, primary, secondary, selected)

    def _sig_sort_key(sig: tuple[Any, ...]) -> str:
        return "|".join(str(x) for x in sig)

    unique_sigs = sorted(set(sig_by_id.values()), key=_sig_sort_key)
    id_of_sig = {sig: idx for idx, sig in enumerate(unique_sigs, start=1)}

    sig_id = np.zeros(n_items, dtype=np.int32)
    for item_id, sig in sig_by_id.items():
        sig_id[item_id] = id_of_sig[sig]

    return MiniSigTables(
        sig_id=sig_id,
        primary_color=primary,
        secondary_color=secondary,
        selected_color=selected,
    )


# ---------------------------------------------------------------------------
# Canonical CPU reference selector
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Cached production effective-equivalence tables
# ---------------------------------------------------------------------------


_CONTEXT_TABLES_LOCK = threading.Lock()
_CONTEXT_TABLES_CACHE: dict[tuple[int, str, str, str], tuple[np.ndarray, np.ndarray]] = {}
_CONTEXT_TABLES_SINGLEFLIGHT: SingleFlight[
    tuple[int, str, str, str], tuple[np.ndarray, np.ndarray]
] = SingleFlight()
# The cache key is id(registry); registries are LRU-evicted from the 32-entry _REGISTRY_GPU_CACHE
# and rebuilt with fresh ids, so without a bound every rebuild leaks a permanent
# (gear_name_rank, sig_id) ndarray pair for a now-dead registry. The live working set is the
# <=32 registries x their colour contexts, so a generous cap clears rarely and only sheds orphans.
_CONTEXT_TABLES_CACHE_MAX = 256


def effective_tables_for_context(
    registry: ItemRegistry,
    *,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Build (gear_name_rank, mini_sig_id) for one song color context, cached.

    The cache key is (registry identity, colors): registries are long-lived and
    shared across songs of a pool, so repeat songs hit the cache and the build
    cost stays off the per-song path. A rebuilt registry gets a new id and a
    fresh (correct) build.
    """
    key = (
        id(registry),
        str(primary_color or ""),
        str(secondary_color or ""),
        str(selected_color or ""),
    )
    with _CONTEXT_TABLES_LOCK:
        cached = _CONTEXT_TABLES_CACHE.get(key)
    if cached is not None:
        return cached

    def _build_and_cache() -> tuple[np.ndarray, np.ndarray]:
        with _CONTEXT_TABLES_LOCK:
            existing = _CONTEXT_TABLES_CACHE.get(key)
        if existing is not None:
            return existing
        gear_rank = build_gear_name_rank(registry)
        sig_tables = build_mini_sig_id(
            registry,
            primary_color=str(primary_color or ""),
            secondary_color=str(secondary_color or ""),
            selected_color=str(selected_color or ""),
        )
        tables = (gear_rank, sig_tables.sig_id)
        with _CONTEXT_TABLES_LOCK:
            if len(_CONTEXT_TABLES_CACHE) >= _CONTEXT_TABLES_CACHE_MAX:
                _CONTEXT_TABLES_CACHE.clear()
            _CONTEXT_TABLES_CACHE[key] = tables
        return tables

    return _CONTEXT_TABLES_SINGLEFLIGHT.run(key, _build_and_cache)
