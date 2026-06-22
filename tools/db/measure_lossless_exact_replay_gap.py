"""Measure inherited-gems replay gap for an active (tier, color, timing) config.

This is the A.0 evidence harness from the exact 0ms / Lossless-Exact Replay handoff:
for persisted baseline loadouts, compare today's served replay against a config-specific
within-loadout re-solve.

Current replay:
- replays the persisted baseline loadout through `build_team_buff_tier_db_batches()`
- inherits the baseline gem allocation

Re-solve:
- keeps the same gear + minis identity
- re-runs the canonical gem solver for the active config
- scores the re-solved loadout with the exact CPU reference
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.core.config import load_config
from gear_optimizer.core.constants import TOTAL_GEM_BUDGET
from gear_optimizer.core.team_buff import (
    normalize_team_buff,
    resolve_baseline_team_buff_from_cfg_dict,
    resolve_team_color_from_cfg_dict,
    team_buff_effect,
)
from gear_optimizer.core.utils import cfg_to_dict, get_selected_element
from gear_optimizer.data.database import get_best_loadouts, get_evolution_db_path
from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
    build_team_buff_tier_db_batches,
    resolve_zero_ms_base,
    resolve_zero_ms_fg_force,
)
from gear_optimizer.solver.fg_response_frontier_cache_prebuild import ensure_response_frontier_cache_for_calc_song
from gear_optimizer.solver.scoring.exact_rescore import (
    score_force_greats_response_surface_exact,
    score_stats_exact_with_timeline_trace,
    score_stats_fixed_timing_exact,
)
from gear_optimizer.solver.solver_common import (
    build_candidate_payload,
    build_solver_cfg_data,
    build_solver_override_cfg,
)
from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
    prepare_force_greats_response_frontier_scoring_batch,
    score_prepared_force_greats_response_frontier_batch_cpu_sync,
    score_prepared_force_greats_response_frontier_batch_sync,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


ELEMENT_SET = ("Chill", "Flow", "Rush", "Beat", "Vibe")


@dataclass(frozen=True, slots=True)
class ReplayGapRow:
    song_name: str
    loadout_hash: str
    mode: str
    tier: str
    timing_mode: str
    team_buff_color: str
    chart_primary: str
    chart_secondary: str
    selected_element: str
    replay_score: int
    resolved_score: int
    score_delta: int
    score_delta_pct: float
    gems_changed: bool
    replay_gem_counts: dict[str, int]
    resolved_gem_counts: dict[str, int]


def _song_palette(metadata: dict[str, Any]) -> tuple[str, str]:
    primary = str(metadata.get("Primary Color") or "").strip()
    secondary = str(metadata.get("Secondary Color") or "").strip()
    primary = primary if primary in ELEMENT_SET else ""
    secondary = secondary if secondary in ELEMENT_SET and secondary != primary else ""
    return primary, secondary


def _allowed_song_colors(song_primary: str, song_secondary: str) -> dict[str, str]:
    allowed: dict[str, str] = {}
    if song_primary:
        allowed[song_primary.lower()] = song_primary
    if song_secondary:
        allowed[song_secondary.lower()] = song_secondary
    return allowed


def _resolve_element_override(raw: str, *, default_value: str, allowed_colors: dict[str, str]) -> str:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return str(default_value or "")
    if cleaned.lower() == "other":
        return ""
    resolved = allowed_colors.get(cleaned.lower())
    if resolved is None:
        raise ValueError(f"Invalid element override: {raw!r}")
    return str(resolved)


def _resolve_team_buff_color_override(raw: str, *, default_value: str) -> str:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return str(default_value or "")
    if cleaned.lower() == "none":
        return ""
    allowed = {color.lower(): color for color in ELEMENT_SET}
    resolved = allowed.get(cleaned.lower())
    if resolved is None:
        raise ValueError(f"Invalid Team Buff color override: {raw!r}")
    return str(resolved)


def _resolve_color_overrides(
    *,
    metadata: dict[str, Any],
    team_buff_color_override: str,
    primary_element_override: str,
    secondary_element_override: str,
) -> tuple[str | None, str | None, str, str]:
    song_primary, song_secondary = _song_palette(metadata)
    has_overrides = bool(
        str(team_buff_color_override or "").strip()
        or str(primary_element_override or "").strip()
        or str(secondary_element_override or "").strip()
    )
    if not has_overrides:
        return None, None, song_primary, song_secondary

    allowed_colors = _allowed_song_colors(song_primary, song_secondary)
    resolved_primary = _resolve_element_override(
        primary_element_override,
        default_value=song_primary,
        allowed_colors=allowed_colors,
    )
    resolved_secondary = _resolve_element_override(
        secondary_element_override,
        default_value=song_secondary,
        allowed_colors=allowed_colors,
    )
    resolved_team_buff_color = _resolve_team_buff_color_override(
        team_buff_color_override,
        default_value=song_primary,
    )
    return song_primary or None, resolved_team_buff_color, resolved_primary, resolved_secondary


def _prepare_active_calc_song(
    base_calc_song: dict[str, Any],
    *,
    timing_mode: str,
    team_buff_color_override: str,
    primary_element_override: str,
    secondary_element_override: str,
) -> tuple[dict[str, Any], str | None, str | None]:
    calc_song = clone_calc_song(base_calc_song)
    metadata = calc_song.get("metadata")
    metadata = dict(metadata) if isinstance(metadata, dict) else {}
    base_color_override, target_color_override, resolved_primary, resolved_secondary = _resolve_color_overrides(
        metadata=metadata,
        team_buff_color_override=team_buff_color_override,
        primary_element_override=primary_element_override,
        secondary_element_override=secondary_element_override,
    )
    metadata["Primary Color"] = resolved_primary
    metadata["Secondary Color"] = resolved_secondary
    calc_song["metadata"] = metadata
    apply_timing_envelope(calc_song, mode=str(timing_mode or "perfect_window"))
    return calc_song, base_color_override, target_color_override


def _team_buff_delta_map(
    *,
    base_team_buff: str,
    target_team_buff: str,
    base_team_color: str,
    target_team_color: str,
) -> dict[str, int]:
    base = team_buff_effect(base_team_buff, base_team_color)
    target = team_buff_effect(target_team_buff, target_team_color)
    keys = set(base.keys()) | set(target.keys())
    out: dict[str, int] = {}
    for key in keys:
        delta = int(target.get(key, 0) or 0) - int(base.get(key, 0) or 0)
        if delta:
            out[str(key)] = int(delta)
    return out


def _apply_stat_delta(stats: dict[str, Any], delta: dict[str, int]) -> dict[str, Any]:
    out = dict(stats or {})
    for key, value in (delta or {}).items():
        out[str(key)] = int(out.get(key, 0) or 0) + int(value)
    return out


def _resolve_target_fixed_stats(
    *,
    fixed_stats: dict[str, Any],
    cfg_dict: dict[str, Any],
    calc_song: dict[str, Any],
    tier: str,
    base_team_color_override: str | None,
    target_team_color_override: str | None,
) -> tuple[dict[str, Any], str, str, str]:
    metadata = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}
    song_primary = str(metadata.get("Primary Color") or "").strip()
    resolved_color = resolve_team_color_from_cfg_dict(cfg_dict, primary_color=song_primary)
    base_team_color = str(base_team_color_override if base_team_color_override is not None else resolved_color or "")
    target_team_color = str(
        target_team_color_override if target_team_color_override is not None else base_team_color or ""
    )
    base_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
    delta = _team_buff_delta_map(
        base_team_buff=str(base_team_buff),
        target_team_buff=normalize_team_buff(tier, default="T5"),
        base_team_color=base_team_color,
        target_team_color=target_team_color,
    )
    return (
        _apply_stat_delta(dict(fixed_stats or {}), delta),
        str(base_team_buff),
        str(base_team_color),
        str(target_team_color),
    )


def _normalize_gem_counts(payload: dict[str, Any]) -> dict[str, int]:
    gem_counts = dict(payload.get("GemCounts") or {}) if isinstance(payload, dict) else {}
    out = {str(key): int(value or 0) for key, value in gem_counts.items()}
    if isinstance(payload, dict):
        out["Fever Time"] = int(payload.get("FT", out.get("Fever Time", 0)) or 0)
        out["Fever Fill Rate"] = int(payload.get("FF", out.get("Fever Fill Rate", 0)) or 0)
    return out


def _score_delta_pct(*, replay_score: int, resolved_score: int) -> float:
    replay = int(replay_score or 0)
    resolved = int(resolved_score or 0)
    if replay <= 0:
        return 0.0 if resolved <= 0 else 100.0
    return round(((resolved - replay) / replay) * 100.0, 6)


def _entry_hash(entry: dict[str, Any]) -> str:
    return str(entry.get("loadout_hash") or "").strip()


def _infer_difficulty_from_song_name(song_name: str) -> str:
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in str(song_name or ""):
            return diff
    return "Normal"


def _song_file_from_name(song_name: str, details: dict[str, Any] | None = None) -> Path | None:
    difficulty = str((details or {}).get("Difficulty") or "").strip() or _infer_difficulty_from_song_name(song_name)
    direct = PROJECT_ROOT / "Data" / difficulty / f"{song_name}.txt"
    if direct.exists():
        return direct

    diff_dir = PROJECT_ROOT / "Data" / difficulty
    if not diff_dir.exists():
        return None
    for path in sorted(diff_dir.glob("*.txt")):
        if path.stem == str(song_name):
            return path
    return None


def _entry_loadout_items(entry: dict[str, Any]) -> list[dict[str, Any]]:
    gear = [dict(item) for item in list(entry.get("gear") or [])[:6]]
    minis = [dict(item) for item in list(entry.get("minis") or [])[:3]]
    if len(gear) != 6 or len(minis) != 3:
        raise ValueError(f"Loadout {_entry_hash(entry)!r} does not have 6 gear + 3 minis")
    return gear + minis


def _find_replay_row(
    *,
    entry: dict[str, Any],
    active_calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    cfg_dict: dict[str, Any],
    tier: str,
    timing_mode: str,
    base_team_color_override: str | None,
    target_team_color_override: str | None,
) -> dict[str, Any]:
    batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=clone_calc_song(active_calc_song),
        ref_arrays=dict(ref_arrays),
        cfg_dict=dict(cfg_dict),
        limit=1,
        tiers=(str(tier),),
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
        replay_surface="both",
        timing_mode=str(timing_mode),
    )
    rows = list(batches.get(str(tier), []) or [])
    wanted_hash = _entry_hash(entry)
    if not rows:
        raise ValueError(f"No replay rows returned for loadout {wanted_hash!r}")
    if not wanted_hash:
        return dict(rows[0])
    for row in rows:
        if str(row.get("loadout_hash") or "").strip() == wanted_hash:
            return dict(row)
    raise ValueError(f"Replay rows did not include loadout {wanted_hash!r}")


def _replay_payload_for_mode(row: dict[str, Any], mode: str) -> dict[str, Any] | None:
    if str(mode) == "fg":
        force_payload = row.get("force")
        return dict(force_payload) if isinstance(force_payload, dict) else None
    details = row.get("details")
    return dict(details) if isinstance(details, dict) else None


def _replay_score_for_mode(row: dict[str, Any], mode: str) -> int:
    if str(mode) == "fg":
        return int(row.get("fg_score", 0) or 0)
    return int(row.get("score", 0) or 0)


def _exact_base_score(
    *,
    stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    timing_mode: str,
) -> int:
    if str(timing_mode) == "zero_ms":
        return int(score_stats_fixed_timing_exact(stats, calc_song, ref_arrays))
    return int(score_stats_exact_with_timeline_trace(stats, calc_song, ref_arrays).get("score", 0) or 0)


def _exact_fg_score(
    *,
    stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_element: str,
) -> int:
    ensure_response_frontier_cache_for_calc_song(calc_song, ref_arrays)
    batch = prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=[dict(stats)],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=str(selected_element or ""),
        total_budget=0,
    )
    results = score_prepared_force_greats_response_frontier_batch_cpu_sync(
        batch,
        include_forced_counts=False,
    )
    if len(results) != 1:
        raise ValueError(f"Expected exactly one FG replay result, got {len(results)}")
    surface_score = score_force_greats_response_surface_exact(stats, calc_song, ref_arrays, results[0].surface)
    if surface_score is None:
        raise ValueError("FG exact response-surface replay failed")
    return int(surface_score)


def _solve_fg_exact(
    *,
    fixed_song_stats: dict[str, Any],
    loadout_items: list[dict[str, Any]],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_element: str,
) -> tuple[int, dict[str, int], dict[str, Any]]:
    # Single canonical recipe, shared with serving: song fixed stats + loadout item stats
    # + budget=90 -> GPU FG search (fp-gated kernel) -> CPU-f64 exact rescore (force["Score"]).
    # Using the SAME production helper here is what makes served == native (delta=0).
    force = resolve_zero_ms_fg_force(
        fixed_song_stats=fixed_song_stats,
        loadout_items=loadout_items,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=str(selected_element or ""),
    )
    resolved_stats = dict(force.get("Stats") or {})
    resolved_score = int(force.get("Score") or 0)
    return resolved_score, _normalize_gem_counts(force), resolved_stats


def _selected_element_for_mode(*, replay_payload: dict[str, Any] | None, fallback_primary: str) -> str:
    return str(get_selected_element(replay_payload or {}, fallback_primary) or fallback_primary or "").strip()


def _compare_entry_mode(
    *,
    entry: dict[str, Any],
    cfg: Any,
    cfg_dict: dict[str, Any],
    fixed_stats: dict[str, Any],
    active_calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    tier: str,
    timing_mode: str,
    mode: str,
    use_gpu_solver: bool,
    base_team_color_override: str | None,
    target_team_color_override: str | None,
) -> ReplayGapRow | None:
    replay_row = _find_replay_row(
        entry=entry,
        active_calc_song=active_calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        tier=tier,
        timing_mode=timing_mode,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
    )
    replay_payload = _replay_payload_for_mode(replay_row, mode)
    if replay_payload is None:
        return None

    metadata = active_calc_song.get("metadata", {}) if isinstance(active_calc_song, dict) else {}
    chart_primary = str(metadata.get("Primary Color") or "").strip()
    chart_secondary = str(metadata.get("Secondary Color") or "").strip()
    selected_element = _selected_element_for_mode(replay_payload=replay_payload, fallback_primary=chart_primary)

    target_fixed_stats, _base_team_buff, _base_team_color, target_team_color = _resolve_target_fixed_stats(
        fixed_stats=fixed_stats,
        cfg_dict=cfg_dict,
        calc_song=active_calc_song,
        tier=tier,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
    )
    loadout_items = _entry_loadout_items(entry)
    if str(mode) == "fg":
        resolved_score, resolved_gem_counts, resolved_stats = _solve_fg_exact(
            fixed_song_stats=target_fixed_stats,
            loadout_items=loadout_items,
            calc_song=clone_calc_song(active_calc_song),
            ref_arrays=ref_arrays,
            selected_element=selected_element,
        )
    elif str(timing_mode) == "zero_ms":
        # Single canonical recipe, shared with serving: song fixed stats + loadout item stats
        # + GPU base exhaustive search (MoltenVK-correct after the warmstart fix) + CPU-f64 0ms
        # exact rescore. Using the SAME helper here is what makes served base == native (delta=0).
        resolved, resolved_score = resolve_zero_ms_base(
            cfg=cfg,
            fixed_song_stats=target_fixed_stats,
            loadout_items=loadout_items,
            calc_song=clone_calc_song(active_calc_song),
            ref_arrays=ref_arrays,
            primary_color=chart_primary,
            secondary_color=chart_secondary,
            selected_color=selected_element,
        )
        resolved_stats = dict(resolved.get("Stats") or {})
        resolved_gem_counts = _normalize_gem_counts(resolved)
    else:
        cfg_data = build_solver_cfg_data(
            cfg,
            p_color=chart_primary,
            s_color=chart_secondary,
            selected_color=selected_element,
        )
        override_cfg = build_solver_override_cfg(
            cfg_data,
            p_color=chart_primary,
            selected_color=selected_element,
        )
        override_cfg["use_gpu"] = bool(use_gpu_solver)
        resolved = build_candidate_payload(
            cfg=cfg,
            base_stats_fixed=target_fixed_stats,
            calc_song=clone_calc_song(active_calc_song),
            ref_arrays=ref_arrays,
            genome=loadout_items,
            override_cfg=override_cfg,
            gpu_client=None,
        )
        resolved_stats = dict(resolved.get("Stats") or {})
        if not resolved_stats:
            raise ValueError(f"Re-solve returned no Stats for loadout {_entry_hash(entry)!r}")
        resolved_score = _exact_base_score(
            stats=resolved_stats,
            calc_song=clone_calc_song(active_calc_song),
            ref_arrays=ref_arrays,
            timing_mode=timing_mode,
        )
        resolved_gem_counts = _normalize_gem_counts(resolved)

    replay_score = _replay_score_for_mode(replay_row, mode)
    replay_gem_counts = _normalize_gem_counts(replay_payload)
    return ReplayGapRow(
        song_name=str(metadata.get("Song Name") or ""),
        loadout_hash=_entry_hash(entry),
        mode=str(mode),
        tier=str(tier),
        timing_mode=str(timing_mode),
        team_buff_color=str(target_team_color or ""),
        chart_primary=chart_primary,
        chart_secondary=chart_secondary,
        selected_element=selected_element,
        replay_score=int(replay_score),
        resolved_score=int(resolved_score),
        score_delta=int(resolved_score - replay_score),
        score_delta_pct=_score_delta_pct(replay_score=replay_score, resolved_score=resolved_score),
        gems_changed=replay_gem_counts != resolved_gem_counts,
        replay_gem_counts=replay_gem_counts,
        resolved_gem_counts=resolved_gem_counts,
    )


def _distinct_song_names(*, db_path: str, team_buff: str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT song_name
            FROM team_buff_loadouts
            WHERE UPPER(COALESCE(team_buff, '')) = UPPER(?)
            ORDER BY song_name
            """,
            (str(team_buff),),
        ).fetchall()
    finally:
        conn.close()
    return [str(row[0] or "").strip() for row in rows if str(row[0] or "").strip()]


def _render_table(rows: list[ReplayGapRow]) -> str:
    if not rows:
        return "No comparison rows."
    header = (
        f"{'SONG':<48} {'MODE':<4} {'TIER':<4} {'REPLAY':>10} "
        f"{'RESOLVED':>10} {'DELTA':>10} {'DELTA%':>9} {'GEMS?':>6}"
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{row.song_name[:48]:<48} {row.mode:<4} {row.tier:<4} {row.replay_score:>10} "
            f"{row.resolved_score:>10} {row.score_delta:>10} {row.score_delta_pct:>8.4f}% "
            f"{('yes' if row.gems_changed else 'no'):>6}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=str, default=str(get_evolution_db_path()))
    parser.add_argument("--config", type=str, default=str(PROJECT_ROOT / "config.ini"))
    parser.add_argument("--song", action="append", default=[])
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--per-song-limit", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260621)
    parser.add_argument("--tier", type=str, default="T10")
    parser.add_argument("--timing-mode", choices=("perfect_window", "zero_ms"), default="zero_ms")
    parser.add_argument(
        "--mode",
        choices=("meta", "fg", "both"),
        default="meta",
        help="Replay surface to compare against the exact zero_ms re-solve.",
    )
    parser.add_argument("--team-buff-color", type=str, default="")
    parser.add_argument("--primary-element", type=str, default="")
    parser.add_argument("--secondary-element", type=str, default="")
    parser.add_argument(
        "--solver",
        choices=("cpu", "gpu"),
        default="cpu",
        help="Backend for the within-loadout gem re-solve. CPU is the default evidence path.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a text table.")
    args = parser.parse_args()

    db_path = Path(str(args.db or "").strip())
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")
    # FG-mode exact re-solve is now supported on macOS: the FG gem kernel is fp-gated
    # (f32 on MoltenVK / f64 on AMD), so the GPU gem search runs here; the served score is the
    # CPU-f64 exact rescore of the winner (lossless). --mode {meta,fg,both} all run.

    cfg = load_config(str(args.config))
    cfg_dict = cfg_to_dict(cfg)
    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

    baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
    gears_by_name = get_gears_by_name_cached()
    minis_by_name = get_minis_by_name_cached()

    requested_songs = [str(song).strip() for song in list(args.song or []) if str(song).strip()]
    if requested_songs:
        song_names = requested_songs
    else:
        song_names = _distinct_song_names(db_path=str(db_path), team_buff=str(baseline_team_buff))
        rng = random.Random(int(args.seed))
        rng.shuffle(song_names)

    rows: list[ReplayGapRow] = []
    mode_list = ["meta", "fg"] if str(args.mode) == "both" else [str(args.mode)]
    for song_name in song_names:
        entries = get_best_loadouts(
            song_name,
            limit=max(1, int(args.per_song_limit)),
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            team_buff=str(baseline_team_buff),
            db_path=str(db_path),
        )
        if not entries:
            continue

        song_file = _song_file_from_name(song_name, details=entries[0].get("details"))
        if song_file is None or not song_file.exists():
            continue

        base_calc_song = get_base_calc_song(str(song_file), cfg_dict)
        active_calc_song, base_team_color_override, target_team_color_override = _prepare_active_calc_song(
            base_calc_song,
            timing_mode=str(args.timing_mode),
            team_buff_color_override=str(args.team_buff_color),
            primary_element_override=str(args.primary_element),
            secondary_element_override=str(args.secondary_element),
        )
        build_or_load_timeline_frontier_payload(clone_calc_song(active_calc_song), ref_arrays)

        from gear_optimizer.helpers.song_helpers.song_config import setup_song_config
        from gear_optimizer.core.constants import PATHS

        _ga_settings, fixed_stats, _cur_gear_stats, _cur_gear_list, _cur_mini_stats, _cur_mini_list = setup_song_config(
            cfg,
            clone_calc_song(active_calc_song),
            PATHS,
            gears_by_name,
            minis_by_name,
        )

        for entry in entries[: max(1, int(args.per_song_limit))]:
            for mode in mode_list:
                row = _compare_entry_mode(
                    entry=entry,
                    cfg=cfg,
                    cfg_dict=cfg_dict,
                    fixed_stats=fixed_stats,
                    active_calc_song=active_calc_song,
                    ref_arrays=ref_arrays,
                    tier=normalize_team_buff(args.tier, default="T5"),
                    timing_mode=str(args.timing_mode),
                    mode=mode,
                    use_gpu_solver=str(args.solver) == "gpu",
                    base_team_color_override=base_team_color_override,
                    target_team_color_override=target_team_color_override,
                )
                if row is not None:
                    rows.append(row)
                if len(rows) >= int(args.samples):
                    break
            if len(rows) >= int(args.samples):
                break
        if len(rows) >= int(args.samples):
            break

    if args.json:
        print(json.dumps([asdict(row) for row in rows], indent=2, sort_keys=True))
    else:
        print(_render_table(rows))
        improved = sum(1 for row in rows if row.resolved_score > row.replay_score)
        changed = sum(1 for row in rows if row.gems_changed)
        print()
        print(
            f"rows={len(rows)} improved={improved} gems_changed={changed} "
            f"timing_mode={args.timing_mode} tier={normalize_team_buff(args.tier, default='T5')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
