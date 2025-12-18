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
| $f_{FT}(x)$ | Fever Time lookup: stat → multiplier |
| $f_{FF}(x)$ | Fever Fill Rate lookup: stat → multiplier |

---

## Core Formulas

### Fill Rate (notes to trigger fever)

$$\text{non\_fever\_cas} = (N - L) \times 0.333$$

$$\text{non\_fever\_base} = \lceil \text{non\_fever\_cas} \times f_{FF}(FF) \rceil$$

### Fever Duration

$$\text{fever\_duration} = t_{last} \times f_{FT}(FT)$$

### Fill Penalty (forced greats delay)

$$\text{non\_fever\_great\_to\_fill} = \lceil \text{non\_fever\_cas} \times f_{FF}(FF) \times 2 \rceil$$

$$\text{fill\_penalty}(k) = \left\lceil \frac{k}{\text{non\_fever\_great\_to\_fill}} \right\rceil$$

Where $k$ = number of forced greats in section.

---

## Binary Search: Find Fever End

Given fever starts at note index $i$ at timestamp $t_i$:

$$\text{fever\_end\_time} = t_i + \text{fever\_duration}$$

Find $j$ such that:
$$t_j \geq \text{fever\_end\_time} \quad \text{and} \quad t_{j-1} < \text{fever\_end\_time}$$

**This uses `side="left"` binary search (≥ condition)**

```python
j = binary_search_left(T, fever_end_time)
```

---

## Timeline Walk Algorithm

```
idx = 0                          # Current note index
fever_activations = 0            # Count of fever windows
section_starts = []              # Where each non-fever section starts

WHILE idx < N:
    # Non-fever section: count notes until bar fills
    section_start = idx
    notes_needed = non_fever_base - 1  (first section) 
                   OR non_fever_base   (later sections)
    
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
```

---

## Breakpoint Detection (Analytical)

A **breakpoint** at forced count $k$ exists if:

$$\text{new\_section\_start}(k) \neq \text{new\_section\_start}(k-1)$$

Where:
$$\text{new\_section\_start}(k) = \text{baseline\_start} + k + \text{fill\_penalty}(k)$$

### Optimization Insight

Since $\text{fill\_penalty}(k)$ increases in discrete steps:

$$\text{Breakpoints} = \{0\} \cup \{k : \text{fill\_penalty}(k) \neq \text{fill\_penalty}(k-1)\}$$

The fill penalty increases every $\text{non\_fever\_great\_to\_fill}$ forced greats.

---

## Score Impact

### Perfect Note Value
$$V_{perfect} = (P_{val} \times 2 + S_{val} + PP_{bonus}) \times \text{combo\_multiplier}$$

### Great Note Value (forced great)
$$V_{great} = \left\lfloor (P_{val} \times 2 + S_{val}) \times \frac{2}{3} + 150 \right\rfloor \times \text{combo\_multiplier}$$

### Score Penalty per Forced Great
$$\text{penalty} = V_{perfect} - V_{great}$$

### Fill Penalty (extra perfects lost)
$$\text{fill\_penalty\_score} = \text{fill\_penalty}(k) \times V_{perfect}$$

---

## Total FG Evaluation

For a config $C = [c_0, c_1, ..., c_S]$ (forced greats per section):

$$\text{total\_score} = \text{base\_score} - \sum_{s=0}^{S} \left( c_s \times \text{penalty}_s + \text{fill\_penalty}(c_s) \times V_{perfect} \right)$$

The optimizer finds $C^*$ that maximizes $\text{total\_score}$.
