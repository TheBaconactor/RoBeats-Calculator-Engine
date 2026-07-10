"""D-bis tail-activation directed tests (FG_TAIL_ACTIVATION_DBIS.md).

Pins the Stage-1 engine verdicts with executable game_sim replays:

* Q1/Q2 matcher facts: a pending (Holding) tail can never consume a press, and a release never
  binds a tap -- the premises behind the follower-tail analysis.
* Gap (a) verdict: the activation cap at a following tail's widened label edge is the exact
  fill-crossing-identity bound -- delaying the activation press past it flips WHICH note crosses
  (replay-proven), so the capped production surface is not an under-report and the wider claim
  is not physically realizable.
* Gap (b) verdict: a tail IS an activation candidate today with its own widened +80 Perfect /
  +200 despawn-capped late-Great window (per-note envelopes), and the produced tail surfaces are
  physically replayable (two-directional check on the directed tail charts).
* Gap (c): the index-inversion classifier recognizes the designed family's live witness and
  rejects index-ordered surfaces (guards the oracle gate against silent drift).
* Physicality filter: hold bracketing (press < release, no same-lane press inside a span).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_TOOLS_VERIFY = _REPO / "tools" / "verify"
if str(_TOOLS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_TOOLS_VERIFY))

from game_sim import NoteChart, Press, simulate  # noqa: E402
from two_directional_frontier_oracle import (  # noqa: E402
    _realize_surface,
    _schedule_is_physical,
    _surface_key_from_sim,
    _tail_head_pairs,
    _witness_is_index_inverted,
    check_chart,
)

def _sim(chart, presses, config, stats=None):
    return simulate(chart, stats or {}, [], presses, config, frame_dt_ms=1000.0 / 240.0)


# ---------------------------------------------------------------------------------------------
# Q1/Q2 matcher facts (engine-level premises)
# ---------------------------------------------------------------------------------------------


def test_pending_tail_never_consumes_a_press():
    """While a hold is Holding, a same-lane press binds NOTHING (whiffs) -- it neither completes
    the tail nor disturbs the hold; the tail still resolves by its release (game_sim
    press_lane:541-554 state gates == noteSystem.ts:492-506)."""
    chart = NoteChart(
        timestamps_ms=[0.0, 400.0], lanes=[0, 0], note_types=[2, 3]
    )
    cfg = {"hitCount": 2, "hitObjectsCount": 1, "lastNoteTimeSec": 3.0}
    presses = [
        Press(0, 0.0),            # head Perfect -> Holding
        Press(0, 200.0),          # press on the HELD lane: must consume nothing
        Press(0, 400.0, is_release=True),  # tail Perfect
    ]
    r = _sim(chart, presses, cfg)
    tail_hits = [h for h in r.registered if h.is_tail]
    assert len(tail_hits) == 1
    assert tail_hits[0].result == "perfect"
    assert tail_hits[0].press_ms == 400.0  # resolved by the RELEASE, not the 200ms press
    # the stray press consumed no note: only head + tail registered as notes
    assert sorted(h.note_index for h in r.registered if h.kind == "note") == [0, 1]


def test_release_never_binds_a_tap():
    """A release on a lane with only taps is a complete no-op (release_lane skips non-holds:
    game_sim.py:559-560 == noteSystem.ts:516)."""
    chart = NoteChart(timestamps_ms=[0.0, 300.0], lanes=[0, 0], note_types=[1, 1])
    cfg = {"hitCount": 2, "hitObjectsCount": 2, "lastNoteTimeSec": 3.0}
    presses = [
        Press(0, 0.0),
        Press(0, 290.0, is_release=True),  # in the tap's window, but a RELEASE: must not bind
        Press(0, 300.0),
    ]
    r = _sim(chart, presses, cfg)
    assert r.tally == {"perfect": 2, "great": 0, "okay": 0, "miss": 0}
    assert all(not h.is_tail for h in r.registered)


# ---------------------------------------------------------------------------------------------
# Gap (a) verdict: the follower-tail cap is the exact fill-crossing-identity bound
# ---------------------------------------------------------------------------------------------

# One lane of taps + a cross-lane hold whose TAIL is the BINDING follower of the delayed
# activation tap: t_tap + 190 (its own late-Great top, 590) exceeds t_tail + 80 (540), so the
# tail's widened Perfect edge is the operative cap. denom = hitObjectsCount * 0.333 = 1.332;
# lastNoteTimeSec = 1.2 -> fever lasts ~196.7ms. Intended play: idx0 late-Great (0.5), head
# early-Great (0.5) -- bar 1.0 < 1.332 -- so the delayed idx2 Great (0.5 -> 1.5) is the
# crossing. Chart: tap(0,L0) head(100,L1) tap(400,L0) tail(460,L1) tap(760,L0).
_GAP_A_TS = [0.0, 100.0, 400.0, 460.0, 760.0]
_GAP_A_LANES = [0, 1, 0, 1, 0]
_GAP_A_NTS = [1, 2, 1, 3, 1]
_GAP_A_CFG = {"hitCount": 5, "hitObjectsCount": 4, "lastNoteTimeSec": 1.2}


def _gap_a_chart() -> NoteChart:
    return NoteChart(
        timestamps_ms=list(_GAP_A_TS), lanes=list(_GAP_A_LANES), note_types=list(_GAP_A_NTS)
    )


def _gap_a_schedule(tap2_press_ms: float, tail_release_ms: float) -> list[Press]:
    return [
        Press(0, _GAP_A_TS[0] + 41.0),            # idx0 tap late-Great (0.5 units)
        Press(1, _GAP_A_TS[1] - 94.0),            # idx1 head early-Great (0.5 units)
        Press(0, tap2_press_ms),                  # idx2 tap: the intended delayed crossing
        Press(1, tail_release_ms, is_release=True),  # idx3 tail (Perfect window 421..540)
        Press(0, _GAP_A_TS[4]),                   # idx4 tap on time
    ]


def test_follower_tail_edge_is_a_fill_identity_cap_not_a_matcher_cap():
    """Just inside the following tail's +80 edge the delayed tap IS the crossing; past it the
    tail's forced-earlier release deposits first and the CROSSING IDENTITY flips onto the tail
    (game_sim fever_sections.activationMs) -- even though the press itself still binds its own
    tap in both runs (no matcher steal, Q1/Q2). That crossing flip, not press consumption, is
    what the production cap bounds -- and it caps at the tail's widened +80, not a tap edge."""
    chart = _gap_a_chart()
    # In-cap: crossing tap pressed at 539 < tail_hi 540; tail released at its +80 edge (540).
    r_in = _sim(chart, _gap_a_schedule(539.0, _GAP_A_TS[3] + 80.0), _GAP_A_CFG)
    key_in = _surface_key_from_sim(r_in, 5)
    assert key_in is not None
    fever_in, great_in = key_in
    assert great_in == 0b00111  # idx0, idx1, idx2 Greats
    assert (fever_in >> 2) & 1 == 1  # the crossing tap is fevered
    assert (fever_in >> 3) & 1 == 1  # the following tail deposits inside fever
    assert (fever_in >> 4) & 1 == 0  # idx4 (760ms) is beyond the capped fever reach
    assert r_in.fever_sections[0]["activationMs"] == 539.0  # fever starts AT the tap's press
    tail_in = next(h for h in r_in.registered if h.is_tail)
    act_in = next(h for h in r_in.registered if h.note_index == 2)
    assert act_in.press_ms < tail_in.press_ms  # deposit order: activation BEFORE the tail

    # Past the cap: the tap delays to 560 > 540, so keeping the tail's Perfect label FORCES its
    # release before the press. The press still binds the tap (matcher untouched) but the
    # tail's deposit crosses the bar first: activation flips to the tail's release time.
    r_out = _sim(chart, _gap_a_schedule(560.0, _GAP_A_TS[3] + 80.0), _GAP_A_CFG)
    key_out = _surface_key_from_sim(r_out, 5)
    assert key_out is not None
    tail_out = next(h for h in r_out.registered if h.is_tail)
    act_out = next(h for h in r_out.registered if h.note_index == 2)
    assert act_out.result == "great"  # the press bound its own tap and judged in-band
    assert tail_out.press_ms < act_out.press_ms  # deposit order inverted
    assert r_out.fever_sections[0]["activationMs"] == 540.0  # crossing = the TAIL's release


def test_claimed_surface_past_tail_edge_is_not_realizable():
    """Adversarial over-report probe: what skipping the follower tail as a preemptor would have
    claimed -- the in-cap surface with the fever window stretched to cover the next note
    (activation pushed past the tail's +80 while everything keeps its label) -- is physically
    unrealizable: to fever idx4 the activation must be >= ~544ms, but the tail's Perfect label
    forces its 1.0-unit deposit by 540ms, which crosses the bar first. The breakpoint-enriched
    realizer confirms no schedule replays it."""
    r_in = _sim(_gap_a_chart(), _gap_a_schedule(539.0, _GAP_A_TS[3] + 80.0), _GAP_A_CFG)
    key_in = _surface_key_from_sim(r_in, 5)
    assert key_in is not None
    fever_in, great_in = key_in
    assert (fever_in >> 4) & 1 == 0
    over_claim = (fever_in | (1 << 4), great_in)
    assert not _realize_surface(
        over_claim, _GAP_A_TS, _GAP_A_LANES, _GAP_A_NTS, {}, _GAP_A_CFG
    )


# ---------------------------------------------------------------------------------------------
# Gap (b) verdict: tails are activation candidates with their widened self-window, exactly
# ---------------------------------------------------------------------------------------------


def test_directed_tail_charts_two_directional_exact():
    """The directed tail shapes are two-directionally exact on current production up to the
    DESIGNED index-inverted family: no hard over-report (every produced tail surface is
    physically replayable, breakpoint pass included) and no un-designed winning witness."""
    cases = [
        ([0.0, 100.0, 240.0, 460.0, 480.0, 800.0], [0, 1, 0, 1, 0, 0], [1, 2, 1, 3, 1, 1]),
        ([0.0, 100.0, 120.0, 240.0, 460.0, 700.0], [0, 1, 0, 0, 1, 0], [1, 2, 1, 1, 3, 1]),
    ]
    for ts, lanes, nts in cases:
        res = check_chart(ts, lanes, {}, "directed", note_types=nts)
        assert res["over_hard"] == [], f"hard over-report on {ts}: {res['over_hard']}"
        assert res["under"] == [], f"un-designed under-report on {ts}: {res['under']}"


# ---------------------------------------------------------------------------------------------
# Gap (c): the designed-family classifier
# ---------------------------------------------------------------------------------------------


def test_known_gap_witness_is_index_inverted():
    """The live 337.5 witness (fever starts at a note the index-order bar cannot cross on) is
    classified into the designed family; an index-consistent surface is not."""
    # From the tail-follower directed chart: F=.11111 G=.1...1, denom=1.665, n=6.
    fever = 0b111110
    great = 0b100010
    assert _witness_is_index_inverted((fever, great), 1.665, 6)
    # Index-consistent: fever starts exactly at the index-order crossing (idx1 after 1.0+1.0).
    assert not _witness_is_index_inverted((0b000110, 0), 1.665, 6)


# ---------------------------------------------------------------------------------------------
# Physicality filter (hold bracketing)
# ---------------------------------------------------------------------------------------------


def test_schedule_physicality_bracketing():
    nts = [2, 1, 3]
    lanes = [0, 0, 0]
    pairs = _tail_head_pairs(nts, lanes)
    assert pairs == {2: 0}
    # release before press: impossible
    assert not _schedule_is_physical([300.0, 900.0, 200.0], nts, lanes, pairs)
    # same-lane press inside the held span: impossible
    assert not _schedule_is_physical([0.0, 200.0, 400.0], nts, lanes, pairs)
    # same-lane press after the release: fine
    assert _schedule_is_physical([0.0, 500.0, 400.0], nts, lanes, pairs)
