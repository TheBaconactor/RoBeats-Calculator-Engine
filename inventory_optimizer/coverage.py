from __future__ import annotations

import os
import random
import sys
import time
import zlib
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

from .db import (
    fetch_candidates_for_peak,
    fetch_peak_candidates_allow_missing,
    fetch_song_names_limited,
    fetch_song_peak,
)
from .export import export_inventory_meta_json, hydrate_force_details
from .gpu_dynamic_solver import solve_coverage_gpu_dynamic
from .gpu_eda_solver import solve_coverage_gpu_eda
from .gpu_full_solver import solve_coverage_gpu_full
from .gpu_inventory_repair import repair_uncovered_with_inventory_gpu
from .gpu_witness_pool import build_witness_offsets_gpu
from .keys import ELEMENT_TO_ID, ID_TO_ELEMENT, OV_INDEX, STAT_KEYS
from .models import CandidateSpec, SongCandidate, SongSpec
from .seed_inventory import ALLOWED_UPGRADE_IDS, UPGRADE_ID_TO_ELEMENT, UPGRADE_ID_TO_STAT, normalize_for_lookup
from .seed_inventory import SeedInventoryResult, build_seeded_inventory_variants
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


@lru_cache(maxsize=1)
def _offset_lookup() -> Dict[Tuple[int, ...], int]:
    gems, colors = build_variant_offset_tables()
    lookup: Dict[Tuple[int, ...], int] = {}
    for idx in range(int(gems.shape[0])):
        vec = gems[idx]
        key = (
            int(vec[0]),
            int(vec[1]),
            int(vec[2]),
            int(vec[3]),
            int(vec[4]),
            int(vec[5]),
            int(colors[idx]),
        )
        lookup[key] = int(idx)
    return lookup


def _extract_upgrade_ids(entry: Any) -> List[int]:
    upgrades_raw = entry.get("upgrades") if isinstance(entry, dict) else None
    if not isinstance(upgrades_raw, list):
        return []
    upgrade_ids: List[int] = []
    for upgrade in upgrades_raw:
        upgrade_id = None
        if isinstance(upgrade, dict):
            upgrade_id = upgrade.get("upgradeId")
        elif isinstance(upgrade, int):
            upgrade_id = upgrade
        if upgrade_id is None:
            continue
        try:
            upgrade_id_int = int(upgrade_id)
        except Exception:
            continue
        if upgrade_id_int in ALLOWED_UPGRADE_IDS:
            upgrade_ids.append(upgrade_id_int)
    return upgrade_ids


_ELEMENT_BY_LOWER: Dict[str, str] = {str(k).strip().lower(): str(k) for k in ELEMENT_TO_ID.keys()}


def _normalize_element_filter(value: Any) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() == "all":
        return None
    canonical = _ELEMENT_BY_LOWER.get(cleaned.lower())
    if canonical:
        return canonical
    if cleaned in ELEMENT_TO_ID:
        return cleaned
    return None


def _raw_vid_for_variant_dict(variant: Dict[str, Any], gear_id_map: Dict[str, int]) -> Optional[int]:
    gear_name = str(variant.get("gear_name") or "").strip()
    if not gear_name:
        return None
    gid = gear_id_map.get(gear_name)
    if gid is None:
        return None

    gems = variant.get("gems")
    if not isinstance(gems, dict):
        return None

    counts = [0] * len(STAT_KEYS)
    for i, key in enumerate(STAT_KEYS):
        try:
            counts[i] = int(gems.get(key) or 0)
        except Exception:
            counts[i] = 0

    ov = int(counts[OV_INDEX])
    color_id = 0
    if ov > 0:
        ov_color = str(variant.get("ov_color") or "").strip()
        color_id = int(ELEMENT_TO_ID.get(ov_color, 0) or 0)
    key = (counts[0], counts[1], counts[2], counts[3], counts[4], counts[5], int(color_id))
    off = _offset_lookup().get(key)
    if off is None:
        return None
    return (int(gid) << 16) | int(off)


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
    seed: int | None = None,
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
    seed_int = None
    if seed is not None:
        try:
            seed_int = int(seed)
        except Exception:
            seed_int = None

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
            # Keep the best candidate deterministic, then add a small number of diverse alternatives.
            # This helps coverage under a hard inventory cap by allowing "stat shifting" candidates
            # that still hit peak for a song but unlock reuse across other songs.
            if seed_int is None:
                ranked = ranked[:k_candidates]
            else:
                def _pair_distance(a: CandidateSpec, b: CandidateSpec) -> int:
                    gear_diff = 0
                    for j in range(6):
                        if int(a.gear_ids[j]) != int(b.gear_ids[j]):
                            gear_diff += 1
                    ta = a.candidate.gem_totals
                    tb = b.candidate.gem_totals
                    l1 = 0
                    for j in range(6):
                        l1 += abs(int(ta[j]) - int(tb[j]))
                    return int(gear_diff * 50 + l1)

                top = ranked[0]
                chosen: List[CandidateSpec] = [top]
                chosen_ids = {id(top)}

                pool_limit = min(len(ranked), max(32, int(k_candidates) * 16))
                pool = list(enumerate(ranked[1:pool_limit], start=1))

                salt = zlib.crc32(song.name.encode("utf-8")) & 0xFFFFFFFF
                for _ in range(int(k_candidates) - 1):
                    if not pool:
                        break
                    best_i = -1
                    best_key: Optional[Tuple[int, int, int]] = None
                    for i, (rank_pos, cand) in enumerate(pool):
                        if id(cand) in chosen_ids:
                            continue
                        min_dist = min(_pair_distance(cand, prev) for prev in chosen)
                        tie = zlib.crc32(f"{cand.candidate.rowid}:{rank_pos}".encode("utf-8")) & 0xFFFFFFFF
                        # Prefer large distance, then better rank, then a stable seeded tie-break.
                        key = (int(min_dist), int(-rank_pos), int((int(seed_int) ^ int(salt) ^ int(tie)) & 0xFFFFFFFF))
                        if best_key is None or key > best_key:
                            best_key = key
                            best_i = i
                    if best_i < 0:
                        break
                    _pos, picked = pool.pop(best_i)
                    chosen.append(picked)
                    chosen_ids.add(id(picked))

                if len(chosen) < int(k_candidates):
                    for cand in ranked[1:]:
                        if id(cand) in chosen_ids:
                            continue
                        chosen.append(cand)
                        chosen_ids.add(id(cand))
                        if len(chosen) >= int(k_candidates):
                            break

                ranked = chosen[:k_candidates]
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
            "mini_groups": [list(group) for group in cand.mini_groups],
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


def _try_inventory_repair(
    *,
    songs: List[_CoverageSong],
    gear_ids_np: np.ndarray,
    totals_np: np.ndarray,
    elements_np: np.ndarray,
    covered_np: np.ndarray,
    chosen_offsets_np: np.ndarray,
    inv_cap: int,
    attempts: int,
    seed: int,
    max_cands_per_slot: int,
    song_limit: int,
    mem: _MemoryLogger,
    profile: bool,
    seeded_pairs: Optional[Iterable[Tuple[int, int]]] = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Try to cover additional songs using ONLY variants already in the current inventory.

    This does not change inventory size and preserves "exact peak" constraints (we only change per-slot offsets).
    """
    if max_cands_per_slot <= 0:
        raise ValueError("max_cands_per_slot must be positive.")
    song_limit = int(song_limit)
    if song_limit < 0:
        raise ValueError("song_limit must be >= 0.")

    # Build inventory variant list from currently covered songs.
    used_pairs_set: set[Tuple[int, int]] = set()
    for s_idx, is_cov in enumerate(covered_np.tolist()):
        if int(is_cov) <= 0:
            continue
        for j in range(6):
            used_pairs_set.add((int(gear_ids_np[s_idx, j]), int(chosen_offsets_np[s_idx, j])))
    if seeded_pairs:
        for gid, off in seeded_pairs:
            used_pairs_set.add((int(gid), int(off)))

    used_pairs = sorted(used_pairs_set)
    if len(used_pairs) > int(inv_cap):
        raise RuntimeError("Repair invariant violated: inventory exceeds cap.")
    if not used_pairs:
        return covered_np, chosen_offsets_np, {"enabled": True, "repaired": 0, "time_sec": 0.0, "attempts": int(attempts)}

    offset_gems_np, offset_color_np = build_variant_offset_tables()

    inv_gear_ids = np.asarray([p[0] for p in used_pairs], dtype=np.int32)
    inv_offsets = np.asarray([p[1] for p in used_pairs], dtype=np.int32)
    inv_gems = offset_gems_np[inv_offsets].astype(np.int32, copy=False)
    inv_color = offset_color_np[inv_offsets].astype(np.int32, copy=False)

    # Precompute per-song-slot candidate lists into inventory indices.
    S = int(gear_ids_np.shape[0])
    C = int(max_cands_per_slot)
    cand_idx = np.full((S, 6, C), -1, dtype=np.int32)
    cand_count = np.zeros((S, 6), dtype=np.int32)

    # Group inventory indices by (gear_id, color_id) for faster fill.
    by_key: Dict[Tuple[int, int], List[int]] = {}
    for idx in range(int(inv_gear_ids.shape[0])):
        gid = int(inv_gear_ids[idx])
        col = int(inv_color[idx])
        by_key.setdefault((gid, col), []).append(int(idx))

    for s_idx in range(S):
        if int(covered_np[s_idx]) != 0:
            continue
        elem = int(elements_np[s_idx])
        for slot in range(6):
            gid = int(gear_ids_np[s_idx, slot])
            # Candidates can be OV==0 (color=0) or OV>0 matching element.
            inds = by_key.get((gid, 0), []) + by_key.get((gid, elem), [])
            if not inds:
                cand_count[s_idx, slot] = 0
                continue
            # Truncate; prefer larger OV and overall fill to make exact matching more likely.
            inds_sorted = sorted(
                inds,
                key=lambda i: (
                    int(inv_gems[i, OV_INDEX]),
                    int(inv_gems[i, 0] + inv_gems[i, 1] + inv_gems[i, 2] + inv_gems[i, 3] + inv_gems[i, 4]),
                ),
                reverse=True,
            )
            take = min(C, len(inds_sorted))
            cand_idx[s_idx, slot, :take] = np.asarray(inds_sorted[:take], dtype=np.int32)
            cand_count[s_idx, slot] = int(take)

    eligible: List[int] = []
    comb_scores: List[Tuple[int, int]] = []
    for s_idx in range(S):
        if int(covered_np[s_idx]) != 0:
            continue
        cc = cand_count[s_idx]
        if int(cc.min()) <= 0:
            continue
        comb = 1
        for j in range(6):
            comb *= int(cc[j])
            if comb > 10**9:
                break
        comb_scores.append((comb, int(s_idx)))
    comb_scores.sort(key=lambda t: t[0])
    if song_limit > 0:
        comb_scores = comb_scores[: int(song_limit)]
    eligible = [s for _comb, s in comb_scores]

    if not eligible:
        return covered_np, chosen_offsets_np, {
            "enabled": True,
            "attempts": int(attempts),
            "repaired": 0,
            "songs_considered": 0,
            "time_sec": 0.0,
        }

    covered_sub = covered_np[np.asarray(eligible, dtype=np.int32)]
    totals_sub = totals_np[np.asarray(eligible, dtype=np.int32)]
    cand_idx_sub = cand_idx[np.asarray(eligible, dtype=np.int32)]
    cand_count_sub = cand_count[np.asarray(eligible, dtype=np.int32)]

    mem.log(f"gpu_full_repair_inputs_ready (songs={len(eligible)})")
    res = repair_uncovered_with_inventory_gpu(
        covered_np=covered_sub,
        totals_np=totals_sub,
        cand_idx_np=cand_idx_sub,
        cand_count_np=cand_count_sub,
        inv_offsets_np=inv_offsets,
        inv_gems_np=inv_gems,
        attempts=int(attempts),
        seed=int(seed),
        profile=bool(profile),
    )
    mem.log("gpu_full_repair_done")

    repaired_mask = np.asarray(res.repaired_mask, dtype=np.int32)
    repaired_offsets = np.asarray(res.repaired_offsets, dtype=np.int32)

    new_covered = covered_np.copy()
    new_chosen = chosen_offsets_np.copy()
    for local_i, s_idx in enumerate(eligible):
        if int(new_covered[s_idx]) != 0:
            continue
        if int(repaired_mask[local_i]) != 0:
            new_covered[s_idx] = 1
            new_chosen[s_idx, :] = repaired_offsets[local_i, :]

    stats = dict(res.stats)
    stats["songs_considered"] = int(len(eligible))
    return new_covered, new_chosen, stats


def _try_inventory_repair_multi(
    *,
    songs: List[SongSpec],
    covered_np: np.ndarray,
    chosen_offsets_np: np.ndarray,
    chosen_candidate_idx: np.ndarray,
    inv_cap: int,
    attempts: int,
    seed: int,
    max_cands_per_slot: int,
    song_limit: int,
    mem: _MemoryLogger,
    profile: bool,
    seeded_pairs: Optional[Iterable[Tuple[int, int]]] = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """
    Multi-candidate variant of `_try_inventory_repair`.

    For each uncovered song, choose a single candidate (among peak candidates) that has the best
    support from the existing inventory, then attempt an exact totals match using only inventory variants.
    """
    if max_cands_per_slot <= 0:
        raise ValueError("max_cands_per_slot must be positive.")
    song_limit = int(song_limit)
    if song_limit < 0:
        raise ValueError("song_limit must be >= 0.")

    covered_np = np.asarray(covered_np, dtype=np.int32)
    chosen_offsets_np = np.asarray(chosen_offsets_np, dtype=np.int32)
    chosen_candidate_idx = np.asarray(chosen_candidate_idx, dtype=np.int32)
    if covered_np.ndim != 1:
        raise ValueError("covered_np must be (S,).")
    if chosen_offsets_np.shape != (covered_np.shape[0], 6):
        raise ValueError("chosen_offsets_np must be (S,6).")
    if chosen_candidate_idx.shape != (covered_np.shape[0],):
        raise ValueError("chosen_candidate_idx must be (S,).")

    # Build inventory variant list from currently covered songs.
    used_pairs_set: set[Tuple[int, int]] = set()
    for s_idx, is_cov in enumerate(covered_np.tolist()):
        if int(is_cov) <= 0:
            continue
        c_idx = int(chosen_candidate_idx[s_idx])
        if c_idx < 0 or c_idx >= int(len(songs[s_idx].candidates)):
            continue
        cand = songs[s_idx].candidates[c_idx]
        for j in range(6):
            used_pairs_set.add((int(cand.gear_ids[j]), int(chosen_offsets_np[s_idx, j])))
    if seeded_pairs:
        for gid, off in seeded_pairs:
            used_pairs_set.add((int(gid), int(off)))

    used_pairs = sorted(used_pairs_set)
    if len(used_pairs) > int(inv_cap):
        raise RuntimeError("Repair invariant violated: inventory exceeds cap.")
    if not used_pairs:
        return (
            covered_np,
            chosen_offsets_np,
            chosen_candidate_idx,
            {"enabled": True, "repaired": 0, "time_sec": 0.0, "attempts": int(attempts)},
        )

    offset_gems_np, offset_color_np = build_variant_offset_tables()

    inv_gear_ids = np.asarray([p[0] for p in used_pairs], dtype=np.int32)
    inv_offsets = np.asarray([p[1] for p in used_pairs], dtype=np.int32)
    inv_gems = offset_gems_np[inv_offsets].astype(np.int32, copy=False)
    inv_color = offset_color_np[inv_offsets].astype(np.int32, copy=False)

    by_key: Dict[Tuple[int, int], List[int]] = {}
    for idx in range(int(inv_gear_ids.shape[0])):
        gid = int(inv_gear_ids[idx])
        col = int(inv_color[idx])
        by_key.setdefault((gid, col), []).append(int(idx))

    S = int(covered_np.shape[0])
    C = int(max_cands_per_slot)
    cand_idx = np.full((S, 6, C), -1, dtype=np.int32)
    cand_count = np.zeros((S, 6), dtype=np.int32)
    totals_np = np.zeros((S, 6), dtype=np.int32)
    elements_np = np.zeros((S,), dtype=np.int32)
    repair_candidate_idx = chosen_candidate_idx.copy()

    for s_idx in range(S):
        if int(covered_np[s_idx]) != 0:
            continue
        best_c = -1
        best_key: Optional[Tuple[int, int, int]] = None
        for c_idx, cand in enumerate(songs[s_idx].candidates):
            elem = int(cand.element_id)
            ok_slots = 0
            support_sum = 0
            min_slot = 10**9
            for slot in range(6):
                gid = int(cand.gear_ids[slot])
                cnt = int(len(by_key.get((gid, 0), [])) + len(by_key.get((gid, elem), [])))
                support_sum += cnt
                if cnt > 0:
                    ok_slots += 1
                if cnt < min_slot:
                    min_slot = cnt
            # Prefer candidates with all slots supported, then higher support, then earlier candidate index.
            key = (int(ok_slots), int(min_slot), int(support_sum))
            if best_key is None or key > best_key:
                best_key = key
                best_c = int(c_idx)
        if best_c < 0:
            continue
        repair_candidate_idx[s_idx] = int(best_c)
        chosen_cand = songs[s_idx].candidates[int(best_c)]
        totals_np[s_idx, :] = np.asarray(chosen_cand.candidate.gem_totals, dtype=np.int32)
        elements_np[s_idx] = int(chosen_cand.element_id)

        elem = int(elements_np[s_idx])
        for slot in range(6):
            gid = int(chosen_cand.gear_ids[slot])
            inds = by_key.get((gid, 0), []) + by_key.get((gid, elem), [])
            if not inds:
                cand_count[s_idx, slot] = 0
                continue
            inds_sorted = sorted(
                inds,
                key=lambda i: (
                    int(inv_gems[i, OV_INDEX]),
                    int(inv_gems[i, 0] + inv_gems[i, 1] + inv_gems[i, 2] + inv_gems[i, 3] + inv_gems[i, 4]),
                ),
                reverse=True,
            )
            take = min(C, len(inds_sorted))
            cand_idx[s_idx, slot, :take] = np.asarray(inds_sorted[:take], dtype=np.int32)
            cand_count[s_idx, slot] = int(take)

    comb_scores: List[Tuple[int, int]] = []
    for s_idx in range(S):
        if int(covered_np[s_idx]) != 0:
            continue
        if int(repair_candidate_idx[s_idx]) < 0:
            continue
        cc = cand_count[s_idx]
        if int(cc.min()) <= 0:
            continue
        comb = 1
        for j in range(6):
            comb *= int(cc[j])
            if comb > 10**9:
                break
        comb_scores.append((comb, int(s_idx)))
    comb_scores.sort(key=lambda t: t[0])
    if song_limit > 0:
        comb_scores = comb_scores[: int(song_limit)]
    eligible = [s for _comb, s in comb_scores]

    if not eligible:
        return covered_np, chosen_offsets_np, chosen_candidate_idx, {
            "enabled": True,
            "attempts": int(attempts),
            "repaired": 0,
            "songs_considered": 0,
            "time_sec": 0.0,
        }

    eligible_np = np.asarray(eligible, dtype=np.int32)
    covered_sub = covered_np[eligible_np]
    totals_sub = totals_np[eligible_np]
    cand_idx_sub = cand_idx[eligible_np]
    cand_count_sub = cand_count[eligible_np]

    mem.log(f"gpu_full_repair_inputs_ready (songs={len(eligible)})")
    res = repair_uncovered_with_inventory_gpu(
        covered_np=covered_sub,
        totals_np=totals_sub,
        cand_idx_np=cand_idx_sub,
        cand_count_np=cand_count_sub,
        inv_offsets_np=inv_offsets,
        inv_gems_np=inv_gems,
        attempts=int(attempts),
        seed=int(seed),
        profile=bool(profile),
    )
    mem.log("gpu_full_repair_done")

    repaired_mask = np.asarray(res.repaired_mask, dtype=np.int32)
    repaired_offsets = np.asarray(res.repaired_offsets, dtype=np.int32)

    new_covered = covered_np.copy()
    new_offsets = chosen_offsets_np.copy()
    new_candidate_idx = chosen_candidate_idx.copy()
    for local_i, s_idx in enumerate(eligible):
        if int(new_covered[s_idx]) != 0:
            continue
        if int(repaired_mask[local_i]) != 0:
            new_covered[s_idx] = 1
            new_offsets[s_idx, :] = repaired_offsets[local_i, :]
            new_candidate_idx[s_idx] = int(repair_candidate_idx[s_idx])

    stats = dict(res.stats)
    stats["songs_considered"] = int(len(eligible))
    return new_covered, new_offsets, new_candidate_idx, stats


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
            "mini_groups": [list(group) for group in cand.mini_groups],
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
    gpu_full_lns_random_destroy_prob: float,
    gpu_full_lns_restore_after: int,
    gpu_full_lns_restore_drop: int,
    gpu_full_variant_freq_mode: str,
    gpu_full_counter_stripes: int,
    gpu_full_witness_pattern_profile: int,
    gpu_full_k_scan_select: int,
    gpu_full_k_scan_repack: int,
    gpu_full_alns_enabled: bool = False,
    gpu_full_alns_islands: int = 1,
    gpu_full_pt_enabled: bool = False,
    gpu_full_pt_t_min: float = 1.0,
    gpu_full_pt_t_max: float = 10.0,
    gpu_full_pt_swap_interval: int = 8,
    gpu_full_pt_destroy_beta: float = 0.0,
    gpu_full_pt_cap_slack_max: int = 0,
    gpu_full_witness_palettes: int,
    witness_anchor_patterns: int = 24,
    witness_seed_streams: int = 4,
    v_pad_bin: int = 4096,
    mem: _MemoryLogger,
    wildcard_freq_bonus: int = 0,
    seeded_raw_vids: Optional[np.ndarray] = None,
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
        gpu_full_alns_enabled=bool(gpu_full_alns_enabled),
        gpu_full_alns_islands=int(gpu_full_alns_islands),
        gpu_full_pt_enabled=bool(gpu_full_pt_enabled),
        gpu_full_pt_t_min=float(gpu_full_pt_t_min),
        gpu_full_pt_t_max=float(gpu_full_pt_t_max),
        gpu_full_pt_swap_interval=int(gpu_full_pt_swap_interval),
        gpu_full_pt_destroy_beta=float(gpu_full_pt_destroy_beta),
        gpu_full_pt_cap_slack_max=int(gpu_full_pt_cap_slack_max),
        lns_time_sec=float(lns_time_sec),
        lns_attempts=int(lns_attempts),
        gpu_lns_destroy=int(gpu_lns_destroy),
        gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
        gpu_full_lns_random_destroy_prob=float(gpu_full_lns_random_destroy_prob),
        gpu_full_lns_restore_after=int(gpu_full_lns_restore_after),
        gpu_full_lns_restore_drop=int(gpu_full_lns_restore_drop),
        gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
        gpu_full_counter_stripes=int(gpu_full_counter_stripes),
        mem=mem,
        wp_stats=wp_stats,
        v_pad_bin=int(v_pad_bin),
        wildcard_freq_bonus=int(wildcard_freq_bonus),
        seeded_raw_vids=seeded_raw_vids,
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

    def _apportion(total: int, weights: List[int], *, min_each: int = 0) -> List[int]:
        total = int(total)
        if total < 0:
            raise ValueError("apportion total must be >= 0.")
        n = int(len(weights))
        if n <= 0:
            return []
        if int(min_each) < 0:
            raise ValueError("apportion min_each must be >= 0.")
        if total < n * int(min_each):
            raise ValueError("apportion total too small for min_each constraint.")
        w = [max(0, int(x)) for x in weights]
        if sum(w) <= 0:
            w = [1] * n

        out = [int(min_each)] * n
        remaining = int(total - n * int(min_each))
        if remaining <= 0:
            return out

        denom = int(sum(w))
        add = [int((remaining * w[i]) // denom) for i in range(n)]
        rem = [int((remaining * w[i]) % denom) for i in range(n)]
        used = int(sum(add))
        leftover = int(remaining - used)
        if leftover > 0:
            order = sorted(range(n), key=lambda i: (rem[i], w[i], -i), reverse=True)
            for t in range(int(leftover)):
                add[order[t % n]] += 1

        for i in range(n):
            out[i] += int(add[i])
        if sum(out) != total:
            raise RuntimeError("apportion sum mismatch.")
        return out

    # Build a flat list of candidate instances so we can run witness generation ONCE with fixed K_total,
    # then slice per-candidate budgets (avoids multiple Taichi recompiles for varying K).
    items: List[Tuple[int, int, CandidateSpec]] = []  # (song_idx, cand_idx, cand)
    cand_counts: List[int] = []
    item_idx_by_song: List[List[int]] = []
    for s_idx, song in enumerate(songs):
        cand_count = int(len(song.candidates))
        if cand_count <= 0:
            raise ValueError(f"No candidates for song: {song.name}")
        if k_total < cand_count:
            raise ValueError("k_total must be >= candidates per song for multi-candidate mode.")
        # Candidate budgets are intentionally skewed toward the best-ranked candidate (index 0).
        # Equal splitting tends to regress coverage because it deprives the primary candidate of
        # enough anchor patterns and exploration budget.
        primary_weight = 4
        other_weight = 1
        weights = [int(primary_weight)] + [int(other_weight)] * max(0, int(cand_count - 1))
        budgets = _apportion(int(k_total), weights, min_each=1)
        cand_counts.append(cand_count)

        # Allocate the witness anchor prefix mostly to the primary candidate to preserve reuse bias,
        # while still giving alternatives enough anchors to be viable.
        k_anchor = max(0, min(int(k_total), int(witness_anchor_patterns)))
        anchor_min_each = 1 if k_anchor >= cand_count else 0
        anchors = _apportion(int(k_anchor), weights, min_each=int(anchor_min_each)) if k_anchor > 0 else [0] * cand_count
        # Clamp anchors to budgets and redistribute any overshoot.
        overshoot = 0
        for i in range(cand_count):
            if anchors[i] > budgets[i]:
                overshoot += int(anchors[i] - budgets[i])
                anchors[i] = int(budgets[i])
        if overshoot > 0:
            cap = [int(budgets[i] - anchors[i]) for i in range(cand_count)]
            order = sorted(range(cand_count), key=lambda i: (cap[i], weights[i], -i), reverse=True)
            for t in range(int(overshoot)):
                i = order[t % cand_count]
                if cap[i] <= 0:
                    continue
                anchors[i] += 1
                cap[i] -= 1

        remaining_anchor = list(anchors)
        c_ptr = 0
        for p in range(int(k_anchor)):
            spins = 0
            while remaining_anchor[c_ptr] <= 0 and spins < cand_count:
                c_ptr = (c_ptr + 1) % cand_count
                spins += 1
            if remaining_anchor[c_ptr] <= 0:
                raise RuntimeError("Multi-candidate witness budget mismatch (anchors exhausted early).")
            part_to_candidate[s_idx, p] = int(c_ptr)
            remaining_anchor[c_ptr] -= 1
            c_ptr = (c_ptr + 1) % cand_count
        if any(r != 0 for r in remaining_anchor):
            raise RuntimeError("Multi-candidate witness budget mismatch (anchors leftover).")

        remaining = [int(budgets[i] - anchors[i]) for i in range(cand_count)]
        for p in range(int(k_anchor), int(k_total)):
            spins = 0
            while remaining[c_ptr] <= 0 and spins < cand_count:
                c_ptr = (c_ptr + 1) % cand_count
                spins += 1
            if remaining[c_ptr] <= 0:
                raise RuntimeError("Multi-candidate witness budget mismatch (allocation exhausted early).")
            part_to_candidate[s_idx, p] = int(c_ptr)
            remaining[c_ptr] -= 1
            c_ptr = (c_ptr + 1) % cand_count
        if any(r != 0 for r in remaining):
            raise RuntimeError("Multi-candidate witness budget mismatch (allocation leftover).")

        idxs: List[int] = []
        for c_idx, cand in enumerate(song.candidates):
            idxs.append(int(len(items)))
            items.append((int(s_idx), int(c_idx), cand))
        item_idx_by_song.append(idxs)

    if not items:
        raise RuntimeError("No candidate instances to build witness pool.")

    gear_ids_np = np.zeros((len(items), 6), dtype=np.int32)
    totals_np = np.zeros((len(items), 6), dtype=np.int32)
    elements_np = np.zeros((len(items),), dtype=np.int32)
    for idx, (_s_idx, _c_idx, cand) in enumerate(items):
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
    for s_idx, song in enumerate(songs):
        cand_count = int(len(song.candidates))
        if cand_count <= 0:
            continue
        if s_idx >= len(item_idx_by_song):
            raise RuntimeError("Multi-candidate witness index mapping mismatch.")
        idxs = item_idx_by_song[s_idx]
        if len(idxs) != cand_count:
            raise RuntimeError("Multi-candidate witness index mapping mismatch.")
        for c_idx, inst_idx in enumerate(idxs):
            mask = part_to_candidate[s_idx] == int(c_idx)
            if not np.any(mask):
                continue
            offsets_out[s_idx, mask, :] = offsets_all[int(inst_idx), mask, :]

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


def _map_seeded_raw_to_dense(
    seed_raw: Optional[np.ndarray],
    dense_vid_universe: np.ndarray,
) -> Tuple[np.ndarray, int, int]:
    if seed_raw is None:
        return np.zeros((0,), dtype=np.int32), 0, 0
    seed_raw = np.asarray(seed_raw, dtype=np.int32).reshape(-1)
    if seed_raw.size == 0:
        return np.zeros((0,), dtype=np.int32), 0, 0
    seed_raw = np.unique(seed_raw)
    idx = np.searchsorted(dense_vid_universe, seed_raw)
    in_bounds = (idx < dense_vid_universe.size) & (dense_vid_universe[idx] == seed_raw)
    dense_idx = idx[in_bounds].astype(np.int32, copy=False)
    missing = int((~in_bounds).sum())
    return dense_idx, missing, int(seed_raw.size)


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
    gpu_full_alns_enabled: bool = False,
    gpu_full_alns_islands: int = 1,
    gpu_full_pt_enabled: bool = False,
    gpu_full_pt_t_min: float = 1.0,
    gpu_full_pt_t_max: float = 10.0,
    gpu_full_pt_swap_interval: int = 8,
    gpu_full_pt_destroy_beta: float = 0.0,
    gpu_full_pt_cap_slack_max: int = 0,
    lns_time_sec: float,
    lns_attempts: int,
    gpu_lns_destroy: int,
    gpu_full_lns_freq_weighted: bool,
    gpu_full_lns_random_destroy_prob: float,
    gpu_full_lns_restore_after: int,
    gpu_full_lns_restore_drop: int,
    gpu_full_variant_freq_mode: str,
    gpu_full_counter_stripes: int,
    mem: _MemoryLogger,
    wp_stats: Optional[dict] = None,
    dense_vid_universe: Optional[np.ndarray] = None,
    v_pad_bin: int = 4096,
    wildcard_freq_bonus: int = 0,
    seeded_raw_vids: Optional[np.ndarray] = None,
    seeded_dense_indices: Optional[np.ndarray] = None,
    seeded_missing_count: int = 0,
):
    part_vids, variant_freq_np, dense_vid_universe, v_count = _pack_part_vids_dense(
        gear_ids_np,
        offsets_np,
        dense_vid_universe=dense_vid_universe,
        v_pad_bin=int(v_pad_bin),
        variant_freq_mode=str(gpu_full_variant_freq_mode),
        wildcard_freq_bonus=int(wildcard_freq_bonus),
    )

    seeded_dense = np.zeros((0,), dtype=np.int32)
    seeded_missing = 0
    seeded_total = 0
    if seeded_dense_indices is not None:
        seeded_dense = np.asarray(seeded_dense_indices, dtype=np.int32).reshape(-1)
        if seeded_dense.size > 0:
            seeded_dense = np.unique(seeded_dense)
        seeded_missing = int(seeded_missing_count)
        seeded_total = int(seeded_dense.size + seeded_missing)
    else:
        seeded_dense, seeded_missing, seeded_total = _map_seeded_raw_to_dense(seeded_raw_vids, dense_vid_universe)

    mem.log(
        "gpu_full_inputs_ready "
        f"(songs={gear_ids_np.shape[0]}, k_total={int(offsets_np.shape[1])}, v={int(v_count)}, "
        f"seeded={seeded_total})"
    )
    gpu_util_summary = None
    gpu_sampler = None
    if sys.platform == "darwin" and bool(mem.enabled):
        try:
            from .macos_gpu_util import MacosGpuUtilSampler

            gpu_sampler = MacosGpuUtilSampler(interval_sec=0.25)
            gpu_sampler.start()
        except Exception:
            gpu_sampler = None
    try:
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
            alns_enabled=bool(gpu_full_alns_enabled),
            alns_islands=int(gpu_full_alns_islands),
            pt_enabled=bool(gpu_full_pt_enabled),
            pt_t_min=float(gpu_full_pt_t_min),
            pt_t_max=float(gpu_full_pt_t_max),
            pt_swap_interval=int(gpu_full_pt_swap_interval),
            pt_destroy_beta=float(gpu_full_pt_destroy_beta),
            pt_cap_slack_max=int(gpu_full_pt_cap_slack_max),
            lns_time_sec=float(lns_time_sec),
            lns_attempts=int(lns_attempts),
            lns_destroy=int(gpu_lns_destroy),
            lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
            lns_random_destroy_prob=float(gpu_full_lns_random_destroy_prob),
            lns_restore_after=int(gpu_full_lns_restore_after),
            lns_restore_drop=int(gpu_full_lns_restore_drop),
            profile=bool(mem.enabled),
            seeded_variant_indices=seeded_dense,
            seeded_extra_count=int(seeded_missing),
        )
    finally:
        if gpu_sampler is not None:
            try:
                gpu_util_summary = gpu_sampler.stop()
            except Exception:
                gpu_util_summary = None
    if gpu_util_summary is not None:
        sol_full.stats["macos_gpu_util_solve"] = {
            "samples": int(gpu_util_summary.samples),
            "wall_sec": round(float(gpu_util_summary.wall_sec), 3),
            "device_util_avg": None
            if gpu_util_summary.device_util_avg is None
            else round(float(gpu_util_summary.device_util_avg), 2),
            "device_util_max": gpu_util_summary.device_util_max,
            "renderer_util_avg": None
            if gpu_util_summary.renderer_util_avg is None
            else round(float(gpu_util_summary.renderer_util_avg), 2),
            "renderer_util_max": gpu_util_summary.renderer_util_max,
            "tiler_util_avg": None
            if gpu_util_summary.tiler_util_avg is None
            else round(float(gpu_util_summary.tiler_util_avg), 2),
            "tiler_util_max": gpu_util_summary.tiler_util_max,
            "last_submit_pid_top": list(gpu_util_summary.last_submit_pid_top),
            "proc_pid": gpu_util_summary.proc_pid,
            "proc_gpu_time_util_est": None
            if gpu_util_summary.proc_gpu_time_util_est is None
            else round(float(gpu_util_summary.proc_gpu_time_util_est), 2),
        }
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
    gpu_full_lns_random_destroy_prob: float,
    gpu_full_lns_restore_after: int,
    gpu_full_lns_restore_drop: int,
    gpu_full_variant_freq_mode: str,
    gpu_full_counter_stripes: int,
    gpu_full_witness_pattern_profile: int,
    gpu_full_k_scan_select: int,
    gpu_full_k_scan_repack: int,
    gpu_full_alns_enabled: bool = False,
    gpu_full_alns_islands: int = 1,
    gpu_full_pt_enabled: bool = False,
    gpu_full_pt_t_min: float = 1.0,
    gpu_full_pt_t_max: float = 10.0,
    gpu_full_pt_swap_interval: int = 8,
    gpu_full_pt_destroy_beta: float = 0.0,
    gpu_full_pt_cap_slack_max: int = 0,
    witness_anchor_patterns: int,
    witness_seed_streams: int,
    mem: _MemoryLogger,
    v_pad_bin: int = 4096,
    wildcard_freq_bonus: int = 0,
    seeded_raw_vids: Optional[np.ndarray] = None,
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
        cand_count = int(len(song.candidates))
        if cand_count <= 0:
            raise RuntimeError("Multi-candidate raw vids build mismatch (no candidates).")
        gids = (np.stack([np.asarray(c.gear_ids, dtype=np.int32) for c in song.candidates], axis=0) << np.int32(16)).astype(
            np.int32,
            copy=False,
        )
        cand_idx = np.asarray(part_to_candidate[s_idx], dtype=np.int32)
        if np.any(cand_idx < 0) or np.any(cand_idx >= cand_count):
            raise RuntimeError("Multi-candidate raw vids build mismatch (candidate index out of range).")
        raw_vids[s_idx, :, :] = gids[cand_idx, :] | offsets_np[s_idx, :, :]

    part_vids, variant_freq_np, dense_vid_universe, v_count = _pack_part_vids_dense_from_raw(
        raw_vids,
        v_pad_bin=int(v_pad_bin),
        variant_freq_mode=str(gpu_full_variant_freq_mode),
        wildcard_freq_bonus=int(wildcard_freq_bonus),
    )
    seeded_dense, seeded_missing, seeded_total = _map_seeded_raw_to_dense(seeded_raw_vids, dense_vid_universe)

    mem.log(
        f"gpu_full_inputs_ready (songs={part_vids.shape[0]}, k_total={int(k_total)}, v={int(v_count)}, "
        f"seeded={seeded_total})"
    )
    gpu_util_summary = None
    gpu_sampler = None
    if sys.platform == "darwin" and bool(mem.enabled):
        try:
            from .macos_gpu_util import MacosGpuUtilSampler

            gpu_sampler = MacosGpuUtilSampler(interval_sec=0.25)
            gpu_sampler.start()
        except Exception:
            gpu_sampler = None
    try:
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
            alns_enabled=bool(gpu_full_alns_enabled),
            alns_islands=int(gpu_full_alns_islands),
            pt_enabled=bool(gpu_full_pt_enabled),
            pt_t_min=float(gpu_full_pt_t_min),
            pt_t_max=float(gpu_full_pt_t_max),
            pt_swap_interval=int(gpu_full_pt_swap_interval),
            pt_destroy_beta=float(gpu_full_pt_destroy_beta),
            pt_cap_slack_max=int(gpu_full_pt_cap_slack_max),
            lns_time_sec=float(lns_time_sec),
            lns_attempts=int(lns_attempts),
            lns_destroy=int(gpu_lns_destroy),
            lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
            lns_random_destroy_prob=float(gpu_full_lns_random_destroy_prob),
            lns_restore_after=int(gpu_full_lns_restore_after),
            lns_restore_drop=int(gpu_full_lns_restore_drop),
            profile=bool(mem.enabled),
            seeded_variant_indices=seeded_dense,
            seeded_extra_count=int(seeded_missing),
        )
    finally:
        if gpu_sampler is not None:
            try:
                gpu_util_summary = gpu_sampler.stop()
            except Exception:
                gpu_util_summary = None
    if gpu_util_summary is not None:
        sol_full.stats["macos_gpu_util_solve"] = {
            "samples": int(gpu_util_summary.samples),
            "wall_sec": round(float(gpu_util_summary.wall_sec), 3),
            "device_util_avg": None
            if gpu_util_summary.device_util_avg is None
            else round(float(gpu_util_summary.device_util_avg), 2),
            "device_util_max": gpu_util_summary.device_util_max,
            "renderer_util_avg": None
            if gpu_util_summary.renderer_util_avg is None
            else round(float(gpu_util_summary.renderer_util_avg), 2),
            "renderer_util_max": gpu_util_summary.renderer_util_max,
            "tiler_util_avg": None
            if gpu_util_summary.tiler_util_avg is None
            else round(float(gpu_util_summary.tiler_util_avg), 2),
            "tiler_util_max": gpu_util_summary.tiler_util_max,
            "last_submit_pid_top": list(gpu_util_summary.last_submit_pid_top),
            "proc_pid": gpu_util_summary.proc_pid,
            "proc_gpu_time_util_est": None
            if gpu_util_summary.proc_gpu_time_util_est is None
            else round(float(gpu_util_summary.proc_gpu_time_util_est), 2),
        }
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
    gpu_full_lns_random_destroy_prob: float = 0.0,
    gpu_full_lns_restore_after: int = 12,
    gpu_full_lns_restore_drop: int = 4,
    gpu_full_variant_freq_mode: str = "occurrence",
    gpu_full_witness_pattern_profile: int = 0,
    gpu_full_counter_stripes: int = 1,
    gpu_full_k_scan_select: int = 0,
    gpu_full_k_scan_repack: int = 0,
    seeded_raw_vids: Optional[np.ndarray] = None,
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
    seeded_dense, seeded_missing, seeded_total = _map_seeded_raw_to_dense(seeded_raw_vids, dense_vid_universe)
    if seeded_total:
        mem.log(f"gpu_full_seeded_inventory (seeded={seeded_total}, missing={seeded_missing})")

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
            gpu_full_lns_random_destroy_prob=float(gpu_full_lns_random_destroy_prob),
            gpu_full_lns_restore_after=int(gpu_full_lns_restore_after),
            gpu_full_lns_restore_drop=int(gpu_full_lns_restore_drop),
            gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
            gpu_full_counter_stripes=int(gpu_full_counter_stripes),
            mem=mem,
            wp_stats=wp_stats_by_seed[int(s)],
            dense_vid_universe=dense_vid_universe,
            v_pad_bin=int(v_pad_bin),
            wildcard_freq_bonus=int(wildcard_freq_bonus),
            seeded_dense_indices=seeded_dense,
            seeded_missing_count=int(seeded_missing),
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
    seed_inventory_gear: Optional[Iterable[Dict[str, Any]]] = None,
    element: Optional[str] = None,
    secondary_element: Optional[str] = None,
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
    gpu_full_lns_random_destroy_prob: float = 0.0,
    gpu_full_lns_restore_after: int = 12,
    gpu_full_lns_restore_drop: int = 4,
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
    gpu_full_alns_enabled: bool = False,
    gpu_full_alns_islands: int = 1,
    gpu_full_pt_enabled: bool = False,
    gpu_full_pt_t_min: float = 1.0,
    gpu_full_pt_t_max: float = 10.0,
    gpu_full_pt_swap_interval: int = 8,
    gpu_full_pt_destroy_beta: float = 0.0,
    gpu_full_pt_cap_slack_max: int = 0,
    gpu_full_repair_enabled: bool = False,
    gpu_full_repair_attempts: int = 128,
    gpu_full_repair_max_cands_per_slot: int = 8,
    gpu_full_repair_song_limit: int = 512,
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
    - `element` and `secondary_element` restrict the song set to peak rows matching those selected elements.
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
    gpu_full_lns_random_destroy_prob = float(gpu_full_lns_random_destroy_prob)
    if not (0.0 <= gpu_full_lns_random_destroy_prob <= 1.0):
        raise ValueError("gpu_full_lns_random_destroy_prob must be in [0, 1].")
    gpu_full_lns_restore_after = int(gpu_full_lns_restore_after)
    if gpu_full_lns_restore_after <= 0:
        raise ValueError("gpu_full_lns_restore_after must be positive.")
    gpu_full_lns_restore_drop = int(gpu_full_lns_restore_drop)
    if gpu_full_lns_restore_drop < 0:
        raise ValueError("gpu_full_lns_restore_drop must be >= 0.")
    gpu_full_witness_pattern_profile = int(gpu_full_witness_pattern_profile)
    if gpu_full_witness_pattern_profile < 0:
        raise ValueError("gpu_full_witness_pattern_profile must be >= 0.")
    gpu_full_counter_stripes = int(gpu_full_counter_stripes)
    if gpu_full_counter_stripes <= 0:
        raise ValueError("gpu_full_counter_stripes must be positive.")
    gpu_full_alns_enabled = bool(gpu_full_alns_enabled)
    gpu_full_alns_islands = int(gpu_full_alns_islands)
    if gpu_full_alns_islands <= 0:
        raise ValueError("gpu_full_alns_islands must be positive.")
    gpu_full_pt_enabled = bool(gpu_full_pt_enabled)
    gpu_full_pt_t_min = float(gpu_full_pt_t_min)
    gpu_full_pt_t_max = float(gpu_full_pt_t_max)
    gpu_full_pt_swap_interval = int(gpu_full_pt_swap_interval)
    gpu_full_pt_destroy_beta = float(gpu_full_pt_destroy_beta)
    gpu_full_pt_cap_slack_max = int(gpu_full_pt_cap_slack_max)
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
    gpu_full_repair_enabled = bool(gpu_full_repair_enabled)
    gpu_full_repair_attempts = int(gpu_full_repair_attempts)
    if gpu_full_repair_attempts <= 0:
        raise ValueError("gpu_full_repair_attempts must be positive.")
    gpu_full_repair_max_cands_per_slot = int(gpu_full_repair_max_cands_per_slot)
    if gpu_full_repair_max_cands_per_slot <= 0:
        raise ValueError("gpu_full_repair_max_cands_per_slot must be positive.")
    gpu_full_repair_song_limit = int(gpu_full_repair_song_limit)
    if gpu_full_repair_song_limit < 0:
        raise ValueError("gpu_full_repair_song_limit must be >= 0.")

    solver = str(solver or "gpu_dynamic").strip().lower()
    if solver not in {"gpu_dynamic", "gpu_eda", "gpu_full"}:
        raise ValueError("solver must be one of: gpu_dynamic, gpu_eda, gpu_full")

    # Entrapment avoidance: element-scoped runs are much smaller, so a few cheap restarts dramatically
    # reduces "stuck" outcomes (same coverage but worse variant count) without blowing up runtime.
    if solver == "gpu_full" and int(restarts) == 1 and (element is not None or secondary_element is not None):
        restarts = 3

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
                # Inventory meta coverage is exact-peak-only: ignore "within delta" candidate fetching.
                mem.log("gpu_full_candidate_score_delta_ignored_exact_peak_only")
            candidates_by_song, missing = fetch_peak_candidates_allow_missing(conn)
    finally:
        conn.close()
        mem.log("db_closed")

    songs_total_unfiltered = int(len(candidates_by_song))
    element = _normalize_element_filter(element)
    secondary_element = _normalize_element_filter(secondary_element)
    allowed_elements = {e for e in (element, secondary_element) if e}
    songs_filtered_out = 0
    if allowed_elements:
        filtered: Dict[str, List[SongCandidate]] = {}
        for song_name, candidates in candidates_by_song.items():
            kept = [cand for cand in candidates if cand.selected_element in allowed_elements]
            if kept:
                filtered[song_name] = kept
        songs_filtered_out = int(len(candidates_by_song) - len(filtered))
        candidates_by_song = filtered
        if song_peak_by_name is not None:
            song_peak_by_name = {k: v for k, v in song_peak_by_name.items() if k in candidates_by_song}

    if not candidates_by_song:
        raise ValueError("No candidates found in loadouts/fg_loadouts.")

    gear_names = _collect_gear_names(candidates_by_song)
    gear_id_map = {name: idx + 1 for idx, name in enumerate(gear_names)}

    mini_names = _collect_mini_names(candidates_by_song)
    mini_id_map = {name: idx for idx, name in enumerate(mini_names)}

    seed_result: Optional[SeedInventoryResult] = None
    seeded_raw_vids: Optional[np.ndarray] = None
    if seed_inventory_gear:
        seed_result = build_seeded_inventory_variants(seed_inventory_gear, gear_id_map)
        seeded_raw_vids = seed_result.raw_variant_ids

    song_specs = _build_song_specs(candidates_by_song, gear_id_map, mini_id_map)
    mem.log(f"song_specs_built (songs={len(song_specs)}, missing={len(missing)})")

    selected_specs = _select_one_peak_candidate_per_song(song_specs)
    mem.log("selected_one_candidate_per_song")

    use_multi_candidates = solver == "gpu_full" and gpu_full_top_candidates > 1
    multi_max_candidates: Optional[int] = None
    gear_ids_np = totals_np = elements_np = gear_freq_np = None
    if use_multi_candidates:
        k_total = int(partitions_per_song) + int(adaptive_rounds) * int(adaptive_keep_per_song)
        k_total = max(int(partitions_per_song), int(k_total))
        multi_max_candidates = min(int(gpu_full_top_candidates), int(k_total))
        mem.log(f"multi_candidate_mode_enabled (k={int(multi_max_candidates)})")
    else:
        gear_ids_np, totals_np, elements_np, gear_freq_np = _build_gpu_dynamic_inputs(selected_specs, gear_names=gear_names)
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
        "gpu_full_alns_enabled": bool(gpu_full_alns_enabled),
        "gpu_full_alns_islands": int(gpu_full_alns_islands),
        "gpu_full_pt_enabled": bool(gpu_full_pt_enabled),
        "gpu_full_pt_t_min": float(gpu_full_pt_t_min),
        "gpu_full_pt_t_max": float(gpu_full_pt_t_max),
        "gpu_full_pt_swap_interval": int(gpu_full_pt_swap_interval),
        "gpu_full_pt_destroy_beta": float(gpu_full_pt_destroy_beta),
        "gpu_full_pt_cap_slack_max": int(gpu_full_pt_cap_slack_max),
        "gpu_full_lns_random_destroy_prob": float(gpu_full_lns_random_destroy_prob),
        "gpu_full_lns_restore_after": int(gpu_full_lns_restore_after),
        "gpu_full_lns_restore_drop": int(gpu_full_lns_restore_drop),
        "gpu_full_repair_enabled": bool(gpu_full_repair_enabled),
        "gpu_full_repair_attempts": int(gpu_full_repair_attempts),
        "gpu_full_repair_max_cands_per_slot": int(gpu_full_repair_max_cands_per_slot),
        "gpu_full_repair_song_limit": int(gpu_full_repair_song_limit),
    }

    best_seed: Optional[int] = None
    best_sol = None
    best_cov = -1
    best_used = 10**9
    best_chosen_candidate_idx: Optional[np.ndarray] = None
    best_multi_specs: Optional[List[SongSpec]] = None
    base_seed = int(seed)
    if base_seed == 0:
        base_seed = int(time.time_ns() & 0x7FFFFFFF) or 1

    # Scale LNS budget across restarts so increasing `restarts` doesn't multiply total runtime.
    # Treat (lns_time_sec, lns_attempts) as a total budget and split per restart.
    lns_time_per_restart = float(lns_time_sec)
    lns_attempts_per_restart = int(lns_attempts)
    if int(restarts) > 1:
        lns_time_per_restart = float(lns_time_sec) / float(int(restarts))
        lns_attempts_per_restart = max(1, int((int(lns_attempts) + int(restarts) - 1) // int(restarts)))

    # `gpu_full` supports a multi-seed path that avoids repeated Taichi recompiles by using a
    # single dense variant universe (`V`) across all restarts.
    if solver == "gpu_full" and restarts > 1 and not use_multi_candidates and not gpu_full_alns_enabled:
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
            lns_time_sec=float(lns_time_per_restart),
            lns_attempts=int(lns_attempts_per_restart),
            gpu_lns_destroy=int(gpu_lns_destroy),
            mem=mem,
            wildcard_freq_bonus=int(gpu_full_wildcard_freq_bonus),
            witness_anchor_patterns=int(gpu_full_witness_anchor_patterns),
            witness_seed_streams=int(gpu_full_witness_seed_streams),
            gpu_full_repack_rarity_weighted=bool(gpu_full_repack_rarity_weighted),
            gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
            gpu_full_lns_random_destroy_prob=float(gpu_full_lns_random_destroy_prob),
            gpu_full_lns_restore_after=int(gpu_full_lns_restore_after),
            gpu_full_lns_restore_drop=int(gpu_full_lns_restore_drop),
            v_pad_bin=int(gpu_full_v_pad_bin),
            gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
            gpu_full_witness_pattern_profile=int(gpu_full_witness_pattern_profile),
            gpu_full_counter_stripes=int(gpu_full_counter_stripes),
            gpu_full_k_scan_select=int(gpu_full_k_scan_select),
            gpu_full_k_scan_repack=int(gpu_full_k_scan_repack),
            seeded_raw_vids=seeded_raw_vids,
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
                    lns_time_sec=lns_time_per_restart,
                    lns_attempts=lns_attempts_per_restart,
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
                    lns_attempts=lns_attempts_per_restart,
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
                    if multi_max_candidates is None:
                        raise RuntimeError("Multi-candidate configuration missing.")
                    selected_multi_specs = _select_top_k_candidates_per_song(
                        song_specs,
                        k_candidates=int(multi_max_candidates),
                        song_peak_by_name=song_peak_by_name,
                        seed=int(run_seed),
                    )
                    gear_freq_np = _build_candidate_gear_freq(selected_multi_specs, gear_count=len(gear_names))
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
                        gpu_full_alns_enabled=bool(gpu_full_alns_enabled),
                        gpu_full_alns_islands=int(gpu_full_alns_islands),
                        gpu_full_pt_enabled=bool(gpu_full_pt_enabled),
                        gpu_full_pt_t_min=float(gpu_full_pt_t_min),
                        gpu_full_pt_t_max=float(gpu_full_pt_t_max),
                        gpu_full_pt_swap_interval=int(gpu_full_pt_swap_interval),
                        gpu_full_pt_destroy_beta=float(gpu_full_pt_destroy_beta),
                        gpu_full_pt_cap_slack_max=int(gpu_full_pt_cap_slack_max),
                        lns_time_sec=float(lns_time_per_restart),
                        lns_attempts=int(lns_attempts_per_restart),
                        gpu_lns_destroy=int(gpu_lns_destroy),
                        gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
                        gpu_full_lns_random_destroy_prob=float(gpu_full_lns_random_destroy_prob),
                        gpu_full_lns_restore_after=int(gpu_full_lns_restore_after),
                        gpu_full_lns_restore_drop=int(gpu_full_lns_restore_drop),
                        gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
                        gpu_full_counter_stripes=int(gpu_full_counter_stripes),
                        gpu_full_witness_pattern_profile=int(gpu_full_witness_pattern_profile),
                        witness_anchor_patterns=int(gpu_full_witness_anchor_patterns),
                        witness_seed_streams=int(gpu_full_witness_seed_streams),
                        mem=mem,
                        v_pad_bin=int(gpu_full_v_pad_bin),
                        wildcard_freq_bonus=int(gpu_full_wildcard_freq_bonus),
                        seeded_raw_vids=seeded_raw_vids,
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
                        lns_time_sec=float(lns_time_per_restart),
                        lns_attempts=int(lns_attempts_per_restart),
                        gpu_lns_destroy=int(gpu_lns_destroy),
                        gpu_full_lns_freq_weighted=bool(gpu_full_lns_freq_weighted),
                        gpu_full_lns_random_destroy_prob=float(gpu_full_lns_random_destroy_prob),
                        gpu_full_lns_restore_after=int(gpu_full_lns_restore_after),
                        gpu_full_lns_restore_drop=int(gpu_full_lns_restore_drop),
                        gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
                        gpu_full_counter_stripes=int(gpu_full_counter_stripes),
                        gpu_full_witness_pattern_profile=int(gpu_full_witness_pattern_profile),
                        gpu_full_k_scan_select=int(gpu_full_k_scan_select),
                        gpu_full_k_scan_repack=int(gpu_full_k_scan_repack),
                        gpu_full_alns_enabled=bool(gpu_full_alns_enabled),
                        gpu_full_alns_islands=int(gpu_full_alns_islands),
                        gpu_full_pt_enabled=bool(gpu_full_pt_enabled),
                        gpu_full_pt_t_min=float(gpu_full_pt_t_min),
                        gpu_full_pt_t_max=float(gpu_full_pt_t_max),
                        gpu_full_pt_swap_interval=int(gpu_full_pt_swap_interval),
                        gpu_full_pt_destroy_beta=float(gpu_full_pt_destroy_beta),
                        gpu_full_pt_cap_slack_max=int(gpu_full_pt_cap_slack_max),
                        gpu_full_witness_palettes=int(gpu_full_witness_palettes),
                        mem=mem,
                        v_pad_bin=int(gpu_full_v_pad_bin),
                        wildcard_freq_bonus=int(gpu_full_wildcard_freq_bonus),
                        witness_anchor_patterns=int(gpu_full_witness_anchor_patterns),
                        witness_seed_streams=int(gpu_full_witness_seed_streams),
                        seeded_raw_vids=seeded_raw_vids,
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
                    best_multi_specs = selected_multi_specs

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
        if best_multi_specs is None or best_chosen_candidate_idx is None:
            raise RuntimeError("Multi-candidate materialization inputs missing.")
        repair_stats = None
        if solver == "gpu_full" and gpu_full_repair_enabled:
            old_sol = best_sol
            covered_np = np.asarray(best_sol.covered, dtype=np.int32)
            chosen_offsets_np = np.asarray(best_sol.chosen_offsets, dtype=np.int32)
            seeded_pairs = None
            if seeded_raw_vids is not None and int(seeded_raw_vids.size) > 0:
                gids = (seeded_raw_vids >> np.int32(16)).astype(np.int32, copy=False)
                offs = (seeded_raw_vids & np.int32(0xFFFF)).astype(np.int32, copy=False)
                seeded_pairs = list(zip(gids.tolist(), offs.tolist()))
            repaired_cov, repaired_offsets, repaired_cands, repair_stats = _try_inventory_repair_multi(
                songs=best_multi_specs,
                covered_np=covered_np,
                chosen_offsets_np=chosen_offsets_np,
                chosen_candidate_idx=best_chosen_candidate_idx,
                inv_cap=int(inventory_cap),
                attempts=int(gpu_full_repair_attempts),
                seed=int(best_seed or seed),
                max_cands_per_slot=int(gpu_full_repair_max_cands_per_slot),
                song_limit=int(gpu_full_repair_song_limit),
                mem=mem,
                profile=bool(profile),
                seeded_pairs=seeded_pairs,
            )
            from types import SimpleNamespace

            best_sol = SimpleNamespace(
                covered=repaired_cov,
                chosen_offsets=repaired_offsets,
                covered_count=int(repaired_cov.sum()),
                stats=dict(getattr(old_sol, "stats", {})),
            )
            best_chosen_candidate_idx = np.asarray(repaired_cands, dtype=np.int32)
            if isinstance(best_sol.stats, dict):
                best_sol.stats.setdefault("repair", repair_stats)
        result = _materialize_coverage_solution_multi(
            best_multi_specs,
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
        if repair_stats is not None:
            result.setdefault("solver_stats", {}).setdefault("solver", {}).setdefault("repair", repair_stats)
    else:
        if gear_ids_np is None:
            raise RuntimeError("Gear IDs not initialized for materialization.")
        # Optional inventory-aware repair (exact-peak-only): try to cover uncovered songs using ONLY variants
        # already in the inventory. This does not change inventory size.
        repair_stats = None
        if solver == "gpu_full" and gpu_full_repair_enabled:
            if totals_np is None or elements_np is None:
                raise RuntimeError("Repair requires totals/elements inputs.")
            old_sol = best_sol
            covered_np = np.asarray(best_sol.covered, dtype=np.int32)
            chosen_offsets_np = np.asarray(best_sol.chosen_offsets, dtype=np.int32)
            seeded_pairs = None
            if seeded_raw_vids is not None and int(seeded_raw_vids.size) > 0:
                gids = (seeded_raw_vids >> np.int32(16)).astype(np.int32, copy=False)
                offs = (seeded_raw_vids & np.int32(0xFFFF)).astype(np.int32, copy=False)
                seeded_pairs = list(zip(gids.tolist(), offs.tolist()))
            repaired_cov, repaired_offsets, repair_stats = _try_inventory_repair(
                songs=selected_specs,
                gear_ids_np=gear_ids_np,
                totals_np=totals_np,
                elements_np=elements_np,
                covered_np=covered_np,
                chosen_offsets_np=chosen_offsets_np,
                inv_cap=int(inventory_cap),
                attempts=int(gpu_full_repair_attempts),
                seed=int(best_seed or seed),
                max_cands_per_slot=int(gpu_full_repair_max_cands_per_slot),
                song_limit=int(gpu_full_repair_song_limit),
                mem=mem,
                profile=bool(profile),
                seeded_pairs=seeded_pairs,
            )
            from types import SimpleNamespace

            best_sol = SimpleNamespace(
                covered=repaired_cov,
                chosen_offsets=repaired_offsets,
                covered_count=int(repaired_cov.sum()),
                stats=dict(getattr(old_sol, "stats", {})),
            )
            if isinstance(best_sol.stats, dict):
                best_sol.stats.setdefault("repair", repair_stats)
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
        if repair_stats is not None:
            result.setdefault("solver_stats", {}).setdefault("solver", {}).setdefault("repair", repair_stats)

    result.setdefault("solver_stats", {})["restarts"] = int(restarts)
    result.setdefault("solver_stats", {})["seed"] = int(seed)
    result.setdefault("solver_stats", {})["best_seed"] = best_seed
    result["missing_songs"] = missing
    result["db_path"] = db_path
    result["generated_at"] = datetime.now().isoformat()
    stats = result.get("stats")
    if isinstance(stats, dict):
        stats["songs_total_unfiltered"] = int(songs_total_unfiltered)
        stats["songs_filtered_out"] = int(songs_filtered_out)
        stats["element_filter"] = str(element or "")
        stats["secondary_element_filter"] = str(secondary_element or "")
    if seed_result is not None:
        seed_diag = dict(seed_result.diagnostics)
        seed_diag["applied"] = bool(solver == "gpu_full")
        solver_seeded = result.get("solver_stats", {}).get("solver", {}).get("seeded")
        if isinstance(solver_seeded, dict):
            seed_diag["solver"] = solver_seeded

        seed_items: List[Dict[str, Any]] = []
        gear_id_by_norm = {normalize_for_lookup(name): gid for name, gid in gear_id_map.items()}
        for entry in seed_inventory_gear or []:
            if not isinstance(entry, dict):
                continue
            inv_id = entry.get("id")
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            gid = gear_id_by_norm.get(normalize_for_lookup(name))
            if gid is None:
                seed_items.append({"id": inv_id, "name": name, "seedable": False, "reason": "unknown_gear"})
                continue

            upgrade_ids = _extract_upgrade_ids(entry)
            if not upgrade_ids:
                seed_items.append({"id": inv_id, "name": name, "seedable": False, "reason": "partial_upgrades"})
                continue

            counts = [0] * len(STAT_KEYS)
            element_name = None
            mixed_element = False
            for upgrade_id in upgrade_ids:
                stat = UPGRADE_ID_TO_STAT.get(int(upgrade_id))
                if stat:
                    counts[STAT_KEYS.index(stat)] += 1
                    continue
                element = UPGRADE_ID_TO_ELEMENT.get(int(upgrade_id))
                if element:
                    counts[OV_INDEX] += 1
                    if element_name is None:
                        element_name = element
                    elif element_name != element:
                        mixed_element = True
                    continue

            if mixed_element:
                seed_items.append({"id": inv_id, "name": name, "seedable": False, "reason": "mixed_elements"})
                continue

            total_gems = sum(counts)
            if total_gems != 15:
                seed_items.append(
                    {"id": inv_id, "name": name, "seedable": False, "reason": "partial_upgrades", "total_gems": total_gems}
                )
                continue

            ov = counts[OV_INDEX]
            if ov > 0 and not element_name:
                seed_items.append({"id": inv_id, "name": name, "seedable": False, "reason": "invalid_offsets"})
                continue

            color_id = int(ELEMENT_TO_ID.get(element_name or "", 0) or 0) if ov > 0 else 0
            key = (counts[0], counts[1], counts[2], counts[3], counts[4], counts[5], int(color_id))
            off = _offset_lookup().get(key)
            if off is None:
                seed_items.append({"id": inv_id, "name": name, "seedable": False, "reason": "invalid_offsets"})
                continue

            raw_vid = (int(gid) << 16) | int(off)
            seed_items.append(
                {
                    "id": inv_id,
                    "name": name,
                    "seedable": True,
                    "raw_variant_id": int(raw_vid),
                    "gear_id": int(gid),
                }
            )

        # Allocate each required inventory variant to either an exact-owned copy, a rerollable copy, or "add".
        required_variants = (result.get("inventory") or {}).get("gear_variants") or []
        required_by_gid: Dict[int, List[Dict[str, Any]]] = {}
        raw_by_variant_id: Dict[int, int] = {}

        for variant in required_variants:
            if not isinstance(variant, dict):
                continue
            try:
                variant_id = int(variant.get("id") or 0)
            except Exception:
                continue
            raw_vid = _raw_vid_for_variant_dict(variant, gear_id_map)
            if raw_vid is None:
                continue
            raw_by_variant_id[variant_id] = int(raw_vid)
            gid = int(raw_vid >> 16)
            required_by_gid.setdefault(gid, []).append({"variant_id": variant_id, "raw_variant_id": int(raw_vid)})

        pool_by_gid: Dict[int, List[Dict[str, Any]]] = {}
        for item in seed_items:
            if not isinstance(item, dict):
                continue
            if not item.get("seedable"):
                continue
            try:
                gid = int(item.get("gear_id"))
                raw_vid = int(item.get("raw_variant_id"))
            except Exception:
                continue
            pool_by_gid.setdefault(gid, []).append({"id": item.get("id"), "raw_variant_id": raw_vid})

        for pool in pool_by_gid.values():
            pool.sort(key=lambda it: str(it.get("id") or ""))

        actions: List[Dict[str, Any]] = []
        counts = {"owned_exact": 0, "reroll": 0, "add": 0}

        for gid, required in required_by_gid.items():
            pool = pool_by_gid.get(int(gid)) or []

            action_by_vid: Dict[int, Dict[str, Any]] = {}

            for req in required:
                vid = int(req["variant_id"])
                target_raw = int(req["raw_variant_id"])
                matched = None
                for idx, item in enumerate(pool):
                    if int(item["raw_variant_id"]) == target_raw:
                        matched = pool.pop(idx)
                        break
                if matched is not None:
                    action_by_vid[vid] = {
                        "action": "owned_exact",
                        "from_inventory_gear_id": matched.get("id"),
                        "from_raw_variant_id": int(matched.get("raw_variant_id")),
                    }

            for req in required:
                vid = int(req["variant_id"])
                target_raw = int(req["raw_variant_id"])
                if vid in action_by_vid:
                    continue
                matched = pool.pop(0) if pool else None
                if matched is not None:
                    action_by_vid[vid] = {
                        "action": "reroll",
                        "from_inventory_gear_id": matched.get("id"),
                        "from_raw_variant_id": int(matched.get("raw_variant_id")),
                    }
                else:
                    action_by_vid[vid] = {"action": "add"}

                action_by_vid[vid]["to_raw_variant_id"] = int(target_raw)

            for req in required:
                vid = int(req["variant_id"])
                info = action_by_vid.get(vid) or {"action": "add"}
                row = {
                    "variant_id": vid,
                    "action": str(info.get("action") or "add"),
                    "to_raw_variant_id": int(req["raw_variant_id"]),
                }
                if info.get("from_inventory_gear_id") is not None:
                    row["from_inventory_gear_id"] = info.get("from_inventory_gear_id")
                if info.get("from_raw_variant_id") is not None:
                    row["from_raw_variant_id"] = info.get("from_raw_variant_id")
                actions.append(row)
                counts[row["action"]] = int(counts.get(row["action"], 0)) + 1

        # Strict "current coverage" within the solver's covered set: songs where every used variant is owned exact.
        owned_raw_set: set[int] = set()
        for item in seed_items:
            if item.get("seedable") and item.get("raw_variant_id") is not None:
                try:
                    owned_raw_set.add(int(item["raw_variant_id"]))
                except Exception:
                    pass

        current_song_names: List[str] = []
        assignments = result.get("assignments") or {}
        if isinstance(assignments, dict):
            for song_name, assignment in assignments.items():
                if not isinstance(assignment, dict):
                    continue
                vids = assignment.get("variant_ids") or []
                if not isinstance(vids, list) or len(vids) != 6:
                    continue
                ok = True
                for vid in vids:
                    try:
                        raw = raw_by_variant_id.get(int(vid))
                    except Exception:
                        raw = None
                    if raw is None or int(raw) not in owned_raw_set:
                        ok = False
                        break
                if ok:
                    current_song_names.append(str(song_name))

        seed_diag["inventory_actions"] = {
            "gear_variants": sorted(actions, key=lambda row: int(row.get("variant_id", 0))),
            "stats": counts,
        }
        seed_diag["coverage"] = {"songs_current": len(current_song_names), "songs_current_list": current_song_names}
        result["seeded_inventory"] = seed_diag

    hydrate_force_details(result, db_path=db_path)

    if mem.enabled:
        result["profiling"] = {"memory": mem.records}
    return result


__all__ = ["export_inventory_meta_json", "run_inventory_meta_coverage"]
