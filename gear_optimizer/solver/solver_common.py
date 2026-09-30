from __future__ import annotations

from typing import Any

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.gamedata import SKIP_ITEM_KEYS
from gear_optimizer.solver.force_greats_common import extract_base_stats
from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination

GEAR_SLOTS: tuple[str, ...] = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")


def _add_genome_item_stats(base_stats: dict[str, Any], genome: list[dict]) -> dict[str, Any]:
    merged = dict(base_stats or {})
    for item in genome or []:
        if not item:
            continue
        for key, value in item.items():
            if key in SKIP_ITEM_KEYS:
                continue
            merged[key] = merged.get(key, 0) + value
    return merged


def build_candidate_payload(
    *,
    base_stats_fixed: dict[str, Any],
    calc_song: dict[str, Any],
    curves: StatCurves,
    genome: list[dict],
    selected_color: str,
) -> dict[str, Any]:
    merged = _add_genome_item_stats(base_stats_fixed, genome)
    out = dict(solve_best_fever_combination(merged, calc_song, curves, selected_color=selected_color))
    out["Genome"] = list(genome)
    out["Gear"] = list(genome[:6])
    out["Minis"] = list(genome[6:9])
    out["GearNames"] = [g.get("Name", "None") for g in out["Gear"]]
    out["MiniNames"] = [m.get("Name", "None") for m in out["Minis"]]
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
