from __future__ import annotations

import argparse
import configparser
import copy
import json
import os
import sys
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def _truthy(v: object) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _round6(v: float) -> float:
    return round(float(v), 6)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def _parse_int_csv(raw: object) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for part in str(raw or "").split(","):
        piece = str(part or "").strip()
        if not piece:
            continue
        value = int(piece)
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _resolve_ga_seeds(args: argparse.Namespace) -> list[int]:
    explicit = _parse_int_csv(getattr(args, "ga_seeds", ""))
    if explicit:
        return explicit

    base = int(getattr(args, "ga_seed_base", 1337)) & 0xFFFFFFFF
    runs = max(1, int(getattr(args, "ga_runs", 1)))
    out: list[int] = []
    used: set[int] = set()
    for idx in range(runs):
        seed = int((base + idx) & 0xFFFFFFFF) or 1
        while seed in used:
            seed = int((seed + 1) & 0xFFFFFFFF) or 1
        used.add(seed)
        out.append(seed)
    return out


def _load_cfg_dict(config_path: Path) -> dict:
    from gear_optimizer.core.utils import cfg_to_dict

    cfg = configparser.ConfigParser()
    cfg.read(str(config_path), encoding="utf-8-sig")
    return cfg_to_dict(cfg)


def _force_autozero_manual_inputs(cfg_dict: dict) -> None:
    cfg_dict.setdefault("UserInputStatsGems", {})
    cfg_dict.setdefault("ElementalGems", {})
    for k in ("perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"):
        cfg_dict["UserInputStatsGems"][k] = "0"
    for k in ("Chill", "Flow", "Rush", "Beat", "Vibe"):
        cfg_dict["ElementalGems"][k] = "0"


def _get_song_keys(song: str, artist: str) -> dict[str, str]:
    return {
        "Easy": f"{song} (Easy) by {artist}",
        "Normal": f"{song} by {artist}",
        "Hard": f"{song} (Hard) by {artist}",
    }


def _resolve_song_file(paths: dict, difficulty: str, song_key: str) -> str:
    data_dir = Path(paths.get("Data", "Data") or "Data")
    diff_dir = data_dir / difficulty
    fp = diff_dir / f"{song_key}.txt"
    if fp.exists():
        return str(fp)
    for cand in diff_dir.glob("*.txt"):
        if cand.stem == song_key:
            return str(cand)
    raise FileNotFoundError(f"Song file not found for {difficulty}: {song_key}")


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
    gears_by_name = {str(g.get("Name", "")): g for g in all_gears if isinstance(g, dict)}
    minis_by_name = {str(m.get("Name", "")): m for m in all_minis if isinstance(m, dict)}
    return paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name


def _candidate_key(gear_names: list[str], mini_names: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    gear_key = tuple(str(x or "") for x in (gear_names or []))
    mini_key = tuple(sorted(str(x or "") for x in (mini_names or [])))
    return gear_key, mini_key


def _key_to_label(key: tuple[tuple[str, ...], tuple[str, ...]]) -> str:
    gear, minis = key
    return " / ".join(
        [
            "gear=" + ",".join(gear),
            "minis=" + ",".join(minis),
        ]
    )


def _prepare_cfg_dict(
    base_cfg_dict: dict,
    *,
    hitsim_seed: int,
    ga_depth: int | None,
    candidate_limit: int,
    disable_fg: bool,
) -> dict:
    cfg_dict = copy.deepcopy(base_cfg_dict)
    _force_autozero_manual_inputs(cfg_dict)

    cfg_dict.setdefault("IterationEngine", {})
    cfg_dict.setdefault("HumanHitSim", {})

    # Isolate the experiment from DB state and queue-repeat behavior.
    cfg_dict["IterationEngine"]["useevolutiondb"] = "false"
    cfg_dict["IterationEngine"]["loopforever"] = "false"
    cfg_dict["IterationEngine"]["songrepeats"] = "1"
    cfg_dict["IterationEngine"]["fg_candidatelimit"] = str(int(candidate_limit))
    cfg_dict["IterationEngine"]["gpu_mode"] = "true"
    cfg_dict["IterationEngine"]["gpu_native_ga"] = "true"
    if ga_depth is not None and int(ga_depth) > 0:
        cfg_dict["IterationEngine"]["ga_searchdepth"] = str(int(ga_depth))

    if disable_fg:
        cfg_dict["IterationEngine"]["forcegreatsmode"] = "false"
        cfg_dict["IterationEngine"]["forcegreatsfinder"] = "false"

    # Force the current experiment focus.
    cfg_dict["HumanHitSim"]["enabled"] = "true"
    cfg_dict["HumanHitSim"]["applyto"] = "ALL"
    cfg_dict["HumanHitSim"]["seed"] = str(int(hitsim_seed))
    cfg_dict["HumanHitSim"]["distribution"] = str(
        cfg_dict["HumanHitSim"].get("distribution", cfg_dict["HumanHitSim"].get("Distribution", "uniform"))
        or "uniform"
    )
    cfg_dict["HumanHitSim"]["greatmode"] = str(
        cfg_dict["HumanHitSim"].get("greatmode", cfg_dict["HumanHitSim"].get("GreatMode", "full")) or "full"
    )
    # Disable post-GA refinement so the experiment measures dimension-sensitive reranking, not an extra seed search.
    cfg_dict["HumanHitSim"]["refineafterga"] = "false"
    cfg_dict["HumanHitSim"]["refinetrials"] = "0"
    cfg_dict["HumanHitSim"]["refineseedbase"] = "0"

    return cfg_dict


def _clear_solver_state() -> None:
    from gear_optimizer.solver.fever_timeline import SONG_TIMELINE_GRIDS
    from gear_optimizer.solver.scoring import FEVER_TIMELINE_CACHE, FG_CACHE, GEM_SOLVER_CACHE
    from gear_optimizer.solver.scoring import stats_scoring

    GEM_SOLVER_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()
    FG_CACHE.clear()
    SONG_TIMELINE_GRIDS.clear()
    stats_scoring._FG_BASELINE_CACHE.clear()
    stats_scoring._FG_BASELINE_GRID_CACHE.clear()

    try:
        from gear_optimizer.solver.taichi_gem.api.timeline import reset_timeline_state

        reset_timeline_state()
    except Exception:
        pass


def _run_full_ga_task(
    *,
    fp: str,
    song_key: str,
    difficulty: str,
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    ga_seed: int,
) -> dict:
    from gear_optimizer.pipeline.song_processor import process_song_task

    _clear_solver_state()
    repeat_ctx = {"repeat_index": 1, "repeat_total": 1, "ga_seed": int(ga_seed)}
    args = (
        fp,
        song_key,
        difficulty,
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        False,  # use_evo_db
        True,  # auto_buff
        _safe_int((cfg_dict.get("IterationEngine") or {}).get("ga_searchdepth", 0), 0),
        None,  # status_queue
        1,  # parallel_workers
        False,  # fg_debug
        repeat_ctx,
        True,  # defer_post
    )
    with redirect_stdout(StringIO()):
        return process_song_task(args)


def _dedupe_ranked_loadouts(rows: list[dict]) -> list[dict]:
    by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], dict] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        gear_names = [str(x or "") for x in (row.get("Gear") or row.get("gear") or [])]
        mini_names = [str(x or "") for x in (row.get("Minis") or row.get("minis") or [])]
        if not gear_names and not mini_names:
            continue
        key = _candidate_key(gear_names, mini_names)
        score = _safe_int(row.get("BaseScore", row.get("score", row.get("Score", 0))), 0)
        prev = by_key.get(key)
        if prev is None or _safe_int(prev.get("BaseScore", prev.get("score", prev.get("Score", 0))), 0) < score:
            by_key[key] = {
                "key": key,
                "label": _key_to_label(key),
                "Gear": gear_names,
                "Minis": mini_names,
                "BaseScore": int(score),
            }
    return sorted(by_key.values(), key=lambda r: (int(r["BaseScore"]), r["label"]), reverse=True)


def _rank_loadouts(rows: list[dict], *, limit: int) -> list[dict]:
    ranked = _dedupe_ranked_loadouts(rows)
    return ranked[: max(1, int(limit))]


def _build_target_context(
    *,
    fp: str,
    cfg_dict: dict,
    paths: dict,
    gears_by_name: dict,
    minis_by_name: dict,
):
    from gear_optimizer.core.utils import cfg_from_dict
    from gear_optimizer.helpers.song_helpers import setup_song_config
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.hit_simulation import apply_human_hit_sim

    base_calc_song = get_base_calc_song(fp, cfg_dict)
    calc_song = clone_calc_song(base_calc_song)
    apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
    cfg = cfg_from_dict(cfg_dict)
    (
        _ga_settings,
        fixed_stats,
        _current_gear_stats,
        _current_gear_list,
        _current_mini_stats,
        _current_mini_list,
        _meta_finder,
        _enable_fever,
        _enable_mini,
        _enable_gear,
        _force_greats_mode,
        _force_greats_finder,
        _force_greats_config,
        _manual_force_greats,
    ) = setup_song_config(cfg, calc_song, True, paths, gears_by_name, minis_by_name)
    return cfg, calc_song, fixed_stats


def _combine_stats_for_loadout(
    *,
    fixed_stats: dict,
    gear_names: list[str],
    mini_names: list[str],
    gears_by_name: dict,
    minis_by_name: dict,
) -> dict:
    from gear_optimizer.core.constants import SKIP_ITEM_KEYS

    merged = dict(fixed_stats or {})

    def _apply_item(item: dict) -> None:
        for k, v in item.items():
            if k in SKIP_ITEM_KEYS:
                continue
            if not isinstance(v, (int, float)):
                continue
            merged[k] = merged.get(k, 0) + v

    for name in gear_names or []:
        item = gears_by_name.get(str(name or ""))
        if isinstance(item, dict):
            _apply_item(item)
    for name in mini_names or []:
        item = minis_by_name.get(str(name or ""))
        if isinstance(item, dict):
            _apply_item(item)
    return merged


def _rerank_source_pool_on_target(
    *,
    source_pool: list[dict],
    fp: str,
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    gears_by_name: dict,
    minis_by_name: dict,
    topk: int,
) -> list[dict]:
    from gear_optimizer.solver.scoring import solve_best_fever_combination

    _clear_solver_state()
    with redirect_stdout(StringIO()):
        cfg, calc_song, fixed_stats = _build_target_context(
            fp=fp,
            cfg_dict=cfg_dict,
            paths=paths,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
        )

        reranked: list[dict] = []
        for cand in source_pool or []:
            if not isinstance(cand, dict):
                continue
            gear_names = [str(x or "") for x in (cand.get("Gear") or [])]
            mini_names = [str(x or "") for x in (cand.get("Minis") or [])]
            combined_stats = _combine_stats_for_loadout(
                fixed_stats=fixed_stats,
                gear_names=gear_names,
                mini_names=mini_names,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
            )
            best_data = solve_best_fever_combination(
                cfg,
                combined_stats,
                calc_song,
                ref_arrays,
                silent=True,
            )
            score = _safe_int((best_data or {}).get("BaseScore", (best_data or {}).get("Score", 0)), 0)
            key = _candidate_key(gear_names, mini_names)
            reranked.append(
                {
                    "key": key,
                    "label": _key_to_label(key),
                    "Gear": gear_names,
                    "Minis": mini_names,
                    "BaseScore": int(score),
                }
            )
    return _rank_loadouts(reranked, limit=topk)


def _compare_rankings(source_ranked: list[dict], target_ranked: list[dict], *, topk: int) -> dict:
    compare_k = max(1, int(topk))
    src_keys_full = [tuple(r["key"]) for r in source_ranked or []]
    tgt_keys_full = [tuple(r["key"]) for r in target_ranked or []]
    src_keys = src_keys_full[:compare_k]
    tgt_keys = tgt_keys_full[:compare_k]
    src_set = set(src_keys)
    tgt_set = set(tgt_keys)
    overlap = src_set & tgt_set

    target_top1_key = tgt_keys_full[0] if tgt_keys_full else None
    source_top1_key = src_keys_full[0] if src_keys_full else None
    target_best_rank = None
    if target_top1_key is not None:
        try:
            target_best_rank = 1 + src_keys_full.index(target_top1_key)
        except ValueError:
            target_best_rank = None

    target_best_score = int(target_ranked[0]["BaseScore"]) if target_ranked else 0
    source_best_score = int(source_ranked[0]["BaseScore"]) if source_ranked else 0
    denom = max(1, len(tgt_keys))
    return {
        "top1_match": bool(target_top1_key is not None and source_top1_key == target_top1_key),
        "topk_overlap": int(len(overlap)),
        "topk_recall": float(len(overlap)) / float(denom),
        "target_top1_recovered": bool(target_top1_key in set(src_keys_full)) if target_top1_key is not None else False,
        "target_top1_rank_in_rerank": target_best_rank,
        "source_best_score": int(source_best_score),
        "target_best_score": int(target_best_score),
        "best_score_gap": int(target_best_score - source_best_score),
        "source_beats_reference": bool(source_best_score > target_best_score),
        "exact_set_match": bool(len(src_keys) == len(tgt_keys) and src_set == tgt_set),
        "exact_order_match": bool(src_keys == tgt_keys and len(src_keys) == len(tgt_keys)),
        "compare_k_effective": int(denom),
        "source_top1": source_ranked[0]["label"] if source_ranked else "",
        "target_top1": target_ranked[0]["label"] if target_ranked else "",
    }


def _pair_brief(row: dict | None) -> dict:
    if not isinstance(row, dict):
        return {}
    return {
        "source_seed": int(row.get("source_seed") or 0),
        "target_seed": int(row.get("target_seed") or 0),
        "top1_match": bool(row.get("top1_match")),
        "topk_recall": _round6(float(row.get("topk_recall") or 0.0)),
        "topk_overlap": int(row.get("topk_overlap") or 0),
        "compare_k_effective": int(row.get("compare_k_effective") or 0),
        "best_score_gap": int(row.get("best_score_gap") or 0),
        "target_top1_rank_in_rerank": row.get("target_top1_rank_in_rerank"),
        "source_top1": str(row.get("source_top1") or ""),
        "target_top1": str(row.get("target_top1") or ""),
    }


def _summarize_rows(rows: list[dict]) -> dict:
    if not rows:
        return {
            "pairs": 0,
            "top1_match_rate": 0.0,
            "target_top1_recovered_rate": 0.0,
            "exact_set_match_rate": 0.0,
            "exact_order_match_rate": 0.0,
            "source_beats_reference_rate": 0.0,
            "topk_recall_mean": 0.0,
            "topk_recall_min": 0.0,
            "best_score_gap_mean": 0.0,
            "best_score_gap_min": 0,
            "best_score_gap_max": 0,
            "worst_recall_pair": {},
            "worst_gap_pair": {},
            "best_negative_gap_pair": {},
        }

    worst_recall_pair = min(rows, key=lambda r: (float(r.get("topk_recall") or 0.0), -int(r.get("best_score_gap") or 0)))
    worst_gap_pair = max(rows, key=lambda r: (int(r.get("best_score_gap") or 0), -float(r.get("topk_recall") or 0.0)))
    negative_gap_rows = [r for r in rows if int(r.get("best_score_gap") or 0) < 0]
    best_negative_gap_pair = min(negative_gap_rows, key=lambda r: int(r.get("best_score_gap") or 0)) if negative_gap_rows else None

    recalls = [float(r.get("topk_recall") or 0.0) for r in rows]
    gaps = [int(r.get("best_score_gap") or 0) for r in rows]
    return {
        "pairs": int(len(rows)),
        "top1_match_rate": _round6(_mean([1.0 if bool(r.get("top1_match")) else 0.0 for r in rows])),
        "target_top1_recovered_rate": _round6(
            _mean([1.0 if bool(r.get("target_top1_recovered")) else 0.0 for r in rows])
        ),
        "exact_set_match_rate": _round6(_mean([1.0 if bool(r.get("exact_set_match")) else 0.0 for r in rows])),
        "exact_order_match_rate": _round6(_mean([1.0 if bool(r.get("exact_order_match")) else 0.0 for r in rows])),
        "source_beats_reference_rate": _round6(
            _mean([1.0 if bool(r.get("source_beats_reference")) else 0.0 for r in rows])
        ),
        "topk_recall_mean": _round6(_mean(recalls)),
        "topk_recall_min": _round6(min(recalls)),
        "best_score_gap_mean": _round6(_mean([float(x) for x in gaps])),
        "best_score_gap_min": int(min(gaps)),
        "best_score_gap_max": int(max(gaps)),
        "worst_recall_pair": _pair_brief(worst_recall_pair),
        "worst_gap_pair": _pair_brief(worst_gap_pair),
        "best_negative_gap_pair": _pair_brief(best_negative_gap_pair),
    }


def _build_summary(matrix: list[dict], *, hitsim_seeds: list[int]) -> dict:
    same_seed_rows = [row for row in matrix if int(row.get("source_seed") or 0) == int(row.get("target_seed") or 0)]
    cross_seed_rows = [row for row in matrix if int(row.get("source_seed") or 0) != int(row.get("target_seed") or 0)]
    return {
        "all_pairs": _summarize_rows(matrix),
        "same_seed_pairs": _summarize_rows(same_seed_rows),
        "cross_seed_pairs": _summarize_rows(cross_seed_rows),
        "by_source_seed": {
            str(seed): _summarize_rows([row for row in cross_seed_rows if int(row.get("source_seed") or 0) == int(seed)])
            for seed in hitsim_seeds
        },
        "by_target_seed": {
            str(seed): _summarize_rows([row for row in cross_seed_rows if int(row.get("target_seed") or 0) == int(seed)])
            for seed in hitsim_seeds
        },
    }


def _merge_run_candidate_groups(run_candidate_groups: list[list[dict]], *, run_count: int) -> list[dict]:
    max_runs = max(0, min(int(run_count), len(run_candidate_groups or [])))
    merged: list[dict] = []
    for rows in list(run_candidate_groups or [])[:max_runs]:
        for row in rows or []:
            if isinstance(row, dict):
                merged.append(row)
    return _dedupe_ranked_loadouts(merged)


def _build_seed_subset_pool(
    *,
    run_candidate_groups: list[list[dict]],
    fp: str,
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    gears_by_name: dict,
    minis_by_name: dict,
    run_count: int,
    pool_limit: int,
) -> list[dict]:
    merged_candidates = _merge_run_candidate_groups(run_candidate_groups, run_count=run_count)
    if not merged_candidates:
        return []
    ranked = _rerank_source_pool_on_target(
        source_pool=merged_candidates,
        fp=fp,
        cfg_dict=cfg_dict,
        paths=paths,
        ref_arrays=ref_arrays,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        topk=max(1, len(merged_candidates)),
    )
    return list(ranked[: max(1, int(pool_limit))])


def _build_hybrid_sweeps(
    *,
    full_runs: dict[int, dict],
    hitsim_seeds: list[int],
    anchor_seed: int,
    shared_run_counts: list[int],
    local_run_counts: list[int],
    fp: str,
    paths: dict,
    ref_arrays: dict,
    gears_by_name: dict,
    minis_by_name: dict,
    pool_limit: int,
    topk: int,
    total_reference_ga_runs: int,
) -> dict:
    subset_pool_cache: dict[tuple[int, int, int], list[dict]] = {}

    def _subset_pool(seed: int, run_count: int, limit: int) -> list[dict]:
        clipped = max(0, min(int(run_count), len((full_runs[int(seed)] or {}).get("ga_run_candidates") or [])))
        cache_key = (int(seed), int(clipped), int(limit))
        cached = subset_pool_cache.get(cache_key)
        if cached is not None:
            return list(cached)
        if clipped <= 0:
            subset_pool_cache[cache_key] = []
            return []
        pool = _build_seed_subset_pool(
            run_candidate_groups=list((full_runs[int(seed)] or {}).get("ga_run_candidates") or []),
            fp=fp,
            cfg_dict=dict((full_runs[int(seed)] or {}).get("cfg_dict") or {}),
            paths=paths,
            ref_arrays=ref_arrays,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            run_count=clipped,
            pool_limit=limit,
        )
        subset_pool_cache[cache_key] = list(pool)
        return list(pool)

    sweeps: list[dict] = []
    non_anchor_dims = max(0, len(hitsim_seeds) - 1)
    max_runs_per_seed = len((full_runs[int(anchor_seed)] or {}).get("ga_run_candidates") or [])

    for shared_runs_raw in shared_run_counts:
        shared_runs = max(1, min(int(shared_runs_raw), int(max_runs_per_seed)))
        shared_pool = _subset_pool(int(anchor_seed), shared_runs, int(pool_limit))
        for local_runs_raw in local_run_counts:
            local_runs = max(0, min(int(local_runs_raw), int(max_runs_per_seed)))
            rows: list[dict] = []
            for target_seed in hitsim_seeds:
                target_seed_i = int(target_seed)
                target_cfg = dict((full_runs[target_seed_i] or {}).get("cfg_dict") or {})
                target_reference_ranked = list((full_runs[target_seed_i] or {}).get("reference_ranked") or [])
                local_pool: list[dict] = []
                local_runs_used = 0
                if target_seed_i != int(anchor_seed) and local_runs > 0:
                    local_runs_used = int(local_runs)
                    local_pool = _subset_pool(target_seed_i, local_runs_used, int(pool_limit))
                local_only_ranked: list[dict] = []
                local_only_metrics = None
                if target_seed_i != int(anchor_seed) and local_pool:
                    local_only_ranked = _rerank_source_pool_on_target(
                        source_pool=local_pool,
                        fp=fp,
                        cfg_dict=target_cfg,
                        paths=paths,
                        ref_arrays=ref_arrays,
                        gears_by_name=gears_by_name,
                        minis_by_name=minis_by_name,
                        topk=max(1, len(local_pool)),
                    )
                    local_only_metrics = _compare_rankings(local_only_ranked, target_reference_ranked, topk=topk)
                hybrid_source_pool = _dedupe_ranked_loadouts(list(shared_pool) + list(local_pool))
                reranked_ranked = _rerank_source_pool_on_target(
                    source_pool=hybrid_source_pool,
                    fp=fp,
                    cfg_dict=target_cfg,
                    paths=paths,
                    ref_arrays=ref_arrays,
                    gears_by_name=gears_by_name,
                    minis_by_name=minis_by_name,
                    topk=max(1, len(hybrid_source_pool)),
                )
                metrics = _compare_rankings(reranked_ranked, target_reference_ranked, topk=topk)
                row = {
                    "anchor_seed": int(anchor_seed),
                    "shared_runs": int(shared_runs),
                    "local_runs_requested": int(local_runs_raw),
                    "local_runs_used": int(local_runs_used),
                    "target_seed": int(target_seed_i),
                    "is_anchor_target": bool(target_seed_i == int(anchor_seed)),
                    "shared_pool_n": len(shared_pool),
                    "local_pool_n": len(local_pool),
                    "local_only_pool_n": len(local_pool),
                    "hybrid_source_pool_n": len(hybrid_source_pool),
                    "target_reference_ranked_n": len(target_reference_ranked),
                }
                row.update(metrics)
                if isinstance(local_only_metrics, dict):
                    row["local_only_top1_match"] = bool(local_only_metrics.get("top1_match"))
                    row["local_only_topk_recall"] = float(local_only_metrics.get("topk_recall") or 0.0)
                    row["local_only_topk_overlap"] = int(local_only_metrics.get("topk_overlap") or 0)
                    row["local_only_target_top1_recovered"] = bool(local_only_metrics.get("target_top1_recovered"))
                    row["local_only_target_top1_rank_in_rerank"] = local_only_metrics.get("target_top1_rank_in_rerank")
                    row["local_only_best_score"] = int(local_only_metrics.get("source_best_score") or 0)
                    row["hybrid_minus_local_only_best_score"] = int(row["source_best_score"]) - int(
                        local_only_metrics.get("source_best_score") or 0
                    )
                    row["hybrid_minus_local_only_recall"] = _round6(
                        float(row.get("topk_recall") or 0.0) - float(local_only_metrics.get("topk_recall") or 0.0)
                    )
                else:
                    row["local_only_top1_match"] = None
                    row["local_only_topk_recall"] = None
                    row["local_only_topk_overlap"] = None
                    row["local_only_target_top1_recovered"] = None
                    row["local_only_target_top1_rank_in_rerank"] = None
                    row["local_only_best_score"] = None
                    row["hybrid_minus_local_only_best_score"] = None
                    row["hybrid_minus_local_only_recall"] = None
                rows.append(row)

            non_anchor_rows = [row for row in rows if not bool(row.get("is_anchor_target"))]
            hybrid_total_ga_runs = int(shared_runs) + int(local_runs) * int(non_anchor_dims)
            sweeps.append(
                {
                    "anchor_seed": int(anchor_seed),
                    "shared_runs": int(shared_runs),
                    "local_runs": int(local_runs),
                    "shared_pool_n": len(shared_pool),
                    "hybrid_total_ga_runs": int(hybrid_total_ga_runs),
                    "full_reference_ga_runs": int(total_reference_ga_runs),
                    "ga_run_ratio_vs_full_reference": _round6(
                        float(hybrid_total_ga_runs) / float(max(1, int(total_reference_ga_runs)))
                    ),
                    "ga_run_savings_vs_full_reference": _round6(
                        1.0 - (float(hybrid_total_ga_runs) / float(max(1, int(total_reference_ga_runs))))
                    ),
                    "summary_all_targets": _summarize_rows(rows),
                    "summary_non_anchor_targets": _summarize_rows(non_anchor_rows),
                    "rows": rows,
                }
            )

    return {
        "anchor_seed": int(anchor_seed),
        "shared_run_counts": [int(x) for x in shared_run_counts],
        "local_run_counts": [int(x) for x in local_run_counts],
        "pool_limit": int(pool_limit),
        "sweeps": sweeps,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compare stronger per-dimension GA references against reusing one dimension's GA pool on another HitSim seed."
    )
    ap.add_argument("--song", default="Aether")
    ap.add_argument("--artist", default="Geoxor")
    ap.add_argument("--difficulty", default="Hard", choices=["Easy", "Normal", "Hard"])
    ap.add_argument("--config", default="config.ini")
    ap.add_argument(
        "--hitsim-seeds",
        default="11111,22222,33333",
        help="Comma-separated HitSim seeds used as current proxy dimensions.",
    )
    ap.add_argument(
        "--ga-seed-base",
        "--ga-seed",
        dest="ga_seed_base",
        type=int,
        default=1337,
        help="Base GA seed when generating multiple GA runs per HitSim dimension.",
    )
    ap.add_argument(
        "--ga-seeds",
        default="",
        help="Optional explicit GA seeds for the reference union (overrides --ga-seed-base/--ga-runs).",
    )
    ap.add_argument(
        "--ga-runs",
        type=int,
        default=4,
        help="Number of GA seeds to union per HitSim dimension when --ga-seeds is not provided.",
    )
    ap.add_argument("--ga-depth", type=int, default=0, help="Optional GA_SearchDepth override (0 = keep config).")
    ap.add_argument(
        "--candidate-limit",
        type=int,
        default=256,
        help="Per-run GA candidate funnel retained before unioning multiple GA runs into one dimension reference.",
    )
    ap.add_argument(
        "--pool-limit",
        type=int,
        default=128,
        help="Size of the reusable witness pool kept from each dimension after self-reranking.",
    )
    ap.add_argument("--topk", type=int, default=51, help="Top-K loadouts compared for recall/overlap.")
    ap.add_argument(
        "--disable-fg",
        action="store_true",
        help="Disable ForceGreats to focus the experiment on base-score loadout stability under ApplyTo=ALL.",
    )
    ap.add_argument(
        "--out",
        default=str(Path("artifacts") / "bench" / "hitsim_shared_pool_recall.json"),
    )
    ap.add_argument(
        "--hybrid-anchor-seed",
        type=int,
        default=None,
        help="Optional anchor HitSim seed used as the shared scout pool for hybrid sweeps (default: first hitsim seed).",
    )
    ap.add_argument(
        "--hybrid-anchor-seeds",
        default="",
        help="Optional comma-separated anchor HitSim seeds. When set, hybrid sweeps are computed for each anchor against the same full reference runs.",
    )
    ap.add_argument(
        "--hybrid-shared-runs",
        default="",
        help="Optional comma-separated counts of anchor GA runs used for the shared scout pool.",
    )
    ap.add_argument(
        "--hybrid-local-runs",
        default="",
        help="Optional comma-separated counts of target-local GA runs added on top of the shared scout pool.",
    )
    args = ap.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 2

    hitsim_seeds = [int(x.strip()) for x in str(args.hitsim_seeds or "").split(",") if str(x).strip()]
    if len(hitsim_seeds) < 2:
        raise SystemExit("Provide at least two HitSim seeds for a source-vs-target experiment.")
    ga_seeds = _resolve_ga_seeds(args)
    if not ga_seeds:
        raise SystemExit("Provide at least one GA seed for the reference search.")
    hybrid_shared_runs = _parse_int_csv(args.hybrid_shared_runs)
    hybrid_local_runs = _parse_int_csv(args.hybrid_local_runs)

    candidate_limit = max(1, int(args.candidate_limit))
    pool_limit = max(1, int(args.pool_limit))
    topk = max(1, int(args.topk))
    if pool_limit < topk:
        raise SystemExit("--pool-limit must be >= --topk so the shared pool can, in principle, recover the requested top-K.")
    if candidate_limit < topk:
        raise SystemExit(
            "--candidate-limit must be >= --topk so each reference GA run can contribute at least the requested top-K."
        )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name = _load_runtime_inputs()
    base_cfg_dict = _load_cfg_dict(config_path)
    song_keys = _get_song_keys(str(args.song), str(args.artist))
    song_key = song_keys[str(args.difficulty)]
    fp = _resolve_song_file(paths, str(args.difficulty), song_key)
    hybrid_anchor_seed = int(args.hybrid_anchor_seed) if args.hybrid_anchor_seed is not None else int(hitsim_seeds[0])
    if hybrid_anchor_seed not in set(hitsim_seeds):
        raise SystemExit("--hybrid-anchor-seed must be one of --hitsim-seeds.")
    hybrid_anchor_seeds = _parse_int_csv(args.hybrid_anchor_seeds)
    if hybrid_anchor_seeds:
        invalid_anchors = [seed for seed in hybrid_anchor_seeds if seed not in set(hitsim_seeds)]
        if invalid_anchors:
            raise SystemExit("--hybrid-anchor-seeds must all be present in --hitsim-seeds.")
    else:
        hybrid_anchor_seeds = [int(hybrid_anchor_seed)]

    full_runs: dict[int, dict] = {}
    t0 = time.perf_counter()
    print(
        "[Experiment] Running stronger per-dimension references: "
        f"song={song_key}, difficulty={args.difficulty}, hitsim_seeds={hitsim_seeds}, "
        f"ga_seeds={ga_seeds}, candidate_limit={candidate_limit}, pool_limit={pool_limit}"
    )
    for seed in hitsim_seeds:
        cfg_dict = _prepare_cfg_dict(
            base_cfg_dict,
            hitsim_seed=int(seed),
            ga_depth=int(args.ga_depth) if int(args.ga_depth) > 0 else None,
            candidate_limit=candidate_limit,
            disable_fg=bool(args.disable_fg),
        )
        run_details: list[dict] = []
        ga_run_candidates: list[list[dict]] = []
        merged_candidates: list[dict] = []
        for ga_seed in ga_seeds:
            result = _run_full_ga_task(
                fp=fp,
                song_key=song_key,
                difficulty=str(args.difficulty),
                cfg_dict=cfg_dict,
                paths=paths,
                ref_arrays=ref_arrays,
                all_gears=all_gears,
                all_minis=all_minis,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
                ga_seed=int(ga_seed),
            )
            ga_candidates = list(result.get("ga_candidates") or [])
            ga_run_candidates.append(list(ga_candidates))
            merged_candidates.extend(ga_candidates)
            run_details.append(
                {
                    "ga_seed": int(ga_seed),
                    "candidate_count": len(ga_candidates),
                    "best_data_base_score": _safe_int((result.get("best_data") or {}).get("BaseScore", 0), 0),
                }
            )
            print(
                f"[Experiment] HitSim={int(seed)} GA={int(ga_seed)} "
                f"candidates={len(ga_candidates)} best={run_details[-1]['best_data_base_score']}"
            )

        union_candidates = _dedupe_ranked_loadouts(merged_candidates)
        reference_ranked = _rerank_source_pool_on_target(
            source_pool=union_candidates,
            fp=fp,
            cfg_dict=cfg_dict,
            paths=paths,
            ref_arrays=ref_arrays,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            topk=max(1, len(union_candidates)),
        )
        baseline_topk = list(reference_ranked[: max(1, int(topk))])
        source_pool = list(reference_ranked[: max(1, int(pool_limit))])
        full_runs[int(seed)] = {
            "cfg_dict": cfg_dict,
            "ga_runs": run_details,
            "ga_run_candidates": ga_run_candidates,
            "reference_ranked": reference_ranked,
            "baseline_topk": baseline_topk,
            "source_pool": source_pool,
            "candidate_count_total": sum(int(run["candidate_count"]) for run in run_details),
            "union_candidate_count": len(union_candidates),
        }
        print(
            f"[Experiment] HitSim={int(seed)} union_candidates={len(union_candidates)} "
            f"pool={len(source_pool)} baseline_topk={len(baseline_topk)}"
        )

    matrix: list[dict] = []
    for source_seed in hitsim_seeds:
        source_pool = list((full_runs[int(source_seed)] or {}).get("source_pool") or [])
        for target_seed in hitsim_seeds:
            target_cfg = dict((full_runs[int(target_seed)] or {}).get("cfg_dict") or {})
            reranked_ranked = _rerank_source_pool_on_target(
                source_pool=source_pool,
                fp=fp,
                cfg_dict=target_cfg,
                paths=paths,
                ref_arrays=ref_arrays,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
                topk=max(1, len(source_pool)),
            )
            reference_ranked = list((full_runs[int(target_seed)] or {}).get("reference_ranked") or [])
            metrics = _compare_rankings(reranked_ranked, reference_ranked, topk=topk)
            row = {
                "source_seed": int(source_seed),
                "target_seed": int(target_seed),
                "source_pool_n": len(source_pool),
                "source_ranked_n": len(reranked_ranked),
                "target_reference_candidate_n": int((full_runs[int(target_seed)] or {}).get("union_candidate_count") or 0),
                "target_reference_ranked_n": len(reference_ranked),
                "baseline_topk_n": min(topk, len(reference_ranked)),
            }
            row.update(metrics)
            matrix.append(row)
            print(
                "[Matrix] "
                f"src={int(source_seed)} -> tgt={int(target_seed)} "
                f"top1_match={row['top1_match']} overlap={row['topk_overlap']}/{max(1, row['baseline_topk_n'])} "
                f"gap={row['best_score_gap']}"
            )

    elapsed = time.perf_counter() - t0
    summary = _build_summary(matrix, hitsim_seeds=hitsim_seeds)
    hybrid = None
    hybrid_by_anchor = None
    if hybrid_shared_runs and hybrid_local_runs:
        hybrid_payloads = {
            str(anchor_seed): _build_hybrid_sweeps(
                full_runs=full_runs,
                hitsim_seeds=hitsim_seeds,
                anchor_seed=int(anchor_seed),
                shared_run_counts=hybrid_shared_runs,
                local_run_counts=hybrid_local_runs,
                fp=fp,
                paths=paths,
                ref_arrays=ref_arrays,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
                pool_limit=pool_limit,
                topk=topk,
                total_reference_ga_runs=len(hitsim_seeds) * len(ga_seeds),
            )
            for anchor_seed in hybrid_anchor_seeds
        }
        hybrid = hybrid_payloads.get(str(int(hybrid_anchor_seed)))
        hybrid_by_anchor = hybrid_payloads if len(hybrid_payloads) > 1 else None
    payload = {
        "song": str(args.song),
        "artist": str(args.artist),
        "song_key": song_key,
        "difficulty": str(args.difficulty),
        "config": str(config_path),
        "hitsim_apply_to": "ALL",
        "hitsim_seeds": [int(x) for x in hitsim_seeds],
        "ga_seeds": [int(x) for x in ga_seeds],
        "ga_depth_override": int(args.ga_depth),
        "candidate_limit": int(candidate_limit),
        "pool_limit": int(pool_limit),
        "topk": int(topk),
        "disable_fg": bool(args.disable_fg),
        "solver_state_cleared_between_runs": True,
        "elapsed_sec": float(elapsed),
        "full_runs": {
            str(seed): {
                "candidate_count_total": int(full_runs[int(seed)]["candidate_count_total"]),
                "union_candidate_count": int(full_runs[int(seed)]["union_candidate_count"]),
                "baseline_top1": (
                    full_runs[int(seed)]["baseline_topk"][0]["label"] if full_runs[int(seed)]["baseline_topk"] else ""
                ),
                "baseline_top1_score": (
                    int(full_runs[int(seed)]["baseline_topk"][0]["BaseScore"])
                    if full_runs[int(seed)]["baseline_topk"]
                    else 0
                ),
                "source_pool_n": len(full_runs[int(seed)]["source_pool"]),
                "ga_runs": list(full_runs[int(seed)]["ga_runs"]),
            }
            for seed in hitsim_seeds
        },
        "summary": summary,
        "hybrid": hybrid,
        "hybrid_by_anchor": hybrid_by_anchor,
        "matrix": matrix,
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[Experiment] Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
