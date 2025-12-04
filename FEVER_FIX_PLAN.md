# Fever Calculation Fix - Main.py Update Plan

## Summary

The fever calculation in Main.py has two bugs that cause score mismatches with the server:
1. **Binary search condition**: Using `>` instead of `>=` for fever end detection
2. **Non-fever note count**: Always using `-1` instead of section-aware logic

The old "adjustment patch" (`fever_activations_count - 1`) was a workaround that can be removed once the root cause is fixed.

---

## Root Cause Analysis

### Server Behavior (from Roblox source)

The server drains fever bar based on **actual time between notes**:

```lua
-- Server calls update with real deltaTime
PowerState:update(deltaTime)  -- Drains bar by deltaTime/duration
```

Fever ends when: `elapsed_time >= real_fever_time`

### The "Wasted Note" Issue

When fever ends mid-song:
1. The note where fever ends is marked as **non-fever**
2. But that note **doesn't contribute a fill** (fever was still active at start of processing)
3. So subsequent non-fever sections need +1 note

---

## Changes Required

### 1. Fix `calculate_fever_timeline_indices` (lines 942-986)

**Current (WRONG):**
```python
def calculate_fever_timeline_indices(...):
    non_fever_cas = (total_notes - long_notes_count) * 0.333
    notes_to_fill_fever = ceil(non_fever_cas * fever_fill_rate) - 1  # Always -1
    ...
    while current_note_idx < total_notes:
        end_normal_idx = min(current_note_idx + notes_to_fill_fever, total_notes)
        ...
        fever_end_idx = np.searchsorted(song_timestamps, end_time, side="right")  # > (wrong)
```

**Fixed:**
```python
def calculate_fever_timeline_indices(...):
    non_fever_cas = (total_notes - long_notes_count) * 0.333
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    ...
    fever_section = 0
    while current_note_idx < total_notes:
        fever_section += 1
        # First section: -1, Later sections: use base (wasted note effect)
        if fever_section == 1:
            notes_to_fill = non_fever_base - 1
        else:
            notes_to_fill = non_fever_base
        
        end_normal_idx = min(current_note_idx + notes_to_fill, total_notes)
        ...
        fever_end_idx = np.searchsorted(song_timestamps, end_time, side="left")  # >= (correct)
```

### 2. Fix `fast_calculate_score` (lines 992-1025)

**Current (has workaround patch):**
```python
@jit(nopython=True, cache=True)
def fast_calculate_score(
    base_value,
    combo_mul,
    fever_mul,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
    fever_activations_count,  # <-- Used for patch
):
    ...
    # OLD PATCH - REMOVE THIS
    if fever_activations_count > 1:
        diff = combo_val_per_note - fever_val_per_note
        body_score += diff * (fever_activations_count - 1)
    ...
```

**Fixed:**
```python
@jit(nopython=True, cache=True)
def fast_calculate_score(
    base_value,
    combo_mul,
    fever_mul,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
):  # <-- Remove fever_activations_count parameter
    ...
    # REMOVE the adjustment block entirely
    # (No longer needed - timeline is now correct)
    ...
```

### 3. Update All Callers of `fast_calculate_score`

Search for all usages and remove the `fever_activations` argument:

**Locations to update:**
- `optimize_core_jit` function call
- Any other direct calls to `fast_calculate_score`

---

## Formula Summary

### Non-Fever Notes Per Section
| Section | Notes | Reason |
|---------|-------|--------|
| 1 (start of song) | `ceil(X) - 1` | All notes fill, fever activates on ceil(X)th |
| 2+ (after fever) | `ceil(X)` | 1 wasted note + normal fills |

Where `X = (total_notes - long_notes) × 0.333 × fever_fill_rate`

### Fever End Detection
```
Binary search for first note where: time[i] >= start_time + real_fever_time
That note is NOT in fever.
```

- **OLD**: `np.searchsorted(..., side="right")` → finds `>`
- **NEW**: `np.searchsorted(..., side="left")` → finds `>=`

### Fever Duration
```
fever_time_cas = last_note_time × 0.15 + 0.15
real_fever_time = fever_time_cas × fever_time_stat
```

---

## Validation

The fix was validated against the server simulation with **4,270 test combinations**:
- Fill rates: 0.01 to 1.5 (systematic + random)
- Fever times: 0.1 to 10.0 (systematic + random)

**Result: ✅ ALL 4,270 TESTS PASSED**

---

## Files to Modify

1. **Manual_Calculator - Main.py**
   - `calculate_fever_timeline_indices` function
   - `fast_calculate_score` function
   - `optimize_core_jit` function (caller)
   - Any other callers of `fast_calculate_score`

---

## Verification After Changes

Run the calculator and verify:
1. Score matches target: **20,226,825** (for Irish Meadow Dance test case)
2. Section breakdown matches:
   - Section 01 [Non-Fever]: 56 notes
   - Section 02 [Fever]: 178 notes
   - Section 03 [Non-Fever]: 57 notes
   - Section 04 [Fever]: 202 notes
   - Section 05 [Non-Fever]: 57 notes
   - Section 06 [Fever]: 210 notes
   - Section 07 [Non-Fever]: 5 notes
