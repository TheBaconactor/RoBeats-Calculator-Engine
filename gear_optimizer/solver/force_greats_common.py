from __future__ import annotations

import logging
from typing import Any

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from gear_optimizer.core.gem_defs import element_gem_count


logger = logging.getLogger(__name__)
STAT_KEYS = (
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

# Key under which the GPU-native GA decode carries each candidate's device-computed
# base_stats7 vector (see solver/genetic_pipeline.decode_gpu_native_ga_runs_payload).
# Cols: [pp, cm, fm, p_val (primary-color stat), s_val (secondary-color stat), ft, ff].
# This is the SAME 7-vector the host derives from a candidate's BaseStats dict
# (proven bit-exact on real device data in tests/test_gpu_base_stats7_equivalence.py),
# but produced on-device so the FG funnel does not re-derive it from a host dict.
FG_BASE_STATS7_KEY = "_base_stats7"


def response_frontier_base_components_row(
    base_stats: dict[str, Any] | None,
    base_stats7: Any,
    *,
    primary_color: str,
    secondary_color: str,
) -> tuple[int, int, int, int, int, int, int]:
    """Canonical FG response-frontier base-components for ONE candidate.

    Returns ``[pp, cm, fm, base[primary], base[secondary], ft, ff]``.

    There are exactly two legitimate, canonical input origins (NOT a fallback):

    * GPU-native GA candidates carry ``base_stats7`` computed on-device by the pack
      kernel; this is the authoritative scoring input for the fused GA->FG handoff.
    * DB-best / skyline / previous-record candidates have no payload row, so their
      canonical source is their ``BaseStats`` dict, extracted with the same
      semantics (primary/secondary select the song's elemental color stats).

    Both produce the identical vector for the same loadout; they differ only by which
    representation the candidate's origin makes available. Pass ``base_stats7=None``
    for dict-sourced candidates; pass the device vector for GA candidates.
    """
    if base_stats7 is not None:
        seq = tuple(int(v) for v in base_stats7)
        if len(seq) != 7:
            raise ValueError(
                f"response frontier base_stats7 must have 7 components, got {len(seq)}"
            )
        return seq  # type: ignore[return-value]

    if not isinstance(base_stats, dict) or not base_stats:
        raise ValueError(
            "response frontier base components require a BaseStats dict when no device "
            "base_stats7 is present"
        )
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    return (
        int(base_stats.get("Perfect Points", 0) or 0),
        int(base_stats.get("Combo Multiplier", 0) or 0),
        int(base_stats.get("Fever Multiplier", 0) or 0),
        int(base_stats.get(primary, 0) or 0) if primary else 0,
        int(base_stats.get(secondary, 0) or 0) if secondary else 0,
        int(base_stats.get("Fever Time", 0) or 0),
        int(base_stats.get("Fever Fill Rate", 0) or 0),
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

    gs = stats.get
    base = {key: gs(key, 0) for key in STAT_KEYS}
    if not gem_counts:
        return base

    try:
        g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
        g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
        g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
        g_ov = element_gem_count(gem_counts)
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
            selected = str(selected_color)
            deltas[selected] = deltas.get(selected, 0) + g_ov * int(ELEMENTAL_GEM_SCALE)

        for key, delta in deltas.items():
            if int(delta) > 0 and int(gs(key, 0)) - int(delta) < -50:
                raise ValueError(
                    "Cannot losslessly extract base stats: "
                    f"{key!r} stat {int(gs(key, 0))} is smaller than applied gem delta {int(delta)}."
                )
    except (TypeError, ValueError) as exc:
        logger.debug("force_greats_common:extract_base_stats: %s", exc)
        raise

    for key, delta in deltas.items():
        base[key] = base.get(key, 0) - delta
    return base
