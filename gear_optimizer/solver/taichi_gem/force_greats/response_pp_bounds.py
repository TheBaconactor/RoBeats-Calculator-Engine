"""Surface-independent PP/overflow upper bounds for one FG solve."""

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)


def build_pp_prefix_bounds(cur_pp_values, ref_pp, color_flags):
    """Return one prefix row per distinct raw PP stat and each owner's row index.

    Build from this call's reference values in the solver's precision; no cached
    table can outlive a reference revision. Keep raw (including negative) starting
    stats until after adding gems, matching the device's lookup clamping.
    """
    states, owners = np.unique(np.asarray(cur_pp_values, dtype=np.int32), return_inverse=True)
    gems = np.arange(TOTAL_GEM_BUDGET + 1, dtype=np.int32)
    indices = np.clip(states[:, None] + gems * GEM_SCALE_NORMAL, 0, TOTAL_ROWS)
    p_pp, s_pp, *_, p_ov, s_ov = color_flags
    delta = GEM_STAT_TO_ELEMENT_SCALE * (2 * int(p_pp) + int(s_pp)) - ELEMENTAL_GEM_SCALE * (2 * int(p_ov) + int(s_ov))
    extras = (gems * delta).astype(ref_pp.dtype) + ref_pp[indices]
    return np.maximum.accumulate(extras, axis=1), owners.astype(np.int32)
