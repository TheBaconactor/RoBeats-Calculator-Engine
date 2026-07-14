"""cProfile one dense-chart engine-physical Base frontier build."""
from __future__ import annotations

import cProfile
import io
import os
import pstats
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gear_optimizer.data.song_io import read_song_file  # noqa: E402
from gear_optimizer.solver import timeline_exact_frontier as tef  # noqa: E402
from gear_optimizer.solver.timing_envelope import (  # noqa: E402
    build_perfect_candidate_envelope_sec,
    build_perfect_floor_envelope_sec,
)

GRID = 161
FT = np.linspace(0.5, 1.6, GRID).astype(np.float32)
FF = np.linspace(0.5, 1.6, GRID).astype(np.float32)
SONG = os.path.join(ROOT, "Data", "Hard", "Dark Sheep [EXTENDED CUT] (Hard) by Chroma.txt")


def _payload():
    d = read_song_file(SONG)
    ts = np.asarray(d.get("timestamps", []), np.float32).reshape(-1)
    nt = np.asarray(d.get("note_types", []), np.int16).reshape(-1)
    lanes = np.asarray(d.get("lanes", []), np.int32).reshape(-1)
    n = int(ts.shape[0])
    lnt = float(d.get("song_details", {}).get("Last Note Time", ts[-1]))
    lon = int(np.count_nonzero(nt == 2))
    perfect_candidates = build_perfect_candidate_envelope_sec(ts, nt)
    perfect_floor = build_perfect_floor_envelope_sec(ts, nt)
    return dict(song_slot=0, total_notes=n, long_notes=lon, last_note_time=lnt, song_key=None,
                timestamps=ts, perfect_candidate_timestamps=perfect_candidates,
                perfect_floor_timestamps=perfect_floor, lanes=lanes, ref_ft=FT, ref_ff=FF)


def main():
    kw = _payload()
    tef.build_timeline_frontier_grid_payload(**kw)  # warm JIT cache
    pr = cProfile.Profile()
    pr.enable()
    tef.build_timeline_frontier_grid_payload(**kw)
    pr.disable()
    s = io.StringIO()
    st = pstats.Stats(pr, stream=s).strip_dirs()
    st.sort_stats("tottime").print_stats(22)
    print(s.getvalue())


if __name__ == "__main__":
    main()
