from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from gear_optimizer.solver.fever_timeline import calculate_force_greats_timeline_indices


logger = logging.getLogger(__name__)

_TIMELINE_TLS = threading.local()


def _timeline_buffers(total_notes: int):
    n = max(0, int(total_notes))
    section_cap = n + 1
    buf = getattr(_TIMELINE_TLS, "buf", None)
    if buf is None:
        buf = {}
        _TIMELINE_TLS.buf = buf

    fever_mask = buf.get("fever_mask")
    if fever_mask is None or int(getattr(fever_mask, "shape", (0,))[0]) != n:
        fever_mask = np.zeros(n, dtype=np.bool_)
        buf["fever_mask"] = fever_mask
    else:
        fever_mask[:] = False

    section_start = buf.get("section_start")
    if section_start is None or int(getattr(section_start, "shape", (0,))[0]) != section_cap:
        section_start = np.zeros(section_cap, dtype=np.int32)
        buf["section_start"] = section_start
    else:
        section_start[:] = 0

    section_forced = buf.get("section_forced")
    if section_forced is None or int(getattr(section_forced, "shape", (0,))[0]) != section_cap:
        section_forced = np.zeros(section_cap, dtype=np.int32)
        buf["section_forced"] = section_forced
    else:
        section_forced[:] = 0

    section_fill_penalty = buf.get("section_fill_penalty")
    if section_fill_penalty is None or int(getattr(section_fill_penalty, "shape", (0,))[0]) != section_cap:
        section_fill_penalty = np.zeros(section_cap, dtype=np.int32)
        buf["section_fill_penalty"] = section_fill_penalty
    else:
        section_fill_penalty[:] = 0

    section_skip_wasted = buf.get("section_skip_wasted")
    if section_skip_wasted is None or int(getattr(section_skip_wasted, "shape", (0,))[0]) != section_cap:
        section_skip_wasted = np.zeros(section_cap, dtype=np.bool_)
        buf["section_skip_wasted"] = section_skip_wasted
    else:
        section_skip_wasted[:] = False

    return fever_mask, section_start, section_forced, section_fill_penalty, section_skip_wasted


def compute_force_greats_timeline(
    timestamps,
    great_candidate_timestamps,
    total_notes: int,
    fever_fill_rate: float,
    fever_time_stat: float,
    long_notes: int,
    last_note_time: float,
    force_counts,
    *,
    clamp_base_notes_nonnegative: bool,
    clamp_forced_to_section_notes: bool,
    use_forced_great_timing: bool,
):
    forced_arr = np.asarray(force_counts, dtype=np.int32) if force_counts else np.zeros(0, dtype=np.int32)
    fever_mask, section_start, section_forced, section_fill_penalty, section_skip_wasted = _timeline_buffers(
        int(total_notes)
    )

    (
        fever_mask_head_view,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_count,
    ) = calculate_force_greats_timeline_indices(
        timestamps,
        great_candidate_timestamps,
        int(total_notes),
        float(fever_fill_rate),
        float(fever_time_stat),
        int(long_notes),
        float(last_note_time),
        forced_arr,
        int(forced_arr.shape[0]),
        bool(clamp_base_notes_nonnegative),
        bool(clamp_forced_to_section_notes),
        bool(use_forced_great_timing),
        fever_mask,
        section_start,
        section_forced,
        section_fill_penalty,
        section_skip_wasted,
    )

    section_details = []
    for idx in range(int(section_count)):
        base_notes = int(non_fever_base) - 1 if idx == 0 else int(non_fever_base)
        if clamp_base_notes_nonnegative:
            base_notes = max(0, int(base_notes))
        section_details.append(
            {
                "start_idx": int(section_start[idx]),
                "forced": int(section_forced[idx]),
                "fill_penalty_notes": int(section_fill_penalty[idx]),
                "skip_wasted": bool(section_skip_wasted[idx]),
                "notes": int(base_notes) + int(section_fill_penalty[idx]),
            }
        )

    return (
        fever_mask_head_view.copy(),
        int(count_body_fever),
        int(count_body_normal),
        int(non_fever_base),
        section_details,
    )


def extract_base_stats(
    stats: dict[str, Any],
    gem_counts: dict[str, Any] | None,
    selected_color: str,
    ft_gems: int = 0,
    ff_gems: int = 0,
) -> dict[str, Any]:
    if not isinstance(stats, dict) or not stats:
        return {}

    keys = (
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Beat",
        "Vibe",
        "Rush",
        "Flow",
        "Chill",
    )
    gs = stats.get
    if not gem_counts:
        return {key: gs(key, 0) for key in keys}

    try:
        g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
        g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
        g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
        g_ov = int(gem_counts.get("Element", 0) or 0)
        deltas = {
            "Perfect Points": g_pp * int(GEM_SCALE_NORMAL),
            "Chill": g_pp * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Combo Multiplier": g_cm * int(GEM_SCALE_NORMAL),
            "Flow": g_cm * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Multiplier": g_fm * int(GEM_SCALE_FEVER),
            "Rush": g_fm * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Time": int(ft_gems) * int(GEM_SCALE_FEVER),
            "Beat": int(ft_gems) * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Fill Rate": int(ff_gems) * int(GEM_SCALE_FEVER),
            "Vibe": int(ff_gems) * int(GEM_STAT_TO_ELEMENT_SCALE),
        }
        if selected_color:
            deltas[str(selected_color)] = g_ov * int(ELEMENTAL_GEM_SCALE)

        for key, delta in deltas.items():
            if int(delta) > 0 and int(gs(key, 0)) - int(delta) < -50:
                return {base_key: gs(base_key, 0) for base_key in keys}
    except (TypeError, ValueError) as exc:
        logger.debug("force_greats_common:extract_base_stats: %s", exc)

    base = {key: gs(key, 0) for key in keys}
    g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
    g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
    g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
    g_ov = int(gem_counts.get("Element", 0) or 0)

    base["Perfect Points"] = base.get("Perfect Points", 0) - g_pp * GEM_SCALE_NORMAL
    base["Chill"] = base.get("Chill", 0) - g_pp * GEM_STAT_TO_ELEMENT_SCALE
    base["Combo Multiplier"] = base.get("Combo Multiplier", 0) - g_cm * GEM_SCALE_NORMAL
    base["Flow"] = base.get("Flow", 0) - g_cm * GEM_STAT_TO_ELEMENT_SCALE
    base["Fever Multiplier"] = base.get("Fever Multiplier", 0) - g_fm * GEM_SCALE_FEVER
    base["Rush"] = base.get("Rush", 0) - g_fm * GEM_STAT_TO_ELEMENT_SCALE
    base["Fever Time"] = base.get("Fever Time", 0) - int(ft_gems) * GEM_SCALE_FEVER
    base["Beat"] = base.get("Beat", 0) - int(ft_gems) * GEM_STAT_TO_ELEMENT_SCALE
    base["Fever Fill Rate"] = base.get("Fever Fill Rate", 0) - int(ff_gems) * GEM_SCALE_FEVER
    base["Vibe"] = base.get("Vibe", 0) - int(ff_gems) * GEM_STAT_TO_ELEMENT_SCALE
    if selected_color:
        base[str(selected_color)] = base.get(str(selected_color), 0) - g_ov * ELEMENTAL_GEM_SCALE
    return base
