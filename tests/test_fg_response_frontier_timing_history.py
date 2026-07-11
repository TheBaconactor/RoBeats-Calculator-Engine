from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from gear_optimizer.solver.fg_response_frontier_timing_history import (
    FgPrebuildChart,
    FgPrebuildTimingContext,
    load_fg_prebuild_timing_history,
    predict_fg_prebuild_duration,
    update_fg_prebuild_timing_history,
)


def _chart(digest: str = "chart", notes: int = 1000) -> FgPrebuildChart:
    return FgPrebuildChart(
        path=f"{digest}.txt",
        digest=digest,
        note_count=notes,
        long_notes=notes // 5,
        duration_sec=float(notes) / 6.0,
    )


def _context(**changes) -> FgPrebuildTimingContext:
    values = {
        "algorithm_version": "v1+logic-a",
        "cpu_identity": "cpu-a",
        "reducer_threads": 4,
        "ref_signature": "ref-a",
        "stat_signature": "stats-a",
        "frontier_cpus": 31,
    }
    values.update(changes)
    return FgPrebuildTimingContext(**values)


def _record(chart: FgPrebuildChart, context: FgPrebuildTimingContext, **changes):
    record = {
        **asdict(context),
        "chart_digest": chart.digest,
        "note_count": chart.note_count,
        "long_notes": chart.long_notes,
        "chart_duration_sec": chart.duration_sec,
        "duration_ms": 1000.0,
        "completed_at": 1.0,
    }
    record.update(changes)
    return record


def test_fg_prebuild_prediction_uses_latest_exact_compatible_duration() -> None:
    chart = _chart()
    context = _context()
    records = [
        _record(chart, context, duration_ms=1200.0, completed_at=2.0),
        _record(chart, context, duration_ms=900.0, completed_at=1.0),
        _record(chart, _context(reducer_threads=2), duration_ms=99999.0, completed_at=3.0),
        _record(chart, _context(algorithm_version="v2"), duration_ms=99999.0, completed_at=4.0),
    ]

    prediction = predict_fg_prebuild_duration(chart, context, records)

    assert prediction.source == "history"
    assert prediction.duration_ms == 1200.0


def test_fg_prebuild_prediction_uses_structural_history_then_note_count() -> None:
    context = _context()
    records = [
        _record(_chart(f"near-{index}", 900 + 50 * index), context, duration_ms=2000.0 + 100 * index)
        for index in range(3)
    ]

    structural = predict_fg_prebuild_duration(_chart("new", 1100), context, records)
    notes = predict_fg_prebuild_duration(_chart("new", 1100), _context(cpu_identity="cpu-b"), records)

    assert structural.source == "structure"
    assert structural.duration_ms > 0.0
    assert notes.source == "notes"
    assert notes.duration_ms == 1100.0


@pytest.mark.parametrize("contents", ["not json", "[]", '{"schema_version": 1, "records": {}}'])
def test_fg_prebuild_timing_history_missing_or_corrupt_is_optional_boundary(
    tmp_path, contents: str
) -> None:
    path = tmp_path / "timing.json"
    assert load_fg_prebuild_timing_history(path) == []
    path.write_text(contents, encoding="utf-8")
    assert load_fg_prebuild_timing_history(path) == []


def test_fg_prebuild_timing_history_updates_atomically_and_replaces_compatible_key(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "timing.json"
    chart = _chart()
    context = _context()
    monkeypatch.setattr(
        "gear_optimizer.solver.fg_response_frontier_timing_history.time.time", lambda: 123.0
    )

    records = update_fg_prebuild_timing_history(
        path, [], chart=chart, context=context, duration_ms=1000.0
    )
    records = update_fg_prebuild_timing_history(
        path, records, chart=chart, context=context, duration_ms=800.0
    )

    assert len(records) == 1
    assert records[0]["duration_ms"] == 800.0
    assert load_fg_prebuild_timing_history(path) == records
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert list(tmp_path.glob("*.tmp")) == []


def test_fg_prebuild_timing_history_does_not_rotate_frontier_fingerprint() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_types

    source_names = {source.name for source in response_cache_types._FG_DP_SOURCES}
    assert "fg_response_frontier_cache_prebuild.py" not in source_names
    assert "fg_response_frontier_timing_history.py" not in source_names
    assert (
        response_cache_types._FG_RESPONSE_CACHE_VERSION
        == "fg-response-frontier-visible-first-v29+logic-91c317d47ec4"
    )
