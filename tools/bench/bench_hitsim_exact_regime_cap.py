from __future__ import annotations

import argparse
import copy
import json
import sqlite3
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.bench.bench_hitsim_shared_pool_recall import (  # noqa: E402
    _clear_solver_state,
    _build_target_context,
    _combine_stats_for_loadout,
    _load_cfg_dict,
    _load_runtime_inputs,
    _prepare_cfg_dict,
    _run_full_ga_task,
    _safe_int,
)


def _compact_item_names(rows: list) -> list[str]:
    out: list[str] = []
    for row in rows or []:
        if isinstance(row, dict):
            out.append(str(row.get("Name", "") or ""))
        else:
            out.append(str(row or ""))
    return out


def _needs_stat_hydration(payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return True
    stats = payload.get("Stats")
    return not isinstance(stats, dict) or not stats


def _hydrate_refine_payloads_if_needed(
    *,
    base_result: dict,
    paths: dict,
    ref_arrays: dict,
    gears_by_name: dict,
    minis_by_name: dict,
) -> tuple[dict, list[dict]]:
    from gear_optimizer.solver.scoring import solve_best_fever_combination

    best_data = copy.deepcopy(base_result.get("best_data") or {})
    ga_candidates = copy.deepcopy(base_result.get("ga_candidates") or [])

    need_hydrate_best = _needs_stat_hydration(best_data)
    need_hydrate_candidates = any(_needs_stat_hydration((cand.get("Data") if isinstance(cand, dict) else None) or {}) for cand in ga_candidates)
    if not need_hydrate_best and not need_hydrate_candidates:
        return best_data, ga_candidates

    _clear_solver_state()
    cfg, calc_song, fixed_stats = _build_target_context(
        fp=str(base_result.get("file_path") or ""),
        cfg_dict=dict(base_result.get("cfg_dict") or {}),
        paths=paths,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
    )

    def _hydrate_row(gear_names: list[str], mini_names: list[str]) -> dict:
        combined_stats = _combine_stats_for_loadout(
            fixed_stats=fixed_stats,
            gear_names=gear_names,
            mini_names=mini_names,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
        )
        return solve_best_fever_combination(
            cfg,
            combined_stats,
            calc_song,
            ref_arrays,
            silent=True,
        )

    if need_hydrate_best:
        best_gear = _compact_item_names(base_result.get("best_gear") or [])
        best_minis = _compact_item_names(base_result.get("best_minis") or [])
        hydrated = _hydrate_row(best_gear, best_minis)
        if isinstance(hydrated, dict) and hydrated:
            best_data = hydrated

    for cand in ga_candidates:
        if not isinstance(cand, dict):
            continue
        data = cand.get("Data")
        if not _needs_stat_hydration(data if isinstance(data, dict) else {}):
            continue
        gear_names = _compact_item_names(cand.get("Gear") or [])
        mini_names = _compact_item_names(cand.get("Minis") or [])
        hydrated = _hydrate_row(gear_names, mini_names)
        if isinstance(hydrated, dict) and hydrated:
            cand["Data"] = hydrated

    return best_data, ga_candidates


def _resolve_song_file_by_name(paths: dict, song_name: str, *, preferred_difficulty: str = "") -> tuple[str, str]:
    data_dir = Path(paths.get("Data", "Data") or "Data")
    difficulty_dirs = [diff_dir for diff_dir in sorted(data_dir.iterdir()) if diff_dir.is_dir()]
    preferred = str(preferred_difficulty or "").strip()
    if preferred:
        difficulty_dirs.sort(key=lambda diff_dir: (diff_dir.name != preferred, diff_dir.name))
    for diff_dir in difficulty_dirs:
        if not diff_dir.is_dir():
            continue
        fp = diff_dir / f"{song_name}.txt"
        if fp.exists():
            return str(fp), str(diff_dir.name)
    raise FileNotFoundError(f"Song file not found for DB entry: {song_name}")


def _pick_high_attempt_song(db_path: Path, paths: dict, *, difficulty: str = "Hard", limit: int = 50) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT name, attempt_lifetime, attempts_first, best_score "
            "FROM songs ORDER BY attempt_lifetime DESC LIMIT ?",
            (int(limit),),
        ).fetchall()

    for name, attempt_lifetime, attempts_first, best_score in rows:
        if difficulty and f"({difficulty})" not in str(name):
            continue
        try:
            fp, song_difficulty = _resolve_song_file_by_name(paths, str(name), preferred_difficulty=difficulty)
        except FileNotFoundError:
            continue
        return {
            "name": str(name),
            "file_path": str(fp),
            "difficulty": str(song_difficulty),
            "attempt_lifetime": int(attempt_lifetime or 0),
            "attempts_first": int(attempts_first or 0),
            "db_best_score": int(best_score or 0),
        }
    raise RuntimeError("No high-attempt DB song with a local chart file was found")


def _build_base_ga_result(
    *,
    fp: str,
    song_name: str,
    difficulty: str,
    base_cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    ga_seed: int,
    ga_depth: int,
    candidate_limit: int,
    disable_fg: bool,
    hitsim_seed: int,
    refine_candidate_limit: int,
) -> dict:
    cfg_dict = _prepare_cfg_dict(
        base_cfg_dict,
        hitsim_seed=hitsim_seed,
        ga_depth=ga_depth,
        candidate_limit=candidate_limit,
        disable_fg=disable_fg,
    )
    cfg_dict.setdefault("HumanHitSim", {})
    cfg_dict["HumanHitSim"]["enabled"] = "true"
    cfg_dict["HumanHitSim"]["applyto"] = "ALL"
    cfg_dict["HumanHitSim"]["seed"] = str(int(hitsim_seed))
    cfg_dict["HumanHitSim"]["refineafterga"] = "false"
    cfg_dict["HumanHitSim"]["refinemode"] = "exact"
    cfg_dict["HumanHitSim"]["refinetrials"] = "0"
    cfg_dict["HumanHitSim"]["refinecandidatelimit"] = str(int(refine_candidate_limit))

    t0 = time.perf_counter()
    result = _run_full_ga_task(
        fp=fp,
        song_key=song_name,
        difficulty=difficulty,
        cfg_dict=cfg_dict,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        ga_seed=ga_seed,
    )
    elapsed = time.perf_counter() - t0
    result["_base_ga_elapsed_sec"] = round(float(elapsed), 6)
    return result


def _load_variant(
    *,
    label: str,
    base_result: dict,
    paths: dict,
    ref_arrays: dict,
    gears_by_name: dict,
    minis_by_name: dict,
    hitsim_seed: int,
    refine_candidate_limit: int,
    regime_cap: int,
    regime_selection: str,
) -> dict:
    from gear_optimizer.solver.hit_simulation import refine_human_hit_sim_after_ga

    _clear_solver_state()
    calc_song = copy.deepcopy(base_result.get("calc_song") or {})
    best_data, candidate_pool = _hydrate_refine_payloads_if_needed(
        base_result=base_result,
        paths=paths,
        ref_arrays=ref_arrays,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
    )
    cfg_dict = copy.deepcopy(base_result.get("cfg_dict") or {})
    cfg_dict.setdefault("HumanHitSim", {})
    cfg_dict["HumanHitSim"]["enabled"] = "true"
    cfg_dict["HumanHitSim"]["applyto"] = "ALL"
    cfg_dict["HumanHitSim"]["seed"] = str(int(hitsim_seed))
    cfg_dict["HumanHitSim"]["refineafterga"] = "true"
    cfg_dict["HumanHitSim"]["refinemode"] = "exact"
    cfg_dict["HumanHitSim"]["refinetrials"] = "1"
    cfg_dict["HumanHitSim"]["refinecandidatelimit"] = str(int(refine_candidate_limit))
    cfg_dict["HumanHitSim"]["refinemaxregimes"] = str(int(regime_cap))
    cfg_dict["HumanHitSim"]["refineregimeselection"] = str(regime_selection)

    t0 = time.perf_counter()
    refine_info = refine_human_hit_sim_after_ga(
        calc_song,
        cfg_dict=cfg_dict,
        best_data=best_data,
        ref_arrays=ref_arrays,
        ga_seed=int(base_result.get("_ga_seed") or 0),
        candidate_pool=candidate_pool,
    )
    elapsed = time.perf_counter() - t0

    selected_candidate = (refine_info or {}).get("selected_candidate") or {}
    best_data = (selected_candidate.get("Data") if isinstance(selected_candidate, dict) else None) or best_data
    meta = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
    best_gear = _compact_item_names(selected_candidate.get("Gear") or base_result.get("best_gear") or [])
    best_minis = _compact_item_names(selected_candidate.get("Minis") or base_result.get("best_minis") or [])
    return {
        "label": str(label),
        "elapsed_sec": round(float(elapsed), 6),
        "best_score": int(_safe_int(best_data.get("BaseScore", best_data.get("Score", 0)), 0)),
        "best_gear": best_gear,
        "best_minis": best_minis,
        "best_loadout_label": "gear=" + ",".join(best_gear) + " / minis=" + ",".join(best_minis),
        "exact_regime_count": int(meta.get("HumanHitSimRefineExactRegimeCount", 0) or 0),
        "exact_full_regime_count": int(meta.get("HumanHitSimRefineExactFullRegimeCount", 0) or 0),
        "exact_raw_interval_count": int(meta.get("HumanHitSimRefineExactRawIntervalCount", 0) or 0),
        "exact_regime_cap": int(meta.get("HumanHitSimRefineExactRegimeCap", 0) or 0),
        "exact_regime_selection": str(meta.get("HumanHitSimRefineExactRegimeSelection", "") or ""),
        "boundary_domain_active_params": int(meta.get("HumanHitSimRefineBoundaryDomainActiveParams", 0) or 0),
        "boundary_domain_planner_params": int(meta.get("HumanHitSimRefineBoundaryPlannerParams", 0) or 0),
        "boundary_domain_unique_params": int(meta.get("HumanHitSimRefineBoundaryDomainUniqueParams", 0) or 0),
        "boundary_domain_full_pairs": int(meta.get("HumanHitSimRefineBoundaryDomainFullPairs", 0) or 0),
        "exact_planner_family_mode": str(meta.get("HumanHitSimRefineExactPlannerFamilyMode", "") or ""),
        "regime_id": str(meta.get("HumanHitSimRegimeId", "") or ""),
        "regime_alpha": [
            int(meta.get("HumanHitSimRegimeAlphaNumerator", 0) or 0),
            int(meta.get("HumanHitSimRegimeAlphaDenominator", 1) or 1),
        ],
        "candidate_count": int(meta.get("HumanHitSimRefineCandidateCount", 0) or 0),
        "evaluated_trials": int(meta.get("HumanHitSimRefineEvaluatedTrials", 0) or 0),
        "seed_attempts": int(meta.get("HumanHitSimRefineSeedAttempts", 0) or 0),
        "candidate_changed": bool(meta.get("HumanHitSimRefineCandidateChanged", False)),
        "base_score_before_refine": int(_safe_int((base_result.get("best_data") or {}).get("BaseScore", 0), 0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare full exact HitSim refinement vs capped exact regimes.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config.ini"))
    parser.add_argument(
        "--db",
        default=str(PROJECT_ROOT.parent / "ExternalDatabases" / "evolution.db"),
        help="Evolution DB path used to auto-pick a high-attempt song.",
    )
    parser.add_argument("--song-name", default="", help="Full DB song name/file stem. If omitted, auto-pick.")
    parser.add_argument("--difficulty", default="Hard", help="Preferred difficulty when auto-picking or resolving a name.")
    parser.add_argument("--ga-seed", type=int, default=1337)
    parser.add_argument("--hitsim-seed", type=int, default=11111)
    parser.add_argument("--ga-depth", type=int, default=8)
    parser.add_argument("--candidate-limit", type=int, default=64, help="GA candidate funnel kept in the deferred payload.")
    parser.add_argument("--refine-candidate-limit", type=int, default=8, help="Top GA candidates rechecked in refinement.")
    parser.add_argument("--max-regimes", type=int, default=18)
    parser.add_argument("--selection", default="even", choices=["even", "head"])
    parser.add_argument("--enable-fg", action="store_true", help="Enable ForceGreats during the benchmark.")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    base_cfg_dict = _load_cfg_dict(Path(args.config))
    paths, ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name = _load_runtime_inputs()

    if args.song_name:
        fp, difficulty = _resolve_song_file_by_name(
            paths,
            str(args.song_name),
            preferred_difficulty=str(args.difficulty),
        )
        song_pick = {
            "name": str(args.song_name),
            "file_path": str(fp),
            "difficulty": str(difficulty),
            "attempt_lifetime": 0,
            "attempts_first": 0,
            "db_best_score": 0,
        }
    else:
        song_pick = _pick_high_attempt_song(Path(args.db), paths, difficulty=str(args.difficulty))

    base_result = _build_base_ga_result(
        fp=str(song_pick["file_path"]),
        song_name=str(song_pick["name"]),
        difficulty=str(song_pick["difficulty"]),
        base_cfg_dict=base_cfg_dict,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        ga_seed=int(args.ga_seed),
        ga_depth=int(args.ga_depth),
        candidate_limit=int(args.candidate_limit),
        disable_fg=bool(not args.enable_fg),
        hitsim_seed=int(args.hitsim_seed),
        refine_candidate_limit=int(args.refine_candidate_limit),
    )

    variants = [
        ("full_exact", 0, "all"),
        (f"cap{int(args.max_regimes)}_{str(args.selection)}", int(args.max_regimes), str(args.selection)),
    ]

    results: dict[str, dict] = {}
    for label, regime_cap, regime_selection in variants:
        results[label] = _load_variant(
            label=label,
            base_result=base_result,
            paths=paths,
            ref_arrays=ref_arrays,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            hitsim_seed=int(args.hitsim_seed),
            refine_candidate_limit=int(args.refine_candidate_limit),
            regime_cap=int(regime_cap),
            regime_selection=str(regime_selection),
        )

    ref = results["full_exact"]
    capped = results[f"cap{int(args.max_regimes)}_{str(args.selection)}"]
    summary = {
        "song": song_pick,
        "settings": {
            "ga_seed": int(args.ga_seed),
            "hitsim_seed": int(args.hitsim_seed),
            "ga_depth": int(args.ga_depth),
            "candidate_limit": int(args.candidate_limit),
            "refine_candidate_limit": int(args.refine_candidate_limit),
            "disable_fg": bool(not args.enable_fg),
            "max_regimes": int(args.max_regimes),
            "selection": str(args.selection),
        },
        "base_ga": {
            "elapsed_sec": float(base_result.get("_base_ga_elapsed_sec") or 0.0),
            "best_score": int(_safe_int((base_result.get("best_data") or {}).get("BaseScore", 0), 0)),
            "ga_candidate_count": int(len(base_result.get("ga_candidates") or [])),
        },
        "results": results,
        "comparison": {
            "top1_match": bool(ref["best_loadout_label"] == capped["best_loadout_label"]),
            "score_gap": int(ref["best_score"] - capped["best_score"]),
            "runtime_ratio_vs_full": round(
                float(capped["elapsed_sec"]) / float(ref["elapsed_sec"] or 1.0),
                6,
            ),
        },
    }

    out = Path(args.out) if args.out else None
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
