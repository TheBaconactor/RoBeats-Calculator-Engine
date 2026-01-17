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
    fetch_peak_candidates_allow_missing,
    fetch_song_names_limited,
    fetch_song_peak,
)
from .export import export_inventory_meta_json, hydrate_force_details
from .gpu_full_solver import solve_coverage_gpu_full
from .keys import (
    ELEMENTS,
    ELEMENT_TO_ID,
    ID_TO_ELEMENT,
    OV_INDEX,
    STAT_KEYS,
    decode_gem_code,
    encode_gem_vec,
    unpack_variant_key,
    variant_key,
)
from .models import CandidateSpec, SongCandidate, SongSpec


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
            freq_sum = sum(gear_freq.get(g, 0) for g in cand.gear_ids)
            src_rank = 0 if cand.candidate.source_table == "loadouts" else 1
            ov_total = int(cand.candidate.gem_totals[OV_INDEX])
            key = (ov_total, -freq_sum, src_rank, cand.candidate.rowid)
            if best is None or key < best_key:
                best = cand
                best_key = key
        if best is None:
            continue
        selected.append(_CoverageSong(song_name=song.name, candidate=best))
    return selected


def _generate_partitions_taichi(
    totals_by_song: Any,
    stat_orders: Any,
    slot_orders: Any,
) -> Any:
    import taichi as ti

    from gear_optimizer.solver.taichi_gem.runtime import init_taichi

    init_taichi()

    totals_np = np.asarray(totals_by_song, dtype=np.int32)
    orders_np = np.asarray(stat_orders, dtype=np.int32)
    slots_np = np.asarray(slot_orders, dtype=np.int32)

    num_songs, k_count, stat_count = orders_np.shape
    out = ti.field(dtype=ti.i32, shape=(num_songs, k_count, 6, stat_count))
    totals = ti.field(dtype=ti.i32, shape=totals_np.shape)
    orders = ti.field(dtype=ti.i32, shape=orders_np.shape)
    slots = ti.field(dtype=ti.i32, shape=slots_np.shape)
    totals.from_numpy(totals_np)
    orders.from_numpy(orders_np)
    slots.from_numpy(slots_np)

    @ti.kernel
    def partition():
        for s in range(num_songs):
            for k in range(k_count):
                slot_sums = ti.Vector.zero(ti.i32, 6)
                for slot in ti.static(range(6)):
                    for stat in ti.static(range(len(STAT_KEYS))):
                        out[s, k, slot, stat] = 0
                for o in ti.static(range(len(STAT_KEYS))):
                    stat = orders[s, k, o]
                    remaining = totals[s, stat]
                    for j in ti.static(range(6)):
                        slot = slots[s, k, j]
                        cap = 15 - slot_sums[slot]
                        if (remaining > 0) and (cap > 0):
                            assign = ti.min(remaining, cap)
                            out[s, k, slot, stat] = assign
                            slot_sums[slot] += assign
                            remaining -= assign

    partition()
    return out.to_numpy()


def _solve_coverage_gpu_full(
    songs: List[_CoverageSong],
    *,
    gear_names: List[str],
    inventory_cap: int,
    partitions_per_song: int,
    seed: int,
    gpu_repack_passes: int,
    gpu_lns_destroy: int,
    adaptive_rounds: int,
    adaptive_patterns_per_round: int,
    adaptive_keep_per_song: int,
    adaptive_repack_songs: int,
    lns_time_sec: float,
    lns_attempts: int,
    mem: _MemoryLogger,
) -> dict:
    if not songs:
        raise ValueError("No songs provided.")

    num_songs = len(songs)
    rng = np.random.default_rng(seed if seed != 0 else None)

    totals_np = np.zeros((num_songs, len(STAT_KEYS)), dtype=np.int32)
    base_orders = np.zeros((num_songs, len(STAT_KEYS)), dtype=np.int32)
    for s_idx, song in enumerate(songs):
        totals = np.array(song.candidate.candidate.gem_totals, dtype=np.int32)
        totals_np[s_idx] = totals
        base_orders[s_idx] = np.array(sorted(range(len(STAT_KEYS)), key=lambda i: (-int(totals[i]), i)), dtype=np.int32)

    k = int(partitions_per_song)
    orders_np = np.zeros((num_songs, k, len(STAT_KEYS)), dtype=np.int32)
    slots_np = np.zeros((num_songs, k, 6), dtype=np.int32)

    stat_lib = [
        np.array(list(range(len(STAT_KEYS))), dtype=np.int32),
        np.array([OV_INDEX] + [i for i in range(len(STAT_KEYS)) if i != OV_INDEX], dtype=np.int32),
        np.array([i for i in range(len(STAT_KEYS)) if i != OV_INDEX] + [OV_INDEX], dtype=np.int32),
    ]
    stat_lib = stat_lib + [x[::-1].copy() for x in stat_lib]
    slot_lib = [
        np.arange(6, dtype=np.int32),
        np.arange(5, -1, -1, dtype=np.int32),
        np.array([0, 2, 4, 1, 3, 5], dtype=np.int32),
        np.array([1, 3, 5, 0, 2, 4], dtype=np.int32),
    ]
    library: List[Tuple[Any, Any]] = []
    for so in stat_lib:
        for sl in slot_lib:
            library.append((so, sl))

    global_orders: List[Any] = []
    global_slots: List[Any] = []
    global_count = max(0, k - 5)
    for kk in range(global_count):
        if kk < len(library):
            o, s = library[kk]
            global_orders.append(o.astype(np.int32, copy=False))
            global_slots.append(s.astype(np.int32, copy=False))
        else:
            global_orders.append(rng.permutation(len(STAT_KEYS)).astype(np.int32))
            global_slots.append(rng.permutation(6).astype(np.int32))

    canonical0 = np.array(list(range(len(STAT_KEYS))), dtype=np.int32)
    canonical1 = np.array([OV_INDEX] + [i for i in range(len(STAT_KEYS)) if i != OV_INDEX], dtype=np.int32)
    canonical2 = np.array([i for i in range(len(STAT_KEYS)) if i != OV_INDEX] + [OV_INDEX], dtype=np.int32)

    for s_idx in range(num_songs):
        base = base_orders[s_idx].tolist()
        if k >= 1:
            orders_np[s_idx, 0] = canonical0
            slots_np[s_idx, 0] = np.arange(6, dtype=np.int32)
        if k >= 2:
            orders_np[s_idx, 1] = canonical1
            slots_np[s_idx, 1] = np.arange(6, dtype=np.int32)
        if k >= 3:
            orders_np[s_idx, 2] = canonical2
            slots_np[s_idx, 2] = np.arange(5, -1, -1, dtype=np.int32)
        if k >= 4:
            orders_np[s_idx, 3] = np.array(base, dtype=np.int32)
            slots_np[s_idx, 3] = np.arange(6, dtype=np.int32)
        if k >= 5:
            moved = [OV_INDEX] + [i for i in base if i != OV_INDEX]
            orders_np[s_idx, 4] = np.array(moved, dtype=np.int32)
            slots_np[s_idx, 4] = np.arange(6, dtype=np.int32)

        for kk in range(5, k):
            orders_np[s_idx, kk] = global_orders[kk - 5]
            slots_np[s_idx, kk] = global_slots[kk - 5]

    mem.log(f"partition_inputs_ready (songs={num_songs}, k={k})")
    partitions_np = _generate_partitions_taichi(totals_np, orders_np, slots_np)
    mem.log("gpu_partitions_generated")

    def build_variant_ids(keys_by_song: Any) -> Tuple[Any, Any, Any]:
        flat = keys_by_song.reshape(-1)
        uniq_keys, inv = np.unique(flat, return_inverse=True)
        part_vids = inv.reshape(keys_by_song.shape[0], keys_by_song.shape[1], 6).astype(np.int32, copy=False)

        variant_freq = np.zeros(len(uniq_keys), dtype=np.int32)
        for s_idx in range(keys_by_song.shape[0]):
            rows = np.ascontiguousarray(part_vids[s_idx])
            row_view = rows.view(np.dtype((np.void, rows.dtype.itemsize * rows.shape[1])))
            _, idx = np.unique(row_view, return_index=True)
            uniq_rows = rows[idx]
            np.add.at(variant_freq, uniq_rows.reshape(-1), 1)

        return uniq_keys, part_vids, variant_freq

    def solve_once(keys_by_song: Any, *, lns_time: float) -> Tuple[Any, Any, Any, Any, Any, Any, Any, Any]:
        uniq_keys, part_vids, variant_freq = build_variant_ids(keys_by_song)
        mem.log(f"gpu_full_inputs_ready (songs={num_songs}, k={keys_by_song.shape[1]}, variants={len(uniq_keys)})")
        sol = solve_coverage_gpu_full(
            part_vids,
            variant_freq,
            inventory_cap=inventory_cap,
            seed=seed,
            repack_passes=gpu_repack_passes,
            lns_time_sec=float(lns_time),
            lns_attempts=lns_attempts,
            lns_destroy=gpu_lns_destroy,
            profile=bool(mem.enabled),
        )
        mem.log("gpu_full_solved")

        covered = [bool(int(x)) for x in sol.covered.tolist()]
        chosen_part = [int(x) if int(x) >= 0 else None for x in sol.chosen_part.tolist()]
        counts_np = np.asarray(sol.counts, dtype=np.int32)
        used_vids = np.flatnonzero(counts_np > 0).astype(np.int32)
        used_vids.sort()
        return sol, uniq_keys, part_vids, variant_freq, counts_np, covered, chosen_part, used_vids

    keys_np = np.zeros((num_songs, k, 6), dtype=np.int64)
    num_elements = len(ELEMENTS)
    for s_idx, song in enumerate(songs):
        element_id = song.candidate.element_id
        for kk in range(k):
            for slot_idx in range(6):
                vec = tuple(int(partitions_np[s_idx, kk, slot_idx, stat_idx]) for stat_idx in range(len(STAT_KEYS)))
                code = encode_gem_vec(vec)
                ov = vec[OV_INDEX]
                ov_color = int(element_id) if ov > 0 else 0
                if ov_color < 0 or ov_color > num_elements:
                    ov_color = 0
                gid = int(song.candidate.gear_ids[slot_idx])
                keys_np[s_idx, kk, slot_idx] = variant_key(gid, code, ov_color)

    adaptive_round_stats: List[dict] = []
    best_state: Optional[Tuple[Any, Any, Any, Any, Any, Any, Any, Any]] = None
    best_keys_np: Optional[Any] = None

    def maybe_update_best(keys_snapshot: Any, state: Any) -> None:
        nonlocal best_state, best_keys_np
        sol = state[0]
        cov = int(sol.covered_count)
        inv_used = int(sol.inventory_size)
        if best_state is None:
            best_state = state
            best_keys_np = keys_snapshot
            return
        b_sol = best_state[0]
        b_cov = int(b_sol.covered_count)
        b_inv = int(b_sol.inventory_size)
        if (cov > b_cov) or (cov == b_cov and inv_used < b_inv):
            best_state = state
            best_keys_np = keys_snapshot

    mem.log("gpu_full_round0_solve")
    state = solve_once(keys_np, lns_time=0.0)
    maybe_update_best(keys_np, state)

    rng_adapt = np.random.default_rng(seed if seed != 0 else None)
    for round_idx in range(int(adaptive_rounds)):
        sol, uniq_keys, part_vids, _vf, counts_np, covered, chosen_part, used_vids = state
        uncovered_idx = [i for i in range(num_songs) if not covered[i]]
        if not uncovered_idx:
            break

        inventory_keys = set(int(x) for x in uniq_keys[np.asarray(used_vids, dtype=np.int32)].tolist())

        repair_idx: List[int] = []
        if adaptive_repack_songs > 0:
            scored: List[Tuple[int, int]] = []
            for s_idx in range(num_songs):
                if not covered[s_idx]:
                    continue
                p = chosen_part[s_idx]
                if p is None:
                    continue
                vids = part_vids[s_idx, int(p)]
                uniq = int(np.sum(counts_np[vids] == 1))
                if uniq > 0:
                    scored.append((-uniq, int(s_idx)))
            scored.sort()
            repair_idx = [s for _, s in scored[: int(adaptive_repack_songs)]]

        candidate_idx: List[int] = uncovered_idx + [s for s in repair_idx if s not in uncovered_idx]
        if not candidate_idx:
            break

        totals_sub = totals_np[candidate_idx]
        k_new = int(adaptive_patterns_per_round)
        orders_new = np.zeros((len(candidate_idx), k_new, len(STAT_KEYS)), dtype=np.int32)
        slots_new = np.zeros((len(candidate_idx), k_new, 6), dtype=np.int32)

        stat_lib2 = [
            canonical0,
            canonical1,
            canonical2,
            canonical0[::-1],
            canonical1[::-1],
        ]
        slot_lib2 = [
            np.arange(6, dtype=np.int32),
            np.arange(5, -1, -1, dtype=np.int32),
            np.array([0, 2, 4, 1, 3, 5], dtype=np.int32),
            np.array([1, 3, 5, 0, 2, 4], dtype=np.int32),
        ]
        library2: List[Tuple[Any, Any]] = []
        for so in stat_lib2:
            for sl in slot_lib2:
                library2.append((so, sl))

        global_orders2: List[Any] = []
        global_slots2: List[Any] = []
        for kk in range(k_new):
            if kk < len(library2):
                o, s = library2[kk]
                global_orders2.append(o.astype(np.int32))
                global_slots2.append(s.astype(np.int32))
            else:
                global_orders2.append(rng_adapt.permutation(len(STAT_KEYS)).astype(np.int32))
                global_slots2.append(rng_adapt.permutation(6).astype(np.int32))

        for si in range(len(candidate_idx)):
            for kk in range(k_new):
                orders_new[si, kk] = global_orders2[kk]
                slots_new[si, kk] = global_slots2[kk]

        mem.log(f"adaptive_full_partitions_generate (round={round_idx + 1}, songs={len(candidate_idx)}, k={k_new})")
        parts_np = _generate_partitions_taichi(totals_sub, orders_new, slots_new)
        mem.log("adaptive_full_gpu_partitions_generated")

        append_block = np.repeat(keys_np[:, :1, :], repeats=int(adaptive_keep_per_song), axis=1)
        added_distinct = 0
        for sub_i, s_idx in enumerate(candidate_idx):
            song = songs[int(s_idx)]
            element_id = song.candidate.element_id
            seen = {tuple(row.tolist()) for row in keys_np[int(s_idx)]}
            scored_parts: List[Tuple[int, int, Tuple[int, ...]]] = []

            for kk in range(k_new):
                keys: List[int] = []
                for slot_idx in range(6):
                    vec = tuple(int(parts_np[sub_i, kk, slot_idx, stat_idx]) for stat_idx in range(len(STAT_KEYS)))
                    code = encode_gem_vec(vec)
                    ov = vec[OV_INDEX]
                    ov_color = int(element_id) if ov > 0 else 0
                    if ov_color < 0 or ov_color > num_elements:
                        ov_color = 0
                    gid = int(song.candidate.gear_ids[slot_idx])
                    keys.append(variant_key(gid, code, ov_color))
                t = tuple(keys)
                if t in seen:
                    continue
                cost = sum(1 for key in keys if int(key) not in inventory_keys)
                scored_parts.append((int(cost), int(kk), t))

            scored_parts.sort(key=lambda x: (x[0], x[1]))
            kept = scored_parts[: int(adaptive_keep_per_song)]
            for out_i, (_cost, _kk, t) in enumerate(kept):
                append_block[int(s_idx), out_i, :] = np.asarray(t, dtype=np.int64)
                seen.add(t)
                added_distinct += 1

        keys_np = np.concatenate([keys_np, append_block], axis=1)
        adaptive_round_stats.append(
            {
                "round": round_idx + 1,
                "candidate_songs": len(candidate_idx),
                "added_partitions_distinct": int(added_distinct),
                "k_total": int(keys_np.shape[1]),
            }
        )

        mem.log(f"adaptive_full_round{round_idx + 1}_solve")
        state = solve_once(keys_np, lns_time=0.0)
        maybe_update_best(keys_np, state)

    assert best_state is not None
    assert best_keys_np is not None

    final_state = best_state
    if float(lns_time_sec) > 0:
        mem.log("gpu_full_final_lns_solve")
        lns_state = solve_once(best_keys_np, lns_time=float(lns_time_sec))
        maybe_update_best(best_keys_np, lns_state)
        final_state = best_state

    sol, uniq_keys, part_vids, _vf, counts_np, covered, chosen_part, used_vids = final_state

    used_vids = np.asarray(used_vids, dtype=np.int32)
    vid_to_id = {int(vid): idx for idx, vid in enumerate(used_vids.tolist())}

    variants_out: List[dict] = []
    for idx, vid in enumerate(used_vids.tolist()):
        key = int(uniq_keys[int(vid)])
        gid, gem_code, ov_color_id = unpack_variant_key(key)
        gear_name = gear_names[gid - 1] if gid > 0 else ""
        vec = decode_gem_code(gem_code)
        variants_out.append(
            {
                "id": idx,
                "gear_name": gear_name,
                "gems": {STAT_KEYS[i]: int(vec[i]) for i in range(len(STAT_KEYS))},
                "ov_color": ID_TO_ELEMENT.get(int(ov_color_id), "") if ov_color_id else "",
            }
        )

    minis_used: set[str] = set()
    assignments: Dict[str, dict] = {}
    for s_idx, song in enumerate(songs):
        if not covered[s_idx]:
            continue
        p_idx = chosen_part[s_idx]
        if p_idx is None:
            continue
        cand = song.candidate.candidate

        minis = set()
        for group in cand.mini_groups:
            minis.update(group)
        minis_used.update(minis)

        vids = part_vids[s_idx, int(p_idx)]
        assignments[song.song_name] = {
            "source_table": cand.source_table,
            "candidate_rowid": cand.rowid,
            "score": cand.score,
            "fg_score": cand.fg_score,
            "gear": list(cand.gear_names),
            "selected_element": cand.selected_element,
            "gem_totals": {STAT_KEYS[i]: int(cand.gem_totals[i]) for i in range(len(STAT_KEYS))},
            "variant_ids": [int(vid_to_id[int(v)]) for v in vids.tolist()],
            "minis": sorted(minis),
            "force_details": None,
        }

    uncovered_songs = [songs[i].song_name for i in range(num_songs) if not covered[i]]
    solution = {
        "mode": "coverage_gpu_full",
        "inventory": {"gear_variants": variants_out, "minis": sorted(minis_used)},
        "assignments": assignments,
        "uncovered_songs": uncovered_songs,
        "stats": {
            "songs_total": num_songs,
            "songs_covered": int(sol.covered_count),
            "gear_variants_used": len(variants_out),
            "gear_variants_cap": inventory_cap,
            "partitions_per_song": partitions_per_song,
        },
        "solver_stats": {
            "status": "GPU_FULL_HEURISTIC",
            "seed": seed,
            "gpu_full": sol.stats,
            "gpu_repack_passes": gpu_repack_passes,
            "gpu_lns_destroy": gpu_lns_destroy,
            "lns": {
                "enabled": bool(float(lns_time_sec) > 0),
                "time_sec": float(lns_time_sec),
                "attempts": int(lns_attempts),
            },
            "adaptive": {
                "rounds_requested": adaptive_rounds,
                "rounds_used": len(adaptive_round_stats),
                "round_stats": adaptive_round_stats,
            },
        },
    }
    return solution


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
) -> dict:
    """
    Inventory Meta coverage mode (GPU-only optimization loop):
    - Picks ONE peak row per song (top peak; tie broken heuristically).
    - Generates many valid gem partitions per song on GPU.
    - Selects songs to maximize covered songs under `inventory_cap`.
    Minis are not constrained; duplicates are ignored.
    """
    inventory_cap = int(inventory_cap)
    if inventory_cap <= 0:
        raise ValueError("inventory_cap must be positive.")
    partitions_per_song = int(partitions_per_song)
    if partitions_per_song <= 0:
        raise ValueError("partitions_per_song must be positive.")
    restarts = int(restarts)
    if restarts <= 0:
        raise ValueError("restarts must be positive.")
    gpu_repack_passes = int(gpu_repack_passes)
    if gpu_repack_passes < 0:
        raise ValueError("gpu_repack_passes must be >= 0.")
    gpu_lns_destroy = int(gpu_lns_destroy)
    if gpu_lns_destroy < 0:
        raise ValueError("gpu_lns_destroy must be >= 0.")
    adaptive_rounds = int(adaptive_rounds)
    if adaptive_rounds < 0:
        raise ValueError("adaptive_rounds must be >= 0.")
    adaptive_patterns_per_round = int(adaptive_patterns_per_round)
    if adaptive_patterns_per_round <= 0:
        raise ValueError("adaptive_patterns_per_round must be positive.")
    adaptive_keep_per_song = int(adaptive_keep_per_song)
    if adaptive_keep_per_song <= 0:
        raise ValueError("adaptive_keep_per_song must be positive.")
    adaptive_repack_songs = int(adaptive_repack_songs)
    if adaptive_repack_songs < 0:
        raise ValueError("adaptive_repack_songs must be >= 0.")
    lns_time_sec = float(lns_time_sec)
    if lns_time_sec < 0:
        raise ValueError("lns_time_sec must be >= 0.")
    lns_attempts = int(lns_attempts)
    if lns_attempts <= 0:
        raise ValueError("lns_attempts must be positive.")

    mem = _MemoryLogger(enabled=bool(profile))
    mem.log("start")

    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Evolution DB not found: {db_path}")

    conn = get_db_connection(db_path)
    try:
        mem.log("db_connected")
        if song_limit is not None:
            song_names = fetch_song_names_limited(conn, int(song_limit))
            candidates_by_song: Dict[str, List[SongCandidate]] = {}
            missing: List[str] = []
            for name in song_names:
                peak, base_peak, fg_peak = fetch_song_peak(conn, name)
                cands = fetch_candidates_for_peak(conn, name, peak, base_peak, fg_peak)
                if not cands:
                    missing.append(name)
                    continue
                candidates_by_song[name] = cands
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

    best_result: Optional[dict] = None
    best_seed: Optional[int] = None
    for r in range(restarts):
        run_seed = int(seed) + r if int(seed) != 0 else 0
        if profile and restarts > 1:
            mem.log(f"restart_{r + 1}_of_{restarts} (seed={run_seed})")
        result = _solve_coverage_gpu_full(
            selected_specs,
            gear_names=gear_names,
            inventory_cap=inventory_cap,
            partitions_per_song=partitions_per_song,
            seed=run_seed,
            gpu_repack_passes=gpu_repack_passes,
            gpu_lns_destroy=gpu_lns_destroy,
            adaptive_rounds=adaptive_rounds,
            adaptive_patterns_per_round=adaptive_patterns_per_round,
            adaptive_keep_per_song=adaptive_keep_per_song,
            adaptive_repack_songs=adaptive_repack_songs,
            lns_time_sec=lns_time_sec,
            lns_attempts=lns_attempts,
            mem=mem,
        )
        if best_result is None:
            best_result = result
            best_seed = run_seed
            continue
        b = best_result.get("stats", {})
        c = result.get("stats", {})
        b_cov = int(b.get("songs_covered", 0))
        c_cov = int(c.get("songs_covered", 0))
        if c_cov > b_cov:
            best_result = result
            best_seed = run_seed
            continue
        if c_cov == b_cov:
            b_used = int(b.get("gear_variants_used", 10**9))
            c_used = int(c.get("gear_variants_used", 10**9))
            if c_used < b_used:
                best_result = result
                best_seed = run_seed

    assert best_result is not None
    result = best_result
    result.setdefault("solver_stats", {})["restarts"] = restarts
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
