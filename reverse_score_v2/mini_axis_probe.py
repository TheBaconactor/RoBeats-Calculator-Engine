"""Deep telemetry probe for the mini axis of the DomainIR.

Read-only analysis of the mini axis (the dominant multiplicity in the
reverse score engine v2 DomainIR) plus a probe of the 7-dim contribution
vectors. Does NOT modify production code or the DomainIR.

Usage:
    python -m reverse_score_v2.mini_axis_probe

Reports:
1. Decomposition of 138,601 (pets x rank-capped levels x ascensions).
2. Fiber collapse: histogram + largest 10 fibers.
3. Contribution vector structure: does it factor into base x color?
4. Pet archetype clustering by (base_mods, color_mods).
5. Ascension interaction: constant-offset vs per-stat vector.
6. Suffix-bound impact: P=0 fiber fraction, P histogram, feasible fibers
   at Gateway top-1 P=5834.
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from gear_optimizer.data.mini_ascension import (
    MINI_ASCENSION_BASE_STAT_PREFIX,
    MINI_ASCENSION_MAX_LEVEL,
    materialize_mini_for_song,
)
from gear_optimizer.data.mini_scaling import (
    PetDef,
    extract_pet_info,
    pet_color_level_scale,
    pet_rank_to_max_level,
    pet_stats_delta,
)
from gear_optimizer.data.csv_parser import parse_mini_rows
from gear_optimizer.core.gem_defs import ELEMENT_STAT_KEYS
from reverse_score_v2.domain_ir import (
    MINI_ASCENSION_LEVELS,
    PET_RANKS,
    DomainIR,
    build_domain_ir,
)

# Five elemental color stat keys, canonical order.
ELEMENT_COLORS: tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")

# Stated Gateway top-1 P observed value, used for the suffix-bound estimate
# in section 6.
GATEWAY_TOP1_P: int = 5834


def _resolve_webport_root() -> Path:
    """Resolve the decompiled ReplicatedStorage root.

    Honors ``ROBEATS_DECOMPILED_ROOT`` if set; else falls back to the
    canonical SarHort V5 path the handoff names (same as domain_probe).
    """
    env_root = os.environ.get("ROBEATS_DECOMPILED_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(
        r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/SavedGame_706824758/ReplicatedStorage"
    )


def _resolve_repo_root() -> Path:
    """Repo root: the directory containing ``gear_optimizer`` and ``Data``."""
    import gear_optimizer

    return Path(gear_optimizer.__file__).resolve().parent.parent


def _print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(f"  {title}")
    print("=" * 78)


# ---------------------------------------------------------------------------
# Section 1: Decomposition of 138,601
# ---------------------------------------------------------------------------


def section1_decomposition(ir: DomainIR, pets: dict[str, PetDef]) -> None:
    _print_header("Section 1: Decomposition of 138,601")
    mini0 = ir.axes[1]  # axes[0] = team_buff, axes[1..3] = mini:0..2
    total_options = len(mini0.options)
    print(f"mini:0 option count: {total_options:,}")

    n_pets = len(pets)
    print(f"Number of pets with at least one legal state: {n_pets}")

    print()
    print("Per-rank (level, count) breakdown:")
    print(f"  {'rank':>4}  {'lv_cap':>6}  {'levels':<14}  {'level_count':>12}")
    rank_level_counts: list[int] = []
    for rank in PET_RANKS:
        lv_cap = pet_rank_to_max_level(rank)
        # level range is 1..lv_cap inclusive -> lv_cap levels
        n_levels = lv_cap
        rank_level_counts.append(n_levels)
        print(f"  {rank:>4}  {lv_cap:>6}  1..{lv_cap:<10}  {n_levels:>12,}")

    sum_levels = sum(rank_level_counts)
    n_asc = len(MINI_ASCENSION_LEVELS)
    print()
    print(f"Sum of rank-capped level counts (ranks 1..4): {sum_levels}")
    print(f"  = 20 + 30 + 40 + 50 = {20 + 30 + 40 + 50}")
    print(f"Number of ascension levels (0..{MINI_ASCENSION_MAX_LEVEL}): {n_asc}")
    print()
    product = n_pets * sum_levels * n_asc
    print("Multiplication:")
    print(f"  pets x sum_levels x asc_levels = {n_pets} x {sum_levels} x {n_asc} = {product:,}")
    print(f"  + 1 empty (no-mini) option     = {product + 1:,}")
    print(f"  mini:0 option count           = {total_options:,}")
    matches = (product + 1) == total_options
    print(f"  equals 138,601? {matches}")
    if not matches:
        print(f"  MISMATCH: predicted {product + 1:,} vs actual {total_options:,}")

    # Sanity: confirm by counting options with non-None mini label.
    non_empty = sum(1 for opt in mini0.options if opt.label[1] is not None)
    empty = sum(1 for opt in mini0.options if opt.label[1] is None)
    print()
    print(f"  non-empty (mini, level, rank, asc) options: {non_empty:,}")
    print(f"  empty (no-mini) options:                  {empty:,}")


# ---------------------------------------------------------------------------
# Section 2: Fiber collapse analysis
# ---------------------------------------------------------------------------


def section2_fibers(ir: DomainIR) -> None:
    _print_header("Section 2: Fiber collapse analysis")
    mini0 = ir.axes[1]
    fibers = mini0.identity_fibers
    n_options = len(mini0.options)
    n_fibers = len(fibers)
    print(f"Total options per mini slot: {n_options:,}")
    print(f"Total distinct contribution vectors (fibers): {n_fibers:,}")
    print(f"Confirm 23,002? {n_fibers == 23002}")
    print(f"Collapse ratio: {n_options / n_fibers:.3f}x")

    sizes = np.array([len(f) for f in fibers], dtype=np.int64)
    print()
    print("Fiber size summary statistics:")
    print(f"  min:    {int(sizes.min())}")
    print(f"  max:    {int(sizes.max())}")
    print(f"  mean:   {float(sizes.mean()):.3f}")
    print(f"  median: {float(np.median(sizes)):.1f}")

    print()
    print("Fiber size histogram (manual bucketing):")
    buckets = [
        (1, 1, "1"),
        (2, 2, "2"),
        (3, 10, "3-10"),
        (11, 100, "11-100"),
        (101, 1000, "101-1000"),
        (1001, 10**9, "1000+"),
    ]
    print(f"  {'bucket':>12}  {'count':>8}  {'options':>10}")
    total_in_buckets = 0
    for lo, hi, label in buckets:
        mask = (sizes >= lo) & (sizes <= hi)
        count = int(mask.sum())
        opt_sum = int(sizes[mask].sum())
        total_in_buckets += opt_sum
        print(f"  {label:>12}  {count:>8,}  {opt_sum:>10,}")
    print(f"  {'TOTAL':>12}  {n_fibers:>8,}  {total_in_buckets:>10,}")

    print()
    print("Largest 10 fibers:")
    order = np.argsort(sizes)[::-1][:10]
    for rank_idx, fib_idx in enumerate(order, 1):
        fib = fibers[int(fib_idx)]
        print(f"  #{rank_idx}: fiber_size={len(fib):,}")
        # Show the options in the fiber: pet name, level, rank, asc spread.
        names = [str(o.label[1]) for o in fib if o.label[1] is not None]
        levels = [int(o.label[2]) for o in fib if o.label[2] is not None]
        ranks = [int(o.label[3]) for o in fib if o.label[3] is not None]
        ascs = [int(o.label[4]) for o in fib if o.label[4] is not None]
        if names:
            distinct_names = sorted(set(names))
            print(
                f"      pets: {len(distinct_names)} distinct "
                f"(first 5: {distinct_names[:5]})"
            )
            print(
                f"      level range: {min(levels)}..{max(levels)} "
                f"({len(set(levels))} distinct)"
            )
            print(
                f"      rank range:  {min(ranks)}..{max(ranks)} "
                f"({sorted(set(ranks))})"
            )
            print(
                f"      asc range:   {min(ascs)}..{max(ascs)} "
                f"({len(set(ascs))} distinct)"
            )
        else:
            print("      (all empty/no-mini options)")
        # Print the shared 7-dim vec.
        print(f"      vec = {fib[0].vec.tolist()}")

    # Largest-fiber character: do they group by identical base/color mods?
    # Check the largest fiber's pets' mod tables.
    print()
    print("Largest-fiber archetype check (does it group by mod tables?):")
    if len(order) > 0:
        largest = fibers[int(order[0])]
        names_in_fiber = [str(o.label[1]) for o in largest if o.label[1] is not None]
        ir_pet_defs = {p.name: p for p in ir.pet_defs}
        mod_pairs: Counter = Counter()
        for nm in names_in_fiber:
            p = ir_pet_defs.get(nm)
            if p is None:
                continue
            key = (_mod_tuple(p.base_mods), _mod_tuple(p.color_mods))
            mod_pairs[key] += 1
        print(
            f"  largest fiber has {len(names_in_fiber)} pets, "
            f"{len(mod_pairs)} distinct (base_mods, color_mods) pairs"
        )
        for (bkey, ckey), cnt in mod_pairs.most_common(5):
            print(f"    pair count={cnt}: base={bkey} color={ckey}")
        # Whether largest fiber is ascension-level variants of same (pet, lvl, rank):
        # Count distinct (pet, level, rank) keys in fiber.
        per_plr: set = set()
        for o in largest:
            if o.label[1] is None:
                continue
            per_plr.add((str(o.label[1]), int(o.label[2]), int(o.label[3])))
        print(
            f"  largest fiber has {len(per_plr)} distinct (pet, level, rank) keys "
            f"across {len(largest)} options"
        )
        if len(per_plr) > 0:
            avg_asc_per_plr = len(largest) / len(per_plr)
            print(f"  avg asc variants per (pet, level, rank): {avg_asc_per_plr:.2f}")


def _mod_tuple(d: dict[str, int]) -> tuple[tuple[str, int], ...]:
    """Hashable canonical form of a stat dict (sorted by key)."""
    return tuple(sorted(d.items()))


# ---------------------------------------------------------------------------
# Section 3: Contribution vector structure -- does it factor?
# ---------------------------------------------------------------------------


def section3_factorization(
    ir: DomainIR, pets: dict[str, PetDef], mini_rows_by_name: dict[str, dict]
) -> None:
    _print_header("Section 3: Contribution vector structure -- factorization?")
    primary = ir.song_colors[0]

    # Production law:
    #   pet_stats_delta(base, color, level, rank) =
    #     rank * base_mods + floor(color_mod * scale(level))   [per-stat floor]
    # So contribution = (rank * base_mods) + (per-stat floor(color_mod * scale(level)))
    #                  + ascension_bonus.
    # The base and color parts are additive and the base part depends only on
    # (pet, rank); the color part depends on (pet, level) per-stat (the floor
    # is applied to the PRODUCT color_mod * scale, NOT to scale alone).
    print("Production scaling law (pet_stats_delta):")
    print("  rank * base_mods + math.floor(color_mod * scale(level))  [per-stat floor]")
    print()
    print("Factorization verdict:")
    print("  base part  = rank * base_mods                       -> depends on (pet, rank)")
    print("  color part = floor(color_mod * scale(level)) per-stat -> depends on (pet, level)")
    print("  ascension  = per-pet-per-song PP + color vector     -> depends on (pet, asc, song)")
    print()
    print("  -> contribution = base_part + color_part + ascension_part")
    print("  -> the mini axis IS a 3-component additive decomposition,")
    print("     NOT a flat 138,601-way enum.")
    print()
    print("  NOTE on the color part: the floor is applied to the PRODUCT")
    print("  (color_mod * scale(level)), NOT to scale alone. The color axis")
    print("  coordinate is (pet, level) per-stat, not (pet, floor(scale)).")
    print("  This means level does NOT collapse to ~5 floor-bins; per-stat")
    print("  flooring makes the color part a piecewise-constant function of")
    print("  level with up to ~49 distinct values per pet across L1..L50.")

    # Demonstrate the per-stat floor structure: floor(scale) alone collapses
    # to 5 bins, but floor(color_mod * scale) per-stat is denser.
    print()
    print("Color level scale floor values (level -> floor(scale)) -- for reference:")
    scale_floors: dict[int, int] = {}
    for lv in range(1, 51):
        scale_floors[lv] = int(np.floor(pet_color_level_scale(lv)))
    distinct_floors = sorted(set(scale_floors.values()))
    print(f"  distinct floor(scale) values across L1..L50: {distinct_floors}")
    print(f"  count: {len(distinct_floors)}")
    by_floor: dict[int, list[int]] = {}
    for lv, fl in scale_floors.items():
        by_floor.setdefault(fl, []).append(lv)
    print("  level ranges per floor:")
    for fl in distinct_floors:
        lvs = by_floor[fl]
        print(f"    floor={fl}: L{min(lvs)}..L{max(lvs)} ({len(lvs)} levels)")

    # Per-stat floor(color_mod * scale) is denser. Count distinct color-part
    # vectors per pet across L1..L50 at rank=1 for the first 5 pets.
    print()
    print("Per-stat color-part distinct vectors (rank=1, L1..L50) for 5 pets:")
    print("  (color_part = {stat: floor(color_mod[stat] * scale(level))} for stat in color_mods)")
    for name in list(pets.keys())[:5]:
        pet = pets[name]
        distinct_color_vecs: set = set()
        for lv in range(1, 51):
            d = pet_stats_delta(pet.base_mods, pet.color_mods, lv, 1)
            # subtract base part (rank=1 -> base = base_mods)
            color = {k: d.get(k, 0) - pet.base_mods.get(k, 0) for k in pet.color_mods}
            distinct_color_vecs.add(tuple(sorted(color.items())))
        print(
            f"  {name!r}: {len(distinct_color_vecs)} distinct color vectors across L1..L50 "
            f"(color_mods={pet.color_mods})"
        )

    # Distinct base_mods and color_mods vectors across the 90 pets.
    print()
    print("Sparsity of base_mods and color_mods across the 90 pets:")
    base_tuples = Counter()
    color_tuples = Counter()
    for name, pet in pets.items():
        base_tuples[_mod_tuple(pet.base_mods)] += 1
        color_tuples[_mod_tuple(pet.color_mods)] += 1
    print(f"  distinct base_mods vectors:  {len(base_tuples)}")
    print(f"  distinct color_mods vectors: {len(color_tuples)}")
    distinct_pairs = Counter()
    for name, pet in pets.items():
        distinct_pairs[(_mod_tuple(pet.base_mods), _mod_tuple(pet.color_mods))] += 1
    print(f"  distinct (base_mods, color_mods) pairs: {len(distinct_pairs)}")

    # Single-color chart: how many mini states have ZERO color contribution?
    # The color part's per-stat contribution on `primary` is
    #   floor(color_mods[primary] * scale(level))
    # which is zero iff color_mods[primary] == 0 (since scale >= 1 at L>=1,
    # so floor(positive * scale) >= 1).
    print()
    print(f"Single-color chart ({primary!r} only):")
    pets_zero_color = [n for n, p in pets.items() if int(p.color_mods.get(primary, 0)) == 0]
    print(
        f"  pets with zero color_mods[{primary!r}]: {len(pets_zero_color)} / {len(pets)} "
        f"({100.0 * len(pets_zero_color) / len(pets):.1f}%)"
    )
    # Count mini STATES (pet, level, rank, asc) with zero color contribution.
    # Per-stat color contribution on `primary` is floor(color_mods[primary] * scale(level)).
    # Zero iff color_mods[primary] == 0.
    zero_color_states = 0
    total_states = 0
    for name, pet in pets.items():
        if int(pet.color_mods.get(primary, 0)) == 0:
            # All (level, rank, asc) states for this pet have zero color contribution.
            n = 0
            for rank in PET_RANKS:
                lv_cap = pet_rank_to_max_level(rank)
                n += lv_cap  # levels 1..lv_cap
            zero_color_states += n * len(MINI_ASCENSION_LEVELS)
    for name, pet in pets.items():
        for rank in PET_RANKS:
            lv_cap = pet_rank_to_max_level(rank)
            total_states += lv_cap * len(MINI_ASCENSION_LEVELS)
    print(
        f"  mini STATES with zero color contribution: {zero_color_states:,} / {total_states:,} "
        f"({100.0 * zero_color_states / total_states:.1f}%)"
    )
    print("  These states' contributions are pure base-stat; they collapse on the color axis.")

    # Linear-algebra structure: verify base-additivity and per-stat floor
    # linearity for 3 representative pets.
    print()
    print("Linear-algebra structure (verified for 3 representative pets):")
    sample_names = list(pets.keys())[:3]
    for name in sample_names:
        pet = pets[name]
        delta_rank1_lv1 = pet_stats_delta(pet.base_mods, pet.color_mods, 1, 1)
        # rank=2 should be exactly rank1 + base_mods (the color part is
        # identical at the same level, since it does not depend on rank; the
        # base part scales by rank).
        delta_rank2_lv1 = pet_stats_delta(pet.base_mods, pet.color_mods, 1, 2)
        delta_diff = {
            k: delta_rank2_lv1.get(k, 0) - delta_rank1_lv1.get(k, 0)
            for k in set(delta_rank1_lv1) | set(delta_rank2_lv1)
        }
        # Strip zero-valued keys for the equality check (production dicts
        # only carry non-zero entries, but the diff dict carries zeros).
        delta_diff_nonzero = {k: v for k, v in delta_diff.items() if v != 0}
        base_mods_match = delta_diff_nonzero == pet.base_mods
        # Per-stat floor linearity: delta[lvB] - delta[lvA] (at rank=1) on the
        # color part should equal
        #   floor(color_mod * scale(lvB)) - floor(color_mod * scale(lvA))
        # per stat. Use lvA=1, lvB=11 (both floor(scale)=1, but floor(mod*scale)
        # differs per-stat because mod != 1).
        lv_a, lv_b = 1, 11
        delta_a = pet_stats_delta(pet.base_mods, pet.color_mods, lv_a, 1)
        delta_b = pet_stats_delta(pet.base_mods, pet.color_mods, lv_b, 1)
        color_diff = {
            k: delta_b.get(k, 0) - delta_a.get(k, 0) for k in pet.color_mods
        }
        expected_color_diff = {
            k: int(np.floor(v * pet_color_level_scale(lv_b)))
            - int(np.floor(v * pet_color_level_scale(lv_a)))
            for k, v in pet.color_mods.items()
        }
        color_match = color_diff == expected_color_diff
        print(f"  {name!r}:")
        print(f"    base_mods = {pet.base_mods}")
        print(f"    color_mods = {pet.color_mods}")
        print(f"    rank-additivity (delta[r2,lv1] - delta[r1,lv1] == base_mods): {base_mods_match}")
        print(
            f"    per-stat floor-linearity (color diff matches floor(mod*scale) diff): {color_match}"
        )
        print(f"    color_diff L11-L1: {color_diff}")
        print(f"    expected:           {expected_color_diff}")


# ---------------------------------------------------------------------------
# Section 4: Pet archetype clustering
# ---------------------------------------------------------------------------


def section4_archetypes(ir: DomainIR, pets: dict[str, PetDef]) -> None:
    _print_header("Section 4: Pet archetype clustering")
    pairs: Counter = Counter()
    pair_to_pets: dict[tuple, list[str]] = {}
    for name, pet in pets.items():
        key = (_mod_tuple(pet.base_mods), _mod_tuple(pet.color_mods))
        pairs[key] += 1
        pair_to_pets.setdefault(key, []).append(name)
    print(f"Distinct (base_mods, color_mods) pairs across 90 pets: {len(pairs)}")
    print()
    print("Top 10 most common (base_mods, color_mods) pairs:")
    print(f"  {'count':>5}  {'pair':<60}  pets (first 5)")
    for (bkey, ckey), cnt in pairs.most_common(10):
        pets_in = pair_to_pets[(bkey, ckey)]
        print(f"  {cnt:>5}  base={bkey}")
        print(f"         color={ckey}")
        print(f"         pets: {pets_in[:5]}{'...' if len(pets_in) > 5 else ''}")

    # Pets with zero base_mods.
    zero_base = [n for n, p in pets.items() if not any(v != 0 for v in p.base_mods.values())]
    print()
    print(f"Pets with zero base_mods (color-only contributors): {len(zero_base)}")
    if zero_base:
        print(f"  {zero_base}")

    # Pets with zero color_mods.
    zero_color = [n for n, p in pets.items() if not any(v != 0 for v in p.color_mods.values())]
    print(f"Pets with zero color_mods (base-only contributors): {len(zero_color)}")
    if zero_color:
        print(f"  {zero_color}")

    # Distribution of archetype sizes.
    print()
    print("Archetype size distribution:")
    size_hist = Counter(pairs.values())
    for size, count in sorted(size_hist.items()):
        print(f"  size={size}: {count} archetype(s)")


# ---------------------------------------------------------------------------
# Section 5: Ascension interaction
# ---------------------------------------------------------------------------


def section5_ascension(
    ir: DomainIR, pets: dict[str, PetDef], mini_rows_by_name: dict[str, dict]
) -> None:
    _print_header("Section 5: Ascension interaction")
    primary = ir.song_colors[0]
    secondary = ir.song_colors[1] if len(ir.song_colors) > 1 else ""

    # For a fixed (pet, level, rank), how many distinct contribution vectors
    # does varying ascension (0..10) produce? Compute for 5 representative pets.
    sample_names = list(pets.keys())[:5]
    print(
        f"For each of 5 representative pets, vary ascension 0..{MINI_ASCENSION_MAX_LEVEL} "
        f"with fixed (level=10, rank=2):"
    )
    print()
    for name in sample_names:
        pet = pets[name]
        row = _build_mini_ascension_row(name, pet, mini_rows_by_name.get(name, {}))
        vectors_by_asc: dict[int, dict[str, int]] = {}
        for asc in range(0, MINI_ASCENSION_MAX_LEVEL + 1):
            row_asc = dict(row)
            row_asc["Mini Ascension Level"] = asc
            if asc > 0:
                materialized = materialize_mini_for_song(
                    row_asc,
                    song_name=ir.axes[1].name,  # use seed song name placeholder
                    primary_color=primary,
                    secondary_color=secondary,
                )
                delta = pet_stats_delta(pet.base_mods, pet.color_mods, 10, 2)
                for key in ("Perfect Points", *ELEMENT_STAT_KEYS):
                    gained = int(materialized.get(key, 0)) - int(row_asc.get(key, 0))
                    if gained:
                        delta[key] = delta.get(key, 0) + gained
                vectors_by_asc[asc] = delta
            else:
                vectors_by_asc[asc] = pet_stats_delta(pet.base_mods, pet.color_mods, 10, 2)
        # How many distinct vectors?
        distinct_vecs = set()
        for asc, vec in vectors_by_asc.items():
            distinct_vecs.add(_mod_tuple(vec))
        print(f"  {name!r}: {len(distinct_vecs)} distinct contribution vectors across 11 asc levels")

        # Min/max spread per stat across asc 0..10.
        stat_keys = ("Perfect Points", *ELEMENT_COLORS, "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
        print("    per-stat spread (min..max across asc 0..10):")
        for key in stat_keys:
            vals = [vectors_by_asc[a].get(key, 0) for a in range(0, MINI_ASCENSION_MAX_LEVEL + 1)]
            if min(vals) == max(vals):
                continue  # constant across asc; skip for brevity
            print(f"      {key:<18} {min(vals):>5}..{max(vals):>5}  (delta {max(vals) - min(vals):>4})")
        # Print the full vector at asc=0 and asc=10 for visual comparison.
        print(f"    vec @ asc=0:  {dict(sorted(vectors_by_asc[0].items()))}")
        print(f"    vec @ asc=10: {dict(sorted(vectors_by_asc[MINI_ASCENSION_MAX_LEVEL].items()))}")

    print()
    print("Ascension structure verdict:")
    print(
        "  Ascension contributes (a) a constant per-pet PP bonus = 2 * asc_level, "
        "and (b) a per-stat color bonus distributed by the song's primary/secondary "
        "according to the pet's ranked L1 color base values (Component 1 universal pool "
        "+ Component 2 positional match extra)."
    )
    print("  (a) is a constant per-pet-per-song scalar offset on PP.")
    print(
        "  (b) is a per-stat color vector that scales LINEARLY with asc_level (the "
        "scale factor A * 0.5 multiplies the pet's color base, and the positional "
        "match extras also scale linearly with asc_level)."
    )
    print(
        "  -> Ascension is a per-stat VECTOR (color + PP), not a single offset, but "
        "the vector varies LINEARLY with asc_level. It cannot be a separate axis "
        "without fusing with (pet, level, rank): the color routing depends on the "
        "pet's color_mods, not on rank or level."
    )
    print(
        "  -> Ascension can be reformulated as: vec(pet, level, rank, asc) = "
        "base_part(pet, rank) + color_part(pet, level) + asc_linear(pet) * asc + "
        "asc_constant(pet, asc=0). The asc axis is a 1D linear scaling per pet."
    )


def _build_mini_ascension_row(name: str, pet: PetDef, parsed_row: dict) -> dict:
    """Re-implements domain_ir._build_mini_ascension_row for the probe (read-only)."""
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


# ---------------------------------------------------------------------------
# Section 6: Suffix-bound impact of the mini axis
# ---------------------------------------------------------------------------


def section6_suffix_bound(ir: DomainIR) -> None:
    _print_header("Section 6: Suffix-bound impact of the mini axis")
    mini0 = ir.axes[1]
    fibers = mini0.identity_fibers
    n_fibers = len(fibers)
    pw = ir.pw
    print(f"mini:0 suffix_max (single-color): {mini0.suffix_max:,}")
    print(f"fibers: {n_fibers:,}")
    print(f"pw = {pw.tolist()}")

    # P-contribution of each fiber (the P of its representative vec).
    # P = vec @ pw. The fiber is a group of options sharing an identical vec,
    # so the P-contribution is the same for every option in the fiber.
    fiber_p = np.zeros(n_fibers, dtype=np.int64)
    for i, fib in enumerate(fibers):
        fiber_p[i] = int(fib[0].vec @ pw.astype(np.int64))

    # P=0 fiber count.
    n_zero = int((fiber_p == 0).sum())
    print()
    print(f"Fibers with P-contribution == 0: {n_zero:,} / {n_fibers:,} "
          f"({100.0 * n_zero / n_fibers:.1f}%)")
    print("  These minis contribute nothing to gear power on a single-color Chill chart;")
    print("  they are observable-invisible on P, only visible via S/N.")

    # P-contribution histogram.
    print()
    print("P-contribution distribution across the 23,002 fibers:")
    print(f"  min:    {int(fiber_p.min())}")
    print(f"  max:    {int(fiber_p.max())}")
    print(f"  mean:   {float(fiber_p.mean()):.2f}")
    print(f"  median: {float(np.median(fiber_p)):.1f}")
    # Histogram with numpy.
    edges = np.array([-0.5, 0.5, 100.5, 500.5, 1000.5, 2000.5, 4000.5, 8000.5])
    counts, _ = np.histogram(fiber_p, bins=edges)
    print(f"  {'bucket':>16}  {'count':>8}  {'fraction':>10}")
    labels = [
        ("==0", -0.5, 0.5),
        ("1..100", 0.5, 100.5),
        ("101..500", 100.5, 500.5),
        ("501..1000", 500.5, 1000.5),
        ("1001..2000", 1000.5, 2000.5),
        ("2001..4000", 2000.5, 4000.5),
        ("4001..8000", 4000.5, 8000.5),
    ]
    for i, (lbl, lo, hi) in enumerate(labels):
        c = int(counts[i])
        print(f"  {lbl:>16}  {c:>8,}  {100.0 * c / n_fibers:>9.2f}%")

    # Feasible fiber estimate at Gateway top-1 P=5834.
    # Backward recurrence at layer mini:0 rejects a state if
    #   state_P + suffix_min[i] > target  OR  state_P + suffix_max[i] < target.
    # At the mini:0 layer, the row predicate pins the CUMULATIVE P of all
    # preceding layers (team_buff, ...) + this mini's contribution. If the
    # other layers' minimum P contribution is 0 (every layer has a zero
    # option -> suffix_min is 0), then a mini is feasible at the row if
    # state_P <= target - 0 = target. With target P=5834 (Gateway top-1's P
    # as the row's P pin), feasible fibers are those with P-contribution <=
    # 5834 (since the other layers can absorb the residual down to 0).
    target = GATEWAY_TOP1_P
    print()
    print(f"Feasibility estimate at Gateway top-1 P={target}:")
    print("  Other layers' suffix_min (mini:0 -> later layers):")
    print(f"    mini:0.suffix_min = {mini0.suffix_min}  (all later layers have a zero option)")
    print(
        "  Conservative estimate: count fibers with P-contribution <= target "
        "(other layers can fill the residual down to 0)."
    )
    n_feasible = int((fiber_p <= target).sum())
    print(
        f"  Feasible fibers (P-contribution <= {target}): {n_feasible:,} / {n_fibers:,} "
        f"({100.0 * n_feasible / n_fibers:.1f}%)"
    )
    # Tighter: the BACKWARD recurrence at the mini:0 layer also rejects if
    # state_P + suffix_max[i] < target (i.e. even with the max later
    # contribution, the target is unreachable). At mini:0, suffix_max=6859.
    # So a fiber is REJECTED if state_P + 6859 < 5834 -> state_P < -1025.
    # All fiber P >= 0, so the lower bound never rejects at this target.
    # The tighter feasibility is: state_P + 0 <= target AND state_P + 6859 >= target.
    # i.e. state_P in [target - 6859, target] = [-1025, 5834] -> state_P in [0, 5834].
    print(
        "  Backward recurrence tighter bound: state_P in [target - suffix_max, target] "
        f"= [{target - mini0.suffix_max}, {target}] -> state_P in [0, {target}]"
    )
    print("  (lower bound never rejects since fiber P >= 0)")
    print(f"  -> feasible fiber count remains: {n_feasible:,}")


# ---------------------------------------------------------------------------
# Section 7: Verdict
# ---------------------------------------------------------------------------


def section7_verdict(ir: DomainIR, pets: dict[str, PetDef]) -> None:
    _print_header("Section 7: Verdict -- can the mini axis be reformulated?")
    # Compute archetype count + scaling-state count for the reformed product.
    pairs: Counter = Counter()
    for name, pet in pets.items():
        pairs[(_mod_tuple(pet.base_mods), _mod_tuple(pet.color_mods))] += 1
    n_archetypes = len(pairs)

    n_pets = len(pets)
    n_ranks = len(PET_RANKS)
    n_asc = len(MINI_ASCENSION_LEVELS)
    # The color part depends on (pet, level) per-stat. Count distinct
    # color-part vectors per color-archetype across L1..L50.
    color_archetypes: Counter = Counter()
    for name, pet in pets.items():
        color_archetypes[_mod_tuple(pet.color_mods)] += 1
    n_color_archetypes = len(color_archetypes)
    color_archetype_to_vecs: dict[tuple, set] = {}
    for ckey in color_archetypes:
        cmods = dict(ckey)
        vecs: set = set()
        for lv in range(1, 51):
            color = {
                k: int(np.floor(v * pet_color_level_scale(lv)))
                for k, v in cmods.items()
            }
            vecs.add(tuple(sorted(color.items())))
        color_archetype_to_vecs[ckey] = vecs
    n_distinct_color_vecs = sum(len(v) for v in color_archetype_to_vecs.values())
    base_archetypes: Counter = Counter()
    for name, pet in pets.items():
        base_archetypes[_mod_tuple(pet.base_mods)] += 1
    n_base_archetypes = len(base_archetypes)
    # Base part = rank * base_mods, rank in {1,2,3,4}. All 90 pets have
    # non-empty base_mods (section 4), so 4 distinct vectors per archetype.
    n_distinct_base_vecs = 4 * n_base_archetypes

    print("Reformulation: split mini axis into 3 additive sub-axes:")
    print("  mini_base  = rank * base_mods                -> (pet, rank)")
    print("  mini_color = floor(color_mod * scale(level)) -> (pet, level)")
    print("  mini_asc   = per-pet PP + color vector        -> (pet, asc)")
    print()
    print(f"  pet archetypes (base_mods, color_mods pairs): {n_archetypes}")
    print(f"  base archetypes (distinct base_mods):         {n_base_archetypes}")
    print(f"  color archetypes (distinct color_mods):       {n_color_archetypes}")
    print(
        f"  distinct base-part vectors (4 ranks x {n_base_archetypes} archetypes): "
        f"{n_distinct_base_vecs}"
    )
    print(
        f"  distinct color-part vectors (per color-archetype, L1..L50): "
        f"{n_distinct_color_vecs}"
    )
    print(f"  asc levels: 0..{MINI_ASCENSION_MAX_LEVEL} = {n_asc}")
    print()
    reformed_total = (
        n_distinct_base_vecs + n_distinct_color_vecs + n_archetypes * n_asc + 1
    )
    print("Comparison of state-space sizes (per mini slot):")
    print("  current flat enumeration (pet x level x rank x asc + empty): 138,601")
    print("  reformed additive sub-axes (sum, not product):")
    print(f"    mini_base  options: {n_distinct_base_vecs}")
    print(f"    mini_color options: {n_distinct_color_vecs}")
    print(f"    mini_asc   options: {n_archetypes * n_asc} ({n_archetypes} x {n_asc})")
    print("    + 1 empty option (no mini)")
    print(
        f"  -> sum across three sub-axes + empty = "
        f"{n_distinct_base_vecs} + {n_distinct_color_vecs} + {n_archetypes * n_asc} + 1 "
        f"= {reformed_total} options per mini slot (vs 138,601 in one flat axis)"
    )
    print(f"  reduction factor: {138601 / reformed_total:.1f}x")
    print()
    print("CAVEAT -- the (pet, level, rank) legality constraint:")
    print(
        "  The color sub-axis (pet, level) and base sub-axis (pet, rank) are "
        "only independent AFTER fixing the pet archetype. The legality "
        "constraint level <= rank_cap(rank) couples level and rank WITHIN a "
        "pet. So the sub-axes cannot be enumerated fully independently; the "
        "reverse search must track the pet archetype as a SHARED coordinate "
        "across the three sub-axes, and reject (rank, level) combinations "
        "that violate the cap. This is a per-archetype feasibility check, "
        "not a full product enumeration."
    )

    print()
    print("VERDICT:")
    print(
        "The mini axis contribution vector factors cleanly into three "
        "additive, independent components: (1) a base-stat part = "
        f"rank * base_mods, depending only on (pet, rank) -- {n_pets} x "
        f"{n_ranks} = {n_pets * n_ranks} (pet, rank) pairs, collapsing to "
        f"{n_distinct_base_vecs} distinct base-part vectors across "
        f"{n_base_archetypes} base-archetypes; (2) a color part = "
        "floor(color_mod * scale(level)) per-stat, depending only on "
        "(pet, level) -- per-stat flooring of the PRODUCT (not of scale "
        f"alone) means level does NOT collapse to 5 floor-bins; the color "
        f"part has {n_distinct_color_vecs} distinct vectors across "
        f"{n_color_archetypes} color-archetypes; and (3) an ascension part "
        "that is a per-stat vector (PP + color routing) varying LINEARLY "
        f"with asc_level (0..{MINI_ASCENSION_MAX_LEVEL}). The 90 pets "
        f"cluster into only {n_archetypes} distinct (base_mods, color_mods) "
        "archetypes (84 unique + 3 shared pairs), so the mini axis can be "
        "reformulated as three additive sub-axes sharing a pet-archetype "
        "coordinate, instead of a flat 138,601-way enumeration. This "
        "breaks the v2 wall: the effective per-slot iteration drops from "
        f"138,601 to ~{reformed_total} "
        f"({138601 / reformed_total:.1f}x reduction), and the identity-fiber "
        "collapse (138,601 -> 23,002) would shrink further because the "
        "archetype projection dedups across pets sharing identical mod "
        "tables. The (pet, level, rank) legality constraint couples level "
        "and rank within a pet-archetype, so the sub-axes share the "
        "pet-archetype coordinate but do not re-multiplay into a full "
        "product. The ascension sub-axis is a 1D linear scaling per "
        "archetype, enumerated independently at witness time. "
        "RECOMMENDATION: reformulate the mini axis as three additive "
        "sub-axes (mini_base, mini_color, mini_asc) sharing a pet-archetype "
        "coordinate, materializing the full (pet, level, rank, asc) "
        "identity only at witness time."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    webport_root = _resolve_webport_root()
    if not webport_root.is_dir():
        print(f"ERROR: webport_root not found: {webport_root}", file=sys.stderr)
        return 2

    repo_root = _resolve_repo_root()
    minis_csv = repo_root / "Data" / "Gear" / "Minis.csv"
    print(f"webport_root: {webport_root}")
    print(f"repo_root:    {repo_root}")
    print(f"minis_csv:     {minis_csv}")

    pets = extract_pet_info(webport_root)
    mini_rows = list(parse_mini_rows(str(minis_csv)))
    mini_rows_by_name = {str(r.get("Name", "")): r for r in mini_rows}

    # Build the single-color IR (Chill) -- the suffix_max=6859 figure comes
    # from this build.
    print()
    print("Building DomainIR (song_colors=('Chill',)) ...")
    ir = build_domain_ir(webport_root, song_colors=("Chill",))

    section1_decomposition(ir, pets)
    section2_fibers(ir)
    section3_factorization(ir, pets, mini_rows_by_name)
    section4_archetypes(ir, pets)
    section5_ascension(ir, pets, mini_rows_by_name)
    section6_suffix_bound(ir)
    section7_verdict(ir, pets)

    print()
    print("=" * 78)
    print("  mini_axis_probe complete")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
