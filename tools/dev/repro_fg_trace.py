#!/usr/bin/env python3
"""CPU-only repro: build ONE named song's FG response frontier and reconstruct
every first-frontier surface's trace.

This is a scoring-correctness verifier for the radix-overflow fix in the FG
response-frontier BUILD kernel
(`gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu_numba.py`).
Pre-fix, a wide issue-#44 early-Great band let `body_fever_great >= pair_mod`, so
the `(normal_great, body_fever_great)` pack ALIASED onto a phantom surface; that
phantom then crashed trace reconstruction with
`ValueError("could not reconstruct FG response surface trace")`
(`response_builder.py`). Reconstructing the trace for *every* built first-frontier
surface forces any phantom to surface that crash.

Pure CPU: the response-frontier BUILD (numba) and trace reconstruction are
CPU-only. The exact per-surface FG replay used for `top_fg`
(`score_force_greats_response_surface_exact`) is also pure float64 CPU. No
GPU/Vulkan/Taichi scoring path is touched.

Reconstruction coverage: the phantom is a function only of a surface's packed
fields, and the radix overflow could alias ONLY surfaces carrying a large
body_fever_great. MEASURED: pure-Python reconstruction of a dense surface costs
~1-4 s, and there are ~7.3M distinct first-frontier surfaces on the worst-case
3020-note song, so exhaustive reconstruction is many days. This verifier instead
reconstructs the MOST-OVERFLOW-PRONE distinct surfaces -- highest body_fever_great
first, down to a floor -- under a hard wall-clock budget, plus a small breadth
sample, deduped globally by surface fields. Any phantom in that set fails loud.
Tunable via env:
  REPRO_BFG_FLOOR      (default 12)   only reconstruct surfaces with body_fever_great >= this
  REPRO_MAX_RECON      (default 1200) hard cap on number of reconstructions
  REPRO_SAMPLE_BREADTH (default 200)  uniform sample across the lower bands
  REPRO_BUDGET_S       (default 1500) hard wall-clock budget (s) for reconstruction
  REPRO_TOPFG_CELLS    (default 12)   FT/FF cells sampled to compute a real top_fg
On a small song, set REPRO_BFG_FLOOR=0 REPRO_MAX_RECON=10000000 REPRO_BUDGET_S=100000
to reconstruct the entire distinct-surface set.

Usage:
    python tools/dev/repro_fg_trace.py "Challenge Letter|Hard"

Each SONG arg is "NAME|DIFFICULTY":
    NAME        case-insensitive substring of the chart header "Song Name"
    DIFFICULTY  Easy | Normal | Hard
NAME must resolve to exactly one chart in Data/<DIFFICULTY>/ (fails loud on 0/>1).

Prints a final line:
    PASS: built <N> surfaces, reconstructed <M> traces, top_fg=<score>
or the full exception + traceback.
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# Route the FG response-frontier disk cache to a throwaway dir BEFORE importing any
# optimizer module, so the production `bin/fg_response_frontier_cache` is never read
# or written. `_fg_response_disk_cache_dir` reads this via env_get/os.environ live, and
# `reset_fg_response_frontier_payload_cache()` (below) clears the in-process memory
# cache, forcing a FRESH build off the current working tree.
_REPRO_CACHE_DIR = REPO / ".calc" / "repro_fg_cache"
_REPRO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["FG_RESPONSE_FRONTIER_CACHE_DIR"] = str(_REPRO_CACHE_DIR)

DIFF_FOLDERS = {"easy": "Easy", "normal": "Normal", "hard": "Hard"}


def _fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    raise SystemExit(f"[repro_fg_trace] {msg}")


def parse_song_arg(arg: str) -> tuple[str, str]:
    if "|" not in arg:
        _fail(f"bad SONG arg {arg!r}; expected 'NAME|DIFFICULTY'")
    name_q, diff_raw = (p.strip() for p in arg.rsplit("|", 1))
    diff_key = diff_raw.lower()
    if diff_key not in DIFF_FOLDERS:
        _fail(f"bad difficulty {diff_raw!r} in {arg!r}; expected Easy|Normal|Hard")
    if not name_q:
        _fail(f"empty song name in {arg!r}")
    return name_q, DIFF_FOLDERS[diff_key]


def resolve_chart_path(name_q: str, difficulty: str) -> tuple[str, str]:
    """Return (chart_file_path, header_song_name) for the one chart in
    Data/<difficulty>/ whose header 'Song Name' contains name_q (case-insensitive).
    Fail loud on 0 or >1 matches."""
    from gear_optimizer.data.song_io import scan_song_header

    diff_dir = REPO / "Data" / difficulty
    if not diff_dir.is_dir():
        _fail(f"missing chart folder: {diff_dir}")
    q = name_q.lower()
    matches: list[tuple[str, str]] = []
    for fp in sorted(diff_dir.glob("*.txt")):
        meta = scan_song_header(str(fp))
        nm = str((meta or {}).get("Song Name", "") or "")
        if nm and q in nm.lower():
            matches.append((str(fp), nm))
    if not matches:
        _fail(f"no chart in Data/{difficulty}/ matches {name_q!r}")
    if len(matches) > 1:
        listing = "\n".join(f"      - {nm}" for _fp, nm in matches)
        _fail(f"{len(matches)} charts match {name_q!r} in {difficulty}; be more specific:\n{listing}")
    return matches[0]


def build_calc_song(chart_path: str) -> dict:
    """Production calc_song build: cached base calc_song -> per-run clone ->
    timing-envelope streams (FG perfect/great candidate + floor envelopes)."""
    from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    base = get_base_calc_song(chart_path, {})
    if not base:
        _fail(f"could not load base calc_song for {chart_path}")
    calc_song = clone_calc_song(base)
    envelope = apply_timing_envelope(calc_song)
    if not envelope or envelope.get("mode") != "fg":
        _fail(f"timing envelope did not attach FG streams for {chart_path}: {envelope!r}")
    return calc_song


def load_ref_arrays() -> dict:
    """Production exact-replay ref arrays (float64 gear stat curves from the Stats
    CSV). These are the curves the real optimizer/prebuild use; they are designed to
    sit inside the head-dominance box, so the build's `_assert_head_dominance_box_covers`
    accepts them. Fail loud if the Stats CSV is not discoverable (do NOT fabricate)."""
    from gear_optimizer.helpers.song_helpers.ref_array_builder import (
        get_exact_replay_ref_arrays_cached,
    )

    ref_arrays = get_exact_replay_ref_arrays_cached()
    if not ref_arrays:
        _fail(
            "could not build production ref_arrays from the Stats CSV "
            "(get_exact_replay_ref_arrays_cached returned None) -- check paths cache / Stats path"
        )
    required = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")
    missing = [k for k in required if k not in ref_arrays]
    if missing:
        _fail(f"production ref_arrays missing required curves: {missing}")
    return ref_arrays


def _stats_for_cell(ft_stat: int, ff_stat: int, primary: str, secondary: str):
    """A concrete post-gem stats dict for exact per-surface FG replay: PP/CM/FM at the
    head-dominance corner (max stat index) and FT/FF set to this frontier cell's stat
    indices. This is only used to produce a real `top_fg` number; the trace
    reconstruction (the phantom detector) does not depend on it."""
    from gear_optimizer.core.constants import MAX_STAT_INDEX

    stats = {
        "Perfect Points": int(MAX_STAT_INDEX),
        "Combo Multiplier": int(MAX_STAT_INDEX),
        "Fever Multiplier": int(MAX_STAT_INDEX),
        "Fever Time": int(ft_stat),
        "Fever Fill Rate": int(ff_stat),
    }
    # Colour stat values feed base_value in the exact replay; any nonzero head-dominance
    # value is fine for a sanity score. Keep them at max so top_fg is a real upper-ish FG.
    for color in {str(primary or ""), str(secondary or "")}:
        if color:
            stats[color] = int(MAX_STAT_INDEX)
    return stats


def run(song_arg: str) -> int:
    name_q, difficulty = parse_song_arg(song_arg)
    chart_path, header_name = resolve_chart_path(name_q, difficulty)
    print(f"resolved: {name_q!r} ({difficulty}) -> {header_name}")
    print(f"  chart file: {chart_path}")
    print(f"  fresh FG cache dir: {_REPRO_CACHE_DIR}")

    from gear_optimizer.solver.scoring.exact_rescore import (
        score_force_greats_response_surface_exact,
    )
    from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
    from gear_optimizer.solver.taichi_gem.force_greats import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
        all_response_stat_keys,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    calc_song = build_calc_song(chart_path)
    ref_arrays = load_ref_arrays()

    song_inputs = extract_fg_song_inputs(calc_song)
    n = int(song_inputs.total_notes)
    print(f"  note count n = {n}")
    print(
        f"  use_forced_great_timing = {bool(song_inputs.use_forced_great_timing)} "
        f"(long_notes={int(song_inputs.long_notes)})"
    )

    # FRESH build off the current working tree: clear the in-process memory cache and
    # build the full FT/FF stat grid (the same grid the production prebuild fills).
    reset_fg_response_frontier_payload_cache()
    stat_keys = all_response_stat_keys()
    print(f"  building FG response frontier for {len(stat_keys)} FT/FF stat cells ...", flush=True)
    prewarm = build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=stat_keys)
    payload = prewarm.payload
    print(
        f"  build done: cache_source={prewarm.cache_source} elapsed_ms={prewarm.elapsed_ms:.1f} "
        f"distinct_frontiers={len(payload.frontiers)} cells={len(payload.frontier_by_key)}"
    )

    raw_fill_by_ff = payload.raw_fill_by_ff
    real_time_by_ft = payload.real_time_by_ft

    # ------------------------------------------------------------------------------------
    # Reconstruction strategy (why this exact set):
    #
    # The phantom is a function ONLY of a surface's packed fields. The radix-overflow bug
    # packed (normal_great, body_fever_great) as normal_great*pair_mod + body_fever_great
    # with pair_mod sized to the section count; the alias happened exactly when
    # body_fever_great >= pair_mod, i.e. for surfaces carrying a LARGE body_fever_great.
    # So the radix bug can corrupt only high-body_fever_great surfaces, and trace
    # reconstruction is what fails on a phantom (ValueError in response_builder.py).
    #
    # MEASURED on this worst-case 3020-note song: pure-Python trace reconstruction of a
    # dense (high body_fever_great) surface costs ~1-4 s each (the recursive section DP
    # branches heavily), and there are ~7.3M distinct first-frontier surfaces -- so an
    # exhaustive reconstruction is many days and even the full high band (~17k surfaces) is
    # hours. The build/trace are CPU-only with no faster exact CPU reconstructor, so the
    # verifier reconstructs the SMALL, MOST-OVERFLOW-PRONE set that actually exercises the
    # bug, under a hard wall-clock budget so it always finishes and reports:
    #
    #   (A) TOP-BAND EXHAUSTIVE: every distinct surface in descending body_fever_great
    #       order, starting from the song max, down to whatever the budget allows. The
    #       highest body_fever_great surfaces are exactly the ones the pack could overflow,
    #       so this is the targeted radix-bug detector.
    #   (B) BREADTH SAMPLE: a small uniform random sample across all bands for coverage.
    #
    # Distinct surfaces are deduped GLOBALLY by field tuple (the phantom is
    # field-determined), each reconstructed once via a carrier frontier's axes. ANY phantom
    # in the reconstructed set fails loud. Env-tunable; on a small song set
    # REPRO_BFG_FLOOR=0, REPRO_MAX_RECON huge, REPRO_BUDGET_S huge to cover everything.
    # ------------------------------------------------------------------------------------
    import random
    import time as _time

    from gear_optimizer.core.parsing import env_int

    bfg_floor = max(0, env_int("REPRO_BFG_FLOOR", 12))        # only reconstruct surfaces with bfg >= this
    max_recon = max(1, env_int("REPRO_MAX_RECON", 1200))      # hard cap on reconstructions
    sample_breadth = max(0, env_int("REPRO_SAMPLE_BREADTH", 200))
    budget_s = max(1, env_int("REPRO_BUDGET_S", 1500))        # hard wall-clock budget for reconstruction
    top_fg_cells = max(0, env_int("REPRO_TOPFG_CELLS", 12))

    total_first_surfaces = int(sum(len(f.first_frontier) for f in payload.frontiers))
    cells_total = len(payload.frontier_by_key)

    # GLOBAL distinct-surface table: surface field tuple -> (carrier frontier, ft, ff).
    print("  indexing distinct first-frontier surfaces ...", flush=True)
    carrier: dict[tuple, tuple] = {}
    for (ft_stat, ff_stat), frontier in payload.frontier_by_key.items():
        for surface in frontier.first_frontier:
            key = tuple(int(v) for v in surface)
            if key not in carrier:
                carrier[key] = (frontier, int(ft_stat), int(ff_stat))
    distinct_total = len(carrier)
    all_keys = list(carrier.keys())
    max_bfg = max((k[10] for k in all_keys), default=0)
    print(
        f"  distinct surfaces={distinct_total} max_body_fever_great={max_bfg} "
        f"(reconstruct bfg>={bfg_floor}, top-down, cap={max_recon}, budget={budget_s}s)",
        flush=True,
    )

    # (A) phantom-target: distinct surfaces with body_fever_great >= floor, highest first.
    high_keys = sorted((k for k in all_keys if k[10] >= bfg_floor), key=lambda k: -k[10])
    # (B) breadth: small uniform sample of the rest.
    rng = random.Random(20260619)
    low_pool = [k for k in all_keys if k[10] < bfg_floor]
    breadth = rng.sample(low_pool, sample_breadth) if (sample_breadth and len(low_pool) > sample_breadth) else low_pool
    recon_keys = high_keys + list(breadth)
    if len(recon_keys) > max_recon:
        # keep all of the highest-bfg surfaces; trim from the (low-bfg) tail.
        recon_keys = recon_keys[:max_recon]
    print(
        f"  reconstructing up to {len(recon_keys)} distinct surfaces "
        f"(high-band candidates={len(high_keys)}, breadth={len(breadth)}) ...",
        flush=True,
    )

    def _surface_from_key(key: tuple):
        return FgResponseSurface(*[int(v) for v in key])

    traces_reconstructed = 0
    min_bfg_reconstructed = None
    started_recon = _time.perf_counter()
    budget_hit = False
    for idx, key in enumerate(recon_keys, start=1):
        frontier, ft_stat, ff_stat = carrier[key]
        surface = _surface_from_key(key)
        # The phantom detector: fails loud with
        # ValueError("could not reconstruct FG response surface trace") if this surface
        # aliases a phantom the build's DP edges cannot reproduce.
        trace = reconstruct_force_greats_response_trace(
            non_fever_base=int(frontier.non_fever_base),
            target_surface=surface,
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.perfect_floor,
            great_floor_timestamps=song_inputs.great_floor,
            raw_fever_fill=float(raw_fill_by_ff[int(ff_stat)]),
            real_fever_time=float(real_time_by_ft[int(ft_stat)]),
            use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
        )
        traces_reconstructed += 1
        if min_bfg_reconstructed is None or int(key[10]) < min_bfg_reconstructed:
            min_bfg_reconstructed = int(key[10])
        _ = trace  # reconstruction success is the assertion
        if idx % 100 == 0:
            elapsed = _time.perf_counter() - started_recon
            print(
                f"  ... reconstructed {idx}/{len(recon_keys)} "
                f"(elapsed {elapsed:.0f}s, current bfg={key[10]})",
                flush=True,
            )
        if (_time.perf_counter() - started_recon) > budget_s:
            budget_hit = True
            print(
                f"  [budget] stopping reconstruction after {traces_reconstructed} surfaces "
                f"({_time.perf_counter() - started_recon:.0f}s >= {budget_s}s)",
                flush=True,
            )
            break

    # top_fg: real production exact FG replay (pure CPU, no GPU) over a tiny cell sample.
    top_fg: int | None = None
    cells_scored = 0
    surfaces_scored = 0
    cell_items = list(payload.frontier_by_key.items())
    if top_fg_cells and len(cell_items) > top_fg_cells:
        step = max(1, len(cell_items) // top_fg_cells)
        topfg_items = cell_items[::step][:top_fg_cells]
    else:
        topfg_items = cell_items
    print(f"  scoring per-cell winners over {len(topfg_items)} sampled cells for top_fg ...", flush=True)
    for (ft_stat, ff_stat), frontier in topfg_items:
        cell_stats = _stats_for_cell(int(ft_stat), int(ff_stat), song_inputs.primary_color, song_inputs.secondary_color)
        for surface in frontier.first_frontier:
            score = score_force_greats_response_surface_exact(cell_stats, calc_song, ref_arrays, surface)
            surfaces_scored += 1
            if score is not None and (top_fg is None or int(score) > top_fg):
                top_fg = int(score)
        cells_scored += 1

    top_fg_str = "n/a" if top_fg is None else str(int(top_fg))
    coverage = (
        f"covered body_fever_great band [{min_bfg_reconstructed}..{max_bfg}] exhaustively"
        if not budget_hit
        else f"covered body_fever_great band [{min_bfg_reconstructed}..{max_bfg}] (budget-capped)"
    )
    print(
        f"  cells={cells_total} distinct_surfaces={distinct_total} max_body_fever_great={max_bfg} "
        f"reconstructed={traces_reconstructed} {coverage} "
        f"top_fg_cells_scored={cells_scored} top_fg_surfaces_scored={surfaces_scored}"
    )
    print(
        f"PASS: built {total_first_surfaces} surfaces, reconstructed {traces_reconstructed} traces, "
        f"top_fg={top_fg_str}  (n={n})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CPU-only FG response-frontier build + trace reconstruction repro.")
    ap.add_argument("song", help="one 'NAME|DIFFICULTY' (e.g. \"Challenge Letter|Hard\")")
    args = ap.parse_args(argv)
    try:
        return run(args.song)
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - this verifier must surface the FULL failure
        print(f"FAIL: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
