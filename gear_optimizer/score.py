"""Exact scores: the game's per-note integer scoring, computed in float64 like the game's numbers.

A Perfect is worth base = 2 x primary element + secondary element + the Perfect Points bonus. The combo
multiplier ramps in over the first HEAD_NOTES notes and applies in full after them; notes inside a
fever window are also multiplied by the fever multiplier. Every note's value is floored on its own, so the
operation order below is part of the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any

import numpy as np

from .gamedata import StatCurves

HEAD_NOTES = 100
# A Great is worth 4/3 x primary + 2/3 x secondary + GREAT_POINTS before multipliers.
GREAT_POINTS = 150


@dataclass(frozen=True, slots=True)
class Factors:
    """What a stat row contributes to scoring on one song."""

    base: float
    combo: float
    fever: float
    great_base: int
    fever_time_row: int
    fever_fill_row: int


def factors(stats: dict[str, int], curves: StatCurves, primary: str, secondary: str) -> Factors:
    """Scoring factors for a stat row on a song with the given primary/secondary elements.

    A one-color song names its primary as its secondary too, so its base is 3 x the element.
    """
    primary_value = stats.get(primary, 0)
    secondary_value = stats.get(secondary, 0)
    return Factors(
        base=float(primary_value * 2 + secondary_value) + curves.factor("Perfect Points", stats["Perfect Points"]),
        combo=curves.factor("Combo Multiplier", stats["Combo Multiplier"]),
        fever=curves.factor("Fever Multiplier", stats["Fever Multiplier"]),
        great_base=(primary_value * 2 if primary == secondary else floor(float(primary_value) * (4.0 / 3.0)) + floor(float(secondary_value) * (2.0 / 3.0))) + GREAT_POINTS,
        fever_time_row=stats["Fever Time"],
        fever_fill_row=stats["Fever Fill Rate"],
    )


def _head_scaling(f: Factors, head_len: int) -> np.ndarray:
    """Per-position combo ramp of the head notes: 1 + (combo - 1) / 100 x position."""
    positions = np.arange(1, head_len + 1, dtype=np.float64)
    return ((f.combo - 1.0) / 100.0) * positions + 1.0


@dataclass(frozen=True, slots=True)
class TimelineCell:
    """The timing frontier's surfaces for one (Fever Time, Fever Fill) cell.

    head_words: (n, 4) uint32 bitmask of the head notes inside fever windows.
    body_fever / body_normal: (n,) counts of the notes after the head inside / outside fever.
    """

    head_words: np.ndarray
    body_fever: np.ndarray
    body_normal: np.ndarray


def single_surface_cell(head_in_fever: np.ndarray, body_fever: int, body_normal: int) -> TimelineCell:
    """A TimelineCell holding one fixed surface: which head notes are in fever, and the body counts."""
    words = np.zeros((1, 4), dtype=np.uint64)
    for note in np.flatnonzero(head_in_fever):
        # Bit k of word w marks head note 32 * w + k.
        words[0, note // 32] |= np.uint64(1) << np.uint64(note % 32)
    return TimelineCell(
        head_words=words,
        body_fever=np.asarray([body_fever], dtype=np.int64),
        body_normal=np.asarray([body_normal], dtype=np.int64),
    )


def timeline_cell(payload: Any, fever_time_row: int, fever_fill_row: int, max_row: int) -> tuple[TimelineCell, int]:
    """Read one cell of a timing frontier payload; returns the cell and its first pool index."""
    ft = max(0, min(int(fever_time_row), max_row))
    ff = max(0, min(int(fever_fill_row), max_row))
    count = int(payload.grid_frontier_count[0, ft, ff])
    offset = int(payload.grid_frontier_offset[0, ft, ff])
    if count <= 0 or offset < 0 or offset + count > int(payload.frontier_pool_used):
        raise ValueError(f"timing frontier cell ({ft}, {ff}) has no valid surface range")
    end = offset + count
    cell = TimelineCell(
        head_words=np.asarray(payload.grid_frontier_masks_bits_pool[0, offset:end, :4], dtype=np.uint64),
        body_fever=np.asarray(payload.grid_frontier_body_fever_pool[0, offset:end], dtype=np.int64),
        body_normal=np.asarray(payload.grid_frontier_body_normal_pool[0, offset:end], dtype=np.int64),
    )
    return cell, offset


def best_timeline_score(f: Factors, cell: TimelineCell, total_notes: int) -> tuple[int, int]:
    """Best score over a cell's surfaces, and the index of the first surface reaching it."""
    body_total = max(0, total_notes - HEAD_NOTES)
    if np.any(cell.body_fever < 0) or np.any(cell.body_normal < 0) or np.any(
        cell.body_fever + cell.body_normal != body_total
    ):
        raise ValueError("timing surface body counts do not match the song's body note count")
    combo_value = np.int64(floor(f.base * f.combo))
    fever_value = np.int64(floor(f.base * f.combo * f.fever))
    scores = cell.body_fever * fever_value + cell.body_normal * combo_value

    head_len = min(total_notes, HEAD_NOTES)
    perfect = f.base * _head_scaling(f, head_len)
    normal = np.floor(perfect).astype(np.int64)
    fever = np.floor(perfect * f.fever).astype(np.int64)
    notes = np.arange(head_len)
    head_bits = (cell.head_words[:, notes // 32] >> (notes % 32).astype(np.uint64)) & np.uint64(1)
    scores = scores + np.int64(normal.sum()) + head_bits.astype(np.int64) @ (fever - normal)
    best = int(np.argmax(scores))
    return int(scores[best]), best


def fg_surface_score(f: Factors, surface: Any, total_notes: int) -> int:
    """Exact score of a Force Great response surface (fever and Great masks over the head notes, plus
    body counts of fever notes, Great notes and notes that are both)."""
    head_len = min(total_notes, HEAD_NOTES)
    body_total = max(0, total_notes - HEAD_NOTES)
    body_fever, body_great, body_fever_great = surface.body_fever, surface.body_great, surface.body_fever_great
    if (
        min(body_fever, body_great, body_fever_great) < 0
        or body_fever_great > min(body_fever, body_great)
        or body_fever + body_great - body_fever_great > body_total
    ):
        raise ValueError("Force Great surface body counts do not match the song's body note count")

    combo_value = floor(f.base * f.combo)
    fever_value = floor(f.base * f.combo * f.fever)
    great = float(f.great_base)
    normal_great_loss = max(0, combo_value - floor(great * f.combo))
    fever_great_loss = max(0, fever_value - floor(great * f.combo * f.fever))
    score = body_fever * fever_value + (body_total - body_fever) * combo_value
    score -= (body_great - body_fever_great) * normal_great_loss + body_fever_great * fever_great_loss

    fever_words = (surface.fever0, surface.fever1, surface.fever2, surface.fever3)
    great_words = (surface.great0, surface.great1, surface.great2, surface.great3)
    slope = (f.combo - 1.0) / 100.0
    for note in range(head_len):
        in_fever = (fever_words[note // 32] >> (note % 32)) & 1
        is_great = (great_words[note // 32] >> (note % 32)) & 1
        scaling = slope * float(note + 1) + 1.0
        perfect = f.base * scaling
        value = floor(perfect * f.fever) if in_fever else floor(perfect)
        if is_great:
            great_value = great * scaling
            great_value = floor(great_value * f.fever) if in_fever else floor(great_value)
            value -= max(0, value - great_value)
        score += value
    return score
