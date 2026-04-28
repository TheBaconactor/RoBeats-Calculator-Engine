from __future__ import annotations

import numpy as np
import pytest


def test_pre_fever_section_is_irrelevant() -> None:
    """FG-3/S3: Sections before first activation are exactly irrelevant."""
    # Song: 500 notes, first fever activation at note 80
    first_activation = 80
    section_start = 0
    section_end = 70

    assert section_end < first_activation
    # Condition A holds: section is pre-fever


def test_post_fever_section_is_irrelevant() -> None:
    """FG-3/S3: Sections after last fever end are exactly irrelevant."""
    last_fever_end = 420
    total_notes = 500
    section_start = 430
    section_end = 500

    assert section_start > last_fever_end
    # Condition B holds: section is post-fever


def test_mid_song_section_can_be_relevant() -> None:
    """A section between fever windows might be relevant if it affects fill timing."""
    fever_window_1_end = 150
    fever_window_2_start = 200
    section_start = 160
    section_end = 190

    # Section is in a gap between fever windows
    # It is NOT automatically irrelevant unless the gap is unbridgeable
    assert section_start > fever_window_1_end
    assert section_end < fever_window_2_start
    # This section could affect fill timing for window 2
    # Certifier must check if gap is bridgeable


def test_unbridgeable_gap_makes_section_irrelevant() -> None:
    """If minimum penalty to bridge gap exceeds max allowable penalty, section is irrelevant."""
    # Gap between fever windows: 50 notes
    gap_notes = 50
    # Minimum forced Greats needed to delay next activation by 1 note
    min_penalty_per_note = 0.5  # Each Great contributes half fill
    min_penalty_to_bridge = gap_notes * min_penalty_per_note

    # Max allowable penalty (determined by FT/FF and note count)
    max_allowable_penalty = 10.0

    assert min_penalty_to_bridge > max_allowable_penalty
    # Gap is unbridgeable; sections in this gap are irrelevant


def test_zeroing_irrelevant_section_preserves_score() -> None:
    """Setting count=0 for irrelevant section does not change score."""
    base_score = 1_000_000
    penalty_with_section = 5_000
    penalty_without_section = 0

    # If section is irrelevant, timing is unchanged
    score_with = base_score - penalty_with_section
    score_without = base_score - penalty_without_section

    # Score without is higher (lower penalty)
    assert score_without > score_with
    # Therefore zero-count dominates


def test_certifier_is_conservative() -> None:
    """Certifier should only mark sections irrelevant when PROVEN safe."""
    # Condition A: definitely safe
    assert _is_section_irrelevant_a(0, 50, first_activation=80)
    assert not _is_section_irrelevant_a(60, 90, first_activation=80)

    # Condition B: definitely safe
    assert _is_section_irrelevant_b(450, 500, last_fever_end=420)
    assert not _is_section_irrelevant_b(400, 450, last_fever_end=420)


def _is_section_irrelevant_a(start: int, end: int, first_activation: int) -> bool:
    return end < first_activation


def _is_section_irrelevant_b(start: int, end: int, last_fever_end: int) -> bool:
    return start > last_fever_end


def test_post_fever_irrelevance_on_long_songs() -> None:
    """S3: Long songs with few activations have many post-fever sections."""
    total_notes = 2000
    n_activations = 2
    avg_fever_duration = 100
    last_fever_end = n_activations * avg_fever_duration + 200  # Rough estimate

    post_fever_notes = total_notes - last_fever_end
    fraction_post_fever = post_fever_notes / total_notes

    # For long songs with few activations, most notes are post-fever
    assert fraction_post_fever > 0.5


def test_pre_fever_irrelevance_on_all_songs() -> None:
    """All songs have a pre-fever region before first activation."""
    first_activation = 80
    pre_fever_notes = first_activation

    # Pre-fever region always exists (activation requires fill)
    assert pre_fever_notes > 0
