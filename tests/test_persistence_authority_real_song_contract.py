from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.song_helpers.persistence_canon import build_persistence_entries
from gear_optimizer.helpers.song_helpers.persistence_payload import make_build_details_fn
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact
from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload


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


def _prebuild_timeline_frontier(calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> None:
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    apply_timing_envelope(calc_song, mode="perfect_window")
    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)


def _calc_song_with_truncated_timeline(calc_song: dict[str, Any]) -> dict[str, Any]:
    meta = dict(calc_song.get("metadata") or {})
    song_data_src = dict(calc_song.get("song_data") or {})
    song_data = dict(song_data_src)

    ts = np.asarray(song_data_src.get("timestamps"), dtype=np.float32)
    if ts.size > 20:
        ts_bad = np.asarray(ts[::2], dtype=np.float32)
    elif ts.size > 1:
        ts_bad = np.asarray(ts[:-1], dtype=np.float32)
    else:
        ts_bad = np.asarray(ts, dtype=np.float32)

    song_data["timestamps"] = ts_bad
    song_data["chart_timestamps"] = ts_bad
    note_types = song_data_src.get("note_types")
    if note_types is not None:
        song_data["note_types"] = np.asarray(note_types, dtype=np.int16)[: ts_bad.shape[0]]
    lanes = song_data_src.get("lanes")
    if lanes is not None:
        song_data["lanes"] = np.asarray(lanes, dtype=np.int32)[: ts_bad.shape[0]]

    if ts_bad.size:
        meta["Last Note Time"] = float(ts_bad[-1])
    return {"metadata": meta, "song_data": song_data}


def test_persistence_authority_contract_real_song_be_right_there_t5_base():
    frozen = _fixture_payload("persistence_authority_be_right_there_t5.json")
    song_file = Path(__file__).resolve().parents[1] / str(frozen["song_file_rel"])
    assert song_file.exists(), f"Missing frozen chart fixture: {song_file}"

    cfg_dict = {
        "IterationEngine": {},
        "TeamContributionBuffConstant": {
            "TeamBuff": str(frozen["team_buff"]),
            "TeamColor": str(frozen["primary_color"]),
        },
    }
    calc_song = get_base_calc_song(str(song_file), cfg_dict)
    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert isinstance(ref_arrays, dict) and ref_arrays
    _prebuild_timeline_frontier(calc_song, ref_arrays)
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
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
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
    exact = int(score_stats_exact(stats, calc_song, ref_arrays))
    authority_score = 47192170
    assert int(row["score"]) == exact == int(base_entry["expected_score"]) == authority_score
    assert int(row["score"]) != stale_score
    assert int(row.get("fg_score") or 0) == 0
    assert row.get("force") is None

    gem_counts = dict(details_actual.get("GemCounts") or {})
    assert int(gem_counts.get("Fever Multiplier", 0)) == 13
    assert int(gem_counts.get("Element", 0)) == 64
    assert int(details_actual.get("FF", 0)) == 13

    wrong_timeline_calc_song = _calc_song_with_truncated_timeline(calc_song)
    _prebuild_timeline_frontier(wrong_timeline_calc_song, ref_arrays)
    wrong_timeline_score = int(score_stats_exact(stats, wrong_timeline_calc_song, ref_arrays))
    assert wrong_timeline_score <= authority_score
