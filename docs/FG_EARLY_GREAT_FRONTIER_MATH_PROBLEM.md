# Force-Greats Early-Great Frontier — Self-Contained Mathematical Problem

> [!NOTE]
> This document freezes a research formulation for independent algorithm work.
> It is not a description of the current production module layout or runtime
> strategy.

**Audience:** algorithms / optimization / combinatorics people. No domain knowledge of the
game or the codebase is required; everything needed is below. The goal is an **exact,
polynomial-time** algorithm (or an impossibility proof + best achievable) for the
optimization in §6, exploiting the structure in §8.

---

## 0. One-paragraph statement

We have a sequential decision process ("a play") over `N` ordered items (musical notes).
A play partitions the items into alternating *non-fever* and *fever* segments and labels
some items *great*. Each play induces a **feature vector** `S` (a 200-bit head mask plus
3 integer body counts). A play's **value** is `score(S; θ)`, an explicitly-given,
piecewise-linear-with-integer-floors function of a parameter vector `θ`. For a fixed
instance we must compute `max over feasible plays of score(S; θ)` **for every `θ` in a
given finite grid `Θ`**, exactly. The naïve method — enumerate the Pareto set of feature
vectors `S` once (independent of `θ`), then score each against every `θ` — is the
baseline formulation studied here; the "early-Great extension" in §5
makes that Pareto set **exponential** in the number of segments. We want a method whose
cost is polynomial in `N` and `|Θ|`. §8 gives strong structural hints (the value function
decomposes into a position-sensitive 100-element *head* and a position-flat *body*).

---

## 1. Givens (the instance)

- `N ∈ ℤ_{>0}`: number of items, indexed `0 … N−1`.
- `t[0] ≤ t[1] ≤ … ≤ t[N−1]`, integers (item times in **milliseconds**, nondecreasing).
- `type[i] ∈ {1, 2}` for each `i`: `1` = normal, `2` = "wide" (call these **wide items**).
  A wide item doubles its timing offsets (below). Let `μ[i] = 1` if `type[i]=1`, `μ[i]=2`
  if `type[i]=2`.
- A finite set `Θ` of parameter vectors. Each `θ ∈ Θ` is
  `θ = (v, c, f, γ)` with reals
  - `v > 0` — "base value",
  - `c ≥ 1` — "combo multiplier",
  - `f ≥ 1` — "fever multiplier",
  - `γ` with `0 < γ ≤ v` — "great base" (a penalized version of `v`).
- A finite set `Γ` of **geometries**. Each geometry `g = (β, ρ, R)`:
  - `ρ > 0` real ("raw fill"), `β = ⌈ρ⌉ ∈ ℤ_{≥0}` ("fill base"),
  - `R ∈ ℤ_{≥0}` ("fever duration", milliseconds).
  (`Θ` and `Γ` come from a separate "stat grid"; for this problem they are just given finite
  sets. Typical sizes: `|Γ|` up to a few thousand distinct `(β,R)`; `|Θ|` up to ~10⁴. In the
  real system `θ` and `g` are weakly coupled, but you may treat them as independent — solving
  the fully-independent version is sufficient and is the hard core.)

**Fixed global constants** (these are concrete numbers; nothing hidden):

| window | lower offset `Lᵒ` (ms) | upper offset `Uᵒ` (ms) |
|--------|------------------------|------------------------|
| Perfect | `−20` | `+40` |
| Great   | `−75` | `+190` |

(Wide items multiply both offsets by `μ[i]=2`, e.g. Perfect window `[−40,+80]`. The `+190`
Great-upper is the value used by the production envelope; see Remark R1.)

Great-base point constant `P = 150`.

---

## 2. Derived monotone envelopes (precompute, `O(N)`)

All are integer sequences of length `N`. Define per-item offsets
`Lᴾ[i] = −20·μ[i]`, `Uᴾ[i] = +40·μ[i]`, `Lᴳ[i] = −75·μ[i]`, `Uᴳ[i] = +190·μ[i]`.

- **Perfect-candidate** (latest perfect hit time of item `i`):  `pc[i] = t[i] + Uᴾ[i]`.
- **Great-candidate** (latest great hit time of item `i`):     `gc[i] = t[i] + Uᴳ[i]`.
- **Perfect-floor** (earliest perfect hit, made monotone):
  `pf[i] = max_{j ≤ i} ( t[j] + Lᴾ[j] )`   (prefix-maximum ⇒ nondecreasing).
- **Great-floor** (earliest great hit, made monotone):
  `gf[i] = max_{j ≤ i} ( t[j] + Lᴳ[j] )`    (prefix-maximum ⇒ nondecreasing).

Because `Lᴳ[j] ≤ Lᴾ[j]` pointwise, **`gf[i] ≤ pf[i]` for all `i`** (key inequality).

For a real cutoff time `C` define two boundary indices via binary search on these monotone
arrays:
```
EP(C) = min { e ∈ {0..N} : pf[e] ≥ C }     (treat pf[N] = +∞)   — "perfect end"
EG(C) = min { e ∈ {0..N} : gf[e] ≥ C }     (treat gf[N] = +∞)   — "great end"
```
Since `gf ≤ pf` pointwise, `EG(C) ≥ EP(C)` always.

*(Interpretation, not needed to solve: an item `e` is reachable into the fever segment iff
its earliest legal hit precedes the cutoff `C`. With perfect hits the boundary is `EP(C)`;
allowing wider "great" hits extends it to `EG(C) ≥ EP(C)`. The extra items `[EP(C), EG(C))`
can only be in fever **as greats**.)*

---

## 3. Feasible plays (the constraint structure)

A **play** is built left-to-right by a sequence of **segments** `s = 1, 2, …`, maintaining a
cursor `i` (next unprocessed item), starting at `i = 0`. Fix a geometry `g=(β,ρ,R)`.
Each segment makes the following choices and advances the cursor:

**(a) Forced-great count.** Choose `k ∈ {0, 1, …, β}`.

**(b) Fill length (determined by `k`).**
```
base = β − [s = 1]                         (clamp base ← max(0, base))
fill = ⌈ ρ + 0.5·k ⌉ − [s = 1]             (the non-fever fill length)
a    = min( i + fill , N )                 (activation index)
```
Items `[i, a)` are **non-fever**. Among them, the first `kʹ = min(k, a−i)` items starting at
`fs = i + [s ≠ 1]` (i.e. `fs=i` for the first segment, else `fs=i+1`) are **non-fever
greats**; the rest are non-fever normals.

**(c) Termination.** If `a ≥ N`: the play ends; items `[i, N)` are non-fever (with the great
labels from (b)). No fever segment is produced.

**(d) Activation time / mode.** Otherwise (`a < N`) choose an *activation mode*
`m ∈ {perfect, lateGreat}` (the `lateGreat` mode is optional — only available when `k>0`
context permits; you may also always allow it, it never helps unless it strictly extends the
cutoff). Define the **start time**
```
carry   = max{ gc[j] : j ∈ [fs, fs+kʹ) }   (or −∞ if kʹ=0)     -- "forced-great carry"
start   = pc[a]                                                 -- perfect activation
if m = lateGreat:  start = max( pc[a], gc[a] )   and item a becomes a fever-AND-great item
else:              start = max( pc[a], carry )
C       = start + R                                              -- fever cutoff time
```
**(e) Fever end (the early-Great extension — the crux).** Let
`eP = EP(C)`, `eG = EG(C)` (so `a < eP ≤ eG`, after clamping `eP ← max(eP, a+1)`,
`eG ← max(eG, a+1)`, both `≤ N`). Choose
```
e ∈ { eP, eP+1, …, eG }.
```
Items `[a, e)` are the **fever** items. Of these, items `[a, eP)` are fever (and not forced
to be great), while items **`[eP, e)` are fever-AND-great** (the "early-Great tail"). If
`m=lateGreat`, item `a` is additionally great.

**(f) Advance.** Set `i ← e` and continue with segment `s+1`.

A play is any finite sequence of such segments ending via (c). (Existence: choosing
`k=0, m=perfect, e=eP` every segment always yields a valid play.)

---

## 4. The feature vector `S` induced by a play

Let head index set `H = {0,…,min(N,100)−1}` and body index set `B = {100,…,N−1}`
(`B = ∅` if `N ≤ 100`). From a play, aggregate over all its segments:

- `Fev` = set of all fever items (union of all `[a, e)`),
- `Grt` = set of all great items = (all non-fever greats from (b)) ∪ (all early-Great tails
  `[eP,e)`) ∪ (all `lateGreat` activation items `a`).

By construction `Grt ∩ Fev` = (early-Great tails) ∪ (lateGreat activations); non-fever greats
are in `Grt \ Fev`.

The **feature vector** is
```
S = ( Fev ∩ H ,  Grt ∩ H ,  b_f ,  b_g ,  b_fg )
where  b_f  = |Fev ∩ B|          (body fever count)
       b_g  = |Grt ∩ B|          (body great count)
       b_fg = |Fev ∩ Grt ∩ B|    (body fever-and-great count)
```
i.e. the head is kept as **exact per-position 0/1 masks** (two 100-bit vectors), the body is
kept only as **three integer counts**. (`|H| ≤ 100`, so the masks are ≤100 bits each.)

This compression — exact head, counts-only body — is forced by the value function (§5):
head value is position-dependent, body value is position-independent.

---

## 5. The value function `score(S; θ)` (exact, with all floors)

Fix `θ = (v, c, f, γ)`. Let `⌊·⌋` be floor. Precompute scalars
```
cv = ⌊ v·c ⌋                 (combo value, per body normal item)
fv = ⌊ v·c·f ⌋               (fever value, per body fever item)
pnp = max(0, cv − ⌊ γ·c ⌋ )         (body normal-great penalty)
pfp = max(0, fv − ⌊ γ·c·f ⌋ )       (body fever-great penalty)
```
Body total `Bcnt = max(0, N − 100)`. With `b_f, b_g, b_fg` from `S` and
`b_ng = b_g − b_fg` (body normal-greats), `b_nf = Bcnt − b_f` (body normals):

**Body contribution**
```
score_body =  b_f·fv  +  b_nf·cv  −  b_ng·pnp  −  b_fg·pfp
```

**Head contribution.** For each head index `i ∈ H` let
`σ_i = 1 + (c−1)·(i+1)/100` (the per-position "scaling", affine increasing in `i`), and
`p_i = v·σ_i`, `q_i = γ·σ_i`. Define the per-item score
```
if i ∈ Fev:   base_i = ⌊ p_i · f ⌋ ;   gr_i = ⌊ q_i · f ⌋
else:         base_i = ⌊ p_i ⌋ ;       gr_i = ⌊ q_i ⌋
h_i = base_i − ( [ i ∈ Grt ] · max(0, base_i − gr_i) )
```
(If `i` is great, it scores `min(base_i, gr_i) = gr_i` since `γ ≤ v`; else `base_i`.)
```
score_head = Σ_{i ∈ H} h_i
```

**Total**  `score(S; θ) = score_body + score_head`.

`γ` itself is a given component of `θ`. (In the real system `γ = 2p+P` for a "single-color"
song or `⌊4p/3⌋ + ⌊2s/3⌋ + P` for two colors, where `p,s` are color-stat values also feeding
`v = 2p + s + pp`; you may treat `γ` and `v` as an arbitrary given pair with `0<γ≤v`.)

---

## 6. The computational problem

For the fixed instance (§1) we must compute, **for each geometry `g ∈ Γ` and each parameter
`θ ∈ Θ`,**
```
OPT(g, θ) = max over feasible plays of geometry g  of  score( S(play) ; θ ).
```

**Performance requirement.** The dominating cost in production is *building*, for each
geometry `g`, a representation that can then be scored against all `θ ∈ Θ`. Today this is a
"frontier" `𝓕_g` = the Pareto set of feature vectors `S` reachable under `g`, after which
`OPT(g,θ) = max_{S ∈ 𝓕_g} score(S;θ)` is a cheap vectorized sweep. **We need the per-geometry
build to stay polynomial in `N`** (it was `≈ O(N²)`/a few thousand vectors before the §3(e)
extension was added). Concretely: **do not enumerate anything of size `2^{(#segments)}`.**

**Correctness requirement.** Bit-exact: equal to the brute force over all feasible plays
(which is finite). A reference brute force and small test instances are in §10.

So the deliverable is **one** of:
1. An algorithm computing all `OPT(g,θ)` in `poly(N, |Γ|, |Θ|)` time, **or**
2. A proof that the per-geometry optimal-vector set can be exponential for *all* scoring of
   `Θ` (i.e. that no small geometry-only representation exists) **plus** the best achievable
   (e.g. a `poly(N)·|Θ|` per-`θ` algorithm that avoids the blowup).

---

## 7. Why the obvious approach blows up

Fix `g`. Build the frontier `𝓕_g` (Pareto-undominated feature vectors). Dominance: `S`
dominates `S'` if `Fev⊇Fev'`, `Grt⊆Grt'` (fewer greats is weakly better — greats only ever
*subtract*), `b_f≥b_f'`, `b_g≤b_g'`, `b_fg≤b_fg'`. Before §3(e), every segment had a single
forced end `e=eP`, and `|𝓕_g|` stayed small (`≈2·10³` on real instances). With §3(e), each
segment independently chooses `e ∈ {eP,…,eG}`; extending segment `s` by `Δ_s = e−eP` **shifts
every later segment's start index by `Δ_s`** (the consumed items no longer fill the next bar
⇒ later activations move). The choices **cascade**, so the number of reachable plays — and of
*pairwise-incomparable* feature vectors — grows like `∏_s (1+Δ_s^{max})`. Measured on a
dense instance with `N=80`: `|𝓕_g|` jumps from `2,008` (extension off) to `319,699`
(extension on), and these are **all distinct, none dominated** (they trade more fever for
more great penalty). So the blowup is *real Pareto growth*, not a dedup bug. It makes the
build and the score sweep both explode and violates the performance requirement.

---

## 8. Structure to exploit (this is where a reduction should live)

These are proven/measured properties of the exact functions above.

**(S1) Head/body value split.** `score = score_head(Fev∩H, Grt∩H; θ) + score_body(b_f,b_g,b_fg; θ)`.
`score_body` depends on the body **only through the 3 counts** (no position term):
`b_f·fv + b_nf·cv − b_ng·pnp − b_fg·pfp`.

**(S2) The body is position-flat ⇒ body extensions are cascade-neutral and bounded.**
Every body item contributes the *same* value for its label class (`fv`, `cv`, or a fixed
penalty). Consequence: extending a fever segment whose end lies in `B` by `Δ` body items has
the **constant** marginal effect "`Δ` items move from non-fever-normal to fever-great"
(`+Δ·(fv − cv) − Δ·pfp` … per the §5 body formula), and the downstream index shift only
relabels equal-valued body items. Hence over the body the reachable `(b_f, b_g, b_fg)` triples
form a **bounded** set (an integer Pareto set in a box `[0,Bcnt]³`), and the §3(e) extension
does **not** blow up the body — the explosion in §7 is entirely within the head. (Empirically:
the `319,699` head-masks collapse to **175** distinct `(|Fev∩H|, |Grt∩H|)` count-classes; the
multiplicity is purely *which* head positions, i.e. the position-sensitive head value.)

**(S3) The head is affine-in-position.** `σ_i = 1 + (c−1)(i+1)/100` is increasing affine in
`i`; later head items are worth (weakly) more. `|H| ≤ 100` regardless of `N`.

**(S4) Greats only subtract, monotonically.** For any `i`, `gr_i ≤ base_i` and the great
penalty `base_i − gr_i ≥ 0`; on the body, `pnp, pfp ≥ 0`. So labeling an item great is never
beneficial *except* when it is the price of moving an item into fever (the §3(e) tradeoff:
`+` fever multiplier, `−` great penalty).

**(S5) Parametric / linear structure.** Ignoring the integer floors, `score(S;θ)` is **linear
in `(v, vf, γ, γf, …)`** — the per-item contributions are products of `θ`-scalars with
`{0,1}` indicators. The set of feature vectors that are optimal for *some* `θ` is therefore an
**upper envelope** (a parametric-optimization / linear-programming object); its combinatorial
complexity is governed by the number of distinct `θ`-regions, which for a constant number of
effective parameters is typically polynomial — *far* smaller than the full Pareto set in §7.
The floors perturb this but are bounded (each floor moves a value by `<1`).

**(S6) Per-segment extension is small and local.** `Δ_s^{max} = eG−eP ≤ ⌈ (Uᴾ−Lᴳ window
width) / (min item gap) ⌉`; since `Lᴾ−Lᴳ = 55` ms (normal) / `110` ms (wide), `Δ_s^{max}` is
`0` for most segments and a small constant elsewhere.

**(S7) A per-`(g,θ)` DP is already polynomial.** For a *single* fixed `θ`, `OPT(g,θ)` is a
shortest/longest-path DP on a DAG with one node per cursor index `i ∈ {0..N}`: from `i`,
edges to `e` for each `(k, m, e)` choice in §3, with additive edge weight = the exact score of
the items the segment fixes (computable in `O(1)` with prefix sums for the body and an
`O(100)` head term). This is `O(N · (β+1) · Δ^{max})` per `(g,θ)`. The open issue is doing all
`|Θ|` parameters without re-running an `N`-DP per `θ`, *and/or* compiling a small
geometry-only object as the production design wants.

---

## 9. The questions to answer

1. **Main:** Give an algorithm for §6 that is `poly(N,|Γ|,|Θ|)` and exact. Equivalently:
   produce, per geometry, a representation of size `poly(N)` sufficient to recover `OPT(g,θ)`
   for every `θ`, **or** show the per-`θ` DP (S7) can be batched/accelerated across `Θ` to the
   same bound.
2. **Envelope size:** Is the *upper-envelope* feature-vector set (those optimal for some
   `θ∈Θ`, S5) of polynomial size in `N`? If yes, can it be constructed without first
   enumerating the exponential Pareto set (S7-style parametric DP / Megiddo-style search)?
3. **Decomposition:** Can (S1)/(S2) be turned into a clean reduction — solve the **body**
   exactly with a bounded count-DP (it already is bounded), and solve the **head** (a fixed
   ≤100-item, affine-weight subproblem with the §3 segment constraints) by a *separate*
   bounded method (e.g. a per-`θ` head DP of size `O(100·Δ^{max})`, or a parametric head
   envelope), then combine across the single head/body boundary crossing at index `100`?
   The crossing couples them through one shared cursor value — how tight is that coupling?
4. **Monotonicity:** Does the optimal total extension `Σ_s Δ_s` (and the per-segment `Δ_s`)
   vary **monotonically** along a one-dimensional sweep of an effective parameter (e.g. the
   "fever premium" `f·γ/v`)? If a total order on `Θ` makes all optima nested, the envelope is
   a chain of length `O(N)` and the build is easy. Identify the largest parameter family for
   which monotonicity holds, and a counterexample for where it fails (the great penalty `γ`
   and combo `c` enter too, so it is likely ≥2-parameter).
5. **Floors:** Do the integer floors in §5 ever change the optimal feature vector relative to
   the floor-free (purely linear) problem? Bound the discrepancy, or show floors can be folded
   into the parametric analysis (they are piecewise-constant corrections of magnitude `<1`).

A positive answer to (3) is the production team's preferred outcome: keep the **bounded** body
in the compiled per-geometry frontier, and handle the **≤100-item head** exactly by a cheap
secondary pass — because that matches the existing architecture and provably cannot blow up.

---

## 10. Reference brute force + test instances (for checking any proposed method)

**Brute force (exponential, exact — the ground truth).** Enumerate all feasible plays by
recursion on the cursor `i` and the choices `(k,m,e)` of §3; for each play form `S` (§4) and
evaluate `score(S;θ)` (§5); take the max. Memoize on `i` only to enumerate *distinct* feature
vectors, but the value max itself is over all plays. For `N ≤ ~14` this is directly runnable.

**Micro-instance (exhibits the early-Great gain).** A single fever segment, items in ms:
`t = [0,100,200,400,600,800,1000,1290,1600]`, all `type=1`, geometry chosen so the only
activation is at index `a=2` with `R=1000`. Then `start = pc[2] = 200+40 = 240`,
`C = 240+1000 = 1240`. Perfect-floor boundary `eP = EP(1240) = 7` (items `2..6` in fever:
item 7 at `t=1290` has `pf[7]=1290−20=1270 ≥ 1240`, excluded). Great-floor boundary
`eG = EG(1240) = 8` (item 7 has `gf[7]=1290−75=1215 < 1240`, included **as a great**). So the
extension adds exactly one fever-great item (index 7) over the perfect-only end. Verify any
method reproduces: perfect end count `=5` items, great-extended end `=6` items, the added item
is great-only (its earliest perfect hit `1270 ≥ 1240`, its earliest great hit `1215 < 1240`).

**Tradeoff witness (shows intermediate ends matter; ⇒ you cannot just take `e=eG`).** With
head index `i≈40`, `v=900, c=2`, single-color `γ=2·300+150=750`: a boundary item scored as
**great-in-fever** beats **perfect-not-in-fever** when `f=3.0` (`⌊⌊γσ⌋f⌋ > ⌊vσ⌋`) but **loses**
when `f=1.05`. So for some `θ` the optimum extends a given segment and for others it does not;
across `Θ` every `e ∈ {eP,…,eG}` can be the unique optimum ⇒ a correct method must consider
all of them (this is exactly what makes §6 a parametric problem, not a single optimization).

**Blow-up instance (stress).** `N=80`, `t[i] = 40·i` ms (uniform 40 ms), all `type=1`, any
geometry with `β≈3, R≈300`: extension-off frontier `=2,008` vectors; extension-on `=319,699`
vectors, all distinct, `175` distinct head count-classes. A good method must handle this in
`poly(N)` (it has `N<100`, so it is *all head* — the worst case for the head subproblem).

---

## 11. Glossary ↔ production code (for engineers verifying against the implementation)

| symbol / term | code location |
|---|---|
| `pf`, `gf`, `pc`, `gc` envelopes | `gear_optimizer/solver/timing_envelope.py` (`build_perfect_floor_envelope_sec`, `build_great_floor_envelope_sec`, `build_perfect_candidate_envelope_sec`, `build_great_candidate_envelope_sec`) |
| `EP`, `EG`, fever-end search | `searchsorted(pf/gf, cutoff)` in `response_build_gpu_precompute.py::_precompute_end_indices` |
| play / segment DP, frontier build | `response_build_gpu_numba.py::_first_frontier_from_precomputed_end_indices_numba` |
| §3(e) early-Great extension (the new, blowing-up code) | `_numba_packet_queue_push_activation`, the head loop, `_numba_pack_edge_eg` in the same file |
| feature vector `S` | `FgResponseSurface` (`response_types.py`): `fever0..3`, `great0..3` (head bitmasks, 4×32 bits), `body_fever`, `body_great`, `body_fever_great` |
| `score(S;θ)` | `gear_optimizer/solver/scoring/exact_rescore.py::score_force_greats_response_surface_exact` |
| timeline / forced-greats / fill | `gear_optimizer/solver/fever_timeline.py::calculate_force_greats_timeline_indices`; constants `0.333, 0.15, 0.15`, great base `+150` in `fg_policy.py::compute_great_penalty_base` |

**Remark R1 (a separate, secondary correctness item — not part of the math problem).** The
production Great-upper offset is `+190` ms (`Uᴳ`), whereas the game's decompiled Great window
upper at the modeled stat tier is `+150` ms. This only affects the `lateGreat` activation
start `gc[a]` in §3(d); it does not change the structure of the problem. Use whichever value;
the algorithmic question is identical. (The early-Great *lower* edge `−75` ms, which drives
`gf` and the whole §3(e) extension, is confirmed correct.)

---

## 12. Success criteria

A solution is accepted if it (a) matches the §10 brute force bit-for-bit on all small
instances including the tradeoff witness, (b) handles the §10 blow-up instance and real
instances (`N` up to ~3000) with per-geometry build cost no worse than a small polynomial in
`N` (no `2^{#segments}` factor, no `>10⁵` vectors), and (c) computes `OPT(g,θ)` for all
`θ∈Θ` within the same asymptotic budget as the pre-extension system times a `poly`-factor.
