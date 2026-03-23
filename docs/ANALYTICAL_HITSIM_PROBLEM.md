# Analytical Optimal Hit-Timing for Fever Maximization

## Problem Context

A rhythm game scores players based on how accurately they hit notes at prescribed chart times. The total score depends on a **fever system**: a power meter that fills as the player hits notes, activates for a fixed duration (in seconds), then must refill. Notes hit during fever receive a multiplicative bonus. The optimizer's goal is to find the gear loadout (stat allocation) that maximizes total score.

**The complication:** In the real game, players don't hit notes at exactly the chart time. They hit within a timing window (e.g. -20ms to +40ms for a "Perfect" judgment). The exact hit time doesn't affect the per-note judgment (all times in the window are "Perfect"), but it **does** affect when fever activates and ends, because fever duration is measured in **wall-clock seconds**, not note counts. Small timing offsets can push notes in or out of fever windows at the boundaries.

Currently, the optimizer handles this via **Monte Carlo sampling**: run the optimizer multiple times with different random hit-timing seeds (`SongRepeats`), and keep the best result. This is expensive. We want an **analytical approach** that computes the optimal (or expected) hit-timing outcome in a single evaluation.

---

## Game Mechanics (Simplified Model)

### Inputs

| Symbol | Description |
|--------|-------------|
| $N$ | Total notes in the song |
| $L$ | Count of "long notes" (held notes, excluded from fill calculation) |
| $T = [t_0, t_1, \ldots, t_{N-1}]$ | Chart timestamps (seconds), sorted ascending |
| $\text{FF}$ | Fever Fill Rate stat multiplier (real number, from gear loadout) |
| $\text{FT}$ | Fever Time stat multiplier (real number, from gear loadout) |
| $\text{base}$ | Base score value per note (from gear loadout) |
| $\text{combo\_mul}$ | Combo multiplier (from gear loadout) |
| $\text{fever\_mul}$ | Fever multiplier (from gear loadout, > 1) |

### Fever Fill (Count-Based)

The number of non-fever notes required to trigger each fever activation:

$$\text{raw\_fill} = (N - L) \times 0.333 \times \text{FF}$$

$$\text{fill\_count} = \lceil \text{raw\_fill} \rceil$$

### Fever Duration (Time-Based)

$$\text{fever\_duration} = (t_{N-1} \times 0.15 + 0.15) \times \text{FT}$$

This is a fixed number of **seconds**, determined entirely by song length and the FT stat.

For the offset analysis below, define $D_{\text{ms}} = 1000 \times \text{fever\_duration}$ so the boundary comparisons use the same units as the hit offsets.

### Fever Timeline Walk

The fever timeline is constructed by walking through the song note-by-note:

```
idx = 0
section = 1
fever_notes = set()

while idx < N:
    # Non-fever section: consume notes to fill the meter
    if section == 1:
        notes_needed = fill_count - 1      # first section: activation note is fever
    else:
        notes_needed = fill_count           # later sections: +1 for "transition note"
    
    idx += notes_needed
    if idx >= N: break
    
    # Fever activates at note idx
    fever_start_time = T[idx]              # <-- depends on actual hit time
    fever_end_time = fever_start_time + fever_duration
    
    # Find where fever ends (first note at or past the end time)
    fever_end_idx = binary_search_left(T, fever_end_time)    # T[j] >= fever_end_time
    
    # Mark fever notes
    for j in range(idx, fever_end_idx):
        fever_notes.add(j)
    
    idx = fever_end_idx                    # <-- cascades into next section
    section += 1
```

**Key observations:**
- `fill_count` (how many notes to fill the bar) is **fixed** for a given loadout, independent of hit timing.
- But `fever_end_idx` depends on the **actual timestamps** via `binary_search_left`, because fever duration is measured in seconds.
- Critically, the loop sets `idx = fever_end_idx` after each window, so **every fever window after the first has its activation index determined by the previous window's end**, which depends on hit timing. The entire timeline structure from window 2 onward is timing-dependent.

### Score Calculation

```
total_score = 0
for i in range(N):
    if i < 100:
        # "Head" region: combo ramp
        ramp = base + (i + 1) * (combo_mul - 1) * base / 100
        if i in fever_notes:
            total_score += floor(ramp * fever_mul)
        else:
            total_score += floor(ramp)
    else:
        # "Body" region: flat per-note value
        if i in fever_notes:
            total_score += floor(base * combo_mul * fever_mul)
        else:
            total_score += floor(base * combo_mul)
```

Because `fever_mul > 1`, every note being in fever contributes a **non-negative** score gain relative to normal.
The true optimization objective is to maximize a **weighted** sum of fever indicators (combo ramp makes early notes
slightly lower-weight than later notes in the first 100), but in the body region (>= 100 notes) the score depends
only on the **count** of fever vs normal notes.

---

## The Hit-Timing Model

### Perfect Timing Window

Each note has a chart time $c_i$ (in integer milliseconds after quantization). The player hits within the "Perfect" window:

$$t_i = c_i + \delta_i \quad \text{where} \quad \delta_i \in [-20, +40] \text{ ms (integers)}$$

For held/tail notes (type 3), the window doubles to $[-40, +80]$ ms.

### Chord Grouping

Notes at the same chart time form a **chord group**. All notes in a chord group share a single offset:

$$\forall\, i, j \text{ in same group}: \delta_i = \delta_j$$

### Monotonicity Constraint

Hit times must be non-decreasing across groups. If group $g$ has base chart time $c_g$ and group $g-1$ produced event time $e_{g-1}$:

$$c_g + \delta_g \geq e_{g-1}$$

$$\implies \delta_g \geq e_{g-1} - c_g$$

In the implementation, each group samples from its own feasible integer-ms interval after intersecting its nominal window with the monotonicity constraint from the previous group's realized event time. If that interval is empty, the group is forced forward to preserve non-decreasing timestamps, even if that means moving beyond the nominal window.

### Distribution

Let $[l_g, u_g]$ be the nominal integer-ms offset window for group $g$ after applying the note-type rules (regular notes or held-tail notes). The feasible interval is:

$$\text{eff\_low}_g = \max(l_g, e_{g-1} - c_g)$$

$$\text{eff\_high}_g = u_g$$

If $\text{eff\_low}_g \leq \text{eff\_high}_g$, the group offset is sampled uniformly from the integers in $[\text{eff\_low}_g, \text{eff\_high}_g]$. If the interval is empty, the implementation snaps the group to the latest feasible time and then, if needed, advances it to the previous group's event time to keep the sequence monotone.

---

## Problem Formulation

### What Hit-Timing Affects

Fever fill is **count-based** (fixed number of notes per section, independent of timing). However, hit timing affects score through **two** mechanisms:

**Mechanism 1: Fever end boundary.** Within each fever window, the **end index** depends on timestamps:

$$j^* = \min\{j : t_j \geq t_a + D_{\text{ms}}\}$$

where $a$ is the activation index and $D_{\text{ms}}$ is the fever duration in milliseconds. This determines how many notes receive the fever bonus.

**Mechanism 2: Cascade into subsequent activations.** After each fever window, the walk resumes at `idx = fever_end_idx`. The *next* fever activation occurs `fill_count` notes later. So while the **first** activation index is fully determined by `fill_count` alone, **every subsequent activation index depends on the previous `fever_end_idx`**, which depends on hit times.

This means hit timing affects not just how many notes are in each fever window, but also **which note indices** activate fever for windows 2, 3, etc.

Substituting the offset model into the end-boundary condition:

$$j^* = \min\{j : c_j + \delta_j \geq c_a + \delta_a + D_{\text{ms}}\}$$

Rearranging for each candidate note $j$:

$$\text{Note } j \text{ is in fever} \iff \delta_j - \delta_a < D_{\text{ms}} - (c_j - c_a)$$

### The Swing Zone

Define the chart gap $\Delta_j = c_j - c_a$ (fixed, known from chart data). The swing-zone width depends on the **note types** of both the activation note and the candidate note, because held-tail notes (type 3) get a **x2 timing window**.

| Activation note | Candidate note | $\delta_a$ range | $\delta_j$ range | $\delta_j - \delta_a$ range | Swing zone width |
|----------------|----------------|-------------------|-------------------|------------------------------|-----------------|
| Regular | Regular | $[-20, +40]$ | $[-20, +40]$ | $[-60, +60]$ | 120 ms |
| Held tail | Regular | $[-40, +80]$ | $[-20, +40]$ | $[-80, +60]$ | 140 ms |
| Regular | Held tail | $[-20, +40]$ | $[-40, +80]$ | $[-100, +60]$ | 160 ms |
| Held tail | Held tail | $[-40, +80]$ | $[-40, +80]$ | $[-120, +120]$ | 240 ms |

Let $R = \max(\delta_j) - \min(\delta_a)$ and $L = \min(\delta_j) - \max(\delta_a)$ be the extremes of $\delta_j - \delta_a$ for the specific note types involved. This partitions notes into three categories:

| Condition | Category | Fever membership |
|-----------|----------|-----------------|
| $\Delta_j < D_{\text{ms}} - R$ | **Interior** | Always in fever (any valid offsets) |
| $\Delta_j \geq D_{\text{ms}} - L$ | **Exterior** | Never in fever (any valid offsets) |
| Otherwise | **Boundary/Swing** | Depends on $\delta_a$ and $\delta_j$ |

For the common case (regular-regular), the swing zone is 120ms wide. With held tails it can be up to 240ms. At typical note densities, this still means only **0-4 notes per fever window** are swing notes, but it's wider than the regular-only case and must be accounted for per note.

### The Cascade

Fever windows are linked: the end index of fever window $k$ determines where the non-fever section for window $k+1$ starts, and therefore where window $k+1$ activates. If a boundary decision at window $k$ includes/excludes one more note, it shifts the activation of window $k+1$ by one index, potentially changing its boundary notes.

This creates a **sequential dependency** across fever windows (typically 3-8 per song).

---

## Research Questions

### Q1: Optimal Single-Evaluation Hit Timing (Primary)

Given a song's chart times $T$, note count $N$, long note count $L$, and a loadout's stats ($\text{FF}$, $\text{FT}$, $\text{base}$, $\text{combo\_mul}$, $\text{fever\_mul}$):

**Find a set of offsets $\{\delta_g\}$ for each chord group $g$ that maximizes total score, subject to:**
1. $\delta_g \in [\delta_{\min}^{(g)}, \delta_{\max}^{(g)}]$ (Perfect window, possibly doubled for held tails)
2. $c_g + \delta_g \geq c_{g-1} + \delta_{g-1}$ for all consecutive groups (monotonicity)

Or equivalently: **compute the maximum achievable score over all valid offset assignments.**

#### Notes on Complexity
- The optimizer evaluates **thousands of loadouts per song** (each with different FF, FT, base, combo_mul, fever_mul). The analytical method must be efficient enough to run per-evaluation, or precompute a structure that makes per-evaluation lookups cheap.
- The current scoring function runs in ~microseconds per evaluation. An analytical HitSim solution that adds more than ~10x overhead per evaluation would need to compensate by eliminating repeats.

### Q2: Expected Score Under Random Timing (Secondary)

Under the random offset model, compute $E[\text{score}]$ analytically.

**Naive approach (known to be an approximation):** If offsets were i.i.d. uniform and independent across groups, the difference $\delta_j - \delta_a$ would follow a discrete triangular distribution (convolution of two uniform PMFs), and linearity of expectation would give:

$$E[\text{score}] = \sum_{i=0}^{N-1} \left[ V_{\text{fever}}(i) \cdot P(i \in \text{fever}) + V_{\text{normal}}(i) \cdot P(i \notin \text{fever}) \right]$$

**Why the naive approach is wrong in general:** The offsets are **not** i.i.d. in the actual model:

1. **Chord grouping:** All notes in a chord group share one offset draw. If the activation note and a candidate note are in the same group (or share a group with an intermediate note), $\delta_j - \delta_a$ is not a difference of two independent uniforms.

2. **Monotonicity constraint:** Each group's effective lower bound depends on the previous group's realized event time ($\delta_g \geq e_{g-1} - c_g$). This creates a **Markov chain** across groups: early groups that draw high offsets shrink the range for subsequent groups. The marginal distributions are not uniform, and adjacent offsets are positively correlated.

3. **Cascade across windows:** Even if you correctly compute $P(\text{note } j \in \text{fever for window } k)$ for each window independently, the cross-window cascade means fever membership in window $k+1$ is conditionally dependent on the outcome at window $k$.

**Challenge:** Can the exact $E[\text{score}]$ be computed efficiently despite these dependencies? How tight is the i.i.d. approximation in practice -- does monotonicity binding happen often enough to matter, or is the gap between chart times usually large enough that the constraint is slack?

### Q3: Sensitivity and Diminishing Returns (Exploratory)

How does the **score gap** between best and worst HitSim outcomes vary as a function of:
- Note density near fever boundaries
- Fever duration ($D$)
- Number of fever windows
- Fever multiplier magnitude

If the gap is small for most songs/loadouts, the analytical approach has less value (meaning HitSim off or a single random seed is "good enough"). If it's large and concentrated in specific song structures, the analytical approach should be targeted there.

---

## Worked Example

Consider a simplified song:

- $N = 50$ notes, $L = 0$ long notes
- Chart times: notes at 100ms intervals, so $c_i = 100i$ ms for $i = 0, \ldots, 49$
- $\text{FF} = 1.0$ (no stat bonus), $\text{FT} = 1.0$
- Last note time: $t_{49} = 4.9$ s

**Fill count:**
$$\text{raw\_fill} = 50 \times 0.333 \times 1.0 = 16.65$$
$$\text{fill\_count} = \lceil 16.65 \rceil = 17$$

**Fever duration:**
$$D_{\text{ms}} = (4.9 \times 0.15 + 0.15) \times 1.0 = 0.885 \text{ s} = 885 \text{ ms}$$

**Section 1 (first fever window):**
- Non-fever notes: $17 - 1 = 16$ (indices 0-15)
- Fever activates at index 16, chart time $c_{16} = 1600$ ms
- Fever end time: $1600 + 885 = 2485$ ms (with 0ms offsets)
- Notes in fever: indices 16-24 (chart times 1600-2400 ms; note 25 at 2500ms >= 2485ms)
- Fever notes: **9 notes**

**Boundary analysis for window 1:**
- Note 24: $\Delta_{24} = c_{24} - c_{16} = 800$ ms. Need $\delta_{24} - \delta_{16} < 885 - 800 = 85$. Since max difference is 60, **always in fever** (interior note).
- Note 25: $\Delta_{25} = 900$ ms. Need $\delta_{25} - \delta_{16} < 885 - 900 = -15$. This threshold IS in $[-60, +60]$, so **swing note**.

**Can we capture note 25?** We need $\delta_{25} - \delta_{16} < -15$, i.e., $\delta_{25} < \delta_{16} - 15$.

The key insight is to maximize $\delta_{16}$ (hit activation note **late**) and minimize $\delta_{25}$ (hit boundary note **early**):
- Set $\delta_{16} = +40$: fever starts at $1640$ ms, ends at $1640 + 885 = 2525$ ms
- Set $\delta_{25} = -20$: note 25 hits at $2500 - 20 = 2480$ ms
- Check: $2480 < 2525$ ✓ → **note 25 is in fever!**

Contrast with the worst case ($\delta_{16} = -20$, $\delta_{25} = +40$):
- Fever starts at $1580$ ms, ends at $2465$ ms
- Note 25 hits at $2540$ ms ≥ $2465$ → **note 25 is out of fever**

So for window 1, the optimal strategy is: **activation note late (+40ms), boundary note early (-20ms)**. This captures note 25, gaining 1 extra fever note.

**Counterintuitive insight:** The naive intuition is "hit early to start fever sooner." But the actual optimum is the opposite -- hit the activation note **late** (pushing the fever end time further out in absolute time) while hitting boundary notes **early** (pulling them into the window). What matters is maximizing the gap $t_a + D_{\text{ms}} - t_j$, which benefits from **both** a late activation and early boundary hits.

---

## Deliverables

1. **Algorithm** for computing the optimal offset assignment (Q1) with complexity analysis.
2. **Proof or bound** on when the greedy approach (optimize each window independently) equals the global optimum vs. when cascade effects matter.
3. **Closed-form or efficient formula** for $E[\text{score}]$ (Q2), with analysis of the approximation error from ignoring cascade correlation.
4. **Characterization** of when the HitSim gap is large enough to matter (Q3).

---

## Appendix: Notation Summary

| Symbol | Domain | Description |
|--------|--------|-------------|
| $N$ | $\mathbb{Z}^+$ | Total notes |
| $L$ | $\mathbb{Z}_{\geq 0}$ | Long notes count |
| $c_i$ | $\mathbb{Z}_{\geq 0}$ (ms) | Chart time for note $i$ (integer ms) |
| $\delta_g$ | $\{-20, \ldots, +40\}$ or $\{-40, \ldots, +80\}$ | Offset for chord group $g$ (integer ms; range doubles for held-tail notes) |
| $t_i = c_i + \delta_i$ | $\mathbb{Z}$ (ms) | Actual hit time (integer ms) |
| $\text{FF}$ | $\mathbb{R}^+$ | Fever Fill Rate multiplier |
| $\text{FT}$ | $\mathbb{R}^+$ | Fever Time multiplier |
| $D$ | $\mathbb{R}^+$ (seconds) | Fever duration |
| $D_{\text{ms}}$ | $\mathbb{R}^+$ (ms) | Fever duration converted to milliseconds for boundary comparisons |
| $\text{fill\_count}$ | $\mathbb{Z}^+$ | Notes to trigger fever |
| $V_{\text{fever}}(i)$ | $\mathbb{Z}^+$ | Score for note $i$ if in fever |
| $V_{\text{normal}}(i)$ | $\mathbb{Z}^+$ | Score for note $i$ if not in fever |

## Appendix: Real-World Parameter Ranges

| Parameter | Typical Range | Notes |
|-----------|--------------|-------|
| $N$ | 200 - 3000+ | Short songs ~200, marathon songs 3000+ |
| $L$ | 0 - ~30% of $N$ | Song-dependent |
| Notes per second | 2 - 15 | Varies by difficulty; higher = more boundary notes |
| $D$ (fever duration) | 0.5 - 8 seconds | Depends on song length and FT stat |
| Fever windows per song | 3 - 12 | Depends on fill rate and song length |
| Swing notes per window | 0 - 4 | Depends on note density near boundary; wider with held tails |
| Chord group size | 1 - 4 notes | Singles, doubles, triples |
| $\text{fever\_mul}$ | 1.1 - 2.0+ | Higher multiplier = larger score impact per swing note |
| Evaluations per song | 10,000 - 500,000 | GA search; analytical method runs per evaluation |
