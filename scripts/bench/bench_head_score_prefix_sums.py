"""
Benchmark: Head Score Prefix Sums vs Loop-Based Calculation

Tests whether precomputing prefix sums for fever masks can improve head score
calculation performance. The hypothesis is that O(1) lookup with prefix sums
might beat O(head_len) loops when many score calculations share the same mask.

Test Setup:
- Load 30 real songs from Data/Hard
- For each song, compute fever masks for all 161x161 FT/FF combinations
- Benchmark two approaches:
  1. Loop-based: iterate through each note (current implementation)
  2. Prefix-sum: precompute prefix tables, then O(1) lookup

The prefix sum approach precomputes for each (FT, FF) mask:
- fever_count[k]: number of fever notes in [0, k)
- fever_index_sum[k]: sum of (i+1) for fever notes i in [0, k)

Then head_score can be computed as:
  fever_contribution = fever_mul * (base * fever_count + factor * fever_index_sum)
  normal_contribution = base * (head_len - fever_count) + factor * (total_index_sum - fever_index_sum)
  total_index_sum = head_len * (head_len + 1) / 2
"""

import os
import sys
import time
import random
import numpy as np
from pathlib import Path
from numba import jit

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.constants import TOTAL_ROWS, FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET
from gear_optimizer.data.song_io import read_song_file
from gear_optimizer.solver.fever_timeline import SongTimelineGrid, calculate_fever_timeline_indices
from gear_optimizer.solver.scoring.scoring_core import lookup_reference_py


def build_calc_song(song_data: dict) -> dict:
    """Build a calc_song dict from raw song file data."""
    details = song_data.get("song_details", {})
    timestamps = song_data.get("timestamps", [])

    # Convert to numpy array
    if not isinstance(timestamps, np.ndarray):
        timestamps = np.array(timestamps, dtype=np.float64)

    return {
        "song_data": {
            "timestamps": timestamps,
        },
        "metadata": {
            "Song Name": details.get("Song Name", "Unknown"),
            "Total Notes": len(timestamps),
            "Long Notes": int(details.get("Long Notes", 0) or 0),
            "Last Note Time": float(details.get("Last Note Time", 0) or timestamps[-1] if len(timestamps) else 0),
            "Primary Color": details.get("Primary Color", "Rush"),
            "Secondary Color": details.get("Secondary Color", ""),
        },
    }


def load_reference_arrays(gear_dir: Path) -> dict:
    """Load stats reference arrays from Stats.txt."""
    stats_file = gear_dir / "Stats.txt"
    if not stats_file.exists():
        return {}

    try:
        with open(stats_file, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()

        # Parse stats table
        stats_table = []
        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 6:
                try:
                    row = [float(x) for x in parts[1:6]]  # Skip index column
                    stats_table.append(row)
                except ValueError:
                    continue

        # Build ref arrays (indexed by stat value 0-160)
        stat_names = [
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Fill Rate",
            "Fever Time",
        ]
        ref_arrays = {}
        for i, name in enumerate(stat_names):
            arr = np.zeros(TOTAL_ROWS + 1, dtype=np.float64)
            for v in range(TOTAL_ROWS + 1):
                lookup_idx = TOTAL_ROWS - v
                if lookup_idx < len(stats_table):
                    arr[v] = stats_table[lookup_idx][i]
            ref_arrays[name] = arr

        return ref_arrays
    except Exception as e:
        print(f"ERROR loading stats: {e}")
        return {}


# =============================================================================
# CURRENT IMPLEMENTATION: Loop-based head score
# =============================================================================


@jit(nopython=True, cache=True)
def head_score_loop(base_value, factor, fever_mul, fever_mask_head):
    """
    Current loop-based head score calculation.
    O(head_len) per call.
    """
    head_score = 0
    head_len = len(fever_mask_head)
    for i in range(head_len):
        ramp_val = base_value + (i + 1) * factor
        if fever_mask_head[i]:
            head_score += int(ramp_val * fever_mul)
        else:
            head_score += int(ramp_val)
    return head_score


# =============================================================================
# PREFIX SUM IMPLEMENTATION: O(1) head score
# =============================================================================


def build_prefix_tables(fever_mask_head):
    """
    Build prefix sum tables for a fever mask.

    Returns:
        fever_count: array[k] = number of fever notes in [0, k)
        fever_index_sum: array[k] = sum of (i+1) for fever notes i in [0, k)

    Table size: 101 values each (for k=0..100)
    """
    head_len = len(fever_mask_head)
    max_len = min(head_len, 100)

    fever_count = np.zeros(max_len + 1, dtype=np.int32)
    fever_index_sum = np.zeros(max_len + 1, dtype=np.int64)

    for k in range(1, max_len + 1):
        fever_count[k] = fever_count[k - 1]
        fever_index_sum[k] = fever_index_sum[k - 1]
        if fever_mask_head[k - 1]:  # Note index k-1 is fever
            fever_count[k] += 1
            fever_index_sum[k] += k  # (i+1) where i = k-1, so k

    return fever_count, fever_index_sum


@jit(nopython=True, cache=True)
def head_score_prefix_sum(base_value, factor, fever_mul, head_len, fever_count, fever_index_sum, total_index_sum):
    """
    O(1) head score calculation using prefix sums.

    IMPORTANT: This is an APPROXIMATION! The loop-based version truncates each term
    individually with int(), while this aggregates before truncation. This causes
    small numerical differences (typically < 1% error).

    Args:
        base_value: base score value
        factor: combo ramp factor
        fever_mul: fever multiplier
        head_len: number of notes in head
        fever_count: precomputed count of fever notes in [0, head_len)
        fever_index_sum: precomputed sum of (i+1) for fever notes in [0, head_len)
        total_index_sum: precomputed 1+2+...+head_len = head_len*(head_len+1)/2

    Returns:
        head score (int)

    Math derivation:
    head_score = sum over i in [0, head_len): (base + (i+1)*factor) * mul[i]

    Where mul[i] = fever_mul if fever[i] else 1.0

    Split into fever and normal contributions:
    fever_part = sum over fever notes: (base + (i+1)*factor) * fever_mul
               = fever_mul * (base * fever_count + factor * fever_index_sum)

    normal_part = sum over normal notes: (base + (i+1)*factor)
                = base * normal_count + factor * normal_index_sum

    Where:
    - normal_count = head_len - fever_count
    - normal_index_sum = total_index_sum - fever_index_sum
    """
    normal_count = head_len - fever_count
    normal_index_sum = total_index_sum - fever_index_sum

    # Fever contribution
    fever_base_part = base_value * fever_count
    fever_ramp_part = factor * fever_index_sum
    fever_contribution = fever_mul * (fever_base_part + fever_ramp_part)

    # Normal contribution
    normal_base_part = base_value * normal_count
    normal_ramp_part = factor * normal_index_sum
    normal_contribution = normal_base_part + normal_ramp_part

    return int(fever_contribution) + int(normal_contribution)


# =============================================================================
# BENCHMARK HARNESS
# =============================================================================


def load_songs(data_dir: Path, difficulty: str = "Hard", max_songs: int = 30):
    """Load up to max_songs from the specified difficulty folder."""
    diff_dir = data_dir / difficulty
    if not diff_dir.exists():
        print(f"ERROR: {diff_dir} not found")
        return []

    song_files = list(diff_dir.glob("*.txt"))
    if not song_files:
        print(f"ERROR: No song files found in {diff_dir}")
        return []

    # Shuffle and take max_songs
    random.seed(42)  # Reproducible selection
    random.shuffle(song_files)
    song_files = song_files[:max_songs]

    songs = []
    for song_file in song_files:
        try:
            song_data = read_song_file(str(song_file))
            if song_data and len(song_data.get("timestamps", [])) >= 100:
                calc_song = build_calc_song(song_data)
                songs.append((song_file.stem, calc_song))
        except Exception as e:
            print(f"  Skip {song_file.stem}: {e}")

    return songs


def benchmark_single_song(calc_song, ref_arrays, num_ftff_samples=100, num_score_calls=100):
    """
    Benchmark loop vs prefix-sum for a single song.

    Returns:
        dict with timing results
    """
    grid = SongTimelineGrid(calc_song, ref_arrays)

    # Sample FT/FF combinations
    ftff_pairs = []
    for ft in range(0, 161, 16):  # Sample every 16th
        for ff in range(0, 161, 16):
            ftff_pairs.append((ft, ff))
    ftff_pairs = ftff_pairs[:num_ftff_samples]

    # Precompute all timelines and prefix tables
    timelines = []
    prefix_tables = []

    for ft_idx, ff_idx in ftff_pairs:
        tl = grid.get_timeline(ft_idx, ff_idx)
        fever_mask_head = tl[0]  # First 100 notes fever mask
        timelines.append(fever_mask_head)

        fever_count, fever_index_sum = build_prefix_tables(fever_mask_head)
        prefix_tables.append((fever_count, fever_index_sum))

    # Test parameters (vary base and factor like real gem allocation does)
    base_values = np.linspace(50.0, 200.0, 10).astype(np.float32)
    factors = np.linspace(0.1, 0.5, 10).astype(np.float32)
    fever_mul = np.float32(1.5)

    # Warmup JIT
    for _ in range(10):
        head_score_loop(100.0, 0.3, 1.5, timelines[0])
        head_score_prefix_sum(
            100.0,
            0.3,
            1.5,
            len(timelines[0]),
            prefix_tables[0][0][len(timelines[0])],
            prefix_tables[0][1][len(timelines[0])],
            len(timelines[0]) * (len(timelines[0]) + 1) // 2,
        )

    # Benchmark loop-based
    loop_results = []
    t0 = time.perf_counter()
    for _ in range(num_score_calls):
        for i, (ft_idx, ff_idx) in enumerate(ftff_pairs):
            fever_mask_head = timelines[i]
            for base in base_values:
                for factor in factors:
                    score = head_score_loop(base, factor, fever_mul, fever_mask_head)
                    loop_results.append(score)
    loop_time = time.perf_counter() - t0

    # Benchmark prefix-sum based
    prefix_results = []
    t0 = time.perf_counter()
    for _ in range(num_score_calls):
        for i, (ft_idx, ff_idx) in enumerate(ftff_pairs):
            fever_count_arr, fever_index_sum_arr = prefix_tables[i]
            head_len = len(timelines[i])
            fever_count = fever_count_arr[head_len]
            fever_index_sum = fever_index_sum_arr[head_len]
            total_index_sum = head_len * (head_len + 1) // 2
            for base in base_values:
                for factor in factors:
                    score = head_score_prefix_sum(
                        base, factor, fever_mul, head_len, fever_count, fever_index_sum, total_index_sum
                    )
                    prefix_results.append(score)
    prefix_time = time.perf_counter() - t0

    # Verify correctness (check a sample) and measure error
    mismatches = 0
    max_abs_error = 0
    total_abs_error = 0
    for i in range(min(1000, len(loop_results))):
        diff = abs(loop_results[i] - prefix_results[i])
        if diff > 0:
            mismatches += 1
            max_abs_error = max(max_abs_error, diff)
            total_abs_error += diff
    avg_abs_error = total_abs_error / max(1, mismatches)

    return {
        "loop_time": loop_time,
        "prefix_time": prefix_time,
        "speedup": loop_time / prefix_time if prefix_time > 0 else 0,
        "num_calls": len(loop_results),
        "mismatches": mismatches,
        "max_abs_error": max_abs_error,
        "avg_abs_error": avg_abs_error,
    }


def benchmark_prefix_table_build(calc_song, ref_arrays):
    """
    Benchmark the cost of building prefix tables for all 161x161 FT/FF combinations.
    This is the "upfront cost" that must be amortized over score calculations.
    """
    grid = SongTimelineGrid(calc_song, ref_arrays)

    # Time building prefix tables for all combinations
    t0 = time.perf_counter()
    all_tables = {}
    for ft in range(161):
        for ff in range(161):
            tl = grid.get_timeline(ft, ff)
            fever_mask_head = tl[0]
            fever_count, fever_index_sum = build_prefix_tables(fever_mask_head)
            all_tables[(ft, ff)] = (fever_count, fever_index_sum)
    build_time = time.perf_counter() - t0

    # Memory footprint
    memory_bytes = 161 * 161 * 2 * 101 * 4  # 161x161 combinations, 2 arrays, 101 values, 4 bytes each
    memory_mb = memory_bytes / (1024 * 1024)

    return {
        "build_time": build_time,
        "memory_mb": memory_mb,
        "num_tables": len(all_tables),
    }


def main():
    print("=" * 80)
    print("HEAD SCORE PREFIX SUMS BENCHMARK")
    print("=" * 80)

    # Load reference arrays
    data_dir = PROJECT_ROOT / "Data"
    ref_arrays = load_reference_arrays(data_dir / "Gear")
    if not ref_arrays:
        print("ERROR: Failed to load reference arrays")
        return

    # Load songs
    print(f"\nLoading songs from {data_dir / 'Hard'}...")
    songs = load_songs(data_dir, "Hard", max_songs=30)
    print(f"Loaded {len(songs)} songs")

    if not songs:
        print("ERROR: No songs loaded")
        return

    # =========================================================================
    # Part 1: Benchmark prefix table build cost (one song)
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 1: PREFIX TABLE BUILD COST (one song, all 161x161 FT/FF)")
    print("=" * 80)

    sample_song_name, sample_calc_song = songs[0]
    print(f"Sample song: {sample_song_name}")

    build_stats = benchmark_prefix_table_build(sample_calc_song, ref_arrays)
    print(f"  Build time: {build_stats['build_time'] * 1000:.2f} ms")
    print(f"  Memory: {build_stats['memory_mb']:.2f} MB per song")
    print(f"  Tables: {build_stats['num_tables']} (161x161)")

    # =========================================================================
    # Part 2: Benchmark score calculation across 30 songs
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 2: SCORE CALCULATION (30 songs)")
    print("=" * 80)

    total_loop_time = 0
    total_prefix_time = 0
    total_calls = 0
    total_mismatches = 0

    for i, (song_name, calc_song) in enumerate(songs):
        print(f"\n[{i + 1}/{len(songs)}] {song_name}...", end=" ", flush=True)

        try:
            stats = benchmark_single_song(calc_song, ref_arrays, num_ftff_samples=100, num_score_calls=50)

            total_loop_time += stats["loop_time"]
            total_prefix_time += stats["prefix_time"]
            total_calls += stats["num_calls"]
            total_mismatches += stats["mismatches"]

            print(
                f"Loop: {stats['loop_time'] * 1000:.1f}ms, "
                f"Prefix: {stats['prefix_time'] * 1000:.1f}ms, "
                f"Speedup: {stats['speedup']:.2f}x, "
                f"MaxErr: {stats['max_abs_error']}, AvgErr: {stats['avg_abs_error']:.1f}"
            )
        except Exception as e:
            print(f"ERROR: {e}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nTotal score calls: {total_calls:,}")
    print(f"\nLoop-based approach:")
    print(f"  Total time: {total_loop_time * 1000:.2f} ms")
    print(f"  Per-call: {(total_loop_time / total_calls) * 1e6:.3f} μs")

    print(f"\nPrefix-sum approach:")
    print(f"  Total time: {total_prefix_time * 1000:.2f} ms")
    print(f"  Per-call: {(total_prefix_time / total_calls) * 1e6:.3f} μs")

    speedup = total_loop_time / total_prefix_time if total_prefix_time > 0 else 0
    print(f"\nOverall speedup: {speedup:.2f}x")
    print(f"\n*** CRITICAL: Prefix-sum is NOT bit-exact! ***")
    print(f"The loop truncates each term with int() individually, while prefix-sum")
    print(f"aggregates before truncation. This causes numerical differences.")
    print(f"Total mismatches out of 1000 sampled: ~{total_mismatches // 30}/1000 per song")

    # =========================================================================
    # Break-even analysis
    # =========================================================================
    print("\n" + "=" * 80)
    print("BREAK-EVEN ANALYSIS")
    print("=" * 80)

    build_cost_ms = build_stats["build_time"] * 1000
    loop_per_call_us = (total_loop_time / total_calls) * 1e6
    prefix_per_call_us = (total_prefix_time / total_calls) * 1e6
    savings_per_call_us = loop_per_call_us - prefix_per_call_us

    if savings_per_call_us > 0:
        breakeven_calls = (build_cost_ms * 1000) / savings_per_call_us
        print(f"Build cost: {build_cost_ms:.2f} ms")
        print(f"Savings per call: {savings_per_call_us:.3f} μs")
        print(f"Break-even: {breakeven_calls:,.0f} calls")
        print(f"\nTo amortize the 161x161 prefix table build cost, you need")
        print(f"{breakeven_calls:,.0f} head score calculations per song.")
    else:
        print("Prefix-sum approach is SLOWER than loop-based!")
        print(f"Loop: {loop_per_call_us:.3f} μs, Prefix: {prefix_per_call_us:.3f} μs")

    # Memory consideration
    print("\n" + "=" * 80)
    print("MEMORY CONSIDERATION")
    print("=" * 80)
    memory_per_song_mb = build_stats["memory_mb"]
    print(f"Memory per song (all 161x161 tables): {memory_per_song_mb:.2f} MB")
    print(f"For 30 songs in flight: {memory_per_song_mb * 30:.2f} MB")
    print(f"For 100 songs: {memory_per_song_mb * 100:.2f} MB")


if __name__ == "__main__":
    main()
