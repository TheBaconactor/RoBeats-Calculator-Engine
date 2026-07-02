"""Verify base TimelineFrontier.frontier_trace witness self-consistency (issue #41).

For every unique (fill_count, d_ms) cell of a song, reconstruct the canonical
surface's trace and assert each section is a complete, self-consistent timing
witness:

  * activation_hit_offset_ms == activation_hit_offset_upper_ms  (largest cushion)
  * activation_hit_offset_lower_ms <= activation_hit_offset_upper_ms
  * activation_hit_ms == activation_ms + activation_hit_offset_ms
  * fever_window_end_ms == activation_hit_ms + d_ms             (duration is d_ms)
  * the carry endpoint certificate holds at the reported offset: the first-out
    note's latest Perfect hit is at/after the window end, and the last-in note's
    earliest Perfect hit is before it (so the witness reproduces fever_end_index).

Usage: python tools/verify/verify_timeline_trace_witness.py ["Data/<Diff>/<song>.txt" ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.config import load_config
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays
from gear_optimizer.solver.timeline_exact_frontier import (
    _build_grouped_timeline_context,
    _build_exact_timeline_frontier_from_context,
    reconstruct_timeline_frontier_trace,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope, floor_to_int_ms
from gear_optimizer.solver.taichi_gem.api.timeline import _get_or_build_frontier_group_payload

CARRY_L, CARRY_U = -40, 80
DEFAULT_SONGS = [
    "Data/Easy/(The) Red  Room (Easy) by Camellia.txt",
    "Data/Normal/LiFE Garden by Yooh.txt",
    "Data/Hard/#include signal.h (Hard) by Kurokotei.txt",
]


def verify_song(song_rel: str) -> tuple[int, int]:
    cfg_dict = cfg_to_dict(load_config())
    calc_song = get_base_calc_song(str(PROJECT_ROOT / song_rel), cfg_dict)
    apply_timing_envelope(calc_song, attach_fg=False)
    song_data = calc_song.get("song_data", {})
    ts = np.asarray(song_data.get("chart_timestamps"), dtype=np.float32)
    chart_ms = floor_to_int_ms(ts).astype(np.int64)
    total_notes = int(ts.shape[0])
    meta = calc_song.get("metadata", {}) or {}
    last_note_time = float(ts[-1]) if total_notes else 0.0
    long_notes = int(meta.get("Long Notes", meta.get("LongNotes", 0)) or 0)

    ref_arrays = resolve_exact_replay_ref_arrays(read_table(str(PROJECT_ROOT / "Data/Gear/Stats.txt")))
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32).reshape(-1)
    non_fever_cas = float(max(0, total_notes - long_notes)) * 0.333
    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    fill_counts = np.maximum(np.ceil(np.float32(non_fever_cas) * ref_ff).astype(np.int32), 1)
    d_ms_values = np.maximum(np.ceil(np.float32(fever_time_cas) * ref_ft * np.float32(1000.0)).astype(np.int32), 0)

    gp = _get_or_build_frontier_group_payload(("verify", song_rel), timestamps=ts, note_types=song_data.get("note_types"))
    gs = np.asarray(gp["group_starts"], dtype=np.int32)
    ge = np.asarray(gp["group_ends"], dtype=np.int32)
    gb = np.asarray(gp["group_base_t_ms"], dtype=np.int32)
    gl = np.asarray(gp["group_low_ms"], dtype=np.int32)
    gh = np.asarray(gp["group_high_ms"], dtype=np.int32)
    ngi = np.asarray(gp["note_group_idx"], dtype=np.int32)
    ctx = _build_grouped_timeline_context(total_notes, group_starts=gs, group_ends=ge, group_base_t_ms=gb,
                                          group_low_ms=gl, group_high_ms=gh, note_group_idx=ngi)
    earliest = chart_ms + np.maximum(CARRY_L, gl[ngi]).astype(np.int64)
    latest = chart_ms + np.minimum(CARRY_U, gh[ngi]).astype(np.int64)

    sections = 0
    carry_only = 0
    pairs = sorted(set(zip((int(x) for x in fill_counts.tolist()), (int(x) for x in d_ms_values.tolist()))))
    for fc, d in pairs:
        pack = _build_exact_timeline_frontier_from_context(ctx, fill_count=fc, d_ms=d)
        trace = reconstruct_timeline_frontier_trace(
            total_notes=total_notes, group_starts=gs, group_ends=ge, group_base_t_ms=gb,
            group_low_ms=gl, group_high_ms=gh, note_group_idx=ngi,
            fill_count=fc, d_ms=d, target_surface=pack.canonical)
        for row in trace:
            sections += 1
            a = int(row["activation_index"]); fe = int(row["fever_end_index"])
            w = int(row["fever_start_note_index"])
            off = float(row["activation_hit_offset_ms"])
            up = float(row["activation_hit_offset_upper_ms"])
            lo = float(row["activation_hit_offset_lower_ms"])
            assert row["activation_hit_offset_kind"] == "largest_cushion", f"{song_rel}: witness not labeled largest_cushion"
            assert off == up, f"{song_rel} fc={fc} d={d}: offset {off} != upper {up} (not largest cushion)"
            assert lo <= up, f"{song_rel} fc={fc} d={d}: lower {lo} > upper {up}"
            # The physical activating hit names witness note `w` (the count/mask
            # boundary stays `a`): the hit fields must be anchored to w's chart
            # time and every reported offset must be a legal Perfect hit for w's
            # OWN window (a chorded held tail's wider window must not leak
            # through the carry clock onto a narrower note).
            assert 0 <= w <= a, f"{song_rel} fc={fc} d={d}: witness note {w} after count boundary {a}"
            assert float(row["activation_ms"]) == float(chart_ms[w]), (
                f"{song_rel} fc={fc} d={d}: activation_ms {row['activation_ms']} != witness note #{w} chart ms {chart_ms[w]}"
            )
            assert int(gl[ngi[w]]) <= lo and up <= int(gh[ngi[w]]), (
                f"{song_rel} fc={fc} d={d}: witness offsets [{lo}, {up}] outside "
                f"witness note #{w}'s own Perfect window [{int(gl[ngi[w]])}, {int(gh[ngi[w]])}]"
            )
            assert float(row["activation_hit_ms"]) == float(row["activation_ms"]) + off
            we = float(row["fever_window_end_ms"])
            assert we == float(row["activation_hit_ms"]) + float(d), f"{song_rel}: window end != hit + d_ms"
            # Carry endpoint certificate at the reported offset.
            window_end = int(row["activation_ms"]) + int(off) + int(d)
            first_out_ok = (fe >= total_notes) or (int(latest[fe]) >= window_end)
            last_in_ok = (fe - 1 < a) or (int(earliest[fe - 1]) < window_end)
            assert first_out_ok and last_in_ok, f"{song_rel} fc={fc} d={d}: endpoint cert failed sec a={a} fe={fe}"
            # Is this section reproducible by a *single* activation-only offset?
            offs = np.arange(max(CARRY_L, int(gl[ngi[w]])), min(CARRY_U, int(gh[ngi[w]])) + 1, dtype=np.int64)
            ao = bool((np.searchsorted(chart_ms, int(chart_ms[w]) + offs + int(d), side="left") == fe).any())
            if not ao:
                carry_only += 1
    return sections, carry_only


def main(songs: list[str]) -> int:
    grand = 0
    for song in songs:
        sections, carry_only = verify_song(song)
        grand += sections
        print(f"OK {song}: {sections} sections consistent ({carry_only} carry-dependent, certified via endpoints)")
    print(f"ALL CONSISTENT: {grand} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or DEFAULT_SONGS))
