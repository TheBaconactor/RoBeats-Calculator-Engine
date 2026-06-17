"""Diagnose the startup timeline-frontier prebuild failure: build a few songs single-process
and surface the real exception (the parallel prebuild swallows per-song errors)."""
import glob
import sys
import traceback

sys.path.insert(0, ".")

from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached  # noqa: E402
from gear_optimizer.solver.timeline_frontier_cache_prebuild import build_timeline_frontier_cache_for_path  # noqa: E402

ref = get_exact_replay_ref_arrays_cached()
try:
    print("ref keys:", list(ref.keys()))
except Exception:
    print("ref type:", type(ref))

songs = (
    sorted(glob.glob("Data/Easy/*.txt"))[:1]
    + sorted(glob.glob("Data/Normal/*.txt"))[:1]
    + sorted(glob.glob("Data/Hard/*.txt"))[:2]
)
for s in songs:
    try:
        r = build_timeline_frontier_cache_for_path(s, ref)
        print("OK  ", r.source, round(r.build_ms, 1), "ms", s)
    except Exception as e:  # noqa: BLE001
        print("FAIL", s, "->", repr(e))
        traceback.print_exc()
        break
