"""Fixed-timing (0ms) replay mode: CPU-side mode prep + base scorer (issue #51).

These tests pin the parts that need no GPU: that `apply_timing_envelope(mode="zero_ms")`
produces a chart-only, mode-stamped calc_song whose cache signatures are disjoint from the
Perfect-window path, and that `score_stats_fixed_timing_exact[_batch]` is the deterministic
chart-time fever timeline (independent of any timing frontier payload).
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.scoring.stats_scoring import _song_cache_key_for_fg_timeline
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.solver.scoring.exact_rescore import (
    calculate_score_exact,
    score_stats_exact_batch,
    score_stats_fixed_timing_exact,
    score_stats_fixed_timing_exact_batch,
)
from gear_optimizer.solver.score_math import lookup_reference_py
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


def _ref_arrays() -> dict[str, np.ndarray]:
    rows = TOTAL_ROWS + 1
    return {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 4.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.3, 1.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(0.3, 1.0, rows, dtype=np.float64),
    }


def _calc_song() -> dict:
    timestamps = np.round(np.arange(250, dtype=np.float32) * np.float32(0.1), 3).astype(np.float32)
    return {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
        },
    }


def _stats() -> dict[str, int]:
    return {
        "Perfect Points": 40,
        "Combo Multiplier": 55,
        "Fever Multiplier": 30,
        "Fever Time": 70,
        "Fever Fill Rate": 90,
        "Rush": 20,
        "Flow": 10,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }


def test_zero_ms_mode_prepares_chart_only_streams_and_stamp():
    cs = _calc_song()
    info = apply_timing_envelope(cs, mode="zero_ms")

    assert info["timing_mode"] == "zero_ms"
    assert cs["metadata"]["TimingEnvelopeApplied"] is True
    assert cs["metadata"]["TimingEnvelopeMode"] == "zero_ms"


def test_chart_metadata_selects_zero_ms_when_mode_is_omitted():
    cs = _calc_song()
    cs["metadata"]["Timing Mode"] = "zero_ms"

    info = apply_timing_envelope(cs)

    assert info["timing_mode"] == "zero_ms"
    assert cs["metadata"]["TimingEnvelopeMode"] == "zero_ms"
    # No Perfect-window envelope streams: the FG build uses the chart fallback.
    for stream in (
        "fg_perfect_candidate_timestamps",
        "fg_perfect_floor_timestamps",
        "fg_great_floor_timestamps",
        "fg_great_candidate_timestamps",
    ):
        assert stream not in cs["song_data"]
    # Base chart timestamps are preserved for the fixed timeline.
    assert "chart_timestamps" in cs["song_data"]


def test_perfect_window_mode_attaches_envelope_streams():
    cs = _calc_song()
    apply_timing_envelope(cs, mode="perfect_window")

    assert cs["metadata"]["TimingEnvelopeMode"] == "perfect_window"
    assert "fg_perfect_candidate_timestamps" in cs["song_data"]
    assert "fg_great_candidate_timestamps" in cs["song_data"]


def test_perfect_window_timeline_repairs_incomplete_canonical_envelope():
    from gear_optimizer.solver.taichi_gem.api import timeline

    cs = _calc_song()
    note_count = len(cs["song_data"]["timestamps"])
    cs["song_data"]["note_types"] = np.ones(note_count, dtype=np.int16)
    cs["song_data"]["lanes"] = np.arange(note_count, dtype=np.int32) % 4
    apply_timing_envelope(cs, mode="perfect_window")
    del cs["song_data"]["fg_perfect_candidate_timestamps"]

    loaded = timeline.load_timeline_frontier_payload(cs, _ref_arrays())

    assert loaded.total_notes == note_count
    assert len(cs["song_data"]["fg_perfect_candidate_timestamps"]) == note_count


def test_zero_ms_and_perfect_window_signatures_are_disjoint():
    cs_zero = _calc_song()
    cs_pw = _calc_song()
    apply_timing_envelope(cs_zero, mode="zero_ms")
    apply_timing_envelope(cs_pw, mode="perfect_window")

    sig_zero = _song_cache_key_for_fg_timeline(cs_zero)
    sig_pw = _song_cache_key_for_fg_timeline(cs_pw)
    assert sig_zero != sig_pw


def test_unknown_mode_fails_loudly():
    import pytest

    with pytest.raises(ValueError, match="unknown timing mode"):
        apply_timing_envelope(_calc_song(), mode="bogus")


def test_fixed_timing_base_scorer_matches_fixed_value_primitive():
    """The stats->score adapter equals an independent chart-time fixed-timeline replay.

    The reference re-derives the deterministic chart-time fever timeline
    (``calculate_fever_timeline_indices``) and scores it with the f64 primitive
    (``calculate_score_exact``) -- the same math the adapter performs, computed here
    independently from resolved factors.
    """
    stats = _stats()
    cs = _calc_song()
    ref = _ref_arrays()

    pp = lookup_reference_py(stats["Perfect Points"], ref["Perfect Points"], TOTAL_ROWS)
    combo = lookup_reference_py(stats["Combo Multiplier"], ref["Combo Multiplier"], TOTAL_ROWS)
    fever = lookup_reference_py(stats["Fever Multiplier"], ref["Fever Multiplier"], TOTAL_ROWS)
    ft_factor = lookup_reference_py(stats["Fever Time"], ref["Fever Time"], TOTAL_ROWS)
    ff_factor = lookup_reference_py(stats["Fever Fill Rate"], ref["Fever Fill Rate"], TOTAL_ROWS)
    base_value = float(stats["Rush"] * 2 + stats["Flow"]) + float(pp)

    timestamps = cs["song_data"]["timestamps"]
    total_notes = int(len(timestamps))
    mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    fever_mask_head, count_body_fever, count_body_normal, _non_fever, _acts = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        float(ff_factor),
        float(ft_factor),
        int(cs["metadata"]["Long Notes"]),
        float(cs["metadata"]["Last Note Time"]),
        mask_buffer,
    )
    reference = calculate_score_exact(
        base_value,
        float(combo),
        float(fever),
        fever_mask_head,
        int(count_body_fever),
        int(count_body_normal),
    )

    got = score_stats_fixed_timing_exact(stats, cs, ref)
    assert got == reference
    assert got > 0  # the synthetic song exercises a real fever timeline + body notes


def test_fixed_timing_base_scorer_is_mode_prep_invariant():
    """Base 0ms scoring reads chart timestamps only; the mode stamp does not change it."""
    stats = _stats()
    ref = _ref_arrays()
    raw = _calc_song()
    enveloped = _calc_song()
    apply_timing_envelope(enveloped, mode="zero_ms")

    assert score_stats_fixed_timing_exact(stats, enveloped, ref) == score_stats_fixed_timing_exact(
        stats, raw, ref
    )


def test_fixed_timing_base_scorer_batch_matches_single():
    stats_rows = [_stats(), {**_stats(), "Fever Time": 5, "Fever Fill Rate": 5}]
    cs = _calc_song()
    ref = _ref_arrays()

    batch = score_stats_fixed_timing_exact_batch(stats_rows, cs, ref)
    singles = [score_stats_fixed_timing_exact(s, cs, ref) for s in stats_rows]
    assert batch == singles
    assert batch[0] != batch[1]  # different FT/FF -> different fixed timeline


def test_zero_ms_singleton_payload_matches_fixed_timing_scorer_without_disk_cache(tmp_path, monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import timeline

    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    timeline.reset_timeline_state()
    cs = _calc_song()
    apply_timing_envelope(cs, mode="zero_ms")
    ref = _ref_arrays()
    stats_rows = [
        _stats(),
        {**_stats(), "Fever Time": 0, "Fever Fill Rate": 0},
        {**_stats(), "Fever Time": TOTAL_ROWS, "Fever Fill Rate": TOTAL_ROWS},
        {**_stats(), "Fever Time": 17, "Fever Fill Rate": 143, "Combo Multiplier": 160},
    ]

    loaded = timeline.load_timeline_frontier_payload(cs, ref)

    assert loaded.cache_source == "fixed_zero_ms"
    assert loaded.payload.frontier_pool_used > 0
    assert np.all(loaded.payload.grid_frontier_count == 1)
    assert list(tmp_path.glob("*.npz")) == []
    assert score_stats_exact_batch(stats_rows, cs, ref) == score_stats_fixed_timing_exact_batch(
        stats_rows, cs, ref
    )

    uploads: list[tuple[int, int]] = []
    monkeypatch.setattr(timeline, "ensure_ready", lambda *_args, **_kwargs: b"")
    monkeypatch.setattr(timeline, "_maybe_sync", lambda **_kwargs: None)
    monkeypatch.setattr(timeline, "_emit_timeline_phase", lambda **_kwargs: None)
    monkeypatch.setattr(
        timeline,
        "_upload_timeline_frontier_payload_slot",
        lambda _payload, song_slot, *, source_slot_i: uploads.append((song_slot, source_slot_i)) or 0,
    )

    timeline.precompute_timeline_gpu(cs, ref, song_slot=0, prebuilt_frontier=loaded)

    assert uploads == [(0, 0)]


def test_fixed_timing_fg_ensures_and_loads_only_exactly_reachable_cells(monkeypatch):
    from gear_optimizer.solver import fg_response_frontier_cache_prebuild
    from gear_optimizer.solver.fg_response_scoring import fixed_timing
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache, response_frontier

    seen: dict[str, object] = {}
    bundle = object()

    def _ensure(calc_song, ref_arrays, *, stat_keys):
        seen["ensure"] = tuple(stat_keys)

    def _load(calc_song, ref_arrays, *, stat_keys):
        seen["load"] = tuple(stat_keys)
        return bundle

    def _prepare(**kwargs):
        seen["prepare_bundle"] = kwargs["scoring_bundle"]
        return object()

    monkeypatch.setattr(
        fg_response_frontier_cache_prebuild,
        "ensure_response_frontier_cache_for_calc_song",
        _ensure,
    )
    monkeypatch.setattr(response_cache, "load_response_frontier_scoring_bundle", _load)
    monkeypatch.setattr(response_frontier, "prepare_force_greats_response_frontier_scoring_batch", _prepare)
    monkeypatch.setattr(
        response_frontier,
        "score_prepared_force_greats_response_frontier_batch_cpu_sync",
        lambda *_args, **_kwargs: [SimpleNamespace(surface="exact-surface")],
    )

    surfaces = fixed_timing.build_fixed_timing_response_surfaces(
        [_stats()],
        _calc_song(),
        _ref_arrays(),
        "Rush",
    )

    assert surfaces == ["exact-surface"]
    assert seen == {
        "ensure": ((70, 90),),
        "load": ((70, 90),),
        "prepare_bundle": bundle,
    }
