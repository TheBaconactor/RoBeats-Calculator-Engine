#!/usr/bin/env python3
"""
Benchmark: Inventory Meta Coverage on a synthetic "shift-piece" landscape.

This generates a temporary SQLite DB with many songs that share a core gear set, but
require a few "shift" variants to match different GemCounts totals exactly.

Purpose:
- Provide a reproducible workload to compare solver/heuristic changes.
- Stress reuse/variant-concentration behavior under an inventory cap.

Notes:
- Exact-peak-only: all candidates are inserted at the same peak score per song.
- No human-mode / no score deltas: we always stay on peak rows.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.data.database import get_db_connection  # noqa: E402
from inventory_optimizer import run_inventory_meta_coverage  # noqa: E402


ELEMENTS: Tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")


def _base_details(selected_element: str, *, pp: int, cm: int, fm: int, ft: int, ff: int, ov: int) -> Dict[str, Any]:
    return {
        "FT": int(ft),
        "FF": int(ff),
        "GemCounts": {
            "Perfect Points": int(pp),
            "Combo Multiplier": int(cm),
            "Fever Multiplier": int(fm),
            "Element": int(ov),
        },
        # These keys are read by loadout_equivalence.extract_song_colors()
        "SelectedElement": str(selected_element),
        "PrimaryColor": str(selected_element),
        "SecondaryColor": "Flow",
    }


def _insert_loadout(
    conn,
    *,
    song_name: str,
    score: int,
    gear_names: List[str],
    minis_groups: List[List[str]],
    details: Dict[str, Any],
) -> None:
    # Keep songs table in sync for realism (not required for inventory queries).
    conn.execute(
        """
        INSERT INTO songs (name, best_score, best_fg_score, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            best_score = MAX(best_score, excluded.best_score),
            best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
            last_updated = excluded.last_updated
        """,
        (song_name, int(score), 0, time.time()),
    )
    conn.execute(
        """
        INSERT INTO loadouts (
            song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            song_name,
            f"{song_name}-{score}-{random.getrandbits(32)}",
            int(score),
            0,
            json.dumps(list(gear_names), ensure_ascii=False),
            json.dumps(list(minis_groups), ensure_ascii=False),
            json.dumps(details, ensure_ascii=False),
            None,
            time.time(),
        ),
    )


def _sum6(vecs: Iterable[Tuple[int, int, int, int, int]]) -> Tuple[int, int, int, int, int]:
    pp = cm = fm = ft = ff = 0
    for v in vecs:
        pp += int(v[0])
        cm += int(v[1])
        fm += int(v[2])
        ft += int(v[3])
        ff += int(v[4])
    return pp, cm, fm, ft, ff


def _make_synthetic_workload(
    *,
    db_path: Path,
    songs: int,
    seed: int,
    candidates_per_song: int,
    alt_candidate_rate: float,
) -> None:
    """
    Create a workload where:
    - Most songs share the same 6 gear IDs (core set).
    - Gem totals come from a small "vocabulary" of wildcard 15-gem vectors (OV=0).
    - Some songs also have alternate peak candidates with small gear swaps to enable multi-candidate selection.
    """
    rnd = random.Random(int(seed))
    os.makedirs(db_path.parent, exist_ok=True)
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)

    minis = [["MiniA"], ["MiniB"], ["MiniC"]]
    score = 100

    core_gear = ["HatCore", "NeckCore", "FaceCore", "ShirtCore", "BackCore", "PantCore"]
    alt_gear_pool = {
        "HatCore": ["HatShiftA", "HatShiftB"],
        "NeckCore": ["NeckShiftA", "NeckShiftB"],
        "FaceCore": ["FaceShiftA", "FaceShiftB"],
        "ShirtCore": ["ShirtShiftA", "ShirtShiftB"],
        "BackCore": ["BackShiftA", "BackShiftB"],
        "PantCore": ["PantShiftA", "PantShiftB"],
    }

    # "Vocabulary" of wildcard per-slot 15-gem vectors (PP, CM, FM, FT, FF).
    # These are intentionally a mix of pure and mixed allocations to represent "shift pieces".
    vocab: List[Tuple[int, int, int, int, int]] = [
        (15, 0, 0, 0, 0),
        (0, 15, 0, 0, 0),
        (0, 0, 15, 0, 0),
        (10, 5, 0, 0, 0),
        (5, 10, 0, 0, 0),
        (0, 10, 5, 0, 0),
        (0, 5, 10, 0, 0),
        (7, 3, 5, 0, 0),
        (5, 3, 7, 0, 0),
        (3, 5, 7, 0, 0),
        (6, 0, 6, 3, 0),  # includes FT
        (6, 0, 6, 0, 3),  # includes FF
    ]

    # Define two clusters that share a common 4-vector "core package" but differ in the last 2 vectors.
    # This creates a rugged landscape where a few "shift" vectors unlock many songs.
    core_package = [(15, 0, 0, 0, 0), (0, 15, 0, 0, 0), (0, 0, 15, 0, 0), (10, 5, 0, 0, 0)]
    cluster_a_tail = [(0, 10, 5, 0, 0), (6, 0, 6, 3, 0)]
    cluster_b_tail = [(0, 5, 10, 0, 0), (6, 0, 6, 0, 3)]

    conn = get_db_connection(str(db_path))
    try:
        for i in range(int(songs)):
            song_name = f"S{i:05d}"
            selected_element = rnd.choice(ELEMENTS)

            # Pick cluster and build a 6-slot multiset of vectors.
            if (i % 2) == 0:
                vecs = list(core_package) + list(cluster_a_tail)
            else:
                vecs = list(core_package) + list(cluster_b_tail)

            # Add minor per-song perturbations by swapping one tail vector with a nearby mixed vector.
            # Keeps totals exact and preserves a small set of globally useful "shift" vectors.
            if rnd.random() < 0.35:
                vecs[-1] = rnd.choice(vocab)
                # Ensure total still sums to 6*15 by adjusting the first vector (pure PP) as needed.
                pp, cm, fm, ft, ff = _sum6(vecs)
                target = 90
                delta = target - (pp + cm + fm + ft + ff)
                # Move delta into PP of the first vec (clamp to [0,15] and keep sum=15 via CM trade).
                v0 = list(vecs[0])
                v0[0] = max(0, min(15, v0[0] + delta))
                # Keep sum==15 by compensating in CM.
                v0[1] = 15 - (v0[0] + v0[2] + v0[3] + v0[4])
                if v0[1] < 0:
                    # Fallback: if invalid, undo perturbation for this song.
                    vecs[-1] = cluster_a_tail[-1] if (i % 2) == 0 else cluster_b_tail[-1]
                else:
                    vecs[0] = tuple(int(x) for x in v0)

            pp, cm, fm, ft, ff = _sum6(vecs)
            details = _base_details(selected_element, pp=pp, cm=cm, fm=fm, ft=ft, ff=ff, ov=0)

            # Candidate 0: core gear set (always present).
            _insert_loadout(
                conn,
                song_name=song_name,
                score=score,
                gear_names=list(core_gear),
                minis_groups=minis,
                details=details,
            )

            # Additional peak candidates:
            # - Some are identical gear (different totals are not allowed here since we're "exact peak only")
            # - Others swap 1-2 pieces for alternate gear IDs, enabling multi-candidate selection to prefer core gear IDs.
            for c in range(1, int(candidates_per_song)):
                if rnd.random() > float(alt_candidate_rate):
                    gear_names = list(core_gear)
                else:
                    gear_names = list(core_gear)
                    # Swap 1-2 random slots.
                    swaps = 1 if rnd.random() < 0.75 else 2
                    for _ in range(swaps):
                        idx = rnd.randrange(6)
                        base = core_gear[idx]
                        gear_names[idx] = rnd.choice(alt_gear_pool[base])
                _insert_loadout(
                    conn,
                    song_name=song_name,
                    score=score,
                    gear_names=gear_names,
                    minis_groups=minis,
                    details=details,
                )

        conn.commit()
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(prog="bench_inventory_shift.py")
    ap.add_argument("--songs", type=int, default=2000)
    ap.add_argument("--candidates-per-song", type=int, default=2)
    ap.add_argument("--alt-candidate-rate", type=float, default=0.65)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--inventory-cap", type=int, default=100)
    ap.add_argument("--k", type=int, default=64, help="Witness patterns per song (partitions_per_song).")
    ap.add_argument("--adaptive-rounds", type=int, default=0)
    ap.add_argument("--adaptive-keep-per-song", type=int, default=0)
    ap.add_argument("--solver", type=str, default="gpu_full", choices=["gpu_dynamic", "gpu_eda", "gpu_full"])
    ap.add_argument("--restarts", type=int, default=1)
    ap.add_argument("--lns-time-sec", type=float, default=0.0)
    ap.add_argument("--lns-attempts", type=int, default=200)
    ap.add_argument("--gpu-repack-passes", type=int, default=2)
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--gpu-full-wildcard-palette-size", type=int, default=0)
    ap.add_argument("--gpu-full-wildcard-palette-min-count", type=int, default=2)
    ap.add_argument("--gpu-full-wildcard-palette-scan", type=int, default=8)
    ap.add_argument("--gpu-full-wildcard-palette-tail-slots", type=int, default=3)
    ap.add_argument("--gpu-full-synergy-weight", type=int, default=0)
    ap.add_argument("--gpu-full-synergy-top-offsets", type=int, default=128)
    ap.add_argument("--gpu-full-synergy-min-pair-count", type=int, default=2)
    ap.add_argument("--gpu-full-synergy-scale", type=int, default=256)
    ap.add_argument("--gpu-full-synergy-max-bonus", type=int, default=4095)
    ap.add_argument("--gpu-full-new-gear-penalty", type=int, default=0)
    ap.add_argument("--db-path", type=str, default=str(REPO_ROOT / "artifacts" / "bench_inventory_shift.db"))
    args = ap.parse_args()

    db_path = Path(args.db_path)
    if db_path.exists():
        db_path.unlink()

    print(f"[bench] generating db: {db_path} (songs={args.songs}, cands={args.candidates_per_song})")
    _make_synthetic_workload(
        db_path=db_path,
        songs=int(args.songs),
        seed=int(args.seed),
        candidates_per_song=int(args.candidates_per_song),
        alt_candidate_rate=float(args.alt_candidate_rate),
    )

    # Enable optionality stats in output to inspect variant concentration.
    os.environ.setdefault("INVENTORY_META_OPTIONALITY", "1")

    t0 = time.perf_counter()
    res = run_inventory_meta_coverage(
        solver=str(args.solver),
        inventory_cap=int(args.inventory_cap),
        seed=int(args.seed),
        restarts=int(args.restarts),
        partitions_per_song=int(args.k),
        adaptive_rounds=int(args.adaptive_rounds),
        adaptive_keep_per_song=int(args.adaptive_keep_per_song),
        lns_time_sec=float(args.lns_time_sec),
        lns_attempts=int(args.lns_attempts),
        gpu_repack_passes=int(args.gpu_repack_passes),
        profile=bool(args.profile),
        gpu_full_top_candidates=int(max(1, int(args.candidates_per_song))),
        gpu_full_wildcard_palette_size=int(args.gpu_full_wildcard_palette_size),
        gpu_full_wildcard_palette_min_count=int(args.gpu_full_wildcard_palette_min_count),
        gpu_full_wildcard_palette_scan=int(args.gpu_full_wildcard_palette_scan),
        gpu_full_wildcard_palette_tail_slots=int(args.gpu_full_wildcard_palette_tail_slots),
        gpu_full_synergy_weight=int(args.gpu_full_synergy_weight),
        gpu_full_synergy_top_offsets=int(args.gpu_full_synergy_top_offsets),
        gpu_full_synergy_min_pair_count=int(args.gpu_full_synergy_min_pair_count),
        gpu_full_synergy_scale=int(args.gpu_full_synergy_scale),
        gpu_full_synergy_max_bonus=int(args.gpu_full_synergy_max_bonus),
        gpu_full_new_gear_penalty=int(args.gpu_full_new_gear_penalty),
    )
    dt = time.perf_counter() - t0

    stats = res.get("stats", {}) if isinstance(res, dict) else {}
    opt = (stats.get("optionality") or {}) if isinstance(stats, dict) else {}
    inv_opt = (opt.get("inventory") or {}) if isinstance(opt, dict) else {}

    print()
    print("=" * 70)
    print("BENCH RESULTS")
    print("=" * 70)
    print(f"solver={res.get('mode')} time_sec={dt:.3f}")
    print(f"songs_total={stats.get('songs_total')} songs_covered={stats.get('songs_covered')}")
    print(f"gear_variants_used={stats.get('gear_variants_used')} / cap={stats.get('gear_variants_cap')}")
    if inv_opt:
        print(
            f"unique_gear_ids={inv_opt.get('unique_gear_ids')} avg_variants_per_gear={inv_opt.get('avg_variants_per_gear')}"
        )
        print(
            f"wildcard_share={inv_opt.get('wildcard_share')} top_gears={len(inv_opt.get('top_gears_by_variant_count') or [])}"
        )
    print()


if __name__ == "__main__":
    main()
