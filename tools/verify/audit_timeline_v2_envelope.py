"""Research-only audit for a fast exact timing-envelope V2 certificate.

This script does not change production behavior. It explores a cheap exact
certificate:

    If every fever deadline is separated from every reachable timing band, the
    timing surface is a singleton over all feasible Perfect-window event paths.

Cells that fail this proof are reported as unknown instead of falling back to a
full Bellman / interval DP.

Run examples:
  python tools/verify/audit_timeline_v2_envelope.py --song "Data/Hard/Endless Rain (Hard) by seatrus (feat. marumoko).txt"
  python tools/verify/audit_timeline_v2_envelope.py --self-test
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class TimelineSurface:
    head_len: int
    masks: tuple[int, int, int, int]
    body_fever: int
    body_normal: int
    activations: int
    gap: int


@dataclass(frozen=True)
class ZeroSwingCertificate:
    certified: bool
    surface: TimelineSurface | None
    reason: str
    activations: int
    swing_checks: int
    max_carry_width: int


@dataclass(frozen=True)
class SongAudit:
    song: str
    notes: int
    groups: int
    unique_pairs: int
    grid_cells: int
    certified_pairs: int
    certified_grid_cells: int
    no_fever_pairs: int
    uncertain_pairs: int
    max_carry_width: int
    frontier_hist: Counter[int]
    wall_ms: float


def _load_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.csv_parser import read_table

    paths = load_paths_cache()
    stats_table = read_table(paths.get("Stats", ""))
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    out: dict[str, np.ndarray] = {}
    for i, name in enumerate(stat_names):
        values = []
        for v in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(v)
            try:
                val = stats_table[lookup_index][i] if stats_table else 0.0
            except Exception:
                val = 0.0
            values.append(float(val))
        out[name] = np.asarray(values, dtype=np.float32)
    return out


def _read_song(fp: str) -> dict:
    from gear_optimizer.pipeline.song_processor import read_song_file

    song = read_song_file(fp)
    details = song.get("song_details", {}) or {}
    timestamps = np.asarray(song.get("timestamps", ()), dtype=np.float32)
    note_types = np.asarray(song.get("note_types", ()), dtype=np.int16)

    try:
        long_notes = int(float(details.get("Long Notes", 0) or 0))
    except Exception:
        long_notes = 0

    meta = {
        "Song Name": str(details.get("Song Name") or os.path.basename(fp)),
        "Difficulty": str(details.get("Difficulty") or Path(fp).parent.name),
        "Long Notes": int(long_notes),
        "Last Note Time": float(timestamps[-1]) if timestamps.size else 0.0,
        "Total Notes": int(timestamps.size),
    }
    return {
        "metadata": meta,
        "song_data": {
            "timestamps": timestamps.copy(),
            "chart_timestamps": timestamps.copy(),
            "note_types": note_types.copy(),
        },
    }


def prepare_perfect_envelope_for_song(calc_song: dict) -> dict:
    from gear_optimizer.solver.timing_envelope import prepare_perfect_timing_envelope

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = np.asarray(song_data.get("chart_timestamps", song_data.get("timestamps", ())), dtype=np.float32)
    note_types = np.asarray(song_data.get("note_types", ()), dtype=np.int16)
    return prepare_perfect_timing_envelope(
        timestamps,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )


def _note_group_idx(prepared: dict) -> np.ndarray:
    n = int(prepared.get("n", 0) or 0)
    group_starts = np.asarray(prepared.get("group_starts", ()), dtype=np.int32)
    group_ends = np.asarray(prepared.get("group_ends", ()), dtype=np.int32)
    note_group_idx = np.full(n, -1, dtype=np.int32)
    for g in range(int(group_starts.shape[0])):
        s = int(group_starts[g])
        e = int(group_ends[g])
        if e > s:
            note_group_idx[s:e] = int(g)
    if n > 0 and bool(np.any(note_group_idx < 0)):
        raise ValueError("prepared timing envelope contains uncovered notes")
    return note_group_idx


def _or_head_mask_range(masks: list[int], *, start: int, end: int, head_len: int) -> None:
    s = max(0, int(start))
    e = min(int(end), int(head_len))
    for note_idx in range(s, e):
        word = int(note_idx) >> 5
        bit = int(note_idx) & 31
        masks[word] |= 1 << bit


def _surface_from_signature(
    signature: tuple[int, int, int, bytes], *, activations: int = 0, gap: int = 0
) -> TimelineSurface:
    head_len, body_fever, body_normal, packed = signature
    tmp = np.zeros(16, dtype=np.uint8)
    packed_arr = np.frombuffer(bytes(packed), dtype=np.uint8)
    tmp[: min(int(tmp.shape[0]), int(packed_arr.shape[0]))] = packed_arr[: int(tmp.shape[0])]
    out = np.frombuffer(tmp.tobytes(), dtype=np.uint32)
    return TimelineSurface(
        head_len=int(head_len),
        masks=(int(out[0]), int(out[1]), int(out[2]), int(out[3])),
        body_fever=int(body_fever),
        body_normal=int(body_normal),
        activations=int(activations),
        gap=int(gap),
    )


def _propagate_interval(
    *,
    lo: int,
    hi: int,
    g: int,
    group_base: np.ndarray,
    group_low: np.ndarray,
    group_high: np.ndarray,
) -> tuple[int, int]:
    delta = int(group_base[g]) - int(group_base[g - 1])
    if delta < 1:
        delta = 1
    return (
        max(int(group_low[g]), int(lo) - int(delta)),
        max(int(group_high[g]), int(hi) - int(delta)),
    )


def certify_zero_swing_singleton(
    prepared: dict,
    *,
    fill_count: int,
    d_ms: int,
    max_head: int = 100,
) -> ZeroSwingCertificate:
    """Return an exact singleton surface when the zero-swing proof holds.

    The proof is intentionally one-way. It may reject exact singleton cells, but
    a certified cell should be exact over all feasible grouped Perfect timings.
    """

    n = int(prepared.get("n", 0) or 0)
    if n <= 0:
        return ZeroSwingCertificate(
            certified=True,
            surface=TimelineSurface(0, (0, 0, 0, 0), 0, 0, 0, 0),
            reason="empty",
            activations=0,
            swing_checks=0,
            max_carry_width=0,
        )

    group_starts = np.asarray(prepared["group_starts"], dtype=np.int32)
    group_ends = np.asarray(prepared["group_ends"], dtype=np.int32)
    group_base = np.asarray(prepared["group_base_t"], dtype=np.int32)
    group_low = np.asarray(prepared["group_low"], dtype=np.int32)
    group_high = np.asarray(prepared["group_high"], dtype=np.int32)
    note_group_idx = _note_group_idx(prepared)
    gcount = int(group_starts.shape[0])
    if gcount <= 0:
        raise ValueError("non-empty song has no timing groups")

    global_low = int(np.min(group_low))
    global_high = int(np.max(group_high))

    head_len = int(min(n, int(max_head)))
    masks = [0, 0, 0, 0]
    body_fever = 0
    body_normal = 0
    activations = 0
    last_fever_end_idx = 0
    swing_checks = 0
    max_carry_width = 0

    current_note = 0
    fever_section = 0
    prev_group = -1
    lo = 0
    hi = 0

    def advance_to_group(target_g: int) -> None:
        nonlocal prev_group, lo, hi, max_carry_width
        target = int(target_g)
        if target < 0 or target >= gcount:
            return
        if prev_group == target:
            max_carry_width = max(max_carry_width, int(hi) - int(lo))
            return
        if prev_group < 0:
            lo = int(group_low[target])
            hi = int(group_high[target])
            prev_group = target
            max_carry_width = max(max_carry_width, int(hi) - int(lo))
            return
        if target < prev_group:
            raise ValueError("timing-envelope simulation attempted to move backward")
        for g in range(int(prev_group) + 1, int(target) + 1):
            lo, hi = _propagate_interval(
                lo=lo,
                hi=hi,
                g=int(g),
                group_base=group_base,
                group_low=group_low,
                group_high=group_high,
            )
        prev_group = target
        max_carry_width = max(max_carry_width, int(hi) - int(lo))

    while current_note < n:
        fever_section += 1
        notes_to_fill = int(fill_count) - 1 if fever_section == 1 else int(fill_count)
        if notes_to_fill < 0:
            notes_to_fill = 0

        start_normal_idx = int(current_note)
        end_normal_idx = int(min(n, int(current_note) + int(notes_to_fill)))

        body_normal_start = max(int(current_note), int(max_head))
        if end_normal_idx > body_normal_start:
            body_normal += int(end_normal_idx - body_normal_start)

        walk_note = int(start_normal_idx)
        while walk_note < end_normal_idx:
            g = int(note_group_idx[walk_note])
            if g < 0:
                g = 0
            if g >= gcount:
                break
            advance_to_group(g)
            walk_note = min(int(group_ends[g]), int(end_normal_idx))

        current_note = int(end_normal_idx)
        if current_note >= n:
            break
        if current_note <= 0:
            break

        activations += 1
        activation_note = int(current_note)
        s = int(note_group_idx[activation_note])
        if s < 0:
            s = 0
        if s >= gcount:
            break
        advance_to_group(s)

        r_lo = int(lo)
        r_hi = int(hi)
        q_min = int(group_base[s]) + int(r_lo) + int(d_ms)
        q_max = int(group_base[s]) + int(r_hi) + int(d_ms)

        start_g = int(s + 1)
        left = int(q_min - global_high)
        right = int(q_max - global_low)
        b_lo = int(np.searchsorted(group_base, left, side="left"))
        b_hi = int(np.searchsorted(group_base, right, side="left"))
        if b_lo < start_g:
            b_lo = start_g
        if b_hi < start_g:
            b_hi = start_g
        if b_lo < gcount and b_hi > b_lo:
            return ZeroSwingCertificate(
                certified=False,
                surface=None,
                reason="boundary_swing",
                activations=int(activations),
                swing_checks=int(swing_checks + 1),
                max_carry_width=int(max_carry_width),
            )
        swing_checks += 1

        out_group = int(np.searchsorted(group_base, right, side="left"))
        if out_group < start_g:
            out_group = start_g
        if out_group >= gcount:
            fever_end_idx = int(n)
            if gcount > start_g:
                advance_to_group(gcount - 1)
        else:
            advance_to_group(out_group)
            fever_end_idx = int(group_starts[out_group])

        fever_end_idx = max(int(activation_note), min(int(fever_end_idx), n))
        _or_head_mask_range(masks, start=int(activation_note), end=int(fever_end_idx), head_len=head_len)

        body_fever_start = max(int(activation_note), int(max_head))
        if fever_end_idx > body_fever_start:
            body_fever += int(fever_end_idx - body_fever_start)

        last_fever_end_idx = int(fever_end_idx)
        current_note = int(fever_end_idx)

    body_normal_start = max(int(current_note), int(max_head))
    if n > body_normal_start:
        body_normal += int(n - body_normal_start)

    surface = TimelineSurface(
        head_len=int(head_len),
        masks=tuple(int(x & 0xFFFFFFFF) for x in masks),  # type: ignore[arg-type]
        body_fever=int(body_fever),
        body_normal=int(body_normal),
        activations=int(activations),
        gap=int(n - int(last_fever_end_idx)),
    )
    reason = "no_fever" if activations <= 0 else "zero_swing"
    return ZeroSwingCertificate(
        certified=True,
        surface=surface,
        reason=reason,
        activations=int(activations),
        swing_checks=int(swing_checks),
        max_carry_width=int(max_carry_width),
    )


def brute_force_surfaces_for_small_prepared(
    prepared: dict,
    *,
    fill_count: int,
    d_ms: int,
    max_states: int = 100_000,
) -> set[TimelineSurface]:
    """Enumerate all grouped offsets for tiny synthetic envelopes.

    This is a verifier for the certificate, not a candidate production method.
    """

    from gear_optimizer.solver.timing_envelope import compute_fever_timeline_signature

    n = int(prepared.get("n", 0) or 0)
    group_starts = np.asarray(prepared["group_starts"], dtype=np.int32)
    group_ends = np.asarray(prepared["group_ends"], dtype=np.int32)
    group_base = np.asarray(prepared["group_base_t"], dtype=np.int32)
    group_low = np.asarray(prepared["group_low"], dtype=np.int32)
    group_high = np.asarray(prepared["group_high"], dtype=np.int32)
    ranges = [range(int(group_low[g]), int(group_high[g]) + 1) for g in range(int(group_starts.shape[0]))]

    state_count = 1
    for values in ranges:
        state_count *= len(values)
    if state_count > int(max_states):
        raise ValueError(f"synthetic brute force would enumerate {state_count} states")

    surfaces: set[TimelineSurface] = set()
    for offsets in itertools.product(*ranges):
        event_ms = np.empty(n, dtype=np.int32)
        prev_event = -(10**12)
        ok = True
        for g, off in enumerate(offsets):
            event = int(group_base[g]) + int(off)
            if event < prev_event:
                ok = False
                break
            s = int(group_starts[g])
            e = int(group_ends[g])
            event_ms[s:e] = int(event)
            prev_event = int(event)
        if not ok:
            continue
        sig, _mask, _bf, _bn = compute_fever_timeline_signature(
            event_ms,
            non_fever_base=int(fill_count),
            real_fever_time_ms=int(d_ms),
        )
        surfaces.add(_surface_from_signature(sig))
    return surfaces


def _cell_params(
    *,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    ref_arrays: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32).reshape(-1)
    ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32).reshape(-1)
    non_fever_cas = np.float32(max(0, int(total_notes) - int(long_notes))) * np.float32(0.333)
    fever_time_cas = np.float32(float(last_note_time)) * np.float32(0.15) + np.float32(0.15)
    fill_counts = np.ceil(non_fever_cas * ff).astype(np.int32)
    fill_counts = np.maximum(fill_counts, np.int32(1))
    d_ms = np.ceil(fever_time_cas * ft * np.float32(1000.0)).astype(np.int32)
    d_ms = np.maximum(d_ms, np.int32(0))
    return fill_counts, d_ms


def audit_song(calc_song: dict, ref_arrays: dict[str, np.ndarray], *, max_pairs: int = 0) -> SongAudit:
    prepared = prepare_perfect_envelope_for_song(calc_song)
    metadata = calc_song.get("metadata", {}) or {}
    total_notes = int(metadata.get("Total Notes", prepared.get("n", 0)) or 0)
    long_notes = int(metadata.get("Long Notes", 0) or 0)
    last_note_time = float(metadata.get("Last Note Time", 0.0) or 0.0)

    fill_counts, d_ms_values = _cell_params(
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        ref_arrays=ref_arrays,
    )
    fill_hist = Counter(int(x) for x in fill_counts.tolist())
    d_hist = Counter(int(x) for x in d_ms_values.tolist())
    pairs = [(fc, d) for fc in sorted(fill_hist) for d in sorted(d_hist)]
    if int(max_pairs) > 0:
        pairs = pairs[: int(max_pairs)]

    t0 = time.perf_counter()
    certified_pairs = 0
    certified_grid_cells = 0
    no_fever_pairs = 0
    uncertain_pairs = 0
    max_carry_width = 0
    frontier_hist: Counter[int] = Counter()

    for fill_count, d_ms in pairs:
        result = certify_zero_swing_singleton(prepared, fill_count=int(fill_count), d_ms=int(d_ms))
        max_carry_width = max(max_carry_width, int(result.max_carry_width))
        multiplicity = int(fill_hist[int(fill_count)]) * int(d_hist[int(d_ms)])
        if result.certified:
            certified_pairs += 1
            certified_grid_cells += int(multiplicity)
            if result.reason == "no_fever":
                no_fever_pairs += 1
            frontier_hist[1] += 1
        else:
            uncertain_pairs += 1
            frontier_hist[0] += 1

    wall_ms = (time.perf_counter() - t0) * 1000.0
    return SongAudit(
        song=str(metadata.get("Song Name") or "unknown"),
        notes=int(total_notes),
        groups=int(np.asarray(prepared.get("group_starts", ())).shape[0]),
        unique_pairs=int(len(pairs)),
        grid_cells=int(fill_counts.shape[0] * d_ms_values.shape[0]),
        certified_pairs=int(certified_pairs),
        certified_grid_cells=int(certified_grid_cells),
        no_fever_pairs=int(no_fever_pairs),
        uncertain_pairs=int(uncertain_pairs),
        max_carry_width=int(max_carry_width),
        frontier_hist=frontier_hist,
        wall_ms=float(wall_ms),
    )


def _synthetic_prepared(*, base_ms: Iterable[int], low: int, high: int) -> dict:
    bases = np.asarray(list(base_ms), dtype=np.int32)
    n = int(bases.shape[0])
    return {
        "n": n,
        "ts_ms": bases.copy(),
        "group_starts": np.arange(n, dtype=np.int32),
        "group_ends": np.arange(1, n + 1, dtype=np.int32),
        "group_base_t": bases.copy(),
        "group_low": np.full(n, int(low), dtype=np.int32),
        "group_high": np.full(n, int(high), dtype=np.int32),
    }


def run_self_test() -> None:
    prepared = _synthetic_prepared(base_ms=[0, 1000, 2000, 3000, 4000, 5000], low=0, high=1)
    cert = certify_zero_swing_singleton(prepared, fill_count=2, d_ms=500)
    brute = brute_force_surfaces_for_small_prepared(prepared, fill_count=2, d_ms=500)
    if not cert.certified or cert.surface is None:
        raise AssertionError(f"expected zero-swing certificate, got {cert}")
    cert_cmp = TimelineSurface(
        cert.surface.head_len, cert.surface.masks, cert.surface.body_fever, cert.surface.body_normal, 0, 0
    )
    brute_cmp = {TimelineSurface(x.head_len, x.masks, x.body_fever, x.body_normal, 0, 0) for x in brute}
    if brute_cmp != {cert_cmp}:
        raise AssertionError(f"certificate mismatch: cert={cert_cmp} brute={brute_cmp}")

    boundary = _synthetic_prepared(base_ms=[0, 1000, 1500, 2000], low=0, high=1)
    rejected = certify_zero_swing_singleton(boundary, fill_count=2, d_ms=500)
    if rejected.certified:
        raise AssertionError(f"expected boundary cell to be unknown, got {rejected}")


def _print_audit(audit: SongAudit) -> None:
    pair_pct = (100.0 * audit.certified_pairs / audit.unique_pairs) if audit.unique_pairs else 0.0
    cell_pct = (100.0 * audit.certified_grid_cells / audit.grid_cells) if audit.grid_cells else 0.0
    per_pair_us = (audit.wall_ms * 1000.0 / audit.unique_pairs) if audit.unique_pairs else 0.0
    print(
        f"{audit.song}: notes={audit.notes} groups={audit.groups} "
        f"certified_pairs={audit.certified_pairs}/{audit.unique_pairs} ({pair_pct:.2f}%) "
        f"certified_grid={audit.certified_grid_cells}/{audit.grid_cells} ({cell_pct:.2f}%) "
        f"no_fever_pairs={audit.no_fever_pairs} unknown_pairs={audit.uncertain_pairs} "
        f"max_carry_width={audit.max_carry_width} wall={audit.wall_ms:.1f}ms "
        f"({per_pair_us:.1f}us/pair)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--song", action="append", default=[], help="Song file to audit. Can be supplied multiple times."
    )
    parser.add_argument(
        "--max-pairs", type=int, default=0, help="Cap unique (fill_count,d_ms) pairs for quick sampling."
    )
    parser.add_argument("--self-test", action="store_true", help="Run tiny brute-force certificate checks.")
    args = parser.parse_args(argv)

    if args.self_test:
        run_self_test()
        print("self-test: passed")

    if not args.song:
        return 0

    ref_arrays = _load_ref_arrays()
    for song_path in args.song:
        calc_song = _read_song(song_path)
        audit = audit_song(calc_song, ref_arrays, max_pairs=int(args.max_pairs))
        _print_audit(audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
