"""Per-loadout note-graph reconstruction data (Deliverable B).

Produces, per note, exactly the fields the game's client `NoteTimeGraph`
(`ReplicatedStorage/Lobby/UI/NoteTimeGraph.lua`) renders for a registered hit:

    HitTime    -> hit_time_ms   (note position on the song timeline, ms)
    Delta      -> delta_ms       (hit timing offset, ms; +late / -early)
    NoteResult -> note_result    ("Perfect" | "Great"; never "Miss" -- the
                                  optimizer's solution assumes every note is hit)
    Fever      -> fever           (bool; the game draws the fever bar across the
                                  contiguous fevered notes)

This is RECONSTRUCTION DATA, not a frontend. The candidate-INDEPENDENT cache + the
per-loadout persisted witness data (`evolution.db`) are mapped onto the runtime song
note times (the frontend feeds the game's Rojo `HitObjects`, which share ordering and
ms with the optimizer's `timestamps`). The gear-stat window lines (`get_note_times`)
are derived frontend-side from the persisted stats.

Two graphs per loadout, matching the intended software behavior:
  * BASE = timeline frontier            -> base_note_graph(...)
        all notes Perfect; the deterministic fever windows mark `fever`.
  * FG   = fg frontier + timeline       -> force_greats_note_graph(...)
        per-note Perfect/Great + fever; the activation-note Late Great is the only
        timing WITNESS (carries the exact `delta_ms`); prefix/forced Greats are pure
        v3 selectors (Great label, `delta_ms=None`, no precise witness).

Both are reconstructable losslessly from already-persisted data (FG: `frontier_trace`
+ `response_surface`; BASE: the packed stats, replayed through the fever timeline),
so there is no candidate-dependent re-solve and no bulky per-note persistence.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

__all__ = [
    "base_note_graph",
    "force_greats_note_graph",
    "reconcile_force_greats_note_graph",
]


def _hit_time_ms(timestamps: np.ndarray, idx: int) -> float:
    return float(timestamps[int(idx)]) * 1000.0


def base_note_graph(
    *,
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    is_fever_mask: Sequence[bool] | np.ndarray,
) -> list[dict[str, Any]]:
    """BASE note-graph (timeline frontier): every note Perfect, with fever windows.

    `is_fever_mask` is the full per-note fever mask produced deterministically by
    `gear_optimizer.solver.fever_timeline.calculate_fever_timeline_indices` from the
    loadout's persisted Fever Fill Rate / Fever Time stats + the song notes (its
    `fever_mask_buffer` argument is written for ALL notes, not just the head slice).
    """
    n = int(total_notes)
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float64).reshape(-1))
    fev = np.asarray(is_fever_mask).reshape(-1)
    if int(ts.shape[0]) < n or int(fev.shape[0]) < n:
        raise ValueError("base_note_graph: timestamps/is_fever_mask shorter than total_notes")
    return [
        {
            "note_index": int(i),
            "hit_time_ms": _hit_time_ms(ts, i),
            "note_result": "Perfect",
            "delta_ms": 0.0,
            "fever": bool(fev[int(i)]),
        }
        for i in range(n)
    ]


def force_greats_note_graph(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
) -> list[dict[str, Any]]:
    """FG note-graph (fg frontier + timeline frontier) from the persisted witness trace.

    `frontier_trace` is the per-loadout `ForceGreats.frontier_trace` (list of section
    dicts emitted by `reconstruct_force_greats_response_trace`). Each section carries a
    sequential, non-overlapping region of the timeline:
      - fever window  [activation_index, fever_end_index)            -> fever
      - forced greats [forced_start_index, forced_start_index+forced_prefix_count) -> Great (selector)
      - if activation_judgment == "late_great": the note at activation_index is also a
        Great and is the timing WITNESS, carrying activation_hit_offset_ms as delta_ms.
    All other notes are Perfect (delta 0). A note may be both fever and Great.
    """
    n = int(total_notes)
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float64).reshape(-1))
    if int(ts.shape[0]) < n:
        raise ValueError("force_greats_note_graph: timestamps shorter than total_notes")

    notes: list[dict[str, Any]] = [
        {
            "note_index": int(i),
            "hit_time_ms": _hit_time_ms(ts, i),
            "note_result": "Perfect",
            "delta_ms": 0.0,            # selector default; witness overrides below
            "fever": False,
            "is_activation_witness": False,
            "section": 0,               # 0 = not associated with a fever section
        }
        for i in range(n)
    ]

    for sec in frontier_trace:
        section = int(sec.get("section", 0))
        a = int(sec["activation_index"])
        e = int(sec["fever_end_index"])
        fs = int(sec["forced_start_index"])
        fc = int(sec["forced_prefix_count"])

        for j in range(max(0, fs), min(fs + fc, n)):     # forced (selector) Greats
            notes[j]["note_result"] = "Great"
            notes[j]["delta_ms"] = None                   # selectors have NO timing witness (v3)
            if notes[j]["section"] == 0:
                notes[j]["section"] = section

        for j in range(max(0, a), min(e, n)):             # fever window
            notes[j]["fever"] = True
            if notes[j]["section"] == 0:
                notes[j]["section"] = section

        if str(sec.get("activation_judgment", "")) == "late_great" and 0 <= a < n:
            notes[a]["note_result"] = "Great"             # activation Late Great = the WITNESS
            notes[a]["delta_ms"] = float(sec["activation_hit_offset_ms"])
            notes[a]["is_activation_witness"] = True
            notes[a]["section"] = section

    return notes


def _head_set_from_words(words: Sequence[int], head_limit: int) -> set[int]:
    """Return the set of note indices in [0, head_limit) set in a 4x32-bit head mask."""
    w = tuple(int(x) for x in tuple(words)[:4]) + (0,) * max(0, 4 - len(words))
    idxs: set[int] = set()
    for i in range(int(head_limit)):
        if (int(w[i // 32]) >> (i % 32)) & 1:
            idxs.add(i)
    return idxs


def reconcile_force_greats_note_graph(
    note_graph: Sequence[Mapping[str, Any]],
    *,
    total_notes: int,
    fever_words: Sequence[int],
    great_words: Sequence[int],
    body_fever: int,
    body_great: int,
    body_fever_great: int,
) -> None:
    """Fail-loud proof that the FG note-graph reconciles EXACTLY with the chosen surface.

    Head notes (0..min(n,100)) must match the surface's fever/great bitmasks bit-for-bit;
    body notes (>=100) must match the surface's fever/great/fever_great counts. This is
    the sufficiency guarantee: the persisted trace + surface fully determine the graph.
    Raises ValueError on any mismatch.
    """
    n = int(total_notes)
    head_limit = min(n, 100)

    g_fever_idx = {int(x["note_index"]) for x in note_graph if bool(x["fever"])}
    g_great_idx = {int(x["note_index"]) for x in note_graph if str(x["note_result"]) == "Great"}

    surf_fever_head_idx = _head_set_from_words(fever_words, head_limit)
    surf_great_head_idx = _head_set_from_words(great_words, head_limit)

    g_fever_head = {i for i in g_fever_idx if i < head_limit}
    g_great_head = {i for i in g_great_idx if i < head_limit}
    if g_fever_head != surf_fever_head_idx:
        raise ValueError(f"FG note-graph head fever positions != surface mask: {g_fever_head ^ surf_fever_head_idx}")
    if g_great_head != surf_great_head_idx:
        raise ValueError(f"FG note-graph head great positions != surface mask: {g_great_head ^ surf_great_head_idx}")

    g_body_fever = sum(1 for i in g_fever_idx if i >= 100)
    g_body_great = sum(1 for i in g_great_idx if i >= 100)
    g_body_fg = sum(1 for i in (g_fever_idx & g_great_idx) if i >= 100)
    if g_body_fever != int(body_fever):
        raise ValueError(f"FG note-graph body_fever {g_body_fever} != surface {int(body_fever)}")
    if g_body_great != int(body_great):
        raise ValueError(f"FG note-graph body_great {g_body_great} != surface {int(body_great)}")
    if g_body_fg != int(body_fever_great):
        raise ValueError(f"FG note-graph body_fever_great {g_body_fg} != surface {int(body_fever_great)}")
