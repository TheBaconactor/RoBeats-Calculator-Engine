"""Bit-exactness guardian for the IR-backed ``score_stats_exact_batch``.

The batch scorer collapses rows on the derived key (curve plateaus,
color-line equivalence) and replays each (FT, FF) frontier cell once,
vectorized over rows and pool lanes. Its contract is BIT-IDENTITY with the
per-row frontier replay (``_score_timeline_frontier_payload_vectorized``,
still the trace path's engine) -- the exact scorer is the persistence /
replay authority, so any drift here is data corruption, not a perf bug.

Covers: curve-plateau boundaries, clamp edges (0/159/160/beyond-table),
empty rows, color-heavy rows, single- and mixed-cell batches,
permutation/duplication invariance of the batch collapse, two-color collapse
parity (handoff §5.B ship gate), base_int monotonicity sweep, and the f64
envelope guard.
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
# The primary guardian chart (used for the ported v1 parity suite).
CHART = REPO_ROOT / "Data" / "Easy" / "LOVERS' OASIS (Easy) by dark cat.txt"
# A chart with DISTINCT primary/secondary colors, required to exercise the
# v = 2*c1 + c2 collapse (when primary == secondary, both stat keys alias the
# same dict entry and the collapse is not independently controllable).
CHART_DISTINCT_COLORS = (
    REPO_ROOT / "Data" / "Easy" / "AI Bomb on vocal (revision 2) (Easy) by naruto2413 (feat Aya Majiro).txt"
)

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
    ir = er.build_exact_score_ir(calc_song, frontier_refs)
    return {
        "calc_song": calc_song,
        "ref_arrays": ref_arrays,
        "frontier_refs": frontier_refs,
        "payload": payload,
        "meta": meta,
        "total_notes": int(len(ts)),
        "ir": ir,
    }


@pytest.fixture(scope="module")
def distinct_color_ctx():
    """A second chart context with primary != secondary, for the collapse parity gate."""
    if not CHART_DISTINCT_COLORS.is_file():
        pytest.skip("distinct-color fixture chart not present")
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.scoring import exact_rescore as er
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        load_timeline_frontier_payload,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    base = get_base_calc_song(str(CHART_DISTINCT_COLORS), {"IterationEngine": {}})
    assert base, f"failed to load chart {CHART_DISTINCT_COLORS}"
    calc_song = clone_calc_song(base)
    apply_timing_envelope(calc_song, mode="perfect_window")
    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert isinstance(ref_arrays, dict) and ref_arrays
    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)

    frontier_refs = er._frontier_replay_refs(ref_arrays)
    payload = load_timeline_frontier_payload(calc_song, frontier_refs).payload
    meta = er.extract_song_meta(calc_song)
    assert meta.primary_color != meta.secondary_color, (
        "distinct-color fixture must have primary != secondary"
    )
    song_data = calc_song.get("song_data", {}) or {}
    ts = song_data.get("chart_timestamps")
    if ts is None:
        ts = song_data.get("timestamps", ())
    ir = er.build_exact_score_ir(calc_song, frontier_refs)
    return {
        "calc_song": calc_song,
        "ref_arrays": ref_arrays,
        "frontier_refs": frontier_refs,
        "payload": payload,
        "meta": meta,
        "total_notes": int(len(ts)),
        "ir": ir,
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


def _rows_to_arrays(rows: list[dict], meta) -> dict[str, np.ndarray]:
    n = len(rows)
    out = {
        "primary_val": np.zeros(n, dtype=np.int64),
        "secondary_val": np.zeros(n, dtype=np.int64),
        "pp_stat": np.zeros(n, dtype=np.int64),
        "cm_stat": np.zeros(n, dtype=np.int64),
        "fm_stat": np.zeros(n, dtype=np.int64),
        "ft_stat": np.zeros(n, dtype=np.int64),
        "ff_stat": np.zeros(n, dtype=np.int64),
    }
    for i, stats in enumerate(rows):
        out["primary_val"][i] = int(stats.get(meta.primary_color, 0) or 0)
        out["secondary_val"][i] = int(stats.get(meta.secondary_color, 0) or 0)
        out["pp_stat"][i] = int(stats.get("Perfect Points", 0) or 0)
        out["cm_stat"][i] = int(stats.get("Combo Multiplier", 0) or 0)
        out["fm_stat"][i] = int(stats.get("Fever Multiplier", 0) or 0)
        out["ft_stat"][i] = int(stats.get("Fever Time", 0) or 0)
        out["ff_stat"][i] = int(stats.get("Fever Fill Rate", 0) or 0)
    return out


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


def test_score_stat_arrays_exact_batch_matches_dict_batch(song_ctx):
    """The array-native adapter must match the dict-driven batch scorer bit-for-bit."""
    from gear_optimizer.solver.scoring import exact_rescore as er

    rows = _stat_rows(song_ctx["meta"])
    expected = er.score_stats_exact_batch(rows, song_ctx["calc_song"], song_ctx["ref_arrays"])
    arrs = _rows_to_arrays(rows, song_ctx["meta"])
    got = er.score_stat_arrays_exact_batch(
        arrs["primary_val"], arrs["secondary_val"],
        arrs["pp_stat"], arrs["cm_stat"], arrs["fm_stat"],
        arrs["ft_stat"], arrs["ff_stat"],
        song_ctx["calc_song"], song_ctx["ref_arrays"],
    )
    assert got.dtype == np.int64
    assert got.tolist() == list(expected)


def test_score_from_ir_matches_per_row_replay(song_ctx):
    """Direct IR entry matches the per-row scalar replay for every row."""
    from gear_optimizer.solver.scoring import exact_rescore as er

    rows = _stat_rows(song_ctx["meta"])
    arrs = _rows_to_arrays(rows, song_ctx["meta"])
    got = er.score_from_ir(
        song_ctx["ir"],
        arrs["primary_val"], arrs["secondary_val"],
        arrs["pp_stat"], arrs["cm_stat"], arrs["fm_stat"],
        arrs["ft_stat"], arrs["ff_stat"],
    )
    for i, stats in enumerate(rows):
        assert int(got[i]) == _reference_score(song_ctx, stats), (
            f"row {i} diverged via IR: {stats}"
        )


def test_score_from_ir_with_pool_idx_matches_vectorized_result(song_ctx):
    """The pool-idx twin must return the same (score, pool_idx) as the legacy result fn."""
    from gear_optimizer.solver.scoring import exact_rescore as er

    rows = _stat_rows(song_ctx["meta"])[:50]
    for stats in rows:
        (pv, sv, ppf, cmf, fmf, ft, ff) = er._score_stat_inputs(
            stats, song_ctx["frontier_refs"],
            song_ctx["meta"].primary_color, song_ctx["meta"].secondary_color,
        )
        expected_score, expected_pool = er._score_timeline_frontier_payload_vectorized_result(
            payload=song_ctx["payload"],
            total_notes=song_ctx["total_notes"],
            primary_val=pv, secondary_val=sv,
            pp_factor=ppf, combo_mul=cmf, fever_mul=fmf,
            ft_idx=ft, ff_idx=ff,
        )
        got_score, got_pool = er.score_from_ir_with_pool_idx(
            song_ctx["ir"],
            primary_val=int(pv), secondary_val=int(sv),
            pp_factor=float(ppf), combo_mul=float(cmf), fever_mul=float(fmf),
            ft_idx=int(ft), ff_idx=int(ff),
        )
        assert int(got_score) == int(expected_score), (
            f"score mismatch for {stats}: {got_score} != {expected_score}"
        )
        assert int(got_pool) == int(expected_pool), (
            f"pool idx mismatch for {stats}: {got_pool} != {expected_pool}"
        )


def test_two_color_collapse_parity(distinct_color_ctx):
    """Handoff §5.B ship gate: rows with the same 2*c1+c2 collapse bit-identically.

    The scorer's base_int = 2*primary + secondary is the only entry the color
    stats have into base_value, so any (c1, c2) pair with the same collapse
    must score identically when all other stats match. Requires a chart whose
    primary and secondary color names differ (otherwise both stat keys alias
    the same dict entry and the collapse is not independently controllable).
    """
    from gear_optimizer.solver.scoring import exact_rescore as er

    meta = distinct_color_ctx["meta"]
    # Pick a target collapse value reachable by multiple (c1, c2) pairs in stat range.
    target_v = 200
    pairs = []
    for c1 in range(0, 251):
        c2 = target_v - 2 * c1
        if 0 <= c2 <= 250:
            pairs.append((c1, c2))
    assert len(pairs) >= 2, "collapse parity test needs >=2 reachable pairs"
    base_stats = {
        "Perfect Points": 80,
        "Combo Multiplier": 120,
        "Fever Multiplier": 100,
        "Fever Time": 60,
        "Fever Fill Rate": 90,
    }
    rows = []
    for c1, c2 in pairs:
        r = dict(base_stats)
        r[meta.primary_color] = c1
        r[meta.secondary_color] = c2
        rows.append(r)
    scores = er.score_stats_exact_batch(rows, distinct_color_ctx["calc_song"], distinct_color_ctx["ref_arrays"])
    first = int(scores[0])
    for i, (c1, c2) in enumerate(pairs):
        assert int(scores[i]) == first, (
            f"collapse parity broken for (c1={c1}, c2={c2}) -> v={target_v}: "
            f"score {scores[i]} != {first}"
        )


def test_base_int_monotonicity_sweep(distinct_color_ctx):
    """Scores are non-decreasing in base_int across the feasible range, fixed surface.

    Holding the (FT, FF) cell and the PP/CM/FM plateaus fixed, increasing the
    color-collapse value must not decrease the score -- the per-lane floor
    expressions are monotone in base_value, and the max over pool lanes
    preserves that. Requires a chart with distinct primary/secondary colors.
    """
    from gear_optimizer.solver.scoring import exact_rescore as er

    meta = distinct_color_ctx["meta"]
    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 130,
        "Fever Multiplier": 110,
        "Fever Time": 50,
        "Fever Fill Rate": 70,
    }
    base_ints = list(range(0, 501, 25))
    rows = []
    for v in base_ints:
        c1 = v // 2
        c2 = v - 2 * c1
        if c2 < 0:
            c1 -= 1
            c2 = v - 2 * c1
        if c1 > 250:
            c1 = 250
            c2 = max(0, v - 2 * c1)
        r = dict(base_stats)
        r[meta.primary_color] = c1
        r[meta.secondary_color] = c2
        rows.append(r)
    scores = er.score_stats_exact_batch(rows, distinct_color_ctx["calc_song"], distinct_color_ctx["ref_arrays"])
    for i in range(1, len(scores)):
        assert int(scores[i]) >= int(scores[i - 1]), (
            f"monotonicity broken at base_int={base_ints[i]}: "
            f"{scores[i]} < {scores[i - 1]}"
        )


def test_f64_envelope_guard_raises(song_ctx):
    """A row whose body_total * max(fever_val) approaches 2^52 raises loudly.

    The exactness argument for the f64 pool reduction requires magnitudes stay
    below 2^52; the IR replay enforces this with a loud ValueError. We trigger
    it by lowering the IR's f64_envelope_guard to 1 so any nonzero replay
    magnitude trips the guard (the body-count invariant still passes because
    body_total is unchanged). Production charts never approach 2^52; this test
    pins the guard exists and fails loud.
    """
    from dataclasses import replace

    from gear_optimizer.solver.scoring import exact_rescore as er

    ir = song_ctx["ir"]
    tiny_ir = replace(ir, f64_envelope_guard=1)
    arrs = _rows_to_arrays(
        [{"Perfect Points": 160, "Combo Multiplier": 160, "Fever Multiplier": 160,
          "Fever Time": 160, "Fever Fill Rate": 160, song_ctx["meta"].primary_color: 250}],
        song_ctx["meta"],
    )
    with pytest.raises(ValueError, match="f64 envelope"):
        er.score_from_ir(
            tiny_ir,
            arrs["primary_val"], arrs["secondary_val"],
            arrs["pp_stat"], arrs["cm_stat"], arrs["fm_stat"],
            arrs["ft_stat"], arrs["ff_stat"],
        )


def test_ir_cache_key_is_well_formed(song_ctx):
    """The cache_key tuple has the 4 documented components."""
    ir = song_ctx["ir"]
    assert isinstance(ir.cache_key, tuple)
    assert len(ir.cache_key) == 4
    frontier_cache_key, ref_content_hash, timing_mode, ir_schema_version = ir.cache_key
    assert isinstance(frontier_cache_key, tuple)
    assert isinstance(ref_content_hash, tuple)
    assert timing_mode in {"perfect_window", "zero_ms"}
    assert isinstance(ir_schema_version, int) and ir_schema_version >= 1


def test_ir_is_immutable(song_ctx):
    """The IR dataclass is frozen -- field mutation raises."""
    ir = song_ctx["ir"]
    with pytest.raises((AttributeError, Exception)):
        ir.total_notes = 999  # type: ignore[misc]


def test_ir_plateau_inverse_is_canonical(song_ctx):
    """np.unique on the PP/CM/FM tables reproduces the IR's plateau fields."""
    ir = song_ctx["ir"]
    from gear_optimizer.core.constants import TOTAL_ROWS

    pp_vals, pp_inv = np.unique(ir.pp_table[: TOTAL_ROWS + 1], return_inverse=True)
    cm_vals, cm_inv = np.unique(ir.cm_table[: TOTAL_ROWS + 1], return_inverse=True)
    fm_vals, fm_inv = np.unique(ir.fm_table[: TOTAL_ROWS + 1], return_inverse=True)
    np.testing.assert_array_equal(pp_vals, ir.pp_plateau_values)
    np.testing.assert_array_equal(pp_inv, ir.pp_plateau_inverse)
    np.testing.assert_array_equal(cm_vals, ir.cm_plateau_values)
    np.testing.assert_array_equal(cm_inv, ir.cm_plateau_inverse)
    np.testing.assert_array_equal(fm_vals, ir.fm_plateau_values)
    np.testing.assert_array_equal(fm_inv, ir.fm_plateau_inverse)
