from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class GemClusterReport:
    k: int
    songs_total: int
    features: List[str]
    clusters: List[dict]
    outliers: List[dict]


def _quantiles(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if x.size == 0:
        return {"min": 0, "q1": 0, "median": 0, "q3": 0, "max": 0, "mean": 0}
    q1, med, q3 = np.quantile(x, [0.25, 0.5, 0.75]).tolist()
    return {
        "min": float(np.min(x)),
        "q1": float(q1),
        "median": float(med),
        "q3": float(q3),
        "max": float(np.max(x)),
        "mean": float(np.mean(x)),
    }


def _kmeans_pp_init(x: np.ndarray, k: int, *, rng: np.random.Generator) -> np.ndarray:
    n = int(x.shape[0])
    if k <= 0:
        raise ValueError("k must be positive.")
    if n <= 0:
        raise ValueError("x must be non-empty.")

    centers = np.zeros((k, x.shape[1]), dtype=np.float64)
    first = int(rng.integers(low=0, high=n))
    centers[0] = x[first]

    d2 = np.sum((x - centers[0]) ** 2, axis=1)
    for i in range(1, k):
        total = float(np.sum(d2))
        if not np.isfinite(total) or total <= 0.0:
            centers[i] = x[int(rng.integers(low=0, high=n))]
            continue
        r = float(rng.random()) * total
        acc = 0.0
        idx = 0
        for j in range(n):
            acc += float(d2[j])
            if acc >= r:
                idx = j
                break
        centers[i] = x[idx]
        d2 = np.minimum(d2, np.sum((x - centers[i]) ** 2, axis=1))
    return centers


def kmeans_cluster(
    x: np.ndarray,
    *,
    k: int,
    seed: int = 1,
    iters: int = 50,
    restarts: int = 8,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simple k-means (numpy-only).

    Returns:
      (labels, centers)
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("x must be 2D.")
    n = int(x.shape[0])
    if n <= 0:
        raise ValueError("x must be non-empty.")
    k = int(k)
    if k <= 0:
        raise ValueError("k must be positive.")
    k = min(k, n)

    iters = max(1, int(iters))
    restarts = max(1, int(restarts))
    rng = np.random.default_rng(int(seed) ^ 0xC0FFEE)

    best_inertia = float("inf")
    best_labels = None
    best_centers = None

    for r in range(restarts):
        r_rng = np.random.default_rng(int(seed) ^ (r * 0x9E3779B9) ^ 0xA5A5A5A5)
        centers = _kmeans_pp_init(x, k, rng=r_rng)
        labels = np.zeros((n,), dtype=np.int32)

        for _ in range(iters):
            d2 = np.sum((x[:, None, :] - centers[None, :, :]) ** 2, axis=2)
            new_labels = np.argmin(d2, axis=1).astype(np.int32, copy=False)
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels
            for j in range(k):
                mask = labels == j
                if not np.any(mask):
                    centers[j] = x[int(r_rng.integers(low=0, high=n))]
                else:
                    centers[j] = np.mean(x[mask], axis=0)

        d2 = np.sum((x - centers[labels]) ** 2, axis=1)
        inertia = float(np.sum(d2))
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()
            best_centers = centers.copy()

    assert best_labels is not None and best_centers is not None
    return best_labels, best_centers


def build_gem_cluster_report(
    *,
    song_names: Sequence[str],
    features: Sequence[str],
    x: np.ndarray,
    labels: np.ndarray,
    centers: np.ndarray,
    outlier_limit: int = 25,
) -> GemClusterReport:
    x = np.asarray(x, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int32).reshape(-1)
    centers = np.asarray(centers, dtype=np.float64)
    if x.shape[0] != labels.shape[0] or x.shape[0] != len(song_names):
        raise ValueError("song_names/x/labels length mismatch.")

    k = int(centers.shape[0])
    clusters: List[dict] = []
    outliers: List[dict] = []

    d2 = np.sum((x - centers[labels]) ** 2, axis=1)
    outlier_idx = np.argsort(d2)[::-1][: int(max(0, outlier_limit))]
    for idx in outlier_idx.tolist():
        outliers.append(
            {
                "song": str(song_names[int(idx)]),
                "cluster": int(labels[int(idx)]),
                "dist2": float(d2[int(idx)]),
                "gem_totals": {str(features[j]): int(round(float(x[int(idx), j]))) for j in range(int(x.shape[1]))},
            }
        )

    for c in range(k):
        mask = labels == c
        xs = x[mask]
        cluster_songs = [str(song_names[i]) for i in np.where(mask)[0].tolist()]
        clusters.append(
            {
                "cluster": int(c),
                "songs": int(xs.shape[0]),
                "centroid": {str(features[j]): float(centers[c, j]) for j in range(int(x.shape[1]))},
                "distribution": {str(features[j]): _quantiles(xs[:, j]) for j in range(int(x.shape[1]))},
                "song_names": cluster_songs,
            }
        )

    clusters.sort(key=lambda rec: (-int(rec["songs"]), int(rec["cluster"])))
    return GemClusterReport(
        k=int(k),
        songs_total=int(x.shape[0]),
        features=[str(f) for f in features],
        clusters=clusters,
        outliers=outliers,
    )


def _allocate_cluster_caps(cluster_sizes: List[int], *, total_cap: int) -> List[int]:
    total_cap = int(total_cap)
    if total_cap <= 0:
        return [0 for _ in cluster_sizes]
    sizes = [max(0, int(s)) for s in cluster_sizes]
    denom = max(1, int(sum(sizes)))
    raw = [float(total_cap) * float(s) / float(denom) for s in sizes]
    caps = [int(np.floor(v)) for v in raw]
    remaining = int(total_cap - sum(caps))
    # Largest remainder method.
    frac = sorted([(i, raw[i] - float(caps[i])) for i in range(len(sizes))], key=lambda t: (-t[1], t[0]))
    for i, _ in frac:
        if remaining <= 0:
            break
        caps[i] += 1
        remaining -= 1
    return caps


def run_clustered_gpu_full_coverage(
    *,
    candidates_by_song: Dict[str, list],
    inventory_cap: int,
    cluster_k: int,
    cluster_seed: int,
    bridge_reserve: int,
    seed: int,
    partitions_per_song: int,
    adaptive_rounds: int,
    adaptive_keep_per_song: int,
    gpu_repack_passes: int,
    gpu_lns_destroy: int,
    lns_time_sec: float,
    lns_attempts: int,
    gpu_full_witness_palettes: int,
    gpu_full_witness_pattern_profile: int,
    gpu_full_witness_anchor_patterns: int,
    gpu_full_witness_seed_streams: int,
    wildcard_freq_bonus: int,
    gpu_full_variant_freq_mode: str,
    gpu_full_counter_stripes: int,
    gpu_full_k_scan_select: int,
    gpu_full_k_scan_repack: int,
    gpu_full_alns_enabled: bool,
    gpu_full_alns_islands: int,
    gpu_full_pt_enabled: bool,
    gpu_full_pt_t_min: float,
    gpu_full_pt_t_max: float,
    gpu_full_pt_swap_interval: int,
    gpu_full_pt_destroy_beta: float,
    gpu_full_pt_cap_slack_max: int,
    gpu_full_repair_enabled: bool,
    gpu_full_repair_attempts: int,
    gpu_full_repair_max_cands_per_slot: int,
    gpu_full_repair_song_limit: int,
    gpu_full_lns_freq_weighted: bool,
    profile: bool,
) -> Tuple[dict, GemClusterReport]:
    """
    Cluster songs by peak `gem_totals`, solve per-cluster with a progressive cap,
    then run a final "bridge" solve seeded with the union inventory.

    Returns:
      (final_solution_dict, cluster_report)
    """
    from . import coverage as cov
    from .gpu_witness_pool import build_witness_offsets_gpu

    # Global stable ID maps (required so seeded raw IDs remain meaningful across cluster solves).
    gear_names = cov._collect_gear_names(candidates_by_song)
    gear_id_map = {name: idx + 1 for idx, name in enumerate(gear_names)}
    mini_names = cov._collect_mini_names(candidates_by_song)
    mini_id_map = {name: idx for idx, name in enumerate(mini_names)}

    song_specs = cov._build_song_specs(candidates_by_song, gear_id_map, mini_id_map)
    selected = cov._select_one_peak_candidate_per_song(song_specs)

    # Build clustering features from selected peak candidates.
    features = list(cov.STAT_KEYS)
    song_names = [s.song_name for s in selected]
    x = np.asarray([list(s.candidate.candidate.gem_totals) for s in selected], dtype=np.float64)

    labels, centers = kmeans_cluster(x, k=int(cluster_k), seed=int(cluster_seed))
    report = build_gem_cluster_report(song_names=song_names, features=features, x=x, labels=labels, centers=centers)

    total_cap = int(inventory_cap)
    bridge_reserve = max(0, int(bridge_reserve))
    cluster_budget = max(0, int(total_cap - bridge_reserve))

    # Solve clusters from largest->smallest so early seeds are broadly reusable.
    cluster_ids = sorted(range(int(report.k)), key=lambda c: (-int(np.sum(labels == c)), int(c)))
    cluster_sizes = [int(np.sum(labels == c)) for c in cluster_ids]
    cluster_caps = _allocate_cluster_caps(cluster_sizes, total_cap=cluster_budget)

    seeded_raw: set[int] = set()
    covered_global: set[str] = set()
    cap_so_far = 0

    # Build cluster solves (warm-start inventory).
    for step, c in enumerate(cluster_ids):
        idxs = np.where(labels == int(c))[0].tolist()
        if not idxs:
            continue
        cap_so_far += int(cluster_caps[step])
        cap_so_far = min(int(cluster_budget), int(cap_so_far))
        if cap_so_far <= 0:
            continue

        cluster_selected = [selected[i] for i in idxs]
        gear_ids_np, totals_np, elements_np, gear_freq_np = cov._build_gpu_dynamic_inputs(cluster_selected, gear_names=gear_names)

        k_total = int(partitions_per_song) + int(adaptive_rounds) * int(adaptive_keep_per_song)
        k_total = max(int(partitions_per_song), int(k_total))
        offsets_np, wp_stats = build_witness_offsets_gpu(
            gear_ids_np,
            totals_np,
            elements_np,
            gear_freq_np,
            k_total=int(k_total),
            seed=int(seed) ^ int((int(c) + 1) * 0x9E3779B9),
            anchor_patterns=int(gpu_full_witness_anchor_patterns),
            seed_streams=int(gpu_full_witness_seed_streams),
            pattern_profile=int(gpu_full_witness_pattern_profile),
            wildcard_palette_vecs=None,
            wildcard_palette_scan=8,
            wildcard_palette_tail_slots=3,
            profile=bool(profile),
        )

        seed_arr = None
        if seeded_raw:
            seed_arr = np.asarray(sorted(seeded_raw), dtype=np.int32)

        mem = cov._MemoryLogger(enabled=bool(profile))
        sol = cov._run_gpu_full_solver_from_offsets(
            gear_ids_np,
            offsets_np,
            inventory_cap=int(cap_so_far),
            seed=int(seed),
            gpu_repack_passes=int(gpu_repack_passes),
            gpu_full_repack_rarity_weighted=False,
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
            gpu_full_lns_random_destroy_prob=0.0,
            gpu_full_lns_restore_after=12,
            gpu_full_lns_restore_drop=4,
            gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
            gpu_full_counter_stripes=int(gpu_full_counter_stripes),
            gpu_full_human_mode=False,
            gpu_full_human_gear_free=2,
            gpu_full_human_gear_penalty_step=0,
            gpu_full_human_colored_penalty=0,
            synergy_weight=0,
            synergy_top_offsets=128,
            synergy_min_pair_count=2,
            synergy_scale=256,
            synergy_max_bonus=4095,
            new_gear_penalty=0,
            mem=mem,
            wp_stats=wp_stats,
            dense_vid_universe=None,
            v_pad_bin=4096,
            wildcard_freq_bonus=int(wildcard_freq_bonus),
            seeded_raw_vids=seed_arr,
        )

        covered_np = np.asarray(sol.covered, dtype=np.int32)
        chosen_offsets = np.asarray(sol.chosen_offsets, dtype=np.int32)
        # Track covered songs and seed inventory variants from this cluster.
        for local_idx, is_cov in enumerate(covered_np.tolist()):
            if int(is_cov) > 0:
                covered_global.add(str(cluster_selected[local_idx].song_name))
                for j in range(6):
                    gid = int(gear_ids_np[local_idx, j])
                    off = int(chosen_offsets[local_idx, j])
                    seeded_raw.add((gid << 16) | (off & 0xFFFF))

    # Final "bridge" solve over all songs (coherent assignments), seeded with the union inventory.
    seed_arr = np.asarray(sorted(seeded_raw), dtype=np.int32) if seeded_raw else None
    gear_ids_np_all, totals_np_all, elements_np_all, gear_freq_np_all = cov._build_gpu_dynamic_inputs(selected, gear_names=gear_names)
    k_total = int(partitions_per_song) + int(adaptive_rounds) * int(adaptive_keep_per_song)
    k_total = max(int(partitions_per_song), int(k_total))
    offsets_np_all, wp_stats_all = build_witness_offsets_gpu(
        gear_ids_np_all,
        totals_np_all,
        elements_np_all,
        gear_freq_np_all,
        k_total=int(k_total),
        seed=int(seed),
        anchor_patterns=int(gpu_full_witness_anchor_patterns),
        seed_streams=int(gpu_full_witness_seed_streams),
        pattern_profile=int(gpu_full_witness_pattern_profile),
        wildcard_palette_vecs=None,
        wildcard_palette_scan=8,
        wildcard_palette_tail_slots=3,
        profile=bool(profile),
    )

    mem = cov._MemoryLogger(enabled=bool(profile))
    sol_all = cov._run_gpu_full_solver_from_offsets(
        gear_ids_np_all,
        offsets_np_all,
        inventory_cap=int(total_cap),
        seed=int(seed),
        gpu_repack_passes=int(gpu_repack_passes),
        gpu_full_repack_rarity_weighted=False,
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
        gpu_full_lns_random_destroy_prob=0.0,
        gpu_full_lns_restore_after=12,
        gpu_full_lns_restore_drop=4,
        gpu_full_variant_freq_mode=str(gpu_full_variant_freq_mode),
        gpu_full_counter_stripes=int(gpu_full_counter_stripes),
        gpu_full_human_mode=False,
        gpu_full_human_gear_free=2,
        gpu_full_human_gear_penalty_step=0,
        gpu_full_human_colored_penalty=0,
        synergy_weight=0,
        synergy_top_offsets=128,
        synergy_min_pair_count=2,
        synergy_scale=256,
        synergy_max_bonus=4095,
        new_gear_penalty=0,
        mem=mem,
        wp_stats=wp_stats_all,
        dense_vid_universe=None,
        v_pad_bin=4096,
        wildcard_freq_bonus=int(wildcard_freq_bonus),
        seeded_raw_vids=seed_arr,
    )

    # Match the main coverage path: attempt inventory-aware repair using ONLY existing inventory variants.
    # This preserves "exact peak" constraints and does not increase inventory size.
    if bool(gpu_full_repair_enabled):
        old_sol = sol_all
        covered_np = np.asarray(sol_all.covered, dtype=np.int32)
        chosen_offsets_np = np.asarray(sol_all.chosen_offsets, dtype=np.int32)
        seeded_pairs = None
        if seed_arr is not None and int(seed_arr.size) > 0:
            gids = (seed_arr >> np.int32(16)).astype(np.int32, copy=False)
            offs = (seed_arr & np.int32(0xFFFF)).astype(np.int32, copy=False)
            seeded_pairs = list(zip(gids.tolist(), offs.tolist()))
        repaired_cov, repaired_offsets, repair_stats = cov._try_inventory_repair(
            songs=selected,
            gear_ids_np=gear_ids_np_all,
            totals_np=totals_np_all,
            elements_np=elements_np_all,
            covered_np=covered_np,
            chosen_offsets_np=chosen_offsets_np,
            inv_cap=int(total_cap),
            attempts=int(gpu_full_repair_attempts),
            seed=int(seed),
            max_cands_per_slot=int(gpu_full_repair_max_cands_per_slot),
            song_limit=int(gpu_full_repair_song_limit),
            mem=mem,
            profile=bool(profile),
            seeded_pairs=seeded_pairs,
        )
        from types import SimpleNamespace

        sol_all = SimpleNamespace(
            covered=repaired_cov,
            chosen_offsets=repaired_offsets,
            covered_count=int(repaired_cov.sum()),
            stats=dict(getattr(old_sol, "stats", {})),
            dense_vid_universe=getattr(old_sol, "dense_vid_universe", None),
        )
        if isinstance(sol_all.stats, dict):
            sol_all.stats.setdefault("repair", repair_stats)

    final = cov._materialize_coverage_solution(
        selected,
        gear_names=gear_names,
        gear_ids_np=gear_ids_np_all,
        sol=sol_all,
        mode="coverage_gpu_full_clustered",
        solver_status="ok",
        inventory_cap=int(total_cap),
        seed=int(seed),
        gpu_repack_passes=int(gpu_repack_passes),
        gpu_lns_destroy=int(gpu_lns_destroy),
        lns_time_sec=float(lns_time_sec),
        lns_attempts=int(lns_attempts),
        mem=mem,
        legacy_args={
            "cluster_k": int(cluster_k),
            "bridge_reserve": int(bridge_reserve),
            "cluster_budget": int(cluster_budget),
        },
    )
    final["stats"]["clustered_seed_variants"] = int(len(seeded_raw))
    final["stats"]["clustered_precovered_songs"] = int(len(covered_global))
    return final, report


def write_cluster_report_json(report: GemClusterReport, path: str) -> None:
    payload = {
        "k": int(report.k),
        "songs_total": int(report.songs_total),
        "features": list(report.features),
        "clusters": list(report.clusters),
        "outliers": list(report.outliers),
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, indent=2, ensure_ascii=False))
        f.write("\n")
