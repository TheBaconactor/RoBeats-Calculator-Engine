from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

from .db import (
    fetch_candidates_for_peak,
    fetch_candidates_within_delta_allow_missing,
    fetch_peak_candidates_allow_missing,
    fetch_song_names_limited,
    fetch_song_peak,
)
from .export import export_inventory_meta_json, hydrate_force_details
from .gpu_dynamic_solver import solve_coverage_gpu_dynamic
from .gpu_eda_solver import solve_coverage_gpu_eda
from .gpu_full_solver import solve_coverage_gpu_full
from .gpu_witness_pool import build_witness_offsets_gpu
from .keys import ELEMENT_TO_ID, ID_TO_ELEMENT, OV_INDEX, STAT_KEYS
from .models import CandidateSpec, SongCandidate, SongSpec
from .variant_space import build_variant_offset_tables


class _MemoryLogger:
    def __init__(self, *, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self._process = psutil.Process(os.getpid()) if self.enabled else None
        self._t0 = time.perf_counter()
        self.records: List[dict] = []

    def _rss_bytes(self) -> int:
        if not self._process:
            return 0
        try:
            return int(self._process.memory_info().rss)
        except Exception:
            return 0

    def log(self, label: str) -> None:
        if not self.enabled:
            return
        now = time.perf_counter()
        rss = self._rss_bytes()
        rec = {
            "t_sec": round(now - self._t0, 3),
            "label": str(label),
            "rss_mb": round(rss / (1024 * 1024), 2),
        }
        self.records.append(rec)
        print(f"[InventoryOptimizer] {rec['label']} t={rec['t_sec']}s rss={rec['rss_mb']}MB", flush=True)


@dataclass(frozen=True)
class _CoverageSong:
    song_name: str
    candidate: CandidateSpec


def _collect_gear_names(candidates_by_song: Dict[str, List[SongCandidate]]) -> List[str]:
    names: set[str] = set()
    for candidates in candidates_by_song.values():
        for cand in candidates:
            names.update(cand.gear_names)
    return sorted(names)


def _collect_mini_names(candidates_by_song: Dict[str, List[SongCandidate]]) -> List[str]:
    names: set[str] = set()
    for candidates in candidates_by_song.values():
        for cand in candidates:
            for group in cand.mini_groups:
                names.update(group)
    return sorted(names)


def _build_song_specs(
    candidates_by_song: Dict[str, List[SongCandidate]],
    gear_id_map: Dict[str, int],
    mini_id_map: Dict[str, int],
) -> List[SongSpec]:
    song_specs: List[SongSpec] = []
    for song_name in sorted(candidates_by_song.keys()):
        specs: List[CandidateSpec] = []
        for cand in candidates_by_song[song_name]:
            gear_ids = tuple(gear_id_map[g] for g in cand.gear_names)
            mini_group_ids: List[Tuple[int, ...]] = []
            for group in cand.mini_groups:
                ids = tuple(mini_id_map[n] for n in group)
                if not ids:
                    continue
                mini_group_ids.append(ids)
            if len(mini_group_ids) != 3:
                continue
            element_id = ELEMENT_TO_ID.get(cand.selected_element, 0)
            if not element_id:
                continue
            specs.append(
                CandidateSpec(
                    candidate=cand,
                    gear_ids=gear_ids,
                    mini_group_ids=tuple(mini_group_ids),
                    element_id=element_id,
                )
            )
        if not specs:
            raise ValueError(f"No valid candidates for song: {song_name}")
        song_specs.append(SongSpec(name=song_name, candidates=specs))
    return song_specs


def _select_one_peak_candidate_per_song(song_specs: List[SongSpec]) -> List[_CoverageSong]:
    """
    Pick ONE peak candidate per song.

    If a song has multiple DB rows tied for the top peak (e.g., base vs FG),
    choose a deterministic candidate that tends to improve inventory reuse:
    - Prefer gear used by many songs.
    - Prefer lower total OV / fewer OV-positive slots (less element-locking).
    - Prefer `loadouts` over `fg_loadouts`, then lower rowid.
    """
    gear_freq: Dict[int, int] = {}
    for song in song_specs:
        for cand in song.candidates:
            for gid in cand.gear_ids:
                gear_freq[gid] = gear_freq.get(gid, 0) + 1

    selected: List[_CoverageSong] = []
    for song in song_specs:
        best: Optional[CandidateSpec] = None
        best_key: Optional[Tuple[Any, ...]] = None
        for cand in song.candidates:
            key = _candidate_rank_key(cand, gear_freq)
            if best is None or key < best_key:
                best = cand
                best_key = key
        if best is None:
            continue
        selected.append(_CoverageSong(song_name=song.name, candidate=best))
    return selected


def _candidate_rank_key(
    cand: CandidateSpec,
    gear_freq: Dict[int, int],
    *,
    song_peak: Optional[int] = None,
) -> Tuple[Any, ...]:
    freq_sum = sum(gear_freq.get(g, 0) for g in cand.gear_ids)
    src_rank = 0 if cand.candidate.source_table == "loadouts" else 1
    ov_total = int(cand.candidate.gem_totals[OV_INDEX])
    eff_score = int(cand.candidate.fg_score) if cand.candidate.source_table == "fg_loadouts" else int(cand.candidate.score)
    score_gap = 0 if song_peak is None else max(0, int(song_peak) - int(eff_score))
    # Minimum number of OV-positive slots needed is ceil(OV_total / 15).
    req_ov_slots = 0 if ov_total <= 0 else (ov_total + 14) // 15
    # Primary objective for coverage is gear reuse: sharing gear IDs across songs reduces the number
    # of distinct variants needed. OV locking matters too, but treat it as a tie-breaker.
    # If provided, include closeness-to-peak as a primary objective (lower gap first).
    return (score_gap, -freq_sum, req_ov_slots, ov_total, src_rank, cand.candidate.rowid)


def _select_top_k_candidates_per_song(
    song_specs: List[SongSpec],
    *,
    k_candidates: int,
    song_peak_by_name: Optional[Dict[str, int]] = None,
) -> List[SongSpec]:
    if int(k_candidates) <= 0:
        raise ValueError("k_candidates must be positive.")

    gear_freq: Dict[int, int] = {}
    for song in song_specs:
        for cand in song.candidates:
            for gid in cand.gear_ids:
                gear_freq[gid] = gear_freq.get(gid, 0) + 1

    selected: List[SongSpec] = []
    k_candidates = int(k_candidates)
    for song in song_specs:
        song_peak = None if song_peak_by_name is None else song_peak_by_name.get(song.name)
        dedup: Dict[Tuple[Any, ...], CandidateSpec] = {}
        best_key_by_dedup: Dict[Tuple[Any, ...], Tuple[Any, ...]] = {}
        for cand in song.candidates:
            dedup_key = (
                cand.gear_ids,
                cand.candidate.gem_totals,
                cand.element_id,
            )
            key = _candidate_rank_key(cand, gear_freq, song_peak=song_peak)
            if dedup_key not in dedup or key < best_key_by_dedup[dedup_key]:
                dedup[dedup_key] = cand
                best_key_by_dedup[dedup_key] = key

        ranked = sorted(dedup.values(), key=lambda c: _candidate_rank_key(c, gear_freq, song_peak=song_peak))
        if not ranked:
            continue
        if len(ranked) > k_candidates:
            ranked = ranked[:k_candidates]
        selected.append(SongSpec(name=song.name, candidates=ranked))
    return selected


def _materialize_coverage_solution(
    songs: List[_CoverageSong],
    *,
    gear_names: List[str],
    gear_ids_np: np.ndarray,
    sol: Any,
    mode: str,
    solver_status: str,
    inventory_cap: int,
    seed: int,
    gpu_repack_passes: int,
    gpu_lns_destroy: int,
    lns_time_sec: float,
    lns_attempts: int,
    mem: _MemoryLogger,
    legacy_args: Optional[dict] = None,
) -> dict:
    if not songs:
        raise ValueError("No songs provided.")

    num_songs = int(len(songs))
    mem.log(f"gpu_dynamic_materialize (songs={num_songs})")

    covered_np = np.asarray(sol.covered, dtype=np.int32)
    chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)

    # Identify used variants from per-song chosen offsets (avoids materializing big `(G, VARIANTS)` count arrays).
    used_pairs_set: set[Tuple[int, int]] = set()
    for s_idx, is_cov in enumerate(covered_np.tolist()):
        if int(is_cov) <= 0:
            continue
        for j in range(6):
            used_pairs_set.add((int(gear_ids_np[s_idx, j]), int(chosen_offsets_np[s_idx, j])))

    used_pairs = sorted(used_pairs_set)
    pair_to_id = {pair: idx for idx, pair in enumerate(used_pairs)}

    offset_gems_np, offset_color_np = build_variant_offset_tables()

    variants_out: List[dict] = []
    for idx, (gid, off) in enumerate(used_pairs):
        vec = offset_gems_np[off]
        ov_color_id = int(offset_color_np[off])
        variants_out.append(
            {
                "id": int(idx),
                "gear_name": gear_names[gid - 1] if gid > 0 else "",
                "gems": {STAT_KEYS[i]: int(vec[i]) for i in range(len(STAT_KEYS))},
                "ov_color": ID_TO_ELEMENT.get(int(ov_color_id), "") if ov_color_id else "",
            }
        )

    minis_used: set[str] = set()
    assignments: Dict[str, dict] = {}
    for s_idx, song in enumerate(songs):
        if int(covered_np[s_idx]) <= 0:
            continue
        cand = song.candidate.candidate

        minis: set[str] = set()
        for group in cand.mini_groups:
            minis.update(group)
        minis_used.update(minis)

        offs = chosen_offsets_np[s_idx]
        gids = song.candidate.gear_ids
        variant_ids = [int(pair_to_id[(int(gids[j]), int(offs[j]))]) for j in range(6)]

        assignments[song.song_name] = {
            "source_table": cand.source_table,
            "candidate_rowid": cand.rowid,
            "score": cand.score,
            "fg_score": cand.fg_score,
            "gear": list(cand.gear_names),
            "selected_element": cand.selected_element,
            "gem_totals": {STAT_KEYS[i]: int(cand.gem_totals[i]) for i in range(len(STAT_KEYS))},
            "variant_ids": variant_ids,
            "minis": sorted(minis),
            "force_details": None,
        }

    uncovered_songs = [songs[i].song_name for i in range(num_songs) if int(covered_np[i]) <= 0]
    solver_stats: dict = {
        "status": str(solver_status),
        "seed": int(seed),
        "gpu_repack_passes": int(gpu_repack_passes),
        "gpu_lns_destroy": int(gpu_lns_destroy),
        "lns": {
            "enabled": bool(float(lns_time_sec) > 0),
            "time_sec": float(lns_time_sec),
            "attempts": int(lns_attempts),
        },
        "legacy": legacy_args or {},
        "solver": sol.stats,
    }
    if str(mode) == "coverage_gpu_dynamic":
        solver_stats["gpu_dynamic"] = sol.stats
    elif str(mode) == "coverage_gpu_eda":
        solver_stats["gpu_eda"] = sol.stats

    solution = {
        "mode": str(mode),
        "inventory": {"gear_variants": variants_out, "minis": sorted(minis_used)},
        "assignments": assignments,
        "uncovered_songs": uncovered_songs,
        "stats": {
            "songs_total": num_songs,
            "songs_covered": int(sol.covered_count),
            "gear_variants_used": len(variants_out),
            "gear_variants_cap": int(inventory_cap),
        },
        "solver_stats": solver_stats,
    }
    return solution


def _materialize_coverage_solution_multi(
    songs: List[SongSpec],
    *,
    gear_names: List[str],
    sol: Any,
    chosen_candidate_idx: np.ndarray,
    mode: str,
    solver_status: str,
    inventory_cap: int,
    seed: int,
    gpu_repack_passes: int,
    gpu_lns_destroy: int,
    lns_time_sec: float,
    lns_attempts: int,
    mem: _MemoryLogger,
    legacy_args: Optional[dict] = None,
) -> dict:
    if not songs:
        raise ValueError("No songs provided.")

    num_songs = int(len(songs))
    mem.log(f"gpu_full_materialize_multi (songs={num_songs})")

    covered_np = np.asarray(sol.covered, dtype=np.int32)
    chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)
    chosen_candidate_idx = np.asarray(chosen_candidate_idx, dtype=np.int32)

    used_pairs_set: set[Tuple[int, int]] = set()
    for s_idx, is_cov in enumerate(covered_np.tolist()):
        if int(is_cov) <= 0:
            continue
        c_idx = int(chosen_candidate_idx[s_idx])
        if c_idx < 0:
            continue
        cand = songs[s_idx].candidates[c_idx]
        for j in range(6):
            used_pairs_set.add((int(cand.gear_ids[j]), int(chosen_offsets_np[s_idx, j])))

    used_pairs = sorted(used_pairs_set)
    pair_to_id = {pair: idx for idx, pair in enumerate(used_pairs)}

    offset_gems_np, offset_color_np = build_variant_offset_tables()

    variants_out: List[dict] = []
    for idx, (gid, off) in enumerate(used_pairs):
        vec = offset_gems_np[off]
        ov_color_id = int(offset_color_np[off])
        variants_out.append(
            {
                "id": int(idx),
                "gear_name": gear_names[gid - 1] if gid > 0 else "",
                "gems": {STAT_KEYS[i]: int(vec[i]) for i in range(len(STAT_KEYS))},
                "ov_color": ID_TO_ELEMENT.get(int(ov_color_id), "") if ov_color_id else "",
            }
        )

    minis_used: set[str] = set()
    assignments: Dict[str, dict] = {}
    for s_idx, song in enumerate(songs):
        if int(covered_np[s_idx]) <= 0:
            continue
        c_idx = int(chosen_candidate_idx[s_idx])
        if c_idx < 0:
            continue
        cand = song.candidates[c_idx].candidate

        minis: set[str] = set()
        for group in cand.mini_groups:
            minis.update(group)
        minis_used.update(minis)

        offs = chosen_offsets_np[s_idx]
        gids = song.candidates[c_idx].gear_ids
        variant_ids = [int(pair_to_id[(int(gids[j]), int(offs[j]))]) for j in range(6)]

        assignments[song.name] = {
            "source_table": cand.source_table,
            "candidate_rowid": cand.rowid,
            "score": cand.score,
            "fg_score": cand.fg_score,
            "gear": list(cand.gear_names),
            "selected_element": cand.selected_element,
            "gem_totals": {STAT_KEYS[i]: int(cand.gem_totals[i]) for i in range(len(STAT_KEYS))},
            "variant_ids": variant_ids,
            "minis": sorted(minis),
            "force_details": None,
        }

    uncovered_songs = [songs[i].name for i in range(num_songs) if int(covered_np[i]) <= 0]
    solver_stats: dict = {
        "status": str(solver_status),
        "seed": int(seed),
        "gpu_repack_passes": int(gpu_repack_passes),
        "gpu_lns_destroy": int(gpu_lns_destroy),
        "lns": {
            "enabled": bool(float(lns_time_sec) > 0),
            "time_sec": float(lns_time_sec),
            "attempts": int(lns_attempts),
        },
        "legacy": legacy_args or {},
        "solver": sol.stats,
    }

    solution = {
        "mode": str(mode),
        "inventory": {"gear_variants": variants_out, "minis": sorted(minis_used)},
        "assignments": assignments,
        "uncovered_songs": uncovered_songs,
        "stats": {
            "songs_total": num_songs,
            "songs_covered": int(sol.covered_count),
            "gear_variants_used": len(variants_out),
            "gear_variants_cap": int(inventory_cap),
        },
        "solver_stats": solver_stats,
    }
    return solution


def _build_gpu_dynamic_inputs(
    songs: List[_CoverageSong], *, gear_names: List[str]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    num_songs = int(len(songs))
    gear_count = int(len(gear_names))
    if gear_count <= 0:
        raise ValueError("No gear names provided.")

    gear_ids_np = np.zeros((num_songs, 6), dtype=np.int32)
    totals_np = np.zeros((num_songs, len(STAT_KEYS)), dtype=np.int32)
    elements_np = np.zeros((num_songs,), dtype=np.int32)
    for s_idx, song in enumerate(songs):
        gear_ids_np[s_idx, :] = np.asarray(song.candidate.gear_ids, dtype=np.int32)
        totals_np[s_idx, :] = np.asarray(song.candidate.candidate.gem_totals, dtype=np.int32)
        elements_np[s_idx] = int(song.candidate.element_id)

    gear_freq_np = np.zeros((gear_count + 1,), dtype=np.int32)
    np.add.at(gear_freq_np, gear_ids_np.reshape(-1), 1)
    return gear_ids_np, totals_np, elements_np, gear_freq_np


def _build_candidate_gear_freq(songs: List[SongSpec], *, gear_count: int) -> np.ndarray:
    gear_freq_np = np.zeros((int(gear_count) + 1,), dtype=np.int32)
    for song in songs:
        for cand in song.candidates:
            for gid in cand.gear_ids:
                gear_freq_np[int(gid)] += 1
    return gear_freq_np


def _run_gpu_dynamic_solver(
    gear_ids_np: np.ndarray,
    totals_np: np.ndarray,
    elements_np: np.ndarray,
    gear_freq_np: np.ndarray,
    *,
    inventory_cap: int,
    seed: int,
    gpu_repack_passes: int,
    gpu_lns_destroy: int,
    lns_time_sec: float,
    lns_attempts: int,
    mem: _MemoryLogger,
):
    sol = solve_coverage_gpu_dynamic(
        gear_ids_np,
        totals_np,
        elements_np,
        gear_freq_np,
        inventory_cap=inventory_cap,
        seed=seed,
        repack_passes=gpu_repack_passes,
        lns_time_sec=float(lns_time_sec),
        lns_attempts=int(lns_attempts),
        lns_destroy=int(gpu_lns_destroy),
        prefer_wildcards=True,
        return_counts=False,
        profile=bool(mem.enabled),
    )
    mem.log("gpu_dynamic_solved")
    return sol


def _run_gpu_eda_solver(
    gear_ids_np: np.ndarray,
    totals_np: np.ndarray,
    elements_np: np.ndarray,
    gear_freq_np: np.ndarray,
    *,
    inventory_cap: int,
    seed: int,
    witnesses_per_song: int,
    population: int,
    iterations: int,
    elites: int,
    alpha: float,
    wildcard_bonus: float,
    seed_witness_offsets: Optional[np.ndarray] = None,
    mem: _MemoryLogger,
):
    mem.log(
        "gpu_eda_start "
        f"(witnesses={int(witnesses_per_song)}, pop={int(population)}, iters={int(iterations)}, elites={int(elites)})"
    )
    sol = solve_coverage_gpu_eda(
        gear_ids_np,
        totals_np,
        elements_np,
        gear_freq_np,
        inventory_cap=inventory_cap,
        seed=seed,
        witnesses_per_song=int(witnesses_per_song),
        population=int(population),
        iterations=int(iterations),
        elites=int(elites),
        alpha=float(alpha),
        wildcard_bonus=float(wildcard_bonus),
        seed_witness_offsets=seed_witness_offsets,
        profile=bool(mem.enabled),
    )
    mem.log("gpu_eda_solved")
    return sol


def _count_used_gear_variants(gear_ids_np: np.ndarray, covered_np: np.ndarray, chosen_offsets_np: np.ndarray) -> int:
    used: set[Tuple[int, int]] = set()
    for s_idx, is_cov in enumerate(covered_np.tolist()):
        if int(is_cov) <= 0:
            continue
        for j in range(6):
            used.add((int(gear_ids_np[s_idx, j]), int(chosen_offsets_np[s_idx, j])))
    return len(used)


def _count_used_gear_variants_multi(
    songs: List[SongSpec],
    covered_np: np.ndarray,
    chosen_offsets_np: np.ndarray,
    chosen_candidate_idx: np.ndarray,
) -> int:
    used: set[Tuple[int, int]] = set()
    for s_idx, is_cov in enumerate(covered_np.tolist()):
        if int(is_cov) <= 0:
            continue
        c_idx = int(chosen_candidate_idx[s_idx])
        if c_idx < 0:
            continue
        cand = songs[s_idx].candidates[c_idx]
        for j in range(6):
            used.add((int(cand.gear_ids[j]), int(chosen_offsets_np[s_idx, j])))
    return len(used)


def _run_gpu_full_solver_from_witness_pool(
    gear_ids_np: np.ndarray,
    totals_np: np.ndarray,
    elements_np: np.ndarray,
    gear_freq_np: np.ndarray,
    *,
    inventory_cap: int,
    seed: int,
    k_total: int,
    gpu_repack_passes: int,
    gpu_full_repack_rarity_weighted: bool = False,
    lns_time_sec: float,
    lns_attempts: int,
    gpu_lns_destroy: int,
    gpu_full_lns_freq_weighted: bool,
    gpu_full_variant_freq_mode: str,
    gpu_full_counter_stripes: int,
    gpu_full_witness_pattern_profile: int,
    gpu_full_k_scan_select: int,
    gpu_full_k_scan_repack: int,
    gpu_full_witness_palettes: int,
    witness_anchor_patterns: int = 24,
    witness_seed_streams: int = 4,
    v_pad_bin: int = 4096,
    mem: _MemoryLogger,
    wildcard_freq_bonus: int = 0,
):
    palettes = int(gpu_full_witness_palettes)
    if palettes <= 0:
        raise ValueError("gpu_full_witness_palettes must be positive.")

    if palettes == 1:
        offsets_np, wp_stats = build_witness_offsets_gpu(
            gear_ids_np,
            totals_np,
            elements_np,
            gear_freq_np,
            k_total=int(k_total),
            seed=int(seed),
            anchor_patterns=int(witness_anchor_patterns),
            seed_streams=int(witness_seed_streams),
            pattern_profile=int(gpu_full_witness_pattern_profile),
            profile=bool(mem.enabled),
        )
    else:
        # Build multiple independent witness palettes and concatenate them along K.
        # This increases witness diversity while still allowing the solver to scan only a subset per step.
        offsets_list: List[np.ndarray] = []
        stats_list: List[dict] = []
        per_k = int(k_total)
        for p_idx in range(palettes):
            # Keep anchors only for the first palette to avoid duplicate anchor blocks.
            anchors = int(witness_anchor_patterns) if p_idx == 0 else 0
            seed_p = int(seed) ^ int((p_idx + 1) * 0x9E3779B9)
            off, st = build_witness_offsets_gpu(
                gear_ids_np,
                totals_np,
                elements_np,
                gear_freq_np,
                k_total=int(per_k),
                seed=int(seed_p),
                anchor_patterns=int(anchors),
                seed_streams=int(witness_seed_streams),
                pattern_profile=int(gpu_full_witness_pattern_profile),
                profile=bool(mem.enabled),
            )
            offsets_list.append(off)
            stats_list.append(st)
        offsets_np = np.concatenate(offsets_list, axis=1)
        wp_stats = {
            "songs": int(offsets_np.shape[0]),
            "k_total": int(offsets_np.shape[1]),
            "palettes": int(palettes),
            "per_palette_k": int(per_k),
            "anchor_patterns": int(witness_anchor_patterns),
            "seed_streams": int(witness_seed_streams),
            "pattern_profile": int(gpu_full_witness_pattern_profile),
            "time_sec": float(round(sum(float(s.get("time_sec") or 0.0) for s in stats_list), 6)),
            "palette_stats": stats_list,
        }
    mem.log("gpu_full_witness_pool_built")
    return _run_gpu_full_solver_from_offsets(
        gear_ids_np,
        offsets_np,
        inventory_cap=int(inventory_cap),
        seed=int(seed),
        gpu_repack_passes=int(gpu_repack_passes),
        gpu_full_repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
        gpu_full_k_scan_select=int(gpu_full_k_scan_select),
        gpu_full_k_scan_repack=int(gpu_full_k_scan_repack),
        lns_time_sec=float(lns_time_sec),
        lns_attempts=int(lns_attempts),
        gpu_lns_destroy=int(gpu_lns_destroy),
        gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
        gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
        gpu_full_counter_stripes=int(gpu_full_counter_stripes),
        mem=mem,
        wp_stats=wp_stats,
        v_pad_bin=int(v_pad_bin),
        wildcard_freq_bonus=int(wildcard_freq_bonus),
    )


def _build_multi_candidate_offsets(
    songs: List[SongSpec],
    *,
    k_total: int,
    seed: int,
    gear_freq_np: np.ndarray,
    witness_anchor_patterns: int,
    witness_seed_streams: int,
    gpu_full_witness_pattern_profile: int,
    mem: _MemoryLogger,
) -> Tuple[np.ndarray, np.ndarray, dict]:
    if not songs:
        raise ValueError("songs must be non-empty.")
    k_total = int(k_total)
    if k_total <= 0:
        raise ValueError("k_total must be positive.")

    song_count = int(len(songs))
    offsets_out = np.zeros((song_count, k_total, 6), dtype=np.int32)
    part_to_candidate = np.full((song_count, k_total), -1, dtype=np.int32)
    write_ptr = np.zeros((song_count,), dtype=np.int32)

    # Build a flat list of candidate instances so we can run witness generation ONCE with fixed K_total,
    # then slice per-candidate budgets (avoids multiple Taichi recompiles for varying K).
    items: List[Tuple[int, int, CandidateSpec, int, int]] = []  # (song_idx, cand_idx, cand, start, k_budget)
    cand_counts: List[int] = []
    for s_idx, song in enumerate(songs):
        cand_count = int(len(song.candidates))
        if cand_count <= 0:
            raise ValueError(f"No candidates for song: {song.name}")
        if k_total < cand_count:
            raise ValueError("k_total must be >= candidates per song for multi-candidate mode.")
        base = k_total // cand_count
        rem = k_total % cand_count
        if base <= 0:
            raise ValueError("k_total budget too small for candidate split.")
        cand_counts.append(cand_count)
        for c_idx, cand in enumerate(song.candidates):
            k_budget = base + (1 if c_idx < rem else 0)
            start = int(write_ptr[s_idx])
            end = start + int(k_budget)
            part_to_candidate[s_idx, start:end] = int(c_idx)
            write_ptr[s_idx] = int(end)
            items.append((int(s_idx), int(c_idx), cand, int(start), int(k_budget)))

    if np.any(write_ptr != int(k_total)):
        raise RuntimeError("Multi-candidate witness layout mismatch (k_total allocation).")

    if not items:
        raise RuntimeError("No candidate instances to build witness pool.")

    gear_ids_np = np.zeros((len(items), 6), dtype=np.int32)
    totals_np = np.zeros((len(items), 6), dtype=np.int32)
    elements_np = np.zeros((len(items),), dtype=np.int32)
    for idx, (_s_idx, _c_idx, cand, _start, _k_budget) in enumerate(items):
        gear_ids_np[idx, :] = np.asarray(cand.gear_ids, dtype=np.int32)
        totals_np[idx, :] = np.asarray(cand.candidate.gem_totals, dtype=np.int32)
        elements_np[idx] = int(cand.element_id)

    offsets_all, wp_stats = build_witness_offsets_gpu(
        gear_ids_np,
        totals_np,
        elements_np,
        gear_freq_np,
        k_total=int(k_total),
        seed=int(seed),
        anchor_patterns=int(witness_anchor_patterns),
        seed_streams=int(witness_seed_streams),
        pattern_profile=int(gpu_full_witness_pattern_profile),
        profile=bool(mem.enabled),
    )
    for idx, (s_idx, _c_idx, _cand, start, k_budget) in enumerate(items):
        end = int(start) + int(k_budget)
        offsets_out[s_idx, start:end, :] = offsets_all[idx, : int(k_budget), :]

    mem.log(f"gpu_full_witness_pool_built (candidate_instances={len(items)})")
    cand_min = int(min(cand_counts)) if cand_counts else 0
    cand_max = int(max(cand_counts)) if cand_counts else 0
    cand_avg = float(sum(cand_counts) / len(cand_counts)) if cand_counts else 0.0
    wp_summary = {
        "songs": int(song_count),
        "k_total": int(k_total),
        "anchor_patterns": int(witness_anchor_patterns),
        "seed_streams": int(witness_seed_streams),
        "pattern_profile": int(gpu_full_witness_pattern_profile),
        "time_sec": float(wp_stats.get("time_sec") or 0.0),
        "candidate_instances": int(len(items)),
        "candidates_per_song": {"min": cand_min, "max": cand_max, "avg": round(cand_avg, 3)},
    }
    return offsets_out, part_to_candidate, wp_summary


def _pad_v_count(v_count: int, *, bin_size: int = 4096) -> int:
    if int(bin_size) <= 0:
        return int(v_count)
    return int(((int(v_count) + int(bin_size) - 1) // int(bin_size)) * int(bin_size))


def _pack_part_vids_dense(
    gear_ids_np: np.ndarray,
    offsets_np: np.ndarray,
    *,
    dense_vid_universe: Optional[np.ndarray] = None,
    v_pad_bin: int = 4096,
    variant_freq_mode: str = "occurrence",
    wildcard_freq_bonus: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """
    Convert (gear_ids, offsets) to:
    - part_vids: dense IDs in [0..V-1] with shape (S, K, 6)
    - variant_freq: (V,) frequency of each dense variant in the witness pool
    - dense_vid_universe: sorted unique raw IDs (gear_id<<16 | offset) that define the dense mapping
    - v_count: padded V passed to the GPU full solver (bin-padded for kernel caching stability)
    """
    gear_ids_b = gear_ids_np[:, None, :].astype(np.int32, copy=False)
    vids = (gear_ids_b.astype(np.int32) << np.int32(16)) | offsets_np.astype(np.int32, copy=False)
    flat = vids.reshape(-1)

    if dense_vid_universe is None:
        dense_vid_universe = np.unique(flat).astype(np.int32, copy=False)
    else:
        dense_vid_universe = np.asarray(dense_vid_universe, dtype=np.int32)

    inv = np.searchsorted(dense_vid_universe, flat).astype(np.int32, copy=False)
    # `dense_vid_universe` is produced by `np.unique(...)` (sorted unique), so `searchsorted` mapping is safe.
    # Avoid validating the full mapping here; it costs ~O(S*K*6) extra work per restart.

    part_vids = inv.reshape(vids.shape).astype(np.int32, copy=False)
    v_raw = int(dense_vid_universe.size)
    v_count = _pad_v_count(v_raw, bin_size=int(v_pad_bin))

    variant_freq_mode = str(variant_freq_mode).strip().lower()
    if variant_freq_mode not in {"occurrence", "song_support"}:
        raise ValueError("variant_freq_mode must be 'occurrence' or 'song_support'.")

    if variant_freq_mode == "song_support":
        # Weight variants by the number of songs that can use them (appears in any pattern for that song).
        # This is often a better reuse proxy than raw occurrence count, which can be inflated by duplicate
        # patterns within the same song.
        variant_freq = np.zeros((v_count,), dtype=np.int32)
        flat_by_song = part_vids.reshape(int(part_vids.shape[0]), -1)
        for s_idx in range(int(flat_by_song.shape[0])):
            u = np.unique(flat_by_song[s_idx])
            variant_freq[u] += np.int32(1)
    else:
        variant_freq = np.bincount(part_vids.reshape(-1), minlength=v_count).astype(np.int32, copy=False)
    if int(wildcard_freq_bonus) != 0 and v_raw > 0:
        # Encourage reuse by slightly preferring OV==0 (color=0) variants in tie-break scoring.
        # `offset < OV0_VARIANTS` is equivalent to OV==0 by construction (see `variant_space.py`).
        from .variant_space import OV0_VARIANTS

        off = (dense_vid_universe & np.int32(0xFFFF)).astype(np.int32, copy=False)
        is_wild = np.zeros((v_count,), dtype=bool)
        is_wild[:v_raw] = off < np.int32(OV0_VARIANTS)
        variant_freq = variant_freq.copy()
        variant_freq[is_wild] = (variant_freq[is_wild] + np.int32(int(wildcard_freq_bonus))).astype(
            np.int32, copy=False
        )
    return part_vids, variant_freq, dense_vid_universe, v_count


def _pack_part_vids_dense_from_raw(
    raw_vids: np.ndarray,
    *,
    v_pad_bin: int = 4096,
    variant_freq_mode: str = "occurrence",
    wildcard_freq_bonus: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    raw_vids = np.asarray(raw_vids, dtype=np.int32)
    if raw_vids.ndim != 3 or raw_vids.shape[2] != 6:
        raise ValueError("raw_vids must have shape (S, K, 6).")

    flat = raw_vids.reshape(-1)
    dense_vid_universe = np.unique(flat).astype(np.int32, copy=False)
    inv = np.searchsorted(dense_vid_universe, flat).astype(np.int32, copy=False)
    part_vids = inv.reshape(raw_vids.shape).astype(np.int32, copy=False)

    v_raw = int(dense_vid_universe.size)
    v_count = _pad_v_count(v_raw, bin_size=int(v_pad_bin))

    variant_freq_mode = str(variant_freq_mode).strip().lower()
    if variant_freq_mode not in {"occurrence", "song_support"}:
        raise ValueError("variant_freq_mode must be 'occurrence' or 'song_support'.")

    if variant_freq_mode == "song_support":
        variant_freq = np.zeros((v_count,), dtype=np.int32)
        flat_by_song = part_vids.reshape(int(part_vids.shape[0]), -1)
        for s_idx in range(int(flat_by_song.shape[0])):
            u = np.unique(flat_by_song[s_idx])
            variant_freq[u] += np.int32(1)
    else:
        variant_freq = np.bincount(part_vids.reshape(-1), minlength=v_count).astype(np.int32, copy=False)

    if int(wildcard_freq_bonus) != 0 and v_raw > 0:
        from .variant_space import OV0_VARIANTS

        off = (dense_vid_universe & np.int32(0xFFFF)).astype(np.int32, copy=False)
        is_wild = np.zeros((v_count,), dtype=bool)
        is_wild[:v_raw] = off < np.int32(OV0_VARIANTS)
        variant_freq = variant_freq.copy()
        variant_freq[is_wild] = (variant_freq[is_wild] + np.int32(int(wildcard_freq_bonus))).astype(
            np.int32, copy=False
        )

    return part_vids, variant_freq, dense_vid_universe, v_count


def _run_gpu_full_solver_from_offsets(
    gear_ids_np: np.ndarray,
    offsets_np: np.ndarray,
    *,
    inventory_cap: int,
    seed: int,
    gpu_repack_passes: int,
    gpu_full_repack_rarity_weighted: bool,
    gpu_full_k_scan_select: int,
    gpu_full_k_scan_repack: int,
    lns_time_sec: float,
    lns_attempts: int,
    gpu_lns_destroy: int,
    gpu_full_lns_freq_weighted: bool,
    gpu_full_variant_freq_mode: str,
    gpu_full_counter_stripes: int,
    mem: _MemoryLogger,
    wp_stats: Optional[dict] = None,
    dense_vid_universe: Optional[np.ndarray] = None,
    v_pad_bin: int = 4096,
    wildcard_freq_bonus: int = 0,
):
    part_vids, variant_freq_np, dense_vid_universe, v_count = _pack_part_vids_dense(
        gear_ids_np,
        offsets_np,
        dense_vid_universe=dense_vid_universe,
        v_pad_bin=int(v_pad_bin),
        variant_freq_mode=str(gpu_full_variant_freq_mode),
        wildcard_freq_bonus=int(wildcard_freq_bonus),
    )

    mem.log(
        f"gpu_full_inputs_ready (songs={gear_ids_np.shape[0]}, k_total={int(offsets_np.shape[1])}, v={int(v_count)})"
    )
    sol_full = solve_coverage_gpu_full(
        part_vids,
        variant_freq_np,
        inventory_cap=int(inventory_cap),
        seed=int(seed),
        repack_passes=int(gpu_repack_passes),
        repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
        counter_stripes=int(gpu_full_counter_stripes),
        k_scan_select=int(gpu_full_k_scan_select),
        k_scan_repack=int(gpu_full_k_scan_repack),
        lns_time_sec=float(lns_time_sec),
        lns_attempts=int(lns_attempts),
        lns_destroy=int(gpu_lns_destroy),
        lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
        profile=bool(mem.enabled),
    )
    mem.log("gpu_full_solved")

    chosen_part = np.asarray(sol_full.chosen_part, dtype=np.int32)
    chosen_offsets = np.full((gear_ids_np.shape[0], 6), -1, dtype=np.int32)
    for s_idx in range(int(gear_ids_np.shape[0])):
        p = int(chosen_part[s_idx])
        if p >= 0:
            chosen_offsets[s_idx, :] = offsets_np[s_idx, p, :]

    covered = (chosen_part >= 0).astype(np.int32, copy=False)

    from types import SimpleNamespace

    stats = {
        "witness_pool": wp_stats,
        "gpu_full": sol_full.stats,
        "k_total": int(offsets_np.shape[1]),
        "v_count": int(v_count),
        "v_unpadded": int(dense_vid_universe.size),
    }
    return SimpleNamespace(
        covered=covered,
        chosen_offsets=chosen_offsets,
        covered_count=int(covered.sum()),
        stats=stats,
        dense_vid_universe=dense_vid_universe,
    )


def _run_gpu_full_solver_from_candidates(
    songs: List[SongSpec],
    *,
    k_total: int,
    gear_freq_np: np.ndarray,
    inventory_cap: int,
    seed: int,
    gpu_repack_passes: int,
    gpu_full_repack_rarity_weighted: bool,
    lns_time_sec: float,
    lns_attempts: int,
    gpu_lns_destroy: int,
    gpu_full_lns_freq_weighted: bool,
    gpu_full_variant_freq_mode: str,
    gpu_full_counter_stripes: int,
    gpu_full_witness_pattern_profile: int,
    gpu_full_k_scan_select: int,
    gpu_full_k_scan_repack: int,
    witness_anchor_patterns: int,
    witness_seed_streams: int,
    mem: _MemoryLogger,
    v_pad_bin: int = 4096,
    wildcard_freq_bonus: int = 0,
):
    offsets_np, part_to_candidate, wp_stats = _build_multi_candidate_offsets(
        songs,
        k_total=int(k_total),
        seed=int(seed),
        gear_freq_np=gear_freq_np,
        witness_anchor_patterns=int(witness_anchor_patterns),
        witness_seed_streams=int(witness_seed_streams),
        gpu_full_witness_pattern_profile=int(gpu_full_witness_pattern_profile),
        mem=mem,
    )

    raw_vids = np.zeros_like(offsets_np, dtype=np.int32)
    for s_idx, song in enumerate(songs):
        write_ptr = 0
        for c_idx, cand in enumerate(song.candidates):
            cand_mask = part_to_candidate[s_idx] == int(c_idx)
            count = int(np.count_nonzero(cand_mask))
            if count <= 0:
                continue
            start = int(write_ptr)
            end = start + int(count)
            write_ptr = int(end)
            gids = (np.asarray(cand.gear_ids, dtype=np.int32) << np.int32(16)).reshape(1, 6)
            raw_vids[s_idx, start:end, :] = gids | offsets_np[s_idx, start:end, :]
        if write_ptr != int(k_total):
            raise RuntimeError("Multi-candidate raw vids build mismatch.")

    part_vids, variant_freq_np, dense_vid_universe, v_count = _pack_part_vids_dense_from_raw(
        raw_vids,
        v_pad_bin=int(v_pad_bin),
        variant_freq_mode=str(gpu_full_variant_freq_mode),
        wildcard_freq_bonus=int(wildcard_freq_bonus),
    )

    mem.log(
        f"gpu_full_inputs_ready (songs={part_vids.shape[0]}, k_total={int(k_total)}, v={int(v_count)})"
    )
    sol_full = solve_coverage_gpu_full(
        part_vids,
        variant_freq_np,
        inventory_cap=int(inventory_cap),
        seed=int(seed),
        repack_passes=int(gpu_repack_passes),
        repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
        counter_stripes=int(gpu_full_counter_stripes),
        k_scan_select=int(gpu_full_k_scan_select),
        k_scan_repack=int(gpu_full_k_scan_repack),
        lns_time_sec=float(lns_time_sec),
        lns_attempts=int(lns_attempts),
        lns_destroy=int(gpu_lns_destroy),
        lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
        profile=bool(mem.enabled),
    )
    mem.log("gpu_full_solved")

    chosen_part = np.asarray(sol_full.chosen_part, dtype=np.int32)
    chosen_offsets = np.full((len(songs), 6), -1, dtype=np.int32)
    chosen_candidate_idx = np.full((len(songs),), -1, dtype=np.int32)
    for s_idx in range(int(len(songs))):
        p = int(chosen_part[s_idx])
        if p >= 0:
            chosen_offsets[s_idx, :] = offsets_np[s_idx, p, :]
            chosen_candidate_idx[s_idx] = int(part_to_candidate[s_idx, p])

    covered = (chosen_part >= 0).astype(np.int32, copy=False)

    from types import SimpleNamespace

    stats = {
        "witness_pool": wp_stats,
        "gpu_full": sol_full.stats,
        "k_total": int(k_total),
        "v_count": int(v_count),
        "v_unpadded": int(dense_vid_universe.size),
        "multi_candidate": {
            "enabled": True,
            "candidates_per_song": wp_stats.get("candidates_per_song"),
        },
    }
    return SimpleNamespace(
        covered=covered,
        chosen_offsets=chosen_offsets,
        covered_count=int(covered.sum()),
        stats=stats,
        dense_vid_universe=dense_vid_universe,
        chosen_candidate_idx=chosen_candidate_idx,
    )


def _run_gpu_full_solver_multi_seed(
    gear_ids_np: np.ndarray,
    totals_np: np.ndarray,
    elements_np: np.ndarray,
    gear_freq_np: np.ndarray,
    *,
    inventory_cap: int,
    seeds: List[int],
    k_total: int,
    gpu_repack_passes: int,
    lns_time_sec: float,
    lns_attempts: int,
    gpu_lns_destroy: int,
    mem: _MemoryLogger,
    v_pad_bin: int = 4096,
    wildcard_freq_bonus: int = 0,
    witness_anchor_patterns: int = 24,
    witness_seed_streams: int = 4,
    gpu_full_repack_rarity_weighted: bool = False,
    gpu_full_lns_freq_weighted: bool = False,
    gpu_full_variant_freq_mode: str = "occurrence",
    gpu_full_witness_pattern_profile: int = 0,
    gpu_full_counter_stripes: int = 1,
    gpu_full_k_scan_select: int = 0,
    gpu_full_k_scan_repack: int = 0,
):
    if not seeds:
        raise ValueError("seeds must be non-empty.")

    offsets_by_seed: Dict[int, np.ndarray] = {}
    wp_stats_by_seed: Dict[int, dict] = {}
    flats: List[np.ndarray] = []

    gear_ids_b = gear_ids_np[:, None, :].astype(np.int32, copy=False)
    for s in seeds:
        offsets_np, wp_stats = build_witness_offsets_gpu(
            gear_ids_np,
            totals_np,
            elements_np,
            gear_freq_np,
            k_total=int(k_total),
            seed=int(s),
            anchor_patterns=int(witness_anchor_patterns),
            seed_streams=int(witness_seed_streams),
            pattern_profile=int(gpu_full_witness_pattern_profile),
            profile=bool(mem.enabled),
        )
        offsets_by_seed[int(s)] = offsets_np
        wp_stats_by_seed[int(s)] = wp_stats
        vids = (gear_ids_b.astype(np.int32) << np.int32(16)) | offsets_np.astype(np.int32, copy=False)
        flats.append(vids.reshape(-1).astype(np.int32, copy=False))

    mem.log(f"gpu_full_witness_pools_built (count={len(seeds)})")

    dense_vid_universe = np.unique(np.concatenate(flats, axis=0)).astype(np.int32, copy=False)
    v_raw = int(dense_vid_universe.size)
    v_count = _pad_v_count(v_raw, bin_size=int(v_pad_bin))
    mem.log(f"gpu_full_union_vids_ready (v_unpadded={v_raw}, v_padded={v_count})")

    best_sol = None
    best_cov = -1
    best_used = 10**9
    best_seed = int(seeds[0])
    per_seed: List[dict] = []
    for s in seeds:
        sol = _run_gpu_full_solver_from_offsets(
            gear_ids_np,
            offsets_by_seed[int(s)],
            inventory_cap=int(inventory_cap),
            seed=int(s),
            gpu_repack_passes=int(gpu_repack_passes),
            gpu_full_repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
            gpu_full_k_scan_select=int(gpu_full_k_scan_select),
            gpu_full_k_scan_repack=int(gpu_full_k_scan_repack),
            lns_time_sec=float(lns_time_sec),
            lns_attempts=int(lns_attempts),
            gpu_lns_destroy=int(gpu_lns_destroy),
            gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
            gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
            gpu_full_counter_stripes=int(gpu_full_counter_stripes),
            mem=mem,
            wp_stats=wp_stats_by_seed[int(s)],
            dense_vid_universe=dense_vid_universe,
            v_pad_bin=int(v_pad_bin),
            wildcard_freq_bonus=int(wildcard_freq_bonus),
        )
        covered_np = np.asarray(sol.covered, dtype=np.int32)
        chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)
        used = _count_used_gear_variants(gear_ids_np, covered_np, chosen_offsets_np)
        cov = int(sol.covered_count)
        # Snapshot stats now; do not retain a reference to `sol.stats` because we mutate the best solution's stats
        # with a multi-seed summary (would create a circular structure when serializing).
        per_seed.append({"seed": int(s), "covered": int(cov), "used": int(used), "stats": dict(sol.stats)})
        if (cov > best_cov) or (cov == best_cov and used < best_used):
            best_cov = cov
            best_used = used
            best_sol = sol
            best_seed = int(s)

    assert best_sol is not None
    best_sol.stats["multi_seed"] = {
        "seeds": [int(s) for s in seeds],
        "v_unpadded": int(v_raw),
        "v_padded": int(v_count),
        "per_seed": per_seed,
        "best_seed": int(best_seed),
    }
    return best_sol, int(best_seed)


def run_inventory_meta_coverage(
    *,
    inventory_cap: int = 100,
    partitions_per_song: int = 32,
    seed: int = 1,
    restarts: int = 1,
    gpu_repack_passes: int = 3,
    gpu_lns_destroy: int = 6,
    adaptive_rounds: int = 3,
    adaptive_patterns_per_round: int = 64,
    adaptive_keep_per_song: int = 8,
    adaptive_repack_songs: int = 256,
    lns_time_sec: float = 0.0,
    lns_attempts: int = 200,
    song_limit: Optional[int] = None,
    profile: bool = False,
    solver: str = "gpu_dynamic",
    eda_witnesses_per_song: int = 16,
    eda_population: int = 64,
    eda_iterations: int = 20,
    eda_elites: int = 8,
    eda_alpha: float = 0.25,
    eda_wildcard_bonus: float = 0.03,
    gpu_full_wildcard_freq_bonus: int = 0,
    gpu_full_witness_anchor_patterns: int = 24,
    gpu_full_witness_seed_streams: int = 4,
    gpu_full_repack_rarity_weighted: bool = False,
    gpu_full_lns_freq_weighted: bool = False,
    gpu_full_v_pad_bin: int = 4096,
    gpu_full_variant_freq_mode: str = "occurrence",
    gpu_full_witness_pattern_profile: int = 0,
    gpu_full_counter_stripes: int = 1,
    gpu_full_witness_palettes: int = 1,
    gpu_full_top_candidates: int = 1,
    gpu_full_candidate_score_delta: int = 0,
    gpu_full_candidate_limit_per_song: int = 0,
    gpu_full_k_scan_select: int = 0,
    gpu_full_k_scan_repack: int = 0,
) -> dict:
    """
    Inventory Meta coverage mode (GPU-only optimization loop):
    - Picks ONE peak row per song (top peak; tie broken deterministically).
    - For `gpu_full` with `gpu_full_top_candidates > 1`, it selects multiple top candidates per song
      and lets the GPU choose among them within a fixed per-song witness budget.
    - If `gpu_full_candidate_score_delta > 0`, the candidate pool is widened to rows within that delta of peak
      (approximate coverage experiment; no longer exact-peak-only).
    - Solves coverage without per-song pattern caps (dynamic per-slot gem partitioning on GPU).
    Minis are not constrained; duplicates are ignored.

    Notes:
    - For `solver='gpu_full'`, `K_total = partitions_per_song + adaptive_rounds * adaptive_keep_per_song`.
    - For other solvers, `partitions_per_song` and `adaptive_*` are legacy arguments kept for CLI compatibility.
    """
    inventory_cap = int(inventory_cap)
    if inventory_cap <= 0:
        raise ValueError("inventory_cap must be positive.")
    restarts = int(restarts)
    if restarts <= 0:
        raise ValueError("restarts must be positive.")
    gpu_repack_passes = int(gpu_repack_passes)
    if gpu_repack_passes < 0:
        raise ValueError("gpu_repack_passes must be >= 0.")
    gpu_lns_destroy = int(gpu_lns_destroy)
    if gpu_lns_destroy < 0:
        raise ValueError("gpu_lns_destroy must be >= 0.")
    lns_time_sec = float(lns_time_sec)
    if lns_time_sec < 0:
        raise ValueError("lns_time_sec must be >= 0.")
    lns_attempts = int(lns_attempts)
    if lns_attempts <= 0:
        raise ValueError("lns_attempts must be positive.")
    gpu_full_witness_anchor_patterns = int(gpu_full_witness_anchor_patterns)
    if gpu_full_witness_anchor_patterns < 0:
        raise ValueError("gpu_full_witness_anchor_patterns must be >= 0.")
    gpu_full_witness_seed_streams = int(gpu_full_witness_seed_streams)
    if gpu_full_witness_seed_streams <= 0:
        raise ValueError("gpu_full_witness_seed_streams must be positive.")
    gpu_full_v_pad_bin = int(gpu_full_v_pad_bin)
    if gpu_full_v_pad_bin <= 0:
        raise ValueError("gpu_full_v_pad_bin must be positive.")
    gpu_full_variant_freq_mode = str(gpu_full_variant_freq_mode).strip().lower()
    if gpu_full_variant_freq_mode not in {"occurrence", "song_support"}:
        raise ValueError("gpu_full_variant_freq_mode must be 'occurrence' or 'song_support'.")
    gpu_full_repack_rarity_weighted = bool(gpu_full_repack_rarity_weighted)
    gpu_full_witness_pattern_profile = int(gpu_full_witness_pattern_profile)
    if gpu_full_witness_pattern_profile < 0:
        raise ValueError("gpu_full_witness_pattern_profile must be >= 0.")
    gpu_full_counter_stripes = int(gpu_full_counter_stripes)
    if gpu_full_counter_stripes <= 0:
        raise ValueError("gpu_full_counter_stripes must be positive.")
    gpu_full_witness_palettes = int(gpu_full_witness_palettes)
    if gpu_full_witness_palettes <= 0:
        raise ValueError("gpu_full_witness_palettes must be positive.")
    gpu_full_top_candidates = int(gpu_full_top_candidates)
    if gpu_full_top_candidates <= 0:
        raise ValueError("gpu_full_top_candidates must be positive.")
    gpu_full_candidate_score_delta = int(gpu_full_candidate_score_delta)
    if gpu_full_candidate_score_delta < 0:
        raise ValueError("gpu_full_candidate_score_delta must be >= 0.")
    gpu_full_candidate_limit_per_song = int(gpu_full_candidate_limit_per_song)
    if gpu_full_candidate_limit_per_song < 0:
        raise ValueError("gpu_full_candidate_limit_per_song must be >= 0.")
    gpu_full_k_scan_select = int(gpu_full_k_scan_select)
    if gpu_full_k_scan_select < 0:
        raise ValueError("gpu_full_k_scan_select must be >= 0.")
    gpu_full_k_scan_repack = int(gpu_full_k_scan_repack)
    if gpu_full_k_scan_repack < 0:
        raise ValueError("gpu_full_k_scan_repack must be >= 0.")

    solver = str(solver or "gpu_dynamic").strip().lower()
    if solver not in {"gpu_dynamic", "gpu_eda", "gpu_full"}:
        raise ValueError("solver must be one of: gpu_dynamic, gpu_eda, gpu_full")

    mem = _MemoryLogger(enabled=bool(profile))
    mem.log("start")

    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Evolution DB not found: {db_path}")

    conn = get_db_connection(db_path)
    try:
        mem.log("db_connected")
        song_peak_by_name: Optional[Dict[str, int]] = None
        if song_limit is not None:
            song_names = fetch_song_names_limited(conn, int(song_limit))
            candidates_by_song: Dict[str, List[SongCandidate]] = {}
            missing: List[str] = []
            song_peak_by_name = {}
            for name in song_names:
                peak, base_peak, fg_peak = fetch_song_peak(conn, name)
                song_peak_by_name[str(name)] = int(peak)
                cands = fetch_candidates_for_peak(conn, name, peak, base_peak, fg_peak)
                if not cands:
                    missing.append(name)
                    continue
                candidates_by_song[name] = cands
        else:
            if solver == "gpu_full" and int(gpu_full_candidate_score_delta) > 0:
                lim = int(gpu_full_candidate_limit_per_song)
                if lim <= 0:
                    lim = max(50, int(gpu_full_top_candidates) * 10)
                candidates_by_song, missing = fetch_candidates_within_delta_allow_missing(
                    conn,
                    score_delta=int(gpu_full_candidate_score_delta),
                    limit_per_song=int(lim),
                )
                song_peak_by_name = None  # will be re-derived lazily from selected candidates
            else:
                candidates_by_song, missing = fetch_peak_candidates_allow_missing(conn)
    finally:
        conn.close()
        mem.log("db_closed")

    if not candidates_by_song:
        raise ValueError("No candidates found in loadouts/fg_loadouts.")

    gear_names = _collect_gear_names(candidates_by_song)
    gear_id_map = {name: idx + 1 for idx, name in enumerate(gear_names)}

    mini_names = _collect_mini_names(candidates_by_song)
    mini_id_map = {name: idx for idx, name in enumerate(mini_names)}

    song_specs = _build_song_specs(candidates_by_song, gear_id_map, mini_id_map)
    mem.log(f"song_specs_built (songs={len(song_specs)}, missing={len(missing)})")

    selected_specs = _select_one_peak_candidate_per_song(song_specs)
    mem.log("selected_one_candidate_per_song")

    use_multi_candidates = solver == "gpu_full" and gpu_full_top_candidates > 1
    selected_multi_specs: Optional[List[SongSpec]] = None
    gear_ids_np = totals_np = elements_np = gear_freq_np = None
    if use_multi_candidates:
        k_total = int(partitions_per_song) + int(adaptive_rounds) * int(adaptive_keep_per_song)
        k_total = max(int(partitions_per_song), int(k_total))
        max_candidates = min(int(gpu_full_top_candidates), int(k_total))
        selected_multi_specs = _select_top_k_candidates_per_song(
            song_specs,
            k_candidates=max_candidates,
            song_peak_by_name=song_peak_by_name,
        )
        mem.log(f"selected_top_candidates_per_song (k={int(max_candidates)})")
        gear_freq_np = _build_candidate_gear_freq(selected_multi_specs, gear_count=len(gear_names))
    else:
        gear_ids_np, totals_np, elements_np, gear_freq_np = _build_gpu_dynamic_inputs(
            selected_specs, gear_names=gear_names
        )
        mem.log("gpu_dynamic_inputs_built")

    legacy_args = {
        "partitions_per_song": int(partitions_per_song),
        "adaptive_rounds": int(adaptive_rounds),
        "adaptive_patterns_per_round": int(adaptive_patterns_per_round),
        "adaptive_keep_per_song": int(adaptive_keep_per_song),
        "adaptive_repack_songs": int(adaptive_repack_songs),
        "gpu_full_top_candidates": int(gpu_full_top_candidates),
        "gpu_full_candidate_score_delta": int(gpu_full_candidate_score_delta),
        "gpu_full_candidate_limit_per_song": int(gpu_full_candidate_limit_per_song),
        "gpu_full_k_scan_select": int(gpu_full_k_scan_select),
        "gpu_full_k_scan_repack": int(gpu_full_k_scan_repack),
        "gpu_full_witness_palettes": int(gpu_full_witness_palettes),
    }

    best_seed: Optional[int] = None
    best_sol = None
    best_cov = -1
    best_used = 10**9
    best_chosen_candidate_idx: Optional[np.ndarray] = None
    base_seed = int(seed)
    if base_seed == 0:
        base_seed = int(time.time_ns() & 0x7FFFFFFF) or 1

    # `gpu_full` supports a multi-seed path that avoids repeated Taichi recompiles by using a
    # single dense variant universe (`V`) across all restarts.
    if solver == "gpu_full" and restarts > 1 and not use_multi_candidates:
        seeds = [int(base_seed) + r for r in range(int(restarts))]
        if profile:
            mem.log(f"gpu_full_multi_seed (restarts={int(restarts)})")
        k_total = int(partitions_per_song) + int(adaptive_rounds) * int(adaptive_keep_per_song)
        k_total = max(int(partitions_per_song), int(k_total))
        best_sol, best_seed = _run_gpu_full_solver_multi_seed(
            gear_ids_np,
            totals_np,
            elements_np,
            gear_freq_np,
            inventory_cap=int(inventory_cap),
            seeds=seeds,
            k_total=int(k_total),
            gpu_repack_passes=int(gpu_repack_passes),
            lns_time_sec=float(lns_time_sec),
            lns_attempts=int(lns_attempts),
            gpu_lns_destroy=int(gpu_lns_destroy),
            mem=mem,
            wildcard_freq_bonus=int(gpu_full_wildcard_freq_bonus),
            witness_anchor_patterns=int(gpu_full_witness_anchor_patterns),
            witness_seed_streams=int(gpu_full_witness_seed_streams),
            gpu_full_repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
            gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
            v_pad_bin=int(gpu_full_v_pad_bin),
            gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
            gpu_full_witness_pattern_profile=int(gpu_full_witness_pattern_profile),
            gpu_full_counter_stripes=int(gpu_full_counter_stripes),
            gpu_full_k_scan_select=int(gpu_full_k_scan_select),
            gpu_full_k_scan_repack=int(gpu_full_k_scan_repack),
        )
    else:
        for r in range(restarts):
            run_seed = int(base_seed) + r
            if profile and restarts > 1:
                mem.log(f"restart_{r + 1}_of_{restarts} (seed={run_seed})")
            if solver == "gpu_dynamic":
                if gear_ids_np is None or totals_np is None or elements_np is None or gear_freq_np is None:
                    raise RuntimeError("GPU dynamic inputs not initialized.")
                sol = _run_gpu_dynamic_solver(
                    gear_ids_np,
                    totals_np,
                    elements_np,
                    gear_freq_np,
                    inventory_cap=inventory_cap,
                    seed=run_seed,
                    gpu_repack_passes=gpu_repack_passes,
                    gpu_lns_destroy=gpu_lns_destroy,
                    lns_time_sec=lns_time_sec,
                    lns_attempts=lns_attempts,
                    mem=mem,
                )
                covered_np = np.asarray(sol.covered, dtype=np.int32)
                chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)
                used = _count_used_gear_variants(gear_ids_np, covered_np, chosen_offsets_np)
            elif solver == "gpu_eda":
                if gear_ids_np is None or totals_np is None or elements_np is None or gear_freq_np is None:
                    raise RuntimeError("GPU EDA inputs not initialized.")
                # Seed the witness pool with a strong baseline (gpu_dynamic) so EDA doesn't start from noise.
                baseline = _run_gpu_dynamic_solver(
                    gear_ids_np,
                    totals_np,
                    elements_np,
                    gear_freq_np,
                    inventory_cap=inventory_cap,
                    seed=run_seed,
                    gpu_repack_passes=gpu_repack_passes,
                    gpu_lns_destroy=gpu_lns_destroy,
                    lns_time_sec=0.0,
                    lns_attempts=lns_attempts,
                    mem=mem,
                )
                sol_eda = _run_gpu_eda_solver(
                    gear_ids_np,
                    totals_np,
                    elements_np,
                    gear_freq_np,
                    inventory_cap=inventory_cap,
                    seed=run_seed,
                    witnesses_per_song=int(eda_witnesses_per_song),
                    population=int(eda_population),
                    iterations=int(eda_iterations),
                    elites=int(eda_elites),
                    alpha=float(eda_alpha),
                    wildcard_bonus=float(eda_wildcard_bonus),
                    seed_witness_offsets=np.asarray(baseline.chosen_offsets, dtype=np.int32),
                    mem=mem,
                )
                # Never regress relative to the baseline dynamic solver for the same seed.
                sol = sol_eda
                if int(baseline.covered_count) > int(sol_eda.covered_count):
                    sol = baseline
                elif int(baseline.covered_count) == int(sol_eda.covered_count):
                    b_used = _count_used_gear_variants(
                        gear_ids_np,
                        np.asarray(baseline.covered, dtype=np.int32),
                        np.asarray(baseline.chosen_offsets, dtype=np.int32),
                    )
                    e_used = _count_used_gear_variants(
                        gear_ids_np,
                        np.asarray(sol_eda.covered, dtype=np.int32),
                        np.asarray(sol_eda.chosen_offsets, dtype=np.int32),
                    )
                    if b_used <= e_used:
                        sol = baseline
                covered_np = np.asarray(sol.covered, dtype=np.int32)
                chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)
                used = _count_used_gear_variants(gear_ids_np, covered_np, chosen_offsets_np)
            else:
                k_total = int(partitions_per_song) + int(adaptive_rounds) * int(adaptive_keep_per_song)
                k_total = max(int(partitions_per_song), int(k_total))
                if use_multi_candidates:
                    if selected_multi_specs is None or gear_freq_np is None:
                        raise RuntimeError("Multi-candidate inputs not initialized.")
                    sol = _run_gpu_full_solver_from_candidates(
                        selected_multi_specs,
                        k_total=int(k_total),
                        gear_freq_np=gear_freq_np,
                        inventory_cap=int(inventory_cap),
                        seed=int(run_seed),
                        gpu_repack_passes=int(gpu_repack_passes),
                        gpu_full_repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
                        gpu_full_k_scan_select=int(gpu_full_k_scan_select),
                        gpu_full_k_scan_repack=int(gpu_full_k_scan_repack),
                        lns_time_sec=float(lns_time_sec),
                        lns_attempts=int(lns_attempts),
                        gpu_lns_destroy=int(gpu_lns_destroy),
                        gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
                        gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
                        gpu_full_counter_stripes=int(gpu_full_counter_stripes),
                        gpu_full_witness_pattern_profile=int(gpu_full_witness_pattern_profile),
                        witness_anchor_patterns=int(gpu_full_witness_anchor_patterns),
                        witness_seed_streams=int(gpu_full_witness_seed_streams),
                        mem=mem,
                        v_pad_bin=int(gpu_full_v_pad_bin),
                        wildcard_freq_bonus=int(gpu_full_wildcard_freq_bonus),
                    )
                    covered_np = np.asarray(sol.covered, dtype=np.int32)
                    chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)
                    chosen_candidate_idx = np.asarray(sol.chosen_candidate_idx, dtype=np.int32)
                    used = _count_used_gear_variants_multi(
                        selected_multi_specs, covered_np, chosen_offsets_np, chosen_candidate_idx
                    )
                else:
                    if gear_ids_np is None or totals_np is None or elements_np is None or gear_freq_np is None:
                        raise RuntimeError("GPU full inputs not initialized.")
                    sol = _run_gpu_full_solver_from_witness_pool(
                        gear_ids_np,
                        totals_np,
                        elements_np,
                        gear_freq_np,
                        inventory_cap=int(inventory_cap),
                        seed=int(run_seed),
                        k_total=int(k_total),
                        gpu_repack_passes=int(gpu_repack_passes),
                        gpu_full_repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
                        lns_time_sec=float(lns_time_sec),
                        lns_attempts=int(lns_attempts),
                        gpu_lns_destroy=int(gpu_lns_destroy),
                        gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
                        gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
                        gpu_full_counter_stripes=int(gpu_full_counter_stripes),
                        gpu_full_witness_pattern_profile=int(gpu_full_witness_pattern_profile),
                        gpu_full_k_scan_select=int(gpu_full_k_scan_select),
                        gpu_full_k_scan_repack=int(gpu_full_k_scan_repack),
                        gpu_full_witness_palettes=int(gpu_full_witness_palettes),
                        mem=mem,
                        v_pad_bin=int(gpu_full_v_pad_bin),
                        wildcard_freq_bonus=int(gpu_full_wildcard_freq_bonus),
                        witness_anchor_patterns=int(gpu_full_witness_anchor_patterns),
                        witness_seed_streams=int(gpu_full_witness_seed_streams),
                    )
                    covered_np = np.asarray(sol.covered, dtype=np.int32)
                    chosen_offsets_np = np.asarray(sol.chosen_offsets, dtype=np.int32)
                    used = _count_used_gear_variants(gear_ids_np, covered_np, chosen_offsets_np)

            cov = int(sol.covered_count)
            if (cov > best_cov) or (cov == best_cov and used < best_used):
                best_cov = cov
                best_used = used
                best_sol = sol
                best_seed = run_seed
                if use_multi_candidates:
                    best_chosen_candidate_idx = np.asarray(sol.chosen_candidate_idx, dtype=np.int32)

    assert best_sol is not None
    if solver == "gpu_dynamic":
        mode = "coverage_gpu_dynamic"
        status = "GPU_DYNAMIC_HEURISTIC"
    elif solver == "gpu_eda":
        mode = "coverage_gpu_eda"
        status = "GPU_EDA_HEURISTIC"
    else:
        mode = "coverage_gpu_full"
        status = "GPU_FULL_HEURISTIC"

    if use_multi_candidates:
        if selected_multi_specs is None or best_chosen_candidate_idx is None:
            raise RuntimeError("Multi-candidate materialization inputs missing.")
        result = _materialize_coverage_solution_multi(
            selected_multi_specs,
            gear_names=gear_names,
            sol=best_sol,
            chosen_candidate_idx=best_chosen_candidate_idx,
            mode=mode,
            solver_status=status,
            inventory_cap=inventory_cap,
            seed=int(best_seed or seed),
            gpu_repack_passes=gpu_repack_passes,
            gpu_lns_destroy=gpu_lns_destroy,
            lns_time_sec=lns_time_sec,
            lns_attempts=lns_attempts,
            mem=mem,
            legacy_args=legacy_args,
        )
    else:
        if gear_ids_np is None:
            raise RuntimeError("Gear IDs not initialized for materialization.")
        result = _materialize_coverage_solution(
            selected_specs,
            gear_names=gear_names,
            gear_ids_np=gear_ids_np,
            sol=best_sol,
            mode=mode,
            solver_status=status,
            inventory_cap=inventory_cap,
            seed=int(best_seed or seed),
            gpu_repack_passes=gpu_repack_passes,
            gpu_lns_destroy=gpu_lns_destroy,
            lns_time_sec=lns_time_sec,
            lns_attempts=lns_attempts,
            mem=mem,
            legacy_args=legacy_args,
        )

    result.setdefault("solver_stats", {})["restarts"] = int(restarts)
    result.setdefault("solver_stats", {})["seed"] = int(seed)
    result.setdefault("solver_stats", {})["best_seed"] = best_seed
    result["missing_songs"] = missing
    result["db_path"] = db_path
    result["generated_at"] = datetime.now().isoformat()

    hydrate_force_details(result, db_path=db_path)

    if mem.enabled:
        result["profiling"] = {"memory": mem.records}
    return result


__all__ = ["export_inventory_meta_json", "run_inventory_meta_coverage"]
