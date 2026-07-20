"""Static DomainIR for the reverse score engine v2.

Compiles the enumerable loadout decision layers once per data-table version
into 7-dim int32 contribution vectors over the observable projection

    (primary_color, secondary_color,
     Perfect Points, Combo Multiplier, Fever Multiplier,
     Fever Time, Fever Fill Rate)

The 7 stat keys are exactly ``exact_rescore._score_stat_inputs``
(``gear_optimizer/solver/scoring/exact_rescore.py:1025``); every other stat
(Perfect Time, off-color side-effect stats) is invisible to all four
observables -- the off-color fiber (handoff §12, spec §4).

No Taichi, no GPU, no per-query state. This module is the long-lived
data-table cache the reverse search consumes; it MUST be rebuilt only when
``Gears.csv`` / ``Minis.csv`` / ``EquipmentUpgradesSet1.lua`` / PetInfo
change.

Production reuse (no game-model duplication):

- ``gear_optimizer.data.csv_parser`` -- Gears.csv / Minis.csv parsing.
- ``gear_optimizer.data.mini_ascension`` -- ascension 0..10 + song-target
  materialization (used to materialize each mini's per-song stat vector).
- ``gear_optimizer.data.mini_scaling`` -- PetUtils level/rank scaling law
  + PetInfo extractor.
- ``gear_optimizer.data.upgrades`` -- 22 upgrade types, signed per-unit
  stat patterns, per-piece cap 15, joint budget 90.
- ``gear_optimizer.solver.scoring.stats_ops.apply_gems_to_base_stats`` --
  gem contribution (canonical pure helper).
- ``gear_optimizer.core.constants`` -- GEM_SCALE_* / ELEMENTAL_GEM_SCALE
  / GEM_STAT_TO_ELEMENT_SCALE / TOTAL_ROWS.
- ``gear_optimizer.core.team_buff.team_buff_effect`` -- team buff stat
  deltas.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from gear_optimizer.core.gem_defs import ELEMENT_STAT_KEYS
from gear_optimizer.core.team_buff import (
    TEAM_BUFF_ELEMENTS,
    TEAM_BUFF_TIER_ORDER,
    team_buff_effect,
)
from gear_optimizer.data.csv_parser import (
    load_csv_db,
    parse_gear_rows,
    parse_mini_rows,
)
from gear_optimizer.data.mini_ascension import (
    MINI_ASCENSION_BASE_STAT_PREFIX,
    MINI_ASCENSION_MAX_LEVEL,
    materialize_mini_for_song,
    mini_ascension_base_perfect_points_for_mini,
)
from gear_optimizer.data.mini_scaling import (
    PET_MAX_LEVEL,
    PET_MIN_LEVEL,
    PET_RANK_TO_MAX_LEVEL,
    PetDef,
    extract_pet_info,
    pet_color_level_scale,
    pet_rank_to_max_level,
    pet_stats_delta,
)
from gear_optimizer.data.upgrades import (
    UPGRADES_PER_PIECE_MAX,
    UPGRADE_TOTAL_MAX,
    UpgradeDef,
    extract_upgrade_defs,
    load_upgrade_defs,
)
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

# Production re-exports: this module is the canonical import surface for
# the reverse engine. The symbols below are imported from production and
# re-exported so downstream reverse-engine modules import them from
# ``reverse_score_v2.domain_ir`` instead of reaching across the package
# boundary. Listed in ``__all__`` to mark them as intentional public
# re-exports (ruff F401 does not flag ``__all__`` members).
__all__ = [
    "DomainIR",
    "Axis",
    "AxisOption",
    "PROJECTION_KEYS",
    "PROJECTION_DIM",
    "GEARPOWER_MAIN_KEYS",
    "GEM_TYPES",
    "GEAR_SLOTS",
    "PET_RANKS",
    "MINI_ASCENSION_LEVELS",
    "build_domain_ir",
    # Production re-exports (game-model constants + table types).
    "ELEMENTAL_GEM_SCALE",
    "GEM_SCALE_FEVER",
    "GEM_SCALE_NORMAL",
    "GEM_STAT_TO_ELEMENT_SCALE",
    "TEAM_BUFF_ELEMENTS",
    "TEAM_BUFF_TIER_ORDER",
    "team_buff_effect",
    "load_csv_db",
    "parse_gear_rows",
    "parse_mini_rows",
    "MINI_ASCENSION_BASE_STAT_PREFIX",
    "MINI_ASCENSION_MAX_LEVEL",
    "materialize_mini_for_song",
    "mini_ascension_base_perfect_points_for_mini",
    "PET_MAX_LEVEL",
    "PET_MIN_LEVEL",
    "PET_RANK_TO_MAX_LEVEL",
    "PetDef",
    "extract_pet_info",
    "pet_color_level_scale",
    "pet_rank_to_max_level",
    "pet_stats_delta",
    "UPGRADES_PER_PIECE_MAX",
    "UPGRADE_TOTAL_MAX",
    "UpgradeDef",
    "extract_upgrade_defs",
    "load_upgrade_defs",
    "apply_gems_to_base_stats",
]

# ---------------------------------------------------------------------------
# Constants fixed by the game model and the handoff.
# ---------------------------------------------------------------------------

# The observable projection axes, in fixed order. Index 0 is the primary
# color slot; index 1 is the secondary color slot (the empty string on
# single-color charts -- the value stays 0 for every contribution vector,
# but the dimension is reserved so the same 7-dim layout serves both
# arities). The two-color fiber (spec §1) collapses (c1, c2) -> v = 2*c1 +
# c2 inside the row-predicate compiler; the DomainIR itself keeps the raw
# 7-dim projection because the gem elemental axis and the upgrade color
# axes need the per-color mass before collapse.
PROJECTION_KEYS: tuple[str, ...] = (
    "__primary_color__",
    "__secondary_color__",
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Time",
    "Fever Fill Rate",
)
PROJECTION_DIM: int = len(PROJECTION_KEYS)

# Indices of the five gear-power main stats inside the projection.
_PP_IDX = 2
_CM_IDX = 3
_FM_IDX = 4
_FT_IDX = 5
_FF_IDX = 6
_MAIN_IDXS: tuple[int, ...] = (_PP_IDX, _CM_IDX, _FM_IDX, _FT_IDX, _FF_IDX)

# Canonical stat keys for the five non-color gear-power stats.
GEARPOWER_MAIN_KEYS: tuple[str, ...] = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Time",
    "Fever Fill Rate",
)

# The five gem types (non-elemental). Each gem contributes ``+scale`` to one
# main stat and ``+GEM_STAT_TO_ELEMENT_SCALE`` to its paired color. The
# pairing is hardwired in the decompiled source and in
# ``stats_ops.apply_gems_to_base_stats`` -- we mirror it here ONLY for
# labeling; the per-gem contribution vector itself is built by calling
# ``apply_gems_to_base_stats`` so the math stays in one place.
#
# (attr, main_stat_key, paired_color_key, per_unit_main_scale)
GEM_TYPES: tuple[tuple[str, str, str, int], ...] = (
    ("perfect_points", "Perfect Points", "Chill", GEM_SCALE_NORMAL),
    ("combo_multiplier", "Combo Multiplier", "Flow", GEM_SCALE_NORMAL),
    ("fever_multiplier", "Fever Multiplier", "Rush", GEM_SCALE_FEVER),
    ("fever_time", "Fever Time", "Beat", GEM_SCALE_FEVER),
    ("fever_fill", "Fever Fill Rate", "Vibe", GEM_SCALE_FEVER),
)

# Six gear slots in the canonical order the optimizer uses. The DomainIR
# emits one axis per slot, last (highest multiplicity).
GEAR_SLOTS: tuple[str, ...] = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")

# Mini progression bounds. Level is rank-capped via
# ``pet_rank_to_max_level``; ascension is 0..10 per
# ``MINI_ASCENSION_MAX_LEVEL``.
PET_RANKS: tuple[int, ...] = (1, 2, 3, 4)
MINI_ASCENSION_LEVELS: tuple[int, ...] = tuple(range(0, MINI_ASCENSION_MAX_LEVEL + 1))


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AxisOption:
    """One enumerable choice on a decision axis.

    ``label`` is the choice identity (a tuple), carried verbatim through
    the search so witness materialization can re-expand the concrete
    loadout without re-deriving identity. ``vec`` is the 7-dim int32
    contribution to the observable projection.
    """

    label: tuple
    vec: np.ndarray  # shape (PROJECTION_DIM,), dtype int32


@dataclass(frozen=True, slots=True)
class Axis:
    """One decision layer.

    ``options`` is the enumerated choices (fixed order; the reverse search
    references by index). ``identity_fibers`` groups options that share an
    identical contribution vector -- the search treats each fiber as one
    state but witness materialization re-expands all members in sorted
    label order (handoff §5.A.3.e). ``suffix_min`` / ``suffix_max`` are the
    min and max gear-power contribution over the suffix from this layer
    (sum of all later layers' min/max P-contribution), used by the
    backward recurrence's rejection step.
    """

    name: str
    options: tuple[AxisOption, ...]
    identity_fibers: tuple[tuple[AxisOption, ...], ...]
    suffix_min: int
    suffix_max: int


@dataclass(frozen=True, slots=True)
class DomainIR:
    """The static, data-table-version-keyed reverse search domain.

    ``axes`` is one per decision layer in the fixed mixing-poor-first order
    (team_buff, mini groups, upgrades, gems, gear slots). ``pw`` is the
    7-dim int32 gear-power weight vector: P = vec @ pw. ``p_target_axis``
    is always ``-1`` (P is a derived axis, not a stored layer) and is kept
    on the IR for the search to assert against. ``song_colors`` records the
    color arity the IR was built for; the gem elemental axis is enumerated
    per song color, so the IR is per-(data-table, color-arity) -- NOT
    per-song, because ascension song-target materialization is deferred to
    witness time (the mini-identity fiber carries the full
    (name, level, rank, ascension) key, and the per-song stat vector is
    re-derived during witness scoring).
    """

    axes: tuple[Axis, ...]
    pw: np.ndarray
    p_target_axis: int
    song_colors: tuple[str, ...]
    # Bookkeeping the reverse search needs.
    # ``option_mats`` is the stacked int32 (options x 7) matrix per axis,
    # precomputed for vectorized suffix-window pruning.
    option_mats: tuple[np.ndarray, ...]
    # ``layer_names`` mirrors ``axes`` for diagnostics.
    layer_names: tuple[str, ...]
    # ``upgrade_total_max`` is the joint upgrade budget (game law: 90).
    upgrade_total_max: int
    # ``gem_max_per_type`` / ``upgrade_max_per_type`` echo the build args.
    gem_max_per_type: int
    upgrade_max_per_type: int
    # ``pet_defs`` / ``upgrade_defs`` are the raw extracted tables, retained
    # so witness materialization can re-derive per-song ascension bonuses
    # without re-reading the decompiled source.
    pet_defs: tuple[PetDef, ...]
    upgrade_defs: tuple[UpgradeDef, ...]
    # ``mini_rows`` is the parsed Minis.csv rows (with ``Song Target``),
    # retained for the same reason.
    mini_rows: tuple[dict, ...]
    # ``gear_rows`` is the parsed Gears.csv rows.
    gear_rows: tuple[dict, ...]
    # ``gem_elemental_colors`` is the per-axis elemental gem color list (the
    # only song-color-dependent part of the IR).
    gem_elemental_colors: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------


def _projection_keys_for_colors(song_colors: tuple[str, ...]) -> tuple[str, ...]:
    """The 7 projection keys for the given color arity.

    Index 0 is always the primary color. Index 1 is the secondary color or
    the empty placeholder on single-color charts. The five main stat keys
    follow.
    """
    if len(song_colors) == 0 or len(song_colors) > 2:
        raise ValueError(f"song_colors must have length 1 or 2, got {song_colors!r}")
    secondary = song_colors[1] if len(song_colors) == 2 else ""
    return (song_colors[0], secondary, *GEARPOWER_MAIN_KEYS)


def _gear_power_weights(song_colors: tuple[str, ...]) -> np.ndarray:
    """The 7-dim int32 gear-power weight vector.

    One-color:  ``pw = [6, 0, 5, 5, 5, 5, 5]``  ->  P = 6*c1 + 5*sum(main).
    Two-color:  ``pw = [4, 2, 5, 5, 5, 5, 5]``  ->  P = 4*c1 + 2*c2 + 5*sum(main).
    """
    if len(song_colors) == 1:
        color_w = (6, 0)
    elif len(song_colors) == 2:
        color_w = (4, 2)
    else:
        raise ValueError(f"song_colors must have length 1 or 2, got {song_colors!r}")
    return np.array([*color_w, 5, 5, 5, 5, 5], dtype=np.int32)


def _project_stats(
    stats: Mapping[str, int],
    *,
    primary: str,
    secondary: str,
) -> np.ndarray:
    """Project a stats dict onto the 7-dim int32 observable projection."""
    vec = np.zeros(PROJECTION_DIM, dtype=np.int32)
    vec[0] = int(stats.get(primary, 0))
    if secondary:
        vec[1] = int(stats.get(secondary, 0))
    vec[_PP_IDX] = int(stats.get("Perfect Points", 0))
    vec[_CM_IDX] = int(stats.get("Combo Multiplier", 0))
    vec[_FM_IDX] = int(stats.get("Fever Multiplier", 0))
    vec[_FT_IDX] = int(stats.get("Fever Time", 0))
    vec[_FF_IDX] = int(stats.get("Fever Fill Rate", 0))
    return vec


# ---------------------------------------------------------------------------
# Gem contribution (adapter around apply_gems_to_base_stats)
# ---------------------------------------------------------------------------


def _gem_contribution(
    *,
    primary: str,
    secondary: str,
    gem_attr: str | None = None,
    gem_count: int = 0,
    elemental_color: str | None = None,
    elemental_count: int = 0,
) -> np.ndarray:
    """Build a 7-dim int32 contribution vector for one gem allocation.

    The math lives in ``apply_gems_to_base_stats``; this function is a thin
    adapter that calls it with an empty base, subtracts the empty base, and
    projects the delta onto the 7-dim observable layout. The DomainIR
    never reimplements gem scaling -- it asks the production helper for the
    per-(count) stat delta and projects it.
    """
    g_pp = g_cm = g_fm = g_ft = g_ff = 0
    if gem_attr == "perfect_points":
        g_pp = gem_count
    elif gem_attr == "combo_multiplier":
        g_cm = gem_count
    elif gem_attr == "fever_multiplier":
        g_fm = gem_count
    elif gem_attr == "fever_time":
        g_ft = gem_count
    elif gem_attr == "fever_fill":
        g_ff = gem_count
    sel_color = elemental_color or ""
    g_ov = int(elemental_count)
    base = apply_gems_to_base_stats(
        {},
        sel_color,
        g_ft,
        g_ff,
        g_pp,
        g_cm,
        g_fm,
        g_ov,
        add_missing_element_key=True,
    )
    # apply_gems_to_base_stats returns the final stats; subtract the empty
    # base (all zeros) to get the delta, then project.
    delta = {k: int(v) for k, v in base.items()}
    return _project_stats(delta, primary=primary, secondary=secondary)


# ---------------------------------------------------------------------------
# Per-axis builders
# ---------------------------------------------------------------------------


def _build_team_buff_axis(
    *,
    primary: str,
    secondary: str,
) -> Axis:
    """Team buff axis: tiers Ã— colors + the (NONE, "") zero option.

    The team buff contributes ``PP`` and one color stat per
    ``team_buff_effect``. The color axis is the 5 elemental colors -- the
    buff can apply to any of them, and the reverse search must enumerate
    all 5 even on a single-color chart (an off-color buff is P-invisible
    but stat-visible to the canonical scorer only through song_colors, so
    off-color buff choices collapse to the zero vector on single-color
    charts and are deduped into the identity fiber with the (NONE, "")
    option).
    """
    options: list[AxisOption] = [AxisOption(label=("team_buff", "NONE", ""), vec=np.zeros(PROJECTION_DIM, dtype=np.int32))]
    for tier in TEAM_BUFF_TIER_ORDER:
        if tier == "NONE":
            continue
        for color in TEAM_BUFF_ELEMENTS:
            eff = team_buff_effect(tier, color)
            vec = _project_stats(eff, primary=primary, secondary=secondary)
            options.append(AxisOption(label=("team_buff", tier, color), vec=vec))
    return _finalize_axis("team_buff", tuple(options))


def _build_mini_axes(
    pets: Mapping[str, PetDef],
    mini_rows: Mapping[str, Mapping],
    *,
    primary: str,
    secondary: str,
    song_name: str,
    mini_max_equipped: int,
) -> list[Axis]:
    """Build the mini slot axes.

    Each mini slot is one axis. The option set is the same for every slot:
    an empty option (no mini in that slot) plus one option per
    (name, level, rank, ascension) state. The mini-identity fiber
    (handoff §12, spec §3) is NOT collapsed -- the full
    (name, level, rank, ascension) key is carried in the label, even when
    two distinct states would project to the same 7-dim vector on the seed
    song. The reverse search dedups by vector at the state level but
    witness materialization re-expands per identity.

    The per-slot stat vector is computed by PetUtils scaling
    (``pet_stats_delta``) plus ascension materialization
    (``materialize_mini_for_song``). The ascension bonus is song-specific;
    we materialize against the seed song ``song_name`` so the IR carries a
    concrete vector. The mini-identity fiber ensures that if the same
    identity projects differently on another song, the multi-row filter
    still distinguishes them.
    """
    # Enumerate (level, rank, ascension) states per mini.
    states: list[tuple] = []
    for name in sorted(pets):
        pet = pets[name]
        for rank in PET_RANKS:
            lv_cap = pet_rank_to_max_level(rank)
            for level in range(PET_MIN_LEVEL, lv_cap + 1):
                for asc in MINI_ASCENSION_LEVELS:
                    states.append((name, level, rank, asc))

    options: list[AxisOption] = [AxisOption(label=("mini", None, None, None, None), vec=np.zeros(PROJECTION_DIM, dtype=np.int32))]
    for name, level, rank, asc in states:
        pet = pets[name]
        # PetUtils scaling -> base + color stat mods at (level, rank).
        delta = pet_stats_delta(pet.base_mods, pet.color_mods, level, rank)
        # Ascension materialization needs a parsed mini row (Song Target +
        # L1 base color columns). Build a minimal row from the PetDef and
        # the parsed Minis.csv entry.
        if asc > 0:
            row = _build_mini_ascension_row(name, pet, mini_rows.get(name, {}))
            row["Mini Ascension Level"] = asc
            materialized = materialize_mini_for_song(
                row,
                song_name=song_name,
                primary_color=primary,
                secondary_color=secondary,
            )
            # Add the ascension delta (materialized - raw row) to the
            # PetUtils delta.
            for key in ("Perfect Points", *ELEMENT_STAT_KEYS):
                gained = int(materialized.get(key, 0)) - int(row.get(key, 0))
                if gained:
                    delta[key] = delta.get(key, 0) + gained
        vec = _project_stats(delta, primary=primary, secondary=secondary)
        options.append(AxisOption(label=("mini", name, level, rank, asc), vec=vec))

    axes: list[Axis] = []
    for slot_idx in range(mini_max_equipped):
        axes.append(_finalize_axis(f"mini:{slot_idx}", tuple(options)))
    return axes


def _build_mini_ascension_row(
    name: str,
    pet: PetDef,
    parsed_row: Mapping,
) -> dict:
    """Build the minimal mini row ``materialize_mini_for_song`` expects.

    ``materialize_mini_for_song`` reads:
    - ``Name`` (for error messages);
    - ``Song Target`` (the JSON list of songs the ascension bonus applies
      to);
    - ``Mini Ascension Enabled`` (bool);
    - ``Mini Ascension Level`` (set by the caller);
    - the L1 base color columns under ``Mini Ascension Base <Color>``
      (preferred) or the main color columns;
    - the main-block color and non-color columns (used by
      ``mini_ascension_elemental_bonus`` via
      ``ranked_mini_ascension_colors``).

    The PetDef's ``color_mods`` are exactly the L1 base color values (the
    PetInfo extractor reads them from ``get_color_statmodifierobj``); we
    set both the main and ``Mini Ascension Base <Color>`` columns to those
    values so the materialization sees a consistent L1 row regardless of
    whether the parsed Minis.csv row was present.
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


def _build_upgrade_axes(
    upgrades: list[UpgradeDef],
    *,
    primary: str,
    secondary: str,
    song_colors: tuple[str, ...],
    upgrade_max_per_type: int,
) -> list[Axis]:
    """Build the per-type upgrade count axes (coin representation).

    Each of the 22 upgrade types is one axis; options are count 0..cap.
    The per-unit stat pattern is projected to the 7-dim layout and scaled
    by the count. The upgrade-count fiber (handoff §12, spec §2) collapses
    placements of the same multiset -- the canonical key carries aggregate
    count per type, not per-(slot, type). The fiber is verified per type
    by the forward oracle (spec §2.4); the DomainIR trusts that
    verification and emits one count-axis per type.

    Upgrade types whose 7-dim projection is all-zero on this song (pure
    Perfect Time / off-color trades) are still emitted as axes with a
    single non-trivial option (count = 0) plus the count range -- the
    joint budget is enforced through the count column, and the search
    cannot recover an all-zero type's count from observables (it is
    bounded only by the budget). The reverse search treats these as
    free dimensions; witness materialization re-expands them under the
    budget constraint.
    """
    axes: list[Axis] = []
    for upgrade in upgrades:
        options: list[AxisOption] = []
        unit_vec = _project_stats(upgrade.stat_pattern, primary=primary, secondary=secondary)
        for count in range(0, upgrade_max_per_type + 1):
            vec = (unit_vec * count).astype(np.int32)
            options.append(AxisOption(label=("upgrade", upgrade.uid, upgrade.name, count), vec=vec))
        axes.append(_finalize_axis(f"upgrade:{upgrade.uid}:{upgrade.name}", tuple(options)))
    return axes


def _build_gem_axes(
    *,
    primary: str,
    secondary: str,
    song_colors: tuple[str, ...],
    gem_max_per_type: int,
) -> list[Axis]:
    """Build the 5 gem-type count axes + the elemental gem axis.

    The five non-elemental types are count-axes 0..cap. The elemental axis
    enumerates (color, count) for each song color plus the zero option;
    off-color elemental gems are P-invisible and stat-invisible and are
    not emitted (they collapse to the zero option).
    """
    axes: list[Axis] = []
    for attr, _main_key, _color_key, _scale in GEM_TYPES:
        options: list[AxisOption] = []
        for count in range(0, gem_max_per_type + 1):
            vec = _gem_contribution(
                primary=primary,
                secondary=secondary,
                gem_attr=attr,
                gem_count=count,
            )
            options.append(AxisOption(label=("gem", attr, count), vec=vec))
        axes.append(_finalize_axis(f"gem:{attr}", tuple(options)))

    # Elemental gem axis: one option per (color, count) for song colors,
    # plus the zero option. Only song colors are visible; off-color
    # elementals collapse to the zero vector and are not emitted.
    elem_options: list[AxisOption] = [
        AxisOption(label=("gem", "elemental", "", 0), vec=np.zeros(PROJECTION_DIM, dtype=np.int32))
    ]
    # Unique colors: ("Chill", "Chill") must not emit duplicate elemental
    # options (same vec / same label stem).
    for color in dict.fromkeys(song_colors):
        for count in range(1, gem_max_per_type + 1):
            vec = _gem_contribution(
                primary=primary,
                secondary=secondary,
                elemental_color=color,
                elemental_count=count,
            )
            elem_options.append(AxisOption(label=("gem", "elemental", color, count), vec=vec))
    axes.append(_finalize_axis("gem:elemental", tuple(elem_options)))
    return axes


def _build_gear_axis(
    slot: str,
    gear_rows: list[Mapping],
    *,
    primary: str,
    secondary: str,
) -> Axis:
    """Build one gear slot axis.

    Options: an empty option (no gear in this slot) plus one per gear row
    of the matching type. Gear pieces with identical 7-dim projection are
    grouped into one identity fiber (the search treats them as one state;
    witness materialization re-expands all members in sorted name order).
    """
    options: list[AxisOption] = [AxisOption(label=("gear", slot, None), vec=np.zeros(PROJECTION_DIM, dtype=np.int32))]
    for row in sorted(gear_rows, key=lambda r: str(r.get("Name", ""))):
        if str(row.get("type", "")).strip() != slot:
            continue
        stats = {k: int(row.get(k, 0)) for k in (*ELEMENT_STAT_KEYS, *GEARPOWER_MAIN_KEYS)}
        vec = _project_stats(stats, primary=primary, secondary=secondary)
        options.append(AxisOption(label=("gear", slot, row["Name"]), vec=vec))
    return _finalize_axis(f"gear:{slot}", tuple(options))


# ---------------------------------------------------------------------------
# Axis finalization (identity fibers + stacking)
# ---------------------------------------------------------------------------


def _finalize_axis(name: str, options: tuple[AxisOption, ...]) -> Axis:
    """Group options into identity fibers and stub suffix bounds.

    Identity fibers group options with identical 7-dim contribution
    vectors. The search treats each fiber as one state; witness
    materialization re-expands all members in sorted label order. The
    fiber order is the first-option appearance order (stable); within a
    fiber, members are sorted by label.

    ``suffix_min`` / ``suffix_max`` are filled in by
    ``_compute_suffix_bounds`` after all axes are built.
    """
    fibers: dict[bytes, list[AxisOption]] = {}
    order: list[bytes] = []
    for opt in options:
        key = opt.vec.tobytes()
        if key not in fibers:
            fibers[key] = []
            order.append(key)
        fibers[key].append(opt)
    grouped = tuple(
        tuple(sorted(fibers[key], key=lambda o: tuple(str(x) for x in o.label)))
        for key in order
    )
    return Axis(
        name=name,
        options=options,
        identity_fibers=grouped,
        suffix_min=0,
        suffix_max=0,
    )


def _compute_suffix_bounds(axes: list[Axis], pw: np.ndarray) -> None:
    """Fill in ``suffix_min`` / ``suffix_max`` on each axis in place.

    For axis ``i``, ``suffix_min[i]`` is the sum of min P-contribution over
    axes ``i+1..end`` (the suffix from this layer). The backward recurrence
    at layer ``i`` rejects a state if ``state_P + suffix_min[i] > target``
    or ``state_P + suffix_max[i] < target``.

    We mutate the frozen dataclass via ``object.__setattr__`` -- the IR is
    built once and then read-only, so this is a one-shot setup step.
    """
    n = len(axes)
    suffix_min = [0] * (n + 1)
    suffix_max = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        opt_mat = np.stack([opt.vec for opt in axes[i].options], axis=0).astype(np.int64)
        opt_p = opt_mat @ pw.astype(np.int64)
        suffix_min[i] = suffix_min[i + 1] + int(opt_p.min())
        suffix_max[i] = suffix_max[i + 1] + int(opt_p.max())
    for i, axis in enumerate(axes):
        object.__setattr__(axis, "suffix_min", int(suffix_min[i + 1]))
        object.__setattr__(axis, "suffix_max", int(suffix_max[i + 1]))


# ---------------------------------------------------------------------------
# Top-level build
# ---------------------------------------------------------------------------


def build_domain_ir(
    webport_root: Path,
    *,
    gear_csv: Path | None = None,
    minis_csv: Path | None = None,
    song_colors: tuple[str, ...] = ("Chill",),
    song_name: str = "__domain_ir_seed__",
    mini_max_equipped: int = 3,
    gem_max_per_type: int = 15,
    upgrade_max_per_type: int = 15,
) -> DomainIR:
    """Compile the static DomainIR for one data-table version + color arity.

    ``webport_root`` is the decompiled ``ReplicatedStorage`` parent; PetInfo
    is read from ``<root>/Pets/PetInfo`` and upgrades from
    ``<root>/Avatar/EquipmentUpgradesSet1``.

    ``gear_csv`` / ``minis_csv`` default to ``Data/Gear/Gears.csv`` /
    ``Data/Gear/Minis.csv`` resolved relative to the repo root (the
    directory two levels above this module's ``gear_optimizer`` import
    root).

    ``song_colors`` fixes the color arity. The IR is per-(data-table,
    color-arity) -- the gem elemental axis enumerates only song colors.
    The mini stat vectors are materialized against ``song_name`` (a seed
    song for the IR build); the mini-identity fiber carries the full
    (name, level, rank, ascension) key so witness materialization can
    re-derive the per-query song's ascension bonus without rebuilding the
    IR.
    """
    root = Path(webport_root)
    if len(song_colors) == 0 or len(song_colors) > 2:
        raise ValueError(f"song_colors must have length 1 or 2, got {song_colors!r}")
    primary, secondary = (song_colors[0], song_colors[1] if len(song_colors) == 2 else "")

    # Resolve CSV paths relative to the repo root. The repo root is the
    # directory two levels above ``gear_optimizer`` -- i.e. the directory
    # that contains ``gear_optimizer/`` and ``Data/``.
    if gear_csv is None:
        gear_csv = _repo_root() / "Data" / "Gear" / "Gears.csv"
    if minis_csv is None:
        minis_csv = _repo_root() / "Data" / "Gear" / "Minis.csv"
    gear_csv = Path(gear_csv)
    minis_csv = Path(minis_csv)
    if not gear_csv.is_file():
        raise FileNotFoundError(f"Gears.csv not found: {gear_csv}")
    if not minis_csv.is_file():
        raise FileNotFoundError(f"Minis.csv not found: {minis_csv}")

    # --- Load production data tables -------------------------------------
    gear_rows = list(parse_gear_rows(str(gear_csv)))
    if not gear_rows:
        raise ValueError(f"no gear rows parsed from {gear_csv}")
    mini_rows = list(parse_mini_rows(str(minis_csv)))
    if not mini_rows:
        raise ValueError(f"no mini rows parsed from {minis_csv}")
    pet_defs = extract_pet_info(root)
    upgrade_defs = list(extract_upgrade_defs(root))
    if not upgrade_defs:
        raise ValueError(f"no upgrade defs extracted from {root}")

    pets_by_name = dict(pet_defs)
    mini_rows_by_name = {str(r.get("Name", "")): r for r in mini_rows}

    # --- Build axes in the fixed mixing-poor-first order ----------------
    axes: list[Axis] = []

    # 1. team_buff (small)
    axes.append(_build_team_buff_axis(primary=primary, secondary=secondary))

    # 2. mini group 1, 2, 3
    axes.extend(
        _build_mini_axes(
            pets_by_name,
            mini_rows_by_name,
            primary=primary,
            secondary=secondary,
            song_name=song_name,
            mini_max_equipped=mini_max_equipped,
        )
    )

    # 3. upgrade types (22 axes, count 0..cap per type)
    axes.extend(
        _build_upgrade_axes(
            upgrade_defs,
            primary=primary,
            secondary=secondary,
            song_colors=song_colors,
            upgrade_max_per_type=upgrade_max_per_type,
        )
    )

    # 4. gem types (5 + elemental)
    axes.extend(
        _build_gem_axes(
            primary=primary,
            secondary=secondary,
            song_colors=song_colors,
            gem_max_per_type=gem_max_per_type,
        )
    )

    # 5. gear slots 1..6 (last -- highest multiplicity)
    for slot in GEAR_SLOTS:
        axes.append(
            _build_gear_axis(
                slot,
                gear_rows,
                primary=primary,
                secondary=secondary,
            )
        )

    # --- Gear-power weights + suffix bounds ------------------------------
    pw = _gear_power_weights(song_colors)
    _compute_suffix_bounds(axes, pw)

    option_mats = tuple(
        np.stack([opt.vec for opt in axis.options], axis=0).astype(np.int32)
        for axis in axes
    )

    return DomainIR(
        axes=tuple(axes),
        pw=pw,
        p_target_axis=-1,
        song_colors=tuple(song_colors),
        option_mats=option_mats,
        layer_names=tuple(axis.name for axis in axes),
        upgrade_total_max=UPGRADE_TOTAL_MAX,
        gem_max_per_type=gem_max_per_type,
        upgrade_max_per_type=upgrade_max_per_type,
        pet_defs=tuple(pet_defs.values()),
        upgrade_defs=tuple(upgrade_defs),
        mini_rows=tuple(mini_rows),
        gear_rows=tuple(gear_rows),
        gem_elemental_colors=tuple(song_colors),
    )


def _repo_root() -> Path:
    """Return the repo root (the directory containing ``gear_optimizer/``).

    This module imports from ``gear_optimizer.*``, so the repo root is the
    first parent of ``gear_optimizer`` found on ``sys.path``. We resolve it
    from the ``gear_optimizer`` package directory to avoid depending on
    ``os.getcwd()`` (the reverse engine is a long-lived service).
    """
    import gear_optimizer

    return Path(gear_optimizer.__file__).resolve().parent.parent
