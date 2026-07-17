"""Reverse engine: exact preimage search over the loadout lattice.

Method (constraint-first, no reward search):
1. Build per-axis option tables (gear slots, upgrade-type counts, mini
   combos, gem-type counts, team buff), each option carrying its
   observable-projected stat vector for the query song.
2. Fold axes sequentially in numpy with dedup, pruning by the exact gear
   power target (P is linear in the projection, so partial sums admit hard
   min/max window pruning).
3. Batch the surviving aggregate vectors through the canonical exact scorer
   and keep exact score matches.
4. Expand matched vectors back into concrete loadouts (DFS with per-suffix
   bounds), then re-run every witness through the full forward oracle -- the
   soundness gate. Any gate failure is an engine bug and raises.

The observable projection is (song colors..., PP, CM, FM, FT, FF). Stats
outside it (e.g. Perfect Time) are invisible to score and gear power alike;
witnesses that differ only there are one equivalence class by construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

from .domain import (
    GEAR_SLOTS,
    MINI_SLOTS,
    DomainError,
    GemAlloc,
    Loadout,
    MiniState,
    Tables,
    TEAM_BUFF_TIERS,
    gem_stats_delta,
    mini_stats_delta,
)
from gear_optimizer.core.team_buff import team_buff_effect

from .game_model import GEARPOWER_MAIN_KEYS, gear_power
from .oracle import Observables, SongOracle
from .webport_extract import UPGRADES_PER_PIECE_MAX


class EngineError(RuntimeError):
    pass


class CapExceeded(EngineError):
    """A lattice/result row cap (max_rows) was exceeded. Distinct from other
    engine failures so query protocols can react to capacity specifically
    (e.g. the gem-floor ladder aborts: wider rungs only search supersets)."""


class DomainMismatch(EngineError):
    """Observables are inconsistent with the song/domain (e.g. naked score
    differs -> wrong chart or game-version drift). Never silently absorbed."""


@dataclass(frozen=True)
class DomainSpec:
    """Enumerable domain caps. The synthetic generator samples strictly inside
    the same spec the engine enumerates, so round-trips are closed.

    ``gear_pool`` restricts each slot to a named subset (None = full table);
    tests use it to keep the lattice deliberately tiny."""

    mini_options: tuple[MiniState, ...] = ()
    mini_max_equipped: int = MINI_SLOTS
    upgrade_type_ids: tuple[int, ...] = ()
    upgrade_max_per_type: int = 3
    upgrade_total_max: int = 6
    gem_max_per_type: int = 6
    # Per-type gem count FLOOR (the progressive real-row ladder pins gems
    # near their caps first: gems dominate P, so a floor collapses the
    # analytic-gem P-slack -- the band width the join must survive -- from
    # thousands to (cap - floor) * p_unit). 0 = the full domain.
    gem_min_per_type: int = 0
    elemental_gem_max: int = 3
    team_buff_options: tuple[tuple[str, str] | None, ...] = (None,)
    allow_empty_gear_slots: bool = True
    gear_pool: dict[str, tuple[str, ...]] | None = None
    force_archetype: str | None = None  # synthetic sampler hint only

    def __post_init__(self):
        if not (0 <= self.gem_min_per_type <= self.gem_max_per_type):
            raise DomainError(
                f"gem_min_per_type={self.gem_min_per_type} outside "
                f"[0, gem_max_per_type={self.gem_max_per_type}]"
            )

    @staticmethod
    def default_team_buffs() -> tuple[tuple[str, str] | None, ...]:
        opts: list[tuple[str, str] | None] = [None]
        opts.extend((tier, color) for tier in TEAM_BUFF_TIERS for color in ("Chill", "Flow", "Rush", "Beat", "Vibe"))
        return tuple(opts)


@dataclass(frozen=True)
class AxisOption:
    label: tuple
    vec: tuple[int, ...]


@dataclass(frozen=True)
class Axis:
    name: str
    options: tuple[AxisOption, ...]


@dataclass
class WitnessClass:
    stats_vec: tuple[int, ...]
    loadouts: list[Loadout] = field(default_factory=list)
    truncated: bool = False


@dataclass
class InversionResult:
    matches: list[WitnessClass]
    candidates_after_p: int
    candidates_scored: int
    lattice_peak_rows: int
    corner_evals: int = 0

    @property
    def witness_count(self) -> int:
        return sum(len(m.loadouts) for m in self.matches)

    @property
    def total_evals(self) -> int:
        return self.candidates_scored + self.corner_evals


def _projection_keys(oracle: SongOracle) -> tuple[str, ...]:
    return (*oracle.song_colors, *GEARPOWER_MAIN_KEYS)


def _p_weights(oracle: SongOracle) -> np.ndarray:
    colors = oracle.song_colors
    if len(colors) == 1:
        color_w = [6]
    else:
        color_w = [4, 2]
    return np.array([*color_w, 5, 5, 5, 5, 5], dtype=np.int64)


def _project(stats: dict[str, int], keys: Sequence[str]) -> tuple[int, ...]:
    return tuple(int(stats.get(k, 0)) for k in keys)


def build_axes(
    oracle: SongOracle,
    tables: Tables,
    spec: DomainSpec,
    *,
    include_gems: bool = True,
) -> list[Axis]:
    """Axis order: gear slots, upgrade types, minis, gem types, elemental,
    team buff. Labels carry enough structure to reassemble loadouts.

    ``include_gems=False`` omits the gem axes: the production join handles
    gems analytically (they dominate gear power and explode any enumerated
    lattice); the brute path keeps them enumerated so the equivalence gate
    proves the analytic algebra."""
    keys = _projection_keys(oracle)
    axes: list[Axis] = []

    gear_axes: list[Axis] = []
    for slot in GEAR_SLOTS:
        options: list[AxisOption] = []
        if spec.allow_empty_gear_slots:
            options.append(AxisOption(label=("gear", slot, None), vec=(0,) * len(keys)))
        pool = None if spec.gear_pool is None else spec.gear_pool.get(slot)
        for name, gdef in sorted(tables.gear_by_slot[slot].items()):
            if pool is not None and name not in pool:
                continue
            options.append(
                AxisOption(label=("gear", slot, name), vec=_project(gdef.stats, keys))
            )
        if not options:
            raise EngineError(f"gear slot {slot} has no options")
        gear_axes.append(Axis(name=f"gear:{slot}", options=tuple(options)))

    # Upgrade ids sharing an identical visible projection are one equivalence
    # class: fold them as a single count-axis and let witness assembly pick
    # representative ids. Ids whose projection is all-zero (e.g. pure Perfect
    # Time trades on an off-color song) are invisible in principle -- they are
    # rejected here so specs stay honest instead of silently enumerable.
    pattern_axes: dict[tuple[tuple[int, ...], ...], list[int]] = {}
    for uid in spec.upgrade_type_ids:
        upgrade = tables.upgrades_by_id.get(uid)
        if upgrade is None:
            raise EngineError(f"spec references unknown upgrade id {uid}")
        base_vec = _project(upgrade.stats, keys)
        if not any(base_vec):
            raise EngineError(
                f"upgrade id {uid} is invisible on this song (zero projection); "
                "remove it from the spec -- its count is unrecoverable in principle"
            )
        pattern_axes.setdefault((base_vec,), []).append(uid)
    for (base_vec,), ids in sorted(pattern_axes.items(), key=lambda kv: kv[1]):
        options = [
            AxisOption(
                label=("upgrade", tuple(ids), count),
                vec=tuple(v * count for v in base_vec),
            )
            for count in range(spec.upgrade_max_per_type + 1)
        ]
        axes.append(Axis(name=f"upgrade:{'+'.join(map(str, ids))}", options=tuple(options)))

    # Minis as three interchangeable slot axes (scales to hundreds of
    # (pet, level, rank, ascension) options; the old subset-combination axis
    # exploded combinatorially). Permutation duplicates collapse in the vector
    # dedup; witness assembly canonicalizes and rejects duplicate names.
    mini_option_vecs: list[AxisOption] = [
        AxisOption(label=("mini_slot", None), vec=(0,) * len(keys))
    ]
    for mini in spec.mini_options:
        delta = mini_stats_delta(
            mini,
            tables,
            song_name=oracle.song_display,
            primary_color=oracle.primary_color,
            secondary_color=oracle.secondary_color,
        )
        mini_option_vecs.append(
            AxisOption(label=("mini_slot", mini), vec=_project(delta, keys))
        )
    for slot_idx in range(min(spec.mini_max_equipped, MINI_SLOTS)):
        axes.append(Axis(name=f"mini_slot:{slot_idx}", options=tuple(mini_option_vecs)))

    if include_gems:
        for attr in ("perfect_points", "combo_multiplier", "fever_multiplier", "fever_time", "fever_fill"):
            options = []
            for count in range(spec.gem_min_per_type, spec.gem_max_per_type + 1):
                gems = GemAlloc(**{attr: count})
                options.append(
                    AxisOption(label=("gem", attr, count), vec=_project(gem_stats_delta(gems), keys))
                )
            axes.append(Axis(name=f"gem:{attr}", options=tuple(options)))

        elem_opts = [AxisOption(label=("elemental", "", 0), vec=(0,) * len(keys))]
        for element in oracle.song_colors:
            for count in range(1, spec.elemental_gem_max + 1):
                gems = GemAlloc(elemental=count, selected_element=element)
                elem_opts.append(
                    AxisOption(
                        label=("elemental", element, count),
                        vec=_project(gem_stats_delta(gems), keys),
                    )
                )
        axes.append(Axis(name="gem:elemental", options=tuple(elem_opts)))

    buff_opts = []
    for buff in spec.team_buff_options:
        if buff is None:
            buff_opts.append(AxisOption(label=("buff", None), vec=(0,) * len(keys)))
        else:
            tier, color = buff
            eff = {k: int(v) for k, v in team_buff_effect(tier, color).items()}
            buff_opts.append(AxisOption(label=("buff", buff), vec=_project(eff, keys)))
    axes.append(Axis(name="team_buff", options=tuple(buff_opts)))

    # Virtual slots first, gear last: the exact-P suffix window tightens with
    # every folded axis, so the high-multiplicity gear axes see the hardest
    # pruning instead of exploding the intermediate lattice early.
    return axes + gear_axes


# Expansion budget: at most this many freshly materialized rows per chunk
# (rows x dim x int32 -- ~112 MB at the default). Bounds peak RAM on the
# no-pagefile target box regardless of table sizes.
_EXPAND_BUDGET_ROWS = 4_000_000


class _GemModel:
    """Analytic gem handling for the production join.

    Gems dominate gear power (real rows: P ~5800 vs ~1000 of gear), and
    enumerating their allocations is THE measured lattice explosion. But a
    gem unit's effect is a fixed pattern, and units pushing a main past the
    160 cap are score-invisible -- only their P mass matters. So the join
    enumerates gems only in EFFECTIVE space (visible increments per type,
    elemental up to cap) and absorbs saturated overflow as exact P-slack
    (bounded-coin feasibility). Witness expansion reconstructs concrete
    allocations from the carried columns."""

    def __init__(self, oracle: SongOracle, spec: DomainSpec, keys: Sequence[str]):
        from .domain import GEM_TYPES

        self.cap = int(spec.gem_max_per_type)
        self.floor = int(spec.gem_min_per_type)
        self.elem_cap = int(spec.elemental_gem_max)
        key_index = {k: i for i, k in enumerate(keys)}
        color_weight = dict(
            zip(oracle.song_colors, (6,) if len(oracle.song_colors) == 1 else (4, 2))
        )
        self.types = []  # (attr, main_dim, main_scale, color_dim|None, p_unit)
        for attr, main_key, color_key, scale in GEM_TYPES:
            main_dim = key_index[main_key]
            color_dim = key_index.get(color_key)
            p_unit = 5 * scale + (3 * color_weight.get(color_key, 0) if color_dim is not None else 0)
            if color_dim is not None and color_key not in color_weight:
                color_dim = None  # off-color side effect: invisible AND P-free
            self.types.append((attr, main_dim, scale, color_dim, p_unit))
        # Elemental gems: only song-color elements are visible/P-bearing.
        self.elements = [
            (elem, key_index[elem], 6 * color_weight[elem])
            for elem in oracle.song_colors
        ]

    def p_reachable(self, r_max: int) -> np.ndarray:
        """Bool array over 0..r_max: total-P values achievable by some gem
        allocation with every type count in [floor, cap] (bounded-coin DP
        on top of the mandatory floor mass)."""
        reach = np.zeros(r_max + 1, dtype=bool)
        base = self.min_p()
        if base > r_max:
            return reach
        reach[base] = True
        for _attr, _md, _sc, _cd, p_unit in self.types:
            if p_unit <= 0:
                continue
            for _ in range(self.cap - self.floor):
                nxt = reach.copy()
                nxt[p_unit:] |= reach[:-p_unit]
                if (nxt == reach).all():
                    break
                reach = nxt
        for _elem, _dim, p_unit in self.elements:
            for _ in range(self.elem_cap):
                nxt = reach.copy()
                nxt[p_unit:] |= reach[:-p_unit]
                if (nxt == reach).all():
                    break
                reach = nxt
        return reach

    def max_p(self) -> int:
        """Maximum total P a gem allocation can contribute (all types at cap
        + the best single elemental at cap). Used to widen the non-gem
        composite windows so lower-P bases (gems fill the gap) survive."""
        total = sum(p_unit * self.cap for _a, _m, _s, _c, p_unit in self.types)
        if self.elements:
            total += self.elem_cap * max(pu for _e, _d, pu in self.elements)
        return int(total)

    def min_p(self) -> int:
        """Mandatory P mass: every type carries at least ``floor`` units.
        (Elemental gems stay optional -- their floor is 0.) The non-gem
        composite windows tighten by this much on the high side: a base
        within ``min_p`` of the target leaves no room for the mandatory
        gems."""
        return int(sum(p_unit * self.floor for _a, _m, _s, _c, p_unit in self.types))

    def slack_splits(
        self, slack: int, coins: list[tuple[int, int]], limit: int
    ) -> list[tuple[int, ...]]:
        """All (u_i) with sum(u_i * p_i) == slack, u_i <= cap_i, up to limit.
        coins = [(p_unit, capacity)]."""
        out: list[tuple[int, ...]] = []

        def rec(idx: int, rem: int, acc: list[int]) -> bool:
            if idx == len(coins):
                if rem == 0:
                    out.append(tuple(acc))
                    return len(out) < limit
                return True
            p_unit, capacity = coins[idx]
            hi = min(capacity, rem // p_unit) if p_unit > 0 else 0
            for u in range(hi + 1):
                acc.append(u)
                alive = rec(idx + 1, rem - u * p_unit, acc)
                acc.pop()
                if not alive:
                    return False
            return True

        rec(0, slack, [])
        return out


def _gem_expand(
    states: np.ndarray,
    gm: _GemModel,
    pw: np.ndarray,
    dim: int,
    n_colors: int,
    p_target: int,
    max_rows: int,
) -> np.ndarray:
    """Expand non-gem candidate states over observably-distinct gem choices.

    Input states: [stats(dim), over_p]. Output rows:
    [stats_final(dim), over_p_final, k1..k5, elem_idx, f, slack,
     m0_1..m0_5, over_p0]  (all int32; elem_idx -1 = none).

    Per state, a DFS over the 5 gem types enumerates visible increments
    k_i (each unit +scale to its main, clamped at 160; +3 to its paired
    on-color if visible) followed by the elemental choice; the exact P
    remainder must be absorbable as saturated-overflow slack (bounded-coin
    feasibility via gm.slack_splits with limit=1).

    ``gm.floor`` constrains each type's TOTAL units (visible k + invisible
    slack units): where a type cannot grow coins (on-color always; off-color
    while unsaturated), k itself must reach the floor; where coins exist,
    the coin carries a mandatory minimum of (floor - k) units."""
    mains0 = slice(n_colors, dim)
    out: list[np.ndarray] = []
    total = 0
    pw64 = pw.astype(np.int64)
    for state in states.astype(np.int64):
        p_state = int(state[:dim] @ pw64) + int(state[dim])
        r_gem = p_target - p_state
        if r_gem < 0:
            continue
        base_row = np.zeros(dim + 15, dtype=np.int64)
        base_row[: dim + 1] = state
        base_row[dim + 6] = -1  # elem_idx none
        base_row[dim + 9 : dim + 14] = state[mains0]
        base_row[dim + 14] = state[dim]

        def emit(row: np.ndarray, rem: int, sat_coins: list[tuple[int, int, int]]):
            nonlocal total
            # Coins carry (p_unit, mandatory_min, capacity): commit the
            # mandatory floor units first, then split the residual freely.
            mandatory = sum(mn * p for p, mn, _cap in sat_coins)
            free_coins = [(p, cap_ - mn) for p, mn, cap_ in sat_coins if cap_ > mn]
            choices: list[tuple[int, int, int, int]] = [(-1, 0, 0, 0)]  # no elemental
            for e_idx, (_elem, e_dim, e_punit) in enumerate(gm.elements):
                for f in range(1, gm.elem_cap + 1):
                    choices.append((e_idx, f, e_dim, f * e_punit))
            for e_idx, f, e_dim, cost in choices:
                if cost + mandatory > rem:
                    continue
                slack = rem - cost
                residual = slack - mandatory
                if residual and (
                    not free_coins or not gm.slack_splits(residual, free_coins, 1)
                ):
                    continue
                final = row.copy()
                if f:
                    final[e_dim] += 6 * f
                final[dim + 6] = e_idx
                final[dim + 7] = f
                final[dim + 8] = slack
                out.append(final)
                total += 1
                if total > max_rows:
                    raise CapExceeded(
                        f"gem expansion exceeded max_rows={max_rows:,}"
                    )

        def rec(t_idx: int, row: np.ndarray, rem: int, sat_coins: list[tuple[int, int, int]]):
            if t_idx == len(gm.types):
                emit(row, rem, sat_coins)
                return
            _attr, main_dim, scale, color_dim, p_unit = gm.types[t_idx]
            eff0 = int(row[main_dim])
            if color_dim is not None:
                # On-color type: EVERY unit stays observable through its
                # +3 color side effect (colors never clamp), so enumerate
                # from the floor to the full cap; main-cap spill lands in
                # over_p. k here IS the type's total.
                for k in range(gm.floor, gm.cap + 1):
                    cost = k * p_unit
                    if cost > rem:
                        break
                    raw_main = eff0 + scale * k
                    nrow = row.copy()
                    nrow[main_dim] = min(raw_main, _STAT_CLAMP_HI)
                    nrow[dim] += 5 * max(0, raw_main - _STAT_CLAMP_HI)
                    if k:
                        nrow[color_dim] += 3 * k
                    nrow[dim + 1 + t_idx] = k
                    rec(t_idx + 1, nrow, rem - cost, sat_coins)
                return
            # Off-color type: units beyond main saturation are fully
            # invisible (off-color side effect carries no P weight either);
            # they become slack coins.
            headroom = _STAT_CLAMP_HI - eff0
            k_nocross = min(gm.cap, headroom // scale) if scale > 0 else 0
            for k in range(k_nocross + 1):
                cost = k * p_unit
                if cost > rem:
                    break
                nrow = row.copy()
                nrow[main_dim] = eff0 + scale * k
                nrow[dim + 1 + t_idx] = k
                saturated = nrow[main_dim] == _STAT_CLAMP_HI and k < gm.cap
                if k < gm.floor and not saturated:
                    continue  # total would fall short of the floor: no coins
                coins = sat_coins
                if saturated:
                    coins = sat_coins + [(p_unit, max(0, gm.floor - k), gm.cap - k)]
                rec(t_idx + 1, nrow, rem - cost, coins)
            # Crossing option: one more unit saturates the main mid-unit; the
            # spilled fraction is score-invisible and lands in over_p.
            k_cross = k_nocross + 1
            if scale > 0 and k_cross <= gm.cap and headroom - k_nocross * scale > 0:
                cost = k_cross * p_unit
                if cost <= rem:
                    nrow = row.copy()
                    spill = scale * k_cross - headroom
                    nrow[main_dim] = _STAT_CLAMP_HI
                    nrow[dim] += 5 * spill
                    nrow[dim + 1 + t_idx] = k_cross
                    coins = sat_coins + [
                        (p_unit, max(0, gm.floor - k_cross), gm.cap - k_cross)
                    ]
                    rec(t_idx + 1, nrow, rem - cost, coins)

        rec(0, base_row, r_gem, [])
    if not out:
        return np.zeros((0, dim + 15), dtype=np.int32)
    arr = np.unique(np.stack(out, axis=0), axis=0)
    return arr.astype(np.int32)


def _fold_mats(
    option_mats: list[np.ndarray],
    names: list[str],
    pw: np.ndarray,
    p_target: int | None,
    max_rows: int,
    *,
    window: tuple[int, int] | None = None,
    col_cap: tuple[int, int] | None = None,
) -> tuple[np.ndarray, int]:
    """Chunked expand + dedup fold over option matrices.

    Pruning modes: ``p_target`` folds to P == p_target exactly; ``window``
    folds to P within an inclusive band (used for group pre-folds against the
    other groups' complement range); neither means dedup only. The cross
    product is expanded in chunks of at most ``_EXPAND_BUDGET_ROWS`` rows
    (int32) and the retained lattice is capped at ``max_rows`` -- loud
    failure, never silent truncation."""
    dim = int(pw.shape[0])
    band = (p_target, p_target) if p_target is not None else window
    option_ps = [mat.astype(np.int64) @ pw for mat in option_mats]
    n = len(option_mats)
    suffix_min = np.zeros(n + 1, dtype=np.int64)
    suffix_max = np.zeros(n + 1, dtype=np.int64)
    for i in range(n - 1, -1, -1):
        suffix_min[i] = suffix_min[i + 1] + option_ps[i].min()
        suffix_max[i] = suffix_max[i + 1] + option_ps[i].max()

    current = np.zeros((1, dim), dtype=np.int32)
    peak = 1
    for i, mat in enumerate(option_mats):
        n_opts = mat.shape[0]
        if band is not None:
            lo = band[0] - suffix_max[i + 1]
            hi = band[1] - suffix_min[i + 1]
        slice_rows = max(1, _EXPAND_BUDGET_ROWS // max(1, n_opts))
        kept_chunks: list[np.ndarray] = []
        kept_total = 0
        for start in range(0, current.shape[0], slice_rows):
            part = current[start : start + slice_rows]
            combined = (part[:, None, :] + mat[None, :, :]).reshape(-1, dim)
            if band is not None:
                p_now = combined.astype(np.int64) @ pw
                combined = combined[(p_now >= lo) & (p_now <= hi)]
            if col_cap is not None and combined.shape[0]:
                combined = combined[combined[:, col_cap[0]] <= col_cap[1]]
            if combined.shape[0] == 0:
                continue
            combined = np.unique(combined, axis=0)
            kept_chunks.append(combined)
            kept_total += combined.shape[0]
            if kept_total > max_rows:
                raise CapExceeded(
                    f"lattice exceeded max_rows={max_rows:,} while folding "
                    f"axis {names[i]} ({kept_total:,}+ rows before final "
                    "dedup); tighten the DomainSpec or raise the cap"
                )
        if not kept_chunks:
            return np.zeros((0, dim), dtype=np.int32), peak
        current = kept_chunks[0] if len(kept_chunks) == 1 else np.unique(
            np.concatenate(kept_chunks, axis=0), axis=0
        )
        del kept_chunks
        peak = max(peak, current.shape[0])
        if current.shape[0] > max_rows:
            raise CapExceeded(
                f"lattice exceeded max_rows={max_rows:,} after axis "
                f"{names[i]} ({current.shape[0]:,} rows); tighten the "
                f"DomainSpec or raise the cap"
            )
    if band is not None:
        final_p = current.astype(np.int64) @ pw
        current = current[(final_p >= band[0]) & (final_p <= band[1])]
    return current, peak


def _build_composites(
    axes: list[Axis],
    pw: np.ndarray,
    p_target: int,
    max_rows: int,
    upgrade_total_max: int | None,
    gem_slack: int = 0,
    gem_p_min: int = 0,
) -> tuple[list[np.ndarray], int]:
    """Pre-fold axes into small composite row sets (meet-in-the-middle
    groups), each windowed against the other groups' P-complement range.
    Every composite carries one extra zero-P-weight column: its upgrade
    count (zero for non-upgrade groups), so the joint upgrade budget stays
    enforceable through any later join.

    ``gem_slack`` is the maximum P that analytic gems can supply: with gems
    handled outside the enumerated lattice, the NON-GEM total may fall short
    of ``p_target`` by up to this much (gems fill the gap). The group windows
    and feasibility check are widened on the low side accordingly -- without
    this, lower-P non-gem bases (the common case, since gems dominate P on
    real rows) are wrongly pruned before the walk sees them. ``gem_p_min``
    is the MANDATORY gem P mass (per-type floors): the non-gem total can sit
    at most ``p_target - gem_p_min``, which tightens the high side -- the
    progressive real-row ladder's whole speedup lives in this band width
    (gem_slack - gem_p_min)."""

    def group_of(name: str, gear_seen: int) -> str:
        if name.startswith("gear:"):
            return "gearL" if gear_seen < 3 else "gearR"
        if name.startswith("mini_slot:"):
            return "minis"  # 3 slot axes pre-folded under the mini P-window
        if name.startswith("upgrade:"):
            return ""  # assigned to a small subgroup below
        if name in ("gem:perfect_points", "gem:combo_multiplier", "gem:fever_multiplier"):
            return "gemsA"
        return "gemsB"  # remaining gems, elemental, team buff

    grouped: dict[str, tuple[list[np.ndarray], list[str]]] = {}
    gear_seen = 0
    upgrade_seen = 0
    for ax in axes:
        mat = np.array([o.vec for o in ax.options], dtype=np.int32)
        tag = group_of(ax.name, gear_seen)
        if ax.name.startswith("gear:"):
            gear_seen += 1
        if ax.name.startswith("upgrade:"):
            # Small subgroups (<=3 axes): one big upgrade group's reachable
            # lattice alone is ~1e7 at production caps; subgroups stay tiny
            # and the joint budget is enforced across them via a carried
            # count column through the join.
            tag = f"upgrades{upgrade_seen // 3}"
            upgrade_seen += 1
        mats, names = grouped.setdefault(tag, ([], []))
        mats.append(mat)
        names.append(ax.name)

    # Two-pass group windows: each group's P contribution must land inside
    # [p_target - sum(other groups' max), p_target - sum(other groups' min)],
    # computable from per-axis option ranges before any folding. For
    # tail-of-range targets (maxed builds -- the realistic production case)
    # this collapses the group lattices themselves, which is what makes
    # per-type upgrade caps at the real game ceiling enumerable at all.
    group_ranges: dict[str, tuple[int, int]] = {}
    for tag, (mats, names) in grouped.items():
        lo = sum(int((mat.astype(np.int64) @ pw).min()) for mat in mats)
        hi = sum(int((mat.astype(np.int64) @ pw).max()) for mat in mats)
        group_ranges[tag] = (lo, hi)
    total_min = sum(lo for lo, _ in group_ranges.values())
    total_max = sum(hi for _, hi in group_ranges.values())
    # Non-gem total T lies in [p_target - gem_slack, p_target - gem_p_min];
    # feasible iff that band intersects the achievable [total_min, total_max].
    if not (total_min <= p_target - gem_p_min and total_max >= p_target - gem_slack):
        return [np.zeros((0, len(pw) + 1), dtype=np.int32)], 1

    # Every composite carries one extra zero-P-weight column: the number of
    # upgrades it contains (zero for non-upgrade groups). The join prunes the
    # column against the joint upgrade budget and strips it at the end.
    pw_ext = np.concatenate([pw, np.zeros(1, dtype=np.int64)])
    budget = upgrade_total_max if upgrade_total_max is not None else 1 << 30
    composites: list[np.ndarray] = []
    peak = 1
    for tag, (mats, names) in grouped.items():
        lo_self, hi_self = group_ranges[tag]
        others_min = total_min - lo_self
        others_max = total_max - hi_self
        # Low end drops by gem_slack (gems can make up the shortfall); high
        # end drops by the mandatory gem mass (it always occupies P).
        window = (
            p_target - gem_slack - others_max,
            p_target - gem_p_min - others_min,
        )
        ext_mats = []
        for mat, name in zip(mats, names):
            if name.startswith("upgrade:"):
                # Upgrade axis options are ordered by count (see build_axes).
                counts = np.arange(mat.shape[0], dtype=np.int32)[:, None]
            else:
                counts = np.zeros((mat.shape[0], 1), dtype=np.int32)
            ext_mats.append(np.hstack([mat, counts]))
        rows, group_peak = _fold_mats(
            ext_mats,
            names,
            pw_ext,
            None,
            max_rows,
            window=window,
            col_cap=(len(pw), budget),
        )
        peak = max(peak, group_peak)
        composites.append(rows)

    # Join order: smallest-first so the largest composites meet the tightest
    # suffix windows.
    composites.sort(key=lambda rows: rows.shape[0])
    return composites, peak


def _fold_lattice(
    axes: list[Axis],
    p_weights: np.ndarray,
    p_target: int,
    max_rows: int,
    upgrade_total_max: int | None = None,
) -> tuple[np.ndarray, int]:
    """P-only candidate generation (the brute reference path): pre-fold
    composites, then join under the exact-P suffix window alone. Kept as the
    guardian baseline for the S-bounded join's equivalence test; production
    inversion uses ``_fold_lattice_s_bounded``."""
    pw = p_weights.astype(np.int64)
    composites, peak = _build_composites(axes, pw, p_target, max_rows, upgrade_total_max)
    if any(c.shape[0] == 0 for c in composites):
        return np.zeros((0, len(pw)), dtype=np.int32), peak
    pw_ext = np.concatenate([pw, np.zeros(1, dtype=np.int64)])
    budget = upgrade_total_max if upgrade_total_max is not None else 1 << 30
    join_names = [f"join:{rows.shape[0]}rows" for rows in composites]
    joined, join_peak = _fold_mats(
        composites,
        join_names,
        pw_ext,
        p_target,
        max_rows,
        col_cap=(len(pw), budget),
    )
    candidates = np.unique(joined[:, : len(pw)], axis=0) if joined.shape[0] else joined[:, : len(pw)]
    return candidates, max(peak, join_peak)


def _witnesses_for_vec(
    target: np.ndarray,
    axes: list[Axis],
    option_mats: list[np.ndarray],
    limit: int,
) -> tuple[list[tuple], bool]:
    """DFS all option-label combos summing to ``target``; per-suffix per-dim
    bounds prune. Returns (label paths, truncated)."""
    n = len(axes)
    dim = target.shape[0]
    suffix_min = np.zeros((n + 1, dim), dtype=np.int64)
    suffix_max = np.zeros((n + 1, dim), dtype=np.int64)
    for i in range(n - 1, -1, -1):
        suffix_min[i] = suffix_min[i + 1] + option_mats[i].min(axis=0)
        suffix_max[i] = suffix_max[i + 1] + option_mats[i].max(axis=0)

    out: list[tuple] = []
    truncated = False
    path: list[tuple] = []

    def dfs(i: int, remaining: np.ndarray) -> bool:
        nonlocal truncated
        if i == n:
            if not remaining.any():
                out.append(tuple(path))
                if len(out) >= limit:
                    truncated = True
                    return False
            return True
        mat = option_mats[i]
        rem_after = remaining[None, :] - mat
        ok = np.all(rem_after >= suffix_min[i + 1], axis=1) & np.all(
            rem_after <= suffix_max[i + 1], axis=1
        )
        for j in np.nonzero(ok)[0]:
            path.append(axes[i].options[j].label)
            alive = dfs(i + 1, remaining - mat[j])
            path.pop()
            if not alive:
                return False
        return True

    dfs(0, target.copy())
    return out, truncated


def _witnesses_for_state(
    state: np.ndarray,
    n_colors: int,
    axes: list[Axis],
    option_mats: list[np.ndarray],
    limit: int,
) -> tuple[list[tuple], bool]:
    """Witness DFS for a clamp-collapsed state row
    [colors, eff mains, count, over_p].

    Reduction: dims with eff < 160 are exact raw targets; dims at the cap
    merge into ONE summed dim with target 160*k + over_p/5 (their raw split
    is score-invisible; only the P mass matters). The reduced problem is an
    exact-sum DFS (reusing _witnesses_for_vec); solutions where a capped dim
    lands below 160 are filtered out afterwards -- they belong to a different
    effective state."""
    dim = n_colors + 5
    over_p = int(state[dim])  # states are [colors, eff mains, over_p]
    eff = state[n_colors:dim]
    capped = [i for i in range(5) if int(eff[i]) == _STAT_CLAMP_HI]
    uncapped = [i for i in range(5) if int(eff[i]) != _STAT_CLAMP_HI]
    if over_p % 5 != 0 or (not capped and over_p != 0):
        return [], False
    overflow_units = over_p // 5

    reduced_targets = [int(state[c]) for c in range(n_colors)]
    reduced_targets += [int(eff[i]) for i in uncapped]
    if capped:
        reduced_targets.append(_STAT_CLAMP_HI * len(capped) + overflow_units)
    target = np.array(reduced_targets, dtype=np.int64)

    reduced_mats = []
    for mat in option_mats:
        cols = [mat[:, c] for c in range(n_colors)]
        cols += [mat[:, n_colors + i] for i in uncapped]
        if capped:
            cols.append(sum(mat[:, n_colors + i] for i in capped))
        reduced_mats.append(np.stack(cols, axis=1).astype(np.int64))

    labels_list, truncated = _witnesses_for_vec(target, axes, reduced_mats, limit)
    if not capped:
        return labels_list, truncated

    # Filter: every capped dim's raw sum must actually reach the cap.
    label_to_vec = [
        {opt.label: np.array(opt.vec, dtype=np.int64) for opt in ax.options}
        for ax in axes
    ]
    valid: list[tuple] = []
    for labels in labels_list:
        raw = np.zeros(dim, dtype=np.int64)
        for ax_i, label in enumerate(labels):
            raw += label_to_vec[ax_i][label]
        if all(int(raw[n_colors + i]) >= _STAT_CLAMP_HI for i in capped):
            valid.append(labels)
    return valid, truncated


def _witnesses_for_gem_state(
    row: np.ndarray,
    gm: "_GemModel",
    n_colors: int,
    axes: list[Axis],
    option_mats: list[np.ndarray],
    limit: int,
) -> tuple[list[tuple[tuple, GemAlloc]], bool]:
    """Witnesses for a gem-expanded candidate row: reconstruct the non-gem
    state from the carried columns, DFS it over the non-gem axes, and
    enumerate the concrete gem allocations realizing the visible increments
    plus the saturated-overflow slack."""
    dim = n_colors + 5
    k = [int(row[dim + 1 + t]) for t in range(5)]
    elem_idx = int(row[dim + 6])
    f = int(row[dim + 7])
    slack = int(row[dim + 8])
    m0 = row[dim + 9 : dim + 14].astype(np.int64)
    over_p0 = int(row[dim + 14])

    nongem = np.zeros(dim + 1, dtype=np.int64)
    nongem[:dim] = row[:dim]
    nongem[n_colors:dim] = m0
    nongem[dim] = over_p0
    for t, (_attr, _main_dim, _scale, color_dim, _p_unit) in enumerate(gm.types):
        if color_dim is not None and k[t]:
            nongem[color_dim] -= 3 * k[t]
    if f and elem_idx >= 0:
        _elem, e_dim, _pu = gm.elements[elem_idx]
        nongem[e_dim] -= 6 * f
    if (nongem[:dim] < 0).any():
        return [], False

    labels_list, truncated = _witnesses_for_state(
        nongem, n_colors, axes, option_mats, limit
    )
    if not labels_list:
        return [], truncated

    # (type index, p_unit, mandatory minimum, capacity). Coins exist only
    # for OFF-color types (invisible overflow); on-color types were
    # enumerated to cap in the expansion. The floor constrains each type's
    # TOTAL units: coin types carry a mandatory (floor - k) minimum, and a
    # coinless type below the floor is inconsistent with the expansion.
    coins: list[tuple[int, int, int, int]] = []
    for t, (_attr, main_dim, _scale, color_dim, p_unit) in enumerate(gm.types):
        if (
            color_dim is None
            and int(row[main_dim]) == _STAT_CLAMP_HI
            and k[t] < gm.cap
        ):
            coins.append((t, p_unit, max(0, gm.floor - k[t]), gm.cap - k[t]))
        elif k[t] < gm.floor:
            raise EngineError(
                f"gem-state row carries type {t} total {k[t]} below the "
                f"domain floor {gm.floor} with no overflow coins -- "
                "expansion/witness inconsistency (engine bug)"
            )
    mandatory = sum(mn * p for _t, p, mn, _cap in coins)
    residual = slack - mandatory
    if residual < 0:
        raise EngineError(
            "gem-state slack below the mandatory floor mass -- "
            "expansion/witness inconsistency (engine bug)"
        )
    if residual:
        splits = gm.slack_splits(
            residual, [(p, cap_ - mn) for _t, p, mn, cap_ in coins], limit
        )
        if not splits:
            return [], truncated
    else:
        splits = [tuple(0 for _ in coins)]

    element_name = gm.elements[elem_idx][0] if (f and elem_idx >= 0) else ""
    out: list[tuple[tuple, GemAlloc]] = []
    for labels in labels_list:
        for split in splits:
            totals = list(k)
            for (t, _p, mn, _cap), u in zip(coins, split):
                totals[t] += mn + u
            alloc = GemAlloc(
                perfect_points=totals[0],
                combo_multiplier=totals[1],
                fever_multiplier=totals[2],
                fever_time=totals[3],
                fever_fill=totals[4],
                elemental=f,
                selected_element=element_name,
            )
            out.append((labels, alloc))
            if len(out) >= limit:
                return out, True
    return out, truncated


def _assemble_loadout(
    labels: Sequence[tuple],
    tables: Tables,
    gems_override: GemAlloc | None = None,
) -> Loadout | None:
    gear: dict[str, str | None] = {}
    upgrade_counts: dict[int, int] = {}
    mini_states: list[MiniState] = []
    gem_kwargs: dict[str, int] = {}
    elemental = (0, "")
    buff: tuple[str, str] | None = None
    for label in labels:
        kind = label[0]
        if kind == "gear":
            _, slot, name = label
            gear[slot] = name
        elif kind == "upgrade":
            _, ids, count = label
            # Ids sharing one projection are interchangeable; assign the count
            # to the first id as the class representative. (Today every
            # pattern has exactly one id; if the game ever ships duplicate
            # patterns, canonical_form must compare pattern-level counts.)
            if count:
                upgrade_counts[ids[0]] = upgrade_counts.get(ids[0], 0) + count
        elif kind == "mini_slot":
            if label[1] is not None:
                mini_states.append(label[1])
        elif kind == "gem":
            _, attr, count = label
            if count:
                gem_kwargs[attr if attr != "fever_fill" else "fever_fill"] = count
        elif kind == "elemental":
            _, element, count = label
            if count:
                elemental = (count, element)
        elif kind == "buff":
            buff = label[1]
        else:
            raise EngineError(f"unknown axis label {label!r}")

    names = [m.name for m in mini_states]
    if len(set(names)) != len(names):
        return None  # same mini in two slots is not a legal loadout
    minis = tuple(sorted(mini_states, key=lambda m: (m.name, m.level, m.rank, m.ascension)))

    total_upgrades = sum(upgrade_counts.values())
    occupied = [s for s in GEAR_SLOTS if gear.get(s) is not None]
    if total_upgrades > len(occupied) * UPGRADES_PER_PIECE_MAX:
        return None  # no legal placement of these upgrades on this gear

    # Canonical placement: upgrades are placement-invariant for stats, so
    # assign ids to occupied slots in slot order, respecting the per-piece cap.
    upgrades: dict[str, tuple[int, ...]] = {}
    flat: list[int] = []
    for uid, count in sorted(upgrade_counts.items()):
        flat.extend([uid] * count)
    idx = 0
    for slot in occupied:
        take = min(UPGRADES_PER_PIECE_MAX, len(flat) - idx)
        if take <= 0:
            break
        upgrades[slot] = tuple(flat[idx : idx + take])
        idx += take

    if gems_override is not None:
        gems = gems_override
    else:
        gems = GemAlloc(
            perfect_points=gem_kwargs.get("perfect_points", 0),
            combo_multiplier=gem_kwargs.get("combo_multiplier", 0),
            fever_multiplier=gem_kwargs.get("fever_multiplier", 0),
            fever_time=gem_kwargs.get("fever_time", 0),
            fever_fill=gem_kwargs.get("fever_fill", 0),
            elemental=elemental[0],
            selected_element=elemental[1],
        )
    loadout = Loadout(
        gear={slot: gear.get(slot) for slot in GEAR_SLOTS},
        upgrades=upgrades,
        minis=minis,
        gems=gems,
        team_buff=buff,
    )
    try:
        loadout.validate(tables)
    except DomainError:
        return None
    return loadout


_STAT_CLAMP_HI = 160  # scorer table span; raw values above collapse per dim


def _base_color_weights(oracle: SongOracle, n_colors: int) -> np.ndarray:
    """The scorer's color mass: base_int = 2*primary + secondary, where on
    single-color charts the secondary column IS the primary one when the
    metadata names it so (weight 3) and absent otherwise (weight 2)."""
    base_w = np.zeros(n_colors, dtype=np.int64)
    base_w[0] = 2
    if n_colors == 2:
        base_w[1] = 1
    if oracle.secondary_color == oracle.primary_color:
        base_w[0] += 1
    return base_w


_S_KEYS_MAX_COMBOS = 150_000


def _build_s_preimage_keys(
    oracle: SongOracle,
    axes: list[Axis],
    gem_model: "_GemModel",
    pw: np.ndarray,
    s_target: int,
) -> dict | None:
    """Exact-S derived-key preimage set over the spec's achievable windows.

    The exact score depends on a candidate ONLY through (base_int =
    base_w . colors, PP/CM/FM curve VALUES, FT cell, FF cell), and at fixed
    (CM, FM, cell) it is non-decreasing in base_value = base_int + ppf. So
    for every achievable (cell, cm plateau, fm plateau, pp plateau) combo
    the exact-S preimage in base_int is ONE integer interval, found here by
    vectorized integer bisection through the canonical batch scorer
    (~2*log2(width)+2 batch calls total).

    Every completion the walk can reach lies inside the axis-sum stat
    windows plus the gem envelope, so its derived key is covered here.
    Returns a ``_SKeyMemo``: EAGER (full enumeration; an empty set proves
    NO PREIMAGE over the whole spec domain) when the global combo space is
    within ``_S_KEYS_MAX_COMBOS``, else LAZY (per-branch boxes bisected on
    demand and memoized)."""
    from .game_model import combo_multiplier, fever_multiplier, perfect_points

    dim = len(pw)
    n_colors = dim - 5
    lo = np.zeros(dim, dtype=np.int64)
    hi = np.zeros(dim, dtype=np.int64)
    for ax in axes:
        mat = np.array([o.vec for o in ax.options], dtype=np.int64)
        lo += mat.min(axis=0)
        hi += mat.max(axis=0)
    if gem_model is not None:
        # Analytic-gem windows; with gems enumerated as plain axes (the
        # key-first path) the axis sums above already cover them.
        for _attr, main_dim_g, scale_g, color_dim_g, _pu in gem_model.types:
            lo[main_dim_g] += scale_g * gem_model.floor
            hi[main_dim_g] += scale_g * gem_model.cap
            if color_dim_g is not None:
                lo[color_dim_g] += 3 * gem_model.floor
                hi[color_dim_g] += 3 * gem_model.cap
        for _elem, e_dim, _pu in gem_model.elements:
            hi[e_dim] += 6 * gem_model.elem_cap

    pp_tab = np.array([perfect_points(s) for s in range(_STAT_CLAMP_HI + 1)], dtype=np.float64)
    cm_tab = np.array([combo_multiplier(s)[2] for s in range(_STAT_CLAMP_HI + 1)], dtype=np.float64)
    fm_tab = np.array([fever_multiplier(s) for s in range(_STAT_CLAMP_HI + 1)], dtype=np.float64)
    _pv, pp_first, pp_id_of = np.unique(pp_tab, return_index=True, return_inverse=True)
    _cv, cm_first, cm_id_of = np.unique(cm_tab, return_index=True, return_inverse=True)
    _fv, fm_first, fm_id_of = np.unique(fm_tab, return_index=True, return_inverse=True)

    def stat_win(d: int) -> tuple[int, int]:
        return (
            int(np.clip(lo[n_colors + d], 0, _STAT_CLAMP_HI)),
            int(np.clip(hi[n_colors + d], 0, _STAT_CLAMP_HI)),
        )

    pp_a, pp_b = stat_win(0)
    cm_a, cm_b = stat_win(1)
    ff_a, ff_b = stat_win(2)
    fm_a, fm_b = stat_win(3)
    ft_a, ft_b = stat_win(4)
    pp_ids = np.arange(int(pp_id_of[pp_a]), int(pp_id_of[pp_b]) + 1)
    cm_ids = np.arange(int(cm_id_of[cm_a]), int(cm_id_of[cm_b]) + 1)
    fm_ids = np.arange(int(fm_id_of[fm_a]), int(fm_id_of[fm_b]) + 1)
    fts = np.arange(ft_a, ft_b + 1)
    ffs = np.arange(ff_a, ff_b + 1)

    base_w = _base_color_weights(oracle, n_colors)
    bi_lo = int(base_w @ lo[:n_colors])
    bi_hi = int(base_w @ hi[:n_colors])
    if bi_hi < bi_lo:
        return None

    memo = _SKeyMemo(
        oracle=oracle,
        s_target=int(s_target),
        base_w=base_w,
        id_of=(pp_id_of, cm_id_of, fm_id_of),
        first=(pp_first, cm_first, fm_first),
        id_windows=(
            (int(pp_id_of[pp_a]), int(pp_id_of[pp_b])),
            (int(cm_id_of[cm_a]), int(cm_id_of[cm_b])),
            (int(fm_id_of[fm_a]), int(fm_id_of[fm_b])),
            (ft_a, ft_b),
            (ff_a, ff_b),
        ),
        bi_window=(bi_lo, bi_hi),
    )
    n_combos = pp_ids.size * cm_ids.size * fm_ids.size * fts.size * ffs.size
    if 0 < n_combos <= _S_KEYS_MAX_COMBOS:
        memo.build_eager(fts, ffs, cm_ids, fm_ids, pp_ids)
    return memo


_S_KEYS_BOX_MAX = 4096


class _SKeyMemo:
    """Exact-S derived-key oracle for the walk.

    Answers "can ANY completion inside this derived-envelope box score
    exactly S?" For each (cell, cm/fm/pp plateau) combo the S-preimage in
    base_int is one integer interval (score is non-decreasing in base at a
    fixed combo), computed by vectorized bisection through the canonical
    batch scorer over the spec's global base window.

    Two modes: EAGER (small global combo space -- full enumeration up
    front, which also yields the domain-wide NO PREIMAGE proof when no
    combo has an interval) and LAZY (combos bisected on first touch and
    memoized; boxes wider than ``_S_KEYS_BOX_MAX`` combos return True --
    undecided, the corridor still applies -- so cost concentrates on the
    deep, tight branches where the kill actually lands)."""

    _EMPTY = (1, 0)  # canonical empty interval sentinel

    def __init__(
        self,
        *,
        oracle: SongOracle,
        s_target: int,
        base_w: np.ndarray,
        id_of: tuple[np.ndarray, np.ndarray, np.ndarray],
        first: tuple[np.ndarray, np.ndarray, np.ndarray],
        id_windows: tuple[tuple[int, int], ...],
        bi_window: tuple[int, int],
    ):
        self.oracle = oracle
        self.s_target = int(s_target)
        self.base_w = base_w
        self.pp_id_of, self.cm_id_of, self.fm_id_of = id_of
        self.pp_first, self.cm_first, self.fm_first = first
        self.win_pp, self.win_cm, self.win_fm, self.win_ft, self.win_ff = id_windows
        self.bi_lo, self.bi_hi = bi_window
        self.eager: dict | None = None
        self.empty = False
        self._memo: dict[int, tuple[int, int]] = {}

    def _bisect(
        self,
        k_ft: np.ndarray,
        k_ff: np.ndarray,
        k_cm: np.ndarray,
        k_fm: np.ndarray,
        k_pp: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Per-combo exact-S base_int interval over the global base window:
        (b_lo, b_hi, valid)."""
        cm_rep = self.cm_first[k_cm].astype(np.int64)
        fm_rep = self.fm_first[k_fm].astype(np.int64)
        pp_rep = self.pp_first[k_pp].astype(np.int64)

        def evals(b: np.ndarray) -> np.ndarray:
            return self.oracle.score_derived_batch(
                b, pp_rep, cm_rep, fm_rep, k_ft, k_ff
            )

        s64 = np.int64(self.s_target)
        lo_b = np.full(k_ft.shape[0], self.bi_lo, dtype=np.int64)
        hi_b = np.full(k_ft.shape[0], self.bi_hi, dtype=np.int64)
        while True:
            active = lo_b < hi_b
            if not bool(active.any()):
                break
            mid = (lo_b + hi_b) // 2
            low = evals(mid) < s64
            lo_b = np.where(active & low, mid + 1, lo_b)
            hi_b = np.where(active & ~low, mid, hi_b)
        lower = lo_b
        valid = evals(lower) == s64
        lo_b2 = lower.copy()
        hi_b2 = np.full(k_ft.shape[0], self.bi_hi, dtype=np.int64)
        while True:
            active = valid & (lo_b2 < hi_b2)
            if not bool(active.any()):
                break
            mid = (lo_b2 + hi_b2 + 1) // 2
            ok = evals(mid) <= s64
            lo_b2 = np.where(active & ok, mid, lo_b2)
            hi_b2 = np.where(active & ~ok, mid - 1, hi_b2)
        return lower, lo_b2, valid

    def build_eager(
        self,
        fts: np.ndarray,
        ffs: np.ndarray,
        cm_ids: np.ndarray,
        fm_ids: np.ndarray,
        pp_ids: np.ndarray,
    ) -> None:
        g = np.meshgrid(fts, ffs, cm_ids, fm_ids, pp_ids, indexing="ij")
        k_ft = g[0].ravel().astype(np.int64)
        k_ff = g[1].ravel().astype(np.int64)
        k_cm = g[2].ravel().astype(np.int64)
        k_fm = g[3].ravel().astype(np.int64)
        k_pp = g[4].ravel().astype(np.int64)
        b_lo, b_hi, valid = self._bisect(k_ft, k_ff, k_cm, k_fm, k_pp)
        self.eager = {
            "ft": k_ft[valid],
            "ff": k_ff[valid],
            "cm_id": k_cm[valid],
            "fm_id": k_fm[valid],
            "pp_id": k_pp[valid],
            "b_lo": b_lo[valid],
            "b_hi": b_hi[valid],
        }
        self.empty = int(self.eager["ft"].size) == 0

    def _combo_key(self, ft: int, ff: int, cm: int, fm: int, pp: int) -> int:
        return (((ft * 161 + ff) * 161 + cm) * 161 + fm) * 161 + pp

    def box_may_hit(
        self,
        ft_a: int,
        ft_b: int,
        ff_a: int,
        ff_b: int,
        cm_a: int,
        cm_b: int,
        fm_a: int,
        fm_b: int,
        pp_a: int,
        pp_b: int,
        bi_lo_b: int,
        bi_hi_b: int,
    ) -> bool:
        ft_a, ft_b = max(ft_a, self.win_ft[0]), min(ft_b, self.win_ft[1])
        ff_a, ff_b = max(ff_a, self.win_ff[0]), min(ff_b, self.win_ff[1])
        cm_a, cm_b = max(cm_a, self.win_cm[0]), min(cm_b, self.win_cm[1])
        fm_a, fm_b = max(fm_a, self.win_fm[0]), min(fm_b, self.win_fm[1])
        pp_a, pp_b = max(pp_a, self.win_pp[0]), min(pp_b, self.win_pp[1])
        bi_lo_b, bi_hi_b = max(bi_lo_b, self.bi_lo), min(bi_hi_b, self.bi_hi)
        if (
            ft_a > ft_b or ff_a > ff_b or cm_a > cm_b or fm_a > fm_b
            or pp_a > pp_b or bi_lo_b > bi_hi_b
        ):
            return False
        if self.eager is not None:
            e = self.eager
            m = (
                (e["ft"] >= ft_a) & (e["ft"] <= ft_b)
                & (e["ff"] >= ff_a) & (e["ff"] <= ff_b)
                & (e["cm_id"] >= cm_a) & (e["cm_id"] <= cm_b)
                & (e["fm_id"] >= fm_a) & (e["fm_id"] <= fm_b)
                & (e["pp_id"] >= pp_a) & (e["pp_id"] <= pp_b)
                & (e["b_hi"] >= bi_lo_b) & (e["b_lo"] <= bi_hi_b)
            )
            return bool(m.any())
        n_box = (
            (ft_b - ft_a + 1) * (ff_b - ff_a + 1) * (cm_b - cm_a + 1)
            * (fm_b - fm_a + 1) * (pp_b - pp_a + 1)
        )
        if n_box > _S_KEYS_BOX_MAX:
            return True  # undecided: too wide to test; the corridor still applies
        g = np.meshgrid(
            np.arange(ft_a, ft_b + 1),
            np.arange(ff_a, ff_b + 1),
            np.arange(cm_a, cm_b + 1),
            np.arange(fm_a, fm_b + 1),
            np.arange(pp_a, pp_b + 1),
            indexing="ij",
        )
        k_ft = g[0].ravel().astype(np.int64)
        k_ff = g[1].ravel().astype(np.int64)
        k_cm = g[2].ravel().astype(np.int64)
        k_fm = g[3].ravel().astype(np.int64)
        k_pp = g[4].ravel().astype(np.int64)
        memo = self._memo
        missing_idx = []
        for j in range(k_ft.shape[0]):
            ck = self._combo_key(int(k_ft[j]), int(k_ff[j]), int(k_cm[j]), int(k_fm[j]), int(k_pp[j]))
            iv = memo.get(ck)
            if iv is None:
                missing_idx.append(j)
            elif iv[0] <= iv[1] and iv[1] >= bi_lo_b and iv[0] <= bi_hi_b:
                return True
        if missing_idx:
            mi = np.array(missing_idx, dtype=np.int64)
            b_lo, b_hi, valid = self._bisect(k_ft[mi], k_ff[mi], k_cm[mi], k_fm[mi], k_pp[mi])
            hit = False
            for pos, j in enumerate(missing_idx):
                iv = (int(b_lo[pos]), int(b_hi[pos])) if bool(valid[pos]) else self._EMPTY
                memo[self._combo_key(int(k_ft[j]), int(k_ff[j]), int(k_cm[j]), int(k_fm[j]), int(k_pp[j]))] = iv
                if iv[0] <= iv[1] and iv[1] >= bi_lo_b and iv[0] <= bi_hi_b:
                    hit = True
            return hit
        return False


def _fold_lattice_decomp(
    axes: list[Axis],
    p_weights: np.ndarray,
    p_target: int,
    max_rows: int,
    upgrade_total_max: int | None,
    gem_model: "_GemModel | None" = None,
    s_target: int | None = None,
    hit_count: int | None = None,
    fever_grids: tuple[np.ndarray, np.ndarray] | None = None,
    s_keys: dict | None = None,
) -> tuple[np.ndarray, int]:
    """v4 candidate generation: exact-P conditioned decomposition join.

    The sequential band fold dies on real rows (>=43M intermediate rows: any
    P-window wide enough for unresolved composites admits the full gear x
    virtual cross). This join never materializes a band:

    - every composite's rows are grouped by EXACT P value;
    - a DP over the P dimension yields, per composite suffix and per exact
      remaining budget R: reachability and per-dim stat bounds -- windows
      conditioned on the exact path, far tighter than global suffix ranges;
    - a depth-first walk assigns each composite an exact P slice (branch)
      and streams the slice products in bounded chunks, clamp-combining
      states ([colors, eff mains, count, over_p]) as it goes;
    - leaves land exactly on P == p_target by construction.

    The one negative-stat gear piece breaks clamp path-independence, so the
    caller splits into non-negative cases first (_negative_case_split).
    Memory: peak = path depth x chunk budget; the cap applies to the
    RESULT set, never an intermediate band."""
    pw = p_weights.astype(np.int64)
    dim = len(pw)
    n_colors = dim - 5
    ft_dim = n_colors + 4
    ff_dim = n_colors + 2
    mains = slice(n_colors, dim)
    empty = np.zeros((0, dim + 1), dtype=np.int32)

    # Non-gem composites may fall short of p_target by up to the gems' max
    # P contribution (gems are handled analytically, outside this lattice)
    # and must leave room for the mandatory floor mass.
    gem_slack = gem_model.max_p() if gem_model is not None else 0
    gem_p_min = gem_model.min_p() if gem_model is not None else 0
    composites, _peak = _build_composites(
        axes, pw, p_target, max_rows, upgrade_total_max, gem_slack, gem_p_min
    )
    if any(c.shape[0] == 0 for c in composites):
        return empty, 1
    budget = upgrade_total_max if upgrade_total_max is not None else 1 << 30

    cases = _negative_case_split(composites, dim)
    out_chunks: list[np.ndarray] = []
    peak = 1
    total_out = 0
    for start_state, case_comps in cases:
        rows, case_peak = _decomp_case(
            start_state,
            case_comps,
            pw,
            dim,
            n_colors,
            ft_dim,
            ff_dim,
            mains,
            p_target,
            budget,
            max_rows,
            gem_model,
            s_target,
            hit_count,
            fever_grids,
            s_keys,
        )
        peak = max(peak, case_peak)
        if rows.shape[0]:
            out_chunks.append(rows)
            total_out += rows.shape[0]
            if total_out > max_rows:
                # Cases can rediscover the same totals from different
                # negative-row starts; judge the cap on distinct rows.
                merged = np.unique(np.concatenate(out_chunks, axis=0), axis=0)
                out_chunks = [merged]
                total_out = int(merged.shape[0])
                if total_out > max_rows:
                    raise CapExceeded(
                        f"decomposition join result exceeded "
                        f"max_rows={max_rows:,} (distinct rows)"
                    )
    if not out_chunks:
        if gem_model is not None:
            return np.zeros((0, dim + 15), dtype=np.int32), peak
        return empty, peak
    non_gem = np.unique(np.concatenate(out_chunks, axis=0), axis=0).astype(np.int32)
    if gem_model is None:
        return non_gem, peak
    expanded = _gem_expand(
        non_gem, gem_model, pw, dim, n_colors, p_target, max_rows
    )
    return expanded, max(peak, expanded.shape[0])


def _negative_case_split(
    composites: list[np.ndarray], dim: int
) -> list[tuple[np.ndarray, list[np.ndarray]]]:
    """Split into cases with all-non-negative composites.

    Rows with any negative stat (one real gear piece trades -1 PP) are
    peeled off: each such row becomes a case's fixed starting state (added
    before anything can reach the cap -- exact), the rest of its composite
    plus all other composites stay as the case's fold input."""
    neg_idx = [i for i, c in enumerate(composites) if (c[:, :dim] < 0).any()]
    zero_state = np.zeros(composites[0].shape[1], dtype=np.int64)
    if not neg_idx:
        return [(zero_state, composites)]
    if len(neg_idx) > 1:
        raise EngineError(
            "multiple negative-carrying composites; extend the case split"
        )
    i = neg_idx[0]
    comp = composites[i]
    neg_mask = (comp[:, :dim] < 0).any(axis=1)
    pos_rows = comp[~neg_mask]
    cases: list[tuple[np.ndarray, list[np.ndarray]]] = []
    rest = composites[:i] + composites[i + 1 :]
    if pos_rows.shape[0]:
        cases.append((zero_state, rest + [pos_rows]))
    for row in comp[neg_mask]:
        cases.append((row.astype(np.int64), rest))
    return cases


def _score_upper_bound_table() -> np.ndarray:
    """Perfect-points table for the closed-form score upper bound."""
    from .game_model import perfect_points

    return np.array([perfect_points(s) for s in range(_STAT_CLAMP_HI + 1)], dtype=np.float64)


def _decomp_case(
    start_state: np.ndarray,
    composites: list[np.ndarray],
    pw: np.ndarray,
    dim: int,
    n_colors: int,
    ft_dim: int,
    ff_dim: int,
    mains: slice,
    p_target: int,
    budget: int,
    max_rows: int,
    gem_model: "_GemModel | None" = None,
    s_target: int | None = None,
    hit_count: int | None = None,
    fever_grids: tuple[np.ndarray, np.ndarray] | None = None,
    s_keys: dict | None = None,
) -> tuple[np.ndarray, int]:
    """One all-non-negative case of the decomposition join."""
    cdim = composites[0].shape[1]
    # Order: small-P-diversity composites first, the two largest row sets
    # last (their pairing happens under the tightest exact windows).
    # Measured on a real maxed row (2026-07-17): ascending explodes at the
    # upgrade-subgroup cross (level 4 > 40M distinct states) and descending
    # is no better (gear x gear alone is a multi-billion raw cross at level
    # 1) -- no ordering fixes full-cap top-1 rows; the upgrade lattice has
    # to become analytic (count-vector join), same coin structure as gems.
    composites = sorted(composites, key=lambda c: c.shape[0])

    # Per composite: rows grouped by exact P value.
    groups: list[dict[int, np.ndarray]] = []
    p_values: list[np.ndarray] = []
    for comp in composites:
        p_part = comp[:, :dim].astype(np.int64) @ pw
        order = np.argsort(p_part, kind="stable")
        comp_sorted = comp[order]
        p_sorted = p_part[order]
        starts = np.flatnonzero(np.diff(p_sorted, prepend=p_sorted[0] - 1))
        ends = np.append(starts[1:], comp_sorted.shape[0])
        g = {
            int(p_sorted[s]): comp_sorted[s:e] for s, e in zip(starts, ends)
        }
        groups.append(g)
        p_values.append(np.array(sorted(g), dtype=np.int64))

    n = len(composites)
    start_p = int(start_state[:dim] @ pw)
    r0 = p_target - start_p
    if r0 < 0:
        return np.zeros((0, dim + 1), dtype=np.int32), 1

    # Suffix reachability over exact remaining P: reach[i] is a bool array
    # over R in [0, r0]. The leaf condition is "remaining P is absorbable":
    # exactly 0 without a gem model, else any gem-reachable total (bounded
    # coin DP) -- gems never enter the enumerated lattice.
    reach = [np.zeros(r0 + 1, dtype=bool) for _ in range(n + 1)]
    if gem_model is None:
        reach[n][0] = True
    else:
        reach[n][:] = gem_model.p_reachable(r0)
    leaf_ok = reach[n].copy()
    for i in range(n - 1, -1, -1):
        acc = reach[i]
        nxt = reach[i + 1]
        for p in p_values[i]:
            p = int(p)
            if p > r0:
                break
            acc[p:] |= nxt[: r0 + 1 - p]

    if not reach[0][r0]:
        return np.zeros((0, dim + 1), dtype=np.int32), 1

    # S-corridor pruning: closed-form bounds on the exact score of EVERY
    # completion of a partial state. This is where the score equation cuts
    # the P band mid-walk (P alone cannot: the analytic-gem slack admits
    # nearly the whole non-gem lattice below the target).
    use_s_bound = s_target is not None and hit_count is not None
    if use_s_bound:
        from .game_model import combo_multiplier, fever_multiplier

        pp_table = _score_upper_bound_table()
        cm_full_table = np.array(
            [combo_multiplier(s)[2] for s in range(_STAT_CLAMP_HI + 1)], dtype=np.float64
        )
        fm_table = np.array(
            [fever_multiplier(s) for s in range(_STAT_CLAMP_HI + 1)], dtype=np.float64
        )
        # Per-composite suffix stat bounds (per dim, over each composite's
        # own rows -- unconditioned on P).
        suf_hi = np.zeros((len(composites) + 1, dim), dtype=np.int64)
        suf_lo = np.zeros((len(composites) + 1, dim), dtype=np.int64)
        for ci in range(len(composites) - 1, -1, -1):
            suf_hi[ci] = suf_hi[ci + 1] + composites[ci][:, :dim].max(axis=0)
            suf_lo[ci] = suf_lo[ci + 1] + composites[ci][:, :dim].min(axis=0)
        # Gem stat maxima CONDITIONED on the exact remaining P budget r: a
        # unit of type t carries p_unit_t of P, so at most
        # min(cap, r // p_unit_t) units fit any completion. The elemental
        # element choice is unknown here, so every song color is bounded as
        # if chosen (simultaneous over-bound, sound). NOTE the += for the
        # elemental term: the previous (removed) bound OVERWROTE the
        # on-color +3 side-effect mass with the elemental mass via max() --
        # that under-count is what made it drop a valid on-color-gem branch.
        r_axis = np.arange(r0 + 1, dtype=np.int64)
        gem_hi_r = np.zeros((r0 + 1, dim), dtype=np.int64)
        if gem_model is not None:
            for _attr, main_dim_g, scale_g, color_dim_g, p_unit_g in gem_model.types:
                units = np.minimum(gem_model.cap, r_axis // max(1, int(p_unit_g)))
                gem_hi_r[:, main_dim_g] += scale_g * units
                if color_dim_g is not None:
                    gem_hi_r[:, color_dim_g] += 3 * units
            for _elem, e_dim, e_punit in gem_model.elements:
                gem_hi_r[:, e_dim] += 6 * np.minimum(
                    gem_model.elem_cap, r_axis // max(1, int(e_punit))
                )
        # Mandatory gem stat minima: every type carries at least ``floor``
        # units; each unit adds scale to its raw main and +3 to its paired
        # on-color (elemental gems are optional -- no mandatory mass).
        gem_lo = np.zeros(dim, dtype=np.int64)
        if gem_model is not None and gem_model.floor > 0:
            for _attr, main_dim_g, scale_g, color_dim_g, _pu in gem_model.types:
                gem_lo[main_dim_g] += scale_g * gem_model.floor
                if color_dim_g is not None:
                    gem_lo[color_dim_g] += 3 * gem_model.floor
        # Pool-aware fever walls: every legal completion plays SOME lane of
        # its own (FT, FF) cell, so its body fever-hit count lies within the
        # bf range of the reachable cell rectangle. Without grids the walls
        # relax to [0, body_total] (all-normal / all-fever) -- still sound.
        if fever_grids is not None:
            bf_min_grid, bf_max_grid = fever_grids
        else:
            bf_min_grid = np.zeros(
                (_STAT_CLAMP_HI + 1, _STAT_CLAMP_HI + 1), dtype=np.int64
            )
            bf_max_grid = np.full(
                (_STAT_CLAMP_HI + 1, _STAT_CLAMP_HI + 1),
                max(0, int(hit_count) - 100),
                dtype=np.int64,
            )
        # per-hit color bonus weights are 3 (single) or 2/1 (double): derive
        # from the P weights (6->3, 4->2, 2->1).
        color_bonus_w = pw[:n_colors].astype(np.float64) / 2.0
        s_target_f = float(s_target)
        body_total_i = max(0, int(hit_count) - 100)
        head_len_i = min(max(0, int(hit_count)), 100)

        def s_corridor_keep(rows: np.ndarray, i_next: int, r_next: int) -> np.ndarray:
            """Keep-mask: which rows can still have a completion scoring
            EXACTLY s_target.

            Stat envelopes. Any completion's final effective stats are
            per-dim inside [lo, hi]: hi = clip(partial_eff + suffix_hi +
            gem_hi_r[r_next], 0, 160) for mains (raw sums then clamp;
            adding never lowers a clamped partial) and unclipped for colors
            (colors never clamp); lo = clip(partial_eff + suffix_lo +
            gem_lo, 0, 160) likewise (all deltas are non-negative within a
            case, tables are non-decreasing, min(160, e + m) >= clip lower
            bound per dim). gem_hi_r[r] >= gem_lo componentwise: the walk
            only reaches r with r >= floor * p_unit_t for every type.

            Fever walls. The completion's (FT, FF) cell lies inside the
            rectangle spanned by the branch's [lo, hi] FT/FF columns, so its
            body fever count bf satisfies bf_min(rect) <= bf <= bf_max(rect)
            for EVERY lane of its cell (grid mins/maxes over the rect).

            UPPER: body = (body_total - bf) * floor(bc) + bf * floor(bc*f)
            <= bc_hi * (body_total + bf_max_rect * (fm_hi - 1)); every head
            hit <= bc_hi * fm_hi; floor(x) <= x throughout. UB < s_target
            => no completion reaches the target.

            LOWER: the exact score is a max over the cell's lanes, so it is
            >= the score of the lane attaining that cell's minimum bf.
            That lane scores body_total * floor(bc) + bf * (floor(bc*f) -
            floor(bc)) + head with head >= head_len * floor(base) (ramp
            scaling >= 1, fever only raises), floor(bc*f) - floor(bc) >=
            max(0, bc*(f-1) - 1), and every factor evaluated at the lo
            envelope only lowers it. LB > s_target => every completion
            overshoots. (Net-negative completions sit outside the scorer's
            domain and are dropped pre-scoring; clipping only loosens the
            walls for them.)
            """
            hi = rows[:, :dim] + suf_hi[i_next] + gem_hi_r[r_next]
            lo = rows[:, :dim] + suf_lo[i_next] + gem_lo
            pp_hi = pp_table[np.clip(hi[:, n_colors], 0, _STAT_CLAMP_HI)]
            cm_hi = cm_full_table[np.clip(hi[:, n_colors + 1], 0, _STAT_CLAMP_HI)]
            fm_hi = fm_table[np.clip(hi[:, n_colors + 3], 0, _STAT_CLAMP_HI)]
            bonus_hi = (hi[:, :n_colors].astype(np.float64) * color_bonus_w).sum(axis=1)
            base_hi = pp_hi + bonus_hi

            ft_a = int(np.clip(lo[:, n_colors + 4], 0, _STAT_CLAMP_HI).min())
            ft_b = int(np.clip(hi[:, n_colors + 4], 0, _STAT_CLAMP_HI).max())
            ff_a = int(np.clip(lo[:, n_colors + 2], 0, _STAT_CLAMP_HI).min())
            ff_b = int(np.clip(hi[:, n_colors + 2], 0, _STAT_CLAMP_HI).max())

            if s_keys is not None:
                # Exact-S key targeting: every completion's derived key
                # (cell, cm/fm/pp plateau, base_int) lies inside the
                # branch's envelope box; if NO S-preimage key intersects
                # that box, no completion can score exactly s_target --
                # the whole branch dies.
                bw = s_keys.base_w
                if not s_keys.box_may_hit(
                    ft_a,
                    ft_b,
                    ff_a,
                    ff_b,
                    int(s_keys.cm_id_of[int(np.clip(lo[:, n_colors + 1], 0, _STAT_CLAMP_HI).min())]),
                    int(s_keys.cm_id_of[int(np.clip(hi[:, n_colors + 1], 0, _STAT_CLAMP_HI).max())]),
                    int(s_keys.fm_id_of[int(np.clip(lo[:, n_colors + 3], 0, _STAT_CLAMP_HI).min())]),
                    int(s_keys.fm_id_of[int(np.clip(hi[:, n_colors + 3], 0, _STAT_CLAMP_HI).max())]),
                    int(s_keys.pp_id_of[int(np.clip(lo[:, n_colors], 0, _STAT_CLAMP_HI).min())]),
                    int(s_keys.pp_id_of[int(np.clip(hi[:, n_colors], 0, _STAT_CLAMP_HI).max())]),
                    int((lo[:, :n_colors] @ bw).min()),
                    int((hi[:, :n_colors] @ bw).max()),
                ):
                    return np.zeros(rows.shape[0], dtype=bool)

            bf_lo = float(bf_min_grid[ft_a : ft_b + 1, ff_a : ff_b + 1].min())
            bf_hi = float(bf_max_grid[ft_a : ft_b + 1, ff_a : ff_b + 1].max())

            bc_hi = base_hi * cm_hi
            ub = bc_hi * (body_total_i + bf_hi * (fm_hi - 1.0) + head_len_i * fm_hi)
            keep = ub >= s_target_f - 0.5

            pp_lo = pp_table[np.clip(lo[:, n_colors], 0, _STAT_CLAMP_HI)]
            cm_lo = cm_full_table[np.clip(lo[:, n_colors + 1], 0, _STAT_CLAMP_HI)]
            fm_lo = fm_table[np.clip(lo[:, n_colors + 3], 0, _STAT_CLAMP_HI)]
            bonus_lo = (lo[:, :n_colors].astype(np.float64) * color_bonus_w).sum(axis=1)
            base_lo = pp_lo + bonus_lo
            bc_lo = base_lo * cm_lo
            delta_lo = np.maximum(0.0, bc_lo * (fm_lo - 1.0) - 1.0)
            lb = (
                body_total_i * np.floor(bc_lo)
                + bf_lo * delta_lo
                + head_len_i * np.floor(base_lo)
            )
            keep &= lb <= s_target_f + 0.5
            return keep

    peak = 1

    state0 = np.zeros(cdim + 1, dtype=np.int64)  # + over_p column
    state0[:cdim] = start_state
    raw0 = state0[mains]
    eff0 = np.minimum(raw0, _STAT_CLAMP_HI)
    state0[cdim] = 5 * int((raw0 - eff0).sum())
    state0[mains] = eff0

    # Level-synchronous traversal over (composite index, exact remaining P):
    # every partial-state set arriving at one (i, r) node is MERGED AND
    # DEDUPED before the node expands. The previous depth-first walk
    # re-expanded a node once per arrival path, so identical states
    # multiplied through the remaining slices -- path multiplicity, not
    # real state volume, is what blew the result caps. Clamp folding is
    # path-independent within a case (non-negative deltas), so per-node
    # dedup is exact; per-level distinct rows are capped by max_rows, and
    # pending raw arrivals are consolidated incrementally so peak RAM stays
    # a small multiple of the cap (no-pagefile box).
    def consolidate(arr: dict[int, list[np.ndarray]]) -> int:
        total = 0
        for r2, chunks in arr.items():
            if len(chunks) > 1:
                arr[r2] = [np.unique(np.concatenate(chunks, axis=0), axis=0)]
            total += int(arr[r2][0].shape[0])
        return total

    level: dict[int, np.ndarray] = {r0: state0[None, :].astype(np.int32)}
    for i in range(n):
        arrivals: dict[int, list[np.ndarray]] = {}
        arrivals_rows = 0
        for r, partial in level.items():
            for p in p_values[i]:
                p = int(p)
                if p > r or not reach[i + 1][r - p]:
                    continue
                rows = groups[i][p].astype(np.int32)
                n_opts = rows.shape[0]
                slice_rows = max(1, _EXPAND_BUDGET_ROWS // max(1, n_opts))
                branch_chunks: list[np.ndarray] = []
                for start in range(0, partial.shape[0], slice_rows):
                    part = partial[start : start + slice_rows]
                    combined = np.repeat(part, n_opts, axis=0)
                    deltas = np.tile(rows, (part.shape[0], 1))
                    combined[:, :dim] += deltas[:, :dim]
                    combined[:, dim] += deltas[:, dim]  # upgrade count
                    raw_m = combined[:, mains]
                    eff_m = np.minimum(raw_m, _STAT_CLAMP_HI)
                    combined[:, cdim] += 5 * (raw_m - eff_m).sum(axis=1)
                    combined[:, mains] = eff_m
                    combined = combined[combined[:, dim] <= budget]
                    if combined.shape[0] == 0:
                        continue
                    combined = np.unique(combined, axis=0)
                    branch_chunks.append(combined)
                if not branch_chunks:
                    continue
                branch = (
                    branch_chunks[0]
                    if len(branch_chunks) == 1
                    else np.unique(np.concatenate(branch_chunks, axis=0), axis=0)
                )
                if use_s_bound and branch.shape[0]:
                    # Both corridor walls are sound (see s_corridor_keep): a
                    # dropped row has NO completion scoring exactly s_target.
                    branch = branch[s_corridor_keep(branch.astype(np.int64), i + 1, r - p)]
                    if branch.shape[0] == 0:
                        continue
                arrivals.setdefault(r - p, []).append(branch)
                arrivals_rows += int(branch.shape[0])
                if arrivals_rows > max_rows:
                    arrivals_rows = consolidate(arrivals)
                    if arrivals_rows > max_rows:
                        raise CapExceeded(
                            f"decomposition level {i + 1} exceeded "
                            f"max_rows={max_rows:,} (distinct rows)"
                        )
        level_total = consolidate(arrivals)
        if level_total > max_rows:
            raise CapExceeded(
                f"decomposition level {i + 1} exceeded "
                f"max_rows={max_rows:,} (distinct rows)"
            )
        level = {r2: chunks[0] for r2, chunks in arrivals.items()}
        for merged in level.values():
            peak = max(peak, int(merged.shape[0]))
        if not level:
            return np.zeros((0, dim + 1), dtype=np.int32), peak

    leaf_chunks = [
        np.concatenate([rows[:, :dim], rows[:, cdim : cdim + 1]], axis=1)
        for r, rows in level.items()
        if leaf_ok[r] and rows.shape[0]
    ]
    if not leaf_chunks:
        return np.zeros((0, dim + 1), dtype=np.int32), peak
    # Distinct (stats, over_p) rows: dropping the upgrade-count column can
    # re-collide rows, so one final dedup.
    leaves = np.concatenate(leaf_chunks, axis=0).astype(np.int32)
    return np.unique(leaves, axis=0), peak


def _monotone_prune(
    candidates: np.ndarray,
    keys: Sequence[str],
    n_colors: int,
    oracle: SongOracle,
    target_score: int,
    *,
    leaf_size: int = 96,
) -> tuple[np.ndarray, int]:
    """Monotone box pruning. Returns (survivor rows to score exactly, corner
    evaluations spent).

    Safety argument: candidates are bucketed by (clamped FT, clamped FF) --
    BOTH fever-pattern stats. Fever Time and Fever Fill Rate are genuinely
    NON-monotone (measured: +1 FT can lower the exact score -- longer fever
    repositions activation windows off high-value stretches), so they must be
    frozen, never bounded. Within a bucket the legal fever-activation
    strategies are fixed, and the score is a max over strategies of
        S = sum_i floor((PP_val + sum w_c * c) * chain_i(CM) * F_i(FM))
    with every factor monotone non-decreasing in its stat (curve tables are
    non-decreasing, floor preserves monotonicity, fever hits fixed per
    strategy; a max of monotone functions over a fixed set is monotone).
    Hence for any candidate v inside a box [lo, hi] (component-wise, same
    bucket): S(lo) <= S(v) <= S(hi). Boxes whose [S(lo), S(hi)] excludes the
    target are discarded whole; the recursion splits surviving boxes on the
    widest remaining dimension. This prunes regions, never individual
    candidates, so no exact match can be lost. The pruned-vs-brute
    equivalence test is the standing guardian of this argument.

    Projection layout: (colors..., PP, CM, FF, FM, FT) -- see
    GEARPOWER_MAIN_KEYS."""
    ft_dim = n_colors + 4
    ff_dim = n_colors + 2
    ft_b = np.minimum(candidates[:, ft_dim], _STAT_CLAMP_HI)
    ff_b = np.minimum(candidates[:, ff_dim], _STAT_CLAMP_HI)
    bucket_keys = ft_b.astype(np.int64) * 1000 + ff_b.astype(np.int64)

    corner_memo: dict[bytes, int] = {}
    evals = 0

    def corner_score(vec: np.ndarray) -> int:
        nonlocal evals
        key = vec.astype(np.int32).tobytes()
        hit = corner_memo.get(key)
        if hit is not None:
            return hit
        stats = {k: int(v) for k, v in zip(keys, vec) if v}
        score = oracle.score_stats(stats)
        corner_memo[key] = score
        evals += 1
        return score

    survivors: list[np.ndarray] = []
    # Splitting the FT/FF dims is pointless inside a bucket (clamped-equal);
    # mask them out of the widest-dim choice via zero width.
    for bkey in np.unique(bucket_keys):
        rows = candidates[bucket_keys == bkey]
        stack = [rows]
        while stack:
            box = stack.pop()
            lo = box.min(axis=0)
            hi = box.max(axis=0)
            if corner_score(hi) < target_score or corner_score(lo) > target_score:
                continue
            if box.shape[0] <= leaf_size:
                survivors.append(box)
                continue
            widths = hi - lo
            widths[ft_dim] = 0
            widths[ff_dim] = 0
            dim = int(np.argmax(widths))
            if widths[dim] <= 0:
                survivors.append(box)  # degenerate box: score members exactly
                continue
            mid = (int(lo[dim]) + int(hi[dim])) // 2
            left = box[box[:, dim] <= mid]
            right = box[box[:, dim] > mid]
            if left.shape[0]:
                stack.append(left)
            if right.shape[0]:
                stack.append(right)
    if not survivors:
        return np.zeros((0, candidates.shape[1]), dtype=candidates.dtype), evals
    return np.concatenate(survivors, axis=0), evals


def invert(
    observed: Observables,
    oracle: SongOracle,
    tables: Tables,
    spec: DomainSpec,
    *,
    max_rows: int = 5_000_000,
    witness_limit_per_vec: int = 500,
    prune: bool = True,
) -> InversionResult:
    expected_naked = oracle.naked_score()
    if int(observed.naked_score) != expected_naked:
        below = int(observed.naked_score) < expected_naked
        cause = (
            "below the all-Perfect naked ceiling: a coupled press-timing "
            "play (presses timed against the COMPOSITE fever bar, naked "
            "score replayed on the NAKED bar) -- inversion needs the "
            "coupled two-bar frontier"
            if below
            else "above the chart's naked ceiling: wrong chart or "
            "game-version drift"
        )
        raise DomainMismatch(
            f"naked score mismatch: observed {observed.naked_score}, chart "
            f"gives {expected_naked} (all-Perfect) -- {cause}; a rounded-up "
            "accuracy hiding a non-FC play also lands here (the naked score "
            "doubles as the FC-and-timing fingerprint)"
        )
    if observed.accuracy != 1.0:
        from .judgments import feasible_judgment_counts

        counts = feasible_judgment_counts(observed.accuracy, oracle.hit_count)
        raise EngineError(
            "non-FC inversion: judgment-count recovery found "
            f"{len(counts)} feasible (P,G,O,M) multiset(s) for accuracy="
            f"{observed.accuracy} over {oracle.hit_count} events "
            f"(sample: {counts[:3]}); the note-level sequence DP against the "
            "exact naked score is the pending layer -- inversion of this row "
            "is not yet supported and no partial answer is returned"
        )

    keys = _projection_keys(oracle)
    p_weights = _p_weights(oracle)
    # Game-law upgrade ceiling: 6 pieces x 15 slots each. A spec may declare
    # a looser total, but no loadout can assemble past the law (witness
    # assembly already rejects it), so joining under the law keeps the
    # lattice free of physically unassemblable upgrade mass.
    upgrade_budget = min(
        int(spec.upgrade_total_max), len(GEAR_SLOTS) * UPGRADES_PER_PIECE_MAX
    )
    if prune:
        # Production path: exact-P conditioned decomposition join over the
        # NON-GEM domain (level-synchronous, honest distinct-row caps),
        # gems handled analytically, S-corridor + lazy exact-S key
        # targeting inside the walk, fever-bucket-safe box pruning on the
        # completed candidates below.
        #
        # A full KEY-FIRST architecture (enumerate the exact-S derived
        # preimage by monotone branch-and-bound, then interval-target DFS
        # per key) was built and MEASURED OUT 2026-07-17: the derived
        # surface is itself millions of points at production windows
        # (Gateway: >4M live search boxes; ~1e11 (cell, PP, CM, FM) lines x
        # even a ~1/17k exact-hit rate leaves ~1e6 keys; the small-spec
        # low-S surface is fatter still). Every exact architecture
        # converges to the same object count -- see the implementation
        # record's session-3 addendum.
        axes = build_axes(oracle, tables, spec, include_gems=False)
        gem_model = _GemModel(oracle, spec, keys)
        s_keys = _build_s_preimage_keys(
            oracle, axes, gem_model, p_weights, int(observed.score)
        )
        if s_keys is not None and s_keys.empty:
            return InversionResult(
                matches=[],
                candidates_after_p=0,
                candidates_scored=0,
                lattice_peak_rows=1,
            )
        candidates, peak = _fold_lattice_decomp(
            axes,
            p_weights,
            int(observed.gear_power),
            max_rows,
            upgrade_budget,
            gem_model,
            s_target=int(observed.score),
            hit_count=oracle.hit_count,
            fever_grids=oracle.fever_body_range_grids(),
            s_keys=s_keys,
        )
        corner_evals = 0
    else:
        # Brute reference path (equivalence-test baseline): P-only join with
        # gems fully enumerated -- the gate that proves the gem algebra.
        axes = build_axes(oracle, tables, spec, include_gems=True)
        gem_model = None
        candidates, peak = _fold_lattice(
            axes,
            p_weights,
            int(observed.gear_power),
            max_rows,
            upgrade_total_max=upgrade_budget,
        )
        corner_evals = 0
    if candidates.shape[0]:
        # Net-negative visible stats sit outside the exact scorer's modeled
        # domain (see domain.compose_stats); drop them before scoring. Only
        # the stats columns participate -- wide gem rows carry elem_idx=-1
        # as the no-elemental sentinel.
        candidates = candidates[np.all(candidates[:, : len(keys)] >= 0, axis=1)]

    to_score = candidates
    if prune and candidates.shape[0] > 512:
        # Completed rows have fixed (FT, FF): the fever-safe box pruning
        # applies before exact scoring.
        to_score, box_evals = _monotone_prune(
            candidates, keys, len(oracle.song_colors), oracle, int(observed.score)
        )
        corner_evals += box_evals

    matches: list[WitnessClass] = []
    scored = 0
    seen_loadouts: set[tuple] = set()
    if to_score.shape[0]:
        option_mats = [np.array([o.vec for o in ax.options], dtype=np.int64) for ax in axes]
        # Many wide rows share one stats prefix (gem interpretations); score
        # each distinct prefix once and fan matches back to the rows. The
        # array-native scorer further collapses prefixes on its derived key
        # (curve plateaus, color-line equivalence) internally.
        stats_mat = to_score[:, : len(keys)]
        uniq_stats, inverse = np.unique(stats_mat, axis=0, return_inverse=True)
        scores = oracle.score_stats_matrix(uniq_stats, keys)
        scored = int(scores.shape[0])
        uniq_match = scores == np.int64(int(observed.score))
        matched_rows = to_score[uniq_match[inverse]]
        for row in matched_rows:
            if prune:
                pairs, truncated = _witnesses_for_gem_state(
                    row.astype(np.int64),
                    gem_model,
                    len(oracle.song_colors),
                    axes,
                    option_mats,
                    witness_limit_per_vec,
                )
            else:
                labels_list, truncated = _witnesses_for_vec(
                    row.astype(np.int64), axes, option_mats, witness_limit_per_vec
                )
                pairs = [(labels, None) for labels in labels_list]
            witness = WitnessClass(stats_vec=tuple(int(v) for v in row), truncated=truncated)
            for labels, gems_override in pairs:
                loadout = _assemble_loadout(labels, tables, gems_override=gems_override)
                if loadout is None:
                    continue
                key = canonical_form(loadout)
                if key in seen_loadouts:
                    continue  # mini-slot permutations collapse here
                seen_loadouts.add(key)
                witness.loadouts.append(loadout)
            if witness.loadouts:
                matches.append(witness)

    # Soundness gate: every witness must reproduce the observables exactly.
    for witness in matches:
        for loadout in witness.loadouts:
            fwd = oracle.forward(loadout, tables)
            if (
                fwd.score != observed.score
                or fwd.naked_score != observed.naked_score
                or fwd.gear_power != observed.gear_power
            ):
                raise EngineError(
                    "soundness gate failure (engine bug): witness "
                    f"{loadout} -> {fwd}, observed {observed}"
                )

    return InversionResult(
        matches=matches,
        candidates_after_p=int(candidates.shape[0]),
        candidates_scored=scored,
        lattice_peak_rows=peak,
        corner_evals=corner_evals,
    )


def invert_progressive(
    observed: Observables,
    oracle: SongOracle,
    tables: Tables,
    spec: DomainSpec,
    *,
    max_rows: int = 5_000_000,
) -> tuple[InversionResult, DomainSpec, list[tuple[int, str]]]:
    """Real-row query protocol: descend the gem-floor ladder.

    Gems dominate real rows' gear power, and the analytic-gem P-slack (the
    band width the join must survive) is exactly the gems' P freedom. Real
    top rows are maxed-ish builds, so the ladder first searches the
    sub-domain with every gem type within delta of its cap (delta=0: band
    ~ the elemental spread only -- near-instant) and widens delta
    geometrically down to the full spec. Each rung is EXACT AND COMPLETE
    within its declared sub-domain; the last rung IS the full spec, so the
    ladder as a whole preserves the engine's completeness contract.

    Honesty contract: a hit on a non-final rung is the complete class OF
    THAT SUB-DOMAIN (gems >= floor per type). Lower-gem preimages were not
    searched -- callers that need certainty confirm across the player's
    other rows (identify_player's forward filter does exactly that; a
    spurious sub-domain class dies against other rows and the caller
    widens). Returns (result, rung spec, [(floor, outcome), ...]).

    A rung that exceeds ``max_rows`` raises immediately: wider rungs search
    supersets, so the cap only gets worse -- escalating would waste minutes
    to learn nothing (the caller must raise the cap or tighten the spec).
    """
    from dataclasses import replace

    cap = int(spec.gem_max_per_type)
    deltas: list[int] = []
    d = 0
    while d < cap:
        deltas.append(d)
        d = 1 if d == 0 else d * 2
    deltas.append(cap)  # final rung == the full spec (floor 0)

    trace: list[tuple[int, str]] = []
    for delta in deltas:
        floor = max(0, cap - delta)
        rung_spec = replace(spec, gem_min_per_type=floor)
        try:
            result = invert(observed, oracle, tables, rung_spec, max_rows=max_rows)
        except CapExceeded as exc:
            trace.append((floor, f"capped: {exc}"))
            raise CapExceeded(
                f"gem-floor ladder capped at floor={floor} (wider rungs are "
                f"supersets and cannot do better); trace={trace}"
            ) from exc
        if result.matches:
            trace.append((floor, f"hit: {result.witness_count} witnesses"))
            return result, rung_spec, trace
        trace.append((floor, "no preimage"))
    return result, rung_spec, trace


def canonical_form(loadout: Loadout) -> tuple:
    """Placement-invariant identity for round-trip comparison: upgrade ids as
    aggregate counts, minis order-free."""
    upgrade_counts: dict[int, int] = {}
    for ids in loadout.upgrades.values():
        for uid in ids:
            upgrade_counts[uid] = upgrade_counts.get(uid, 0) + 1
    return (
        tuple(loadout.gear.get(slot) for slot in GEAR_SLOTS),
        tuple(sorted(upgrade_counts.items())),
        tuple(sorted((m.name, m.level, m.rank, m.ascension) for m in loadout.minis)),
        (
            loadout.gems.perfect_points,
            loadout.gems.combo_multiplier,
            loadout.gems.fever_multiplier,
            loadout.gems.fever_time,
            loadout.gems.fever_fill,
            loadout.gems.elemental,
            loadout.gems.selected_element,
        ),
        loadout.team_buff,
    )


def contains_loadout(result: InversionResult, loadout: Loadout) -> bool:
    key = canonical_form(loadout)
    return any(
        canonical_form(w) == key for m in result.matches for w in m.loadouts
    )


def iter_witnesses(result: InversionResult) -> Iterable[Loadout]:
    for m in result.matches:
        yield from m.loadouts


def gear_power_of_loadout(
    oracle: SongOracle, tables: Tables, loadout: Loadout
) -> int:
    return gear_power(
        oracle.compose(loadout, tables),
        include_base=True,
        song_colors=oracle.song_colors,
    )


def spec_upgrade_budget_ok(spec: DomainSpec) -> bool:
    return (
        spec.upgrade_max_per_type * len(spec.upgrade_type_ids) >= spec.upgrade_total_max
    )


def total_option_product(axes: list[Axis]) -> float:
    prod = 1.0
    for ax in axes:
        prod *= max(1, len(ax.options))
    return prod


def summarize_axes(axes: list[Axis]) -> str:
    parts = [f"{ax.name}={len(ax.options)}" for ax in axes]
    return ", ".join(parts) + f" (raw product {total_option_product(axes):.3g})"
