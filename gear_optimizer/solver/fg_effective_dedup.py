"""Base-to-FG effective-dedup equivalence tables and CPU reference selector.

The production exact Base funnel deduplicates candidates by an effective
loadout hash that folds:

- gear NAME equivalence (two distinct item ids with the same ``Name`` collapse),
- mini song-context signature equivalence (two distinct mini ids whose element
  stats fold to the same effective signature collapse).

This module builds the two id-to-effective-rank lookup tables and provides the
pure NumPy selector used by the exact Base candidate surface.

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

from ..core.catalog_fingerprint import stable_json_fingerprint
from ..core.singleflight import SingleFlight
from ..data.loadout_equivalence import effective_mini_signature
from .item_registry import MINI_SLOT_INDICES, ItemRegistry


def _registry_id_to_item(registry: Any) -> dict[int, dict]:
    """Return the registry's ``id -> item dict`` map, failing loudly if absent."""
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
        if not isinstance(item, dict):
            raise ValueError(
                f"fg_effective_dedup: gear id {item_id} missing from registry"
            )
        name = item.get("Name")
        if not name or not str(name).strip():
            raise ValueError(
                f"fg_effective_dedup: gear id {item_id} has empty/malformed Name"
            )
        name_by_id[item_id] = str(name)

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
    """Mirror candidate_loadout_hash's selected-color defaulting."""
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
    ``candidate_loadout_hash`` does.

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
        if not isinstance(item, dict):
            raise ValueError(
                f"fg_effective_dedup: mini id {item_id} missing from registry"
            )
        name = item.get("Name")
        if not name or not str(name).strip():
            raise ValueError(
                f"fg_effective_dedup: mini id {item_id} has empty/malformed Name"
            )
        # The registry item dict carries the mini's stat columns directly, which
        # is exactly what effective_mini_signature consumes (it reads stat keys
        # via safe_int). This matches the host's known-mini path; the host's
        # unknown-name fallback ("name", name) cannot occur here because every
        # registry id resolves to a concrete item.
        sig_by_id[item_id] = effective_mini_signature(item, primary, secondary, selected)

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


def _effective_key(
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    gear_name_rank: np.ndarray,
    mini_sig_id: np.ndarray,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Effective dedup key for one candidate.

    Mirrors ``effective_loadout_hash_from_names`` (loadout_hashing.py:23):
    gear tokens sorted; mini tokens sorted. Here tokens are dense ranks/sig ids,
    which preserve the host's equivalence partition exactly, so the grouping is
    identical to the host's MD5-of-names key. We key on the (sorted-gear,
    sorted-mini) rank tuple instead of an MD5 string: same partition, no hash
    collisions, GPU-portable.
    """
    gear_ranks = tuple(sorted(int(gear_name_rank[int(g)]) for g in gear_ids))
    mini_sigs = tuple(sorted(int(mini_sig_id[int(m)]) for m in mini_ids))
    return (gear_ranks, mini_sigs)


def extend_effective_loadout_keys(
    keys: set[tuple[tuple[int, ...], tuple[int, ...]]],
    *,
    candidate_ids: np.ndarray,
    gear_name_rank: np.ndarray,
    mini_sig_id: np.ndarray,
    limit: int,
) -> int:
    """Extend ``keys`` in scan order, stopping once ``limit`` unique keys exist."""

    target = int(limit)
    if target <= 0 or len(keys) >= target:
        return int(len(keys))
    ids = np.asarray(candidate_ids)
    if ids.ndim != 2 or ids.shape[1] != 9:
        raise ValueError(f"candidate_ids must have shape (N,9); got {ids.shape}")
    if ids.shape[0] <= 0:
        return int(len(keys))
    if not np.issubdtype(ids.dtype, np.integer) or np.any(ids <= 0):
        raise ValueError("effective-loadout candidates require positive integer IDs")
    gear_rank = np.asarray(gear_name_rank, dtype=np.int32).reshape(-1)
    mini_sig = np.asarray(mini_sig_id, dtype=np.int32).reshape(-1)
    max_id = int(np.max(ids))
    if gear_rank.shape[0] <= max_id or mini_sig.shape[0] <= max_id:
        raise ValueError("effective-equivalence tables do not cover every candidate ID")
    if np.any(gear_rank[ids[:, :6]] <= 0) or np.any(mini_sig[ids[:, 6:]] <= 0):
        raise ValueError("effective-equivalence tables contain an unbound candidate ID")

    for row in ids:
        keys.add(_effective_key(row[:6], row[6:], gear_rank, mini_sig))
        if len(keys) >= target:
            break
    return int(len(keys))


def select_top_base_fg_candidates_reference(
    *,
    base_scores: np.ndarray,
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    gear_name_rank: np.ndarray,
    mini_sig_id: np.ndarray,
    limit: int,
) -> np.ndarray:
    """Pure-NumPy effective-dedup selector for the Base-to-FG funnel.

    Consumes a base score, six gear IDs, and three mini IDs per candidate, plus
    the two effective-equivalence tables.
    Returns the indices (into the input arrays) of the selected candidates, in
    canonical output order.

    Args:
        base_scores: (N,) int candidate base scores. Rows with score <= 0 are skipped.
        gear_ids: (N, 6) int gear item ids.
        mini_ids: (N, 3) int mini item ids (the kernel sorts them; we sort here
            too so callers may pass unsorted).
        gear_name_rank: gear name-rank table from ``build_gear_name_rank``.
        mini_sig_id: per-color mini signature table from ``build_mini_sig_id``.
        limit: top-N cap on the deduped survivors.

    Dedup rule: for each effective key keep the occurrence with the
    MAXIMUM base score; ties broken by EARLIEST scan order (a later row with an
    equal score does not displace the earlier one). The kept candidate's original
    input index is preserved.

    Survivors use one canonical ordering:

        (base_score DESC, canonical_ids DESC, scan_order ASC)

    where ``canonical_ids`` is the kept occurrence's 9-int loadout
    ``(g0..g5, m0, m1, m2)`` with the three mini ids sorted ascending, compared
    left-to-right with the LARGER id winning. ``scan_order`` is the kept
    occurrence's input index (earliest wins). The top ``limit`` survivors are returned.
    """
    base_scores = np.asarray(base_scores)
    gear_ids = np.asarray(gear_ids)
    mini_ids = np.asarray(mini_ids)
    n = int(base_scores.shape[0])
    if n == 0:
        return np.empty(0, dtype=np.int64)
    if gear_ids.shape != (n, 6):
        raise ValueError(f"gear_ids must be (N,6); got {gear_ids.shape}")
    if mini_ids.shape != (n, 3):
        raise ValueError(f"mini_ids must be (N,3); got {mini_ids.shape}")
    limit_i = int(limit)
    if limit_i <= 0:
        return np.empty(0, dtype=np.int64)

    # 1) Dedup by effective key: keep max base score, earliest scan order on ties.
    #    Track the kept occurrence's canonical loadout IDs (6 gear + 3 sorted minis).
    best_idx_by_key: dict[tuple, int] = {}
    best_score_by_key: dict[tuple, int] = {}
    best_ids_by_key: dict[tuple, tuple[int, ...]] = {}
    for order in range(n):
        score = int(base_scores[order])
        if score <= 0:
            continue
        key = _effective_key(
            gear_ids[order], mini_ids[order], gear_name_rank, mini_sig_id
        )
        prev = best_score_by_key.get(key)
        # Strictly-better-or-earliest: only replace on a strictly higher score
        # (earliest scan order wins exact ties, matching both host and GPU).
        if prev is None or score > prev:
            best_score_by_key[key] = score
            best_idx_by_key[key] = order
            gear_row = tuple(int(g) for g in gear_ids[order])
            mini_row = tuple(sorted(int(m) for m in mini_ids[order]))
            best_ids_by_key[key] = gear_row + mini_row

    # 2) Final order: (base_score DESC, canonical_ids DESC,
    #    scan_order ASC), then top-N. Sorting the negated id tuple ascending gives
    #    descending id order (larger id wins left-to-right), and the positive
    #    scan-order index breaks the final tie with the earliest occurrence.
    survivors = []
    for key, idx in best_idx_by_key.items():
        neg_ids = tuple(-int(v) for v in best_ids_by_key[key])
        survivors.append((-int(base_scores[idx]), neg_ids, int(idx)))
    survivors.sort()
    selected = [idx for _neg_score, _neg_ids, idx in survivors[:limit_i]]
    return np.asarray(selected, dtype=np.int64)


# ---------------------------------------------------------------------------
# Cached production effective-equivalence tables
# ---------------------------------------------------------------------------


_CONTEXT_TABLES_LOCK = threading.Lock()
_ContextTableKey = tuple[int, bytes, str, str, str]
_ContextTableEntry = tuple[ItemRegistry, np.ndarray, np.ndarray]

_CONTEXT_TABLES_CACHE: dict[_ContextTableKey, _ContextTableEntry] = {}
_CONTEXT_TABLES_SINGLEFLIGHT: SingleFlight[
    _ContextTableKey, tuple[np.ndarray, np.ndarray]
] = SingleFlight()
_CONTEXT_TABLES_CACHE_MAX = 256


def _registry_content_fingerprint(registry: ItemRegistry) -> bytes:
    id_to_item = _registry_id_to_item(registry)
    payload = {
        "n_items": int(registry.n_items),
        "slot_start": [int(value) for value in registry.slot_start],
        "slot_count": [int(value) for value in registry.slot_count],
        "items": [
            (int(item_id), item)
            for item_id, item in sorted(id_to_item.items(), key=lambda pair: int(pair[0]))
        ],
    }
    return stable_json_fingerprint(payload)


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
        _registry_content_fingerprint(registry),
        str(primary_color or ""),
        str(secondary_color or ""),
        str(selected_color or ""),
    )
    with _CONTEXT_TABLES_LOCK:
        cached = _CONTEXT_TABLES_CACHE.get(key)
    if cached is not None and cached[0] is registry:
        return cached[1], cached[2]

    def _build_and_cache() -> tuple[np.ndarray, np.ndarray]:
        with _CONTEXT_TABLES_LOCK:
            existing = _CONTEXT_TABLES_CACHE.get(key)
        if existing is not None and existing[0] is registry:
            return existing[1], existing[2]
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
            # Retain the registry to defeat object-id reuse. The key's content
            # digest invalidates same-object item/name/stat/slot mutations.
            _CONTEXT_TABLES_CACHE[key] = (registry, gear_rank, sig_tables.sig_id)
        return tables

    return _CONTEXT_TABLES_SINGLEFLIGHT.run(key, _build_and_cache)
