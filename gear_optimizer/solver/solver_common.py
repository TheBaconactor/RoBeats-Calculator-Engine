from __future__ import annotations

from typing import Any

from gear_optimizer.gamedata import Gear, SongMini, StatCurves
from gear_optimizer.solver.force_greats_common import extract_base_stats
from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination
from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.stats import total

GEAR_SLOTS: tuple[str, ...] = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")


def build_candidate_payload(
    *,
    base_stats_fixed: dict[str, Any],
    song: TimedSong,
    curves: StatCurves,
    genome: list[Gear | SongMini],
    selected_color: str,
) -> dict[str, Any]:
    merged = total(base_stats_fixed, *(item.stats for item in genome))
    out = dict(solve_best_fever_combination(merged, song, curves, selected_color=selected_color))
    if out.get("BaseScore") is None:
        out["BaseScore"] = int(out.get("Score", 0) or 0)
    stats = out.get("Stats")
    if isinstance(stats, dict) and stats:
        selected = str(out.get("Selected Element", "") or selected_color or "")
        base_stats = extract_base_stats(
            stats,
            out.get("GemCounts") if isinstance(out.get("GemCounts"), dict) else {},
            selected,
            int(out.get("FT", 0) or 0),
            int(out.get("FF", 0) or 0),
        )
        if isinstance(base_stats, dict) and base_stats:
            out["BaseStats"] = base_stats
    return out
