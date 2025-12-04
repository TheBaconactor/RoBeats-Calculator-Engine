# Fever Offset Implementation Documentation

## Overview

This document describes the fever fill activation offset logic implemented in `Manual_Calculator - Original.py` for calculating accurate scores across infinite fever cycles.

## The Problem

When calculating scores for songs with multiple fever activations, the game applies different offset rules for determining when fever fills are activated. Without accounting for these offsets, the calculated scores don't match actual in-game results.

## The Solution: Fever Duration Offset Rules

Based on empirical testing, the following rules were discovered:

### Offset Pattern

| Fever # | Non-Fever Section | Offset Applied | Notes |
|---------|-------------------|----------------|-------|
| 1st     | Section 01        | None           | Base calculation |
| 2nd     | Section 03        | None           | But check +2 effect |
| 3rd     | Section 05        | +2             | After 2nd fever |
| 4th     | Section 07        | -2             | After 3rd fever |
| 5th     | Section 09        | +2             | After 4th fever |
| ...     | ...               | Alternates     | +2/-2 pattern continues |

### Pattern Summary

- **After even fevers (2nd, 4th, 6th...)**: Apply **+2** offset to non-fever note count
- **After odd fevers ≥3 (3rd, 5th, 7th...)**: Apply **-2** offset to non-fever note count

## Score Adjustment Logic

The `combo_value - fever_value` adjustment is applied to fever scores based on whether the offset would change the following non-fever section's score:

### Even Fevers (2nd, 4th, 6th...)
- Check if **+2 offset** would change the next non-fever's score
- If offset **DOESN'T** change score → **Apply** adjustment
- If offset **DOES** change score → **Don't apply** adjustment

### Odd Fevers ≥3 (3rd, 5th, 7th...)
- Check if **-2 offset** would change the next non-fever's score
- If offset **DOES** change score → **Apply** adjustment
- If offset **DOESN'T** change score → **Don't apply** adjustment

## Code Implementation

### Key Variables

```python
fever_count = 0  # Tracks completed fevers
non_fever_base = ceil((total_notes - long_notes) * 0.333 * fever_fill) - 1
```

### Non-Fever Section Offset Logic

```python
if fever_count == 0:
    # Before 1st fever - no offset
    non_fever = non_fever_base
elif fever_count == 1:
    # Before 2nd fever - no offset, but check +2 for adjustment decision
    non_fever = non_fever_base
elif fever_count % 2 == 0:
    # After even fevers (2nd, 4th, etc.): +2 offset
    non_fever = non_fever_base + 2
else:
    # After odd fevers ≥3 (3rd, 5th, etc.): -2 offset
    non_fever = non_fever_base - 2
```

### Fever Score Adjustment Logic

```python
if loop > 1:  # Not first fever
    # Calculate where next non-fever starts
    next_non_fever_start = current_notes + notes
    
    # Determine offset to check
    if fever_count % 2 == 0:
        check_offset = 2   # Even fevers check +2
    else:
        check_offset = -2  # Odd fevers check -2
    
    # Compare scores with and without offset
    score_with_offset = calculate_non_fever_score(next_non_fever_start, non_fever_base + check_offset, ...)
    score_without_offset = calculate_non_fever_score(next_non_fever_start, non_fever_base, ...)
    offset_changes_score = (score_with_offset != score_without_offset)
    
    # Apply adjustment based on fever type
    if fever_count % 2 == 0:
        # Even fever: apply if offset DOESN'T change score
        if not offset_changes_score:
            new_score += combo_value - fever_value
    else:
        # Odd fever: apply if offset DOES change score
        if offset_changes_score:
            new_score += combo_value - fever_value
```

## Validated Test Cases

### Astar (Normal)
- **non_fever_base**: 41
- **Fever 2**: Adjustment applied (offset +2 doesn't change score due to song end)
- **Expected Total**: 9,136,470 ✓

### Broken Utopia (Normal)
- **non_fever_base**: 71
- **Section 05**: 73 notes (+2 offset)
- **Fever 2**: No adjustment (offset +2 changes score)
- **Fever 3**: No adjustment (offset -2 doesn't change score)
- **Expected Total**: 24,160,506 ✓

## Why This Works

The offset logic accounts for how the game internally tracks fever fill progression. When the offset produces the same score (typically at song boundaries where notes are truncated), the adjustment compensates for the rounding difference in fever activation timing. When the offset produces a different score, the notes actually shift and no compensation is needed.

## Debug Output

The implementation includes debug prints to trace the logic:

```
[Debug] Fever 1: NOT applying adjustment (loop=1)
[Debug] Non-fever before Fever 2: no offset applied, but +2 would_change_score=True
[Debug] Fever 2: NOT applying adjustment (even fever, offset +2 changes score)
[Debug] Non-fever after Fever 2: offset +2, notes=73, offset_changed_score=True
[Debug] Fever 3: NOT applying adjustment (odd fever, offset -2 same score)
```

## Original Note Reference

From `NOTE TO SELF.txt`:
```
2nd fever duration: for fever fill activation, offset the indexing by +2.
3rd fever duration: for fever fill activation, offset the indexing by -2.
```

This cryptic note led to the discovery of the alternating +2/-2 offset pattern for infinite fever cycles.
