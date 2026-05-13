from __future__ import annotations

import argparse
import configparser
import contextlib
import copy
import io
import json
import multiprocessing
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

from gear_optimizer.core.utils import safe_float as _safe_float, safe_int as _safe_int


from gear_optimizer.core.parsing import env_get
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _summary_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    vals = [float(v) for v in values]
    return {
        "min": float(min(vals)),
        "max": float(max(vals)),
        "mean": float(sum(vals) / len(vals)),
    }


def _top_frequency(values: list[str]) -> tuple[str, int]:
    if not values:
        return "", 0
    counts = Counter(str(v or "") for v in values)
    key, count = counts.most_common(1)[0]
    return str(key), int(count)


def _loadout_hash_from_names(gear_names: list[str], mini_names: list[str]) -> str:
    import hashlib

    g = sorted([str(n) for n in (gear_names or []) if str(n)])
    m = sorted([str(n) for n in (mini_names or []) if str(n)])
    payload = f"GEAR:{'|'.join(g)}::MINIS:{'|'.join(m)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _extract_entry_colors(entry: dict[str, Any]) -> tuple[str, str, str]:
    details_raw = entry.get("details", {}) if isinstance(entry, dict) else {}
    details: dict[str, Any] = {}
    if isinstance(details_raw, dict):
        details = details_raw
    elif isinstance(details_raw, str) and details_raw.strip():
        try:
            details = json.loads(details_raw)
        except Exception:
            details = {}
    p_color = str(details.get("PrimaryColor") or details.get("primary_color") or "").strip()
    s_color = str(details.get("SecondaryColor") or details.get("secondary_color") or "").strip()
    sel_color = str(details.get("SelectedElement") or details.get("selected_element") or "").strip()
    if not sel_color:
        sel_color = p_color or s_color
    return p_color, s_color, sel_color


def _effective_loadout_hash_from_entry(entry: dict[str, Any], minis_by_name: dict[str, Any] | None) -> str:
    gear_raw = entry.get("gear") if isinstance(entry, dict) else []
    minis_raw = entry.get("minis") if isinstance(entry, dict) else []
    gear_names = [str(x.get("Name") if isinstance(x, dict) else x or "").strip() for x in (gear_raw or [])]
    mini_names = [str(x.get("Name") if isinstance(x, dict) else x or "").strip() for x in (minis_raw or [])]

    gear_names = [n for n in gear_names if n]
    mini_names = [n for n in mini_names if n]

    if not gear_names and not mini_names:
        return ""

    if not minis_by_name:
        return _loadout_hash_from_names(gear_names, mini_names)

    p_color, s_color, sel_color = _extract_entry_colors(entry)
    if not p_color and not s_color:
        return _loadout_hash_from_names(gear_names, mini_names)

    from gear_optimizer.data.loadout_equivalence import (
        effective_loadout_hash_from_names,
        effective_mini_signature_for_name,
    )

    mini_sigs = [effective_mini_signature_for_name(n, minis_by_name, p_color, s_color, sel_color) for n in mini_names]
    return str(effective_loadout_hash_from_names(gear_names, mini_sigs))


def _extract_top_hashes(
    persist_entries: list[dict[str, Any]], *, minis_by_name: dict[str, Any] | None = None
) -> tuple[str, str]:
    base_hash = ""
    fg_hash = ""
    base_best = -(1 << 60)
    fg_best = -(1 << 60)
    for entry in persist_entries or []:
        if not isinstance(entry, dict):
            continue
        loadout_hash = str(entry.get("loadout_hash", "") or "")
        if not loadout_hash:
            loadout_hash = _effective_loadout_hash_from_entry(entry, minis_by_name)
        score = _safe_int(entry.get("score", 0), 0)
        fg_score = _safe_int(entry.get("fg_score", 0), 0)
        if score > base_best:
            base_best = int(score)
            base_hash = loadout_hash
        if fg_score > fg_best:
            fg_best = int(fg_score)
            fg_hash = loadout_hash
    return base_hash, fg_hash


def summarize_depth_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    base_hashes = [str(row.get("base_hash", "") or "") for row in runs if row.get("base_hash")]
    fg_hashes = [str(row.get("fg_hash", "") or "") for row in runs if row.get("fg_hash")]
    stage_keys = sorted({key for row in runs for key in (row.get("stage_timing") or {}).keys()})
    gpu_keys = sorted({key for row in runs for key in (row.get("gpu_timing") or {}).keys()})

    base_mode_hash, base_mode_count = _top_frequency(base_hashes)
    fg_mode_hash, fg_mode_count = _top_frequency(fg_hashes)

    stage_means = {
        key: _summary_stats([_safe_float((row.get("stage_timing") or {}).get(key, 0.0), 0.0) for row in runs])
        for key in stage_keys
    }
    gpu_means = {
        key: _summary_stats([_safe_float((row.get("gpu_timing") or {}).get(key, 0.0), 0.0) for row in runs])
        for key in gpu_keys
    }

    return {
        "runs": int(len(runs)),
        "base_score": _summary_stats([_safe_float(row.get("best_score", 0), 0.0) for row in runs]),
        "fg_score": _summary_stats([_safe_float(row.get("best_fg_score", 0), 0.0) for row in runs]),
        "duplicate_genome_ratio": _summary_stats(
            [
                _safe_float(row.get("duplicate_genome_ratio", 0.0), 0.0)
                for row in runs
                if row.get("duplicate_genome_ratio") is not None
            ]
        ),
        "elapsed_wall_sec": _summary_stats([_safe_float(row.get("elapsed_wall_sec", 0.0), 0.0) for row in runs]),
        "pending_fg_jobs_song_after": _summary_stats(
            [_safe_float(row.get("pending_fg_jobs_song_after", 0.0), 0.0) for row in runs]
        ),
        "pending_fg_jobs_song_delta": _summary_stats(
            [_safe_float(row.get("pending_fg_jobs_song_delta", 0.0), 0.0) for row in runs]
        ),
        "unique_base_hashes": int(len(set(base_hashes))),
        "unique_fg_hashes": int(len(set(fg_hashes))),
        "base_mode_hash": base_mode_hash,
        "base_mode_count": int(base_mode_count),
        "base_stability_ratio": (float(base_mode_count) / float(len(runs))) if runs else 0.0,
        "fg_mode_hash": fg_mode_hash,
        "fg_mode_count": int(fg_mode_count),
        "fg_stability_ratio": (float(fg_mode_count) / float(len(runs))) if runs else 0.0,
        "error_runs": int(sum(1 for row in runs if str(row.get("error", "") or "").strip())),
        "fg_debt_runs": int(sum(1 for row in runs if _safe_int(row.get("pending_fg_jobs_song_delta", 0), 0) > 0)),
        "stage_timing": stage_means,
        "gpu_timing": gpu_means,
    }


def _load_cfg_dict(config_path: Path) -> dict[str, Any]:
    from gear_optimizer.core.utils import cfg_to_dict

    cfg = configparser.ConfigParser()
    cfg.read(str(config_path), encoding="utf-8-sig")
    return cfg_to_dict(cfg)


def _load_runtime_inputs():
    import numpy as np

    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table

    paths = load_paths_cache()
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays: dict[str, object] = {}
    for i, name in enumerate(stat_names):
        temp_list: list[float] = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}
    return paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name


def _resolve_song_file(paths: dict[str, Any], difficulty: str, found_song_name: str) -> str:
    data_dir = Path(str(paths.get("Data", "Data") or "Data"))
    diff_dir = data_dir / str(difficulty)
    direct = diff_dir / f"{found_song_name}.txt"
    if direct.exists():
        return str(direct)
    for cand in diff_dir.glob("*.txt"):
        if cand.stem == found_song_name:
            return str(cand)
    raise FileNotFoundError(f"Song file not found for {difficulty}: {found_song_name}")


def _prepare_cfg_dict(
    *,
    base_cfg_dict: dict[str, Any],
    song_name: str,
    difficulty: str,
    ga_depth: int,
    ga_multi_start: int,
    fg_candidate_limit: int,
    fg_search_radius: int,
) -> dict[str, Any]:
    cfg_dict = copy.deepcopy(base_cfg_dict)
    cfg_dict.setdefault("CalculateSong", {})
    cfg_dict.setdefault("IterationEngine", {})
    cfg_dict.setdefault("UserInputStatsGems", {})
    cfg_dict.setdefault("ElementalGems", {})

    calc = cfg_dict["CalculateSong"]
    calc["Song_Name"] = str(song_name)
    calc["Difficulty"] = str(difficulty)

    ie = cfg_dict["IterationEngine"]
    ie["LoopForever"] = "false"
    ie["SongRepeats"] = "1"
    ie["BundleSongRepeats"] = "false"
    ie["GA_SearchDepth"] = str(int(ga_depth))
    ie["GA_MultiStart"] = str(int(ga_multi_start))
    ie["FG_CandidateLimit"] = str(int(fg_candidate_limit))
    ie["FG_SearchRadius"] = str(int(fg_search_radius))

    for k in ("perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"):
        cfg_dict["UserInputStatsGems"][k] = "0"
    for k in ("Chill", "Flow", "Rush", "Beat", "Vibe"):
        cfg_dict["ElementalGems"][k] = "0"

    return cfg_dict


def _read_last_audit_record(audit_path: Path, song_name: str) -> dict[str, Any] | None:
    if not audit_path.exists():
        return None
    last = None
    with audit_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if str(record.get("song_name", "") or "") == str(song_name):
                last = record
    return last


def _resolve_db_source_path(explicit_db_path: str | None = None) -> Path | None:
    if explicit_db_path:
        path = Path(str(explicit_db_path))
        return path if path.exists() else None
    env_path = env_get("EVOLUTION_DB_PATH")
    if env_path:
        path = Path(str(env_path))
        return path if path.exists() else None
    default_path = PROJECT_ROOT / "evolution.db"
    return default_path if default_path.exists() else None


def _prepare_seed_db(*, db_source_path: Path | None, temp_root: Path, depth: int, ga_seed: int) -> Path:
    run_db_path = temp_root / f"depth_{int(depth)}_seed_{int(ga_seed)}.db"
    if db_source_path is not None and db_source_path.exists():
        shutil.copy2(str(db_source_path), str(run_db_path))
    return run_db_path


def _count_pending_fg_jobs_for_song(db_path: Path, song_name: str) -> int:
    if not db_path.exists():
        return 0
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='pending_fg_jobs'"
            ).fetchone()
            if not row or int(row[0] or 0) <= 0:
                return 0
            result = conn.execute(
                "SELECT COUNT(*) FROM pending_fg_jobs WHERE song_name = ?",
                (str(song_name),),
            ).fetchone()
            return int((result or [0])[0] or 0)
    except Exception:
        return 0


def _cleanup_temp_root(temp_root: Path) -> None:
    for _ in range(10):
        try:
            shutil.rmtree(str(temp_root))
            return
        except PermissionError:
            time.sleep(0.2)
        except FileNotFoundError:
            return
    try:
        shutil.rmtree(str(temp_root), ignore_errors=True)
    except Exception:
        pass


def _start_post_processor(total_tasks: int) -> tuple[Any, Any]:
    from gear_optimizer.pipeline.post_processor import run_post_processor

    post_queue_size = _safe_int(env_get("POST_PIPELINE_QUEUE", 0), 0)
    post_queue_maxsize = 0 if post_queue_size <= 0 else max(1, post_queue_size)
    post_queue = multiprocessing.Queue(maxsize=post_queue_maxsize)
    post_proc = multiprocessing.Process(
        target=run_post_processor,
        args=(post_queue, int(total_tasks)),
        daemon=True,
        name="SongPostProcessorBench",
    )
    post_proc.start()
    return post_queue, post_proc


def _stop_post_processor(post_queue: Any, post_proc: Any) -> None:
    sentinel_sent = False
    try:
        if post_queue is not None:
            t0 = time.perf_counter()
            while True:
                try:
                    post_queue.put(None, block=True, timeout=0.5)
                    sentinel_sent = True
                    break
                except Exception:
                    try:
                        if post_proc is None or not post_proc.is_alive():
                            break
                    except Exception:
                        break
                    if (time.perf_counter() - t0) >= 15.0:
                        break
                    continue
    except Exception:
        pass
    try:
        if post_proc is not None:
            post_proc.join(timeout=120.0 if sentinel_sent else 5.0)
    except Exception:
        pass
    try:
        if post_proc is not None and post_proc.is_alive():
            post_proc.terminate()
            post_proc.join(timeout=5.0)
    except Exception:
        pass


def _query_team_buff_bests(db_path: Path, song_name: str, *, team_buff: str = "T5") -> dict[str, Any]:
    out: dict[str, Any] = {
        "best_score": 0,
        "best_fg_score": 0,
        "base_hash": "",
        "fg_hash": "",
        "base_rows": 0,
        "fg_rows": 0,
        "pending_fg_jobs": 0,
    }
    if not db_path.exists():
        return out

    try:
        with sqlite3.connect(str(db_path)) as conn:
            base = conn.execute(
                """
                SELECT loadout_hash, score
                FROM team_buff_loadouts
                WHERE song_name = ? AND team_buff = ?
                ORDER BY score DESC, timestamp DESC
                LIMIT 1
                """,
                (str(song_name), str(team_buff)),
            ).fetchone()
            if base:
                out["base_hash"] = str(base[0] or "")
                out["best_score"] = _safe_int(base[1], 0)

            fg = conn.execute(
                """
                SELECT loadout_hash, fg_score
                FROM team_buff_fg_loadouts
                WHERE song_name = ? AND team_buff = ?
                ORDER BY fg_score DESC, timestamp DESC
                LIMIT 1
                """,
                (str(song_name), str(team_buff)),
            ).fetchone()
            if fg:
                out["fg_hash"] = str(fg[0] or "")
                out["best_fg_score"] = _safe_int(fg[1], 0)

            base_rows = conn.execute(
                "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name = ? AND team_buff = ?",
                (str(song_name), str(team_buff)),
            ).fetchone()
            if base_rows:
                out["base_rows"] = _safe_int(base_rows[0], 0)

            fg_rows = conn.execute(
                "SELECT COUNT(*) FROM team_buff_fg_loadouts WHERE song_name = ? AND team_buff = ?",
                (str(song_name), str(team_buff)),
            ).fetchone()
            if fg_rows:
                out["fg_rows"] = _safe_int(fg_rows[0], 0)

            pending = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='pending_fg_jobs'"
            ).fetchone()
            if pending and _safe_int(pending[0], 0) > 0:
                pending_rows = conn.execute(
                    "SELECT COUNT(*) FROM pending_fg_jobs WHERE song_name = ?",
                    (str(song_name),),
                ).fetchone()
                if pending_rows:
                    out["pending_fg_jobs"] = _safe_int(pending_rows[0], 0)
    except Exception:
        return out

    return out


def run_single_seed_direct(
    *,
    fp: str,
    song_name: str,
    difficulty: str,
    cfg_dict: dict[str, Any],
    paths: dict[str, Any],
    ref_arrays: dict[str, Any],
    all_gears: list[Any],
    all_minis: list[Any],
    gears_by_name: dict[str, Any],
    minis_by_name: dict[str, Any],
    ga_depth: int,
    ga_seed: int,
    audit_path: Path,
    run_db_path: Path,
) -> dict[str, Any]:
    from gear_optimizer.pipeline.song_processor import safe_process_song_task

    repeat_ctx = {"repeat_index": 1, "repeat_total": 1, "ga_seed": int(ga_seed)}
    task = (
        fp,
        song_name,
        difficulty,
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        True,
        int(ga_depth),
        None,
        1,
        False,
        repeat_ctx,
    )

    old_audit = env_get("GA_REDUNDANCY_AUDIT")
    old_audit_path = env_get("GA_REDUNDANCY_AUDIT_PATH")
    old_db_path = env_get("EVOLUTION_DB_PATH")
    os.environ["GA_REDUNDANCY_AUDIT"] = "1"
    os.environ["GA_REDUNDANCY_AUDIT_PATH"] = str(audit_path)
    os.environ["EVOLUTION_DB_PATH"] = str(run_db_path)
    pending_fg_before = _count_pending_fg_jobs_for_song(run_db_path, song_name)
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            res = safe_process_song_task(task)
    finally:
        if old_audit is None:
            os.environ.pop("GA_REDUNDANCY_AUDIT", None)
        else:
            os.environ["GA_REDUNDANCY_AUDIT"] = old_audit
        if old_audit_path is None:
            os.environ.pop("GA_REDUNDANCY_AUDIT_PATH", None)
        else:
            os.environ["GA_REDUNDANCY_AUDIT_PATH"] = old_audit_path
        if old_db_path is None:
            os.environ.pop("EVOLUTION_DB_PATH", None)
        else:
            os.environ["EVOLUTION_DB_PATH"] = old_db_path
    elapsed = time.perf_counter() - t0

    if not isinstance(res, dict):
        return {"seed": int(ga_seed), "error": "non-dict-result", "elapsed_wall_sec": float(elapsed)}

    best_data = res.get("best_data") if isinstance(res.get("best_data"), dict) else {}
    base_hash, fg_hash = _extract_top_hashes(res.get("persist_entries") or [], minis_by_name=minis_by_name)
    record = res.get("_record") if isinstance(res.get("_record"), dict) else {}
    audit_record = _read_last_audit_record(audit_path, song_name)
    pending_fg_after = _count_pending_fg_jobs_for_song(run_db_path, song_name)

    return {
        "seed": int(ga_seed),
        "elapsed_wall_sec": float(elapsed),
        "best_score": _safe_int(best_data.get("BaseScore", best_data.get("Score", 0)), 0),
        "best_fg_score": _safe_int(record.get("best_fg_score_run", 0), 0),
        "base_hash": base_hash,
        "fg_hash": fg_hash,
        "stage_timing": dict(res.get("_stage_timing") or {}),
        "gpu_timing": dict(res.get("_gpu_timing") or {}),
        "duplicate_genome_ratio": None
        if audit_record is None
        else _safe_float(audit_record.get("duplicate_genome_ratio", 0.0), 0.0),
        "duplicate_signature_ratio": None
        if audit_record is None
        else _safe_float(audit_record.get("duplicate_signature_ratio", 0.0), 0.0),
        "pending_fg_jobs_song_before": int(pending_fg_before),
        "pending_fg_jobs_song_after": int(pending_fg_after),
        "pending_fg_jobs_song_delta": int(pending_fg_after - pending_fg_before),
        "error": str(res.get("_error", "") or ""),
    }


def run_single_seed_inflight(
    *,
    fp: str,
    song_name: str,
    difficulty: str,
    cfg_dict: dict[str, Any],
    paths: dict[str, Any],
    ref_arrays: dict[str, Any],
    all_gears: list[Any],
    all_minis: list[Any],
    gears_by_name: dict[str, Any],
    minis_by_name: dict[str, Any],
    ga_depth: int,
    ga_seed: int,
    audit_path: Path,
    run_db_path: Path,
) -> dict[str, Any]:
    from gear_optimizer.solver.native_inflight_orchestrator import run_native_inflight_song_pipeline

    repeat_ctx = {"repeat_index": 1, "repeat_total": 1, "ga_seed": int(ga_seed)}
    task = (
        fp,
        song_name,
        difficulty,
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        True,
        int(ga_depth),
        None,
        1,
        False,
        repeat_ctx,
    )

    old_audit = env_get("GA_REDUNDANCY_AUDIT")
    old_audit_path = env_get("GA_REDUNDANCY_AUDIT_PATH")
    old_db_path = env_get("EVOLUTION_DB_PATH")
    os.environ["GA_REDUNDANCY_AUDIT"] = "1"
    os.environ["GA_REDUNDANCY_AUDIT_PATH"] = str(audit_path)
    os.environ["EVOLUTION_DB_PATH"] = str(run_db_path)
    try:
        from gear_optimizer.data.database import init_db

        init_db()
    except Exception:
        pass

    pending_fg_before = _count_pending_fg_jobs_for_song(run_db_path, song_name)
    post_queue, post_proc = _start_post_processor(total_tasks=1)
    completed_songs: set[str] = set()
    t0 = time.perf_counter()
    error_msg = ""
    try:
        run_native_inflight_song_pipeline(
            [task],
            in_flight_songs=1,
            completed_songs=completed_songs,
            memory_resume_tracker=None,
            post_queue=post_queue,
            total_tasks=1,
            stop_requested=None,
            progress_cb=None,
            bundle_completed_cb=None,
        )
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
    finally:
        _stop_post_processor(post_queue, post_proc)
        if old_audit is None:
            os.environ.pop("GA_REDUNDANCY_AUDIT", None)
        else:
            os.environ["GA_REDUNDANCY_AUDIT"] = old_audit
        if old_audit_path is None:
            os.environ.pop("GA_REDUNDANCY_AUDIT_PATH", None)
        else:
            os.environ["GA_REDUNDANCY_AUDIT_PATH"] = old_audit_path
        if old_db_path is None:
            os.environ.pop("EVOLUTION_DB_PATH", None)
        else:
            os.environ["EVOLUTION_DB_PATH"] = old_db_path

    elapsed = time.perf_counter() - t0
    audit_record = _read_last_audit_record(audit_path, song_name)
    summary = _query_team_buff_bests(run_db_path, song_name, team_buff="T5")
    pending_fg_after = _count_pending_fg_jobs_for_song(run_db_path, song_name)

    return {
        "seed": int(ga_seed),
        "elapsed_wall_sec": float(elapsed),
        "best_score": _safe_int(summary.get("best_score", 0), 0),
        "best_fg_score": _safe_int(summary.get("best_fg_score", 0), 0),
        "base_hash": str(summary.get("base_hash", "") or ""),
        "fg_hash": str(summary.get("fg_hash", "") or ""),
        "stage_timing": {},
        "gpu_timing": {},
        "duplicate_genome_ratio": None
        if audit_record is None
        else _safe_float(audit_record.get("duplicate_genome_ratio", 0.0), 0.0),
        "duplicate_signature_ratio": None
        if audit_record is None
        else _safe_float(audit_record.get("duplicate_signature_ratio", 0.0), 0.0),
        "pending_fg_jobs_song_before": int(pending_fg_before),
        "pending_fg_jobs_song_after": int(pending_fg_after),
        "pending_fg_jobs_song_delta": int(pending_fg_after - pending_fg_before),
        "error": str(error_msg or ""),
    }


def run_benchmark(
    *,
    song_name: str,
    difficulty: str,
    config_path: Path,
    depths: list[int],
    seeds: list[int],
    ga_multi_start: int,
    use_db: bool,
    fg_candidate_limit: int,
    fg_search_radius: int,
    pipeline: str = "inflight",
    db_path: str | None = None,
) -> dict[str, Any]:
    pipeline = str(pipeline or "").strip().lower()
    if pipeline not in {"direct", "inflight"}:
        raise ValueError(f"Unknown pipeline: {pipeline}")

    base_cfg_dict = _load_cfg_dict(config_path)
    paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name = _load_runtime_inputs()
    fp = _resolve_song_file(paths, str(difficulty), str(song_name))

    explicit_db_path = bool(db_path and str(db_path).strip())
    allow_db_source = bool(explicit_db_path or use_db)
    db_source_path = _resolve_db_source_path(db_path if explicit_db_path else None) if allow_db_source else None
    all_depth_runs: dict[str, list[dict[str, Any]]] = {}
    temp_root = Path(tempfile.mkdtemp(prefix="ga_stability_"))
    try:
        audit_path = temp_root / "ga_redundancy.jsonl"
        for depth in depths:
            rows: list[dict[str, Any]] = []
            for seed in seeds:
                cfg_dict = _prepare_cfg_dict(
                    base_cfg_dict=base_cfg_dict,
                    song_name=str(song_name),
                    difficulty=str(difficulty),
                    ga_depth=int(depth),
                    ga_multi_start=int(ga_multi_start),
                    fg_candidate_limit=int(fg_candidate_limit),
                    fg_search_radius=int(fg_search_radius),
                )
                run_db_path = _prepare_seed_db(
                    db_source_path=db_source_path,
                    temp_root=temp_root,
                    depth=int(depth),
                    ga_seed=int(seed),
                )
                if pipeline == "direct":
                    row = run_single_seed_direct(
                        fp=fp,
                        song_name=str(song_name),
                        difficulty=str(difficulty),
                        cfg_dict=cfg_dict,
                        paths=paths,
                        ref_arrays=ref_arrays,
                        all_gears=all_gears,
                        all_minis=all_minis,
                        gears_by_name=gears_by_name,
                        minis_by_name=minis_by_name,
                        ga_depth=int(depth),
                        ga_seed=int(seed),
                        audit_path=audit_path,
                        run_db_path=run_db_path,
                    )
                else:
                    row = run_single_seed_inflight(
                        fp=fp,
                        song_name=str(song_name),
                        difficulty=str(difficulty),
                        cfg_dict=cfg_dict,
                        paths=paths,
                        ref_arrays=ref_arrays,
                        all_gears=all_gears,
                        all_minis=all_minis,
                        gears_by_name=gears_by_name,
                        minis_by_name=minis_by_name,
                        ga_depth=int(depth),
                        ga_seed=int(seed),
                        audit_path=audit_path,
                        run_db_path=run_db_path,
                    )
                rows.append(row)
            all_depth_runs[str(depth)] = rows
    finally:
        _cleanup_temp_root(temp_root)

    summary = {depth: summarize_depth_runs(rows) for depth, rows in all_depth_runs.items()}
    return {
        "pipeline": str(pipeline),
        "song_name": str(song_name),
        "difficulty": str(difficulty),
        "config_path": str(config_path),
        "depths": [int(d) for d in depths],
        "seeds": [int(s) for s in seeds],
        "ga_multi_start": int(ga_multi_start),
        "use_db": bool(use_db),
        "fg_candidate_limit": int(fg_candidate_limit),
        "fg_search_radius": int(fg_search_radius),
        "db_source_path": "" if db_source_path is None else str(db_source_path),
        "seed_db_isolated": True,
        "runs_by_depth": all_depth_runs,
        "summary_by_depth": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Measure winner stability and stage timings across depths/seeds.")
    ap.add_argument("--song-name", required=True, help='Exact found song name, e.g. "2NITE (Hard) by nanobii".')
    ap.add_argument("--difficulty", default="Hard")
    ap.add_argument("--config", default="config.ini")
    ap.add_argument("--depths", default="6,12,18,24")
    ap.add_argument("--seeds", default="1337,1338,1339,1340,1341")
    ap.add_argument(
        "--pipeline",
        default="inflight",
        choices=["inflight", "direct"],
        help="Execution pipeline: inflight matches production main.py; direct calls safe_process_song_task.",
    )
    ap.add_argument("--ga-multi-start", type=int, default=3)
    ap.add_argument("--use-db", action="store_true", help="Enable EvolutionDB reads during the run.")
    ap.add_argument("--fg-candidate-limit", type=int, default=51)
    ap.add_argument("--fg-search-radius", type=int, default=5)
    ap.add_argument(
        "--db-path",
        default="",
        help="Optional DB snapshot to copy per seed. Defaults to EVOLUTION_DB_PATH or ./evolution.db when present.",
    )
    ap.add_argument(
        "--out",
        default=str(Path("artifacts") / "runcheck" / "ga_winner_stability.json"),
        help="Output JSON path.",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config_path = Path(str(args.config))
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    depths = [int(part.strip()) for part in str(args.depths or "").split(",") if part.strip()]
    seeds = [int(part.strip()) for part in str(args.seeds or "").split(",") if part.strip()]
    if not depths:
        raise SystemExit("--depths must include at least one integer.")
    if not seeds:
        raise SystemExit("--seeds must include at least one integer.")

    out_path = Path(str(args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = run_benchmark(
        song_name=str(args.song_name),
        difficulty=str(args.difficulty),
        config_path=config_path,
        depths=depths,
        seeds=seeds,
        ga_multi_start=int(args.ga_multi_start),
        use_db=bool(args.use_db),
        fg_candidate_limit=int(args.fg_candidate_limit),
        fg_search_radius=int(args.fg_search_radius),
        pipeline=str(args.pipeline),
        db_path=str(args.db_path or ""),
    )
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[stability] wrote {out_path}")
    for depth in depths:
        depth_key = str(depth)
        row = payload["summary_by_depth"][depth_key]
        print(
            "[stability] depth={} base_stability={:.2f} unique_base_hashes={} dup_mean={:.2%} wall_mean={:.3f}s".format(
                int(depth),
                float(row.get("base_stability_ratio", 0.0) or 0.0),
                int(row.get("unique_base_hashes", 0) or 0),
                float((row.get("duplicate_genome_ratio") or {}).get("mean", 0.0) or 0.0),
                float((row.get("elapsed_wall_sec") or {}).get("mean", 0.0) or 0.0),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
