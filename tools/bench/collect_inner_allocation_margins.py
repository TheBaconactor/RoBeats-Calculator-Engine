"""
Collect exact-inner allocation margin statistics for BASE-5/FG-7 readiness.

This script instruments the exact solver to record the margin between the best
and second-best allocation for random stat vectors. It also computes conservative
cell Δ bounds to check how often M > 2Δ holds in practice.

Usage:
    python tools/bench/collect_inner_allocation_margins.py --samples 500 --output artifacts/margin_stats.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.config import load_config, load_paths_cache
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.solver.scoring.scoring_core import (
    fast_calculate_score,
    lookup_reference_jit,
    optimize_core_exact_bounded_jit,
    semi_exact_upper_bound_jit,
)


@dataclass
class MarginSample:
    pp: int
    cm: int
    fm: int
    p_val: int
    s_val: int
    budget: int
    best_score: int
    second_best_score: int
    margin: int
    delta_cell: float
    reuse_safe: bool


@dataclass
class SongMarginResult:
    song_name: str
    difficulty: str
    total_samples: int
    reuse_safe_count: int
    reuse_safe_fraction: float
    margin_min: int
    margin_p25: float
    margin_median: float
    margin_p75: float
    margin_max: int
    delta_min: float
    delta_p25: float
    delta_median: float
    delta_p75: float
    delta_max: float


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect inner allocation margin statistics.")
    parser.add_argument("--samples", type=int, default=500, help="Random stat samples per song.")
    parser.add_argument("--seed", type=int, default=20260426, help="RNG seed.")
    parser.add_argument("--output", type=str, default="artifacts/margin_stats.json", help="Output JSON path.")
    parser.add_argument("--songs", nargs="*", default=[], help="Optional song names to filter.")
    return parser.parse_args()


def _build_ref_arrays(paths: dict[str, Any]) -> dict[str, np.ndarray]:
    stats_path = str((paths.get("Stats", "") or "").strip())
    stats_table = read_table(stats_path)
    if not stats_table:
        raise RuntimeError(f"Stats table missing: {stats_path}")

    names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays: dict[str, np.ndarray] = {}
    for col_idx, name in enumerate(names):
        values: list[float] = []
        for stat_idx in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(stat_idx)
            try:
                value = float(stats_table[lookup_index][col_idx])
            except Exception:
                value = 0.0
            values.append(value)
        ref_arrays[name] = np.asarray(values, dtype=np.float32)
    return ref_arrays


def _compute_margin_and_delta(
    budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
    refs: dict[str, np.ndarray],
) -> MarginSample:
    """Brute-force compute best, second-best scores and conservative cell delta."""
    GEM_SCALE_NORMAL = 2
    GEM_SCALE_FEVER = 3
    GEM_STAT_TO_ELEMENT_SCALE = 2
    ELEMENTAL_GEM_SCALE = 3
    MAX_STAT_INDEX = int(TOTAL_ROWS)

    ref_pp = refs["Perfect Points"]
    ref_cm = refs["Combo Multiplier"]
    ref_fm = refs["Fever Multiplier"]

    scores: list[int] = []

    max_pp_gems = min(budget, (MAX_STAT_INDEX - cur_pp) // GEM_SCALE_NORMAL) if cur_pp < MAX_STAT_INDEX and (is_p_pp or is_s_pp) else 0
    max_cm_gems = min(budget, (MAX_STAT_INDEX - cur_cm) // GEM_SCALE_NORMAL) if cur_cm < MAX_STAT_INDEX else 0
    if not (is_p_cm or is_s_cm) and cur_cm > 50:
        max_cm_gems = 0
    elif not (is_p_cm or is_s_cm):
        max_cm_gems = min(max_cm_gems, (50 - cur_cm) // GEM_SCALE_NORMAL + 1)
    max_fm_gems = min(budget, (MAX_STAT_INDEX - cur_fm) // GEM_SCALE_FEVER) if cur_fm < MAX_STAT_INDEX else 0

    for g_cm in range(max_cm_gems + 1):
        for g_fm in range(min(max_fm_gems, budget - g_cm) + 1):
            leftover = budget - g_cm - g_fm
            max_pp_here = min(max_pp_gems, leftover)
            for g_pp in range(max_pp_here + 1):
                g_ov = leftover - g_pp

                pp_stat = cur_pp + g_pp * GEM_SCALE_NORMAL
                cm_stat = cur_cm + g_cm * GEM_SCALE_NORMAL
                fm_stat = cur_fm + g_fm * GEM_SCALE_FEVER

                p_val = (
                    cur_p_val
                    + g_pp * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
                    + g_cm * GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
                    + g_fm * GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
                    + g_ov * ELEMENTAL_GEM_SCALE * is_p_ov
                )
                s_val = (
                    cur_s_val
                    + g_pp * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
                    + g_cm * GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
                    + g_fm * GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
                    + g_ov * ELEMENTAL_GEM_SCALE * is_s_ov
                )

                base_value = float((p_val * 2) + s_val + ref_pp[min(pp_stat, MAX_STAT_INDEX)])
                combo_mul = float(ref_cm[min(cm_stat, MAX_STAT_INDEX)])
                fever_mul = float(ref_fm[min(fm_stat, MAX_STAT_INDEX)])

                score = fast_calculate_score(
                    base_value, combo_mul, fever_mul,
                    fever_mask_head, count_body_fever, count_body_normal,
                )
                scores.append(int(score))

    if len(scores) < 2:
        best = scores[0] if scores else 0
        margin = 0
    else:
        scores_sorted = sorted(set(scores), reverse=True)
        best = scores_sorted[0]
        second = scores_sorted[1] if len(scores_sorted) > 1 else best
        margin = best - second

    # Conservative cell delta: assume cell width of 4 stats for PP/CM, 6 for FM, 5 for P_val
    n_total = count_body_fever + count_body_normal + len(fever_mask_head)
    combo_mul_max = float(np.max(ref_cm))
    fever_mul_max = float(np.max(ref_fm))
    base_max = float((cur_p_val + 50) * 2 + (cur_s_val + 50) + np.max(ref_pp))

    delta_pp = 4 * n_total * combo_mul_max * fever_mul_max * 2
    delta_cm = 4 * n_total * base_max * 0.5 * fever_mul_max
    delta_fm = 6 * count_body_fever * base_max * combo_mul_max * 0.5
    delta_cell = delta_pp + delta_cm + delta_fm

    return MarginSample(
        pp=cur_pp, cm=cur_cm, fm=cur_fm, p_val=cur_p_val, s_val=cur_s_val,
        budget=budget, best_score=best, second_best_score=best - margin,
        margin=margin, delta_cell=delta_cell, reuse_safe=margin > 2 * delta_cell,
    )


def _sample_margins_for_song(
    song_name: str,
    difficulty: str,
    n_samples: int,
    rng: np.random.Generator,
    refs: dict[str, np.ndarray],
) -> SongMarginResult:
    samples: list[MarginSample] = []

    for _ in range(n_samples):
        budget = int(rng.integers(5, 21))
        cur_pp = int(rng.integers(0, 80))
        cur_cm = int(rng.integers(0, 60))
        cur_fm = int(rng.integers(0, 60))
        cur_p_val = int(rng.integers(0, 80))
        cur_s_val = int(rng.integers(0, 80))

        head_len = int(rng.integers(10, 101))
        n_hf = int(rng.integers(0, head_len // 2 + 1))
        fever_mask_head = np.zeros(head_len, dtype=np.bool_)
        if n_hf > 0:
            indices = rng.choice(head_len, size=n_hf, replace=False)
            fever_mask_head[indices] = True

        count_body_fever = int(rng.integers(50, 300))
        count_body_normal = int(rng.integers(50, 300))

        sample = _compute_margin_and_delta(
            budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
            1, 0, 1, 0, 1, 0, 1, 0,
            fever_mask_head, count_body_fever, count_body_normal, refs,
        )
        samples.append(sample)

    margins = [s.margin for s in samples]
    deltas = [s.delta_cell for s in samples]
    safe_count = sum(1 for s in samples if s.reuse_safe)

    return SongMarginResult(
        song_name=song_name,
        difficulty=difficulty,
        total_samples=n_samples,
        reuse_safe_count=safe_count,
        reuse_safe_fraction=safe_count / n_samples if n_samples > 0 else 0.0,
        margin_min=int(np.min(margins)),
        margin_p25=float(np.percentile(margins, 25)),
        margin_median=float(np.median(margins)),
        margin_p75=float(np.percentile(margins, 75)),
        margin_max=int(np.max(margins)),
        delta_min=float(np.min(deltas)),
        delta_p25=float(np.percentile(deltas, 25)),
        delta_median=float(np.median(deltas)),
        delta_p75=float(np.percentile(deltas, 75)),
        delta_max=float(np.max(deltas)),
    )


def main() -> int:
    args = _parse_args()
    rng = np.random.default_rng(args.seed)

    config = load_config()
    paths = load_paths_cache()
    refs = _build_ref_arrays(paths)

    # Run on synthetic "songs" with different note counts
    songs = [
        ("Easy_Synthetic", "Easy", 100, 50),
        ("Normal_Synthetic", "Normal", 300, 150),
        ("Hard_Synthetic", "Hard", 500, 250),
    ]

    results: list[dict[str, Any]] = []
    for name, diff, body_fever, body_normal in songs:
        if args.songs and name not in args.songs:
            continue
        print(f"Sampling {args.samples} margins for {name} ({diff})...")
        result = _sample_margins_for_song(name, diff, args.samples, rng, refs)
        results.append(asdict(result))
        print(f"  Reuse safe: {result.reuse_safe_count}/{result.total_samples} ({result.reuse_safe_fraction:.1%})")
        print(f"  Margin median: {result.margin_median:,.0f}, Delta median: {result.delta_median:,.0f}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote results to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
