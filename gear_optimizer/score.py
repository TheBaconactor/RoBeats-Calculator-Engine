"""Exact scores: the game's per-note integer scoring, computed in float64 like the game's numbers.

A Perfect is worth base = 2 x primary element + secondary element + the Perfect Points bonus. The combo
multiplier ramps in over the first HEAD_NOTES notes (the game's line through its combo thresholds,
gamedata.StatCurves.combo_ramp) and applies in full after them; notes inside a fever window are also
multiplied by the fever multiplier. Every note's value is floored on its own, so the operation order
below is part of the result.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import floor
from typing import Any

import numpy as np

from .core.jit_setup import jit
from numba.cpython.unsafe.numbers import trailing_zeros
from .gamedata import COMBO_RAMP_NOTES, StatCurves
from .rules import MAX_STAT

HEAD_NOTES = COMBO_RAMP_NOTES
# A Great is worth 4/3 x primary + 2/3 x secondary + GREAT_POINTS before multipliers.
GREAT_POINTS = 150


@dataclass(frozen=True, slots=True, eq=False)
class Factors:
    """What a stat row contributes to scoring on one song."""

    base: float
    combo: float  # the combo multiplier after the head notes
    ramp: np.ndarray  # the combo multiplier at head notes 1..HEAD_NOTES
    fever: float
    great_base: int
    fever_time_row: int
    fever_fill_row: int


def factors(stats: Mapping[str, Any], curves: StatCurves, primary: str, secondary: str) -> Factors:
    """Scoring factors for a stat row on a song with the given primary/secondary elements.

    A one-color song names its primary as its secondary too, so its base is 3 x the element.
    """
    primary_value = int(stats.get(primary) or 0)
    secondary_value = int(stats.get(secondary) or 0)
    pp = int(stats.get("Perfect Points") or 0)
    cm = int(stats.get("Combo Multiplier") or 0)
    fm = int(stats.get("Fever Multiplier") or 0)
    ft = int(stats.get("Fever Time") or 0)
    ff = int(stats.get("Fever Fill Rate") or 0)
    f64 = curves.f64
    pp_i = 0 if pp < 0 else (MAX_STAT if pp > MAX_STAT else pp)
    cm_i = 0 if cm < 0 else (MAX_STAT if cm > MAX_STAT else cm)
    fm_i = 0 if fm < 0 else (MAX_STAT if fm > MAX_STAT else fm)
    return Factors(
        base=float(primary_value * 2 + secondary_value) + float(f64["Perfect Points"][pp_i]),
        combo=float(f64["Combo Multiplier"][cm_i]),
        ramp=curves.combo_ramp[cm_i],
        fever=float(f64["Fever Multiplier"][fm_i]),
        great_base=(primary_value * 2 if primary == secondary else floor(float(primary_value) * (4.0 / 3.0)) + floor(float(secondary_value) * (2.0 / 3.0))) + GREAT_POINTS,
        fever_time_row=ft,
        fever_fill_row=ff,
    )


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
        head_words=payload.grid_frontier_masks_bits_pool[0, offset:end, :4],
        body_fever=payload.grid_frontier_body_fever_pool[0, offset:end],
        body_normal=payload.grid_frontier_body_normal_pool[0, offset:end],
    )
    return cell, offset


@jit(nopython=True, cache=True, nogil=True)
def _best_timeline_score_numba(head_words, body_fever, body_normal, scalars, ramp, total_notes):
    base, combo, fever = scalars
    head_len = min(total_notes, HEAD_NOTES)
    body_total = max(0, total_notes - HEAD_NOTES)
    n_surfaces = body_fever.shape[0]
    combo_value = np.int64(floor(base * combo))
    fever_value = np.int64(floor(base * combo * fever))
    normal_sum = np.int64(0)
    diff = np.empty(head_len, dtype=np.int64)
    for i in range(head_len):
        perfect = base * ramp[i]
        normal_val = np.int64(floor(perfect))
        normal_sum += normal_val
        diff[i] = np.int64(floor(perfect * fever)) - normal_val
    best_score = np.int64(0)
    best_idx = -1
    for s in range(n_surfaces):
        bf = np.int64(body_fever[s])
        bn = np.int64(body_normal[s])
        if bf < 0 or bn < 0 or bf + bn != body_total:
            return np.int64(-1), -2
        sc = bf * fever_value + bn * combo_value + normal_sum
        for w in range(4):
            word = np.uint64(head_words[s, w]) & np.uint64(0xFFFFFFFF)
            word_base = w << 5
            while word:
                idx = word_base + np.int64(trailing_zeros(word))
                if idx < head_len:
                    sc += diff[idx]
                word &= word - np.uint64(1)
        if best_idx < 0 or sc > best_score:
            best_score = sc
            best_idx = s
    return best_score, best_idx


def best_timeline_score(f: Factors, cell: TimelineCell, total_notes: int) -> tuple[int, int]:
    """Best score over a cell's surfaces, and the index of the first surface reaching it."""
    best_score, best_idx = _best_timeline_score_numba(
        cell.head_words, cell.body_fever, cell.body_normal, (f.base, f.combo, f.fever), f.ramp, int(total_notes)
    )
    if best_idx == -2:
        raise ValueError("timing surface body counts do not match the song's body note count")
    if best_idx < 0:
        raise ValueError("attempt to get argmax of an empty sequence")
    return int(best_score), int(best_idx)


@jit(nopython=True, cache=True, nogil=True)
def _fg_surface_score_numba(scalars, ramp, fever_words, great_words, body_counts, total_notes):
    base, combo, fever, great = scalars
    body_fever, body_great, body_fever_great = body_counts
    head_len = min(total_notes, HEAD_NOTES)
    body_total = max(0, total_notes - HEAD_NOTES)
    combo_value = np.int64(floor(base * combo))
    fever_value = np.int64(floor(base * combo * fever))
    normal_great_loss = max(np.int64(0), combo_value - np.int64(floor(great * combo)))
    fever_great_loss = max(np.int64(0), fever_value - np.int64(floor(great * combo * fever)))
    score = body_fever * fever_value + (body_total - body_fever) * combo_value
    score -= (body_great - body_fever_great) * normal_great_loss + body_fever_great * fever_great_loss
    for note in range(head_len):
        wi = note >> 5
        bit = note & 31
        in_fever = (fever_words[wi] >> bit) & 1
        is_great = (great_words[wi] >> bit) & 1
        scaling = ramp[note]
        perfect = base * scaling
        value = np.int64(floor(perfect * fever)) if in_fever else np.int64(floor(perfect))
        if is_great:
            great_val = great * scaling
            gv = np.int64(floor(great_val * fever)) if in_fever else np.int64(floor(great_val))
            if gv < value:
                value = gv
        score += value
    return score


def fg_surface_score(f: Factors, surface: Any, total_notes: int) -> int:
    """Exact score of a Force Great response surface (fever and Great masks over the head notes, plus
    body counts of fever notes, Great notes and notes that are both)."""
    body_total = max(0, total_notes - HEAD_NOTES)
    body_fever, body_great, body_fever_great = int(surface.body_fever), int(surface.body_great), int(surface.body_fever_great)
    if (
        min(body_fever, body_great, body_fever_great) < 0
        or body_fever_great > min(body_fever, body_great)
        or body_fever + body_great - body_fever_great > body_total
    ):
        raise ValueError("Force Great surface body counts do not match the song's body note count")
    return int(
        _fg_surface_score_numba(
            (f.base, f.combo, f.fever, float(f.great_base)),
            f.ramp,
            (int(surface.fever0), int(surface.fever1), int(surface.fever2), int(surface.fever3)),
            (int(surface.great0), int(surface.great1), int(surface.great2), int(surface.great3)),
            (body_fever, body_great, body_fever_great),
            int(total_notes),
        )
    )
