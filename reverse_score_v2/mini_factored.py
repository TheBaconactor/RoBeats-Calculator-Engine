"""Factored mini relation for the reverse score engine v2 (handoff §16.1).

The flat mini axis in ``reverse_score_v2.domain_ir`` enumerates 138,601
options per mini slot (90 pets × 140 rank-capped levels × 11 ascensions
+ 1 empty option). Handoff §16.1 rejects the §15.3 estimate
(``138,601 → ~4,798``) as unproved: the components couple through pet
compatibility, rank-level legality, ascension routing, cross-slot
uniqueness, and identity multiplicity. This module implements the mini
axis as a **factored relation** -- a JOIN over (pet, level, rank, asc)
compatibility, not a pre-materialized 138,601-row table -- and exposes
the four §16.1 parity surfaces (set equality, contribution multiplicities,
rank/unrank identity, cross-slot legality) plus a deterministic
lexicographic rank/unrank over the factored representation.

Production reuse (no game-model duplication):

- ``gear_optimizer.data.mini_scaling.pet_stats_delta`` -- the canonical
  forward scaling law (rank × base_mods + floor(color_mods × scale(level))).
- ``gear_optimizer.data.mini_scaling.pet_color_level_scale`` -- the
  per-level lerp(1..5 over level 1..50).
- ``gear_optimizer.data.mini_scaling.pet_rank_to_max_level`` -- rank →
  level cap (20/30/40/50).
- ``gear_optimizer.data.mini_scaling.extract_pet_info`` -- PetInfo table
  extractor.
- ``gear_optimizer.data.mini_ascension.materialize_mini_for_song`` --
  canonical ascension 0..10 + song-target materialization.
- ``gear_optimizer.data.csv_parser.parse_mini_rows`` -- Minis.csv parser.

The factored relation decomposes the mini contribution vector

```
contribution(pet, level, rank, asc, song) =
    rank * base_mods(pet)                                  [base part]
  + per-stat floor(color_mods(pet) * scale(level))         [color part]
  + ascension_bonus(pet, asc, song)                       [asc part]
```

into three additive sub-relations sharing a pet-archetype coordinate:

- **base part** depends on (pet, rank) only. Pets with identical
  ``base_mods`` share the same base-part vector for every rank.
- **color part** depends on (pet, level) only. Per-stat flooring of the
  PRODUCT (``color_mod * scale(level)``, NOT of ``scale`` alone) means
  level does NOT collapse to 5 floor-bins.
- **asc part** depends on (pet, asc, song) only. The PP component
  (``2 * asc``) is universal; the color routing is per-pet because pets
  in the same archetype can have different ``Song Target`` lists. This
  is the non-obvious coupling the factored relation exposes.

The factored relation represents the legal (pet, level, rank, asc) tuples
as a JOIN of:

- ``pet ∈ archetype`` (archetype groups pets with identical
  (base_mods, color_mods) -- the base and color parts are
  archetype-level).
- ``(level, rank) ∈ archetype.legal_level_rank_pairs`` (rank caps level
  -- the same legal set for every pet in an archetype).
- ``asc ∈ 0..MINI_ASCENSION_MAX_LEVEL`` (uniform per pet).
- the contribution is then ``base_part[pet, rank] + color_part[pet,
  level] + asc_part[pet, asc, song]``.

The flat 138,601 enumeration is recovered by enumerating the JOIN:

```
for archetype in relation.archetypes:
    for pet_name in archetype.member_pets:
        for (level, rank) in archetype.legal_level_rank_pairs:
            for asc in range(0, MINI_ASCENSION_MAX_LEVEL + 1):
                yield (pet_name, level, rank, asc)
```

The empty (no-mini) option is carried as a separate boolean on the
relation (``MiniRelation.empty_option``) and participates in rank/unrank
as the tuple ``(None, None, None, None)`` at rank 0 (lexicographically
first).

This module does NOT modify ``domain_ir.py`` or any file under
``gear_optimizer/``. It is the new factored-relation surface the §16.1
parity gates bind to.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

import gear_optimizer
from gear_optimizer.core.gem_defs import ELEMENT_STAT_KEYS
from gear_optimizer.data.csv_parser import parse_mini_rows
from gear_optimizer.data.mini_ascension import (
    MINI_ASCENSION_BASE_STAT_PREFIX,
    MINI_ASCENSION_MAX_LEVEL,
    materialize_mini_for_song,
)
from gear_optimizer.data.mini_scaling import (
    PET_MIN_LEVEL,
    PetDef,
    extract_pet_info,
    pet_color_level_scale,
    pet_rank_to_max_level,
    pet_stats_delta,
)
from reverse_score_v2.domain_ir import (
    MINI_ASCENSION_LEVELS,
    PET_RANKS,
    PROJECTION_DIM,
    PROJECTION_KEYS,
)

# Re-exports for downstream reverse-engine modules. Listed in ``__all__``
# so ruff F401 does not flag them.
__all__ = [
    "MiniRelation",
    "PetArchetype",
    "MiniTuple",
    "build_mini_relation",
    "flat_enumerate_mini_tuples",
    "flat_contribution_vector",
    "factored_contribution_vector",
    "rank_mini_tuple",
    "unrank_mini_tuple",
    "PROJECTION_KEYS",
    "PROJECTION_DIM",
    "PET_RANKS",
    "MINI_ASCENSION_LEVELS",
    "MINI_ASCENSION_MAX_LEVEL",
]

# The 7-dim observable projection (mirrors ``domain_ir.PROJECTION_KEYS``):
#   (primary_color, secondary_color, Perfect Points, Combo Multiplier,
#    Fever Multiplier, Fever Time, Fever Fill Rate)
# The factored relation stores its part-vectors in this same layout.


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PetArchetype:
    """One archetype: pets with identical (base_mods, color_mods).

    The base and color contribution parts are identical for every pet in
    ``member_pet_names``; the ascension routing is per-pet because pets
    in the same archetype can have different ``Song Target`` lists (a
    non-obvious coupling this dataclass surfaces explicitly via
    ``per_pet_asc_vectors``).

    Attributes
    ----------
    archetype_id:
        Stable index into ``MiniRelation.archetypes``.
    base_mods_key:
        Sorted-tuple canonical key for the archetype's ``base_mods``.
        Identical across all members.
    color_mods_key:
        Sorted-tuple canonical key for the archetype's ``color_mods``.
        Identical across all members.
    member_pet_names:
        Pets in this archetype, in sorted name order (deterministic).
    legal_level_rank_pairs:
        ``((level, rank), ...)`` -- the legal (level, rank) pairs under
        ``pet_rank_to_max_level``. Identical for every pet in the
        archetype (the cap depends only on rank, not on the pet).
    base_part_vectors:
        ``{(pet_name, rank): ndarray[PROJECTION_DIM] int32}`` -- the base
        part ``rank * base_mods`` projected onto the 7-dim observable
        layout. Identical across members (per-archetype) but keyed per
        pet for direct JOIN access. The color axes are zero.
    color_part_vectors:
        ``{(pet_name, level): ndarray[PROJECTION_DIM] int32}`` -- the
        color part ``floor(color_mods[stat] * scale(level))`` per stat,
        projected. Identical across members; keyed per pet for direct
        JOIN access. The non-color axes are zero.
    per_pet_asc_vectors:
        ``{(pet_name, asc): ndarray[PROJECTION_DIM] int32}`` -- the
        ascension part for THIS pet at asc ``asc`` on the build song.
        Linear in ``asc`` per (pet, song, color-arity); the PP component
        is ``2 * asc`` (universal), and the color routing scales linearly
        with ``asc`` when the song is in the pet's ``Song Target`` list.
        The non-color stat axes are zero except for Perfect Points.
    song_target_active:
        ``{pet_name: bool}`` -- whether the build song is in the pet's
        ``Song Target`` list. ``False`` pets get the PP-only ascension
        bonus (no color routing) on this song.
    """

    archetype_id: int
    base_mods_key: tuple[tuple[str, int], ...]
    color_mods_key: tuple[tuple[str, int], ...]
    member_pet_names: tuple[str, ...]
    legal_level_rank_pairs: tuple[tuple[int, int], ...]
    base_part_vectors: Mapping[tuple[str, int], np.ndarray]
    color_part_vectors: Mapping[tuple[str, int], np.ndarray]
    per_pet_asc_vectors: Mapping[tuple[str, int], np.ndarray]
    song_target_active: Mapping[str, bool]


@dataclass(frozen=True, slots=True)
class MiniTuple:
    """One legal mini state.

    ``pet_name`` is ``None`` for the empty (no-mini) option; the other
    fields are then ``None`` too. ``vec`` is the 7-dim int32
    contribution vector (zero for the empty option).
    """

    pet_name: str | None
    level: int | None
    rank: int | None
    asc: int | None
    vec: np.ndarray  # shape (PROJECTION_DIM,), dtype int32


@dataclass(frozen=True, slots=True)
class MiniRelation:
    """The factored mini relation.

    ``archetypes`` is one entry per distinct (base_mods, color_mods)
    pair across the pet table. ``empty_option`` is the no-mini slot
    state. ``song_name`` / ``song_colors`` fix the ascension-routing
    context the per-pet asc vectors were materialized against; a per-
    query build reconstructs the relation for the query song.

    The legal (pet, level, rank, asc) tuples are the JOIN:

    ```
    for arch in archetypes:
        for pet in arch.member_pet_names:
            for (level, rank) in arch.legal_level_rank_pairs:
                for asc in range(0, MINI_ASCENSION_MAX_LEVEL + 1):
                    yield MiniTuple(pet, level, rank, asc, vec)
    ```

    The flat 138,601-tuple enumeration is ``len(archetypes' join) + 1``
    (the +1 is the empty option). The factored relation represents this
    as a factored JOIN, not a pre-materialized table.
    """

    archetypes: tuple[PetArchetype, ...]
    empty_option: MiniTuple
    song_name: str
    song_colors: tuple[str, ...]
    primary: str
    secondary: str
    # ``pet_to_archetype_id``: pet name -> archetype index. Used by
    # ``rank_mini_tuple`` / ``unrank_mini_tuple`` to locate the archetype
    # for a tuple's pet without a linear scan.
    pet_to_archetype_id: Mapping[str, int]
    # ``legal_tuple_count``: the number of legal (pet, level, rank, asc)
    # tuples EXCLUDING the empty option. Cached on the relation for O(1)
    # ``__len__`` semantics.
    legal_tuple_count: int
    # ``pet_index``: pet name -> its deterministic index in the flat
    # enumeration order (sorted archetype id, sorted pet, sorted
    # (level, rank, asc)). Used by the lexicographic rank function.
    pet_index: Mapping[str, int]
    # ``archetype_pet_offsets``: archetype id -> the flat-enumeration
    # offset of the archetype's first pet's first tuple. Used by the
    # rank/unrank function to avoid a linear scan over archetypes.
    archetype_pet_offsets: tuple[int, ...]
    # ``archetype_pet_tuple_offsets``: archetype id -> tuple of per-pet
    # tuple offsets (one per member pet). ``archetype_pet_tuple_offsets[
    # a][p]`` is the flat offset of archetype ``a``'s pet ``p``'s first
    # (level, rank, asc) tuple.
    archetype_pet_tuple_offsets: tuple[tuple[int, ...], ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mod_key(mods: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    """Sorted-tuple canonical form of a stat dict (hashable)."""
    return tuple(sorted(mods.items()))


def _project_stat_dict_to_vec(
    stats: Mapping[str, int],
    *,
    primary: str,
    secondary: str,
) -> np.ndarray:
    """Project a stat dict onto the 7-dim int32 observable layout."""
    vec = np.zeros(PROJECTION_DIM, dtype=np.int32)
    vec[0] = int(stats.get(primary, 0))
    if secondary:
        vec[1] = int(stats.get(secondary, 0))
    vec[2] = int(stats.get("Perfect Points", 0))
    vec[3] = int(stats.get("Combo Multiplier", 0))
    vec[4] = int(stats.get("Fever Multiplier", 0))
    vec[5] = int(stats.get("Fever Time", 0))
    vec[6] = int(stats.get("Fever Fill Rate", 0))
    return vec


def _build_mini_ascension_row(
    name: str,
    pet: PetDef,
    parsed_row: Mapping,
) -> dict:
    """Build the minimal mini row ``materialize_mini_for_song`` expects.

    Mirrors ``domain_ir._build_mini_ascension_row`` so the factored
    relation's ascension vectors exactly match the flat enumeration's.
    The row carries the pet's L1 base color values under both the main
    color keys and the ``Mini Ascension Base <Color>`` keys, so the
    materializer sees a consistent L1 row regardless of whether the
    parsed Minis.csv row was present.
    """
    row: dict = {
        "Name": name,
        "Song Target": list(parsed_row.get("Song Target") or ()),
        "Mini Ascension Enabled": True,
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
    }
    for color in ELEMENT_STAT_KEYS:
        base_val = int(pet.color_mods.get(color, 0))
        row[color] = base_val
        row[f"{MINI_ASCENSION_BASE_STAT_PREFIX}{color}"] = base_val
    return row


def _legal_level_rank_pairs() -> tuple[tuple[int, int], ...]:
    """The legal (level, rank) pairs under ``pet_rank_to_max_level``.

    Identical for every pet: the cap depends only on rank. Returns pairs
    in the lexicographic order the flat ``domain_ir._build_mini_axes``
    uses: outer rank, inner level (the flat enumeration iterates
    ``for rank in PET_RANKS: for level in range(1, lv_cap + 1)``). Wait --
    the flat enumeration actually iterates the OTHER order: outer pet,
    then ``for rank in PET_RANKS: for level in range(...): for asc in
    MINI_ASCENSION_LEVELS``. So per pet, the (rank, level) order is
    rank-major. We mirror that here.
    """
    pairs: list[tuple[int, int]] = []
    for rank in PET_RANKS:
        lv_cap = pet_rank_to_max_level(rank)
        for level in range(PET_MIN_LEVEL, lv_cap + 1):
            pairs.append((level, rank))
    return tuple(pairs)


def _base_part_vector(
    pet: PetDef,
    rank: int,
    *,
    primary: str,
    secondary: str,
) -> np.ndarray:
    """The base part ``rank * base_mods`` projected to the 7-dim layout.

    The color axes are zero (base_mods only carries non-color stats).
    """
    stats = {key: int(val) * int(rank) for key, val in pet.base_mods.items()}
    return _project_stat_dict_to_vec(stats, primary=primary, secondary=secondary)


def _color_part_vector(
    pet: PetDef,
    level: int,
    *,
    primary: str,
    secondary: str,
) -> np.ndarray:
    """The color part ``floor(color_mods[stat] * scale(level))`` projected.

    Per-stat flooring of the PRODUCT (``color_mod * scale(level)``), NOT
    of ``scale`` alone. The non-color axes are zero.
    """
    scale = pet_color_level_scale(level)
    stats = {
        color: int(math.floor(int(val) * scale))
        for color, val in pet.color_mods.items()
    }
    return _project_stat_dict_to_vec(stats, primary=primary, secondary=secondary)


def _asc_part_vector(
    pet: PetDef,
    asc: int,
    parsed_row: Mapping,
    *,
    song_name: str,
    primary: str,
    secondary: str,
) -> np.ndarray:
    """The ascension part for (pet, asc, song) projected to the 7-dim layout.

    Mirrors the flat ``domain_ir._build_mini_axes`` ascension block: the
    asc delta is ``(materialized - raw_row)`` over the union of
    ``Perfect Points`` and the elemental color keys, then added to the
    PetUtils delta. We return ONLY the asc delta (not base + color) so
    the factored relation can add it to the base and color parts.

    For ``asc == 0`` the materializer is a no-op and the asc part is the
    zero vector.
    """
    if asc <= 0:
        return np.zeros(PROJECTION_DIM, dtype=np.int32)
    row = _build_mini_ascension_row(pet.name, pet, parsed_row)
    row["Mini Ascension Level"] = asc
    materialized = materialize_mini_for_song(
        row,
        song_name=song_name,
        primary_color=primary,
        secondary_color=secondary,
    )
    delta: dict[str, int] = {}
    for key in ("Perfect Points", *ELEMENT_STAT_KEYS):
        gained = int(materialized.get(key, 0)) - int(row.get(key, 0))
        if gained:
            delta[key] = gained
    return _project_stat_dict_to_vec(delta, primary=primary, secondary=secondary)


# ---------------------------------------------------------------------------
# Flat enumeration (reference path)
# ---------------------------------------------------------------------------


def flat_enumerate_mini_tuples(relation: MiniRelation) -> list[MiniTuple]:
    """Enumerate every legal (pet, level, rank, asc) tuple in flat order.

    Order: archetype id (sorted by (base_mods_key, color_mods_key)),
    pet name (sorted), rank (1..4), level (1..cap), asc (0..10). The
    empty option is prepended as the first tuple (lexicographically
    first, rank 0 in the rank/unrank function).

    The returned list has length ``relation.legal_tuple_count + 1`` and
    matches the flat 138,601-tuple enumeration when the relation is
    built over all 90 pets.
    """
    out: list[MiniTuple] = [relation.empty_option]
    for arch in relation.archetypes:
        for pet_name in arch.member_pet_names:
            for (level, rank) in arch.legal_level_rank_pairs:
                for asc in MINI_ASCENSION_LEVELS:
                    vec = (
                        arch.base_part_vectors[pet_name, rank]
                        + arch.color_part_vectors[pet_name, level]
                        + arch.per_pet_asc_vectors[pet_name, asc]
                    ).astype(np.int32, copy=False)
                    out.append(
                        MiniTuple(
                            pet_name=pet_name,
                            level=level,
                            rank=rank,
                            asc=asc,
                            vec=vec,
                        )
                    )
    return out


def flat_contribution_vector(
    pet: PetDef,
    parsed_row: Mapping,
    level: int,
    rank: int,
    asc: int,
    *,
    song_name: str,
    primary: str,
    secondary: str,
) -> np.ndarray:
    """Compute the 7-dim contribution via the flat PetUtils path.

    Reference implementation: ``pet_stats_delta`` +
    ``materialize_mini_for_song`` ascension delta, projected to the 7-dim
    layout. The factored relation's contribution must match this
    bit-exactly (parity gate 2).
    """
    delta = dict(pet_stats_delta(pet.base_mods, pet.color_mods, level, rank))
    if asc > 0:
        row = _build_mini_ascension_row(pet.name, pet, parsed_row)
        row["Mini Ascension Level"] = asc
        materialized = materialize_mini_for_song(
            row,
            song_name=song_name,
            primary_color=primary,
            secondary_color=secondary,
        )
        for key in ("Perfect Points", *ELEMENT_STAT_KEYS):
            gained = int(materialized.get(key, 0)) - int(row.get(key, 0))
            if gained:
                delta[key] = delta.get(key, 0) + gained
    return _project_stat_dict_to_vec(delta, primary=primary, secondary=secondary)


def factored_contribution_vector(
    relation: MiniRelation,
    pet_name: str,
    level: int,
    rank: int,
    asc: int,
) -> np.ndarray:
    """Compute the 7-dim contribution via the factored relation.

    ``base_part[pet, rank] + color_part[pet, level] + asc_part[pet, asc]``.
    The result must match ``flat_contribution_vector`` bit-exactly
    (parity gate 2).
    """
    arch_id = relation.pet_to_archetype_id[pet_name]
    arch = relation.archetypes[arch_id]
    return (
        arch.base_part_vectors[pet_name, rank]
        + arch.color_part_vectors[pet_name, level]
        + arch.per_pet_asc_vectors[pet_name, asc]
    ).astype(np.int32, copy=False)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_mini_relation(
    webport_root: Path,
    *,
    minis_csv: Path | None = None,
    song_name: str = "__domain_ir_seed__",
    song_colors: tuple[str, ...] = ("Chill",),
) -> MiniRelation:
    """Build the factored mini relation from the production tables.

    ``webport_root`` is the decompiled ``ReplicatedStorage`` parent;
    PetInfo is read from ``<root>/Pets/PetInfo``. ``minis_csv`` defaults
    to ``Data/Gear/Minis.csv`` resolved relative to the repo root.

    The relation is per-(data-table, song, color-arity): the ascension
    vectors depend on the build song's ``Song Target`` membership and on
    the color arity. The base and color parts are song-independent.
    """
    if len(song_colors) == 0 or len(song_colors) > 2:
        raise ValueError(f"song_colors must have length 1 or 2, got {song_colors!r}")
    primary = song_colors[0]
    secondary = song_colors[1] if len(song_colors) == 2 else ""

    # --- Load production tables ------------------------------------------
    pets = extract_pet_info(webport_root)
    if minis_csv is None:
        repo_root = Path(gear_optimizer.__file__).resolve().parent.parent
        minis_csv = repo_root / "Data" / "Gear" / "Minis.csv"
    minis_csv = Path(minis_csv)
    if not minis_csv.is_file():
        raise FileNotFoundError(f"Minis.csv not found: {minis_csv}")
    mini_rows = list(parse_mini_rows(str(minis_csv)))
    mini_rows_by_name: dict[str, dict] = {
        str(r.get("Name", "")): r for r in mini_rows
    }

    # --- Group pets into archetypes --------------------------------------
    archetype_map: dict[
        tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]],
        list[str],
    ] = {}
    for name, pet in pets.items():
        key = (_mod_key(pet.base_mods), _mod_key(pet.color_mods))
        archetype_map.setdefault(key, []).append(name)
    # Deterministic archetype order: sorted by (base_mods_key, color_mods_key).
    sorted_keys = sorted(archetype_map.keys())

    legal_pairs = _legal_level_rank_pairs()

    archetypes: list[PetArchetype] = []
    pet_to_archetype_id: dict[str, int] = {}
    pet_index: dict[str, int] = {}
    archetype_pet_offsets: list[int] = []
    archetype_pet_tuple_offsets: list[tuple[int, ...]] = []

    # Per-pet tuple count (legal (level, rank) × asc levels).
    per_pet_tuple_count = len(legal_pairs) * len(MINI_ASCENSION_LEVELS)
    # The empty option occupies flat-rank 0; pets start at flat-rank 1.
    flat_offset = 1

    for arch_id, arch_key in enumerate(sorted_keys):
        member_pet_names = tuple(sorted(archetype_map[arch_key]))
        base_mods_key, color_mods_key = arch_key

        # Base part vectors: identical for all members (per-archetype),
        # but keyed per pet for direct JOIN access.
        base_part_vectors: dict[tuple[str, int], np.ndarray] = {}
        color_part_vectors: dict[tuple[str, int], np.ndarray] = {}
        per_pet_asc_vectors: dict[tuple[str, int], np.ndarray] = {}
        song_target_active: dict[str, bool] = {}

        archetype_pet_offsets.append(flat_offset)
        per_arch_pet_offsets: list[int] = []

        for pet_idx, pet_name in enumerate(member_pet_names):
            pet = pets[pet_name]
            pet_to_archetype_id[pet_name] = arch_id
            pet_index[pet_name] = len(pet_index)
            per_arch_pet_offsets.append(flat_offset)
            flat_offset += per_pet_tuple_count

            parsed_row = mini_rows_by_name.get(pet_name, {})

            # Base part for every rank.
            for rank in PET_RANKS:
                base_part_vectors[pet_name, rank] = _base_part_vector(
                    pet, rank, primary=primary, secondary=secondary
                )
            # Color part for every legal level.
            for (level, _rank) in legal_pairs:
                color_part_vectors[pet_name, level] = _color_part_vector(
                    pet, level, primary=primary, secondary=secondary
                )
            # Asc part for every asc level.
            for asc in MINI_ASCENSION_LEVELS:
                per_pet_asc_vectors[pet_name, asc] = _asc_part_vector(
                    pet,
                    asc,
                    parsed_row,
                    song_name=song_name,
                    primary=primary,
                    secondary=secondary,
                )
            # Song Target active flag.
            target = parsed_row.get("Song Target")
            active = False
            if target:
                if isinstance(target, str):
                    active = target.strip() == song_name.strip()
                else:
                    active = any(
                        str(t or "").strip() == song_name.strip() for t in target
                    )
            song_target_active[pet_name] = active

        archetype_pet_tuple_offsets.append(tuple(per_arch_pet_offsets))

        archetypes.append(
            PetArchetype(
                archetype_id=arch_id,
                base_mods_key=base_mods_key,
                color_mods_key=color_mods_key,
                member_pet_names=member_pet_names,
                legal_level_rank_pairs=legal_pairs,
                base_part_vectors=base_part_vectors,
                color_part_vectors=color_part_vectors,
                per_pet_asc_vectors=per_pet_asc_vectors,
                song_target_active=song_target_active,
            )
        )

    legal_tuple_count = len(pets) * per_pet_tuple_count
    empty_vec = np.zeros(PROJECTION_DIM, dtype=np.int32)
    empty_option = MiniTuple(
        pet_name=None,
        level=None,
        rank=None,
        asc=None,
        vec=empty_vec,
    )

    return MiniRelation(
        archetypes=tuple(archetypes),
        empty_option=empty_option,
        song_name=song_name,
        song_colors=tuple(song_colors),
        primary=primary,
        secondary=secondary,
        pet_to_archetype_id=pet_to_archetype_id,
        legal_tuple_count=legal_tuple_count,
        pet_index=pet_index,
        archetype_pet_offsets=tuple(archetype_pet_offsets),
        archetype_pet_tuple_offsets=tuple(archetype_pet_tuple_offsets),
    )


# ---------------------------------------------------------------------------
# Rank / unrank (deterministic lexicographic ordering)
# ---------------------------------------------------------------------------


def rank_mini_tuple(
    relation: MiniRelation,
    pet_name: str | None,
    level: int | None,
    rank: int | None,
    asc: int | None,
) -> int:
    """Deterministic lexicographic rank of a legal (pet, level, rank, asc) tuple.

    Rank 0 is the empty option. Ranks 1..legal_tuple_count enumerate the
    non-empty tuples in the order: archetype id (sorted by
    (base_mods_key, color_mods_key)), pet name (sorted), rank (1..4),
    level (1..cap), asc (0..10).

    The order is fixed by the relation's construction and is identical to
    ``flat_enumerate_mini_tuples``'s order.
    """
    if pet_name is None:
        # Empty option is rank 0.
        if level is not None or rank is not None or asc is not None:
            raise ValueError(
                f"empty mini tuple must have all-None fields, got "
                f"({pet_name!r}, {level!r}, {rank!r}, {asc!r})"
            )
        return 0
    if pet_name not in relation.pet_to_archetype_id:
        raise KeyError(f"pet {pet_name!r} not in relation")
    arch_id = relation.pet_to_archetype_id[pet_name]
    arch = relation.archetypes[arch_id]
    # Pet offset within the archetype.
    pet_local = arch.member_pet_names.index(pet_name)
    pet_start = relation.archetype_pet_tuple_offsets[arch_id][pet_local]
    # (rank, level, asc) offset within the pet's tuples. The flat
    # enumeration is outer rank, inner level, innermost asc, so:
    #   off = (rank_index * len(legal_levels_for_rank) + level_index) * n_asc + asc
    # where legal_levels_for_rank = levels 1..pet_rank_to_max_level(rank).
    # legal_level_rank_pairs is rank-major: for each rank in PET_RANKS,
    # the pairs (level, rank) for level in 1..cap. So per rank there are
    # ``cap`` pairs, and the (level, rank) pair index within the pet's
    # tuple list is:
    #   pair_index = sum(cap_of_rank_r for r < rank) + (level - 1)
    # The asc offset is just ``asc`` (asc ranges 0..MINI_ASCENSION_MAX_LEVEL).
    rank_idx = PET_RANKS.index(int(rank))
    pair_index = sum(
        pet_rank_to_max_level(PET_RANKS[r]) for r in range(rank_idx)
    ) + (int(level) - 1)
    asc_off = int(asc)
    n_asc = len(MINI_ASCENSION_LEVELS)
    return pet_start + pair_index * n_asc + asc_off


def unrank_mini_tuple(
    relation: MiniRelation,
    rank: int,
) -> MiniTuple:
    """Inverse of ``rank_mini_tuple``: rank -> MiniTuple.

    Returns the empty option for rank 0. Raises for out-of-range ranks.
    """
    if rank < 0 or rank > relation.legal_tuple_count:
        raise IndexError(
            f"mini tuple rank out of range: {rank} (legal 0..{relation.legal_tuple_count})"
        )
    if rank == 0:
        return relation.empty_option
    # Locate the archetype whose pet offset range contains ``rank``.
    # ``archetype_pet_offsets[a]`` is the flat offset of archetype ``a``'s
    # first pet's first tuple; the archetype's last tuple is
    # ``archetype_pet_offsets[a+1] - 1`` or ``legal_tuple_count`` for the
    # last archetype. Binary-search the archetype.
    offsets = relation.archetype_pet_offsets
    n_archetypes = len(offsets)
    lo, hi = 0, n_archetypes
    while lo < hi:
        mid = (lo + hi) // 2
        if offsets[mid] <= rank:
            lo = mid + 1
        else:
            hi = mid
    arch_id = lo - 1
    arch = relation.archetypes[arch_id]
    pet_offsets = relation.archetype_pet_tuple_offsets[arch_id]
    # Find the pet within the archetype whose offset range contains ``rank``.
    pet_local_lo, pet_local_hi = 0, len(pet_offsets)
    while pet_local_lo < pet_local_hi:
        mid = (pet_local_lo + pet_local_hi) // 2
        if pet_offsets[mid] <= rank:
            pet_local_lo = mid + 1
        else:
            pet_local_hi = mid
    pet_local = pet_local_lo - 1
    pet_name = arch.member_pet_names[pet_local]
    pet_start = pet_offsets[pet_local]
    local = rank - pet_start
    n_asc = len(MINI_ASCENSION_LEVELS)
    pair_index, asc_off = divmod(local, n_asc)
    # Recover (level, rank) from pair_index. legal_level_rank_pairs is
    # rank-major: for each rank, cap = pet_rank_to_max_level(rank).
    rank_idx = 0
    remaining = pair_index
    while rank_idx < len(PET_RANKS):
        cap = pet_rank_to_max_level(PET_RANKS[rank_idx])
        if remaining < cap:
            break
        remaining -= cap
        rank_idx += 1
    if rank_idx >= len(PET_RANKS):
        raise IndexError(f"rank {rank} decodes to invalid pair_index {pair_index}")
    rank_val = PET_RANKS[rank_idx]
    level_val = remaining + 1
    asc_val = asc_off
    vec = factored_contribution_vector(
        relation, pet_name, level_val, rank_val, asc_val
    )
    return MiniTuple(
        pet_name=pet_name,
        level=level_val,
        rank=rank_val,
        asc=asc_val,
        vec=vec,
    )


# ---------------------------------------------------------------------------
# Cross-slot legality
# ---------------------------------------------------------------------------


def cross_slot_unique_pets(selection: Iterable[MiniTuple]) -> bool:
    """Return True iff no pet appears in two mini slots.

    The game's ≤3 equipped distinct-pet law forbids the same pet name in
    two slots. The empty option (``pet_name is None``) is exempt (the
    "no mini" state can repeat freely). This is the §16.1 cross-slot
    legality invariant.
    """
    seen: set[str] = set()
    for t in selection:
        if t.pet_name is None:
            continue
        if t.pet_name in seen:
            return False
        seen.add(t.pet_name)
    return True
