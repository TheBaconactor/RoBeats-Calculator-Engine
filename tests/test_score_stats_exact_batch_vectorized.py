"""Bit-exactness guardian for the vectorized ``score_stats_exact_batch``.

The batch scorer collapses rows on the derived key (curve plateaus,
color-line equivalence) and replays each (FT, FF) frontier cell once,
vectorized over rows and pool lanes. Its contract is BIT-IDENTITY with the
per-row frontier replay (``_score_timeline_frontier_payload_vectorized``,
still the trace path's engine) -- the exact scorer is the persistence /
replay authority, so any drift here is data corruption, not a perf bug.

Covers: curve-plateau boundaries, clamp edges (0/159/160/beyond-table),
empty rows, color-heavy rows, single- and mixed-cell batches, and
permutation/duplication invariance of the batch collapse.
"""
from __future__ import annotations

import random
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHART = REPO_ROOT / "Data" / "Easy" / "LOVERS' OASIS (Easy) by dark cat.txt"

pytestmark = pytest.mark.skipif(
    not CHART.is_file(), reason="fixture chart not present"
)


@pytest.fixture(scope="module")
def song_ctx():
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.scoring import exact_rescore as er
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        load_timeline_frontier_payload,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    base = get_base_calc_song(str(CHART), {"IterationEngine": {}})
    assert base, f"failed to load chart {CHART}"
    calc_song = clone_calc_song(base)
    apply_timing_envelope(calc_song, mode="perfect_window")
    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert isinstance(ref_arrays, dict) and ref_arrays
    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)

    frontier_refs = er._frontier_replay_refs(ref_arrays)
    payload = load_timeline_frontier_payload(calc_song, frontier_refs).payload
    meta = er.extract_song_meta(calc_song)
    song_data = calc_song.get("song_data", {}) or {}
    ts = song_data.get("chart_timestamps")
    if ts is None:
        ts = song_data.get("timestamps", ())
    return {
        "calc_song": calc_song,
        "ref_arrays": ref_arrays,
        "frontier_refs": frontier_refs,
        "payload": payload,
        "meta": meta,
        "total_notes": int(len(ts)),
    }


def _reference_score(ctx, stats: dict) -> int:
    from gear_optimizer.solver.scoring import exact_rescore as er

    (pv, sv, ppf, cmf, fmf, ft, ff) = er._score_stat_inputs(
        stats, ctx["frontier_refs"], ctx["meta"].primary_color, ctx["meta"].secondary_color
    )
    return int(
        er._score_timeline_frontier_payload_vectorized(
            payload=ctx["payload"],
            total_notes=ctx["total_notes"],
            primary_val=pv,
            secondary_val=sv,
            pp_factor=ppf,
            combo_mul=cmf,
            fever_mul=fmf,
            ft_idx=ft,
            ff_idx=ff,
        )
    )


def _stat_rows(meta) -> list[dict]:
    rng = random.Random(1337)
    rows: list[dict] = [{}]
    rows.append({"Perfect Points": 160, "Combo Multiplier": 160, "Fever Multiplier": 160,
                 "Fever Time": 160, "Fever Fill Rate": 160, meta.primary_color: 250})
    rows.append({"Perfect Points": 500, "Combo Multiplier": 999, "Fever Time": 400})
    rows.append({meta.primary_color: 61})
    if meta.secondary_color:
        rows.append({meta.secondary_color: 87, "Fever Multiplier": 3})
    for s in (0, 1, 79, 80, 81, 119, 120, 121, 159, 160):
        rows.append({"Perfect Points": s, "Combo Multiplier": 160 - s,
                     "Fever Multiplier": s, "Fever Time": (s * 3) % 161,
                     "Fever Fill Rate": (161 - s) % 161, meta.primary_color: s % 40})
    for _ in range(800):
        r = {
            "Perfect Points": rng.randint(0, 170),
            "Combo Multiplier": rng.randint(0, 170),
            "Fever Multiplier": rng.randint(0, 170),
            "Fever Time": rng.randint(0, 170),
            "Fever Fill Rate": rng.randint(0, 170),
            meta.primary_color: rng.randint(0, 200),
        }
        if meta.secondary_color:
            r[meta.secondary_color] = rng.randint(0, 200)
        if rng.random() < 0.2:
            r.pop("Perfect Points")
        rows.append(r)
    return rows


def test_batch_scorer_bit_identical_to_per_row_replay(song_ctx):
    from gear_optimizer.solver.scoring import exact_rescore as er

    rows = _stat_rows(song_ctx["meta"])
    got = er.score_stats_exact_batch(rows, song_ctx["calc_song"], song_ctx["ref_arrays"])
    assert len(got) == len(rows)
    for i, stats in enumerate(rows):
        assert int(got[i]) == _reference_score(song_ctx, stats), (
            f"row {i} diverged: {stats}"
        )


def test_batch_collapse_is_order_and_duplication_invariant(song_ctx):
    from gear_optimizer.solver.scoring import exact_rescore as er

    rows = _stat_rows(song_ctx["meta"])[:200]
    base = er.score_stats_exact_batch(rows, song_ctx["calc_song"], song_ctx["ref_arrays"])
    shuffled_idx = list(range(len(rows)))
    random.Random(7).shuffle(shuffled_idx)
    shuffled = [rows[i] for i in shuffled_idx]
    got = er.score_stats_exact_batch(shuffled, song_ctx["calc_song"], song_ctx["ref_arrays"])
    for pos, i in enumerate(shuffled_idx):
        assert got[pos] == base[i]
    tripled = rows + rows + rows
    got3 = er.score_stats_exact_batch(tripled, song_ctx["calc_song"], song_ctx["ref_arrays"])
    assert got3 == base * 3
