"""The FG inputs of a synthetic chart: the trace reconstruction reads its timing arrays, lanes and forced-Great timing."""

import numpy as np

from gear_optimizer.solver.scoring.fg_policy import FGSongInputs


def fg_song_inputs(
    *,
    timestamps,
    perfect_floor,
    great_floor,
    lanes,
    perfect_candidates=None,
    great_candidates=None,
    use_forced_great_timing=True,
) -> FGSongInputs:
    return FGSongInputs(
        timestamps=timestamps,
        perfect_candidates=perfect_candidates,
        great_candidates=great_candidates,
        perfect_floor=perfect_floor,
        great_floor=great_floor,
        late_great_floor=None,
        exit_ceiling=None,
        lanes=lanes,
        use_forced_great_timing=use_forced_great_timing,
        total_notes=len(timestamps),
        long_notes=0,
        last_note_time=float(np.asarray(timestamps)[-1]),
        primary_color="Chill",
        secondary_color="Chill",
    )
