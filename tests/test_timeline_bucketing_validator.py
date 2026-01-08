import os

import numpy as np
import pytest

from gear_optimizer.solver.fever_timeline import SongTimelineGrid


def _make_calc_song(*, name: str, n_notes: int, duration: float) -> dict:
    ts = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float64)
    return {
        "song_data": {"timestamps": ts},
        "metadata": {
            "Song Name": str(name),
            "Difficulty": "Test",
            "Last Note Time": str(float(duration)),
            "Total Notes": str(int(n_notes)),
            "Long Notes": "0",
            "Primary Color": "Rush",
            "Secondary Color": "Beat",
        },
    }


def _make_ref_arrays_with_plateaus() -> dict:
    ft = np.repeat(np.linspace(0.75, 1.25, 41, dtype=np.float64), repeats=4)[:161]
    ff = np.repeat(np.linspace(0.6, 2.0, 33, dtype=np.float64), repeats=5)[:161]
    pp = np.linspace(100.0, 300.0, 161, dtype=np.float64)
    cm = np.linspace(1.0, 2.0, 161, dtype=np.float64)
    fm = np.linspace(1.0, 2.0, 161, dtype=np.float64)
    return {
        "Fever Time": ft,
        "Fever Fill Rate": ff,
        "Perfect Points": pp,
        "Combo Multiplier": cm,
        "Fever Multiplier": fm,
    }


def _sig(t) -> tuple:
    mh, cbf, cbn, acts, last_end = t
    return (mh.tobytes(), int(cbf), int(cbn), int(acts), int(last_end))


@pytest.mark.slow
@pytest.mark.parametrize("mode", ["b", "a"])
def test_timeline_bucketing_matches_unbucketed(mode: str) -> None:
    ref_arrays = _make_ref_arrays_with_plateaus()
    calc_song = _make_calc_song(name="S", n_notes=500, duration=60.0)

    env_prev = os.environ.get("TIMELINE_BUCKET_MODE")
    try:
        os.environ["TIMELINE_BUCKET_MODE"] = "off"
        base = SongTimelineGrid(calc_song, ref_arrays)

        os.environ["TIMELINE_BUCKET_MODE"] = mode
        buck = SongTimelineGrid(calc_song, ref_arrays)

        # Sample a reasonable set of pairs (include boundaries).
        pairs = [(0, 0), (0, 160), (160, 0), (160, 160), (80, 80), (40, 120), (120, 40)]
        for i in range(0, 161, 7):
            pairs.append((i, (i * 3) % 161))
            pairs.append(((i * 5) % 161, i))

        for ft_idx, ff_idx in pairs:
            assert _sig(base.get_timeline(ft_idx, ff_idx)) == _sig(buck.get_timeline(ft_idx, ff_idx))
    finally:
        if env_prev is None:
            os.environ.pop("TIMELINE_BUCKET_MODE", None)
        else:
            os.environ["TIMELINE_BUCKET_MODE"] = env_prev
