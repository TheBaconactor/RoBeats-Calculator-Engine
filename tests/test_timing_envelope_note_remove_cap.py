"""Late-Great deliverability is capped by the engine's note removal, not the
classification window.

Decompiled Constants.lua:19 ``NOTE_REMOVE_TIME = -200``: an unhit note
time-misses once ``now - hit > 200`` ms — the SAME edge for taps
(Note.lua:191), hold heads, and the hold despawn (HeldNote.lua:219/231).
A held tail's late-Great CLASSIFICATION edge reaches +380 (2x (40+150)), but
any input scheduled past +200 races the per-frame sweep and is not guaranteed
to land on any frame rate. The planner must therefore never emit a late-Great
candidate beyond +200 (found live: an FG plan scheduled a +318ms tail
activation the game-port replay missed).
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.solver.timing_envelope import (
    NOTE_REMOVE_LATE_CAP_MS,
    judgment_windows_ms,
    perfect_window_envelopes,
)

TAP, HEAD, TAIL = 1, 2, 3


def test_reachable_windows_per_note_type() -> None:
    perfect_low, perfect_high, great_low, great_high = judgment_windows_ms(np.asarray([TAP, HEAD, TAIL]))
    # The early edges are exclusive (+1 after the held-tail x2); the late edges inclusive.
    assert perfect_low.tolist() == [-19, -19, -39]
    assert perfect_high.tolist() == [40, 40, 80]
    assert great_low.tolist() == [-94, -94, -189]
    # The tap/head late-Great edge (40 + 150) is already deliverable; the tail's 380 is capped at removal.
    assert great_high.tolist() == [190, 190, NOTE_REMOVE_LATE_CAP_MS]


def test_great_candidate_envelope_emits_capped_tail_candidates() -> None:
    ts = np.asarray([1.0, 2.0, 3.0], dtype=np.float32)
    out = perfect_window_envelopes(ts, np.asarray([TAP, TAIL, HEAD], dtype=np.int16)).great_candidates
    deltas_ms = np.round((out - ts) * 1000.0).astype(int)
    assert deltas_ms.tolist() == [190, NOTE_REMOVE_LATE_CAP_MS, 190]
