from __future__ import annotations

import argparse
import configparser
import contextlib
import copy
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return float(default)


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


def _extract_top_hashes(persist_entries: list[dict[str, Any]]) -> tuple[str, str]:
    from gear_optimizer.data.database import get_loadout_hash

    base_hash = ""
    fg_hash = ""
    base_best = -(1 << 60)
    fg_best = -(1 << 60)
    for entry in persist_entries or []:
        if not isinstance(entry, dict):
            continue
        loadout_hash = str(entry.get("loadout_hash", "") or "")
        if not loadout_hash:
            try:
                loadout_hash = str(get_loadout_hash(entry.get("gear") or [], entry.get("minis") or []) or "")
            except Exception:
                loadout_hash = ""
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
    use_evo_db: bool,
    fg_candidate_limit: int,
    fg_search_radius: int,
    hitsim_enabled: bool,
    hitsim_seed: int,
) -> dict[str, Any]:
    cfg_dict = copy.deepcopy(base_cfg_dict)
    cfg_dict.setdefault("CalculateSong", {})
    cfg_dict.setdefault("IterationEngine", {})
    cfg_dict.setdefault("HumanHitSim", {})
    cfg_dict.setdefault("UserInputStatsGems", {})
    cfg_dict.setdefault("ElementalGems", {})

    calc = cfg_dict["CalculateSong"]
    calc["Song_Name"] = str(song_name)
    calc["Difficulty"] = str(difficulty)

    ie = cfg_dict["IterationEngine"]
    ie["GPU_Mode"] = "true"
    ie["GPU_Native_GA"] = "true"
    ie["LoopForever"] = "false"
    ie["SongRepeats"] = "1"
    ie["BundleSongRepeats"] = "false"
    ie["UseEvolutionDB"] = "true" if use_evo_db else "false"
    ie["GA_SearchDepth"] = str(int(ga_depth))
    ie["GA_MultiStart"] = str(int(ga_multi_start))
    ie["FG_CandidateLimit"] = str(int(fg_candidate_limit))
    ie["FG_SearchRadius"] = str(int(fg_search_radius))

    hh = cfg_dict["HumanHitSim"]
    hh["Enabled"] = "true" if hitsim_enabled else "false"
    hh["ApplyTo"] = "FG"
    hh["Seed"] = str(int(hitsim_seed))

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
    env_path = os.environ.get("EVOLUTION_DB_PATH")
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


def run_single_seed(
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
    use_evo_db: bool,
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
        bool(use_evo_db),
        True,
        int(ga_depth),
        None,
        1,
        False,
        repeat_ctx,
    )

    old_audit = os.environ.get("GA_REDUNDANCY_AUDIT")
    old_audit_path = os.environ.get("GA_REDUNDANCY_AUDIT_PATH")
    old_db_path = os.environ.get("EVOLUTION_DB_PATH")
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
    base_hash, fg_hash = _extract_top_hashes(res.get("persist_entries") or [])
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
    hitsim_enabled: bool,
    hitsim_seed: int,
    db_path: str | None = None,
) -> dict[str, Any]:
    base_cfg_dict = _load_cfg_dict(config_path)
    paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name = _load_runtime_inputs()
    fp = _resolve_song_file(paths, str(difficulty), str(song_name))

    db_source_path = _resolve_db_source_path(db_path)
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
                    use_evo_db=bool(use_db),
                    fg_candidate_limit=int(fg_candidate_limit),
                    fg_search_radius=int(fg_search_radius),
                    hitsim_enabled=bool(hitsim_enabled),
                    hitsim_seed=int(hitsim_seed),
                )
                run_db_path = _prepare_seed_db(
                    db_source_path=db_source_path,
                    temp_root=temp_root,
                    depth=int(depth),
                    ga_seed=int(seed),
                )
                row = run_single_seed(
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
                    use_evo_db=bool(use_db),
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
        "song_name": str(song_name),
        "difficulty": str(difficulty),
        "config_path": str(config_path),
        "depths": [int(d) for d in depths],
        "seeds": [int(s) for s in seeds],
        "ga_multi_start": int(ga_multi_start),
        "use_db": bool(use_db),
        "fg_candidate_limit": int(fg_candidate_limit),
        "fg_search_radius": int(fg_search_radius),
        "hitsim_enabled": bool(hitsim_enabled),
        "hitsim_seed": int(hitsim_seed),
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
    ap.add_argument("--ga-multi-start", type=int, default=3)
    ap.add_argument("--use-db", action="store_true", help="Enable EvolutionDB reads during the run.")
    ap.add_argument("--fg-candidate-limit", type=int, default=51)
    ap.add_argument("--fg-search-radius", type=int, default=5)
    ap.add_argument("--hitsim-enabled", action="store_true")
    ap.add_argument("--hitsim-seed", type=int, default=1)
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
        hitsim_enabled=bool(args.hitsim_enabled),
        hitsim_seed=int(args.hitsim_seed),
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
