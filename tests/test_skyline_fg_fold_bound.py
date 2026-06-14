"""Documents + bounds the known Skyline (P,S)->2P+S candidate-fold FG gap.

KNOWN LIMITATION (intentional, bounded): the exact Skyline candidate generation
represents a loadout's elemental stats by the single scalar ``base_lane = 2P + S``
(``_lane_base_init`` in mini_skyline.py / tests/parity/exact_skyline.py) and keeps one
survivor per ``(PP,CM,FM,base_lane)`` inside each fixed ``(FT,FF)`` cell
(combined_skyline_sparse.py). The BASE score is exactly a function of ``2P+S``, but the
two-color ForceGreats Great-penalty base is ``floor(4P/3) + floor(2S/3) + 150``
(fg_policy.compute_great_penalty_base). Since ``4P/3 + 2S/3 = 2(2P+S)/3``, the penalty
base is a function of ``2P+S`` EXCEPT the two separate ``floor()`` terms, which wobble by
+-1 on HEAD notes only (the body penalty uses the un-floored ``great_penalty_base_raw =
2C/3 + 150``, a function of ``2P+S`` alone). So two loadouts with identical
``(PP,CM,FM,FT,FF)`` and identical ``2P+S`` (=> identical base score) can have FG scores
differing by a bounded, noise-level amount, and Skyline keeps only one of them -> the
candidate set is technically FG-incomplete on TWO-color songs.

This test makes that gap EXPLICIT and BOUNDED rather than silent:
  (1) base-equal (P,S)-twins have identical base_score (the fold's premise),
  (2) FG *does* distinguish them (so the fold is lossy for FG -- documents the gap),
  (3) the gap is noise-level (<0.01% of score; measured max ~25 pts), so it never flips a
      per-song FG winner.

Single-color songs are unaffected (penalty = 2P+150, base_lane = 2P, both functions of P).
See memory skyline-fg-fold-exactness-gap and tools/dev/prove_skyline_fg_fold_gap.py.
"""

import os

import numpy as np
import pytest

from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
from gear_optimizer.solver.scoring.exact_rescore import evaluate_force_greats_exact

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _first_two_color_song(difficulty: str = "Easy", scan_limit: int = 40):
    """Return (calc_song, primary, secondary) for the first two-color chart, or None."""
    folder = os.path.join(ROOT, "Data", difficulty)
    if not os.path.isdir(folder):
        return None
    for fn in sorted(os.listdir(folder))[:scan_limit]:
        if not fn.lower().endswith(".txt"):
            continue
        cs = get_base_calc_song(os.path.join(folder, fn), {})
        meta = (cs or {}).get("metadata", {}) or {}
        p, s = str(meta.get("Primary Color") or ""), str(meta.get("Secondary Color") or "")
        if p and s and p != s:
            return cs, p, s
    return None


def test_skyline_fg_fold_gap_is_bounded_noise() -> None:
    found = _first_two_color_song("Easy")
    if found is None:
        pytest.skip("no two-color Easy song available to exercise the (P,S) fold")
    calc_song, primary, secondary = found
    ref_arrays = build_ref_arrays_from_stats(read_table(os.path.join(ROOT, "Data", "Gear", "Stats.txt")), dtype=np.float64)

    base = {
        "Perfect Points": 50,
        "Combo Multiplier": 90,
        "Fever Multiplier": 80,
        "Fever Fill Rate": 60,
        "Fever Time": 40,
    }
    c_total = 60  # 2P + S held constant -> identical base score across twins
    twins = [(p, c_total - 2 * p) for p in range(0, c_total // 2 + 1)]

    base_scores: set[int] = set()
    finals: list[int] = []
    for p_val, s_val in twins:
        stats = dict(base)
        stats[primary] = int(p_val)
        stats[secondary] = int(s_val)
        replay = evaluate_force_greats_exact(stats, calc_song, ref_arrays, [20, 0])
        assert replay is not None
        base_scores.add(int(replay["base_score"]))
        finals.append(int(replay["final_score"]))

    # (1) The fold's premise: all twins share one base score.
    assert len(base_scores) == 1, f"(P,S)-twins must have identical base score; got {sorted(base_scores)}"

    spread = max(finals) - min(finals)
    # (2) FG distinguishes the twins -> the 2P+S candidate fold is lossy for FG (the gap exists).
    assert spread > 0, "FG should distinguish (P,S)-twins; if 0, the fold became lossless (revisit this doc)"
    # (3) The gap is noise-level: far below any winner margin (measured max ~25 pts ~0.001%).
    assert spread <= 256, f"FG-fold gap unexpectedly large ({spread}); investigate -- it may now flip winners"
    assert spread < max(finals) * 1e-4, f"FG-fold gap exceeded 0.01% of score ({spread}/{max(finals)})"
