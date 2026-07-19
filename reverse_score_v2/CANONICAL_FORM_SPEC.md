# `canonical_form` Specification — Reverse Score Engine v2

> Status: K1 prerequisite. This document fixes the class-identity rule from
> `docs/REVERSE_SCORE_V2_HANDOFF.md` §12 so the brute-force class-equality
> gate (`test_class_completeness_vs_brute`) is well-defined. No production
> code is changed by this document; it specifies the contract the v2
> `canonical_form` implementation must satisfy.
>
> Scope: defines the canonical key for the v2 reverse score engine, covering
> all four fiber types named in §12 (two-color, upgrade-count, mini-identity,
> off-color / invisible-stat). The brute-force gate hashes
> `canonical_form(loadout)`; two loadouts are the same class member iff their
> canonical keys are equal. Every collapse below is lossy at the physical
> level by design and is proved lossless at the observable level by the
> forward oracle.

## 0. Terminology and references

- **Observable.** One of the four quantities a leaderboard row exposes:
  geared score `S`, naked score `N`, gear power `P`, accuracy `A`. v1's
  ground-truth table (`docs/Implementation Records/REVERSE_SCORE_ENGINE.md`,
  "Observable semantics") fixes their definitions.
- **Forward oracle.** The canonical path in
  `gear_optimizer/solver/scoring/exact_rescore.py`:
  `score_stats_exact` / `score_stats_exact_batch` /
  `score_stat_arrays_exact_batch`. Reused unchanged by v2 per handoff §2.9.
  `score_stat_arrays_exact_batch` now exists in v2 (committed in
  `d0c38be4`) as the canonical array-native Vulkan soundness-gate scorer,
  implemented as `ir = build_exact_score_ir(...); return score_from_ir(ir,
  ...)`.
- **Physical loadout.** A concrete `Loadout` (gear per slot, per-slot
  upgrade ids, mini states, gem alloc, team buff). Two physical loadouts
  may be one class member.
- **Canonical key.** The tuple returned by `canonical_form(loadout)`. The
  brute-force gate hashes it.
- **Fiber.** A set of physical loadouts that the canonical key deliberately
  identifies. Four fiber types are named in §12; this spec defines each.
- **Forward-oracle invariant check.** A named code-level assertion that
  raises loudly if an observable distinguishes two physical loadouts the
  canonical key collapsed. Each fiber type names its check below.

Decompiled ground truth (cited throughout):

- `reverse_score/game_model.py` — 1:1 port of `gear_power`,
  `color_point_bonus_perfect`, `observable_projection`, mini PetUtils
  scaling.
- `docs/Implementation Records/REVERSE_SCORE_ENGINE.md` — "Uniqueness"
  invariant: Perfect Time and off-color side-effect stats are invisible to
  all observables by construction.
- `gear_optimizer/solver/scoring/exact_rescore.py:480` (`_score_stat_inputs`)
  — the exact scorer consumes exactly seven stat inputs: `primary_color`,
  `secondary_color`, `Perfect Points`, `Combo Multiplier`, `Fever
  Multiplier`, `Fever Time`, `Fever Fill Rate`. No other stat appears.

## 1. Two-color fiber

### 1.1 Definition

On a two-color chart with primary color `c1` and secondary color `c2`, the
canonical key carries the single integer

```
v = 2*c1_stat + c2_stat
```

in place of the pair `(c1_stat, c2_stat)`. All `(c1_stat, c2_stat)` pairs
that produce the same `v` are one class member. `c1_stat` and `c2_stat`
are the loadout's total stat contributions in the primary and secondary
color dimensions (after gear + upgrades + minis + gems + team buff).

### 1.2 Invariance proof (all four observables)

Trace each observable through the canonical path. The exact scorer's
per-row inputs (`exact_rescore.py:480`, `_score_stat_inputs`) feed
`primary_val` and `secondary_val` into the scoring arithmetic in exactly
one combination:

- `base_value = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)`
  (`exact_rescore.py:539`, also `:437`, `:619`, `:844`, `:918`).
- Every subsequent score term — `combo_val = floor(base_value * combo_f)`,
  `fever_val = floor(base_value * combo_f * fever_f)`, the head-loop
  `perfect_value = base_value * scaling` — depends on `primary_val` and
  `secondary_val` only through `base_value`. Therefore **geared score `S`
  is a function of `v = 2*c1 + c2` and the other five stat inputs; the
  split between `c1` and `c2` is invisible to `S`**.

Gear power (`reverse_score/game_model.py:225`, `gear_power`):

- One-color: `P = 5*Σ(main) + 6*c1`. No `c2` exists; the question does not
  arise (see §1.3).
- Two-color: `P = 5*Σ(main) + 4*c1 + 2*c2 = 5*Σ(main) + 2*(2*c1 + c2) =
  5*Σ(main) + 2*v`. **`P` is a function of `v` alone** for the color part.

Naked score `N`: the naked score object uses the all-zero statsdict
(`reverse_score/oracle.py:111`, `naked_score`), so `c1 = c2 = 0` and `v =
0` for every loadout on every chart. **`N` is trivially invariant under
any `(c1, c2) ↔ (c1', c2')` collapse because it depends on no loadout
stat at all.**

Accuracy `A`: `(P + 0.75G + 0.25O) / hitCount` where `P`, `G`, `O` are
perfect/great/okay judgment counts (`REVERSE_SCORE_ENGINE.md` observable
table). These are hit-level counts, not stat-derived. v1 inverts
`A == 1` rows; under all-Perfect semantics `P = hitCount`, `G = O = 0`,
and `A = 1` independent of the loadout. **`A` is invariant under the
two-color collapse.**

This is the "Two-color collapse" invariant carried forward from handoff
§5.B and v1's record session 3.

### 1.3 Edge case: single-color chart

`SongOracle.song_colors` returns `(primary,)` when `secondary` is empty
or equal to primary (`reverse_score/oracle.py:93`):

```
@property
def song_colors(self) -> tuple[str, ...]:
    if self.secondary_color and self.secondary_color != self.primary_color:
        return (self.primary_color, self.secondary_color)
    return (self.primary_color,)
```

On a single-color chart the secondary-color axis does not exist; the
scorer's `secondary_val` reads `stats.get(secondary, 0)` where `secondary`
may be `""` (`extract_song_meta` default). Any stat mass in a non-primary
color dimension is therefore read as 0 by the scorer (the column is
absent), and `gear_power` uses the one-color branch `6*c1`. The collapse
`(c1, c2) → v` is not applied because there is no `c2` to collapse.

**Canonical rule:** on a single-color chart, the canonical key carries
`c1_stat` directly (not `v`), and any contribution to non-primary color
dimensions is handled by the off-color / invisible-stat fiber (§4). The
two-color fiber is only defined for charts where
`SongOracle.song_colors` has length 2.

### 1.4 Canonical key encoding

The two-color fiber is encoded in the canonical key as a single signed
integer `v_two_color`, the projected color mass:

```
v_two_color = 2 * stats[c1] + stats[c2]     # two-color chart
```

On a single-color chart the key carries `c1_stat` directly in the same
slot position; no `v` is formed. The fiber is identifiable in the key by
the chart's color arity, which the engine fixes per query (the canonical
key is computed against a known chart context).

### 1.5 Forward-oracle invariant check

The check is `assert_two_color_fiber_invariant` (named in code; the v2
engine MUST implement and call it). For every pair of physical loadouts
`L_a`, `L_b` with the same canonical key (hence the same `v`) but
different `(c1, c2)` split, the check forwards both through
`SongOracle.forward` and asserts:

```
assert forward(L_a) == forward(L_b)   # all four observables
```

A mismatch raises `FiberInvariantViolation("two_color", L_a, L_b,
obs_a, obs_b)`. This is the loud failure mode the §12 rule requires. The
check runs:

- In the K1.c CPU reference test suite, over a sampled set of `(c1, c2)`
  pairs that share `v` (sweep `c1` in `0..min(v//2, stat_max)`, set
  `c2 = v - 2*c1`, require `c2` in `[0, stat_max]`).
- In the production soundness gate, on every class member the engine
  materializes: the canonical scorer gate re-scores each witness; two
  witnesses sharing a key must produce identical observables.

The check is named in code as
`reverse_score_v2.fibers.assert_two_color_fiber_invariant` (target
location; the implementing agent owns the exact module path).

## 2. Upgrade-count fiber

### 2.1 Definition

Two placements of the same multiset of upgrade counts across the 6 gear
slots are one class member iff every observable is invariant to
piece-wise placement. The canonical key carries the aggregate count per
upgrade type, not the per-`(slot, type)` assignment.

Example: 3 Perfect Points upgrades on slot 1 + 2 on slot 2 vs 2 on slot 1
+ 3 on slot 2 → one class member, provided the invariant below holds.

### 2.2 Analysis: which upgrade types have piece-wise-invariant contribution

An `UpgradeDef` (v2 owner: `gear_optimizer.data.upgrades`, committed in
`d0c38be4`; v1 reference: `reverse_score/webport_extract.py:42`) is a
fixed stat pattern per upgrade type id. The v2 module also owns the
22-type pattern table and the constants `UPGRADES_PER_PIECE_MAX = 15` and
`UPGRADE_TOTAL_MAX = 90`:

```
@dataclass(frozen=True)
class UpgradeDef:
    upgrade_id: int
    stats: dict[str, int]
```

The composition path (v2 owner: `gear_optimizer.data.upgrades`; v1
reference: `reverse_score/domain.py:315`, `compose_stats`) sums upgrades
per-slot into a single global statsdict:

```
for slot in GEAR_SLOTS:
    ...
    for uid in loadout.upgrades.get(slot, ()):
        merge_stats(stats, tables.upgrades_by_id[uid].stats)
```

So the **stat contribution** of an upgrade unit is independent of which
slot it is placed on: `merge_stats` is commutative and associative, and
the upgrade's stat pattern is a property of the type, not the piece.

The only places slot-level structure could matter:

1. **Per-piece upgrade capacity (15).** The placement must be legal —
   `Loadout.validate` rejects `len(ids) > UPGRADES_PER_PIECE_MAX`. The
   fiber collapse is only over placements that fit the per-piece cap.
   Two illegal placements are not class members of anything; they are
   not in the domain. The aggregate-count representation preserves the
   legality check via `total_upgrades <= len(occupied) *
   UPGRADES_PER_PIECE_MAX` (`reverse_score/engine.py:993`), and the
   canonical placement in `_assemble_loadout` reconstructs a legal
   slot assignment (`engine.py:996`–`:1008`).
2. **Clamp behavior.** Stats clamp to `[-80, 160]` globally
   (`ExtendedGearStatCap160=true`). The clamp is applied to the total
   statsdict, not per-piece; an upgrade's contribution to a stat is the
   same regardless of which slot it is on, and the clamp sees only the
   total. So **clamp behavior is piece-wise-invariant.**
3. **Color projection.** `gear_power` and the scorer read the total
   `stats[c]` for each song color. Color projection is global, not
   per-piece. **Color projection is piece-wise-invariant.**
4. **Off-color side effects.** An upgrade that contributes to a non-song
   color contributes nothing to any observable (see §4). Moving it
   between slots does not change the total off-color mass, which was
   already invisible. **Off-color side effects are piece-wise-invariant
   (trivially, because they are invisible entirely).**

Therefore **every upgrade type has piece-wise-invariant contribution to
every observable**, and the aggregate-count collapse is sound for all 22
upgrade types, including the negative-stat variants (e.g. PerfectTime+ =
+1 PT / −1 PP): the −1 PP contribution is also a fixed per-type pattern
and is summed globally.

### 2.3 Canonical key encoding

The canonical key carries the upgrade counts as

```
upgrade_fiber = tuple(sorted((upgrade_id, total_count) for upgrade_id in upgrade_ids))
```

matching v1's `canonical_form` (`reverse_score/engine.py:2159`–`:2165`):

```
upgrade_counts: dict[int, int] = {}
for ids in loadout.upgrades.values():
    for uid in ids:
        upgrade_counts[uid] = upgrade_counts.get(uid, 0) + 1
...
tuple(sorted(upgrade_counts.items()))
```

The key is per-type, not per-`(slot, type)`. The implementing agent MUST
preserve v1's note (`engine.py:962`–`:967`): if a future game version
ships two upgrade ids with identical stat patterns, the fiber must
compare **pattern-level** counts (collapse by pattern, not by id). Until
then, per-id counts are correct because every id has a distinct pattern.

### 2.4 Forward-oracle invariant check

The check is `assert_upgrade_count_fiber_invariant` (named in code; v2
MUST implement and call it). For an aggregate-count vector `C` over
upgrade ids, the check samples two legal placements `P_a`, `P_b` (both
fitting per-piece caps), materializes both into physical loadouts, and
forwards each through `SongOracle.forward`:

```
assert forward(loadout_from_placement(P_a)) == forward(loadout_from_placement(P_b))
```

Empirical test protocol (the implementing agent runs this in K1.c):

1. Enumerate a representative set of aggregate-count vectors across the
   22 upgrade types (pattern table owned by
   `gear_optimizer.data.upgrades`), including negative-stat variants,
   with totals up to `6 * UPGRADES_PER_PIECE_MAX = 90`
   (`UPGRADE_TOTAL_MAX`, also owned by `gear_optimizer.data.upgrades`).
2. For each vector, generate ≥2 distinct legal placements (e.g. via the
   canonical assignment in `_assemble_loadout` and one permutation).
3. Forward-score each placement on a fixed chart through the canonical
   oracle.
4. Assert all placements of the same vector produce identical `(S, N, P,
   A)`. Any divergence raises `FiberInvariantViolation("upgrade_count",
   ...)`.
5. The check runs in the production soundness gate on every materialized
   class member: re-score every witness; witnesses sharing a key must
   produce identical observables. Upgrade materialization in v2 reads the
   `UpgradeDef` pattern table from `gear_optimizer.data.upgrades`.

## 3. Mini-identity fiber

### 3.1 Definition

Minis with identical stat contributions on the seed song but divergent
contributions on another song are **distinct** class members. The
canonical key carries the full mini identity tuple `(name, level, rank,
ascension)` per mini slot, sorted into a canonical order. Minis are NOT
collapsed by stat contribution alone.

### 3.2 Canonical key encoding

```
mini_fiber = tuple(sorted(
    (m.name, m.level, m.rank, m.ascension) for m in loadout.minis
))
```

matching v1's `canonical_form` (`engine.py:2166`). The sort order is
lexicographic on `(name, level, rank, ascension)`, which makes the key
slot-order-independent (minis are unordered in the loadout).

### 3.3 The persistence assumption

Mini **STATE** persists across songs: a player's equipped minis — name,
level, rank, ascension — are fixed across that player's leaderboard rows.
Mini **EFFECT** is song-specific. The v2 production owners span two
modules (both committed in `d0c38be4` unless noted):

- `gear_optimizer.data.mini_scaling` — PetUtils level/rank scaling and
  the PetInfo extractor. Exports `pet_stats_delta`, `pet_rank_to_max_level`,
  `pet_color_level_scale`, `extract_pet_info`, `PetDef`, and the constants
  `PET_MIN_LEVEL`, `PET_MAX_LEVEL`, `PET_RANK_TO_MAX_LEVEL`. This module
  produces the level/rank-scaled base/color mods that determine the
  ascension input row.
- `gear_optimizer.data.mini_ascension` (existing production) — ascension
  0..10 and song-target materialization. Exports
  `materialize_mini_for_song` (at v2 line 249),
  `mini_ascension_base_perfect_points_for_mini`, and
  `MINI_ASCENSION_MAX_LEVEL`. This module applies the `Song Target` list
  (`pet_song_targets`) to compute the ascension bonus.

`materialize_mini_for_song` takes `song_name`, `primary_color`,
`secondary_color` parameters and uses the mini's `Song Target` list
(`pet_song_targets`) to compute the ascension bonus. Two minis with the
same base/rank/level/ascension numbers but different `name` can have
identical stat contributions on one song (if their
`materialize_mini_for_song` outputs coincide) but different contributions
on another song (if their `Song Target` lists differ).

The fiber's distinctness proof (§3.4, §9.3) spans BOTH modules: the
level/rank-scaled base/color mods (from `gear_optimizer.data.mini_scaling`)
determine the ascension input row, and the ascension Song Target
application (from `gear_optimizer.data.mini_ascension`) produces the
song-specific stat contribution. The implementing agent must keep both
modules in mind when wiring the proof.

(v1 reference: `reverse_score/domain.py:255`, `mini_stats_delta`.)

**Why this means mini identity cannot be collapsed by stat contribution
alone:**

The multi-row filter (`reverse_score/identify.py`, `forward_matches` and
`run_filter`) keeps a loadout in the survivor set iff it reproduces every
row's observables. If the canonical key collapsed two minis `M_a`, `M_b`
that agree on the seed song's stat contribution but disagree on another
song, the filter would face this situation:

- The seed inversion returns one class member representing both `M_a` and
  `M_b`.
- The forward filter against the other song re-scores the class member
  (which expands to either `M_a` or `M_b` — the canonical key cannot
  distinguish).
- One of `M_a`, `M_b` fails the other song's observables; the other
  passes.
- The filter would eliminate the entire class member, losing the
  passing mini. This is a false negative: the true loadout is in the
  class, but the filter discards it because the collapse conflated it
  with a non-matching mini.

Handoff §12 fixes this: "They are distinct — the multi-row filter would
otherwise eliminate both when only one survives." The mini-identity fiber
is therefore NOT collapsed; the canonical key carries the full identity
tuple.

### 3.4 Forward-oracle invariant check

The multi-row filter itself is the check. The handoff §5.E rule
"canonical_form is song-independent; oracle.forward re-composes per song"
is the invariant: the canonical key must not collapse minis that the
forward oracle can distinguish on some song.

Concretely, the check is `assert_mini_identity_fiber_distinct` (named in
code; v2 MUST implement and call it). For two minis `M_a`, `M_b` with the
same stat contribution on the seed song:

1. Compose `stats(L with M_a)` and `stats(L with M_b)` on the seed song;
   assert they are equal (else the minis are already distinct in the key
   by stat contribution, and the check passes trivially).
2. For each chart in a song-diverse corpus (the K1.c corpus, including at
   least two songs with different `Song Target` lists for `M_a` and
   `M_b`), compose and forward-score both loadouts.
3. If any song's observables distinguish `M_a` from `M_b`, assert the
   canonical keys are distinct: `canonical_form(L_a) != canonical_form(L_b)`.
   A collision raises `FiberInvariantViolation("mini_identity", M_a, M_b,
   distinguishing_song)`.
4. In the production multi-row filter, a collapsed mini that fails another
   row's forward filter is itself a fiber violation: the engine MUST
   escalate to per-mini-identity expansion before discarding. (See §7.)

## 4. Off-color / invisible-stat fiber

### 4.1 Definition

`Perfect Time` and any off-color side-effect stat (a stat in a color
dimension not in `SongOracle.song_colors`) are invisible to all
observables by construction. Witnesses differing only there are one
class member. This is the v1 "Uniqueness" invariant
(`docs/Implementation Records/REVERSE_SCORE_ENGINE.md`,
"Uniqueness" section), carried forward unchanged.

### 4.2 Proof of invisibility

Trace each observable:

**Geared score `S`.** The exact scorer's per-row inputs
(`exact_rescore.py:480`, `_score_stat_inputs`) read exactly these keys
from the statsdict:

```
stats.get("Perfect Points", 0)        # pp_factor
stats.get("Combo Multiplier", 0)      # combo_mul
stats.get("Fever Multiplier", 0)      # fever_mul
stats.get(primary_color, 0)           # primary_val
stats.get(secondary_color, 0)         # secondary_val
stats.get("Fever Time", 0)            # ft_idx
stats.get("Fever Fill Rate", 0)       # ff_idx
```

No other stat key is read. `Perfect Time` is not in the list. An
off-color stat (a color not in `song_colors`) is not in the list because
`primary_color` and `secondary_color` are the only color keys read, and
they are exactly `SongOracle.song_colors`. Therefore `S` is insensitive
to `Perfect Time` and to any off-color stat.

**Naked score `N`.** Computed from the all-zero statsdict
(`reverse_score/oracle.py:111`):

```
self._naked_score = int(score_stats_exact({}, self.calc_song, self.ref_arrays))
```

No loadout stat enters; `N` is insensitive to every loadout stat,
trivially including `Perfect Time` and off-color stats.

**Gear power `P`.** `gear_power` (`reverse_score/game_model.py:225`)
computes:

```
p = 5 * Σ(stats.get(k, 0) for k in GEARPOWER_MAIN_KEYS)  # base part
if song_colors:
    colors = [c for c in song_colors if c]
    if len(colors) == 1:
        p += 6 * stats.get(colors[0], 0)
    elif len(colors) == 2:
        p += 4 * stats.get(colors[0], 0) + 2 * stats.get(colors[1], 0)
```

`GEARPOWER_MAIN_KEYS` is `(Perfect Points, Combo Multiplier, Fever
Multiplier, Fever Time, Fever Fill Rate)` — `Perfect Time` is excluded
(it is not a gear-power stat; see `game_model.py` constants). Color
weighting reads only `song_colors`; off-color stats are not in
`song_colors` and therefore contribute 0. So `P` is insensitive to
`Perfect Time` and to off-color stats.

**Accuracy `A`.** Judgment-count based, not stat-based; under all-Perfect
semantics `A = 1` independent of the loadout. Insensitive to every
loadout stat, trivially including `Perfect Time` and off-color stats.

Conclusion: `Perfect Time` and any off-color stat are invisible to all
four observables by construction. Two loadouts that differ only in those
stat dimensions are one class member.

### 4.3 Canonical key encoding

The canonical key carries only the **visible-stat projection** of the
loadout's total statsdict, in the order fixed by
`reverse_score/game_model.py:319` (`observable_projection`):

```
visible_stat_projection = (
    stats[c] for c in song_colors if c
) + (
    stats[k] for k in (Perfect Points, Combo Multiplier, Fever Multiplier, Fever Time, Fever Fill Rate)
)
```

On a two-color chart this is `(c1, c2, PP, CM, FM, FT, FF)`, which the
two-color fiber (§1) further collapses to `(v, PP, CM, FM, FT, FF)`. On
a single-color chart this is `(c1, PP, CM, FM, FT, FF)` with no further
collapse.

`Perfect Time` and off-color stats are not in the key. The key is
computed from the total statsdict; the loadout's `Perfect Time` and
off-color mass is discarded after composition.

### 4.4 Forward-oracle invariant check

No check is needed because the invisibility is by construction (the
scorer does not read those keys). The handoff §12 rule says: "the
soundness gate would catch any bug that made a stat visible." The
canonical scorer gate (handoff §5.A.3.e, §5.D) re-scores every materialized
witness through `score_stat_arrays_exact_batch` (now present in v2,
committed in `d0c38be4`, as the canonical array-native Vulkan
soundness-gate scorer; implemented as
`ir = build_exact_score_ir(...); return score_from_ir(ir, ...)`); if a
future code change made `Perfect Time` or an off-color stat visible, the
gate would score two witnesses in the same class differently and raise
`SoundnessGateMismatch`. The implementing agent MUST ensure the soundness
gate runs on every materialized class member; that is the off-color
fiber's check.

## 5. Canonical key — complete typed definition

```python
# v2 — typed definition. The brute-force class-equality gate hashes the
# returned tuple. Two physical loadouts are the same class member iff
# their canonical keys are equal.

def canonical_form(
    loadout: Loadout,
    *,
    song_colors: tuple[str, ...],  # SongOracle.song_colors, length 1 or 2
) -> tuple:
    """Placement-invariant, song-color-aware identity for class-equality.

    song_colors is part of the key context, not part of the loadout. The
    caller fixes it per query (the engine inverts one row at a time, so
    the chart's color arity is known). The key is only comparable across
    loadouts inverted against the same song_colors.
    """
    # Gear slot assignment — NOT placement-invariant (gear name per slot
    # matters; two different gear names in the same slot are different
    # class members even if their stats coincide, because gear identity
    # is part of the loadout the player actually equipped).
    gear_fiber = tuple(loadout.gear.get(slot) for slot in GEAR_SLOTS)

    # Upgrade-count fiber (§2): aggregate count per upgrade type id.
    upgrade_counts: dict[int, int] = {}
    for ids in loadout.upgrades.values():
        for uid in ids:
            upgrade_counts[uid] = upgrade_counts.get(uid, 0) + 1
    upgrade_fiber = tuple(sorted(upgrade_counts.items()))

    # Mini-identity fiber (§3): full identity tuple, sorted, not collapsed.
    mini_fiber = tuple(sorted(
        (m.name, m.level, m.rank, m.ascension) for m in loadout.minis
    ))

    # Gem allocation — not a fiber; the canonical key carries the full
    # GemAlloc because gem counts are already the unit of identity.
    gem_fiber = (
        loadout.gems.perfect_points,
        loadout.gems.combo_multiplier,
        loadout.gems.fever_multiplier,
        loadout.gems.fever_time,
        loadout.gems.fever_fill,
        loadout.gems.elemental,
        loadout.gems.selected_element,
    )

    # Team buff — not a fiber; (tier, color) is the unit of identity.
    buff_fiber = loadout.team_buff

    # Visible-stat projection (§4.3) — carries the off-color / invisible-
    # stat fiber (§4). Composed stats are needed because minis' ascension
    # bonuses depend on song_colors and song_name, so the projection is
    # song-aware. The two-color fiber (§1) collapses (c1, c2) -> v when
    # len(song_colors) == 2.
    #
    # The statsdict is computed by the caller and passed in, OR the key
    # carries the loadout and the projection is computed at hash time.
    # Either is acceptable; the typed definition below assumes the caller
    # provides the composed stats.
    return (
        gear_fiber,
        upgrade_fiber,
        mini_fiber,
        gem_fiber,
        buff_fiber,
        visible_stat_projection(loadout, song_colors),  # see §5.1 below
    )
```

### 5.1 `visible_stat_projection`

```
def visible_stat_projection(
    loadout: Loadout,
    song_colors: tuple[str, ...],
) -> tuple:
    stats = compose_stats(loadout, tables, song_name=..., primary_color=...,
                          secondary_color=...)
    if len(song_colors) == 2:
        c1, c2 = song_colors
        v = 2 * int(stats.get(c1, 0)) + int(stats.get(c2, 0))  # §1 two-color fiber
        color_part = (v,)
    elif len(song_colors) == 1:
        color_part = (int(stats.get(song_colors[0], 0)),)
    else:
        raise FiberError(f"song_colors must have length 1 or 2, got {song_colors!r}")
    main_part = tuple(
        int(stats.get(k, 0))
        for k in ("Perfect Points", "Combo Multiplier",
                  "Fever Multiplier", "Fever Time", "Fever Fill Rate")
    )
    return color_part + main_part
```

`Perfect Time` and any non-song-color stat are not in the projection
(§4.3).

### 5.2 Hashing and equality

Two `Loadout` instances are the same class member iff their canonical
keys are equal as Python tuples. The brute-force gate hashes the tuple
with `hash(key)`; collisions are resolved by `==`. The key is total and
deterministic given `loadout` and `song_colors`.

### 5.3 Song-context dependence

The key depends on `song_colors` (chart-level) and, through
`compose_stats`, on `song_name` / `primary_color` / `secondary_color`
(because mini ascension is song-target-specific — §3.3). Two loadouts
inverted against different charts produce keys that are NOT directly
comparable. The brute-force gate runs per-chart; cross-chart identity is
the multi-row filter's job (§7).

## 6. Identity-fiber expansion in rank/unrank (§5.A.3.e)

The rank/unrank materialization expands identity fibers deterministically
so the materialized output is independent of GPU completion order. For
each canonical key, the set of physical loadouts that map to it is
enumerated in sorted order.

### 6.1 Two-color fiber expansion

For a canonical key with `v_two_color = V` on a two-color chart, the
fiber expands to every `(c1, c2)` pair with `2*c1 + c2 == V`, `c1 >= 0`,
`c2 >= 0`, sorted lexicographically by `(c1, c2)`:

```
def expand_two_color(V, stat_max):
    out = []
    for c1 in range(0, min(V // 2, stat_max) + 1):
        c2 = V - 2 * c1
        if 0 <= c2 <= stat_max:
            out.append((c1, c2))
    return tuple(out)  # already sorted by c1 ascending, hence (c1, c2) lex
```

Each expanded pair is a distinct physical loadout (different stat
distributions across the two color dimensions). The rank/unrank step
assigns each a lexicographic rank within the fiber.

### 6.2 Upgrade-count fiber expansion

For a canonical key with `upgrade_fiber = ((uid_1, count_1), ...,
(uid_k, count_k))` and a fixed gear assignment `gear_fiber` (which
determines the occupied slots), the fiber expands to every legal
placement of the aggregate counts into the occupied slots, respecting
the per-piece cap `UPGRADES_PER_PIECE_MAX = 15`. The expansion is sorted
lexicographically by the per-slot id tuple.

Concretely, the canonical placement (`engine.py:996`–`:1008`) is one
specific member; the fiber expansion is the full set of legal placements
that produce the same aggregate counts. The expansion is generated by a
deterministic recursion: assign upgrade ids to occupied slots in slot
order, at each step choosing how many of the remaining count for each id
go to the current slot (bounded by the per-piece cap and the remaining
capacity), in sorted id order.

### 6.3 Mini-identity fiber expansion

The mini-identity fiber is NOT collapsed (§3). The expansion is trivial:
each canonical key maps to exactly one mini configuration (up to slot
permutation, which the sorted `(name, level, rank, ascension)` tuple
already factors out). The expansion assigns minis to the `MINI_SLOTS`
slots in the sorted order; slot permutations of the same sorted tuple
are the same physical loadout because the loadout model treats minis as
unordered (`domain.py:170` rejects duplicate names but does not order
them).

### 6.4 Off-color / invisible-stat fiber expansion

The off-color fiber is collapsed by discarding `Perfect Time` and
off-color stats from the key. The expansion is the set of all
`(Perfect Time, off-color stats)` values that are consistent with the
loadout's gear + upgrades + minis + gems + team buff. Because these
stats are invisible, the expansion is technically infinite (any value
works); in practice the engine enumerates only the values reachable
from the loadout's actual upgrade and gear choices, in sorted order.

The implementing agent MUST document the bounded enumeration: the
off-color mass in a physical loadout is determined by the gear and
upgrades chosen, so the fiber expansion is the set of loadouts that
share the visible-stat projection and differ only in their invisible
stat mass. The engine materializes one representative per fiber in the
ranked-materialization mode; the full expansion is enumerated in the
full-class mode.

### 6.5 Determinism

Every fiber expansion is sorted lexicographically. The rank/unrank step
assigns ranks `0..K-1` where `K` is the total class size after
expansion, and writes each result to its rank-defined location. The
output is independent of GPU workgroup completion order and atomic
append order, satisfying handoff §2.5.

## 7. Multi-row filter interaction (§5.E)

### 7.1 Song-independence of the canonical key

The canonical key is song-independent in the sense that the fiber
definitions (§1, §2, §4) do not depend on the chart. The mini-identity
fiber (§3) carries `(name, level, rank, ascension)`, which is
song-independent **state**. The visible-stat projection (§5.1) is
song-aware (mini ascension effect is song-specific), but it is computed
against the seed song's context, and the multi-row filter re-composes
per song via `oracle.forward`.

### 7.2 Per-row fiber expansion

Handoff §5.E: "The fiber expansion is per-row (the same canonical key
may expand to different physical loadouts on different songs if mini
song-target identity varies)." Concretely:

- The two-color fiber expansion (§6.1) is per-row only in that the
  chart's color arity fixes whether `v` or `c1` is in the key. For two
  two-color charts the expansion is the same.
- The upgrade-count fiber expansion (§6.2) is per-row only in that the
  gear assignment (which slots are occupied) is part of the key; for
  the same `gear_fiber`, the expansion is identical across rows.
- The mini-identity fiber expansion (§6.3) is per-row because mini
  ascension effect depends on `Song Target`, which varies by song. The
  **state** in the key is the same; the **stat contribution** when
  re-composed on another row may differ. The multi-row filter forwards
  the key's representative through `oracle.forward(row_b)` to check.

### 7.3 Class-level survival

A class member that survives one row's forward filter survives or fails
another row's filter **as a whole**. The filter does not split a class
member. If any expansion of a class member fails another row's
observables, the entire class member is eliminated — UNLESS the failure
isolates a mini-identity distinction, in which case the engine MUST
escalate to per-mini-identity expansion (§3.4) before discarding. This
is the §12 rule made operational: collapsing minis that the forward
oracle can distinguish on another row is a fiber violation, and the
engine recovers by re-expanding the mini-identity fiber.

### 7.4 The filter is the mini-identity fiber's check

The multi-row filter is the forward-oracle invariant check for the
mini-identity fiber (§3.4). A collapse that is wrong on another row
surfaces as a class member that fails the other row's forward filter
while one of its mini-identity variants would have passed. The engine
treats this as a fiber violation, re-expands, and re-filters. If the
re-expanded class still fails, the elimination is genuine (different
player, drifted chart).

## 8. Forward-oracle invariant checks — summary table

| Fiber | Check name | When it runs | Failure mode |
|---|---|---|---|
| Two-color (§1) | `assert_two_color_fiber_invariant` | K1.c test sweep; production soundness gate | `FiberInvariantViolation("two_color", ...)` |
| Upgrade-count (§2) | `assert_upgrade_count_fiber_invariant` | K1.c test sweep; production soundness gate | `FiberInvariantViolation("upgrade_count", ...)` |
| Mini-identity (§3) | `assert_mini_identity_fiber_distinct` + multi-row filter | K1.c corpus; production multi-row filter | `FiberInvariantViolation("mini_identity", ...)` |
| Off-color / invisible-stat (§4) | canonical scorer gate (`score_stat_arrays_exact_batch` re-score) | every materialized witness | `SoundnessGateMismatch` |

`score_stat_arrays_exact_batch` (the canonical array-native Vulkan
soundness-gate scorer named above) now exists in v2, committed in
`d0c38be4`, as a thin adapter over the new `ExactScoreIR` +
`score_from_ir`: implemented as
`ir = build_exact_score_ir(...); return score_from_ir(ir, ...)`. The
spec's references to it are valid. The upgrade-count fiber's
materialization reads the `UpgradeDef` pattern table from
`gear_optimizer.data.upgrades` (§2.2, §2.4). The mini-identity fiber's
distinctness proof spans `gear_optimizer.data.mini_scaling` and
`gear_optimizer.data.mini_ascension` (§3.3, §9.3).

## 9. Edge cases and non-trivial proofs

### 9.1 Two-color fiber: stat upper bound

The two-color fiber expansion (§6.1) requires a `stat_max` for the
`(c1, c2)` sweep. The natural bound is `STAT_CLAMP_HI = 160`
(`ExtendedGearStatCap160=true`), but color stats are not clamped in the
gear-power formula (`gear_power` reads raw `stats.get(c, 0)` and applies
no clamp). The scorer, however, reads `primary_val` and `secondary_val`
through `safe_int(stats.get(...), 0)` with no clamp in
`_score_stat_inputs`, but the downstream score arithmetic uses
`base_value = (primary_val * 2) + secondary_val + pp_factor` directly.
The implementing agent MUST verify whether color stats above 160 produce
distinct scores or saturate; if they saturate, the fiber's `stat_max` is
the saturation point. If they do not saturate, the fiber's `stat_max` is
the maximum reachable color stat from the domain (gear + upgrades +
minis + gems + team buff).

This is the non-trivial edge case for the two-color fiber: the
invariance proof in §1.2 holds for any `(c1, c2)` split of a fixed `v`
regardless of the bound, but the **expansion** must enumerate every
reachable `(c1, c2)` pair, and the reachable set depends on the clamp
behavior. The K1.c test sweep MUST include color stats above 160 to
verify the scorer does not distinguish splits at high color mass.

### 9.2 Upgrade-count fiber: future duplicate patterns

v1's note (`engine.py:962`–`:967`) flags this: today every upgrade id
has a distinct stat pattern, so per-id aggregate counts are correct.
If a future game version ships two ids with identical stat patterns,
the fiber must collapse by **pattern**, not by id. The implementing
agent MUST implement the check against `tables.upgrades_by_id` and
raise `FiberInvariantViolation("upgrade_count_duplicate_pattern", ...)`
if two ids with identical stat patterns are not collapsed. This is a
defensive check, not a current correctness issue.

### 9.3 Mini-identity fiber: ascension and Song Target

The mini-identity fiber's non-trivial case is the ascension bonus. The
v2 production owners span two modules (committed in `d0c38be4` unless
noted):

- `gear_optimizer.data.mini_scaling` owns PetUtils level/rank scaling and
  the PetInfo extractor (`pet_stats_delta`, `PetDef`,
  `pet_rank_to_max_level`, `pet_color_level_scale`, `extract_pet_info`,
  `PET_MIN_LEVEL`, `PET_MAX_LEVEL`, `PET_RANK_TO_MAX_LEVEL`). Its output
  is the level/rank-scaled base/color mod row fed into ascension.
- `gear_optimizer.data.mini_ascension` (existing production) owns
  ascension 0..10 and song-target materialization
  (`materialize_mini_for_song` at v2 line 249,
  `mini_ascension_base_perfect_points_for_mini`,
  `MINI_ASCENSION_MAX_LEVEL`).

`materialize_mini_for_song` uses the mini's `Song Target` list
(`pet_song_targets` from `Minis.csv`) to decide whether the ascension
bonus applies on a given song. Two minis with identical `(level, rank,
ascension)` and identical base/color mods but different `name` (hence
different `Song Target` lists) can have identical stat contributions
on one song and different contributions on another. The K1.c test
corpus MUST include at least one such pair, and the
`assert_mini_identity_fiber_distinct` check MUST verify the canonical
keys are distinct.

### 9.4 Off-color fiber: team buff color

A team buff of color `c_buff` not in `song_colors` contributes to an
off-color stat dimension. By §4.2 this is invisible. The canonical key
carries `team_buff = (tier, color)` as the buff's unit of identity, so
two team buffs of the same tier but different off-color are distinct
class members even though they are both invisible. The implementing
agent MUST verify this is the intended behavior: the team buff is part
of the loadout the player equipped, and even if its color contribution
is invisible on this song, the player's loadout identity includes it.
The off-color fiber collapses stat contributions, not team-buff
identity.

## 10. Implementation ownership

- The v2 `canonical_form` lives in `reverse_score_v2/canonical.py`
  (target path; the implementing agent owns the exact module name).
- The four `assert_*_fiber_*` checks live alongside it.
- The brute-force class-equality gate (`test_class_completeness_vs_brute`)
  imports `canonical_form` and hashes the returned tuple.
- The K1.c CPU reference test suite calls every `assert_*_fiber_*` check
  on a representative corpus before any production claim.

This document is the contract. The implementing agent MAY challenge any
assumption above with a measured or proved replacement, per handoff §0.