#!/usr/bin/env python3
"""Verify current-main FG winners against a game-source-faithful score oracle.

This tool is investigation-oriented and intentionally fail-loud. For each song:

1. Resolve and optionally solve the chart into an isolated DB.
2. Read the top persisted FG row from `team_buff_fg_loadouts`.
3. Rebuild the per-note Fever/Great witness from the persisted frontier trace.
4. Prove that witness matches the persisted response surface head bits/body counts.
5. Re-score the same witness with a direct port of the decompiled game score path.

The score oracle comes from the game source, not the optimizer scorer:
  - Perfect points use the decompiled `GearStats.N(...)` curve.
  - Fever multiplier uses the same source curve.
  - Combo multiplier uses the decompiled piecewise combo path.
  - Hidden source fields that are not present in optimizer-visible loadouts are
    treated at their baseline 0 value. MEASURED on the Calamity Fortune anchor:
    `ComboThreshold=0` matches the persisted FG score exactly; wiring the visible
    Combo Multiplier stat into ComboThreshold does not.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from gear_optimizer.core.time_quantize import quantize_to_int_ms
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song, scan_song_header
from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


DIFF_FOLDERS = {"easy": "Easy", "normal": "Normal", "hard": "Hard"}
VISIBLE_STATS_ORDER = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
)
TAIL_NOTE_TYPE = 3
TAIL_MULT = 2
PERFECT_LO_MS = -20
PERFECT_HI_MS = 40
GREAT_LO_MS = -95
GREAT_HI_MS = 190
OKAY_LO_MS = -235
OKAY_HI_MS = 430
HIDDEN_COMBO_THRESHOLD_STAT = 0
HIDDEN_GREAT_POINTS_STAT = 0


def _fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    raise SystemExit(f"[verify_fg_game_oracle] {msg}")


def parse_song_arg(arg: str) -> tuple[str, str]:
    if "|" not in arg:
        _fail(f"bad SONG arg {arg!r}; expected 'NAME|DIFFICULTY'")
    name_q, diff_raw = (part.strip() for part in arg.rsplit("|", 1))
    diff_key = diff_raw.lower()
    if diff_key not in DIFF_FOLDERS:
        _fail(f"bad difficulty {diff_raw!r} in {arg!r}; expected Easy|Normal|Hard")
    if not name_q:
        _fail(f"empty song name in {arg!r}")
    return name_q, DIFF_FOLDERS[diff_key]


def resolve_chart(name_q: str, difficulty: str) -> tuple[str, Path]:
    diff_dir = REPO / "Data" / difficulty
    if not diff_dir.is_dir():
        _fail(f"missing chart folder: {diff_dir}")
    q = name_q.lower()
    matches: list[tuple[str, Path]] = []
    for fp in sorted(diff_dir.glob("*.txt")):
        meta = scan_song_header(str(fp))
        song_name = str((meta or {}).get("Song Name", "") or "")
        if song_name and q in song_name.lower():
            matches.append((song_name, fp))
    if not matches:
        _fail(f"no chart in Data/{difficulty}/ matches {name_q!r}")
    if len(matches) > 1:
        listing = "\n".join(f"      - {song_name}" for song_name, _fp in matches)
        _fail(f"{len(matches)} charts match {name_q!r} in {difficulty}; be more specific:\n{listing}")
    return matches[0]


def run_solve(song_name: str, difficulty: str, db_path: Path, repeats: int, idx: int) -> None:
    cfg_path = db_path.parent / f"_oracle_cfg_{idx}.ini"
    cfg_path.write_text(
        "[CalculateSong]\n"
        f"Song_Name = {song_name}\n"
        f"Difficulty = {difficulty}\n"
        "TargetPrimary = All\n"
        "TargetSecondary = All\n"
        "LoopForever = false\n\n"
        "[IterationEngine]\n"
        f"SongRepeats = {repeats}\n"
        "SongQueueLimit = 1\n",
        encoding="utf-8",
    )
    log_path = db_path.parent / f"_oracle_log_{idx}.log"
    env = dict(os.environ)
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["METAFINDER_CONFIG_PATH"] = str(cfg_path)
    env.setdefault("FG_RESPONSE_FRONTIER_CACHE_DIR", str(db_path.parent / "oracle_fg_cache"))
    env.setdefault("TIMELINE_FRONTIER_CACHE_DIR", str(db_path.parent / "oracle_timeline_cache"))
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.run([sys.executable, str(REPO / "main.py")], env=env, stdout=log, stderr=subprocess.STDOUT)
    cfg_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-25:])
        _fail(f"solve failed for {song_name!r} (exit {proc.returncode}); log tail:\n{tail}")
    log_path.unlink(missing_ok=True)


def build_calc_song(chart_path: Path) -> dict:
    base = get_base_calc_song(str(chart_path), {})
    if not base:
        _fail(f"could not load base calc_song for {chart_path}")
    calc_song = clone_calc_song(base)
    envelope = apply_timing_envelope(calc_song)
    if not envelope or envelope.get("mode") != "fg":
        _fail(f"timing envelope did not attach FG streams for {chart_path}: {envelope!r}")
    return calc_song


def response_surface_from_payload(raw: list[int]) -> FgResponseSurface:
    if not isinstance(raw, list) or len(raw) != 11:
        raise ValueError("FG row response_surface must be an 11-field list")
    return FgResponseSurface(*[int(v) for v in raw])


def bits_for_head(mask: np.ndarray, head_len: int) -> list[int]:
    words: list[int] = []
    for word_idx in range(4):
        word = 0
        for bit_idx in range(32):
            i = word_idx * 32 + bit_idx
            if i < head_len and bool(mask[i]):
                word |= 1 << bit_idx
        words.append(int(word))
    return words


def note_window_bounds_ms(note_type: int) -> tuple[int, int, int, int]:
    mult = TAIL_MULT if int(note_type) == TAIL_NOTE_TYPE else 1
    return (
        int(PERFECT_LO_MS * mult),
        int(PERFECT_HI_MS * mult),
        int(GREAT_LO_MS * mult),
        int(GREAT_HI_MS * mult),
    )


def floor_envelopes_ms(chart_ms: np.ndarray, note_types: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mult = np.where(np.asarray(note_types, dtype=np.int16) == TAIL_NOTE_TYPE, TAIL_MULT, 1).astype(np.int32)
    perfect_floor = np.maximum.accumulate(chart_ms + (PERFECT_LO_MS * mult).astype(np.int32))
    great_floor = np.maximum.accumulate(chart_ms + (GREAT_LO_MS * mult).astype(np.int32))
    return perfect_floor.astype(np.int32), great_floor.astype(np.int32)


def fever_great_masks_from_trace(
    trace: list[dict[str, object]],
    *,
    total_notes: int,
    surface: FgResponseSurface,
) -> tuple[np.ndarray, np.ndarray]:
    fever = np.zeros(total_notes, dtype=np.bool_)
    great = np.zeros(total_notes, dtype=np.bool_)
    for sec in trace:
        activation_index = int(sec["activation_index"])
        fever_end_index = int(sec["fever_end_index"])
        forced_start = int(sec.get("forced_run_start_index", sec["forced_start_index"]))
        forced_prefix = int(sec.get("forced_run_count", sec["forced_prefix_count"]))
        if activation_index < 0 or fever_end_index < activation_index or fever_end_index > total_notes:
            raise ValueError("FG trace contains an invalid activation/fever interval")
        if forced_start < 0 or forced_start + forced_prefix > total_notes:
            raise ValueError("FG trace contains an invalid forced-prefix interval")
        fever[activation_index:fever_end_index] = True
        great[forced_start : forced_start + forced_prefix] = True
        if str(sec.get("activation_judgment") or "") == "late_great":
            great[activation_index] = True
        early_start = int(sec.get("early_great_start", -1) or -1)
        early_end = int(sec.get("early_great_end", -1) or -1)
        if early_start >= 0:
            if early_end <= early_start or early_end > total_notes:
                raise ValueError("FG trace contains an invalid early-Great tail interval")
            great[early_start:early_end] = True

    head_len = min(total_notes, 100)
    if bits_for_head(fever, head_len) != [int(surface.fever0), int(surface.fever1), int(surface.fever2), int(surface.fever3)]:
        raise ValueError("trace-derived Fever head mask does not match persisted response_surface")
    if bits_for_head(great, head_len) != [int(surface.great0), int(surface.great1), int(surface.great2), int(surface.great3)]:
        raise ValueError("trace-derived Great head mask does not match persisted response_surface")
    body_slice = slice(head_len, total_notes)
    body_counts = [
        int(np.count_nonzero(fever[body_slice])),
        int(np.count_nonzero(great[body_slice])),
        int(np.count_nonzero(np.logical_and(fever, great)[body_slice])),
    ]
    surface_counts = [int(surface.body_fever), int(surface.body_great), int(surface.body_fever_great)]
    if body_counts != surface_counts:
        raise ValueError(
            f"trace-derived body counts {body_counts} do not match persisted response_surface {surface_counts}"
        )
    return fever, great


def reconstruct_visible_stats(force_details: dict[str, object], details: dict[str, object]) -> dict[str, int]:
    """Return the FG row's visible (gem-applied) stats.

    Current schema: `force_details.BaseStats` IS the post-gem visible stats row
    (the persisted GemCounts/FT/FF allocation is already included in it), and
    `details.st` packs the same row in VISIBLE_STATS_ORDER. The two are
    persisted independently, so equality is a real integrity check. The former
    pre-gem reconstruction (re-adding gem scales on top of BaseStats) predates
    post-gem persistence and double-counted every gem on current rows.
    """
    base_stats = force_details.get("BaseStats")
    gem_counts = force_details.get("GemCounts")
    if not isinstance(base_stats, dict):
        raise ValueError("FG row force_details_json requires BaseStats")
    if not isinstance(gem_counts, dict):
        raise ValueError("FG row force_details_json requires GemCounts")

    stats = {key: int(base_stats.get(key, 0) or 0) for key in VISIBLE_STATS_ORDER}

    packed = details.get("st")
    if isinstance(packed, list) and len(packed) == len(VISIBLE_STATS_ORDER):
        packed_stats = [int(v) for v in packed]
        visible_stats = [int(stats[key]) for key in VISIBLE_STATS_ORDER]
        if packed_stats != visible_stats:
            raise ValueError(f"visible stats mismatch: details.st={packed_stats} force_details.BaseStats={visible_stats}")
    return stats


@dataclass(frozen=True)
class BezierDist:
    x0: float
    y0: float
    x1: float
    y1: float
    x2: float
    y2: float
    x3: float
    y3: float
    segments: int = 10

    def _samples(self) -> list[tuple[float, float]]:
        samples = [(0.0, 0.0)]
        prev_x = float(self.x0)
        prev_y = float(self.y0)
        dist = 0.0
        t = 0.0
        for _ in range(int(self.segments)):
            t += 1.0 / float(self.segments)
            x = bezier_val(self.x0, self.x1, self.x2, self.x3, t)
            y = bezier_val(self.y0, self.y1, self.y2, self.y3, t)
            dist += math.hypot(x - prev_x, y - prev_y)
            samples.append((t, dist))
            prev_x = x
            prev_y = y
        return samples

    def get_y_for_distance_pct(self, pct: float) -> float:
        samples = self._samples()
        total_dist = float(samples[-1][1])
        target = max(0.0, min(1.0, float(pct))) * total_dist
        if target >= total_dist:
            t = 1.0
        else:
            lo = 0
            hi = len(samples) - 1
            while hi - lo > 1:
                mid = math.floor((lo + hi) * 0.5)
                if float(samples[mid][1]) < target:
                    lo = mid
                else:
                    hi = mid
            t0, d0 = samples[lo]
            t1, d1 = samples[hi]
            t = t0 if d1 == d0 else lerp(t0, t1, (target - d0) / (d1 - d0))
        return bezier_val(self.y0, self.y1, self.y2, self.y3, t)


NEG_80_40 = BezierDist(0, 0, 0.4, 0.1, 1, 0.8, 1, 1)
NEG_40_0 = BezierDist(0, 0, 0.8, 0, 0.9, 0.8, 1, 1)
POS_0_40 = BezierDist(0, 0, 0, 0.4, 0.7, 0.9, 1, 1)
POS_40_80 = BezierDist(0, 0, 0.2, 0.1, 0.4, 1, 1, 1)
POS_80_160 = BezierDist(0, 0, 0, 0.5, 0.6, 1, 1, 1)


def lerp(a: float, b: float, t: float) -> float:
    return (float(b) - float(a)) * float(t) + float(a)


def bezier_val(a: float, b: float, c: float, d: float, t: float) -> float:
    omt = 1.0 - float(t)
    return (omt * omt * omt * float(a)) + (3.0 * float(t) * omt * omt * float(b)) + (3.0 * float(t) * float(t) * omt * float(c)) + (float(t) * float(t) * float(t) * float(d))


def line_y_for_x(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    m = (float(y1) - float(y2)) / (float(x1) - float(x2))
    return (m * float(x)) + (float(y1) - (m * float(x1)))


def gear_curve(a: float, b: float, c: float, d: float, e: float, stat: int) -> float:
    v = max(-80, min(160, int(stat)))
    if v > 0:
        if v < 40:
            return lerp(c, d, POS_0_40.get_y_for_distance_pct(line_y_for_x(0, 0, 40, 1, v)))
        if v > 80:
            return lerp(e, e + (e - d) * 0.35, POS_80_160.get_y_for_distance_pct(line_y_for_x(80, 0, 160, 1, v)))
        return lerp(d, e, POS_40_80.get_y_for_distance_pct(line_y_for_x(40, 0, 80, 1, v)))
    if v < 0:
        if v > -40:
            return lerp(b, c, NEG_40_0.get_y_for_distance_pct(line_y_for_x(-40, 0, 0, 1, v)))
        return lerp(a, b, NEG_80_40.get_y_for_distance_pct(line_y_for_x(-80, 0, -40, 1, v)))
    return float(c)


def combo_multiplier_for_chain(combo_stat: int, chain: int) -> float:
    threshold3 = gear_curve(600, 450, 100, 20, 10, HIDDEN_COMBO_THRESHOLD_STAT)
    t1 = math.floor(threshold3 * 0.25)
    t2 = math.floor(threshold3 * 0.5)
    t3 = float(threshold3)
    v = gear_curve(0, 0.25, 1, 1.4, 1.6, combo_stat)
    m1 = 1.0 + (v * 0.25)
    m2 = 1.0 + (v * 0.5)
    m3 = 1.0 + v
    chain_f = float(chain)
    if chain_f <= t1:
        return line_y_for_x(0, 1, t1, m1, chain_f)
    if chain_f <= t2:
        return line_y_for_x(t1, m1, t2, m2, chain_f)
    if chain_f <= t3:
        return line_y_for_x(t2, m2, t3, m3, chain_f)
    return float(m3)


def score_from_game_source(
    *,
    stats: dict[str, int],
    primary_color: str,
    secondary_color: str,
    fever_mask: np.ndarray,
    great_mask: np.ndarray,
) -> int:
    pp_points = math.floor(gear_curve(50, 100, 200, 350, 450, int(stats["Perfect Points"])))
    fever_mul = gear_curve(1, 1.25, 3, 4.75, 5.25, int(stats["Fever Multiplier"]))
    primary_val = int(stats.get(primary_color, 0))
    secondary_val = int(stats.get(secondary_color, 0)) if secondary_color else 0
    perfect_base = int(pp_points + math.floor(2 * primary_val) + math.floor(secondary_val))
    great_points = math.floor(gear_curve(35, 75, 150, 225, 300, HIDDEN_GREAT_POINTS_STAT))
    great_base = int(
        great_points
        + math.floor((4.0 / 3.0) * primary_val)
        + math.floor((2.0 / 3.0) * secondary_val)
    )

    score = 0
    total_notes = int(fever_mask.shape[0])
    for i in range(total_notes):
        chain = i + 1
        combo_mul = combo_multiplier_for_chain(int(stats["Combo Multiplier"]), chain)
        base_value = great_base if bool(great_mask[i]) else perfect_base
        if bool(fever_mask[i]):
            score += math.floor(float(base_value) * combo_mul * float(fever_mul))
        else:
            score += math.floor(float(base_value) * combo_mul)
    return int(score)


def measured_legality_checks(
    *,
    trace: list[dict[str, object]],
    fever_mask: np.ndarray,
    great_mask: np.ndarray,
    chart_ms: np.ndarray,
    note_types: np.ndarray,
) -> dict[str, int]:
    perfect_floor_ms, great_floor_ms = floor_envelopes_ms(chart_ms, note_types)
    early_tail_notes = 0
    late_great_activations = 0
    held_tail_late_great_activations = 0
    for sec in trace:
        activation_index = int(sec["activation_index"])
        note_type = int(note_types[activation_index])
        offset_ms = float(sec.get("activation_hit_offset_ms", 0.0) or 0.0)
        perfect_lo_ms, perfect_hi_ms, _great_lo_ms, great_hi_ms = note_window_bounds_ms(note_type)
        judgment = str(sec.get("activation_judgment") or "")
        lower = float(sec.get("activation_hit_window_lower_ms", 0.0) or 0.0)
        upper = float(sec.get("activation_hit_window_upper_ms", 0.0) or 0.0)
        hit_ms = float(sec.get("activation_hit_ms", 0.0) or 0.0)
        if judgment == "late_great":
            late_great_activations += 1
            if note_type == TAIL_NOTE_TYPE:
                held_tail_late_great_activations += 1
            if not (float(perfect_hi_ms) < offset_ms <= float(great_hi_ms)):
                raise ValueError(
                    f"late_great activation {activation_index} offset {offset_ms:.3f}ms is outside the legal raw late-Great window"
                )
        elif judgment == "perfect":
            if not (float(perfect_lo_ms) <= offset_ms <= float(perfect_hi_ms)):
                raise ValueError(
                    f"perfect activation {activation_index} offset {offset_ms:.3f}ms is outside the legal Perfect window"
                )
        else:
            raise ValueError(f"unsupported activation_judgment {judgment!r}")
        if not (lower <= hit_ms <= upper):
            raise ValueError(
                f"activation {activation_index} hit_ms {hit_ms:.3f} is outside the persisted witness interval [{lower:.3f}, {upper:.3f}]"
            )

        early_start = int(sec.get("early_great_start", -1) or -1)
        early_end = int(sec.get("early_great_end", -1) or -1)
        fever_end_ms = int(sec.get("fever_window_end_ms", 0) or 0)
        if early_start >= 0:
            if early_end <= early_start:
                raise ValueError("invalid early-Great tail interval")
            for idx in range(early_start, early_end):
                early_tail_notes += 1
                if not bool(fever_mask[idx]) or not bool(great_mask[idx]):
                    raise ValueError(f"early-Great note {idx} is not marked as Fever+Great")
                if not (int(great_floor_ms[idx]) < fever_end_ms <= int(perfect_floor_ms[idx])):
                    raise ValueError(
                        f"early-Great note {idx} does not satisfy great_floor < fever_end <= perfect_floor"
                    )
    return {
        "early_tail_notes": int(early_tail_notes),
        "late_great_activations": int(late_great_activations),
        "held_tail_late_great_activations": int(held_tail_late_great_activations),
    }


def fetch_best_fg_row(conn: sqlite3.Connection, song_name: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM team_buff_fg_loadouts WHERE song_name=? AND force_details_json IS NOT NULL ORDER BY fg_score DESC LIMIT 1",
        (song_name,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no persisted FG row found for {song_name}")
    return row


def verify_song(conn: sqlite3.Connection, song_name: str, chart_path: Path) -> dict[str, object]:
    row = fetch_best_fg_row(conn, song_name)
    details = json.loads(row["details_json"]) if row["details_json"] else {}
    force_details = json.loads(row["force_details_json"]) if row["force_details_json"] else {}
    fg_meta = force_details.get("ForceGreats")
    if not isinstance(fg_meta, dict):
        raise ValueError("FG row force_details_json requires a ForceGreats payload")
    trace = list(fg_meta.get("frontier_trace") or [])
    if not trace:
        raise ValueError("FG row ForceGreats.frontier_trace is empty")

    calc_song = build_calc_song(chart_path)
    chart_ms = quantize_to_int_ms(np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float32)).astype(np.int32)
    note_types = np.asarray(calc_song["song_data"]["note_types"], dtype=np.int16)
    total_notes = int(chart_ms.shape[0])
    surface = response_surface_from_payload(force_details.get("response_surface"))
    fever_mask, great_mask = fever_great_masks_from_trace(trace, total_notes=total_notes, surface=surface)
    stats = reconstruct_visible_stats(force_details, details)
    measured = measured_legality_checks(
        trace=trace,
        fever_mask=fever_mask,
        great_mask=great_mask,
        chart_ms=chart_ms,
        note_types=note_types,
    )

    refs = get_exact_replay_ref_arrays_cached()
    if refs is None:
        raise ValueError("exact replay ref arrays are unavailable")
    source_score = score_from_game_source(
        stats=stats,
        primary_color=str(details.get("pc") or ""),
        secondary_color=str(details.get("sc") or ""),
        fever_mask=fever_mask,
        great_mask=great_mask,
    )
    exact_score = score_force_greats_response_surface_exact(stats, calc_song, refs, surface)
    optimizer_fg = int(row["fg_score"] or 0)
    if int(exact_score or 0) != optimizer_fg:
        raise ValueError(f"optimizer FG row {optimizer_fg} does not replay to the persisted exact_rescore {exact_score}")

    return {
        "song_name": song_name,
        "optimizer_fg": int(optimizer_fg),
        "oracle_fg": int(source_score),
        "delta": int(optimizer_fg - int(source_score)),
        "status": "LEGAL" if int(optimizer_fg) == int(source_score) else "OVER-SCORED",
        "team_buff": str(row["team_buff"] or ""),
        "forced_counts": list(force_details.get("forced_counts") or []),
        "great95_used": bool(int(measured["early_tail_notes"]) > 0),
        "trace_sections": len(trace),
        "early_tail_notes": int(measured["early_tail_notes"]),
        "late_great_activations": int(measured["late_great_activations"]),
        "held_tail_late_great_activations": int(measured["held_tail_late_great_activations"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify FG winners against a game-source score oracle.")
    ap.add_argument("songs", nargs="+", help="one or more 'NAME|DIFFICULTY' (e.g. \"Calamity Fortune|Hard\")")
    ap.add_argument("--db", default=".calc/oracle_verify.db", help="isolated DB path (default .calc/oracle_verify.db)")
    ap.add_argument("--repeats", type=int, default=1, help="SongRepeats per song (default 1)")
    ap.add_argument("--reuse-db", action="store_true", help="do not wipe the isolated DB before solving")
    ap.add_argument("--no-run", action="store_true", help="skip solving and verify the existing isolated DB")
    args = ap.parse_args(argv)

    specs = [parse_song_arg(arg) for arg in args.songs]
    resolved = [resolve_chart(name_q, difficulty) + (difficulty,) for name_q, difficulty in specs]
    db_path = Path(args.db) if os.path.isabs(args.db) else (REPO / args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    for song_name, chart_path, difficulty in resolved:
        print(f"resolved: {song_name} [{difficulty}] -> {chart_path}")

    if not args.no_run:
        if not args.reuse_db:
            for suffix in ("", "-wal", "-shm"):
                p = Path(str(db_path) + suffix)
                if p.exists():
                    p.unlink()
        for idx, (song_name, _chart_path, difficulty) in enumerate(resolved):
            print(f"  solving: {song_name} ({difficulty}) [repeats={args.repeats}] ...", flush=True)
            run_solve(song_name, difficulty, db_path, args.repeats, idx)

    if not db_path.exists():
        _fail(f"DB not found: {db_path} (run without --no-run first)")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        had_mismatch = False
        for song_name, chart_path, _difficulty in resolved:
            result = verify_song(conn, song_name, chart_path)
            print("=" * 78)
            print(f"SONG: {result['song_name']}")
            print(
                f"  optimizer_fg = {int(result['optimizer_fg']):,}   oracle_fg = {int(result['oracle_fg']):,}   "
                f"delta = {int(result['delta']):,}   status = {result['status']}"
            )
            print(
                f"  team_buff={result['team_buff']}  forced_counts={result['forced_counts']}  "
                f"great95_used={result['great95_used']}  trace_sections={result['trace_sections']}"
            )
            print(
                f"  early_tail_notes={result['early_tail_notes']}  late_great_activations={result['late_great_activations']}  "
                f"held_tail_late_great_activations={result['held_tail_late_great_activations']}"
            )
            had_mismatch = had_mismatch or (str(result["status"]) != "LEGAL")
        return 1 if had_mismatch else 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
