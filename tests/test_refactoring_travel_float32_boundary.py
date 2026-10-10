"""Refactoring Travel (Precise), Fever Time 51: the producer prices a section at its latest activation hit in float64
(the next note's latest hit minus 1 us), which lies between two float32 hits, and there the section's fever reaches
one note further than at any float32 hit (the 2026-10-10 recompute's one failed solve)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gear_optimizer.chart import load_chart
from gear_optimizer.solver.taichi_gem.api.timeline import reconstruct_base_trace
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
    UnplayableTrace,
    reconstruct_force_greats_response_trace,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface
from gear_optimizer.solver.timing_envelope import time_song

CHART = Path(__file__).resolve().parents[1] / "Data" / "Normal" / "Refactoring Travel by t+pazolite feat Nanahira.txt"
REAL_FEVER_TIME = 60.81602650844325  # Fever Time 51


@pytest.fixture(scope="module")
def inputs():
    return time_song(load_chart(CHART), "precise").fg_inputs


def test_an_fg_surface_whose_priced_split_no_float32_hit_plays_is_played_by_another_split(inputs):
    # Fever Fill 50. The producer's split ends on a late Great on note 600 whose fever reaches the last note only at
    # the float64 hit; a late Great on note 109 and a Perfect on note 601 give the same surface.
    trace = reconstruct_force_greats_response_trace(
        inputs=inputs,
        non_fever_base=110,
        target_surface=FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 749, 1, 1),
        raw_fever_fill=109.5,
        real_fever_time=REAL_FEVER_TIME,
    )
    assert [(s["activation_index"], s["activation_judgment"], s["fever_end_index"]) for s in trace] == [
        (109, "late_great", 491),
        (601, "perfect", 968),
    ]


def test_a_base_surface_that_no_float32_hit_plays_is_unplayable(inputs):
    # Fever Fill 51: the cell's one surface needs a Perfect on note 594 whose fever ends at note 963.
    with pytest.raises(UnplayableTrace, match=r"no float32 hit of note 594 in .* ends its fever at note 963"):
        reconstruct_base_trace(
            inputs, head_words=(0, 0, 0, 0), body_fever=748, raw_fever_fill=108.0, real_fever_time=REAL_FEVER_TIME
        )
