# Analytical Optimal Force-Greats for Fever Maximization

> [!NOTE]
> This is a self-contained mathematical problem statement, not the current
> runtime architecture. Production uses exact response frontiers and the
> maintained implementation boundaries in [ARCHITECTURE.md](ARCHITECTURE.md).

## Problem Context

A rhythm game optimizer computes the best gear loadout (stat allocation) for each song. The score depends on a **fever system**: a power meter fills as the player hits notes, activates for a fixed time duration, then must refill. Notes hit during fever receive a multiplicative bonus.

**The complication:** The optimizer has discovered that intentionally hitting some non-fever notes as **"Great"** instead of **"Perfect"** can sometimes **increase** total score. A Great judgment contributes only **half** the fever-bar fill of a Perfect, which **delays** when fever activates. This delay shifts the fever window to cover different (potentially more valuable) notes. The tradeoff is that each forced Great note loses some direct score value.

**The baseline approach studied here:** Exhaustively enumerate all possible forced-Great configurations per section, recompute the fever timeline for each, and keep the best. This works for songs with few fever sections but **explodes combinatorially** for songs with many sections.

**The goal:** Find an analytical or structural approach that solves this optimization without exhaustive enumeration.

### Recommended Scope for This Assignment

This document combines two closely related variants of the Force Greats problem:

1. **Primary target: count-only Force Greats.**
   - Decision variables: the forced-Great counts $k_s$ per non-fever section.
   - Fever-timeline effect: only the fill-delay rule
     $$\text{notes to fill}(k) = \lceil \text{raw fill} + 0.5k \rceil$$
   - This is the cleanest analytical problem and the one most likely to admit an exact structural solution.

2. **Bonus / extension: timing-aware Force Greats.**
   - In the production optimizer, a forced Great may also have a candidate hit timestamp.
   - The last forced Great in a section can delay the fever start time further via a carry-time rule.
   - This couples the discrete count problem to the HitSim-style timing problem.

For this assignment, **please treat the count-only model as the primary problem to solve exactly**. If useful, also propose how the solution would extend to the timing-aware variant.

### Relationship to the HitSim Problem

This problem is a companion to the *Analytical HitSim* problem (documented separately). HitSim asks: "given that the player hits within a timing window, what is the best timing pattern?" Force Greats asks: "given that the player can intentionally downgrade some hits, what is the best downgrade pattern?"

Both problems reshape the same fever timeline. HitSim shifts fever boundaries by milliseconds (continuous timing offsets). Force Greats shifts fever boundaries by whole notes (discrete fill delays). In the full optimizer, both interact: the Great judgment's candidate timestamp can further shift fever start time.

---

## Game Mechanics

### Inputs

| Symbol | Description |
|--------|-------------|
| $N$ | Total notes in the song |
| $L$ | Count of "long notes" (held notes, excluded from fill calculation) |
| $T = [t_0, t_1, \ldots, t_{N-1}]$ | Chart timestamps (seconds), sorted ascending |
| $\text{FF}$ | Fever Fill Rate stat multiplier (real number, from gear loadout) |
| $\text{FT}$ | Fever Time stat multiplier (real number, from gear loadout) |
| $\text{base}$ | Base score value per note (from gear loadout) |
| $\text{combo mul}$ | Combo multiplier (from gear loadout) |
| $\text{fever mul}$ | Fever multiplier (from gear loadout, $> 1$) |
| $\text{PP}$ | Perfect Points bonus (from gear loadout) |

### Fever Fill (Count-Based)

The number of non-fever notes required to trigger each fever activation (with all Perfects):

$$\text{raw fill} = (N - L) \times 0.333 \times \text{FF}$$

$$\text{fill count} = \lceil \text{raw fill} \rceil$$

### Fever Duration (Time-Based)

$$\text{fever duration} = (t_{N-1} \times 0.15 + 0.15) \times \text{FT}$$

This is a fixed number of **seconds**, determined entirely by song length and the FT stat. It does not change with Force Greats.

### Force Greats: The Fill Delay

When $k$ notes in a non-fever section are forced to Great instead of Perfect, each Great contributes only **half** the fill of a Perfect. The adjusted fill requirement becomes:

$$\text{notes to fill}(k) = \lceil \text{raw fill} + 0.5k \rceil$$

The **fill penalty** (extra notes needed vs all-Perfect) is:

$$\text{fp}(k) = \lceil \text{raw fill} + 0.5k \rceil - \lceil \text{raw fill} \rceil$$

Since the ceiling function increases in discrete jumps, $\text{fp}(k)$ is a **staircase**: it stays flat for stretches, then jumps by 1. The values of $k$ where $\text{fp}(k)$ increases are called **breakpoints**.

### Breakpoints

A breakpoint at forced count $k$ exists iff:

$$\text{fp}(k) \neq \text{fp}(k-1)$$

Since $\text{fp}(k) = \lceil \text{raw fill} + 0.5k \rceil - \lceil \text{raw fill} \rceil$, a jump occurs when $0.5k$ crosses an integer boundary relative to the fractional part of $\text{raw fill}$. Let $f = \text{raw fill} - \lfloor \text{raw fill} \rfloor$ be the fractional part. Then:

$$\text{breakpoints} = \{k : \lfloor 0.5k + f \rfloor > \lfloor 0.5(k-1) + f \rfloor \}$$

For most songs, breakpoints occur at every 2nd or 3rd forced Great. Between breakpoints, additional forced Greats change the score penalty but **not** the fever timeline.

### Fever Timeline Walk (with Force Greats)

The timeline is constructed by walking through the song note-by-note. This is identical to the base fever walk except that `notes_to_fill` is section-dependent:

```
idx = 0
section = 1
fever_notes = set()
config = [k_1, k_2, ..., k_S]    # forced Great count per section

while idx < N:
    k = config[section] if section <= S else 0
    notes_to_fill = ceil(raw_fill + 0.5 * k)

    if section == 1:
        notes_needed = notes_to_fill - 1    # activation note counts as fever
    else:
        notes_needed = notes_to_fill         # +1 for "transition note" after previous fever

    idx += notes_needed
    if idx >= N: break

    # Fever activates at note idx
    fever_start_time = T[idx]
    fever_end_time = fever_start_time + fever_duration

    # Find where fever ends
    fever_end_idx = first j such that T[j] >= fever_end_time

    # Mark fever notes
    for j in range(idx, fever_end_idx):
        fever_notes.add(j)

    idx = fever_end_idx
    section += 1
```

**Key observation:** Each section's forced-Great count $k_s$ shifts the activation index of that section's fever window. But because `idx = fever_end_idx` cascades into the next section, **a shift in section $s$ propagates through all subsequent sections**.

---

## Scoring

### Perfect Note Value

For notes in the **head region** ($i < 100$), the score ramps linearly:

$$V_{\text{perfect}}(i) = \left\lfloor \text{base value} \times \left(1 + (\text{combo mul} - 1) \times \frac{i+1}{100}\right) \right\rfloor$$

where $\text{base value} = (\text{primary} \times 2) + \text{secondary} + \text{PP}$.

For notes in the **body region** ($i \geq 100$), the score is flat:

$$V_{\text{perfect}}^{\text{body}} = \lfloor \text{base value} \times \text{combo mul} \rfloor$$

### Great Note Value

A Great uses $\frac{2}{3}$ of the primary and secondary components, plus a fixed +150 bonus:

$$\text{great base} = \left\lfloor \text{primary} \times 2 \times \frac{2}{3} \right\rfloor + \left\lfloor \text{secondary} \times \frac{2}{3} \right\rfloor + 150$$

For head notes:

$$V_{\text{great}}(i) = \left\lfloor \text{great base} \times \left(1 + (\text{combo mul} - 1) \times \frac{i+1}{100}\right) \right\rfloor$$

For body notes:

$$V_{\text{great}}^{\text{body}} = \left\lfloor \left(\text{primary} \times 2 \times \frac{2}{3} + \text{secondary} \times \frac{2}{3} + 150\right) \times \text{combo mul} \right\rfloor$$

(Note: the body formula uses the **unrounded** great base for the floor, while the head formula uses the **rounded** great base. This matches the game's floor-after-multiply behavior.)

### Score Penalty per Forced Great

$$\text{penalty}(i) = \max(0,\; V_{\text{perfect}}(i) - V_{\text{great}}(i))$$

This penalty depends on the **note index** where the Great is placed (because of the head ramp). Forced Greats at lower indices have smaller penalties; forced Greats at higher indices (near note 100) have larger penalties.

### Total Score for a Configuration

For a forced-Great configuration $C = [k_1, k_2, \ldots, k_S]$:

$$\text{score}(C) = \text{base score}(\text{timeline}(C)) - \sum_{s=1}^{S} \sum_{i \in \text{forced notes}(s)} \text{penalty}(i)$$

where $\text{base score}(\text{timeline}(C))$ is the all-Perfect score computed on the fever timeline induced by $C$.

The **fill penalty** (shifted activation indices → different fever mask → different base score) is already captured in the timeline-derived base score. It is not subtracted separately.

### Placement of Forced Greats Within a Section

Forced Greats are placed at the **first $k_s$ fill-contributing notes** in each section:

- **Section 1:** The section starts at the beginning of the song (or after the previous fever window for section 1 if the song starts mid-fever — rare). Forced Greats are placed at notes $\text{start}, \text{start}+1, \ldots, \text{start} + k_1 - 1$.
- **Sections 2+:** The first note after a fever window is a "transition note" that does not contribute fill. Forced Greats skip it and start at the second note: indices $\text{start} + 1, \text{start} + 2, \ldots, \text{start} + k_s$.

This placement is fixed — the optimizer chooses **how many** to force per section, not **which specific notes** within the section. The penalty indices follow the same rule: section 1 penalties start at `start_idx + 0` (the `skip_wasted` flag is true), while sections 2+ start at `start_idx + 1`.

---

## The Optimization Problem

### Decision Variables

For each non-fever section $s \in \{1, 2, \ldots, S\}$:

$$k_s \in \{0, 1, 2, \ldots, K_s\}$$

where $K_s = \min(\text{non fever base},\; \text{notes in section}_s)$ is the maximum number of notes that can be forced to Great in section $s$. Here $\text{non fever base} = \lceil \text{raw fill} \rceil$ is the all-Perfects fill count.

### Objective

$$\max_{(k_1, \ldots, k_S)} \text{score}(k_1, \ldots, k_S)$$

### Constraints

1. $0 \leq k_s \leq K_s$ for each section $s$.
2. The fever timeline must be recomputed for each configuration (fill delay cascades).
3. Forced Greats in section $s$ must not exceed the actual number of fill-contributing notes in that section (which depends on the cascaded timeline from earlier sections).

---

## Why the State Space Explodes

### Raw Enumeration Size

The configuration space is:

$$\prod_{s=1}^{S} (K_s + 1)$$

For a typical song:

| Parameter | Typical value |
|-----------|---------------|
| $S$ (sections) | 3–12 |
| $K_s$ (max forced per section) | 10–50 |

Examples:

| Sections | Per-section cap | Configurations |
|----------|-----------------|----------------|
| 3 | 50, 25, 15 | 20,826 |
| 5 | 5 each | 7,776 |
| 8 | 5 each | 1,679,616 |
| 12 | 5 each | 244,140,625 |

### Timeline Coupling

The key difficulty: sections are **not independent**. Changing $k_s$ in section $s$ shifts the activation index of section $s$'s fever window, which shifts the **end index** of that window (because fever duration is time-based, not count-based), which shifts the **start** of section $s+1$, cascading through all subsequent sections.

This means:
- The score contribution of section $s+1$ depends on $k_s$ (and all earlier sections).
- There is no separable per-section objective.
- Each configuration requires a full $O(N)$ timeline walk to evaluate.

### The FT/FF Multiplier

In practice, the optimizer also searches over nearby Fever Fill and Fever Time stat values (a window of $\pm 5$ around each center). This multiplies the search space by the number of (FT, FF) pairs evaluated per configuration:

$$\text{total evaluations} = \prod_{s=1}^{S} (K_s + 1) \times |\text{FT window}| \times |\text{FF window}|$$

With a radius of 5, the FT/FF window is $11 \times 11 = 121$ pairs. Combined with 8 sections at cap 5, this gives $121 \times 1{,}679{,}616 \approx 2 \times 10^8$ evaluations.

### Current Mitigations (Brute Force + Caps)

The current implementation mitigates the explosion with hard caps:

| Sections | Per-section caps | Max configs |
|----------|------------------|-------------|
| 1 | 50 | 51 |
| 2 | 50, 25 | 1,326 |
| 3 | 50, 25, 15 | 20,826 |
| 4+ | 5 per section | $6^S$ |
| 21+ | — | **bail out** (return baseline, skip FG entirely) |

These caps are heuristic. They discard potentially optimal high-count configurations for songs with many sections. The cap of 5 for 4+ sections is particularly aggressive — it reduces the search space but may miss the true optimum.

Note: in current production, FG evaluation is organized around exact, score-sufficient frontiers (a response-frontier bundle plus exact inner solve). Any remaining bounds are GPU-safety/workload guards, not “human hit sim” style probabilistic simulation.

---

## Structural Properties to Exploit

### 1. Breakpoint Sparsity

In the **count-only model**, increasing $k_s$ by 1 between breakpoints does **not** change the fill-delay staircase or the resulting activation index for that section — it only adds one more Great penalty. Since the penalty is always non-negative, the score strictly decreases between breakpoints. Therefore:

**For the count-only model, the optimal $k_s$ for section $s$ (holding other sections fixed) is always at a breakpoint or at 0.**

**Important caveat:** this statement is **not automatically true** in the timing-aware variant. When Great candidate timestamps are enabled, increasing $k_s$ can change the identity of the last forced Great in the section, which can change the `carry_time` used for fever start. In that regime, non-breakpoint counts can still change the score even if the fill-delay staircase stays flat.

This reduces the effective per-section choices from $K_s$ to the number of breakpoints, which is typically $O(K_s / 2)$ to $O(K_s)$.

### 2. Fill Penalty Monotonicity

$\text{fp}(k)$ is non-decreasing: more forced Greats can only delay (never advance) fever activation. The fever window slides rightward on the note axis.

### 3. Score Penalty Monotonicity (Per Section, Fixed Timeline)

For a fixed timeline (fixed activation/end indices), the score penalty from forced Greats is:

$$\text{penalty}(k_s) = \sum_{i=0}^{k_s - 1} \text{penalty}(\text{start}_s + i)$$

This is a prefix sum of non-negative values → monotonically non-decreasing. More forced Greats always cost more in direct score.

### 4. Cascade Decay

In practice, the fill penalty from section $s$ shifts the activation index by $\text{fp}(k_s)$ notes. For songs with roughly uniform note density, this shift moves the fever window by:

$$\Delta t \approx \frac{\text{fp}(k_s)}{\text{notes per second}}$$

If $\Delta t$ is small relative to the fever duration, the fever window captures approximately the same number of notes at the shifted position. The cascade effect decays with note density.

### 5. Fever Note Gain vs Score Penalty Tradeoff

Forcing $k_s$ Greats in section $s$:

- **Costs:** $\sum \text{penalty}(i)$ in direct score loss (monotonically increasing in $k_s$).
- **Gains:** Potentially shifts the fever window to cover $\Delta n$ more (or fewer) notes, each worth $V_{\text{fever}}(j) - V_{\text{normal}}(j) \geq 0$.

The net benefit is:

$$\text{benefit}(k_s) = \underbrace{\Delta n \times (V_{\text{fever}} - V_{\text{normal}})}_{\text{fever gain from shift}} - \underbrace{\sum_{i} \text{penalty}(i)}_{\text{Great score loss}}$$

For body-region notes where values are flat, $\Delta n$ changes in discrete steps (at breakpoints). The tradeoff is: "does gaining one more fever note (worth $g = \lfloor \text{base} \cdot \text{combo mul} \cdot \text{fever mul} \rfloor - \lfloor \text{base} \cdot \text{combo mul} \rfloor$) justify the accumulated Great penalties?"

---

## Research Questions

### Q1: Optimal Configuration (Exact)

Given a song and loadout, find the forced-Great configuration $(k_1, \ldots, k_S)$ that maximizes total score, without exhaustive enumeration.

**Subquestions:**

- Can the problem be decomposed section-by-section using a DP over activation indices?
- Can the cascade be modeled as a compact state (e.g., cumulative fill shift) that enables tractable DP?
- Can breakpoint sparsity reduce the effective branching factor enough for exact search?

### Q2: Interaction with HitSim Timing

Under the timing-envelope model, the Great judgment has a **candidate timestamp**. If this timestamp is later than the Perfect hit time, it can further delay fever activation via a **carry time** mechanism:

```
carry_time = max(carry_time, great_candidate_timestamp[last_forced_note])
fever_start_time = max(chart_time[activation], carry_time)
```

This means the FG optimization is not purely count-based — the **position** of the last forced Great in each section can shift the fever start time by milliseconds, interacting with the HitSim timing problem.

**Subquestion:** Can the HitSim timing interaction be modeled jointly with the FG count optimization, or is it better solved as a two-stage problem (first optimize counts, then optimize timing)?

### Q3: Sensitivity Analysis

For what types of songs/loadouts does FG matter?

**Subquestions:**

- When is the optimal configuration always $(0, 0, \ldots, 0)$ (never force Greats)?
- Can a fast precheck determine whether FG can possibly improve the score?
- How does the benefit scale with $\text{fever mul}$, note density, and section count?

### Q4: Scalability

**Subquestions:**

- Can the solution handle 12+ sections without the current cap-5 heuristic?
- Can the FT/FF search window be handled analytically (as in the HitSim problem's `(fill_count, d)` caching)?
- What is the achievable complexity vs the current $O(\prod K_s \times N)$?

---

## Worked Example

Consider a simple song: $N = 100$ notes, $L = 0$ long notes, evenly spaced at 100ms intervals (10 notes/sec).

### Parameters

| Quantity | Value |
|----------|-------|
| $\text{raw fill}$ | $100 \times 0.333 \times 1.0 = 33.3$ |
| fill_count | 34 |
| fever_duration | $(9.9 \times 0.15 + 0.15) \times 1.0 = 1.635$ s |
| Sections | 2 (section 1: notes 0–32 fill, fever at 33; section 2: after first fever ends) |

### Section 1: Force 0 vs 2 vs 4 Greats

| $k_1$ | $\text{fp}(k_1)$ | Activation index | Fever captures | Great penalty | Net effect |
|--------|-------------------|------------------|----------------|---------------|------------|
| 0 | 0 | 33 | notes 33–49 (17 notes) | 0 | baseline |
| 2 | 1 | 34 | notes 34–50 (17 notes) | $\text{penalty}(0) + \text{penalty}(1)$ | shifted by 1, same count, minus penalties |
| 4 | 2 | 35 | notes 35–51 (17 notes) | $\sum_{i=0}^{3} \text{penalty}(i)$ | shifted by 2, same count, minus penalties |

In this uniform-density case, shifting the window captures the same number of notes. The Great penalties are pure loss → **optimal is $k_1 = 0$**.

### When FG Helps

FG helps when the fever boundary falls in a **density transition** — e.g., a sparse gap followed by a dense burst. Delaying fever activation by a few notes can push the window past the gap into the burst, capturing significantly more notes. The gain from extra fever notes must exceed the accumulated Great penalties.

---

## Notation Reference

| Symbol | Domain | Description |
|--------|--------|-------------|
| $N$ | $\mathbb{Z}^+$ | Total notes |
| $L$ | $\mathbb{Z}_{\geq 0}$ | Long notes count |
| $S$ | $\mathbb{Z}^+$ | Number of non-fever sections |
| $k_s$ | $\{0, \ldots, K_s\}$ | Forced Greats in section $s$ |
| $K_s$ | $\mathbb{Z}_{\geq 0}$ | Max forced Greats in section $s$ |
| $\text{raw fill}$ | $\mathbb{R}^+$ | Base fill before ceiling: $(N-L) \times 0.333 \times \text{FF}$ |
| $\text{fill count}$ | $\mathbb{Z}^+$ | $\lceil \text{raw fill} \rceil$ |
| $\text{fp}(k)$ | $\mathbb{Z}_{\geq 0}$ | Fill penalty: $\lceil \text{raw fill} + 0.5k \rceil - \lceil \text{raw fill} \rceil$ |
| $\text{fever duration}$ | $\mathbb{R}^+$ (seconds) | $(t_{N-1} \times 0.15 + 0.15) \times \text{FT}$ |
| $V_{\text{perfect}}(i)$ | $\mathbb{Z}^+$ | Score for note $i$ as Perfect |
| $V_{\text{great}}(i)$ | $\mathbb{Z}^+$ | Score for note $i$ as Great |
| $\text{penalty}(i)$ | $\mathbb{Z}_{\geq 0}$ | $V_{\text{perfect}}(i) - V_{\text{great}}(i)$ |
| $g$ | $\mathbb{Z}^+$ | Per-note fever gain: $\lfloor \text{base} \cdot \text{combo mul} \cdot \text{fever mul} \rfloor - \lfloor \text{base} \cdot \text{combo mul} \rfloor$ |
| $\text{FF}$ | $\mathbb{R}^+$ | Fever Fill Rate multiplier |
| $\text{FT}$ | $\mathbb{R}^+$ | Fever Time multiplier |
