# Class-Equivalence Resolution — Reverse Score Engine v2

> Status: Binding amendment to `CANONICAL_FORM_SPEC.md`. Resolves the
> §16.4 class-equivalence contradiction (two-color collapse vs mini-identity
> distinctness under the §12 "indistinguishable on EVERY supported row"
> invariant) and specifies the §16.5 weighted recurrence
> `C(s) = Σ w(e)·C(s')`. No production code is changed by this document;
> it specifies the contract the v2 reverse search must satisfy.
>
> Scope: this document is normative for class identity, fiber weights, and
> multi-row filtering. Where it conflicts with `CANONICAL_FORM_SPEC.md`,
> this document governs. The four fiber types named in §12 (two-color,
> upgrade-count, mini-identity, off-color) are all addressed uniformly —
> no fiber type receives special treatment.

## 0. The contradiction

`CANONICAL_FORM_SPEC.md` carries two incompatible rules:

1. **§16.4 binding (handoff):** `canonical_form(a) == canonical_form(b) ⟺
   a and b are indistinguishable on EVERY supported row`.
2. **§12 rules (spec §1, §2, §4):** collapse two-color pairs and
   upgrade-count placements by stat contribution on the seed song;
   mini-identity stays distinct (spec §3).

The contradiction:

- A two-color pair `(c1, c2) ↔ (c1', c2')` with `2c1+c2 == 2c1'+c2'` is
  collapsed by spec §1 on the seed song. But the seed song's score is
  invariant under the split because `base_value = 2·primary + secondary +
  pp_factor` (see `exact_rescore.py:539`); gear power on a two-color
  chart is `P = 5·Σ(main) + 2·v` (see `game_model.py:225`). On ANOTHER
  two-color song with a DIFFERENT `(primary_color, secondary_color)`
  mapping, the SAME physical stat mass `c1, c2` (carried by the same
  loadout — gear name, upgrades, minis, gems, buff) lands in different
  color dimensions and produces a different `v`. The two-color collapse
  is therefore NOT globally invariant under song-color permutation.
- An upgrade-count aggregate vector `C` collapses placements (spec §2)
  because `merge_stats` is commutative/associative. That IS globally
  invariant — every song reads the same summed statsdict.
- An off-color stat is invisible to all four observables by construction
  (spec §4). That IS globally invariant — the scorer reads only
  `song_colors`.
- A mini identity `(name, level, rank, ascension)` is kept distinct
  (spec §3) precisely because `materialize_mini_for_song` is
  song-specific. That IS globally invariant by the explicit multi-row
  filter protocol (spec §7.4).

The contradiction is: §16.4 says "indistinguishable on EVERY supported
row," but spec §1 collapses two-color pairs that a later song-color
permutation can distinguish. Either the §16.4 invariant is wrong, or the
§1 collapse is wrong. They cannot both stand.

The companion contradiction from §15.9 step 6: "re-expand the 8
off-color upgrade count fibers at witness time" assumes off-color
upgrades are one class member during the search but distinct at
materialization. §12 says "invisible stats are one class member." Both
cannot be true under §16.4: if they are one class member, no expansion
is needed; if they must be expanded, they were never one class member.

## 1. The chosen resolution: persistent identities

**The reverse score engine v2 uses persistent identities.**

Every physical loadout the engine enumerates is a distinct class member.
The canonical key carries the FULL identity for every fiber type — no
collapse by stat contribution. The recurrence counts these identities
exactly, weighting each edge by the size of the identity fiber it
represents. K is the exact number of physical loadouts in the supported
domain, NOT a collapsed-state count.

### 1.1 Justification

The §16.4 invariant is binding and correct: a class member is a class
member iff it is indistinguishable on EVERY supported row. The §1
two-color collapse and the §15.9 "expand at witness time" rule both
violate §16.4. The two-color collapse is wrong because song-color
permutation distinguishes `(c1, c2)` splits; the off-color "expand at
witness time" rule is wrong because if off-color mass is one class
member it is one class member on every row, and if it must be expanded
it was never one class member on the seed row.

The other two options fail:

- **Globally identified** requires a forward-oracle invariance proof
  across EVERY supported row for every collapsed fiber. The two-color
  collapse fails this proof (a song-color permutation distinguishes
  splits). The off-color collapse passes (it is invisible by
  construction). Selecting globally identified forces a per-fiber-type
  choice: collapse off-color, keep two-color. That is special-casing,
  which the task forbids. Reject globally identified.
- **Symbolic fiber** changes the result type from a flat loadout list to
  a fiber-bearing class representation. That is a bigger API change than
  the engine needs: the production scorer gate, the brute-force
  `test_class_completeness_vs_brute`, and the multi-row filter all
  consume flat loadouts. Adopting symbolic fiber would force every
  downstream consumer to know about fibers. Reject symbolic fiber.

Persistent identities keeps the result type as a flat loadout list,
treats every physical loadout as one class member, and lets the
recurrence's fiber weights account for multiplicities. The four fiber
types collapse uniformly: NONE of them collapse identity; the weight
on each edge is the count of identities the edge represents. The
multi-row filter operates on flat loadouts and needs no special
expansion protocol — every loadout is already materialized.

### 1.2 Why this is uniform

Under persistent identities:

- The two-color fiber does NOT collapse `(c1, c2)` splits. Each
  physical `(c1, c2)` reachable from the domain is a distinct class
  member. The edge weight is 1 (one identity).
- The upgrade-count fiber does NOT collapse placements. Each legal
  per-slot placement is a distinct class member. The edge weight is the
  number of legal placements of the aggregate count vector into the
  occupied slots (a combinatorial count, computed at axis-build time).
- The mini-identity fiber does NOT collapse. Each `(name, level, rank,
  ascension)` state is a distinct class member. The edge weight is 1.
- The off-color fiber does NOT collapse. Each physical stat distribution
  (including `Perfect Time` and off-color mass) is a distinct class
  member. The edge weight is 1.

Every fiber type carries the full identity. No fiber type collapses.
The recurrence's edge weight encodes the multiplicity of identical
contribution vectors (the `Axis.identity_fibers` grouping the DomainIR
already produces), but the class identity is the full physical loadout,
not the collapsed contribution vector.

This is the only resolution that does not special-case any fiber type.

## 2. The persistent-identity materialization plan

### 2.1 The class identity

The class identity is the FULL physical loadout. The canonical key
carries every piece of identity the engine enumerated:

```
canonical_form(loadout, *, song_colors) -> (
    gear_fiber,            # gear name per slot (NOT collapsed)
    upgrade_fiber,         # per-(slot, type) placement (NOT aggregate count)
    mini_fiber,            # (name, level, rank, ascension) per mini slot
    gem_fiber,             # full GemAlloc
    buff_fiber,            # (tier, color)
    stat_projection,       # the 7-dim visible stat vector
)
```

Differences from `CANONICAL_FORM_SPEC.md` §5:

- `upgrade_fiber` is the per-`(slot, type)` placement (sorted), NOT the
  aggregate count. This is the breaking change. The aggregate-count
  collapse (spec §2) is removed.
- The visible-stat projection is still carried (it is the seed-song
  forward oracle's input), but it is NOT the identity — it is a
  derived quantity. Two loadouts with the same identity necessarily
  share the projection; two loadouts with the same projection need NOT
  share the identity.
- The two-color `v = 2c1+c2` collapse is REMOVED. The key carries the
  full `(c1, c2)` (or `c1` on single-color) in the projection, AND the
  projection is NOT the identity, so even if two physical loadouts
  share `v` they are distinct class members.

The brute-force gate hashes the canonical key. Two physical loadouts
are the same class member iff their keys are equal as Python tuples.

### 2.2 How the fiber weight enters the subtree count

The recurrence uses the DomainIR's `identity_fibers` as the weighted
edge set. For each `Axis`, `identity_fibers` groups options with
identical 7-dim contribution vectors. The search tree's edges are these
fibers, not the raw options:

```
For axis a with options O = (o_1, ..., o_m) and identity_fibers
F = (f_1, ..., f_k) where each f_j is a tuple of options with identical
contribution vector v_j:

  weight(f_j) = |f_j|  (the number of identities in the fiber)
  contribution(f_j) = v_j
```

The recurrence at axis `a` over the suffix `a+1..end`:

```
C(s) = Σ over fibers f of axis a:
         weight(f) * C(s + contribution(f))
```

The weight multiplies the subtree count BEFORE the subtree is
materialized. The fiber multiplicity is in the count, not added after.
This is the §16.5 binding.

Two fibers of the same axis are distinct edges (they have different
contribution vectors). One fiber's options are one weighted edge with
multiplicity = `|f|`. The recurrence descends through fibers, not
options; rank/unrank expands the fiber into its `|f|` member options
at materialization time.

### 2.3 Materialization at rank/unrank time

To unrank index `r` at state `s` over the suffix starting at axis `a`:

1. Compute `C(s, a) = Σ over fibers f of axis a: weight(f) * C(s +
   contribution(f), a+1)`.
2. Walk the fibers of axis `a` in canonical order. For each fiber `f`
   with child state `s' = s + contribution(f)`:
   - Let `span_f = weight(f) * C(s', a+1)`.
   - If `r < span_f`: the unranked identity is in this fiber.
     - Within the fiber, the index splits as `(fiber_index, sub_index)`
       where `fiber_index ∈ [0, weight(f))` selects the member option
       and `sub_index ∈ [0, C(s', a+1))` selects the subtree position.
       The member options are sorted lexicographically by label; pick
       option `o_{fiber_index}` from the fiber.
     - Recurse with `r = sub_index` and `s'` at axis `a+1`.
   - Else: `r -= span_f` and continue.
3. At a terminal state (`a == len(axes)`), `C(s) = 1` and the unranked
   identity is empty (the loadout is fully determined).

The rank operation is the inverse: given a full loadout, project each
axis choice to its fiber and member index, accumulate the weighted
offsets, and return the total index.

The materialization is deterministic because:
- The fibers are in canonical (first-appearance) order.
- The member options within a fiber are sorted lexicographically by
  label.
- The subtree indices are in the canonical axis order.

This satisfies the §5.A.3.e determinism requirement (output independent
of GPU completion order).

### 2.4 K is the exact physical loadout count

K, the root state count, equals the number of physical loadouts in the
supported domain. Under persistent identities, K is computed by the
weighted recurrence and is NOT inflated after the fact. The fiber
weights are the multiplicities; multiplying them through the recurrence
produces the exact count directly.

For research (capacity detection), K saturates at `MAX_K + 1`: the
recurrence caps each `C(s, a)` at `MAX_K + 1` and reports saturation.
For production, K is computed exactly over the full supported range.

## 3. The updated four fiber rules

All four fiber rules are stated under the §16.4 invariant. The unit
of class identity is the physical loadout. No fiber collapses identity.

### 3.1 Two-color fiber

**Rule.** On a two-color chart with `song_colors = (c1, c2)`, the
canonical key carries the full `(c1_stat, c2_stat)` pair in the
visible-stat projection. The fiber weight over `(c1_stat, c2_stat)`
splits is 1 per split — each physical `(c1_stat, c2_stat)` reachable
from the domain is a distinct class member. The two-color collapse
`v = 2c1 + c2` is NOT applied to identity.

The visible-stat projection still records `v` for forward-oracle
consultation (the seed-song scorer reads `v`), but `v` is derived, not
identity.

**Invariance.** Holds trivially under persistent identities: no
collapse, no invariance to prove. The forward-oracle invariant check
`assert_two_color_fiber_invariant` is retired (it asserted collapse
soundness; collapse is no longer performed).

**Multi-row.** A later song with a different `(primary_color,
secondary_color)` reads the same physical stat mass in different color
dimensions. Because identity is the full `(c1_stat, c2_stat)` pair, the
multi-row filter sees the same set of physical loadouts on every row;
no collapse to undo.

### 3.2 Upgrade-count fiber

**Rule.** The canonical key carries the per-`(slot, type)` placement,
sorted by slot then by upgrade id. The fiber weight is the number of
legal placements of the aggregate count vector into the occupied slots
that produce the same contribution vector. Each legal placement is a
distinct class member; the recurrence's edge weight is the count of
placements sharing the contribution vector.

**Invariance.** Holds by the §2.2 proof (merge_stats is
commutative/associative; the scorer reads the summed statsdict). The
forward-oracle invariant check
`assert_upgrade_count_fiber_invariant` is preserved — it verifies the
contribution-vector equivalence that justifies the fiber weight.

**Multi-row.** All placements sharing a contribution vector share it on
every row (the summed statsdict is song-independent). The multi-row
filter sees one representative per fiber; if the representative passes,
every member of the fiber passes. The fiber weight correctly multiplies
the subtree count.

### 3.3 Mini-identity fiber

**Rule.** The canonical key carries the full `(name, level, rank,
ascension)` tuple per mini slot, sorted into canonical order. The
fiber weight is 1 — each mini state is a distinct class member. This
matches `CANONICAL_FORM_SPEC.md` §3 unchanged.

**Invariance.** Holds by the multi-row filter protocol (spec §7.4): a
mini that distinguishes on another song is distinct in the key, so the
multi-row filter sees it as a distinct loadout from the start.

**Multi-row.** Each mini identity is its own class member; the multi-row
filter forwards each one. No escalation needed.

### 3.4 Off-color / invisible-stat fiber

**Rule.** The canonical key carries the full physical stat distribution,
including `Perfect Time` and off-color stat mass. The fiber weight is 1
per physical loadout — each distinct stat distribution is a distinct
class member.

The visible-stat projection drops `Perfect Time` and off-color mass
(scorer invisibility, spec §4.2), but the projection is NOT identity.
Two loadouts sharing a projection but differing in `Perfect Time` or
off-color mass are distinct class members.

**Invariance.** Holds trivially: no collapse, no invariance to prove.
The forward-oracle invariant check (canonical scorer gate re-score) is
preserved as a soundness gate on every materialized witness.

**Multi-row.** Each physical stat distribution is its own class member.
The §15.9 step 6 "re-expand the 8 off-color upgrade count fibers at
witness time" rule is RETIRED — there is nothing to re-expand. Every
off-color upgrade count was a distinct class member throughout the
search.

### 3.5 Summary table

| Fiber | Identity in key | Fiber weight | Forward-oracle check | Multi-row |
|---|---|---|---|---|
| Two-color (§3.1) | full `(c1, c2)` pair | 1 per split | retired (no collapse) | flat filter |
| Upgrade-count (§3.2) | per-`(slot, type)` placement | count of legal placements sharing contribution vector | preserved | flat filter |
| Mini-identity (§3.3) | `(name, level, rank, ascension)` | 1 | preserved (multi-row filter) | flat filter |
| Off-color (§3.4) | full stat distribution | 1 | preserved (soundness gate) | flat filter |

## 4. The multi-row protocol

Under persistent identities, the multi-row filter is a flat filter
over flat loadouts. There is no per-class-member expansion because every
class member IS a physical loadout.

### 4.1 The protocol

Given a seed row `R_0` with `song_colors_0` and a list of additional
rows `R_1, ..., R_n` with their `song_colors_i`:

1. The seed inversion enumerates every physical loadout `L` in the
   supported domain (via the weighted recurrence's rank/unrank), and
   keeps those whose forward-score on `R_0` matches the seed's
   observables. Every loadout is a distinct class member.
2. For each subsequent row `R_i`:
   - For each surviving loadout `L`:
     - Re-compose `L`'s statsdict against `R_i`'s song context (mini
       ascension is song-specific via `materialize_mini_for_song`).
     - Forward-score the recomposed loadout through
       `score_stat_arrays_exact_batch` (the canonical array-native
       scorer).
     - Keep `L` iff its observables match `R_i`'s recorded values.
3. The final survivor set is the engine's output.

### 4.2 Why this satisfies §16.4

A class member is a class member on every row. Under persistent
identities, the class member IS the physical loadout. The multi-row
filter never collapses or expands; it filters the same flat set on
every row. The §16.4 invariant is satisfied by construction.

### 4.3 The cost

The cost is the loss of the two-color and off-color collapses. The
DomainIR's `identity_fibers` grouping still collapses the SEARCH state
space (the recurrence descends through fibers, not options), so the
recurrence's K computation is still fast — but the materialized output
is the full physical set, not a collapsed representative set.

The upgrade-count fiber's weight (the legal-placement count) keeps the
search tree's branching factor low while materializing every legal
placement at rank/unrank time. The two-color and off-color fibers have
weight 1 per identity; their search state does not collapse, but the
contribution vectors are still grouped (the search visits one fiber
state per unique contribution vector, but the weight multiplies the
subtree count by the number of identities sharing that vector).

### 4.4 What is NOT done

- The engine does NOT make one forward call per collapsed class member
  and then re-expand. Every loadout is its own class member; the filter
  forwards each one.
- The engine does NOT escalate to per-mini-identity expansion (spec
  §7.3). Minis are distinct from the start.
- The engine does NOT re-expand off-color upgrade count fibers at
  witness time (§15.9 step 6). Off-color counts are distinct from the
  start.

## 5. Compatibility with the DomainIR

The DomainIR's `Axis.identity_fibers` already groups options with
identical contribution vectors. Under persistent identities:

- The recurrence descends through `identity_fibers` (one edge per
  fiber), weighting by `|f|`.
- The rank/unrank step expands a fiber into its `|f|` member options at
  materialization time.
- The canonical key carries the FULL option label (the identity), not
  just the contribution vector.

No change to `domain_ir.py` is required. The `Axis.identity_fibers`
field is the fiber weight source the recurrence reads. The
`AxisOption.label` field is the identity the canonical key carries.

The DomainIR's two-color behavior: on a two-color chart, the gem
elemental axis enumerates `(color, count)` per song color. The color
stat mass in the projection is the raw `(c1, c2)` — the DomainIR does
not collapse to `v`. The DomainIR already supports persistent
identities; the spec §1 collapse was an additional layer the engine
applied on top. Under this resolution, that layer is removed.

## 6. The weighted recurrence — specification

### 6.1 The recurrence

Let the DomainIR have axes `A_0, ..., A_{n-1}` with `identity_fibers`
`F_i = (f_{i,1}, ..., f_{i,k_i})` per axis. Let `s` be the accumulated
contribution vector (7-dim int32). Define:

```
C(s, i) = 0                                   if i == n and not terminal(s)
        = 1                                   if i == n and terminal(s)
        = Σ over f in F_i: |f| * C(s + vec(f), i+1)   otherwise
```

where `vec(f)` is the shared contribution vector of fiber `f`'s
options, `|f|` is the fiber weight (the number of options in `f`), and
`terminal(s)` is the predicate that accepts `s` (e.g. `s @ pw ==
p_target` for the gear-power-constrained inversion).

The root count is `K = C(0, 0)` (starting from the zero contribution
vector at axis 0). K is the exact number of physical loadouts in the
supported domain that satisfy the terminal predicate.

### 6.2 Saturating counts

For research, `C(s, i)` is capped at `MAX_K + 1`:

```
def cap(x):
    return min(x, MAX_K + 1)
```

applied at every recursive call. If the root K equals `MAX_K + 1`, the
domain is saturated (capacity detected); the engine does not
materialize. For production, the cap is not applied; K is exact.

### 6.3 Rank/unrank through weighted intervals

To unrank index `r ∈ [0, K)` at state `(s, i)`:

```
def unrank(r, s, i):
    if i == n:
        return ()  # terminal: loadout fully determined
    offset = 0
    for f in F_i (in canonical order):
        s_child = s + vec(f)
        if not feasible(s_child, i+1):
            continue
        span = |f| * C(s_child, i+1)
        if r < offset + span:
            within = r - offset
            fiber_index = within // C(s_child, i+1)
            sub_index  = within % C(s_child, i+1)
            option = f[fiber_index]  # sorted member option
            return (option,) + unrank(sub_index, s_child, i+1)
        offset += span
    raise IndexError(f"r={r} out of range at state {(s, i)}")
```

Rank is the inverse: given a loadout (one option per axis), project
each option to its fiber and member index, and accumulate the weighted
offsets.

### 6.4 The feasibility predicate

The recurrence prunes infeasible subtrees. For the gear-power-constrained
inversion, a state `(s, i)` is feasible iff:

```
s @ pw + suffix_min[i] <= p_target <= s @ pw + suffix_max[i]
```

where `suffix_min[i]` and `suffix_max[i]` are the precomputed suffix
bounds on the gear-power contribution (see `domain_ir.py:683`,
`_compute_suffix_bounds`). Infeasible subtrees contribute 0 to `C(s,
i)` and are not enumerated by rank/unrank.

For the unconstrained reference (the synthetic CPU test below), the
predicate is constant-true: every terminal state is feasible and K is
the full option product.

## 7. Edge cases

### 7.1 Single-color charts

On a single-color chart, the two-color fiber is not applicable. The
DomainIR's `song_colors` has length 1; the color stat mass is `c1`
only; the fiber weight is 1 per `c1` value (each `c1` is one class
member).

### 7.2 Empty axes

An axis with one option (the zero option) has one fiber of weight 1.
The recurrence descends through it without branching.

### 7.3 Saturation overflow

For research, `C(s, i)` is capped at `MAX_K + 1` (see §6.2). The cap
must be applied at EVERY recursive return, not just the root, to
prevent integer overflow on large domains.

### 7.4 Zero-K domains

If `K == 0`, the domain is empty (no loadout satisfies the terminal
predicate). The engine reports the empty set. The rank/unrank loop
runs zero iterations.

## 8. Implementation ownership

- The weighted recurrence lives in `reverse_score_v2/weighted_recurrence.py`.
- The CPU reference implementation is in the same module.
- The test is `tests/test_weighted_recurrence.py`.
- The canonical scorer gate (soundness check on materialized
  witnesses) calls `score_stat_arrays_exact_batch` from
  `gear_optimizer.solver.scoring.exact_rescore`.

This document is the contract. The implementing agent MAY challenge any
assumption above with a measured or proved replacement, per handoff §0.