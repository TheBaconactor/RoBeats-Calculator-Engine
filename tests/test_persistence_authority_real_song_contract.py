from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gear_optimizer.gamedata import load_stat_curves
from gear_optimizer.settings import paths
from gear_optimizer.solver.song_preparation import prepare_song
from gear_optimizer.solver.timing_envelope import time_song
from gear_optimizer.helpers.song_helpers.persistence_canon import build_persistence_entries
from gear_optimizer.helpers.song_helpers.persistence_payload import make_build_details_fn
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact
from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
from tests.songs_support import make_chart


def _fixture_payload(filename: str) -> dict[str, Any]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / str(filename)
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _row_signature(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    gear = tuple(str(v) for v in (row.get("gear") or []))
    minis = tuple(str(v) for v in (row.get("minis") or []))
    return gear, minis


def _details_runtime_agnostic_view(details: Any) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {}
    out = dict(details)
    out.pop("attempt_lifetime", None)
    out.pop("attempts_first", None)
    out.pop("TimelineFrontier", None)
    out.pop("st", None)
    out.pop("gc", None)
    return out


def _assert_selected_base_timeline_frontier(details: Any) -> None:
    assert isinstance(details, dict)
    frontier = details.get("TimelineFrontier")
    assert isinstance(frontier, dict)
    assert frontier.get("activation_judgment") == "perfect"
    trace = frontier.get("frontier_trace")
    assert isinstance(trace, list) and trace
    assert all(row.get("activation_judgment") == "perfect" for row in trace)
    assert all("activation_index" in row and "activation_hit_offset_ms" in row for row in trace)


def _song_with_truncated_timeline(song):
    chart = song.chart
    ts = chart.timestamps
    if ts.size > 20:
        keep = slice(None, None, 2)
    elif ts.size > 1:
        keep = slice(None, -1)
    else:
        keep = slice(None)
    truncated = make_chart(
        ts[keep],
        note_types=chart.note_types[keep],
        lanes=chart.lanes[keep],
        name=chart.name,
        difficulty=chart.difficulty,
        primary=chart.primary,
        secondary=chart.secondary,
        long_notes=chart.long_notes,
    )
    return time_song(truncated, "perfect_window")


def test_persistence_authority_contract_real_song_be_right_there_t5_base():
    frozen = _fixture_payload("persistence_authority_be_right_there_t5.json")
    song_file = Path(__file__).resolve().parents[1] / str(frozen["song_file_rel"])
    assert song_file.exists(), f"Missing frozen chart fixture: {song_file}"

    song = prepare_song(str(song_file))
    curves = load_stat_curves(paths().stats_txt)
    build_or_load_timeline_frontier_payload(song, curves)
    build_details_fn = make_build_details_fn(
        str(frozen["primary_color"]),
        str(frozen["secondary_color"]),
        str(frozen["difficulty"]),
    )

    base_entry = dict(frozen["base_entry"])
    stale_score = int(base_entry["expected_score"]) + 55555
    db_payload = {
        "score": stale_score,
        "fg_score": 0,
        "gear": list(base_entry["gear"]),
        "minis": list(base_entry["minis"]),
        "details": dict(base_entry["details"]),
        "force": None,
    }
    persist_entries = build_persistence_entries(
        db_payload,
        ga_candidates=[],
        loadout_entries=None,
        build_details_fn=build_details_fn,
        song=song,
        curves=curves,
    )

    rows_by_signature = {_row_signature(row): row for row in persist_entries if isinstance(row, dict)}
    base_sig = (tuple(str(v) for v in base_entry["gear"]), tuple(str(v) for v in base_entry["minis"]))
    assert base_sig in rows_by_signature

    row = rows_by_signature[base_sig]
    _assert_selected_base_timeline_frontier(row.get("details") or {})
    details_actual = _details_runtime_agnostic_view(row.get("details") or {})
    details_expected = _details_runtime_agnostic_view(base_entry["details"])
    assert details_actual == details_expected
    stats = dict((details_actual.get("Stats") or {}))
    assert stats == dict(details_expected["Stats"])
    exact = int(score_stats_exact(stats, song, curves))
    authority_score = 47192170
    assert int(row["score"]) == exact == int(base_entry["expected_score"]) == authority_score
    assert int(row["score"]) != stale_score
    assert int(row.get("fg_score") or 0) == 0
    assert row.get("force") is None

    gem_counts = dict(details_actual.get("GemCounts") or {})
    assert int(gem_counts.get("Fever Multiplier", 0)) == 13
    assert int(gem_counts.get("Element", 0)) == 64
    assert int(details_actual.get("FF", 0)) == 13

    wrong_timeline_song = _song_with_truncated_timeline(song)
    build_or_load_timeline_frontier_payload(wrong_timeline_song, curves)
    wrong_timeline_score = int(score_stats_exact(stats, wrong_timeline_song, curves))
    assert wrong_timeline_score <= authority_score
