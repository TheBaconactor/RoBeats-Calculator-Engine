"""Production lossless-exact FG re-solve for ONE loadout at the active config (CPU native f64).

Ports the VALIDATED recipe from tools/db/measure_lossless_exact_replay_gap.py::_solve_fg_exact so
the on-demand serving path can RE-SOLVE the FG gem allocation per (loadout, tier/color/timing)
instead of inheriting the perfect_window gems. Returns the materialized ``force`` payload
(re-solved GemCounts/Stats/Score + chart-fixed ForceGreats.frontier_trace) ready for the served
FG card / DB row.

CRITICAL — the re-solve must be fed GEM-LESS *fixed* stats + a budget, NEVER the gem-full
``_fg_stats_at_tier`` stats: feeding gem-full stats + a budget makes the search allocate gems on
top of the existing ones (measured ~63% score inflation). The gem-less stats are built bottom-up:
``merge_fixed_stats_and_genome(target_fixed, genome)`` where ``target_fixed`` is the song's
gem-less ``fixed_stats`` (get_fixed_stats(cfg), incl. baseline team buff) shifted by the tier delta,
and ``genome`` is the loadout's 6 gear + 3 mini stat-dicts (NO gems). total_budget then re-allocates
the gems exactly (CPU native-f64 search in response_inner_cpu_search), bit-exact with the canonical
f64 kernel and (per Task C) faster than GPU f64 emulation on the serving Mac.
"""
from typing import Any, Mapping

from gear_optimizer.core.constants import TOTAL_GEM_BUDGET

_GENOME_GEAR = 6
_GENOME_MINIS = 3


def entry_genome(entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Loadout genome = 6 gear + 3 mini STAT-DICTS (no gems). Mirrors the measure tool's
    _entry_genome. ``entry['gear']`` / ``entry['minis']`` must be lists of stat dicts."""
    gear = [dict(item) for item in list(entry.get("gear") or [])[:_GENOME_GEAR]]
    minis = [dict(item) for item in list(entry.get("minis") or [])[:_GENOME_MINIS]]
    if len(gear) != _GENOME_GEAR or len(minis) != _GENOME_MINIS:
        raise ValueError(
            f"fg_exact_resolve: loadout needs {_GENOME_GEAR} gear + {_GENOME_MINIS} minis as "
            f"stat-dicts, got {len(gear)} gear + {len(minis)} minis "
            f"(hash={entry.get('loadout_hash')!r})"
        )
    return gear + minis


def apply_stat_delta(stats: Mapping[str, Any], delta: Mapping[str, int]) -> dict[str, int]:
    """Add a stat delta, INCLUDING delta-only keys not present in ``stats`` (e.g. a color stat the
    tier introduces). Mirrors team_buff_tiers._apply_stat_delta (kept local to avoid a circular
    import once team_buff_tiers imports this module)."""
    out = {str(k): int(v or 0) for k, v in dict(stats or {}).items()}
    for k, d in dict(delta or {}).items():
        if not d:
            continue
        out[str(k)] = int(out.get(str(k), 0) or 0) + int(d)
    return out


def merge_fixed_stats_and_genome(
    fixed_stats: Mapping[str, Any], genome: list[dict[str, Any]]
) -> dict[str, int]:
    """Gem-less loadout stats = fixed_stats (song base, incl. baseline buff) + gear/mini genome.
    Mirrors the measure tool's _merge_fixed_stats_and_genome."""
    out = {str(key): int(value or 0) for key, value in dict(fixed_stats or {}).items()}
    for item in list(genome or []):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key in {"Name", "type"}:
                continue
            out[str(key)] = int(out.get(key, 0) or 0) + int(value or 0)
    return out


def resolve_fg_force_for_loadouts(
    *,
    entries: list[Mapping[str, Any]],
    fixed_stats: Mapping[str, Any],
    tier_delta: Mapping[str, int],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    selected_color: str,
) -> list[dict[str, Any]]:
    """Re-solve the lossless-exact FG ``force`` for each loadout at one (tier, color, timing=zero_ms)
    config. ``tier_delta`` is the baseline->tier stat delta (apply to gem-less fixed_stats); the
    timing must already be chart-fixed (caller applies apply_timing_envelope(mode="zero_ms") to
    calc_song). Returns one re-solved ``force`` dict per entry, in order.

    The FG Score in each force is exact and independent of the paired base; the paired base sets
    only the displayed BaseScore. Here the gem-less base stats double as the paired-base input (the
    loadout's zero-gem base under the same chart timing) -- a valid >0 paired base.
    """
    from ...solver.fg_response_scoring.fixed_timing import build_fixed_timing_fg_replays

    rows = [dict(e) for e in (entries or [])]
    if not rows:
        return []
    target_fixed = apply_stat_delta(fixed_stats, tier_delta)
    gem_less = [merge_fixed_stats_and_genome(target_fixed, entry_genome(e)) for e in rows]
    replays = build_fixed_timing_fg_replays(
        fg_stats_list=gem_less,
        base_stats_list=gem_less,  # gem-less base = a valid >0 paired base (display-only field)
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=str(selected_color or ""),
        total_budget=int(TOTAL_GEM_BUDGET),
    )
    return [replay["force"] for replay in replays]
