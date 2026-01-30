from __future__ import annotations

import argparse
import json
import random
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.data.database import get_db_connection
from inventory_optimizer.coverage import _build_gpu_dynamic_inputs, _build_song_specs, _pack_part_vids_dense, _select_one_peak_candidate_per_song
from inventory_optimizer.db import fetch_peak_candidates_allow_missing, fetch_song_names, fetch_song_peak
from inventory_optimizer.gpu_full_solver import solve_coverage_gpu_full
from inventory_optimizer.gpu_witness_pool import build_witness_offsets_gpu
from inventory_optimizer.seed_inventory import normalize_for_lookup


def _load_universe(path: Path) -> Tuple[List[dict], Dict[Tuple[str, int], int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    variants = payload.get("variants") if isinstance(payload, dict) else None
    if not isinstance(variants, list) or not variants:
        raise ValueError(f"Invalid universe JSON (missing variants list): {path}")

    key_to_idx: Dict[Tuple[str, int], int] = {}
    for idx, v in enumerate(variants):
        if not isinstance(v, dict):
            continue
        name = str(v.get("gear_name") or "").strip()
        off = v.get("offset")
        if not name:
            continue
        try:
            off_i = int(off)
        except Exception:
            continue
        key_to_idx[(normalize_for_lookup(name), off_i)] = int(idx)
    return variants, key_to_idx


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a toy transformer dataset via repeated GPU solves.")
    ap.add_argument("--db-path", type=str, required=True, help="SQLite snapshot path (DO NOT use live evolution.db).")
    ap.add_argument("--universe", type=str, required=True, help="Variant universe JSON (gear_name+offset list).")
    ap.add_argument("--out", type=str, required=True, help="Output dataset .pt path.")
    ap.add_argument("--examples", type=int, default=200, help="Number of training examples (default: 200).")
    ap.add_argument("--subset-size", type=int, default=128, help="Songs per example (default: 128).")
    ap.add_argument("--inventory-cap", type=int, default=30, help="Inventory cap per example (default: 30).")
    ap.add_argument("--k", type=int, default=128, help="Witness patterns per song (default: 128).")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed (default: 1).")
    ap.add_argument(
        "--label-mode",
        type=str,
        default="binary",
        choices=["binary", "usage_frac", "song_support"],
        help=(
            "Label encoding: binary (used/not used), usage_frac (counts/covered_count; inproc only), "
            "or song_support (covered-song support fraction; inproc only)."
        ),
    )
    ap.add_argument(
        "--label-weighting",
        type=str,
        default="none",
        choices=["none", "covered_linear"],
        help="Optional label weighting: 'covered_linear' scales labels by covered_count/subset_size.",
    )
    ap.add_argument(
        "--v-pad-bin",
        type=int,
        default=16384,
        help="GPU full: pad V to this bin (stabilizes shapes for inproc mode; default: 16384).",
    )
    ap.add_argument(
        "--mode",
        type=str,
        default="inproc",
        choices=["inproc", "subprocess"],
        help="Generation mode (default: inproc).",
    )
    args = ap.parse_args()

    db_path = Path(args.db_path)
    universe_path = Path(args.universe)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure all downstream code (inventory_optimizer) reads from the snapshot, not the live DB.
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)

    universe_variants, universe_key_to_idx = _load_universe(universe_path)
    v_count = len(universe_variants)

    label_mode = str(args.label_mode or "binary").strip().lower()
    if str(args.mode) != "inproc" and label_mode != "binary":
        raise SystemExit("--label-mode usage_frac/song_support is only supported with --mode inproc.")

    # Load DB candidates. In inproc mode, prefer the *candidate-backed* song set to keep IDs aligned.
    conn = get_db_connection(str(db_path))
    try:
        candidates_by_song_all = None
        if str(args.mode) == "inproc":
            candidates_by_song_all, missing = fetch_peak_candidates_allow_missing(conn)
            all_songs = sorted(candidates_by_song_all.keys())
            song_peaks = {
                name: max(max(int(c.score), int(c.fg_score)) for c in cands) for name, cands in candidates_by_song_all.items()
            }
            if missing:
                print(f"[inproc] skipped missing candidate rows: {len(missing)} songs")
        else:
            all_songs = fetch_song_names(conn)
            # Also record the current peak per song for optional analysis/debugging.
            song_peaks = {name: int(fetch_song_peak(conn, name)[0]) for name in all_songs}
    finally:
        conn.close()

    if not all_songs:
        raise SystemExit("No songs found in DB snapshot.")

    subset_size = int(args.subset_size)
    if subset_size <= 0 or subset_size > len(all_songs):
        raise SystemExit(f"--subset-size must be in [1, {len(all_songs)}].")

    n = int(args.examples)
    if n <= 0:
        raise SystemExit("--examples must be positive.")

    song_names_sorted = sorted(all_songs)
    song_to_id = {name: i + 1 for i, name in enumerate(song_names_sorted)}  # 0 reserved for PAD

    songs_tensor = torch.zeros((n, subset_size), dtype=torch.int32)
    labels_tensor = torch.zeros((n, v_count), dtype=torch.float32)
    covered_tensor = torch.zeros((n,), dtype=torch.int32)

    # Inproc mode: precompute the witness pool once for all songs, then reuse it for all examples.
    # This avoids per-example Taichi runtime resets from `gpu_witness_pool` and `gpu_inventory_repair`.
    gear_ids_all = totals_all = offsets_all = None
    dense_vid_universe_all = None
    v_count_padded = None
    if str(args.mode) == "inproc":
        if not isinstance(candidates_by_song_all, dict) or not candidates_by_song_all:
            raise SystemExit("Inproc mode: failed to load candidates_by_song from DB.")

        # Build a stable global gear/minis vocab and candidate selection (matches inventory meta tie-breaking).
        gear_set: set[str] = set()
        mini_set: set[str] = set()
        for cands in candidates_by_song_all.values():
            for cand in cands:
                gear_set.update(getattr(cand, "gear_names", ()) or ())
                for group in getattr(cand, "mini_groups", ()) or ():
                    mini_set.update(group or ())
        gear_names_all = sorted(str(x) for x in gear_set if str(x or "").strip())
        mini_names_all = sorted(str(x) for x in mini_set if str(x or "").strip())
        gear_id_map = {name: idx + 1 for idx, name in enumerate(gear_names_all)}
        mini_id_map = {name: idx for idx, name in enumerate(mini_names_all)}

        song_specs = _build_song_specs(candidates_by_song_all, gear_id_map, mini_id_map)
        selected_specs = _select_one_peak_candidate_per_song(song_specs)

        # Prepare per-song arrays for witness pool generation and later packing.
        gear_ids_all, totals_all, elements_all, gear_freq_all = _build_gpu_dynamic_inputs(
            selected_specs, gear_names=gear_names_all
        )

        offsets_all, _wp_stats = build_witness_offsets_gpu(
            gear_ids_all,
            totals_all,
            elements_all,
            gear_freq_all,
            k_total=int(args.k),
            seed=int(args.seed),
            anchor_patterns=128,
            seed_streams=1,
            pattern_profile=1,
            profile=False,
        )

        # Build a stable dense variant universe across all songs/patterns so V is constant across examples.
        _pv, _vf, dense_vid_universe_all, v_count_padded = _pack_part_vids_dense(
            gear_ids_all,
            offsets_all,
            dense_vid_universe=None,
            v_pad_bin=int(args.v_pad_bin),
            variant_freq_mode="song_support",
            wildcard_freq_bonus=40,
        )
        # Free the full packed tensor; we only need the universe for per-example packing.
        del _pv, _vf

    base_rng = random.Random(int(args.seed))
    for i in range(n):
        rng = random.Random(base_rng.randint(0, 2**31 - 1))
        subset = rng.sample(song_names_sorted, subset_size)
        subset_ids = [song_to_id[s] for s in subset]
        songs_tensor[i, :] = torch.tensor(subset_ids, dtype=torch.int32)

        if str(args.mode) == "inproc":
            if gear_ids_all is None or totals_all is None or offsets_all is None or dense_vid_universe_all is None:
                raise RuntimeError("Inproc precompute state not initialized.")

            idx_np = np.asarray([song_to_id[s] - 1 for s in subset], dtype=np.int32)
            gear_ids_np = gear_ids_all[idx_np, :]
            offsets_np = offsets_all[idx_np, :, :]

            part_vids, variant_freq, _u, v_count = _pack_part_vids_dense(
                gear_ids_np,
                offsets_np,
                dense_vid_universe=dense_vid_universe_all,
                v_pad_bin=int(args.v_pad_bin),
                variant_freq_mode="song_support",
                wildcard_freq_bonus=40,
            )
            assert int(v_count_padded or 0) == int(v_count)

            sol = solve_coverage_gpu_full(
                part_vids,
                variant_freq,
                inventory_cap=int(args.inventory_cap),
                seed=int(args.seed) + i,
                repack_passes=3,
                repack_rarity_weighted=False,
                counter_stripes=1,
                k_scan_select=0,
                k_scan_repack=0,
                alns_enabled=False,
                alns_islands=1,
                pt_enabled=False,
                lns_time_sec=0.0,
                lns_attempts=200,
                lns_destroy=6,
                lns_freq_weighted=False,
                lns_random_destroy_prob=0.0,
                lns_restore_after=12,
                lns_restore_drop=4,
                profile=False,
            )
        else:
            # Subprocess mode is slower but more isolated (kept for debugging).
            allow_dir = out_path.parent / "tmp_allowlists"
            out_dir = out_path.parent / "tmp_solver_outputs"
            allow_dir.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=True)

            allow_path = allow_dir / f"allow_{i:05d}.json"
            allow_path.write_text(json.dumps(subset, indent=0), encoding="utf-8")
            sol_path = out_dir / f"sol_{i:05d}.json"

            cmd = [
                sys.executable,
                str(REPO_ROOT / "inventory_meta_coverage_main.py"),
                "--db-path",
                str(db_path),
                "--solver",
                "gpu_full",
                "--inventory-cap",
                str(int(args.inventory_cap)),
                "--partitions-per-song",
                str(int(args.k)),
                "--adaptive-rounds",
                "0",
                "--adaptive-keep-per-song",
                "0",
                "--seed",
                str(int(args.seed) + i),
                "--restarts",
                "1",
                "--lns-time-sec",
                "0",
                "--lns-attempts",
                "200",
                "--song-allowlist-file",
                str(allow_path),
                "--output",
                str(sol_path),
            ]
            subprocess.run(cmd, check=True)
            sol = json.loads(sol_path.read_text(encoding="utf-8"))

        if str(args.mode) == "inproc":
            covered_tensor[i] = int(getattr(sol, "covered_count", 0))

            v_raw = int(dense_vid_universe_all.size)
            if label_mode == "song_support":
                chosen = np.asarray(getattr(sol, "chosen_part", None))
                covered = np.asarray(getattr(sol, "covered", None))
                if chosen.ndim != 1 or covered.ndim != 1:
                    raise RuntimeError("Unexpected gpu_full_solver output (chosen/covered missing).")
                denom = int(covered_tensor[i])
                if denom <= 0:
                    denom = 1
                support = np.zeros((v_raw,), dtype=np.int32)
                covered_idx = np.nonzero(covered > 0)[0]
                for s_idx in covered_idx:
                    p_idx = int(chosen[int(s_idx)])
                    if p_idx < 0:
                        continue
                    vids = part_vids[int(s_idx), int(p_idx)]
                    for d_idx in np.unique(vids):
                        if 0 <= int(d_idx) < v_raw:
                            support[int(d_idx)] += 1
                used_dense = np.nonzero(support > 0)[0].tolist()
                for d_idx in used_dense:
                    raw = int(dense_vid_universe_all[int(d_idx)])
                    gid = int((np.uint32(raw) >> np.uint32(16)) & np.uint32(0xFFFF))
                    off = int(np.uint32(raw) & np.uint32(0xFFFF))
                    if gid <= 0 or gid > len(gear_names_all):
                        continue
                    name = str(gear_names_all[gid - 1])
                    u_idx = universe_key_to_idx.get((normalize_for_lookup(name), off))
                    if u_idx is not None:
                        frac = float(int(support[int(d_idx)])) / float(denom)
                        if frac > float(labels_tensor[i, int(u_idx)]):
                            labels_tensor[i, int(u_idx)] = float(frac)
            else:
                counts = np.asarray(getattr(sol, "counts", None))
                if counts.ndim != 2:
                    raise RuntimeError("Unexpected gpu_full_solver output (counts missing).")
                counts_total = counts.sum(axis=1).astype(np.int64, copy=False)
                used_dense = np.nonzero(counts_total > 0)[0].tolist()
                denom = int(covered_tensor[i]) if label_mode == "usage_frac" else 1
                if denom <= 0:
                    denom = 1
                for d_idx in used_dense:
                    if int(d_idx) < 0 or int(d_idx) >= v_raw:
                        continue
                    raw = int(dense_vid_universe_all[int(d_idx)])
                    gid = int((np.uint32(raw) >> np.uint32(16)) & np.uint32(0xFFFF))
                    off = int(np.uint32(raw) & np.uint32(0xFFFF))
                    if gid <= 0 or gid > len(gear_names_all):
                        continue
                    name = str(gear_names_all[gid - 1])
                    u_idx = universe_key_to_idx.get((normalize_for_lookup(name), off))
                    if u_idx is not None:
                        if label_mode == "usage_frac":
                            frac = float(int(counts_total[int(d_idx)])) / float(denom)
                            if frac > float(labels_tensor[i, int(u_idx)]):
                                labels_tensor[i, int(u_idx)] = float(frac)
                        else:
                            labels_tensor[i, int(u_idx)] = 1.0
        else:
            stats = sol.get("stats") or {}
            covered_tensor[i] = int(stats.get("songs_covered") or 0)

            inv = (sol.get("inventory") or {}).get("gear_variants") or []
            for v in inv:
                if not isinstance(v, dict):
                    continue
                name = str(v.get("gear_name") or "").strip()
                try:
                    off = int(v.get("offset"))
                except Exception:
                    continue
                idx = universe_key_to_idx.get((normalize_for_lookup(name), off))
                if idx is not None:
                    labels_tensor[i, int(idx)] = 1.0

        if (i + 1) % 10 == 0:
            print(f"[{i + 1}/{n}] covered={int(covered_tensor[i])}")

    if str(args.label_weighting) == "covered_linear":
        denom = max(1, int(subset_size))
        weights = covered_tensor.float().clamp_min(0) / float(denom)
        labels_tensor = labels_tensor * weights.unsqueeze(1)

    payload = {
        "meta": {
            "db_path": str(db_path),
            "universe_path": str(universe_path),
            "examples": int(n),
            "subset_size": int(subset_size),
            "inventory_cap": int(args.inventory_cap),
            "k": int(args.k),
            "seed": int(args.seed),
            "mode": str(args.mode),
            "v_pad_bin": int(args.v_pad_bin),
            "songs_total": int(len(song_names_sorted)),
            "label_mode": str(label_mode),
            "label_weighting": str(args.label_weighting),
        },
        "song_names": song_names_sorted,
        "song_peaks": song_peaks,
        "universe_variants": universe_variants,
        "songs": songs_tensor,
        "labels": labels_tensor,
        "covered": covered_tensor,
    }
    torch.save(payload, out_path)
    print(f"Wrote dataset: {out_path}")


if __name__ == "__main__":
    main()
