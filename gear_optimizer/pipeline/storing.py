"""Storing a solved song: canonicalize it, merge it into its boards (one transaction) and print what the database
holds."""

from __future__ import annotations

from gear_optimizer.gamedata import Gear, Mini
from gear_optimizer.pipeline.canonical import canonical_rows
from gear_optimizer.pipeline.results import SongSolve
from gear_optimizer.stats import GEM_KINDS
from gear_optimizer.store.db import Boards, load_boards, store_results
from gear_optimizer.store.records import Loadout


def store_solve(conn, solve: SongSolve, gears: dict[str, Gear], minis: dict[str, Mini]) -> tuple[int, int]:
    """Canonicalize a solved song, merge it into its boards and print the stored bests; the boards' best score (base or
    FG) before and after."""
    rows = canonical_rows(solve, gears, minis)
    mode = solve.timed.mode
    before = _best_overall(load_boards(conn, mode, solve.song, solve.tier))
    store_results(conn, mode, solve.song, solve.tier, rows)
    boards = load_boards(conn, mode, solve.song, solve.tier)
    after = _best_overall(boards)
    # One write per song: the workers of a run print side by side.
    print(_stored_text(solve, boards, before, after, gears), end="", flush=True)
    return before, after


def _best_overall(boards: Boards) -> int:
    return max([x.score for x in boards.meta[:1]] + [x.fg_score for x in boards.fg[:1]] + [0])


def _stored_text(solve: SongSolve, boards: Boards, before: int, after: int, gears: dict[str, Gear]) -> str:
    meta = boards.meta[0] if boards.meta else None
    fg = boards.fg[0] if boards.fg else None
    lines = [
        "-" * 30,
        f"FINAL CONFIGURATION FOR: {solve.song}",
        f"Best Base Score Found: {meta.score if meta else 0}",
        f"Best FG Score Found: {fg.fg_score if fg else 0}",
        f" >> NEW RECORD! Previous: {before} | New: {after}" if after > before
        else f" >> No improvement over the stored record ({before})",
    ]
    if meta is not None:
        lines += _loadout_lines("Best Gear Loadout (Base)", meta, meta.meta, gears)
    if fg is not None:
        lines += _loadout_lines("Best Gear Loadout (ForceGreats)", fg, fg.fg, gears)
    return "\n".join(lines) + "\n"


def _loadout_lines(title: str, loadout: Loadout, result, gears: dict[str, Gear]) -> list[str]:
    allocation = dict(zip(GEM_KINDS, result.gems))
    return [
        f"\n[{title}]",
        *(f"{gears[name].slot if name in gears else 'Item'}: {name}" for name in loadout.gear),
        f"\n[{title} - Mini Team]",
        *(group[0] for group in loadout.minis),
        f"\nGem Allocation -> Fever Time: {allocation['Fever Time']}",
        f"Gem Allocation -> Fever Fill: {allocation['Fever Fill Rate']}",
        f"Gem Allocation -> Fever Multiplier: {allocation['Fever Multiplier']}",
        f"Gem Allocation -> Combo Multiplier: {allocation['Combo Multiplier']}",
        f"Gem Allocation -> Perfect Points: {allocation['Perfect Points']}",
        f"Gem Allocation -> {result.element} (Overflow): {allocation['Element']}",
    ]
