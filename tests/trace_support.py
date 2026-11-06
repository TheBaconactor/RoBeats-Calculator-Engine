"""Hand-written trace sections in the store's full schema: a test names only the fields it is about."""

from __future__ import annotations

import numpy as np

from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE
from gear_optimizer.trace import note_graph as production
from gear_optimizer.trace.note_graph import (  # noqa: F401  (the tests import the graph API from here)
    base_note_graph,
    reconcile_base_note_graph,
    reconcile_force_greats_note_graph,
)


def stored_sections(frontier_trace, timestamps):
    """The sections as a solve stores them: a section's activation hits default to its witnessed hit, its schedule to
    chart order and its cutoff to the first note past its fever."""
    chart_ms = np.asarray(timestamps, dtype=np.float64).reshape(-1) * 1000.0
    n = int(chart_ms.shape[0])
    sections = []
    for source in frontier_trace:
        row = dict(source)
        activation = int(row["activation_index"])
        offset = float(row.get("activation_hit_offset_ms") or 0.0)
        hit_ms = float(chart_ms[activation]) + offset
        center = float(row.get("activation_hit_ms") or hit_ms)
        row["activation_hit_offset_ms"] = offset
        row.setdefault("section", 0)
        row.setdefault("activation_judgment", "perfect")
        for side in ("lower", "upper"):
            edge = row.get(f"activation_hit_offset_{side}_ms")
            window = center if edge is None else float(chart_ms[activation]) + float(edge)
            row.setdefault(f"activation_hit_window_{side}_ms", window)
        row.setdefault("forced_start_index", 0)
        row.setdefault("forced_run_start_index", -1)
        row.setdefault("forced_run_count", 0)
        row.setdefault("early_great_start", -1)
        row.setdefault("early_great_end", -1)
        row.setdefault("preactivation_order", list(range(int(row["forced_start_index"]), activation)))
        if row.get("fever_window_end_ms") is None:
            fever_end = int(row.get("fever_end_index", n))
            in_chart = 0 <= fever_end < n
            row["fever_window_end_ms"] = (
                float(chart_ms[fever_end]) if in_chart else max(hit_ms + 1.0, float(chart_ms[-1]) + 1000.0)
            )
        row.setdefault("fever_duration_ms", float(row["fever_window_end_ms"]) - hit_ms)
        sections.append(row)
    return sections


def plan_of(notes, note_types, lanes=None, *, precise=True, perfect_time=0):
    """A plan around hand-written notes, to drive one of its passes."""
    is_tail = (np.asarray(note_types) == HELD_TAIL_TYPE).tolist()
    tap, tail = production._tap_and_tail_bands(perfect_time)
    return production._Plan(
        notes=notes,
        bands=[tail if held else tap for held in is_tail],
        is_tail=is_tail,
        lanes=list(range(len(notes)) if lanes is None else lanes),
        precise=precise,
        tap_latest_perfect=tap.perfect[1],
    )


def force_greats_note_graph(
    *, frontier_trace, timestamps, total_notes, note_types=None, lanes=None, timing_mode="precise", perfect_time=0
):
    return production.force_greats_note_graph(
        frontier_trace=stored_sections(frontier_trace, timestamps),
        timestamps=timestamps,
        total_notes=total_notes,
        note_types=np.zeros(total_notes, dtype=np.int32) if note_types is None else note_types,
        lanes=np.arange(total_notes, dtype=np.int32) if lanes is None else lanes,
        timing_mode=timing_mode,
        perfect_time=perfect_time,
    )


def timeline_frontier_note_graph(
    *, frontier_trace, timestamps, total_notes, note_types=None, lanes=None, timing_mode="precise", perfect_time=0
):
    return production.timeline_frontier_note_graph(
        frontier_trace=stored_sections(frontier_trace, timestamps),
        timestamps=timestamps,
        total_notes=total_notes,
        note_types=np.zeros(total_notes, dtype=np.int32) if note_types is None else note_types,
        lanes=np.arange(total_notes, dtype=np.int32) if lanes is None else lanes,
        timing_mode=timing_mode,
        perfect_time=perfect_time,
    )
