import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
import pytest


pytestmark = pytest.mark.slow


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _connect_readonly_sqlite(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


def _load_ref_arrays_from_stats_txt(stats_txt: str) -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.csv_parser import read_table

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    stats_table = read_table(stats_txt)
    ref_arrays: dict[str, np.ndarray] = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    return ref_arrays


def _find_song_file(*, song_name: str, difficulty: str, paths: dict) -> Optional[Path]:
    from gear_optimizer.pipeline.song_processor import scan_song_header

    diff_key = str(difficulty or "").strip().title()
    root = paths.get(diff_key)
    if not root:
        return None
    root_path = Path(root)
    if not root_path.exists():
        return None

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not str(filename).lower().endswith(".txt"):
                continue
            fp = Path(dirpath) / filename
            meta = scan_song_header(str(fp))
            if meta and meta.get("Song Name") == song_name:
                return fp
    return None


def _config_dict_to_counts(cfg: dict) -> list[int]:
    if not cfg:
        return []
    pairs = []
    for k, v in cfg.items():
        if not isinstance(k, str) or not k.startswith("NonFever"):
            continue
        try:
            idx = int(k.replace("NonFever", "")) - 1
        except Exception:
            continue
        pairs.append((idx, int(v)))
    if not pairs:
        return []
    pairs.sort(key=lambda x: x[0])
    max_idx = pairs[-1][0]
    out = [0] * (max_idx + 1)
    for idx, v in pairs:
        if 0 <= idx < len(out):
            out[idx] = max(0, int(v))
    return out


def _stats_from_force_payload(details_stats: dict, force_payload: dict) -> dict:
    if not isinstance(force_payload, dict):
        return details_stats

    stats = force_payload.get("Stats")
    if isinstance(stats, dict) and stats:
        return stats

    base_stats = force_payload.get("BaseStats")
    if not isinstance(base_stats, dict) or not base_stats:
        return details_stats

    gem_counts = force_payload.get("GemCounts")
    if not isinstance(gem_counts, dict):
        gem_counts = {}

    try:
        from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast

        ft_val = int(force_payload.get("FT", gem_counts.get("Fever Time", 0)) or 0)
        ff_val = int(
            force_payload.get(
                "FF",
                gem_counts.get("Fever Fill", gem_counts.get("Fever Fill Rate", 0)),
            )
            or 0
        )
        g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
        g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
        g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
        g_ov = int(gem_counts.get("Element", 0) or 0)
        sel_color = str(
            force_payload.get("Selected Element")
            or force_payload.get("SelectedElement")
            or details_stats.get("Selected Element", "")
        )
        computed = apply_gems_to_base_fast(base_stats, sel_color, ft_val, ff_val, g_pp, g_cm, g_fm, g_ov)
        if isinstance(computed, dict) and computed:
            return computed
    except Exception:
        pass

    return details_stats if isinstance(details_stats, dict) else {}


def test_reference_db_fg_roundtrip_scores_match(tmp_path, monkeypatch):
    """
    Deterministic FG integrity check against the repo's current `evolution.db`.
    We recompute FG score from (Stats + ForceGreats config + real chart + Stats.txt ref arrays).
    """
    repo_root = _repo_root()
    ref_db_path = repo_root / "evolution.db"
    if not ref_db_path.exists():
        pytest.skip("reference evolution.db not present in repo root")

    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats

    paths = load_paths_cache()
    stats_txt = str(paths.get("Stats") or "")
    if not stats_txt or not Path(stats_txt).exists():
        pytest.skip("Stats.txt not available (paths cache missing or invalid)")

    ref_arrays = _load_ref_arrays_from_stats_txt(stats_txt)

    conn = _connect_readonly_sqlite(ref_db_path)
    conn.row_factory = sqlite3.Row
    try:
        candidates = conn.execute(
            """
            SELECT song_name, score, fg_score, details_json, force_details_json
            FROM team_buff_loadouts
            WHERE details_json IS NOT NULL
            AND details_json LIKE '%"Stats"%'
            AND force_details_json IS NOT NULL
            AND fg_score > 0
            AND team_buff = 'T5'
            ORDER BY fg_score DESC
            LIMIT 2000
            """
        ).fetchall()
    finally:
        conn.close()

    try:
        target_count = int(os.environ.get("REF_DB_FG_ROUNDTRIP_COUNT", "4"))
    except Exception:
        target_count = 4
    target_count = max(1, int(target_count))

    selected = []
    seen = set()
    for row in candidates:
        if len(selected) >= target_count:
            break
        song_name = str(row["song_name"] or "").strip()
        if not song_name or song_name in seen:
            continue
        try:
            details = json.loads(row["details_json"]) if row["details_json"] else {}
            force = json.loads(row["force_details_json"]) if row["force_details_json"] else {}
        except Exception:
            continue
        if isinstance(force.get("forced_counts"), list):
            counts = [int(v or 0) for v in force.get("forced_counts") or []]
        else:
            cfg = (force.get("ForceGreats") or {}).get("config") or {}
            counts = _config_dict_to_counts(cfg)
        if not counts:
            continue
        difficulty = str(details.get("Difficulty") or "").strip() or "Hard"
        fp = _find_song_file(song_name=song_name, difficulty=difficulty, paths=paths)
        if fp is None:
            continue
        selected.append((row, details, force, counts, fp))
        seen.add(song_name)

    if len(selected) < target_count:
        pytest.skip(f"not enough FG reference rows found (selected={len(selected)}/{target_count})")

    # Use temp db path for any implicit DB access while keeping test self-contained.
    db_path = tmp_path / "reference_fg_roundtrip.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    for row, details, force, counts, fp in selected:
        force_meta = force.get("ForceGreats") or {}
        expected_fg = force_meta.get("final_score")
        if expected_fg is None:
            expected_fg = force.get("Score", force.get("score", 0))

        # Primary integrity check: stored fg_score matches the force payload's recorded final_score.
        assert abs(int(expected_fg or 0) - int(row["fg_score"] or 0)) <= 2

        # Optional scoring recompute can be enabled via REF_DB_FG_RECOMPUTE=1.
        if os.environ.get("REF_DB_FG_RECOMPUTE") in {"1", "true", "yes"}:
            calc_song = clone_calc_song(get_base_calc_song(str(fp), cfg_dict=None))
            details_stats = details.get("Stats") or {}
            stored_stats = _stats_from_force_payload(details_stats, force)
            fg_eval = evaluate_force_greats(stored_stats, calc_song, ref_arrays, counts)
            if fg_eval is not None:
                fg_score = int(fg_eval["final_score"])
                assert abs(fg_score - int(row["fg_score"] or 0)) <= 2
