from __future__ import annotations

from typing import Any


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
