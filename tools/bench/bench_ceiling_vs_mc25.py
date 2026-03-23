"""
Benchmark / verification: GPU ceiling timeline vs Monte Carlo HitSim (25 seeds).

This script answers:
1) Does the new ceiling timeline differ from the old 25-repeat sampling outcome?
2) Does the GPU ceiling kernel match a CPU reimplementation of the same algorithm?
3) Where do the timelines differ (per-window activation/end indices)?

Run:
  python tools/bench/bench_ceiling_vs_mc25.py

Optional:
  python tools/bench/bench_ceiling_vs_mc25.py --song "<path-to-song.txt>" --ft 160 --ff 0 --seeds 25
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _find_default_song() -> str | None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    hard = os.path.join(root, "Data", "Hard")
    if not os.path.isdir(hard):
        return None
    want = "Everything Will Freeze (Vocal) [EXTENDED CUT] (Hard)"
    for name in sorted(os.listdir(hard)):
        if want in name and name.lower().endswith(".txt"):
            return os.path.join(hard, name)
    return None


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
        tmp = []
        for v in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(v)
            try:
                val = stats_table[lookup_index][i] if stats_table else 0.0
            except Exception:
                val = 0.0
            tmp.append(float(val))
        out[name] = np.asarray(tmp, dtype=np.float32)
    return out


def _read_song(fp: str) -> dict:
    from gear_optimizer.pipeline.song_processor import read_song_file

    song = read_song_file(fp)
    details = song.get("song_details", {}) or {}
    timestamps = np.asarray(song.get("timestamps", ()), dtype=np.float32)
    note_types = np.asarray(song.get("note_types", ()), dtype=np.int16)

    # Fall back if header is malformed.
    try:
        long_notes = int(float(details.get("Long Notes", 0) or 0))
    except Exception:
        long_notes = 0

    meta = {
        "Song Name": str(details.get("Song Name") or os.path.basename(fp)),
        "Difficulty": str(details.get("Difficulty") or "Hard"),
        "Primary Color": str(details.get("Primary Color") or ""),
        "Secondary Color": str(details.get("Secondary Color") or ""),
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


def _count_head_fever_from_bool(mask: np.ndarray) -> int:
    m = np.asarray(mask, dtype=np.bool_).reshape(-1)
    return int(np.count_nonzero(m))


def _pack_head_bits(mask: np.ndarray, head_len: int) -> tuple[int, int, int, int]:
    head = np.asarray(mask[:head_len], dtype=np.uint8)
    packed = np.packbits(head, bitorder="little").astype(np.uint8, copy=False)
    # Pad to 16 bytes so we can safely view as 4 uint32s (GPU head bits layout).
    tmp = np.zeros(16, dtype=np.uint8)
    tmp[: min(int(tmp.shape[0]), int(packed.shape[0]))] = packed[: int(tmp.shape[0])]
    out = np.frombuffer(tmp.tobytes(), dtype=np.uint32)
    return (int(out[0]), int(out[1]), int(out[2]), int(out[3]))


@dataclass(frozen=True)
class _TimelineSig:
    head_len: int
    head_bits: tuple[int, int, int, int]
    body_fever: int
    body_normal: int
    fever_activations: int
    gap: int


def _score_from_sig(sig: _TimelineSig, *, base: float, combo: float, fever: float) -> int:
    from gear_optimizer.solver.scoring_core import fast_calculate_score

    # Unpack head bits to bool for the score function.
    head_len = int(sig.head_len)
    head = np.zeros(head_len, dtype=np.bool_)
    for i in range(head_len):
        w = i >> 5
        b = i & 31
        if (int(sig.head_bits[w]) >> b) & 1:
            head[i] = True

    return int(
        fast_calculate_score(
            float(base),
            float(combo),
            float(fever),
            head,
            int(sig.body_fever),
            int(sig.body_normal),
        )
    )


def _cpu_timeline_for_seed(
    timestamps: np.ndarray,
    *,
    long_notes: int,
    last_note_time: float,
    ff_factor: float,
    ft_factor: float,
    fever_mask_buffer: np.ndarray,
) -> tuple[np.ndarray, int, int, int, int]:
    from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices

    return calculate_fever_timeline_indices(
        np.asarray(timestamps, dtype=np.float32),
        int(timestamps.shape[0]),
        float(ff_factor),
        float(ft_factor),
        int(long_notes),
        float(last_note_time),
        fever_mask_buffer,
    )


def _cpu_trace_windows(
    timestamps: np.ndarray,
    *,
    long_notes: int,
    last_note_time: float,
    ff_factor: float,
    ft_factor: float,
) -> list[tuple[int, int]]:
    from math import ceil

    ts = np.asarray(timestamps, dtype=np.float32).reshape(-1)
    n = int(ts.shape[0])
    if n <= 0:
        return []

    non_fever_cas = float(max(0, n - int(long_notes))) * 0.333
    fill_count = int(ceil(non_fever_cas * float(ff_factor)))
    fill_count = max(1, fill_count)

    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    fever_time = float(fever_time_cas * float(ft_factor))

    out: list[tuple[int, int]] = []
    idx = 0
    section = 0
    while idx < n:
        section += 1
        notes_to_fill = (fill_count - 1) if section == 1 else fill_count
        if notes_to_fill < 0:
            notes_to_fill = 0
        idx = min(idx + int(notes_to_fill), n)
        if idx >= n or idx <= 0:
            break
        start = idx
        end_time = float(ts[start] + np.float32(fever_time))
        end = int(np.searchsorted(ts, end_time, side="left"))
        out.append((int(start), int(end)))
        idx = end
    return out


def _cpu_ceiling_timeline(
    chart_timestamps: np.ndarray,
    note_types: np.ndarray,
    *,
    long_notes: int,
    last_note_time: float,
    ff_factor: float,
    ft_factor: float,
) -> tuple[_TimelineSig, list[dict[str, int]]]:
    """
    CPU reimplementation of `compute_timeline_grid_ceiling_hitsim_kernel` for one (FT, FF) cell.

    Returns:
      - signature compatible with GPU grid output for the chosen cell
      - trace: list of dicts per fever window for introspection
    """
    from math import ceil
    from gear_optimizer.solver.hit_simulation import prepare_perfect_hit_simulation

    ts = np.asarray(chart_timestamps, dtype=np.float32).reshape(-1)
    nt = np.asarray(note_types, dtype=np.int16).reshape(-1)
    n = int(ts.shape[0])

    non_fever_cas = float(max(0, n - int(long_notes))) * 0.333
    fill_count = int(ceil(non_fever_cas * float(ff_factor)))
    fill_count = max(1, fill_count)

    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    d_ms = int(ceil(float(fever_time_cas * float(ft_factor) * 1000.0)))
    d_ms = max(0, d_ms)

    prepared = prepare_perfect_hit_simulation(
        ts,
        nt,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )

    group_starts = np.asarray(prepared.get("group_starts", ()), dtype=np.int32)
    group_ends = np.asarray(prepared.get("group_ends", ()), dtype=np.int32)
    group_base = np.asarray(prepared.get("group_base_t", ()), dtype=np.int32)
    group_low = np.asarray(prepared.get("group_low", ()), dtype=np.int32)
    group_high = np.asarray(prepared.get("group_high", ()), dtype=np.int32)
    gcount = int(group_starts.shape[0])
    if n > 0 and gcount <= 0:
        raise ValueError("prepare_perfect_hit_simulation produced no groups")

    note_group_idx = np.full(n, -1, dtype=np.int32)
    for g in range(gcount):
        s = int(group_starts[g])
        e = int(group_ends[g])
        note_group_idx[s:e] = int(g)
    if n > 0 and int(np.any(note_group_idx < 0)):
        raise ValueError("prepare_perfect_hit_simulation produced uncovered note indices")

    head_len = min(n, 100)
    head_mask = np.zeros(head_len, dtype=np.bool_)
    body_fever = 0
    body_normal = 0
    fever_activations = 0
    last_fever_end_idx = 0

    prev_group = -1
    prev_carry = 0

    def _delta_ms(g: int, prev_g: int) -> int:
        d = int(group_base[g]) - int(group_base[prev_g])
        return d if d >= 1 else 1

    def _prop(lo: int, hi: int, g: int) -> tuple[int, int]:
        d = _delta_ms(int(g), int(g - 1))
        l_g = int(group_low[g])
        u_g = int(group_high[g])
        out_lo = max(l_g, int(lo) - d)
        out_hi = max(u_g, int(hi) - d)
        return int(out_lo), int(out_hi)

    trace: list[dict[str, int]] = []

    current_note = 0
    section = 0
    while current_note < n:
        section += 1
        notes_to_fill = (fill_count - 1) if section == 1 else fill_count
        if notes_to_fill < 0:
            notes_to_fill = 0

        start_normal = int(current_note)
        end_normal = int(min(n, int(current_note) + int(notes_to_fill)))

        body_normal_start = max(start_normal, 100)
        if end_normal > body_normal_start:
            body_normal += int(end_normal - body_normal_start)

        # Carry propagation through the normal segment: choose latest feasible carry per group.
        walk_note = int(start_normal)
        while walk_note < end_normal:
            g = int(note_group_idx[walk_note]) if walk_note < n else 0
            if g < 0 or g >= gcount:
                break
            if g != prev_group:
                u_g = int(group_high[g])
                if prev_group < 0:
                    prev_carry = u_g
                else:
                    prev_carry = max(u_g, int(prev_carry) - _delta_ms(g, int(prev_group)))
                prev_group = g
            group_end = n if (g + 1) >= gcount else int(group_starts[g + 1])
            walk_note = min(group_end, end_normal)

        current_note = end_normal
        if current_note >= n or current_note <= 0:
            break

        fever_activations += 1
        activation_note = int(current_note)
        s = int(note_group_idx[activation_note])
        if s < 0 or s >= gcount:
            break

        if s != prev_group:
            u_s = int(group_high[s])
            if prev_group < 0:
                prev_carry = u_s
            else:
                prev_carry = max(u_s, int(prev_carry) - _delta_ms(s, int(prev_group)))
            prev_group = s

        r_act = int(prev_carry)
        c_s = int(group_base[s])
        Q = int(c_s + r_act + int(d_ms))

        b_minus = int(np.searchsorted(group_base, int(Q - 80), side="left"))
        b_plus = int(np.searchsorted(group_base, int(Q + 40), side="left"))

        start_g = int(s + 1)
        b_minus = max(start_g, min(b_minus, gcount))
        b_plus = max(start_g, min(b_plus, gcount))

        lo = r_act
        hi = r_act
        last_fever_group = s
        last_fever_hi = hi

        # Interior region propagation.
        g = start_g
        while g < b_minus:
            lo, hi = _prop(lo, hi, g)
            last_fever_group = g
            last_fever_hi = hi
            g += 1

        # Boundary band scan.
        exit_group = -1
        g = b_minus
        while g < b_plus and g < gcount:
            prev_lo = lo
            prev_hi = hi
            lo, hi = _prop(lo, hi, g)

            c_g = int(group_base[g])
            remain_hi = int(Q - c_g - 1)
            keep_hi = min(int(hi), int(remain_hi))
            if int(lo) <= int(keep_hi):
                hi = int(keep_hi)
                last_fever_group = g
                last_fever_hi = hi
                g += 1
                continue

            exit_group = g
            lo = prev_lo
            hi = prev_hi
            break

        if exit_group >= 0:
            fever_end = int(group_starts[exit_group])
        else:
            if b_plus < gcount:
                fever_end = int(group_starts[b_plus])
            else:
                fever_end = n

        fever_end = max(activation_note, min(int(fever_end), n))

        # Mark head range + count body range.
        if activation_note < head_len:
            head_mask[activation_note : min(head_len, fever_end)] = True
        body_fever_start = max(activation_note, 100)
        if fever_end > body_fever_start:
            body_fever += int(fever_end - body_fever_start)

        prev_group = int(last_fever_group)
        prev_carry = int(last_fever_hi)
        last_fever_end_idx = int(fever_end)
        current_note = int(fever_end)

        trace.append(
            {
                "activation_note": int(activation_note),
                "fever_end_idx": int(fever_end),
                "activation_group": int(s),
                "r_act": int(r_act),
                "Q": int(Q),
                "b_minus": int(b_minus),
                "b_plus": int(b_plus),
                "last_fever_group": int(last_fever_group),
                "last_fever_hi": int(last_fever_hi),
            }
        )

    body_normal_start = max(int(current_note), 100)
    if n > body_normal_start:
        body_normal += int(n - body_normal_start)

    head_bits = _pack_head_bits(head_mask, head_len)
    gap = int(n - int(last_fever_end_idx))
    sig = _TimelineSig(
        head_len=int(head_len),
        head_bits=head_bits,
        body_fever=int(body_fever),
        body_normal=int(body_normal),
        fever_activations=int(fever_activations),
        gap=int(gap),
    )
    return sig, trace


def _gpu_ceiling_timeline(calc_song: dict, ref_arrays: dict, *, ft_idx: int, ff_idx: int) -> _TimelineSig:
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu, reset_timeline_state
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    init_taichi()
    reset_timeline_state()

    os.environ["GPU_TIMELINE_CEILING_HITSIM"] = "1"
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

    ft = int(ft_idx)
    ff = int(ff_idx)
    head_len_grid = np.asarray(gpu_fields.grid_head_len.to_numpy()[0], dtype=np.int32)
    bits_grid = np.asarray(gpu_fields.grid_fever_masks_bits.to_numpy()[0], dtype=np.uint32)
    body_fever_grid = np.asarray(gpu_fields.grid_count_body_fever.to_numpy()[0], dtype=np.int32)
    body_normal_grid = np.asarray(gpu_fields.grid_count_body_normal.to_numpy()[0], dtype=np.int32)
    gap_grid = np.asarray(gpu_fields.grid_gap.to_numpy()[0], dtype=np.int32)
    act_grid = np.asarray(gpu_fields.grid_fever_activations.to_numpy()[0], dtype=np.int32)

    head_len = int(head_len_grid[ft, ff])
    bits = tuple(int(x) for x in bits_grid[ft, ff, :].tolist())
    body_fever = int(body_fever_grid[ft, ff])
    body_normal = int(body_normal_grid[ft, ff])
    gap = int(gap_grid[ft, ff])
    acts = int(act_grid[ft, ff])

    return _TimelineSig(
        head_len=head_len,
        head_bits=bits,  # type: ignore[arg-type]
        body_fever=body_fever,
        body_normal=body_normal,
        fever_activations=acts,
        gap=gap,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--song", type=str, default="", help="Path to a song .txt file (defaults to Everything Will Freeze)."
    )
    ap.add_argument("--ft", type=int, default=160, help="FT stat index (0-160).")
    ap.add_argument("--ff", type=int, default=0, help="FF stat index (0-160).")
    ap.add_argument("--seeds", type=int, default=25, help="Monte Carlo seed count (default: 25).")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if CPU/GPU ceiling mismatch or if ceiling scores below the MC best.",
    )
    args = ap.parse_args()

    fp = str(args.song or "").strip()
    if not fp:
        fp = _find_default_song() or ""
    if not fp or not os.path.exists(fp):
        raise SystemExit(f"Song not found: {fp!r}")

    calc_song = _read_song(fp)
    ref_arrays = _load_ref_arrays()

    ft_idx = int(args.ft)
    ff_idx = int(args.ff)

    ft_factor = float(ref_arrays["Fever Time"][ft_idx])
    ff_factor = float(ref_arrays["Fever Fill Rate"][ff_idx])
    long_notes = int(calc_song["metadata"].get("Long Notes", 0) or 0)
    last_note_time = float(calc_song["metadata"].get("Last Note Time", 0.0) or 0.0)
    chart_ts = np.asarray(calc_song["song_data"]["chart_timestamps"], dtype=np.float32)
    note_types = np.asarray(calc_song["song_data"]["note_types"], dtype=np.int16)

    n = int(chart_ts.shape[0])

    print(f"[song] {calc_song['metadata'].get('Song Name')} ({calc_song['metadata'].get('Difficulty')})")
    print(f"[song] notes={n} long_notes={long_notes} last_note_time={last_note_time:.3f}s")
    print(f"[cell] ft_idx={ft_idx} ff_idx={ff_idx} ft_factor={ft_factor:.6f} ff_factor={ff_factor:.6f}")

    base = 10000.0
    combo = float(ref_arrays["Combo Multiplier"][80])
    fever = float(ref_arrays["Fever Multiplier"][80])
    print(f"[score] base={base:.1f} combo_mul={combo:.6f} fever_mul={fever:.6f} (fixed for comparison)")

    # Warm JIT once (fever timeline + fast score).
    from gear_optimizer.solver.hit_simulation import simulate_perfect_hit_timestamps_with_great_candidates

    fever_mask_buffer = np.zeros(n, dtype=np.bool_)
    warm_ts, _, _ = simulate_perfect_hit_timestamps_with_great_candidates(
        chart_ts,
        note_types,
        seed=1337,
        distribution="uniform",
        great_mode="late",
    )
    _cpu_timeline_for_seed(
        warm_ts,
        long_notes=long_notes,
        last_note_time=last_note_time,
        ff_factor=ff_factor,
        ft_factor=ft_factor,
        fever_mask_buffer=fever_mask_buffer,
    )
    from gear_optimizer.solver.scoring_core import fast_calculate_score

    fast_calculate_score(base, combo, fever, np.zeros(min(n, 100), dtype=np.bool_), 0, max(0, n - 100))

    # Monte Carlo: best of N seeds (old behavior proxy).
    best_seed = None
    best_sig = None
    best_score = None
    all_scores: list[int] = []
    all_fever_notes: list[int] = []

    t0 = time.perf_counter()
    for s in range(1, int(args.seeds) + 1):
        sim_ts, _, dbg = simulate_perfect_hit_timestamps_with_great_candidates(
            chart_ts,
            note_types,
            seed=int(s),
            distribution="uniform",
            great_mode="late",
        )
        fever_mask_head, body_fever, body_normal, fever_acts, last_end = _cpu_timeline_for_seed(
            sim_ts,
            long_notes=long_notes,
            last_note_time=last_note_time,
            ff_factor=ff_factor,
            ft_factor=ft_factor,
            fever_mask_buffer=fever_mask_buffer,
        )
        head_len = int(fever_mask_head.shape[0])
        head_bits = _pack_head_bits(fever_mask_head, head_len)
        gap = int(n - int(last_end))
        sig = _TimelineSig(
            head_len=head_len,
            head_bits=head_bits,
            body_fever=int(body_fever),
            body_normal=int(body_normal),
            fever_activations=int(fever_acts),
            gap=int(gap),
        )
        score = _score_from_sig(sig, base=base, combo=combo, fever=fever)
        fever_notes = int(_count_head_fever_from_bool(fever_mask_head) + int(body_fever))

        all_scores.append(int(score))
        all_fever_notes.append(int(fever_notes))

        if best_score is None or int(score) > int(best_score):
            best_score = int(score)
            best_seed = int(s)
            best_sig = sig
            best_dbg = dbg

    t1 = time.perf_counter()

    assert best_seed is not None and best_sig is not None and best_score is not None

    print(f"[mc25] wall={((t1 - t0) * 1000.0):.1f}ms best_seed={best_seed} best_score={best_score}")
    try:
        print(f"[mc25] best_seed_dbg={best_dbg}")
    except Exception:
        pass
    best_head = np.unpackbits(
        np.asarray(best_sig.head_bits, dtype=np.uint32).view(np.uint8),
        bitorder="little",
    )[: best_sig.head_len]
    best_fever_notes = int(best_sig.body_fever + _count_head_fever_from_bool(best_head))
    print(f"[mc25] fever_notes(best)={best_fever_notes}")

    # CPU ceiling reimplementation.
    t2 = time.perf_counter()
    ceiling_sig_cpu, ceiling_trace = _cpu_ceiling_timeline(
        chart_ts,
        note_types,
        long_notes=long_notes,
        last_note_time=last_note_time,
        ff_factor=ff_factor,
        ft_factor=ft_factor,
    )
    t3 = time.perf_counter()

    ceiling_score = _score_from_sig(ceiling_sig_cpu, base=base, combo=combo, fever=fever)

    # GPU ceiling output (integration check).
    ceiling_sig_gpu = None
    if _has_taichi():
        t4 = time.perf_counter()
        ceiling_sig_gpu = _gpu_ceiling_timeline(calc_song, ref_arrays, ft_idx=ft_idx, ff_idx=ff_idx)
        t5 = time.perf_counter()
        print(f"[ceiling/gpu] wall={((t5 - t4) * 1000.0):.1f}ms")

    print(f"[ceiling/cpu] wall={((t3 - t2) * 1000.0):.1f}ms score={ceiling_score}")
    print(
        f"[compare] ceiling_vs_mc25: score_delta={int(ceiling_score) - int(best_score)} "
        f"fever_notes_delta={(ceiling_sig_cpu.body_fever - best_sig.body_fever)} (body-only; head diff shown below)"
    )

    same_as_mc = ceiling_sig_cpu == best_sig
    print(f"[compare] ceiling_sig == mc25_best_sig ? {same_as_mc}")

    if ceiling_sig_gpu is not None:
        same_cpu_gpu = ceiling_sig_gpu == ceiling_sig_cpu
        print(f"[compare] ceiling_sig_cpu == ceiling_sig_gpu ? {same_cpu_gpu}")
        if not same_cpu_gpu:
            print(f"[debug] cpu={ceiling_sig_cpu}")
            print(f"[debug] gpu={ceiling_sig_gpu}")
            if bool(args.strict):
                return 2

    if ceiling_score < int(best_score):
        print(f"[error] ceiling_score < mc_best_score: ceiling={ceiling_score} mc={best_score}")
        if bool(args.strict):
            return 3

    # Deep introspection: window boundaries.
    print("[trace] mc25_best windows (activation,end):")
    best_sim_ts, _, _ = simulate_perfect_hit_timestamps_with_great_candidates(
        chart_ts,
        note_types,
        seed=int(best_seed),
        distribution="uniform",
        great_mode="late",
    )
    mc_trace = _cpu_trace_windows(
        best_sim_ts,
        long_notes=long_notes,
        last_note_time=last_note_time,
        ff_factor=ff_factor,
        ft_factor=ft_factor,
    )
    print(f"[trace] mc25_best windows={len(mc_trace)}")  # type: ignore[arg-type]
    for i, (a, e) in enumerate(mc_trace[:16]):
        print(f"  {i:02d}: a={a} e={e} len={e - a}")
    if len(mc_trace) > 16:
        print(f"  ... (+{len(mc_trace) - 16} more)")

    print("[trace] ceiling windows:")
    print(f"[trace] ceiling windows={len(ceiling_trace)}")  # type: ignore[arg-type]
    for i, row in enumerate(ceiling_trace[:16]):
        a = int(row.get("activation_note", 0))
        e = int(row.get("fever_end_idx", 0))
        print(
            f"  {i:02d}: a={a} e={e} len={e - a} r_act={row.get('r_act')} Q={row.get('Q')} "
            f"band=[{row.get('b_minus')},{row.get('b_plus')})"
        )
    if len(ceiling_trace) > 16:
        print(f"  ... (+{len(ceiling_trace) - 16} more)")

    # Quick distribution summary.
    scores = np.asarray(all_scores, dtype=np.int64)
    fever_notes = np.asarray(all_fever_notes, dtype=np.int32)
    print(
        f"[mc25] score: min={int(scores.min())} p50={int(np.median(scores))} max={int(scores.max())} "
        f"fever_notes: min={int(fever_notes.min())} p50={int(np.median(fever_notes))} max={int(fever_notes.max())}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
