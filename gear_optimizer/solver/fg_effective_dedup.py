"""GA->FG effective-dedup equivalence tables + CPU reference selector (Slice 1).

This module is the CPU-side specification for "Slice 1 - GPU effective-dedup"
of the fused GA->FG handoff (docs/research/GA_FG_FUSED_HANDOFF_DESIGN_20260612.md).

The production host selector ``select_top_base_ga_candidates``
(``gear_optimizer/helpers/song_helpers/fg_candidate_selector.py``) dedups GA
candidates by an *effective loadout hash* that folds:

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


def select_top_base_fg_candidates_reference(
    *,
    base_scores: np.ndarray,
    gear_ids: np.ndarray,
    mini_ids: np.ndarray,
    gear_name_rank: np.ndarray,
    mini_sig_id: np.ndarray,
    limit: int,
) -> np.ndarray:
    """Pure-numpy reference for the GPU GA->FG select kernel (the bit-exact spec).

    Consumes the same per-candidate inputs the GPU select kernel sees
    conceptually (payload.py:512-531): a base score int, 6 gear ids, and 3
    sorted mini ids per candidate; plus the two effective-equivalence tables.
    Returns the indices (into the input arrays) of the selected candidates, in
    canonical output order.

    Args:
        base_scores: (N,) int candidate base scores. Rows with score <= 0 are
            skipped (matches the GPU kernel's ``if score <= 0: continue`` at
            payload.py:513 and the host's positive BaseScore rows).
        gear_ids: (N, 6) int gear item ids.
        mini_ids: (N, 3) int mini item ids (the kernel sorts them; we sort here
            too so callers may pass unsorted).
        gear_name_rank: gear name-rank table from ``build_gear_name_rank``.
        mini_sig_id: per-color mini signature table from ``build_mini_sig_id``.
        limit: top-N cap on the deduped survivors.

    Dedup rule (matches host fg_candidate_selector.py:49-54 AND GPU
    payload.py:587-592): for each effective key keep the occurrence with the
    MAXIMUM base score; ties broken by EARLIEST scan order (a later row with an
    equal score does NOT displace the earlier one - the host keeps
    ``rank = (base_score, -order)`` max which is strictly-better-or-earlier, and
    the GPU updates only on ``score > prev_score``). The kept candidate's
    original input index is preserved.

    Output order / final tie-break -- THE single canonical rule (matches the GPU
    ``_better_base``, payload.py:429-452): survivors are ordered by

        (base_score DESC, canonical_ids DESC, scan_order ASC)

    where ``canonical_ids`` is the kept occurrence's 9-int genome
    ``(g0..g5, m0, m1, m2)`` with the three mini ids sorted ascending, compared
    left-to-right with the LARGER id winning. ``scan_order`` is the kept
    occurrence's input index (earliest wins) and mirrors the GPU's "lower stub
    index wins" final stable tie-breaker. The top ``limit`` survivors are then
    returned.

    Canonical tie-break choice and rationale (Slice 1 STEP A decision): the GPU
    kernel's ``_better_base`` rule (canonical-IDs descending) is adopted as THE
    single documented rule on BOTH this host reference and the GPU select kernel.
    It is GPU-portable (no MD5, pure integer comparison) and STEP A proved it
    set-identical to the host's former MD5-hash-descending rule on all 96 real
    captured pools (the 51-cap never binds and no base-score tie ever sits on the
    selection boundary). Base scores are large distinct ints in production, so
    the secondary id/scan tie-breaks are exercised only by synthetic pools; the
    A/B changed==0 gate catches any residue on real data.
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
    #    Track the kept occurrence's canonical genome ids (6 gear + 3 sorted mini)
    #    for the canonical-IDs tie-break, matching the GPU stub_ids (set at the
    #    kept row; the effective key is constant across a key's occurrences but the
    #    raw ids are not -- we compare the kept occurrence's raw ids, exactly as
    #    the GPU ``_better_base`` compares ``ga_fg_select_stub_ids``).
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

    # 2) Final order -- THE canonical rule: (base_score DESC, canonical_ids DESC,
    #    scan_order ASC), then top-N. Sorting the negated id tuple ascending gives
    #    descending id order (larger id wins left-to-right), and the positive
    #    scan-order index breaks the final tie with the earliest occurrence, which
    #    mirrors the GPU "lower stub index wins".
    survivors = []
    for key, idx in best_idx_by_key.items():
        neg_ids = tuple(-int(v) for v in best_ids_by_key[key])
        survivors.append((-int(base_scores[idx]), neg_ids, int(idx)))
    survivors.sort()
    selected = [idx for _neg_score, _neg_ids, idx in survivors[:limit_i]]
    return np.asarray(selected, dtype=np.int64)


# ---------------------------------------------------------------------------
# Slice 1 tie-evidence capture (gated DEBUG instrumentation; OFF by default)
# ---------------------------------------------------------------------------


_CONTEXT_TABLES_LOCK = threading.Lock()
_CONTEXT_TABLES_CACHE: dict[tuple[int, str, str, str], tuple[np.ndarray, np.ndarray]] = {}


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
    gear_rank = build_gear_name_rank(registry)
    sig_tables = build_mini_sig_id(
        registry,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
    )
    tables = (gear_rank, sig_tables.sig_id)
    with _CONTEXT_TABLES_LOCK:
        _CONTEXT_TABLES_CACHE[key] = tables
    return tables


def dump_candidate_pool_jsonl(
    path: str,
    *,
    registry: ItemRegistry,
    candidates: list[dict],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    limit: int,
) -> None:
    """Append one analyzer-shaped pool line to ``path`` (JSONL).

    This is the *only* permanent capture site for Slice 1 tie evidence. It is
    gated by a non-empty ``FG_SELECT_TIE_DUMP`` path (read via the parsing.py
    env helper at the call site) and is OFF in production by default. It writes
    exactly the schema ``tools/dev/analyze_fg_select_tie_boundaries.py`` consumes:
    ``{limit, gear_name_rank, mini_sig_id, candidates:[{score,gear_ids,mini_ids}]}``.

    The two equivalence tables are built for THIS song's color context (the
    mini table is color-context dependent, so it is rebuilt per call - this is
    debug-only, not the hot path). Candidates are the raw GA-decode pool BEFORE
    the host select, so the captured pool matches what the GPU select kernel
    scans (the funnel input, not the funnel output).

    Fails loudly on a malformed pool entry (missing GenomeIDs) - debug capture
    must not silently drop rows and skew the tie statistics.
    """
    import json

    gear_name_rank = build_gear_name_rank(registry)
    mini_tab = build_mini_sig_id(
        registry,
        primary_color=primary_color,
        secondary_color=secondary_color,
        selected_color=selected_color,
    )

    rows: list[dict[str, Any]] = []
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        genome_ids = cand.get("GenomeIDs")
        if genome_ids is None:
            raise ValueError(
                "fg_effective_dedup.dump_candidate_pool_jsonl: candidate missing GenomeIDs"
            )
        ids = [int(x) for x in list(genome_ids)[:9]]
        if len(ids) < 9:
            raise ValueError(
                "fg_effective_dedup.dump_candidate_pool_jsonl: candidate has <9 GenomeIDs"
            )
        score = cand.get("BaseScore")
        if score is None:
            score = cand.get("Score", 0)
        rows.append(
            {
                "score": int(score or 0),
                "gear_ids": ids[:6],
                "mini_ids": sorted(ids[6:9]),
            }
        )

    pool = {
        "limit": int(limit),
        "primary_color": str(primary_color or ""),
        "secondary_color": str(secondary_color or ""),
        "selected_color": str(mini_tab.selected_color or ""),
        "gear_name_rank": [int(x) for x in gear_name_rank.tolist()],
        "mini_sig_id": [int(x) for x in mini_tab.sig_id.tolist()],
        "candidates": rows,
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(pool) + "\n")
