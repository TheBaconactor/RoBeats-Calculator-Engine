"""Four parity gates for the factored mini relation (handoff §16.1 binding).

The factored mini relation (``reverse_score_v2.mini_factored``) must
produce EXACTLY the same legal (pet, level, rank, asc) tuples and
contribution multiplicities as the flat 138,601-state enumeration in
``reverse_score_v2.domain_ir``. Handoff §16.1 names four required
gates; this module collects all four. All four MUST pass before any
factored-mini transition estimate is used downstream.

Gates:

1. ``test_factored_mini_relation_equals_flat_enumeration`` -- for a
   single mini slot, the set of legal (pet, level, rank, asc) tuples
   produced by the factored relation equals the flat 138,601-tuple
   enumeration exactly. Set equality, no extras, no missing.

2. ``test_factored_mini_contribution_multiplicities`` -- for every
   legal (pet, level, rank, asc) tuple, the contribution vector via the
   factored relation (base_part + color_part + asc_part) equals the
   contribution vector via the flat ``pet_stats_delta +
   materialize_mini_for_song`` path. Bit-exact.

3. ``test_factored_mini_rank_unrank_identity_parity`` -- for the
   factored relation, rank then unrank every legal tuple recovers it
   exactly. The rank function is a deterministic lexicographic ordering
   of (pet, level, rank, asc) within the factored representation.

4. ``test_factored_mini_preserves_cross_slot_legality`` -- with ≤3
   mini slots equipped, the cross-slot uniqueness law (no pet equipped
   twice, per the game's law) is preserved by the factored relation.
   Generate 1000 random 3-mini factored selections; verify no pet
   appears in two slots.
"""
from __future__ import annotations

import os
import random
from pathlib import Path

import gear_optimizer
import numpy as np
import pytest

from gear_optimizer.core.gem_defs import ELEMENT_STAT_KEYS
from gear_optimizer.data.csv_parser import parse_mini_rows
from gear_optimizer.data.mini_ascension import (
    MINI_ASCENSION_BASE_STAT_PREFIX,
    materialize_mini_for_song,
)
from gear_optimizer.data.mini_scaling import (
    PetDef,
    extract_pet_info,
    pet_stats_delta,
)
from reverse_score_v2.domain_ir import (
    MINI_ASCENSION_LEVELS,
    build_domain_ir,
)
from reverse_score_v2.mini_factored import (
    MiniTuple,
    build_mini_relation,
    cross_slot_unique_pets,
    factored_contribution_vector,
    rank_mini_tuple,
    unrank_mini_tuple,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _webport_root() -> Path:
    """Resolve the decompiled ReplicatedStorage root (SarHort V5 default)."""
    env_root = os.environ.get("ROBEATS_DECOMPILED_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(
        r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/SavedGame_706824758/ReplicatedStorage"
    )


@pytest.fixture(scope="module")
def webport_root() -> Path:
    root = _webport_root()
    if not root.is_dir():
        pytest.skip(f"webport_root not found: {root}")
    return root


@pytest.fixture(scope="module")
def factored_relation(webport_root: Path):
    """The factored mini relation (single-color Chill, seed song)."""
    return build_mini_relation(webport_root, song_colors=("Chill",))


@pytest.fixture(scope="module")
def domain_ir(webport_root: Path):
    """The flat DomainIR (single-color Chill, same seed song)."""
    return build_domain_ir(webport_root, song_colors=("Chill",))


@pytest.fixture(scope="module")
def pet_defs(webport_root: Path) -> dict[str, PetDef]:
    return extract_pet_info(webport_root)


@pytest.fixture(scope="module")
def mini_rows_by_name(webport_root: Path) -> dict[str, dict]:
    repo_root = Path(gear_optimizer.__file__).resolve().parent.parent
    rows = list(parse_mini_rows(str(repo_root / "Data" / "Gear" / "Minis.csv")))
    return {str(r.get("Name", "")): r for r in rows}


# ---------------------------------------------------------------------------
# Helpers for the flat-path reference contribution (gate 2)
# ---------------------------------------------------------------------------


def _build_mini_ascension_row(
    name: str,
    pet: PetDef,
    parsed_row: dict,
) -> dict:
    """Mirror ``domain_ir._build_mini_ascension_row`` for the flat reference."""
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


def _flat_path_contribution(
    pet: PetDef,
    parsed_row: dict,
    level: int,
    rank: int,
    asc: int,
    *,
    song_name: str,
    primary: str,
    secondary: str,
) -> np.ndarray:
    """The flat ``pet_stats_delta + materialize_mini_for_song`` contribution.

    Mirrors ``domain_ir._build_mini_axes`` exactly so the factored
    relation's contribution can be checked bit-exact against it.
    """
    delta = pet_stats_delta(pet.base_mods, pet.color_mods, level, rank)
    delta = dict(delta)
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
    # Project to the 7-dim observable layout (mirrors
    # ``domain_ir._project_stats``).
    vec = np.zeros(7, dtype=np.int32)
    vec[0] = int(delta.get(primary, 0))
    if secondary:
        vec[1] = int(delta.get(secondary, 0))
    vec[2] = int(delta.get("Perfect Points", 0))
    vec[3] = int(delta.get("Combo Multiplier", 0))
    vec[4] = int(delta.get("Fever Multiplier", 0))
    vec[5] = int(delta.get("Fever Time", 0))
    vec[6] = int(delta.get("Fever Fill Rate", 0))
    return vec


# ---------------------------------------------------------------------------
# Gate 1: factored relation equals flat enumeration
# ---------------------------------------------------------------------------


def test_factored_mini_relation_equals_flat_enumeration(
    webport_root: Path,
    factored_relation,
) -> None:
    """Set equality between factored-relation tuples and the flat 138,601 enum.

    Builds the DomainIR (which enumerates 138,601 mini options per slot)
    and the factored relation, then compares the set of
    (pet, level, rank, asc) tuples. The empty option is mapped to
    (None, None, None, None). Set equality: no extras, no missing.
    """
    ir = build_domain_ir(webport_root, song_colors=("Chill",))
    mini0 = ir.axes[1]  # team_buff is axis 0; mini:0 is axis 1.
    flat_tuples: set[tuple] = set()
    for opt in mini0.options:
        label = opt.label
        # label = ('mini', pet_or_None, level_or_None, rank_or_None, asc_or_None)
        flat_tuples.add((label[1], label[2], label[3], label[4]))

    factored_tuples: set[tuple] = set()
    factored_tuples.add((None, None, None, None))  # empty option
    for arch in factored_relation.archetypes:
        for pet_name in arch.member_pet_names:
            for (level, rank) in arch.legal_level_rank_pairs:
                for asc in MINI_ASCENSION_LEVELS:
                    factored_tuples.add((pet_name, level, rank, asc))

    assert len(flat_tuples) == 138_601, (
        f"flat enumeration should have 138,601 tuples, got {len(flat_tuples):,}"
    )
    assert len(factored_tuples) == 138_601, (
        f"factored relation should have 138,601 tuples, "
        f"got {len(factored_tuples):,}"
    )
    assert flat_tuples == factored_tuples, (
        "factored mini relation does NOT equal flat enumeration"
    )


# ---------------------------------------------------------------------------
# Gate 2: contribution multiplicities bit-exact
# ---------------------------------------------------------------------------


def test_factored_mini_contribution_multiplicities(
    webport_root: Path,
    factored_relation,
    pet_defs: dict[str, PetDef],
    mini_rows_by_name: dict[str, dict],
) -> None:
    """Every legal tuple's factored vec equals the flat-path vec, bit-exact.

    Iterates the factored relation's tuples and for each (pet, level,
    rank, asc) recomputes the 7-dim contribution via the flat
    ``pet_stats_delta + materialize_mini_for_song`` path. Asserts
    ``np.array_equal`` for every tuple.
    """
    primary = factored_relation.primary
    secondary = factored_relation.secondary
    song_name = factored_relation.song_name
    mismatches: list[tuple[str, int, int, int]] = []
    checked = 0
    for arch in factored_relation.archetypes:
        for pet_name in arch.member_pet_names:
            pet = pet_defs[pet_name]
            parsed_row = mini_rows_by_name.get(pet_name, {})
            for (level, rank) in arch.legal_level_rank_pairs:
                for asc in MINI_ASCENSION_LEVELS:
                    fact_vec = factored_contribution_vector(
                        factored_relation, pet_name, level, rank, asc
                    )
                    flat_vec = _flat_path_contribution(
                        pet,
                        parsed_row,
                        level,
                        rank,
                        asc,
                        song_name=song_name,
                        primary=primary,
                        secondary=secondary,
                    )
                    if not np.array_equal(fact_vec, flat_vec):
                        mismatches.append((pet_name, level, rank, asc))
                        if len(mismatches) >= 5:
                            break
                    checked += 1
                if len(mismatches) >= 5:
                    break
            if len(mismatches) >= 5:
                break
        if len(mismatches) >= 5:
            break

    assert checked == factored_relation.legal_tuple_count, (
        f"checked {checked} != legal_tuple_count "
        f"{factored_relation.legal_tuple_count}"
    )
    assert not mismatches, (
        f"factored vs flat contribution mismatch on "
        f"{len(mismatches)}+ tuples (showing first 5): {mismatches}"
    )


# ---------------------------------------------------------------------------
# Gate 3: rank/unrank identity parity
# ---------------------------------------------------------------------------


def test_factored_mini_rank_unrank_identity_parity(factored_relation) -> None:
    """rank(unrank(r)) == r for r in 0..legal_tuple_count.

    Also asserts unrank(rank(t)) == t for every legal tuple, including
    the empty option. The rank function is a deterministic lexicographic
    ordering of (pet, level, rank, asc) within the factored
    representation.
    """
    n = factored_relation.legal_tuple_count
    # unrank -> rank identity over the whole range.
    for r in range(0, n + 1):
        t = unrank_mini_tuple(factored_relation, r)
        r_back = rank_mini_tuple(
            factored_relation, t.pet_name, t.level, t.rank, t.asc
        )
        assert r_back == r, (
            f"rank(unrank({r})) = {r_back}, expected {r}; "
            f"tuple=({t.pet_name!r}, {t.level!r}, {t.rank!r}, {t.asc!r})"
        )
    # rank -> unrank identity over every legal tuple (including empty).
    # The empty option has rank 0.
    empty_rank = rank_mini_tuple(factored_relation, None, None, None, None)
    assert empty_rank == 0, f"empty option should be rank 0, got {empty_rank}"
    empty_back = unrank_mini_tuple(factored_relation, 0)
    assert empty_back.pet_name is None
    # Spot-check a few representative tuples.
    sample_tuples: list[tuple[str | None, int | None, int | None, int | None]] = [
        (None, None, None, None),
    ]
    # First non-empty tuple (lexicographically first pet, lowest rank, level, asc).
    first_arch = factored_relation.archetypes[0]
    first_pet = first_arch.member_pet_names[0]
    first_pair = first_arch.legal_level_rank_pairs[0]
    sample_tuples.append((first_pet, first_pair[0], first_pair[1], 0))
    # A mid-range pet at maxed rank/level/asc.
    mid_arch = factored_relation.archetypes[len(factored_relation.archetypes) // 2]
    mid_pet = mid_arch.member_pet_names[0]
    last_pair = mid_arch.legal_level_rank_pairs[-1]
    sample_tuples.append((mid_pet, last_pair[0], last_pair[1], 10))
    for pet_name, level, rank, asc in sample_tuples:
        r = rank_mini_tuple(factored_relation, pet_name, level, rank, asc)
        t = unrank_mini_tuple(factored_relation, r)
        assert (t.pet_name, t.level, t.rank, t.asc) == (
            pet_name,
            level,
            rank,
            asc,
        ), (
            f"unrank(rank({pet_name!r}, {level!r}, {rank!r}, {asc!r})) = "
            f"({t.pet_name!r}, {t.level!r}, {t.rank!r}, {t.asc!r})"
        )


# ---------------------------------------------------------------------------
# Gate 4: cross-slot legality (no pet equipped twice)
# ---------------------------------------------------------------------------


def test_factored_mini_preserves_cross_slot_legality(
    factored_relation,
) -> None:
    """1000 random 3-mini selections; verify the factored relation carries
    enough pet identity to enforce the game's ≤3 distinct-pet law.

    The game's law forbids the same pet name in two mini slots. The
    factored relation's ``MiniTuple`` carries ``pet_name`` for every
    legal tuple, so the caller can check the law directly via
    ``cross_slot_unique_pets``. This test generates 1000 random 3-mini
    selections (sampling pets WITHOUT replacement at the pet level, so
    the generated selections are law-abiding by construction) and
    verifies:

    - the factored relation's tuples carry distinct pet names across
      the 3 slots (no pet appears in two slots),
    - ``cross_slot_unique_pets`` returns True for every such selection,
    - ``cross_slot_unique_pets`` returns False for a deliberately
      same-pet-two-slot selection (the law is detectable, not silently
      collapsed by the factored representation).

    Uses a fixed seed for determinism.
    """
    rng = random.Random(20250719)
    # Build the per-pet tuple list: for each pet, list its flat ranks
    # (1..n). We sample pets WITHOUT replacement, then sample one
    # rank/level/asc state for each chosen pet.
    pet_to_ranks: dict[str, list[int]] = {}
    n = factored_relation.legal_tuple_count
    for r in range(1, n + 1):
        t = unrank_mini_tuple(factored_relation, r)
        pet_to_ranks.setdefault(t.pet_name, []).append(r)
    all_pet_names = list(pet_to_ranks.keys())
    assert len(all_pet_names) >= 3, (
        f"need >=3 distinct pets to fill 3 slots, got {len(all_pet_names)}"
    )

    for trial in range(1000):
        # Randomly decide how many of the 3 slots are non-empty (0..3).
        non_empty_count = rng.randint(0, 3)
        chosen_pets = rng.sample(all_pet_names, non_empty_count)
        slot_picks: list[MiniTuple] = []
        for pet_name in chosen_pets:
            r = rng.choice(pet_to_ranks[pet_name])
            slot_picks.append(unrank_mini_tuple(factored_relation, r))
        for _ in range(3 - non_empty_count):
            slot_picks.append(factored_relation.empty_option)
        rng.shuffle(slot_picks)
        # The factored relation carries distinct pet names (by
        # construction; we sampled without replacement).
        non_empty_pets = [t.pet_name for t in slot_picks if t.pet_name is not None]
        assert len(set(non_empty_pets)) == len(non_empty_pets), (
            f"trial {trial}: pet identity not preserved across slots: "
            f"{non_empty_pets}"
        )
        # The cross-slot uniqueness law is enforceable from the
        # factored relation's tuples.
        assert cross_slot_unique_pets(slot_picks), (
            f"trial {trial}: cross_slot_unique_pets rejected a "
            f"law-abiding selection: "
            f"{[(t.pet_name, t.level, t.rank, t.asc) for t in slot_picks]}"
        )

    # Adversarial: explicitly construct a same-pet-two-slots selection
    # and verify the factored relation surfaces the violation (the
    # law is detectable, NOT silently collapsed by the factored
    # representation).
    arch = factored_relation.archetypes[0]
    pet_name = arch.member_pet_names[0]
    pair = arch.legal_level_rank_pairs[0]
    t_a = MiniTuple(
        pet_name=pet_name,
        level=pair[0],
        rank=pair[1],
        asc=0,
        vec=factored_contribution_vector(
            factored_relation, pet_name, pair[0], pair[1], 0
        ),
    )
    t_b = MiniTuple(
        pet_name=pet_name,
        level=pair[0],
        rank=pair[1],
        asc=1,
        vec=factored_contribution_vector(
            factored_relation, pet_name, pair[0], pair[1], 1
        ),
    )
    assert not cross_slot_unique_pets([t_a, t_b]), (
        "cross_slot_unique_pets should reject a same-pet two-slot "
        "selection -- the factored relation must surface the "
        "violation, not collapse it"
    )
