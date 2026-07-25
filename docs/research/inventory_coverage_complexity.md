# Inventory Coverage: Complexity, Reductions, and Optimality

**Date:** April 26, 2026  
**Status:** Formal Analysis

> [!NOTE]
> This is a standalone inventory-coverage model preserved as a research
> artifact. Names used in examples and reductions are not current
> RoBeats Calculator Engine runtime APIs.

## 1. Problem Statement (Formal)

### 1.1 Data

| Symbol | Definition |
|--------|-----------|
| $S$ | Set of songs, $|S| = n$ |
| $G$ | Set of gear types, $|G| = m$ |
| $\Omega$ | Universe of variants: all feasible gem distributions. Each $\omega = (g, o)$ where $g \in G$ and offset $o$ encodes a gem 6-vector with $\|o\|_1 = 15$. |
| $|\Omega| = m \cdot 62\,016$ | Enumerated in `variant_space.py` |
| $T_s \in \mathbb{Z}_{\ge 0}^6$ | Target gem totals for song $s$, $\|T_s\|_1 = 90$ |
| $g_{s,1},\ldots,g_{s,6} \in G$ | Required gear types for song $s$ (from peak candidate) |
| $e_s \in \{1,\ldots,5\}$ | Element color required by song $s$ |
| $K$ | Inventory cap (cardinality budget) |

### 1.2 Feasibility

A variant $\omega = (g, o)$ is **feasible** for song $s$ at slot $j$ iff:
- $g = g_{s,j}$ (correct gear type), AND
- $\text{color}(o) \in \{0, e_s\}$ (wildcard or matching element)

For song $s$, a **pattern** $p = (\omega_1, \ldots, \omega_6)$ is **feasible** iff each $\omega_j$ is feasible for slot $j$, AND

$$\sum_{j=1}^6 \text{vec}(\omega_j) = T_s$$

where $\text{vec}(\omega)$ is the gem 6-vector (PP, CM, FM, FT, FF, OV) encoded by the variant's offset.

### 1.3 Decision Problem (IC-DECIDE)

**Input:** $S, G, \{T_s\}, \{g_{s,j}\}, \{e_s\}, K$  
**Question:** Does there exist a set $I \subseteq \Omega$ with $|I| \le K$ such that for every song $s \in S$, there exists a feasible pattern using only variants from $I$?

### 1.4 Optimization Problem (IC-OPT)

Maximize the number of songs $s$ for which a feasible pattern exists using at most $K$ variants from $\Omega$.

---

## 2. NP-Completeness

### Theorem 1
**IC-DECIDE is NP-complete.**

#### Proof: reduction from SUBSET-SUM.

Given a SUBSET-SUM instance: integers $a_1, \ldots, a_n \ge 0$ and target $B$.

Construct an IC instance:
- **One gear type:** $G = \{G_0\}$, so $m = 1$.
- **One song:** $S = \{s^*\}$ with all 6 slots requiring $G_0$.
- **Target totals:** $T_{s^*} = (B,\; 90-B,\; 0,\; 0,\; 0,\; 0)$ — only PP and CM dimensions are non-zero.
- **Element:** $e_{s^*} = 1$ (arbitrary, all variants wildcard).
- **Budget:** $K = 6$.

For each integer $a_i$, create a variant $\omega_i = (G_0, o_i)$ where:
- $\text{vec}(\omega_i) = (a_i,\; 15-a_i,\; 0,\; 0,\; 0,\; 0)$  
  (all 15 gems split between PP and CM only)
- $\text{color}(\omega_i) = 0$ (wildcard)

Additionally, create five dummy variants $\omega_{\text{dummy}} = (G_0, o_{\text{dummy}})$ with $\text{vec} = (0,0,0,0,0,15)$ and color $=0$. These contribute nothing to PP/CM.

Now: song $s^*$ can be covered with 6 variants iff there exists a selection from $\{\omega_i\}$ whose PP components sum to $B$ and whose CM components sum to $90-B$. Since each $\omega_i$ has PP+CM = 15, any 6 variants sum to 90. The PP sum equals $B$ iff exactly those $\omega_i$ with matching $a_i$ are selected — which is equivalent to selecting a subset of $\{a_i\}$ summing to $B$ (padding with dummy variants to reach exactly 6).

Thus SUBSET-SUM reduces to IC-DECIDE. Since SUBSET-SUM is NP-complete and the IC solution can be verified in polynomial time (check $|I| \le K$ and test each song's pattern feasibility against $I$), **IC-DECIDE is NP-complete.** ∎

### Corollary 1
**IC-OPT is NP-hard.** No polynomial-time algorithm can find the globally optimal inventory unless P = NP.

---

## 3. Structural Decomposition

### 3.1 Per-Gear Independence Under Fixed Budget Allocation

Let $k_g$ be the number of variants allocated to gear type $g$, with $\sum_g k_g = K$.

**Observation:** If the allocation $\{k_g\}$ is fixed AND the cross-gear sum constraint is removed, the problem decomposes into $m$ independent subproblems (one per gear type), each solvable as a max-coverage problem on that gear's songs.

**However**, the cross-gear sum constraint couples the subproblems: the offset chosen for gear $g_1$ in song $s$ restricts which offsets are admissible for gear $g_2$ (and all other gears) in the same song. This coupling is the **sole source of hardness beyond standard Max Coverage**.

### 3.2 The Sum Constraint as a 6-Dimensional Linear Equation

For song $s$, the constraint

$$\sum_{j=1}^6 \text{vec}(\omega_j) = T_s$$

is a system of 6 linear Diophantine equations in 36 unknowns (6 variants × 6 dimensions each), with each variant $\omega_j$ restricted to the feasible subset for its gear type.

Because each gear has exactly 15 gems per variant, and each song needs exactly 90 gems, the constraint space is a **6-dimensional transportation polytope** restricted to a 6-simplex per variant.

### Theorem 2 (Fixed-Parameter Tractability for Verification)
For a **fixed** inventory $I$ with $|I| = K$, checking whether all $n$ songs are covered takes $O(n \cdot \bar{v}^6)$ time, where $\bar{v} = \max_g |I \cap \Omega_g|$. With $K=100$ and $m=50$, $\bar{v} \approx 2$, giving roughly $2^6 = 64$ checks per song.

**Proof:** For each song $s$, enumerate all 6-tuples from the inventory variants on the song's 6 required gear types. Sum the vectors and compare to $T_s$. Each gear type contributes at most $\bar{v}$ candidates, giving $\le \bar{v}^6$ combinations per song. ∎

This is exponential only in the constant 6 (number of gear slots), making verification fast in practice.

### 3.3 Elemental Separation

The OV (elemental) dimension has special structure: OV gems on a variant must all share a single color (by construction of the variant space), and that color must either match the song's element $e_s$ or be 0 (wildcard).

**Lemma 1 (Color Separability):** For a song $s$ with element $e_s$, the OV gems used to reach OV target $t_{\text{ov}}$ must come entirely from variants whose color is either $e_s$ or 0. No variant with a different color can contribute valid OV gems.

This means the OV dimension constraint is: $\sum_{j=1}^6 \text{ov}(\omega_j) = t_{\text{ov}}$ with $\text{color}(\omega_j) \in \{0, e_s\}$. The other 5 stat dimensions (PP, CM, FM, FT, FF) have no color restriction.

---

## 4. Lossless Reduction Analysis

### 4.1 Can IC be reduced to a simpler problem class in P?

**Theorem 3:** No lossless reduction from IC to any problem class in P exists (unless P = NP).

**Proof:** Immediate from Theorem 1 (NP-completeness). Any polynomial-time reduction from an NP-complete problem to a problem in P would imply P = NP. ∎

### 4.2 Can IC be reduced to a simpler NP-complete problem?

The question is whether IC can be **losslessly** restated as a standard combinatorial problem (e.g., Set Cover, Max Coverage, ILP) with no increase in problem size.

#### Reduction A: To Maximum Coverage (lossy)

If we pre-select exactly ONE pattern per song (the "best" witness pool pattern), IC becomes:

> Given $n$ sets $P_1, \ldots, P_n$ where each $P_s$ is a set of 6 variants, and budget $K$, choose $K$ variants to maximize the number of sets fully contained.

This is the **Hitting Set / Max Coverage** problem on a hypergraph where each edge (song) requires all 6 vertices. This is NP-complete and has the standard $(1-1/e)$ greedy approximation.

**Lossiness:** By fixing one pattern per song, we discard alternative patterns that might enable better cross-song variant reuse. In IC, a song can be covered by ANY feasible pattern from the witness pool. This reduction loses information.

#### Reduction B: To Integer Linear Programming (lossless)

**Theorem 4:** IC-OPT can be losslessly reduced to an integer linear program with $O(nK_w + |\Omega_{\text{witness}}|)$ variables and $O(nK_w + |\Omega_{\text{witness}}|)$ constraints, where $K_w$ is the number of witness patterns per song and $\Omega_{\text{witness}}$ is the set of variants appearing in any witness pattern.

**Proof (construction):**

Let $P_s$ be the set of witness patterns for song $s$, with $|P_s| = K_w$. Each pattern $p = (\omega_{s,1}^p, \ldots, \omega_{s,6}^p)$.

Variables:
- $x_{s,p} \in \{0,1\}$ — song $s$ uses pattern $p$
- $z_v \in \{0,1\}$ — variant $v$ is in the inventory
- $y_s \in \{0,1\}$ — song $s$ is covered

Constraints:
1. $\sum_p x_{s,p} = y_s \quad \forall s$ (exactly one pattern if covered)
2. $x_{s,p} \le z_v \quad \forall (s,p,v)$ where variant $v$ appears in pattern $p$ of song $s$
3. $\sum_v z_v \le K$ (budget)

Objective: $\max \sum_s y_s$

This ILP is lossless **within the witness pool universe** (i.e., it finds the optimal assignment restricted to witness pool patterns). Adding more witness patterns makes it approach losslessness for the full problem. The ILP has $O(nK_w + V)$ variables and $O(nK_w \cdot 6)$ constraints, which is compact when $K_w$ is modest.

**Practicality:** For $n = 500$, $K_w = 128$, $V \approx 100\text{K}$: the ILP has ~164K boolean variables and ~384K constraints. CP-SAT solves this scale in seconds to minutes with modern hardware. ∎

### 4.3 Fundamental Coupling Structure

The IC problem has the following minimal "hard core":

1. **Without the sum constraint**, IC decomposes into $m$ independent max-coverage subproblems, each solvable by standard greedy $(1-1/e)$ approximation.
2. **Without the budget constraint**, IC becomes trivial: just manufacture one variant per required (gear_id, offset) pair.
3. **With both constraints**, the coupling creates the NP-hardness.

**Theorem 5 (Minimal Hard Instance):** The IC problem restricted to a SINGLE gear type ($m=1$) with 6 slots per song and the sum constraint is still NP-complete (Theorem 1 uses $m=1$).

**Theorem 6 (Tractable Special Case):** If all target gem vectors $T_s$ are identical, IC reduces to a set-cover problem where each variant covers a subset of songs, and each song requires exactly 6 variants of the same type. This is still NP-complete but admits better heuristics due to uniformity.

### 4.4 What a Lossless Reduction to P Would Require

By Theorem 3, any polynomial-time exact algorithm must exploit special structure of the IC problem not present in the SUBSET-SUM reduction. This structure would have to be:

- **Bounded gem range**: Each gem dimension is in $[0, 90]$, which is small. A dynamic programming approach across the 6-dimensional state space would have $O(90^6) = O(5.3 \times 10^{11})$ states — too large.
- **Sparse target distribution**: In practice, the meta finder's targets are NOT uniformly distributed. Many songs share similar targets. But this is an empirical property, not a mathematical guarantee.
- **Small effective dimension**: The 6 dimensions are correlated (must sum to 90, individual per-slot caps). Dimensionality reduction might help — but the SUBSET-SUM reduction uses only 2 effective dimensions and is still hard.

**Conclusion:** No lossless reduction to a polynomial-time problem exists (Theorem 3). The problem is genuinely NP-complete. The practical path to exact solutions is the CP-SAT/ILP approach (Theorem 4) with a sufficiently rich witness pool — which gives optimality within the pool universe and can scale to production song counts.

---

## 5. Complexity Landscape Summary

| Variant | Complexity | Notes |
|---------|-----------|-------|
| IC-OPT (full) | NP-hard | Theorem 1 |
| IC-DECIDE (decision) | NP-complete | Theorem 1 |
| IC with fixed variant set | P (verification) | Theorem 2 — $O(n \bar{v}^6)$ |
| IC via ILP (witness-bounded) | NP-complete | Theorem 4 — practical for $n \le 1000$ |
| IC without sum constraint | NP-hard (Max Coverage) | Decomposes by gear |
| IC without budget constraint | P | Trivial: manufacture one of each needed variant |
| IC with $m=1$ (single gear) | NP-complete | Theorem 5 — still hard |
| IC with identical $T_s$ (all songs) | NP-complete | Theorem 6 — but better heuristics |

---

## 6. Relationship to Solver Architecture

The production solver (`gpu_full_solver.py`) implements a **heuristic pipeline**:
1. Greedy fill (no optimality guarantee)
2. Large Neighborhood Search (LNS) — metaheuristic improvement
3. CP-SAT hypergraph refinement — exact on ≤192-song neighborhoods
4. Inventory repair — local fill without capacity expansion

The CP-SAT component (Theorem 4's ILP construction) already proves optimality on local neighborhoods. Extending it to the global problem (all songs in one ILP) would provide a **global optimality certificate** within the witness pool universe, at the cost of increased solve time.

---

## References

- `inventory_optimizer/variant_space.py` — Variant universe enumeration (62,016 variants/gear)
- `inventory_optimizer/gpu_witness_pool.py` — Witness pattern generator
- `inventory_optimizer/gpu_full_solver.py` — Greedy + LNS solver
- `inventory_optimizer/cpsat_hypergraph.py` — CP-SAT neighborhood exact solver (Theorem 4 construction)
- `inventory_optimizer/coverage.py` — Orchestration and objective
- `gear_optimizer/core/constants.py` — Gem scaling constants
