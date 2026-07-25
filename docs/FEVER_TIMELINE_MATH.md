# Fever Timeline Mathematical Specification

## Constants & Inputs

| Symbol | Description |
|--------|-------------|
| $N$ | Total notes in song |
| $L$ | Long notes count |
| $T$ | Array of note timestamps: $[t_0, t_1, ..., t_{N-1}]$ |
| $t_{last}$ | Last note time (song length proxy) |
| $FT$ | Fever Time stat (0-160) |
| $FF$ | Fever Fill Rate stat (0-160) |
| $f_{FT}(x)$ | Fever Time lookup: stat -> multiplier |
| $f_{FF}(x)$ | Fever Fill Rate lookup: stat -> multiplier |

---

## Core Formulas

### Fill Rate (notes to trigger fever)

$$\text{non fever cas} = (N - L) \times 0.333$$

$$\text{non fever base} = \lceil \text{non fever cas} \times f_{FF}(FF) \rceil$$

### Fever Duration

The game derives fever duration from a 15% base scaled by the approximate song length, then applies the Fever Time stat multiplier. The additive offset is the `+1000ms` song-length convention folded in as `+0.15`; decompiled server note-sequence scoring drains by event-time delta, so the `1/60` tick unit cancels and does not grant an extra duration tick:

$$\text{fever time cas} = (t_{last} \times 0.15) + 0.15$$

$$\text{fever duration} = \text{fever time cas} \times f_{FT}(FT)$$

### Fill Penalty (forced greats delay)

In-game powerbar fill is continuous, and Great contributes **half** the fill of Perfect.

Let:

$$\text{raw fill} = \text{non fever cas} \times f_{FF}(FF)$$

The number of hits required to activate fever when you force $k$ Greats (and the rest Perfects) before fever activates is:

$$\text{notes to fill}(k) = \lceil \text{raw fill} + 0.5k \rceil$$

Define the fill-penalty target (extra hits required vs all-Perfect):

$$fp(k) = \lceil \text{raw fill} + 0.5k \rceil - \lceil \text{raw fill} \rceil$$

Important: $\lceil a + b \rceil \neq \lceil a \rceil + \lceil b \rceil$ in general. The fractional part of `raw_fill` changes when a given number of Greats starts to increase `notes_to_fill`.

#### Activation Note Inclusion (Indexing)

The game scores each hit after updating powerbar state. On the server path, the order is effectively:

1) apply fill/drain for the hit
2) update the powerbar by delta time
3) score the hit

See `<redacted-place-path>`.

This means the hit that crosses the fill threshold is scored as a Fever note (activation is on the note itself).

However, the same ordering also creates a "transition note" after each fever window:
- The note where fever expires is scored as non-fever,
- but it did not contribute fill (because fill/drain was applied while still in fever).

Therefore the number of non-fever scored notes before the fever window begins is section-dependent:

- Section 1 (start of song): `notes_to_fill(k) - 1`
- Section 2+ (after a fever window): `notes_to_fill(k)`

Current behavior:
- The parity model includes both:
  - activation note is Fever, and
  - the transition-note effect after each fever window.

---

## Binary Search: Find Fever End

Given fever starts at note index $i$ at timestamp $t_i$:

$$\text{fever end time} = t_i + \text{fever duration}$$

Find $j$ such that:
$$t_j \geq \text{fever end time} \quad \text{and} \quad t_{j-1} < \text{fever end time}$$

**This uses `side="left"` binary search (>= condition)**

```python
j = binary_search_left(T, fever_end_time)
```

---

## Timeline Walk Algorithm

```
idx = 0                          # Current note index
fever_activations = 0            # Count of fever windows
section_number = 1               # Non-fever sections are 1-indexed
section_starts = []              # Where each non-fever section starts

WHILE idx < N:
    # Non-fever section: count scored notes until fever activates
    section_start = idx
    # Section 1: activation note is Fever -> advance by (notes_to_fill - 1)
    # Section 2+: there is one transition note that does not fill -> advance by notes_to_fill
    notes_needed = notes_to_fill(k) - 1 if section_number == 1 else notes_to_fill(k)
    
    idx += notes_needed
    
    IF idx >= N: BREAK  # Song ended before fever
    
    # Fever activates at note idx
    fever_start_time = T[idx]
    fever_end_time = fever_start_time + fever_duration
    
    # Binary search: find where fever ends
    fever_end_idx = binary_search_left(T, fever_end_time)
    
    section_starts.append(section_start)
    fever_activations += 1
    idx = fever_end_idx  # Jump past fever window
    section_number += 1
```

---

## Breakpoint Detection (Analytical)

A **breakpoint** at forced count $k$ exists if:

$$\text{new section start}(k) \neq \text{new section start}(k-1)$$

Where:
$$\text{new section start}(k) = \text{baseline start} + \left(\text{notes to fill}(k) - \text{notes to fill}(0)\right)$$

### Optimization Insight

Since $fp(k)$ increases in discrete steps:

$$\text{Breakpoints} = \{0\} \cup \{k : fp(k) \neq fp(k-1)\}$$

The Force Great solver enumerates breakpoint configs in **FP-target space** (per-section extra hits), then converts FP targets back into Great counts for output and scoring. That inverse depends on `raw_fill`.

---

## Score Impact

### Perfect Note Value
$$V_{perfect} = (P_{val} \times 2 + S_{val} + PP_{bonus}) \times \text{combo multiplier}$$

### Great Note Value (forced great)
$$V_{great} = \left\lfloor (P_{val} \times 2 + S_{val}) \times \frac{2}{3} + 150 \right\rfloor \times \text{combo multiplier}$$

### Score Penalty per Forced Great
$$\text{penalty} = V_{perfect} - V_{great}$$

### Fill Penalty
Fill penalty is represented by the altered fever timeline (fewer Fever notes / more Normal notes). It should not be applied as an additional independent subtraction on top of the timeline-derived base score.

---

## Total FG Evaluation

For a config $C = [c_0, c_1, ..., c_S]$ (forced greats per section):

1) Build the fever timeline implied by the config (via `notes_to_fill(k)` for each section).  
2) Compute the base score for that timeline assuming Perfect hits.  
3) Subtract Great penalties for the forced Great notes.

In other words (high level):

$$\text{total score}(C) = \text{score from timeline}(C) - \sum_{s=0}^{S}\sum_{i \in \text{forced great notes}(s)} \left(V_{perfect,i} - V_{great,i}\right)$$

The optimizer finds $C^*$ that maximizes $\text{total score}$.

Penalty placement for forced Greats
- Section 1 (start of song): penalties start at `section_start`.
- Section 2+ (after a fever window): penalties start at `section_start + 1` because the
  first non-fever note is the transition note and does not contribute fill.

Implementation Note
- If you see any document claiming `fill_penalty(k) = ceil(k / non_fever_great_to_fill)`, treat it as outdated: the current solver uses `notes_to_fill(k) = ceil(raw_fill + 0.5k)` and derives FP targets from that.
