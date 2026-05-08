# Boundary-Flip Regime Proofs (Analytical HitSim Q1)

Goal: identify **exact** (not heuristic) regimes where the full interval DP for Analytical HitSim’s boundary flips
collapses to something simpler (often the shipped greedy/ceiling-style decision), and prove those collapses.

This is intentionally scoped to the **boundary-flip objective**: the only way hit timing matters is by moving notes
in/out of fever at window boundaries; everything else is timing-independent.

Related spec:

- `docs/ANALYTICAL_HITSIM_PROBLEM.md` (problem definition)
- `docs/ANALYTICAL_HITSIM_SOLUTION.md` (interval DP, greedy discussion, and sufficient conditions)

---

## 0. Minimal model and notation

We work in the repo’s chord-group / carry formulation (see `docs/ANALYTICAL_HITSIM_SOLUTION.md`).

- Chord groups are indexed by `g = 0..G-1`.
- Each group has an integer-ms chart time `c_g`.
- Each group has a feasible **carry** range `[l_g, u_g] ⊆ ℤ` (derived from note type windows and held-tail rules).
- Let `Δ_g = c_g - c_{g-1} ≥ 1` for `g ≥ 1`.
- Carry transition from group `g-1` to `g` is (exactly):

  `r_g ∈ A_g(r_{g-1})`, where

  - if `r_{g-1} - Δ_g ≤ u_g`: then `r_g ∈ [max(l_g, r_{g-1} - Δ_g), u_g]`,
  - else (forced-forward snap): `r_g = r_{g-1} - Δ_g`.

For a fever window activated at note index `a` in group `s = group(a)` with activation carry `r_s`, define the
integer-ms discretized duration

`d = ceil(D_ms)`

and the fever threshold

`Q = c_s + r_s + d`.

A later group `g` is in fever iff `c_g + r_g < Q`. Equivalently, it is out of fever iff `c_g + r_g ≥ Q`.

Let `w_i ≥ 0` be the per-note fever bonus (“fever score minus non-fever score”). For this doc, the objective is:

`maximize sum_{i in fever} w_i`.

(This covers both pure “maximize fever note count” in the body region and the true weighted objective with head ramp.)

---

## 1. The exact interval DP (context only)

The full exact Q1 solver is a DAG DP over fever activations (see `docs/ANALYTICAL_HITSIM_SOLUTION.md`):

- State `x` includes at least `(a, r_s)` (activation note index + activation carry).
- Feasible actions correspond to feasible fever-end chord groups (and an implied next activation index).
- The Bellman form is:

  `V(x) = max_{j ∈ J(x)} [ R_x(j) + V(next(x, j)) ]`,

  where:
  - `J(x)` is the set of feasible fever-end indices from state `x`,
  - `R_x(j) = sum_{i=a}^{j-1} w_i` is the immediate fever gain in that window.

The “greedy ceiling” style decision replaces the max by “choose `j` that maximizes `R_x(j)`” (latest feasible end).

The sections below give regimes where that greedy replacement is **provably exact** (or the problem becomes
deterministic, so greedy vs DP is irrelevant).

---

## 2. Regime A: Zero-swing (no boundary flips) ⇒ deterministic timeline

### Definition (union swing band)

For a fixed activation group `s` and discretized duration `d`, the activation carry satisfies

`r_s ∈ [-40, 80]` (global bound; see `docs/ANALYTICAL_HITSIM_SOLUTION.md`).

So `Q` ranges over:

`Q ∈ [c_s + d - 40, c_s + d + 80]`.

For a fixed `Q`, the “swing” chart-time zone (where fever membership depends on carries) is:

`c_g ∈ [Q - 80, Q + 40)`.

Therefore, *for that activation group*, the union of possible swing zones across all feasible activation carries is:

`c_g ∈ [c_s + d - 120, c_s + d + 120)`.    (A 240ms band.)

Call this the **union swing band** for `(s, d)`.

### Theorem A (zero-swing determinism)

Fix a fever activation group `s` and `d`. Suppose **no chord group base time** lies in the union swing band:

`{ g : c_g ∈ [c_s + d - 120, c_s + d + 120) } = ∅`.

Then, for every feasible hit-timing assignment (every feasible carry path), the fever window end group is the same.
Equivalently, the fever mask for that window is **identical** for all feasible hit timings: there is no boundary flip.

### Proof

Let `Q` be the threshold realized by some feasible activation carry; by the carry bounds, `Q` lies in
`[c_s + d - 40, c_s + d + 80]`.

For any later group `g`, fever membership depends on whether `c_g + r_g < Q` with `r_g ∈ [-40, 80]`. As in the
standard band argument:

- If `c_g < Q - 80`, then even at the largest carry `r_g = 80` we have `c_g + r_g < Q`, so group `g` is always in fever.
- If `c_g ≥ Q + 40`, then even at the smallest carry `r_g = -40` we have `c_g + r_g ≥ Q`, so group `g` is always out.

The only chart times for which fever membership can vary with carries are `c_g ∈ [Q - 80, Q + 40)`.

But by hypothesis there are **no** chord groups whose base times fall in the union of these swing intervals over all
feasible `Q`. Hence, for the realized `Q` as well, there are no groups in the swing interval `[Q - 80, Q + 40)`.

So every group is either always-in or always-out, making the first out-of-fever group (and thus the fever-end index)
unique and independent of the timing assignment. ∎

### Practical consequence

This is a true “regime proof” in the strongest sense: **if the union swing band is empty, the Q1 exact DP is
unnecessary** (every algorithm—MC, greedy ceiling, full DP—must return the same fever mask).

It also yields an exact, cheap precheck: a binary search on `c_g` around `[c_s + d - 120, c_s + d + 120)`.

---

## 3. Regime B: Singleton boundary ⇒ greedy = DP (trivial exactness)

### Theorem B (singleton boundary)

At a DP state `x`, if `|J(x)| = 1` (there is only one feasible fever-end index), then the greedy decision is exact at
`x` and `V(x)` is determined without needing any optimization.

### Proof

If there is only one feasible action, the max is over a singleton set, so the greedy choice equals the DP optimum. ∎

---

## 4. Regime C: Dominance gap ⇒ greedy is exact (Bellman dominance)

This is the most useful “nontrivial” regime: it certifies greedy optimality from a **local** inequality plus a
**global bound** on what the cascade could possibly do in the future.

### Setup

At state `x`, define:

- `R_x(j)` immediate gain for choosing fever-end index `j`,
- `C_x(j) = V(next(x, j))` continuation value after that choice,
- `J(x)` feasible fever-end indices.

Let greedy choose:

`j* ∈ argmax_{j ∈ J(x)} R_x(j)`.

Define the **future swing set** `U(x)` as any superset of all notes whose fever membership might still vary in any
future window reachable after state `x` (under any feasible timing assignments).

Let the **future swing weight bound** be:

`B(x) = sum_{i ∈ U(x)} w_i`.

This is finite and depends only on chart structure + the current window’s position (and the `w_i` weights).

### Lemma C1 (continuation difference is bounded by future swing weight)

For any `j1, j2 ∈ J(x)`:

`|C_x(j1) - C_x(j2)| ≤ B(x)`.

### Proof

All `w_i` are nonnegative. The only way future decisions can change the total score is by changing which notes land in
fever at the boundaries. By definition, any note not in `U(x)` has fixed fever membership across *all* future reachable
states, so its contribution cancels when comparing two policies. Therefore the maximum possible difference in total
future fever gain between any two feasible continuation policies is achieved by flipping every note in `U(x)` from
out-of-fever to in-fever (or vice versa), giving an absolute difference at most `sum_{i∈U(x)} w_i = B(x)`. ∎

### Theorem C (dominance gap ⇒ greedy exact at a state)

If greedy’s immediate advantage dominates the future bound:

`R_x(j*) - R_x(j) ≥ B(x)` for all `j ∈ J(x)`,

then greedy is exact at `x`:

`V(x) = R_x(j*) + C_x(j*)`.

### Proof

Fix any feasible `j`. By Lemma C1,

`C_x(j) - C_x(j*) ≤ |C_x(j) - C_x(j*)| ≤ B(x)`.

So:

`[R_x(j*) + C_x(j*)] - [R_x(j) + C_x(j)]`

`= (R_x(j*) - R_x(j)) - (C_x(j) - C_x(j*))`

`≥ B(x) - B(x) = 0`.

Therefore `j*` attains the maximum in the Bellman equation. ∎

### Practical consequence

This theorem is useful because:

- it does **not** require solving the full DP to prove greedy at a state,
- it gives a concrete “regime predicate”: if you can compute a tight enough `B(x)`, you can certify greedy exactness.

Computing the *minimal* `U(x)` is as hard as solving the DP, but conservative choices are cheap:

- `U(x) ⊆` “all notes in any future window’s union swing band,”
- or even coarser `U(x) ⊆ {i : i ≥ a}` (suffix bound, usually too loose).

---

## 5. What this means for “can we reduce more?”

If you want **unconditional exactness** for boundary flips, the interval DP is essentially the end of the road.
However, Theorems A/B/C show you can often replace the DP by:

1) **a precheck** proving there are no boundary flips (Regime A), or
2) **a certification bound** proving the greedy decision is exact at relevant states (Regime C),
3) and only run full DP when neither certificate triggers.

That is the “regime proof” path to keeping the computation incredibly fast while staying mathematically honest.

