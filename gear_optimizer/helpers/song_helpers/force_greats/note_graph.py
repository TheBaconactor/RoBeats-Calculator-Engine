"""Per-loadout note-graph reconstruction data (Deliverable B).

Produces, per note, exactly the fields the game's client `NoteTimeGraph`
(`ReplicatedStorage/Lobby/UI/NoteTimeGraph.lua`) renders for a registered hit:

    HitTime    -> hit_time_ms   (note position on the song timeline, ms)
    Delta      -> delta_ms       (hit timing offset, ms; +late / -early). Carries the exact
                                  offset for every note whose timing is load-bearing: the
                                  activation witness (fever-start, hit late) and any
                                  endpoint-early fever note (issue #42 -- a note at/after the
                                  fever cutoff that is in fever only because it is hit early).
                                  Notes whose timing does not matter stay at 0.
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
  * BASE = timeline frontier            -> base_note_graph(..., timing_mode=...)
        all notes Perfect; selected activation witnesses carry exact `delta_ms`
        when a compact timeline trace is available. The last note of each fever
        run is also a witness (`is_fever_end_witness`) carrying `fever_end_ms`,
        the largest-cushion fever cutoff time -- symmetric to the activation
        witness that anchors where fever starts.
  * FG   = fg frontier + timeline       -> force_greats_note_graph(..., timing_mode=...)
        per-note Perfect/Great + fever; optimized activation hits are timing
        WITNESSES (Perfect-window or Late-Great, carrying exact `delta_ms`);
        prefix/forced Greats are pure v3 selectors (Great label, `delta_ms=None`,
        no precise witness).

``timing_mode`` selects the timing semantic (issue #66):
  * ``"perfect_window"`` (default): apply activation witness offsets, endpoint-early
    guidance, and fever-end safe-target guidance.
  * ``"zero_ms"``: every playable hit at chart time (`delta_ms=0.0`; Great selectors
    stay ``None``). Fever/great sets and witness metadata are unchanged.

Both are reconstructable losslessly from already-persisted data (FG: `frontier_trace`
+ `response_surface`; BASE: the packed stats, replayed through the fever timeline),
so there is no candidate-dependent re-solve and no bulky per-note persistence.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

__all__ = [
    "base_note_graph",
    "timeline_frontier_note_graph",
    "force_greats_note_graph",
    "reconcile_force_greats_note_graph",
]

# Perfect-window lower bound (ms), matching the scoring envelope (timing_envelope.py): a normal
# note can legally be hit as early as -20 ms; a held tail (note_type == 3) as early as -40 ms
# (the Perfect window is widened x2 for held tails).
_PERFECT_LOWER_MS = -20
_PERFECT_UPPER_MS = 40
_HELD_TAIL_TYPE = 3
_HELD_TAIL_TIME_MULT = 2
_FEVER_END_SAME_CHART_TIME_MS = 0.01
_TIMING_MODES = frozenset({"perfect_window", "zero_ms"})
_EARLY_GREAT_LOWER_EXTRA_MS = -75.0
_EARLY_GREAT_FLOOR_MS = float(_PERFECT_LOWER_MS) + float(_EARLY_GREAT_LOWER_EXTRA_MS)  # -95
_ENDPOINT_CUTOFF_SAFETY_MS = 1.0
_EARLY_GREAT_ONLY_UPPER_GAP_MS = 1.0


def _normalize_timing_mode(timing_mode: str) -> str:
    mode = str(timing_mode or "perfect_window").strip().lower()
    if mode not in _TIMING_MODES:
        raise ValueError(f"note_graph: unknown timing_mode {timing_mode!r}")
    return mode


def _perfect_bounds_ms_at(note_types: np.ndarray, j: int) -> tuple[float, float]:
    if int(note_types.shape[0]) <= j:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display "
            "fever-end cluster timing at the note's legal judgment bounds -- it is never guessed"
        )
    mult = _HELD_TAIL_TIME_MULT if int(note_types[j]) == _HELD_TAIL_TYPE else 1
    return float(_PERFECT_LOWER_MS * mult), float(_PERFECT_UPPER_MS * mult)


def _early_great_bounds_ms_at(note_types: np.ndarray, j: int) -> tuple[float, float]:
    """Return early-Great-only guidance bounds for note j (issue #68).

    Great-only endpoint claw-in is a different semantic than Perfect-window claw-in:
    a note that is fevered only via an early Great hit should be shown inside the
    early-Great band, not collapsed to the Perfect-low line.
    """
    if int(note_types.shape[0]) <= j:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display "
            "early-Great fever-end timing at judgment bounds -- it is never guessed"
        )
    mult = _HELD_TAIL_TIME_MULT if int(note_types[j]) == _HELD_TAIL_TYPE else 1
    great_low = float(_EARLY_GREAT_FLOOR_MS * mult)
    # Great-only region ends just before Perfect-low (exclusive), leaving a visible gap.
    great_high = float((_PERFECT_LOWER_MS * mult) - _EARLY_GREAT_ONLY_UPPER_GAP_MS)
    return great_low, great_high


def _center_safe_delta(*, low_ms: float, high_ms: float) -> float:
    return 0.5 * (float(low_ms) + float(high_ms))


def _same_chart_time_ms(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= _FEVER_END_SAME_CHART_TIME_MS

def _hit_time_ms(timestamps: np.ndarray, idx: int) -> float:
    return float(timestamps[int(idx)]) * 1000.0


def _perfect_note_graph(total_notes: int, timestamps: Sequence[float] | np.ndarray) -> list[dict[str, Any]]:
    n = int(total_notes)
    ts = np.asarray(timestamps).reshape(-1)
    if int(ts.shape[0]) < n:
        raise ValueError("note graph timestamps shorter than total_notes")
    return [
        {
            "note_index": int(i),
            "hit_time_ms": _hit_time_ms(ts, i),
            "note_result": "Perfect",
            "delta_ms": 0.0,
            "fever": False,
            "is_activation_witness": False,
            "is_fever_end_witness": False,
            "fever_end_ms": None,
            "section": 0,
        }
        for i in range(n)
    ]


def _mark_endpoint_early_hits(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    note_types: Sequence[int] | np.ndarray | None,
    skip_range: tuple[int, int] | None = None,
) -> None:
    """Issue #42 endpoint-early inclusion, shown as the LARGEST-CUSHION legal hit per note.

    A fever note whose chart time is at/after the fever cutoff is in fever ONLY because it is hit
    EARLY (its corrected event time slips before the cutoff). The shown offset is the timing with
    the MOST error margin: the CENTER of the note's legal in-fever hit range, in hit-time space.
    (This center sense of "largest cushion" is DISTINCT from the edge-anchored ``largest_cushion``
    activation_hit_offset_kind elsewhere, which denotes the LATEST legal hit / band edge -- here the
    endpoint note is shown at the range's center, not its edge.)
    For a clawed note with chart time ``hit``:

      * ``legal_low_hit = hit + legal_low``        earliest legal Perfect hit (held-tail-aware
        lower bound: -20 normal, -40 held tail)
      * ``upper_hit = cutoff - 1ms``               latest hit still inside the fever cutoff
      * ``lo_hit = max(legal_low_hit, prev_hit)``  also >= the previous shown hit (monotonic order)
      * if ``lo_hit >= upper_hit`` (degenerate / no in-fever room): ``shown_hit = lo_hit`` -- the
        legal + monotonic floor; for a valid trace ``lo_hit < cutoff``, so the note still lands in
        fever, within ~1ms of the cutoff.
      * else: ``shown_hit = 0.5 * (lo_hit + upper_hit)`` -- the largest-cushion center.

    ``delta_ms = shown_hit - hit``. This is DISPLAY-ONLY: it changes only the per-note timing
    offset shown, never the fever/great set or any score (the note graph is not on the scoring
    path; ``reconcile_*`` checks fever/great positions + counts, not deltas). The shown hit stays
    LEGAL (``delta >= legal_low``), IN-FEVER (``shown_hit < cutoff``; the center case is
    ``<= cutoff - 1``), and MONOTONIC (``>= prev shown hit``, including the degenerate clamp).

    Monotonicity is tracked across ALL notes of the section left-to-right: each note's shown hit is
    ``hit_time_ms + delta_ms`` (treating ``None``/unset delta as 0; the activation witness
    contributes its nominal time + its load-bearing delta). The clawed note's shown hit must be
    ``>= prev_hit``.

    ``note_types`` is REQUIRED runtime song data, but only load-bearing when a note is actually
    clawed in (chart >= cutoff): the lower bound is never guessed. If a clawed-in note is found and
    ``note_types`` is missing or shorter than ``total_notes``, this FAILS LOUD rather than display
    a possibly-false hit. Notes comfortably inside the cutoff keep ``delta_ms = 0``; Great
    selectors (``delta_ms is None``) and the activation witness are left untouched.
    """
    if fever_window_end_ms is None:
        return
    cutoff = float(fever_window_end_ms)
    upper_hit = cutoff - _ENDPOINT_CUTOFF_SAFETY_MS  # latest hit still inside the fever cutoff
    nt = None if note_types is None else np.asarray(note_types).reshape(-1)
    skip_lo = int(skip_range[0]) if skip_range is not None else -1
    skip_hi = int(skip_range[1]) if skip_range is not None else -1
    prev_hit = -np.inf  # running largest shown hit across the section (monotonic order)
    for j in range(max(0, int(activation_index)), min(int(fever_end_index), int(total_notes))):
        if skip_range is not None and skip_lo <= j < skip_hi:
            # Great-only endpoint notes are handled by the early-Great helper; do not overwrite
            # them with Perfect-only endpoint logic (which would collapse to Perfect-low).
            continue
        note = notes[j]
        delta = note["delta_ms"]
        hit = float(note["hit_time_ms"])
        if delta is None:
            # Great selector: no timing witness; does not move the monotonic frontier.
            continue
        if note["is_activation_witness"] or hit < cutoff:
            # Not re-centered: a score-determining activation witness (left untouched) or a note
            # comfortably inside the cutoff (no claw). Its shown hit advances the monotonic frontier.
            prev_hit = max(prev_hit, hit + float(delta))
            continue
        # Clawed-in note: shown with the largest-cushion legal in-fever hit.
        if nt is None or int(nt.shape[0]) <= j:
            raise ValueError(
                "note_graph: note_types (length == total_notes) is required to display an "
                "endpoint-early hit at the note's legal lower bound -- it is never guessed"
            )
        legal_low = _PERFECT_LOWER_MS * (_HELD_TAIL_TIME_MULT if int(nt[j]) == _HELD_TAIL_TYPE else 1)
        legal_low_hit = hit + float(legal_low)
        lo_hit = max(legal_low_hit, prev_hit)
        if lo_hit >= upper_hit:
            shown_hit = lo_hit  # no in-fever room: keep the legal + monotonic floor (>= prev_hit, < cutoff)
        else:
            shown_hit = 0.5 * (lo_hit + upper_hit)  # largest cushion = center of the legal range
        note["delta_ms"] = shown_hit - hit
        prev_hit = shown_hit


def _mark_endpoint_early_great_hits(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    note_types: Sequence[int] | np.ndarray | None,
    early_great_start: int,
    early_great_end: int,
) -> tuple[int, int] | None:
    """Issue #68: early-Great fever extension tail, shown in the Great-only band."""
    if fever_window_end_ms is None:
        return None
    if early_great_start < 0 or early_great_end < 0:
        return None
    start = max(int(activation_index), int(early_great_start), 0)
    end = min(int(early_great_end), int(fever_end_index), int(total_notes))
    if end <= start:
        return None
    if note_types is None:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display early-Great "
            "fever-end timing at judgment bounds -- it is never guessed"
        )

    cutoff = float(fever_window_end_ms)
    nt = np.asarray(note_types).reshape(-1)
    prev_hit = -np.inf

    # Reconstruct the monotonic frontier up to the early-Great start from already-set deltas.
    for j in range(max(0, int(activation_index)), min(end, int(total_notes))):
        note = notes[j]
        hit = float(note["hit_time_ms"])
        delta = note.get("delta_ms")
        if j < start:
            if delta is not None:
                prev_hit = max(prev_hit, hit + float(delta))
            continue

        if not bool(note.get("fever")):
            continue
        if note.get("is_activation_witness"):
            continue

        great_low, great_high = _early_great_bounds_ms_at(nt, j)
        fever_high = cutoff - hit - _ENDPOINT_CUTOFF_SAFETY_MS
        safe_low = float(great_low)
        safe_high = min(float(great_high), float(fever_high))
        if safe_low > safe_high:
            raise ValueError(
                f"note_graph: early-Great fever-end note {j} has empty safe interval "
                f"[{safe_low}, {safe_high}] ms"
            )

        lo_hit = max(hit + safe_low, prev_hit)
        hi_hit = hit + safe_high
        if lo_hit > hi_hit:
            raise ValueError(
                f"note_graph: early-Great fever-end note {j} has empty safe interval after "
                f"monotonic/cutoff constraints (lo_hit={lo_hit}, hi_hit={hi_hit})"
            )

        shown_hit = 0.5 * (lo_hit + hi_hit)
        note["note_result"] = "Great"
        note["delta_ms"] = shown_hit - hit
        prev_hit = shown_hit

    return (start, end)


def _early_great_endpoint_range(
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    early_great_start: int,
    early_great_end: int,
) -> tuple[int, int] | None:
    if early_great_start < 0 or early_great_end < 0:
        return None
    start = max(int(activation_index), int(early_great_start), 0)
    end = min(int(early_great_end), int(fever_end_index), int(total_notes))
    if end <= start:
        return None
    return (start, end)

def _mark_fever_end_witness(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    section: int,
) -> None:
    """Mark the last note of the fever run as the fever-end witness.

    Anchors where fever ends with the largest-cushion cutoff (``fever_window_end_ms``) -- the
    same latest-legal convention the activation witness uses for where fever starts. Shared by
    the base and FG note graphs so the two stay symmetric. ``last_fever`` is ``min(e, n) - 1``,
    always ``< n``, so only the lower bound is checked.
    """
    last_fever = min(int(fever_end_index), int(total_notes)) - 1
    if int(activation_index) <= last_fever:
        notes[last_fever]["is_fever_end_witness"] = True
        if fever_window_end_ms is not None:
            notes[last_fever]["fever_end_ms"] = float(fever_window_end_ms)
        notes[last_fever]["section"] = int(section)


def _mark_fever_end_cluster_safe_delta(
    notes: list[dict[str, Any]],
    *,
    activation_index: int,
    fever_end_index: int,
    total_notes: int,
    fever_window_end_ms: float | None,
    note_types: Sequence[int] | np.ndarray | None,
) -> None:
    """Fever-end cluster: judgment-safe ∩ in-fever display delta (issue #64).

    ``fever_window_end_ms`` is a continuous fever **cutoff**, not a playable hit target.
    A guidance ``delta_ms`` must stay inside the note's required judgment window (Perfect
    first) **and** land before the cutoff (``hit + delta < cutoff``).

    For each same-chart-time fever cluster at the section tail:

      * ``judgment_safe = [perfect_lower, perfect_upper]`` (held-tail-aware)
      * ``fever_safe_upper = cutoff - hit - 1ms``
      * ``safe = judgment_safe ∩ (-inf, fever_safe_upper]``
      * ``cluster_safe = intersection of every cluster note's safe interval``

    Display only when the cutoff **constrains** the upper bound below Perfect upper
    (comfortable ends keep ``delta_ms = 0``). Otherwise ``+560 ms``-style values are
    impossible. Great-interval fever-end guidance is not implemented; a tight cutoff
    with a non-Perfect same-chart-time cluster **fails loud** rather than silently
    leaving ``0 ms``.

    Display-only; fever/great sets and scores are unchanged.
    """
    if fever_window_end_ms is None:
        return
    cutoff = float(fever_window_end_ms)
    a = int(activation_index)
    last_fever = min(int(fever_end_index), int(total_notes)) - 1
    if last_fever < a:
        return
    witness = notes[last_fever]
    if not witness.get("is_fever_end_witness"):
        return
    if witness.get("is_activation_witness"):
        return
    hit = float(witness["hit_time_ms"])
    if hit >= cutoff:
        return
    fever_upper_witness = cutoff - hit - 1.0
    if fever_upper_witness >= _PERFECT_UPPER_MS:
        return
    witness_result = str(witness.get("note_result", "Perfect"))
    if witness_result != "Perfect":
        raise ValueError(
            "note_graph: unsupported fever-end guidance at tight cutoff: "
            f"witness note {last_fever} is {witness_result!r}, not Perfect"
        )
    if note_types is None:
        raise ValueError(
            "note_graph: note_types (length == total_notes) is required to display "
            "fever-end cluster timing at judgment bounds -- it is never guessed"
        )
    nt = np.asarray(note_types).reshape(-1)

    cluster: list[int] = []
    for j in range(max(0, a), last_fever + 1):
        note = notes[j]
        if not note.get("fever"):
            continue
        if note.get("is_activation_witness"):
            continue
        if not _same_chart_time_ms(note["hit_time_ms"], hit):
            continue
        note_result = str(note.get("note_result", "Perfect"))
        if note.get("delta_ms") is None or note_result != "Perfect":
            raise ValueError(
                "note_graph: unsupported fever-end guidance at tight cutoff: "
                f"same-chart-time cluster note {j} is {note_result!r} "
                "(Perfect-only guidance not implemented)"
            )
        cluster.append(j)
    if not cluster:
        return

    cluster_lo = -np.inf
    cluster_hi = np.inf
    min_judgment_hi = np.inf
    for j in cluster:
        j_lo, j_hi = _perfect_bounds_ms_at(nt, j)
        min_judgment_hi = min(min_judgment_hi, j_hi)
        fever_upper_delta = cutoff - float(notes[j]["hit_time_ms"]) - 1.0
        safe_hi = min(j_hi, fever_upper_delta)
        safe_lo = j_lo
        if safe_lo > safe_hi:
            raise ValueError(
                f"note_graph: fever-end cluster note {j} has empty safe interval "
                f"[{safe_lo}, {safe_hi}] ms"
            )
        cluster_lo = max(cluster_lo, safe_lo)
        cluster_hi = min(cluster_hi, safe_hi)

    if cluster_lo > cluster_hi:
        raise ValueError(
            "note_graph: fever-end cluster has empty shared safe interval after intersection"
        )
    if cluster_hi >= float(min_judgment_hi):
        return

    display_delta = _center_safe_delta(low_ms=cluster_lo, high_ms=cluster_hi)
    for j in cluster:
        notes[j]["delta_ms"] = display_delta


def timeline_frontier_note_graph(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray | None = None,
    timing_mode: str = "perfect_window",
) -> list[dict[str, Any]]:
    """BASE note-graph from the selected timeline-frontier witness trace.

    ``note_types`` is runtime song data (like ``timestamps``) needed to show a clawed-in
    endpoint-early note's held-tail-aware LEGAL early hit; it is required (fails loud) only when a
    note is actually clawed in -- never guessed.
    """

    n = int(total_notes)
    apply_guidance = _normalize_timing_mode(timing_mode) == "perfect_window"
    notes = _perfect_note_graph(n, timestamps)
    for sec in frontier_trace:
        section = int(sec.get("section", 0))
        a = int(sec["activation_index"])
        e = int(sec["fever_end_index"])
        for j in range(max(0, a), min(e, n)):
            notes[j]["fever"] = True
            if notes[j]["section"] == 0:
                notes[j]["section"] = section
        if apply_guidance and 0 <= a < n:
            notes[a]["delta_ms"] = float(sec["activation_hit_offset_ms"])
            notes[a]["is_activation_witness"] = True
            notes[a]["section"] = section
        # The last note of the fever run is the fever-end witness (largest-cushion cutoff);
        # any fever note at/after that cutoff is shown with its LARGEST-CUSHION legal early hit --
        # the center of its legal in-fever range, the timing with the most error margin (issue #42).
        # Display-only: the per-note timing keeps the scored fever set unchanged.
        fever_end_ms = sec.get("fever_window_end_ms")
        _mark_fever_end_witness(
            notes, activation_index=a, fever_end_index=e, total_notes=n,
            fever_window_end_ms=fever_end_ms, section=section,
        )
        if apply_guidance:
            _mark_endpoint_early_hits(
                notes, activation_index=a, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )
            _mark_fever_end_cluster_safe_delta(
                notes, activation_index=a, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )
    return notes


def base_note_graph(
    *,
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    is_fever_mask: Sequence[bool] | np.ndarray,
    frontier_trace: Sequence[Mapping[str, Any]] | None = None,
    note_types: Sequence[int] | np.ndarray | None = None,
    timing_mode: str = "perfect_window",
) -> list[dict[str, Any]]:
    """BASE note-graph (timeline frontier): every note Perfect, with fever windows.

    The mask path (no ``frontier_trace``) needs no ``note_types`` (no endpoint-early offsets); the
    trace path delegates to ``timeline_frontier_note_graph``, which REQUIRES ``note_types`` and
    fails loud if it is absent -- the held-tail-aware lower bound is never guessed.

    `is_fever_mask` is the full per-note fever mask produced deterministically by
    `gear_optimizer.solver.fever_timeline.calculate_fever_timeline_indices` from the
    loadout's persisted Fever Fill Rate / Fever Time stats + the song notes (its
    `fever_mask_buffer` argument is written for ALL notes, not just the head slice).
    """
    if frontier_trace is not None:
        return timeline_frontier_note_graph(
            frontier_trace=frontier_trace,
            total_notes=int(total_notes),
            timestamps=timestamps,
            note_types=note_types,
            timing_mode=timing_mode,
        )
    n = int(total_notes)
    fev = np.asarray(is_fever_mask).reshape(-1)
    if int(fev.shape[0]) < n:
        raise ValueError("base_note_graph: timestamps/is_fever_mask shorter than total_notes")
    notes = _perfect_note_graph(n, timestamps)
    for i in range(n):
        notes[i]["fever"] = bool(fev[int(i)])
    return notes


def force_greats_note_graph(
    *,
    frontier_trace: Sequence[Mapping[str, Any]],
    total_notes: int,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray | None = None,
    timing_mode: str = "perfect_window",
) -> list[dict[str, Any]]:
    """FG note-graph (fg frontier + timeline frontier) from the persisted witness trace.

    ``note_types`` is runtime song data (like ``timestamps``) needed to show a clawed-in
    endpoint-early note's held-tail-aware LEGAL early hit; required (fails loud) only when a note
    is actually clawed in -- never guessed.

    `frontier_trace` is the per-loadout `ForceGreats.frontier_trace` (list of section
    dicts emitted by `reconstruct_force_greats_response_trace`). Each section carries a
    sequential, non-overlapping region of the timeline:
      - fever window  [activation_index, fever_end_index)            -> fever
      - forced greats [forced_start_index, forced_start_index+forced_prefix_count) -> Great (selector)
      - the activation note is a timing WITNESS when activation_hit_offset_ms is nonzero.
        If activation_judgment == "late_great", that witness is also a Great; otherwise
        it remains Perfect.
    All other notes are Perfect (delta 0). A note may be both fever and Great.
    """
    n = int(total_notes)
    apply_guidance = _normalize_timing_mode(timing_mode) == "perfect_window"
    notes = _perfect_note_graph(n, timestamps)

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

        # Fever-end witness: last note of the fever run, carrying the largest-cushion
        # cutoff (`fever_window_end_ms`). Symmetric to the base note-graph.
        fever_end_ms = sec.get("fever_window_end_ms")
        _mark_fever_end_witness(
            notes, activation_index=a, fever_end_index=e, total_notes=n,
            fever_window_end_ms=fever_end_ms, section=section,
        )

        if apply_guidance:
            activation_judgment = str(sec.get("activation_judgment", ""))
            if activation_judgment == "late_great" and 0 <= a < n:
                notes[a]["note_result"] = "Great"             # activation Late Great = the WITNESS
                notes[a]["delta_ms"] = float(sec["activation_hit_offset_ms"])
                notes[a]["is_activation_witness"] = True
                notes[a]["section"] = section
            elif (
                activation_judgment == "perfect"
                and 0 <= a < n
                and float(sec.get("activation_hit_offset_ms", 0.0) or 0.0) != 0.0
            ):
                notes[a]["delta_ms"] = float(sec["activation_hit_offset_ms"])
                notes[a]["is_activation_witness"] = True
                notes[a]["section"] = section

            # Endpoint-early (issue #42): any Perfect fever note at/after the cutoff is shown with its
            # LARGEST-CUSHION legal early hit -- the center of its legal in-fever range (most error
            # margin), display-only so the scored fever set is unchanged. Great selectors (delta_ms
            # None) are skipped.
            early_great_start = int(sec.get("early_great_start", -1))
            early_great_end = int(sec.get("early_great_end", -1))
            early_great_range = _early_great_endpoint_range(
                activation_index=a,
                fever_end_index=e,
                total_notes=n,
                early_great_start=early_great_start,
                early_great_end=early_great_end,
            )
            _mark_endpoint_early_hits(
                notes,
                activation_index=a,
                fever_end_index=e,
                total_notes=n,
                fever_window_end_ms=fever_end_ms,
                note_types=note_types,
                skip_range=early_great_range,
            )
            _mark_endpoint_early_great_hits(
                notes,
                activation_index=a,
                fever_end_index=e,
                total_notes=n,
                fever_window_end_ms=fever_end_ms,
                note_types=note_types,
                early_great_start=early_great_start,
                early_great_end=early_great_end,
            )
            _mark_fever_end_cluster_safe_delta(
                notes, activation_index=a, fever_end_index=e, total_notes=n,
                fever_window_end_ms=fever_end_ms, note_types=note_types,
            )

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
