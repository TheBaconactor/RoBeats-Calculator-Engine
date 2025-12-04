# Great Penalty Implementation Documentation

## Overview

This document describes the great judgement penalty logic implemented in the Manual Calculator scripts for accurately calculating scores when players hit "great" judgements instead of "perfect" judgements.

## The Problem

When a player hits a "great" instead of a "perfect", two penalties are applied:
1. **Fill Penalty**: Delays fever activation by requiring more notes to fill the fever bar
2. **Score Penalty**: Reduces the score for that note compared to a perfect

Without accounting for these penalties, calculated scores don't match actual in-game results.

## Formula Breakdown

### Great Judgement Penalty Base

The base penalty value is calculated from the song's elemental colors:

```python
great_judgement_penalty_base = floor((primary_elemental * 2 + secondary_elemental) * (2/3) + 150)
```

Where:
- `primary_elemental`: Player's stat points in the song's primary color
- `secondary_elemental`: Player's stat points in the song's secondary color

### Penalty Variants

The base penalty is scaled by combo and fever multipliers:

```python
great_judgement_penalty_combo = floor(great_judgement_penalty_base * combo_mul)
great_judgement_penalty_fever = floor(great_judgement_penalty_base * combo_mul * fever_mul)
```

**Important**: These values represent the **score of a great note**, NOT the penalty itself.

### Actual Score Penalty

The penalty uses **ramping values** for notes 0-99 and **flat values** for notes 100+:

```python
def calculate_great_penalty_for_notes(start_note_idx, greats_count, ...):
    for i in range(greats_count):
        note_idx = start_note_idx + i
        
        if note_idx < 100:
            # Ramping penalty for first 100 notes
            scaling_factor = 1 + (combo_mul - 1) * (note_idx + 1) / 100
            perfect_at_note = floor(base_value * scaling_factor)
            great_at_note = floor(great_judgement_penalty_base * scaling_factor)
            penalty_at_note = perfect_at_note - great_at_note
        else:
            # Flat penalty for notes 100+
            penalty_at_note = combo_value - great_judgement_penalty_combo
```

**Greats are prioritized at the earliest notes** (lowest penalty first).

**Example (note 0 vs note 100+)**:
- Note 0: `scaling = 1.016`, `perfect = 2616`, `great = 1664`, penalty = **952**
- Note 100+: `perfect = 6692`, `great = 4257`, penalty = **2435**

## Fill Penalty Calculation

When greats are hit in a non-fever section, the fever bar takes longer to fill:

```python
great_fill_penalty = ceil(max(0, non_fever_base * (1/non_fever_great_to_fill) * forced_greats_count))
```

Where:
- `non_fever_base = ceil((total_notes - long_notes) * 0.333 * fever_fill)`
- `non_fever_great_to_fill = ceil(non_fever_base * 2)`

This adds extra notes to the non-fever section before fever activates.

## Implementation Differences

### Original.py (Full Implementation)

Includes:
- Complex fever offset pattern (+2/-2 alternating based on fever count)
- Great penalty logic (fill + score)
- Helper functions for deduplication
- Debug flag for toggling output

### Original - Copy.py (Simple Implementation)

Includes:
- Simple fever adjustment: `if loop > 1: new_score += combo_value - fever_value`
- Great penalty logic (fill + score)
- No complex offset pattern

Use Original.py for accurate score matching with the game.
Use Original - Copy.py for simpler calculations or testing.

## Configuration

Greats are configured in `config.ini`:

```ini
[ForceGreats]
NonFever1=0
NonFever2=1
NonFever3=0
NonFever4=0
```

Each value represents the number of great judgements in that non-fever section.

## Code Structure

### Helper Functions (Original.py)

```python
def check_offset_changes_score(current_notes, total_notes, base_notes, offset, combo_value, first_100_values):
    """Check if applying an offset to note count changes the score."""

def get_non_fever_notes_and_offset(fever_count, non_fever_base):
    """Returns (notes_count, offset_value) based on fever count."""

def get_fever_check_offset(fever_count):
    """Returns the offset to check for fever score adjustment decision."""

def should_apply_fever_adjustment(fever_count, offset_changes_score):
    """Determine if fever score adjustment should be applied."""

def debug_print(message):
    """Print debug message only if DEBUG_OUTPUT is enabled."""
```

### Debug Output Control

```python
DEBUG_OUTPUT = True  # Set to False to suppress debug prints
```

## Validated Test Cases

### Astar (Normal) with 1 Great in NonFever2

| Metric | Value |
|--------|-------|
| Base Score (no greats) | 9,108,171 |
| Fill Penalty | 1 note |
| Score Penalty | 2,435 |
| Final Score | 9,105,736 |

### Penalty Breakdown

- `great_judgement_penalty_base` = 1638
- `great_judgement_penalty_combo` = 4257
- `combo_value` = 6692
- `actual_penalty` = 6692 - 4257 = 2435

## Common Mistakes

1. **Using great_value as penalty**: The penalty is NOT the great value itself, but the DIFFERENCE between perfect and great values.

   ```python
   # WRONG
   penalty = great_judgement_penalty_combo  # 4257
   
   # CORRECT
   penalty = combo_value - great_judgement_penalty_combo  # 2435
   ```

2. **Forgetting fill penalty**: Greats don't just reduce score, they also delay fever activation by adding notes to non-fever sections.

## Integration with Main.py (Future)

For GA optimization, the great penalty logic needs to be adapted for the vectorized approach:
- Main.py uses pre-computed fever masks instead of loops
- The fill penalty affects fever timing indices
- The score penalty can be applied post-calculation

This integration is planned for future implementation.

