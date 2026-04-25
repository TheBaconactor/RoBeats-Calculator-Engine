"""
Compare CURRENT vs LEGACY DB on "overall best" per song.

Overall best = max(best base score, best FG score) for a given (song, team_buff).

This script compares *persisted* scores. Legacy DBs can be stale relative to the
current scorer / current Data charts, so treat regressions here as "candidates"
until verified by re-scoring.

Usage:
  python tools/db/compare_overall_best_to_legacy_db.py --team-buff T5 --eps 2
  python tools/db/compare_overall_best_to_legacy_db.py --current evolution.db --legacy evolution_legacy.db --eps 2
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _infer_difficulty_from_song_name(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    return "Normal"


def _song_file_from_name(project_root: Path, song_name: str) -> Path | None:
    diff = _infer_difficulty_from_song_name(song_name)
    fp = project_root / "Data" / diff / f"{song_name}.txt"
    if fp.exists():
        return fp
    return None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (str(table),),
    ).fetchone()
    return row is not None


def _norm_team_buff(team_buff: str) -> str:
    return str(team_buff or "").strip().upper() or "T5"


@dataclass(frozen=True)
class BestRow:
    score: int
    loadout_hash: str


def _best_base(conn: sqlite3.Connection, *, song: str, team_buff: str) -> BestRow | None:
    if not _table_exists(conn, "team_buff_loadouts"):
        return None
    row = conn.execute(
        """
        SELECT score, loadout_hash
        FROM team_buff_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        ORDER BY score DESC, loadout_hash ASC
        LIMIT 1
        """,
        (str(song), str(team_buff)),
    ).fetchone()
    if row is None:
        return None
    return BestRow(score=int(row[0] or 0), loadout_hash=str(row[1] or "").strip())


def _best_fg(conn: sqlite3.Connection, *, song: str, team_buff: str) -> BestRow | None:
    if not _table_exists(conn, "team_buff_fg_loadouts"):
        return None
    row = conn.execute(
        """
        SELECT fg_score, loadout_hash
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        ORDER BY fg_score DESC, loadout_hash ASC
        LIMIT 1
        """,
        (str(song), str(team_buff)),
    ).fetchone()
    if row is None:
        return None
    return BestRow(score=int(row[0] or 0), loadout_hash=str(row[1] or "").strip())


def _best_overall(conn: sqlite3.Connection, *, song: str, team_buff: str) -> dict:
    base = _best_base(conn, song=song, team_buff=team_buff)
    fg = _best_fg(conn, song=song, team_buff=team_buff)

    base_score = int(base.score) if base else 0
    fg_score = int(fg.score) if fg else 0

    if fg_score > base_score:
        return {"best": fg_score, "source": "fg", "hash": fg.loadout_hash if fg else ""}
    return {"best": base_score, "source": "base", "hash": base.loadout_hash if base else ""}


def _best_base_rescored_legacy(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    project_root: Path,
    cfg_dict: dict,
    ref_arrays: dict,
    calc_song_cache: dict[str, dict],
):
    """
    Recompute legacy best base score using GPU fixed scoring on persisted Stats.

    NOTE: This is a "staleness correction" pass for legacy DBs whose `score` column
    may have been produced under older scorers / chart data.
    """
    if not _table_exists(conn, "team_buff_loadouts"):
        return {"best": 0, "hash": ""}

    # Lazy imports to keep the default compare fast.
    import numpy as np

    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.pipeline.song_processor import get_base_calc_song
    from gear_optimizer.solver.scoring_core import lookup_reference_py
    from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.api.fixed_scoring import score_fixed_stats_gpu

    calc_song = calc_song_cache.get(song)
    if calc_song is None:
        fp = _song_file_from_name(project_root, song)
        if fp is None:
            # Fall back to the slower index scan used by EvolutionDbManager.
            from gear_optimizer.data.db_manager import _build_song_index_for_difficulty

            diff = _infer_difficulty_from_song_name(song)
            idx = _build_song_index_for_difficulty(diff)
            fp = Path(str(idx.get(song) or ""))
            if not fp.exists():
                return {"best": 0, "hash": ""}
        calc_song = get_base_calc_song(str(fp), cfg_dict)
        calc_song_cache[song] = calc_song

    meta = calc_song.get("metadata", {}) or {}
    primary = str(meta.get("Primary Color", "") or "").strip()
    secondary = str(meta.get("Secondary Color", "") or "").strip()
    if not primary and not secondary:
        return {"best": 0, "hash": ""}

    rows = conn.execute(
        """
        SELECT loadout_hash, details_json
        FROM team_buff_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        """,
        (str(song), str(team_buff)),
    ).fetchall()

    score_inputs = []
    hashes: list[str] = []
    for r in rows or []:
        h = str(r[0] or "").strip()
        details_json = r[1]
        if not h or not details_json:
            continue
        try:
            details = json.loads(details_json)
        except Exception:
            continue
        details = _unpack_stats_after_load(details) if isinstance(details, dict) else None
        stats = (details or {}).get("Stats") if isinstance(details, dict) else None
        if not isinstance(stats, dict) or not stats:
            continue

        pp_stat = int(stats.get("Perfect Points", 0) or 0)
        p_val = int(stats.get(primary, 0) or 0) if primary else 0
        s_val = int(stats.get(secondary, 0) or 0) if secondary else 0
        pp_factor = lookup_reference_py(pp_stat, ref_arrays["Perfect Points"], TOTAL_ROWS)
        cm_factor = lookup_reference_py(
            int(stats.get("Combo Multiplier", 0) or 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS
        )
        fm_factor = lookup_reference_py(
            int(stats.get("Fever Multiplier", 0) or 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS
        )

        base_value = (p_val * 2) + s_val + float(pp_factor)
        ft_idx = int(stats.get("Fever Time", 0) or 0)
        ff_idx = int(stats.get("Fever Fill Rate", 0) or 0)

        score_inputs.append(
            {
                "base_value": np.float32(base_value),
                "combo_mul": np.float32(cm_factor),
                "fever_mul": np.float32(fm_factor),
                "ft_idx": int(ft_idx),
                "ff_idx": int(ff_idx),
            }
        )
        hashes.append(h)

    if not score_inputs:
        return {"best": 0, "hash": ""}

    with _GPU_LOCK:
        gpu_scores = score_fixed_stats_gpu(score_inputs, calc_song, ref_arrays=ref_arrays)

    best_score = 0
    best_hash = ""
    for h, s in zip(hashes, gpu_scores, strict=True):
        si = int(s)
        if si > best_score:
            best_score = si
            best_hash = h
    return {"best": best_score, "hash": best_hash}


def _force_config_counts(force_details: dict, details: dict | None = None) -> list[int]:
    forced = force_details.get("forced_counts")
    if isinstance(forced, list) and forced:
        try:
            return [max(0, int(v or 0)) for v in forced]
        except Exception:
            pass

    cfg = None
    fg = force_details.get("ForceGreats")
    if isinstance(fg, dict):
        cfg = fg.get("config")
    if not isinstance(cfg, dict) and isinstance(details, dict):
        fg = details.get("ForceGreats")
        if isinstance(fg, dict):
            cfg = fg.get("config")

    if not isinstance(cfg, dict):
        return []

    out: list[int] = []
    i = 1
    while True:
        key = f"NonFever{i}"
        if key not in cfg:
            break
        try:
            out.append(max(0, int(cfg.get(key) or 0)))
        except Exception:
            out.append(0)
        i += 1
    return out


def _forced_counts_to_fp_targets(
    *,
    forced_counts: list[int],
    base_stats: dict,
    ft_gems: int,
    ff_gems: int,
    scorer,
    gem_scale_fever: int = 3,
) -> list[int]:
    if not forced_counts:
        return []
    ft_stat = int(base_stats.get("Fever Time", 0) or 0) + int(ft_gems) * int(gem_scale_fever)
    ff_stat = int(base_stats.get("Fever Fill Rate", 0) or 0) + int(ff_gems) * int(gem_scale_fever)
    non_fever_base, _fever_duration, _great_to_fill, raw_fill = scorer.get_fever_params(ft_stat, ff_stat)
    if int(non_fever_base) <= 0:
        return [0] * len(forced_counts)
    base_ceil = math.ceil(float(raw_fill))
    targets: list[int] = []
    for forced in forced_counts:
        k = max(0, int(forced or 0))
        fp = math.ceil(float(raw_fill) + (float(k) * 0.5)) - int(base_ceil)
        targets.append(max(0, int(fp)))
    return targets


def _best_fg_rescored_legacy(
    conn: sqlite3.Connection,
    *,
    song: str,
    team_buff: str,
    project_root: Path,
    cfg_dict: dict,
    ref_arrays: dict,
    calc_song_cache: dict[str, dict],
):
    """
    Recompute legacy FG rows with the current GPU exact-inner solver.

    Legacy FG payloads can be stale in the same way legacy base payloads can be:
    the persisted `fg_score` may have been produced by an older timeline/config
    ranking path. This pass keeps the persisted base stats, FT/FF gems, and
    forced-Great config, then re-solves the remaining gem budget exactly.
    """
    if not _table_exists(conn, "team_buff_fg_loadouts"):
        return {"best": 0, "hash": ""}

    import numpy as np

    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.pipeline.song_processor import get_base_calc_song
    from gear_optimizer.solver.analytical_fg import create_chart_scorer_from_calc_song
    from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.force_greats.api import solve_force_greats_finder_gpu

    rows = conn.execute(
        """
        SELECT loadout_hash, force_details_json, details_json
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=?
        """,
        (str(song), str(team_buff)),
    ).fetchall()
    if not rows:
        return {"best": 0, "hash": ""}

    calc_song = calc_song_cache.get(song)
    if calc_song is None:
        fp = _song_file_from_name(project_root, song)
        if fp is None:
            from gear_optimizer.data.db_manager import _build_song_index_for_difficulty

            diff = _infer_difficulty_from_song_name(song)
            idx = _build_song_index_for_difficulty(diff)
            fp = Path(str(idx.get(song) or ""))
            if not fp.exists():
                return {"best": 0, "hash": ""}
        calc_song = get_base_calc_song(str(fp), cfg_dict)
        calc_song_cache[song] = calc_song

    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = np.asarray(song_data.get("timestamps", ()), dtype=np.float32)
    if timestamps.size <= 0:
        return {"best": 0, "hash": ""}

    scorer = create_chart_scorer_from_calc_song(calc_song, ref_arrays)
    primary_default = str(meta.get("Primary Color", "") or "").strip()
    secondary_default = str(meta.get("Secondary Color", "") or "").strip()
    long_notes = int(meta.get("Long Notes", 0) or 0)
    last_note_time = float(meta.get("Last Note Time", timestamps[-1]) or timestamps[-1])

    groups: dict[tuple, list[tuple[str, dict]]] = {}
    for row in rows:
        loadout_hash = str(row[0] or "").strip()
        force_json = row[1]
        if not loadout_hash or not force_json:
            continue
        try:
            force_details = json.loads(force_json)
        except Exception:
            continue
        if not isinstance(force_details, dict):
            continue
        try:
            details = json.loads(row[2]) if row[2] else {}
        except Exception:
            details = {}
        if not isinstance(details, dict):
            details = {}

        base_stats = force_details.get("BaseStats")
        if not isinstance(base_stats, dict) or not base_stats:
            continue
        forced_counts = _force_config_counts(force_details, details)
        if not forced_counts:
            continue
        try:
            ft_gems = int(force_details.get("FT", 0) or 0)
            ff_gems = int(force_details.get("FF", 0) or 0)
        except Exception:
            continue

        selected = str(
            force_details.get("Selected Element")
            or force_details.get("SelectedElement")
            or details.get("SelectedElement")
            or details.get("se")
            or ""
        ).strip()
        primary = str(details.get("PrimaryColor") or details.get("pc") or primary_default or selected).strip()
        secondary = str(details.get("SecondaryColor") or details.get("sc") or secondary_default or selected).strip()
        if not primary or not secondary or not selected:
            continue

        try:
            fp_targets = _forced_counts_to_fp_targets(
                forced_counts=forced_counts,
                base_stats=base_stats,
                ft_gems=ft_gems,
                ff_gems=ff_gems,
                scorer=scorer,
            )
        except Exception:
            continue
        if not fp_targets:
            continue

        try:
            genome = {
                "base_pp": int(base_stats.get("Perfect Points", 0) or 0),
                "base_cm": int(base_stats.get("Combo Multiplier", 0) or 0),
                "base_fm": int(base_stats.get("Fever Multiplier", 0) or 0),
                "base_p_val": int(base_stats.get(primary, 0) or 0),
                "base_s_val": int(base_stats.get(secondary, 0) or 0),
                "base_ft_stat": int(base_stats.get("Fever Time", 0) or 0),
                "base_ff_stat": int(base_stats.get("Fever Fill Rate", 0) or 0),
            }
        except Exception:
            continue

        flags = build_color_flags(primary, secondary, selected)
        key = (
            primary,
            secondary,
            selected,
            int(ft_gems),
            int(ff_gems),
            tuple(int(x) for x in fp_targets),
            tuple(int(flags[k]) for k in sorted(flags)),
        )
        groups.setdefault(key, []).append((loadout_hash, genome))

    best_score = 0
    best_hash = ""
    for key, items in groups.items():
        primary, secondary, selected, ft_gems, ff_gems, fp_targets, _flags_tuple = key
        flags = build_color_flags(str(primary), str(secondary), str(selected))
        genomes = [g for _h, g in items]
        if not genomes:
            continue
        try:
            with _GPU_LOCK:
                out = solve_force_greats_finder_gpu(
                    genomes,
                    timestamps,
                    None,
                    int(long_notes),
                    float(last_note_time),
                    [list(fp_targets)],
                    [(int(ft_gems), int(ff_gems))],
                    n_sections=len(fp_targets),
                    ref_arrays=ref_arrays,
                    total_budget=90,
                    gem_scale_fever=3,
                    return_raw=True,
                    pair_caps_grid=None,
                    pair_caps_from_timeline=False,
                    song_slot=0,
                    cfg_chunk=64,
                    **flags,
                )
        except Exception:
            continue
        if not isinstance(out, dict) or "final_score" not in out:
            continue
        scores = out.get("final_score")
        for (loadout_hash, _genome), score in zip(items, scores, strict=False):
            si = int(score)
            if si > best_score:
                best_score = si
                best_hash = str(loadout_hash)

    return {"best": best_score, "hash": best_hash}


def _songs_in_db(conn: sqlite3.Connection, *, team_buff: str) -> set[str]:
    team_buff = _norm_team_buff(team_buff)
    out: set[str] = set()
    for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
        if not _table_exists(conn, table):
            continue
        rows = conn.execute(
            f"""
            SELECT DISTINCT song_name
            FROM {table}
            WHERE UPPER(COALESCE(team_buff,''))=?
            """,
            (str(team_buff),),
        ).fetchall()
        for r in rows or []:
            s = str(r[0] or "").strip()
            if s:
                out.add(s)
    return out


def _hash_present(conn: sqlite3.Connection, *, song: str, team_buff: str, loadout_hash: str) -> bool:
    if not loadout_hash:
        return False
    for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
        if not _table_exists(conn, table):
            continue
        row = conn.execute(
            f"""
            SELECT 1
            FROM {table}
            WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? AND loadout_hash=?
            LIMIT 1
            """,
            (str(song), str(team_buff), str(loadout_hash)),
        ).fetchone()
        if row is not None:
            return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Compare current vs legacy DB overall-best per song.")
    p.add_argument("--current", type=str, default=str(PROJECT_ROOT / "evolution.db"))
    p.add_argument("--legacy", type=str, default=str(PROJECT_ROOT / "evolution_legacy.db"))
    p.add_argument("--team-buff", type=str, default="T5")
    p.add_argument("--eps", type=int, default=2, help="Treat scores within +/- eps as ties.")
    p.add_argument("--artifacts-dir", type=str, default=str(PROJECT_ROOT / "artifacts"))
    p.add_argument("--examples", type=int, default=25, help="Max regression examples to embed in JSON.")
    p.add_argument(
        "--rescore-legacy-base",
        action="store_true",
        help="Recompute legacy base best via GPU fixed scoring on persisted Stats (staleness correction).",
    )
    p.add_argument(
        "--rescore-legacy-fg",
        action="store_true",
        help=(
            "Recompute legacy FG via the current GPU exact-inner solver when persisted FG would otherwise "
            "produce a regression."
        ),
    )
    p.add_argument(
        "--rescore-legacy-fg-full",
        action="store_true",
        help="Recompute legacy FG for every compared song. Slower; use for exhaustive audit reports.",
    )
    args = p.parse_args()

    current_db = Path(str(args.current))
    legacy_db = Path(str(args.legacy))
    if not current_db.exists():
        raise SystemExit(f"Current DB not found: {current_db}")
    if not legacy_db.exists():
        raise SystemExit(f"Legacy DB not found: {legacy_db}")

    team_buff = _norm_team_buff(args.team_buff)
    eps = max(0, int(args.eps))
    example_limit = max(0, int(args.examples))
    rescore_legacy_base = bool(args.rescore_legacy_base)
    rescore_legacy_fg = bool(args.rescore_legacy_fg or args.rescore_legacy_fg_full)
    rescore_legacy_fg_full = bool(args.rescore_legacy_fg_full)

    cur = sqlite3.connect(str(current_db))
    leg = sqlite3.connect(str(legacy_db))
    try:
        songs = sorted(_songs_in_db(cur, team_buff=team_buff) | _songs_in_db(leg, team_buff=team_buff))

        cfg_dict: dict = {}
        ref_arrays: dict = {}
        calc_song_cache: dict[str, dict] = {}
        if rescore_legacy_base or rescore_legacy_fg:
            from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
            from gear_optimizer.core.config import load_config
            from gear_optimizer.core.utils import cfg_to_dict

            cfg_dict = cfg_to_dict(load_config())
            ref_arrays = _get_team_buff_ref_arrays_cached()
            if not isinstance(ref_arrays, dict) or not ref_arrays:
                raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

        improvements = 0
        ties = 0
        regressions = 0
        regression_detail: list[dict] = []
        regression_buckets: dict[str, int] = {}

        for song in songs:
            cur_best = _best_overall(cur, song=song, team_buff=team_buff)
            cur_score = int(cur_best["best"] or 0)
            if not (rescore_legacy_base or rescore_legacy_fg):
                leg_best = _best_overall(leg, song=song, team_buff=team_buff)
            else:
                leg_fg_persisted = _best_fg(leg, song=song, team_buff=team_buff)
                leg_base = (
                    _best_base_rescored_legacy(
                        leg,
                        song=song,
                        team_buff=team_buff,
                        project_root=PROJECT_ROOT,
                        cfg_dict=cfg_dict,
                        ref_arrays=ref_arrays,
                        calc_song_cache=calc_song_cache,
                    )
                    if rescore_legacy_base
                    else _best_base(leg, song=song, team_buff=team_buff)
                )
                leg_base_score = (
                    int(leg_base.get("best") or 0)
                    if isinstance(leg_base, dict)
                    else (int(leg_base.score) if leg_base else 0)
                )
                leg_fg_persisted_score = int(leg_fg_persisted.score) if leg_fg_persisted else 0
                should_rescore_fg = bool(rescore_legacy_fg_full)
                if rescore_legacy_fg and not should_rescore_fg:
                    persisted_legacy_best = max(int(leg_base_score), int(leg_fg_persisted_score))
                    should_rescore_fg = bool(
                        leg_fg_persisted_score > leg_base_score
                        and int(cur_score) - int(persisted_legacy_best) < -int(eps)
                    )

                leg_fg = (
                    _best_fg_rescored_legacy(
                        leg,
                        song=song,
                        team_buff=team_buff,
                        project_root=PROJECT_ROOT,
                        cfg_dict=cfg_dict,
                        ref_arrays=ref_arrays,
                        calc_song_cache=calc_song_cache,
                    )
                    if should_rescore_fg
                    else leg_fg_persisted
                )
                leg_fg_score = int(leg_fg.get("best") if isinstance(leg_fg, dict) else leg_fg.score) if leg_fg else 0
                if leg_fg_score > leg_base_score:
                    leg_fg_hash = str(
                        leg_fg.get("hash") if isinstance(leg_fg, dict) else (leg_fg.loadout_hash if leg_fg else "")
                    )
                    leg_best = {"best": leg_fg_score, "source": "fg", "hash": leg_fg_hash}
                else:
                    leg_base_hash = str(
                        leg_base.get("hash")
                        if isinstance(leg_base, dict)
                        else (leg_base.loadout_hash if leg_base else "")
                    )
                    leg_best = {"best": leg_base_score, "source": "base", "hash": leg_base_hash}

            leg_score = int(leg_best["best"] or 0)
            delta = int(cur_score) - int(leg_score)

            if abs(delta) <= eps:
                ties += 1
                continue
            if delta > 0:
                improvements += 1
                continue

            regressions += 1
            legacy_hash = str(leg_best.get("hash") or "").strip()
            legacy_present = _hash_present(
                cur,
                song=song,
                team_buff=team_buff,
                loadout_hash=legacy_hash,
            )
            bucket = f"{leg_best.get('source')}:{'present' if legacy_present else 'missing'}"
            regression_buckets[bucket] = int(regression_buckets.get(bucket, 0)) + 1
            if example_limit and len(regression_detail) < example_limit:
                regression_detail.append(
                    {
                        "song": song,
                        "legacy_source": leg_best.get("source"),
                        "legacy_best": leg_score,
                        "current_best": cur_score,
                        "delta": delta,
                        "legacy_winner_present": legacy_present,
                        "legacy_hash": legacy_hash,
                        "current_hash": str(cur_best.get("hash") or "").strip(),
                    }
                )

        out = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "team_buff": team_buff,
            "eps": eps,
            "current_db": str(current_db),
            "legacy_db": str(legacy_db),
            "legacy_base_rescored": rescore_legacy_base,
            "legacy_fg_rescored": rescore_legacy_fg,
            "legacy_fg_rescore_full": rescore_legacy_fg_full,
            "songs_compared": len(songs),
            "counts": {
                "improvements": improvements,
                "ties": ties,
                "regressions": regressions,
            },
            "regression_buckets": dict(sorted(regression_buckets.items())),
            "regressions_detail": regression_detail,
        }

        artifacts_dir = Path(str(args.artifacts_dir))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = artifacts_dir / f"db_overall_best_compare_current_vs_legacy_{stamp}_eps{eps}.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

        print("=" * 80)
        print(f"overall_best (team_buff={team_buff}, eps=+/-{eps})")
        print("=" * 80)
        print(f"Songs compared: {len(songs):,}")
        print(f"Improvements: {improvements:,}")
        print(f"Ties: {ties:,}")
        print(f"Regressions: {regressions:,}")
        print("Wrote report:", str(out_path))
        return 0 if regressions == 0 else 2
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            leg.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
