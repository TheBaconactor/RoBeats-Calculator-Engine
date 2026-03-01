from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from .gpu_witness_pool import build_witness_offsets_gpu
from .wildcard_palette import learn_wildcard_palette

try:
    from ortools.sat.python import cp_model
except Exception:  # pragma: no cover - graceful fallback when OR-Tools is absent.
    cp_model = None


def _status_name(status: int) -> str:
    if cp_model is None:
        return "ORTOOLS_MISSING"
    if status == cp_model.OPTIMAL:
        return "OPTIMAL"
    if status == cp_model.FEASIBLE:
        return "FEASIBLE"
    if status == cp_model.INFEASIBLE:
        return "INFEASIBLE"
    if status == cp_model.MODEL_INVALID:
        return "MODEL_INVALID"
    if status == cp_model.UNKNOWN:
        return "UNKNOWN"
    return f"STATUS_{int(status)}"


def _count_used_gear_variants(gear_ids_np: np.ndarray, covered_np: np.ndarray, chosen_offsets_np: np.ndarray) -> int:
    used: Set[Tuple[int, int]] = set()
    for s_idx, is_cov in enumerate(np.asarray(covered_np, dtype=np.int32).tolist()):
        if int(is_cov) <= 0:
            continue
        for j in range(6):
            off = int(chosen_offsets_np[s_idx, j])
            if off < 0:
                continue
            used.add((int(gear_ids_np[s_idx, j]), off))
    return int(len(used))


def _collect_used_raw_variants(
    *,
    gear_ids_np: np.ndarray,
    covered_np: np.ndarray,
    chosen_offsets_np: np.ndarray,
    mask: np.ndarray,
) -> Set[int]:
    raw: Set[int] = set()
    covered_np = np.asarray(covered_np, dtype=np.int32)
    chosen_offsets_np = np.asarray(chosen_offsets_np, dtype=np.int32)
    mask = np.asarray(mask, dtype=np.int32)
    for s_idx, keep in enumerate(mask.tolist()):
        if int(keep) <= 0:
            continue
        if int(covered_np[s_idx]) <= 0:
            continue
        for j in range(6):
            gid = int(gear_ids_np[s_idx, j])
            off = int(chosen_offsets_np[s_idx, j])
            if gid <= 0 or off < 0:
                continue
            raw.add((gid << 16) | off)
    return raw


def _select_hypergraph_neighborhood(
    *,
    gear_ids_np: np.ndarray,
    covered_np: np.ndarray,
    max_songs: int,
    rng: random.Random,
) -> np.ndarray:
    covered_np = np.asarray(covered_np, dtype=np.int32)
    uncovered_idx = np.flatnonzero(covered_np <= 0).astype(np.int32, copy=False)
    if int(uncovered_idx.size) <= 0:
        return np.zeros((0,), dtype=np.int32)

    max_songs = max(1, int(max_songs))
    covered_idx = np.flatnonzero(covered_np > 0).astype(np.int32, copy=False)

    # If uncovered set is already huge, pick the uncovered songs with strongest overlap potential
    # against currently covered songs.
    if int(uncovered_idx.size) >= int(max_songs):
        covered_gear_weight: Dict[int, int] = {}
        for s_idx in covered_idx.tolist():
            for gid in gear_ids_np[int(s_idx), :].tolist():
                g = int(gid)
                covered_gear_weight[g] = int(covered_gear_weight.get(g, 0) + 1)
        scored: List[Tuple[int, float, int]] = []
        for s_idx in uncovered_idx.tolist():
            score = 0
            for gid in gear_ids_np[int(s_idx), :].tolist():
                score += int(covered_gear_weight.get(int(gid), 0))
            scored.append((int(score), float(rng.random()), int(s_idx)))
        scored.sort(key=lambda t: (-int(t[0]), float(t[1]), int(t[2])))
        picked = [int(t[2]) for t in scored[: int(max_songs)]]
        return np.asarray(sorted(picked), dtype=np.int32)

    selected: Set[int] = {int(x) for x in uncovered_idx.tolist()}
    remaining = int(max_songs) - int(len(selected))
    if remaining <= 0:
        return np.asarray(sorted(selected), dtype=np.int32)

    uncovered_gear_weight: Dict[int, int] = {}
    for s_idx in uncovered_idx.tolist():
        for gid in gear_ids_np[int(s_idx), :].tolist():
            g = int(gid)
            uncovered_gear_weight[g] = int(uncovered_gear_weight.get(g, 0) + 1)

    scored_cov: List[Tuple[int, float, int]] = []
    for s_idx in covered_idx.tolist():
        score = 0
        for gid in gear_ids_np[int(s_idx), :].tolist():
            score += int(uncovered_gear_weight.get(int(gid), 0))
        if score > 0:
            scored_cov.append((int(score), float(rng.random()), int(s_idx)))
    scored_cov.sort(key=lambda t: (-int(t[0]), float(t[1]), int(t[2])))

    for _score, _j, s_idx in scored_cov:
        if remaining <= 0:
            break
        if int(s_idx) in selected:
            continue
        selected.add(int(s_idx))
        remaining -= 1

    if remaining > 0:
        fallback = [int(x) for x in covered_idx.tolist() if int(x) not in selected]
        rng.shuffle(fallback)
        for s_idx in fallback[:remaining]:
            selected.add(int(s_idx))

    return np.asarray(sorted(selected), dtype=np.int32)


def _build_pattern_library(
    *,
    gear_ids_np: np.ndarray,
    totals_np: np.ndarray,
    elements_np: np.ndarray,
    gear_freq_np: np.ndarray,
    baseline_offsets_np: np.ndarray,
    k_total: int,
    patterns_per_song: int,
    seed: int,
    anchor_patterns: int,
    seed_streams: int,
    pattern_profile: int,
    wildcard_palette_size: int,
    wildcard_palette_min_count: int,
    wildcard_palette_scan: int,
    wildcard_palette_tail_slots: int,
    profile: bool,
) -> Tuple[List[List[Tuple[int, int, int, int, int, int]]], dict]:
    palette_vecs = None
    if int(wildcard_palette_size) > 0:
        pal = learn_wildcard_palette(
            totals_np,
            palette_size=int(wildcard_palette_size),
            min_count=int(wildcard_palette_min_count),
        )
        vecs = np.asarray(getattr(pal, "vecs", np.zeros((0, 5), dtype=np.int32)), dtype=np.int32)
        if int(vecs.size) > 0:
            palette_vecs = vecs

    offsets_np, wp_stats = build_witness_offsets_gpu(
        gear_ids_np,
        totals_np,
        elements_np,
        gear_freq_np,
        k_total=int(max(1, k_total)),
        seed=int(seed),
        anchor_patterns=int(max(0, anchor_patterns)),
        seed_streams=int(max(1, seed_streams)),
        pattern_profile=int(max(0, pattern_profile)),
        wildcard_palette_vecs=palette_vecs,
        wildcard_palette_scan=int(max(0, wildcard_palette_scan)),
        wildcard_palette_tail_slots=int(max(0, min(6, wildcard_palette_tail_slots))),
        profile=bool(profile),
    )

    patterns: List[List[Tuple[int, int, int, int, int, int]]] = []
    for s_idx in range(int(gear_ids_np.shape[0])):
        seen: Set[Tuple[int, int, int, int, int, int]] = set()
        song_patterns: List[Tuple[int, int, int, int, int, int]] = []
        baseline = tuple(int(x) for x in baseline_offsets_np[s_idx, :].tolist())
        if all(int(x) >= 0 for x in baseline):
            song_patterns.append(baseline)
            seen.add(baseline)
        for p in range(int(offsets_np.shape[1])):
            key = tuple(int(x) for x in offsets_np[s_idx, p, :].tolist())
            if key in seen:
                continue
            if any(int(x) < 0 for x in key):
                continue
            song_patterns.append(key)
            seen.add(key)
            if len(song_patterns) >= int(max(1, patterns_per_song)):
                break
        if not song_patterns:
            # Keep at least one feasible option for each song.
            key = tuple(int(x) for x in offsets_np[s_idx, 0, :].tolist())
            song_patterns = [key]
        patterns.append(song_patterns)

    return patterns, wp_stats


def _solve_cpsat_round(
    *,
    gear_ids_np: np.ndarray,
    baseline_covered_np: np.ndarray,
    baseline_offsets_np: np.ndarray,
    song_patterns: List[List[Tuple[int, int, int, int, int, int]]],
    fixed_raw_vids: Set[int],
    inventory_cap: int,
    time_limit_sec: float,
    random_seed: int,
    num_workers: int,
    randomized: bool,
    enforce_non_regression: bool,
) -> Optional[dict]:
    if cp_model is None:
        return None
    S = int(gear_ids_np.shape[0])
    if S <= 0:
        return None

    budget_left = int(inventory_cap) - int(len(fixed_raw_vids))
    if budget_left < 0:
        return None

    # Precompute raw variants per pattern and build the free-variant universe.
    free_vid_to_idx: Dict[int, int] = {}
    pattern_raw_vids: List[List[List[int]]] = []
    baseline_pattern_idx: List[int] = []
    for s_idx in range(S):
        row_patterns = song_patterns[s_idx]
        baseline_key = tuple(int(x) for x in baseline_offsets_np[s_idx, :].tolist())
        b_idx = -1
        row_raw: List[List[int]] = []
        for p_idx, off_tuple in enumerate(row_patterns):
            if tuple(int(x) for x in off_tuple) == baseline_key:
                b_idx = int(p_idx)
            raws: List[int] = []
            for j in range(6):
                gid = int(gear_ids_np[s_idx, j])
                off = int(off_tuple[j])
                raw = (gid << 16) | off
                raws.append(raw)
                if raw not in fixed_raw_vids and raw not in free_vid_to_idx:
                    free_vid_to_idx[raw] = int(len(free_vid_to_idx))
            row_raw.append(raws)
        pattern_raw_vids.append(row_raw)
        baseline_pattern_idx.append(int(b_idx))

    model = cp_model.CpModel()

    x_vars: List[List[object]] = []
    cover_vars: List[object] = []
    keep_vars: List[object] = []
    uncovered_cover_vars: List[object] = []
    for s_idx in range(S):
        row: List[object] = []
        for p_idx in range(len(song_patterns[s_idx])):
            row.append(model.NewBoolVar(f"x_s{s_idx}_p{p_idx}"))
        x_vars.append(row)
        if row:
            model.Add(sum(row) <= 1)
            cover = model.NewBoolVar(f"cover_s{s_idx}")
            model.Add(sum(row) == cover)
        else:
            cover = model.NewConstant(0)
        cover_vars.append(cover)

        base_cov = int(baseline_covered_np[s_idx])
        if bool(enforce_non_regression) and base_cov > 0:
            model.Add(cover == 1)
        if base_cov <= 0:
            uncovered_cover_vars.append(cover)

        b_idx = int(baseline_pattern_idx[s_idx])
        if b_idx >= 0 and b_idx < len(row):
            keep_vars.append(row[b_idx])

    z_vars: List[object] = [model.NewBoolVar(f"z_v{idx}") for idx in range(len(free_vid_to_idx))]
    for s_idx in range(S):
        for p_idx, x in enumerate(x_vars[s_idx]):
            raws = pattern_raw_vids[s_idx][p_idx]
            unique_free = {int(raw) for raw in raws if int(raw) not in fixed_raw_vids}
            for raw in unique_free:
                model.Add(x <= z_vars[int(free_vid_to_idx[raw])])
    if z_vars:
        model.Add(sum(z_vars) <= int(max(0, budget_left)))

    # Lexicographic approximation (single objective):
    # 1) maximize newly-covered songs, 2) maximize baseline retention, 3) minimize new variants.
    w_cover = int(1_000_000)
    w_keep = int(10)
    w_new = int(1)
    model.Maximize(w_cover * sum(uncovered_cover_vars) + w_keep * sum(keep_vars) - w_new * sum(z_vars))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(max(0.01, time_limit_sec))
    solver.parameters.num_search_workers = int(max(1, num_workers))
    solver.parameters.random_seed = int(max(1, random_seed))
    solver.parameters.randomize_search = bool(randomized)
    solver.parameters.log_search_progress = False

    t0 = time.perf_counter()
    status = solver.Solve(model)
    wall = float(time.perf_counter() - t0)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return {
            "ok": False,
            "status": _status_name(int(status)),
            "wall_time_sec": float(round(wall, 6)),
            "num_conflicts": int(solver.NumConflicts()),
            "num_branches": int(solver.NumBranches()),
        }

    out_covered = np.asarray(baseline_covered_np, dtype=np.int32).copy()
    out_offsets = np.asarray(baseline_offsets_np, dtype=np.int32).copy()
    used_raw: Set[int] = set(int(x) for x in fixed_raw_vids)
    for s_idx in range(S):
        chosen = -1
        for p_idx, x in enumerate(x_vars[s_idx]):
            if solver.BooleanValue(x):
                chosen = int(p_idx)
                break
        if chosen < 0:
            out_covered[s_idx] = 0
            continue
        out_covered[s_idx] = 1
        pat = song_patterns[s_idx][chosen]
        out_offsets[s_idx, :] = np.asarray(list(pat), dtype=np.int32)
        for raw in pattern_raw_vids[s_idx][chosen]:
            used_raw.add(int(raw))

    return {
        "ok": True,
        "status": _status_name(int(status)),
        "covered_np": out_covered,
        "offsets_np": out_offsets,
        "used_total": int(len(used_raw)),
        "objective": int(round(float(solver.ObjectiveValue()))),
        "best_objective_bound": int(round(float(solver.BestObjectiveBound()))),
        "wall_time_sec": float(round(wall, 6)),
        "num_conflicts": int(solver.NumConflicts()),
        "num_branches": int(solver.NumBranches()),
    }


@dataclass
class CPSatHypergraphResult:
    covered_np: np.ndarray
    chosen_offsets_np: np.ndarray
    improved: bool
    stats: dict


def refine_with_cpsat_hypergraph(
    *,
    gear_ids_np: np.ndarray,
    totals_np: np.ndarray,
    elements_np: np.ndarray,
    gear_freq_np: np.ndarray,
    covered_np: np.ndarray,
    chosen_offsets_np: np.ndarray,
    inventory_cap: int,
    seed: int,
    rounds: int,
    max_songs: int,
    patterns_per_song: int,
    witness_anchor_patterns: int,
    witness_seed_streams: int,
    witness_pattern_profile: int,
    wildcard_palette_size: int,
    wildcard_palette_min_count: int,
    wildcard_palette_scan: int,
    wildcard_palette_tail_slots: int,
    time_limit_sec: float,
    num_workers: int,
    randomized: bool,
    enforce_non_regression: bool,
    seeded_raw_vids: Optional[np.ndarray],
    seeded_mode: str,
    profile: bool = False,
    log_fn: Optional[Callable[[str], None]] = None,
) -> CPSatHypergraphResult:
    covered_np = np.asarray(covered_np, dtype=np.int32)
    chosen_offsets_np = np.asarray(chosen_offsets_np, dtype=np.int32)

    base_cov = int(covered_np.sum())
    base_used = _count_used_gear_variants(gear_ids_np, covered_np, chosen_offsets_np)
    stats: dict = {
        "enabled": bool(cp_model is not None),
        "rounds": int(max(0, rounds)),
        "max_songs": int(max(1, max_songs)),
        "patterns_per_song": int(max(1, patterns_per_song)),
        "time_limit_sec": float(max(0.01, time_limit_sec)),
        "num_workers": int(max(1, num_workers)),
        "randomized": bool(randomized),
        "enforce_non_regression": bool(enforce_non_regression),
        "baseline": {"covered": int(base_cov), "used": int(base_used)},
        "round_stats": [],
        "improvements": 0,
    }
    if cp_model is None:
        stats["reason"] = "ortools_missing"
        return CPSatHypergraphResult(
            covered_np=covered_np.copy(),
            chosen_offsets_np=chosen_offsets_np.copy(),
            improved=False,
            stats=stats,
        )
    if int(rounds) <= 0:
        stats["reason"] = "disabled_rounds"
        return CPSatHypergraphResult(
            covered_np=covered_np.copy(),
            chosen_offsets_np=chosen_offsets_np.copy(),
            improved=False,
            stats=stats,
        )

    current_cov = covered_np.copy()
    current_offsets = chosen_offsets_np.copy()
    rng = random.Random(int(seed))

    for r in range(int(rounds)):
        round_seed = int(seed) + int(r) * 7919 + int(rng.randint(0, 10_000))
        neighborhood = _select_hypergraph_neighborhood(
            gear_ids_np=gear_ids_np,
            covered_np=current_cov,
            max_songs=int(max_songs),
            rng=rng,
        )
        if int(neighborhood.size) <= 0:
            stats["round_stats"].append({"round": int(r + 1), "skipped": "no_uncovered_songs"})
            continue

        sub_gear = np.asarray(gear_ids_np[neighborhood], dtype=np.int32)
        sub_totals = np.asarray(totals_np[neighborhood], dtype=np.int32)
        sub_elements = np.asarray(elements_np[neighborhood], dtype=np.int32)
        sub_cov = np.asarray(current_cov[neighborhood], dtype=np.int32)
        sub_offsets = np.asarray(current_offsets[neighborhood], dtype=np.int32)

        fixed_mask = np.ones((int(current_cov.shape[0]),), dtype=np.int32)
        fixed_mask[neighborhood] = 0
        fixed_raw = _collect_used_raw_variants(
            gear_ids_np=gear_ids_np,
            covered_np=current_cov,
            chosen_offsets_np=current_offsets,
            mask=fixed_mask,
        )
        if str(seeded_mode or "").strip().lower() == "hard" and seeded_raw_vids is not None:
            for raw in np.asarray(seeded_raw_vids, dtype=np.int32).tolist():
                fixed_raw.add(int(raw))

        patterns, wp_stats = _build_pattern_library(
            gear_ids_np=sub_gear,
            totals_np=sub_totals,
            elements_np=sub_elements,
            gear_freq_np=gear_freq_np,
            baseline_offsets_np=sub_offsets,
            k_total=int(max(4, patterns_per_song)),
            patterns_per_song=int(max(1, patterns_per_song)),
            seed=int(round_seed),
            anchor_patterns=int(min(max(0, witness_anchor_patterns), max(4, patterns_per_song))),
            seed_streams=int(max(1, witness_seed_streams)),
            pattern_profile=int(max(0, witness_pattern_profile)),
            wildcard_palette_size=int(max(0, wildcard_palette_size)),
            wildcard_palette_min_count=int(max(1, wildcard_palette_min_count)),
            wildcard_palette_scan=int(max(0, wildcard_palette_scan)),
            wildcard_palette_tail_slots=int(max(0, min(6, wildcard_palette_tail_slots))),
            profile=bool(profile),
        )

        solved = _solve_cpsat_round(
            gear_ids_np=sub_gear,
            baseline_covered_np=sub_cov,
            baseline_offsets_np=sub_offsets,
            song_patterns=patterns,
            fixed_raw_vids=fixed_raw,
            inventory_cap=int(inventory_cap),
            time_limit_sec=float(max(0.01, time_limit_sec)),
            random_seed=int(round_seed),
            num_workers=int(max(1, num_workers)),
            randomized=bool(randomized),
            enforce_non_regression=bool(enforce_non_regression),
        )
        if solved is None or not bool(solved.get("ok")):
            stats["round_stats"].append(
                {
                    "round": int(r + 1),
                    "songs": int(neighborhood.size),
                    "fixed_variants": int(len(fixed_raw)),
                    "witness_pool": wp_stats,
                    "cp_sat": solved,
                    "accepted": False,
                }
            )
            continue

        candidate_cov = current_cov.copy()
        candidate_offsets = current_offsets.copy()
        candidate_cov[neighborhood] = np.asarray(solved["covered_np"], dtype=np.int32)
        candidate_offsets[neighborhood, :] = np.asarray(solved["offsets_np"], dtype=np.int32)

        cur_cov_count = int(current_cov.sum())
        cur_used = _count_used_gear_variants(gear_ids_np, current_cov, current_offsets)
        cand_cov_count = int(candidate_cov.sum())
        cand_used = _count_used_gear_variants(gear_ids_np, candidate_cov, candidate_offsets)
        accepted = bool((cand_cov_count > cur_cov_count) or (cand_cov_count == cur_cov_count and cand_used < cur_used))
        if accepted:
            current_cov = candidate_cov
            current_offsets = candidate_offsets
            stats["improvements"] = int(stats.get("improvements", 0) + 1)
            if log_fn is not None:
                log_fn(
                    f"cp_sat_hypergraph_round_{int(r + 1)}_accepted "
                    f"(covered={cand_cov_count}, used={cand_used}, songs={int(neighborhood.size)})"
                )

        stats["round_stats"].append(
            {
                "round": int(r + 1),
                "songs": int(neighborhood.size),
                "fixed_variants": int(len(fixed_raw)),
                "witness_pool": wp_stats,
                "cp_sat": solved,
                "candidate": {"covered": int(cand_cov_count), "used": int(cand_used)},
                "accepted": bool(accepted),
            }
        )

    final_cov = int(current_cov.sum())
    final_used = _count_used_gear_variants(gear_ids_np, current_cov, current_offsets)
    improved = bool((final_cov > base_cov) or (final_cov == base_cov and final_used < base_used))
    stats["final"] = {"covered": int(final_cov), "used": int(final_used)}
    stats["improved"] = bool(improved)
    return CPSatHypergraphResult(
        covered_np=current_cov,
        chosen_offsets_np=current_offsets,
        improved=bool(improved),
        stats=stats,
    )


__all__ = [
    "CPSatHypergraphResult",
    "refine_with_cpsat_hypergraph",
]
