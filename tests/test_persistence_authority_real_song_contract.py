from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.helpers.song_helpers.fg_config import require_response_surface
from gear_optimizer.helpers.song_helpers.persistence_canon import build_persistence_entries
from gear_optimizer.helpers.song_helpers.persistence_payload import make_build_details_fn, normalize_force_payload
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import (
    score_force_greats_response_surface_exact,
    score_stats_exact,
)
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


def _float32_ref_arrays(ref_arrays: dict[str, Any]) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for name, values in dict(ref_arrays or {}).items():
        out[str(name)] = np.asarray(values, dtype=np.float32)
    return out


def _calc_song_with_truncated_timeline(calc_song: dict[str, Any]) -> dict[str, Any]:
    """
    Build a deliberately wrong-timeline calc_song variant.

    Used as a guard assertion: if authoritative replay accidentally switches timeline
    selection, score must drift away from the known authoritative value.
    """
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
        nt = np.asarray(note_types, dtype=np.int16)
        song_data["note_types"] = np.asarray(nt[: ts_bad.shape[0]], dtype=np.int16)
    lanes = song_data_src.get("lanes")
    if lanes is not None:
        lane_arr = np.asarray(lanes, dtype=np.int32)
        song_data["lanes"] = np.asarray(lane_arr[: ts_bad.shape[0]], dtype=np.int32)

    if ts_bad.size:
        meta["Last Note Time"] = float(ts_bad[-1])

    return {"metadata": meta, "song_data": song_data}


def test_persistence_authority_contract_real_song_ourovoros_t5():
    frozen = _fixture_payload("persistence_authority_ourovoros_t5.json")
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
    fg_entry = dict(frozen["fg_entry"])
    missing_stats_entry = dict(frozen["missing_stats_retained_entry"])

    db_payload = {
        "score": int(base_entry["expected_score"]) + 11111,
        "fg_score": 0,
        "gear": list(base_entry["gear"]),
        "minis": list(base_entry["minis"]),
        "details": dict(base_entry["details"]),
        "force": None,
        "best_fg": {
            "score": int(fg_entry["expected_fg_score"]) + 22222,
            "base_score": int(fg_entry["expected_score"]) + 33333,
            "gear": list(fg_entry["gear"]),
            "minis": list(fg_entry["minis"]),
            "details": dict(fg_entry["details"]),
            "force": dict(fg_entry["force"]),
        },
    }

    loadout_entries = {
        str(missing_stats_entry["loadout_hash"]): {
            "score": int(missing_stats_entry["expected_score"]) + 44444,
            "fg_score": 0,
            "gear": list(missing_stats_entry["gear"]),
            "minis": list(missing_stats_entry["minis"]),
            "details": dict(missing_stats_entry["details_without_stats"]),
            "eval_data": dict(missing_stats_entry["eval_data"]),
            "force": None,
        }
    }

    persist_entries = build_persistence_entries(
        db_payload,
        base_candidates=[],
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
    )

    rows_by_signature = {_row_signature(row): row for row in persist_entries if isinstance(row, dict)}
    base_sig = (tuple(str(v) for v in base_entry["gear"]), tuple(str(v) for v in base_entry["minis"]))
    fg_sig = (tuple(str(v) for v in fg_entry["gear"]), tuple(str(v) for v in fg_entry["minis"]))
    missing_sig = (
        tuple(str(v) for v in missing_stats_entry["gear"]),
        tuple(str(v) for v in missing_stats_entry["minis"]),
    )
    assert base_sig in rows_by_signature
    assert fg_sig in rows_by_signature
    assert missing_sig in rows_by_signature

    base_row = rows_by_signature[base_sig]
    _assert_selected_base_timeline_frontier(base_row.get("details") or {})
    base_details_actual = _details_runtime_agnostic_view(base_row.get("details") or {})
    base_details_expected = _details_runtime_agnostic_view(base_entry["details"])
    assert base_details_actual == base_details_expected
    base_stats = dict((base_details_actual.get("Stats") or {}))
    assert base_stats
    assert base_stats == dict(base_entry["details"]["Stats"])
    base_exact = int(score_stats_exact(base_stats, calc_song, ref_arrays))
    assert int(base_row["score"]) == base_exact
    assert int(base_row["score"]) == int(base_entry["expected_score"])
    assert int(base_row["score"]) != int(db_payload["score"])

    fg_row = rows_by_signature[fg_sig]
    _assert_selected_base_timeline_frontier(fg_row.get("details") or {})
    fg_details_actual = _details_runtime_agnostic_view(fg_row.get("details") or {})
    fg_details_expected = _details_runtime_agnostic_view(fg_entry["details"])
    assert fg_details_actual == fg_details_expected
    fg_stats = dict((fg_details_actual.get("Stats") or {}))
    assert fg_stats
    assert fg_stats == dict(fg_entry["details"]["Stats"])
    fg_base_exact = int(score_stats_exact(fg_stats, calc_song, ref_arrays))
    assert int(fg_row["score"]) == fg_base_exact
    assert int(fg_row["score"]) == int(fg_entry["expected_score"])

    force_norm = normalize_force_payload(fg_row.get("force"))
    force_stats = dict(force_norm.get("Stats") or {})
    assert force_stats
    fg_exact = int(
        score_force_greats_response_surface_exact(
            force_stats, calc_song, ref_arrays, require_response_surface(force_norm)
        )
    )
    assert fg_exact > int(fg_row["score"])
    assert int(fg_row["fg_score"]) == fg_exact
    assert int(fg_row["fg_score"]) == int(fg_entry["expected_fg_score"])
    assert int(fg_row["fg_score"]) != int(db_payload["best_fg"]["score"])

    missing_row = rows_by_signature[missing_sig]
    _assert_selected_base_timeline_frontier(missing_row.get("details") or {})
    missing_details_actual = _details_runtime_agnostic_view(missing_row.get("details") or {})
    missing_details_expected = _details_runtime_agnostic_view(build_details_fn(dict(missing_stats_entry["eval_data"])))
    assert missing_details_actual == missing_details_expected
    missing_stats = dict((missing_details_actual.get("Stats") or {}))
    assert missing_stats
    assert missing_stats == dict(missing_stats_entry["eval_data"]["Stats"])
    missing_exact = int(score_stats_exact(missing_stats, calc_song, ref_arrays))
    assert int(missing_row["score"]) == missing_exact
    assert int(missing_row["score"]) == int(missing_stats_entry["expected_score"])
    assert int(missing_row["score"]) != int(loadout_entries[str(missing_stats_entry["loadout_hash"])]["score"])

    for row in persist_entries:
        details = row.get("details") or {}
        stats = details.get("Stats") if isinstance(details, dict) else {}
        assert isinstance(stats, dict) and stats
        assert int(row.get("score") or 0) == int(score_stats_exact(stats, calc_song, ref_arrays))


def test_persistence_authority_contract_real_song_ourovoros_runtime_float32_refs_still_use_exact_replay():
    frozen = _fixture_payload("persistence_authority_ourovoros_t5.json")
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
    authoritative_ref_arrays = _get_team_buff_ref_arrays_cached()
    assert isinstance(authoritative_ref_arrays, dict) and authoritative_ref_arrays
    _prebuild_timeline_frontier(calc_song, authoritative_ref_arrays)
    runtime_ref_arrays = _float32_ref_arrays(authoritative_ref_arrays)
    assert np.asarray(authoritative_ref_arrays["Perfect Points"]).dtype == np.float64
    assert np.asarray(runtime_ref_arrays["Perfect Points"]).dtype == np.float32
    build_details_fn = make_build_details_fn(
        str(frozen["primary_color"]),
        str(frozen["secondary_color"]),
        str(frozen["difficulty"]),
    )

    base_entry = dict(frozen["base_entry"])
    fg_entry = dict(frozen["fg_entry"])
    missing_stats_entry = dict(frozen["missing_stats_retained_entry"])

    db_payload = {
        "score": int(base_entry["expected_score"]) + 11111,
        "fg_score": 0,
        "gear": list(base_entry["gear"]),
        "minis": list(base_entry["minis"]),
        "details": dict(base_entry["details"]),
        "force": None,
        "best_fg": {
            "score": int(fg_entry["expected_fg_score"]) + 22222,
            "base_score": int(fg_entry["expected_score"]) + 33333,
            "gear": list(fg_entry["gear"]),
            "minis": list(fg_entry["minis"]),
            "details": dict(fg_entry["details"]),
            "force": dict(fg_entry["force"]),
        },
    }

    loadout_entries = {
        str(missing_stats_entry["loadout_hash"]): {
            "score": int(missing_stats_entry["expected_score"]) + 44444,
            "fg_score": 0,
            "gear": list(missing_stats_entry["gear"]),
            "minis": list(missing_stats_entry["minis"]),
            "details": dict(missing_stats_entry["details_without_stats"]),
            "eval_data": dict(missing_stats_entry["eval_data"]),
            "force": None,
        }
    }

    authoritative_entries = build_persistence_entries(
        db_payload,
        base_candidates=[],
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
        calc_song=calc_song,
        ref_arrays=authoritative_ref_arrays,
        cfg_dict=cfg_dict,
    )
    runtime_entries = build_persistence_entries(
        db_payload,
        base_candidates=[],
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
        calc_song=calc_song,
        ref_arrays=runtime_ref_arrays,
        cfg_dict=cfg_dict,
    )

    authoritative_by_signature = {
        _row_signature(row): row for row in authoritative_entries if isinstance(row, dict)
    }
    runtime_by_signature = {_row_signature(row): row for row in runtime_entries if isinstance(row, dict)}
    assert runtime_by_signature.keys() == authoritative_by_signature.keys()

    base_sig = (tuple(str(v) for v in base_entry["gear"]), tuple(str(v) for v in base_entry["minis"]))
    fg_sig = (tuple(str(v) for v in fg_entry["gear"]), tuple(str(v) for v in fg_entry["minis"]))
    missing_sig = (
        tuple(str(v) for v in missing_stats_entry["gear"]),
        tuple(str(v) for v in missing_stats_entry["minis"]),
    )

    assert int(runtime_by_signature[base_sig]["score"]) == int(base_entry["expected_score"])
    assert int(runtime_by_signature[fg_sig]["score"]) == int(fg_entry["expected_score"])
    assert int(runtime_by_signature[fg_sig]["fg_score"]) == int(fg_entry["expected_fg_score"])
    assert int(runtime_by_signature[missing_sig]["score"]) == int(missing_stats_entry["expected_score"])

    for signature, runtime_row in runtime_by_signature.items():
        authoritative_row = authoritative_by_signature[signature]

        runtime_details = _details_runtime_agnostic_view(runtime_row.get("details") or {})
        authoritative_details = _details_runtime_agnostic_view(authoritative_row.get("details") or {})
        _assert_selected_base_timeline_frontier(runtime_row.get("details") or {})
        _assert_selected_base_timeline_frontier(authoritative_row.get("details") or {})
        assert runtime_details == authoritative_details

        stats = dict(runtime_details.get("Stats") or {})
        assert stats
        assert int(runtime_row.get("score") or 0) == int(score_stats_exact(stats, calc_song, runtime_ref_arrays))
        assert int(runtime_row.get("score") or 0) == int(authoritative_row.get("score") or 0)

        force_norm = normalize_force_payload(runtime_row.get("force"))
        if not force_norm:
            assert int(runtime_row.get("fg_score") or 0) == 0
            assert int(authoritative_row.get("fg_score") or 0) == 0
            continue

        force_stats = dict(force_norm.get("Stats") or {})
        assert force_stats
        fg_exact = int(
            score_force_greats_response_surface_exact(
                force_stats, calc_song, runtime_ref_arrays, require_response_surface(force_norm)
            )
        )
        assert int(runtime_row.get("fg_score") or 0) == fg_exact
        assert int(runtime_row.get("fg_score") or 0) == int(authoritative_row.get("fg_score") or 0)


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
        base_candidates=[],
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
    assert stats
    assert stats == dict(base_entry["details"]["Stats"])
    exact = int(score_stats_exact(stats, calc_song, ref_arrays))
    authority_score = 45507369
    assert int(row["score"]) == exact
    assert int(row["score"]) == int(base_entry["expected_score"])
    assert int(row["score"]) == authority_score, (
        "Authoritative replay drift: Be Right There loadout replay score changed "
        f"(got {int(row['score'])}, expected {authority_score})."
    )
    assert int(row["score"]) != stale_score
    assert int(row.get("fg_score") or 0) == 0
    assert row.get("force") is None

    gem_counts = dict(details_actual.get("GemCounts") or {})
    assert int(gem_counts.get("Fever Multiplier", 0)) == 13
    assert int(gem_counts.get("Element", 0)) == 64
    assert int(details_actual.get("FF", 0)) == 13

    # Timeline-selection guard: alternate timeline can tie, but must never beat authority.
    wrong_timeline_calc_song = _calc_song_with_truncated_timeline(calc_song)
    _prebuild_timeline_frontier(wrong_timeline_calc_song, ref_arrays)
    wrong_timeline_score = int(score_stats_exact(stats, wrong_timeline_calc_song, ref_arrays))
    assert wrong_timeline_score <= authority_score, (
        "Timeline selection guard failed: alternate timeline beat authoritative score "
        f"(alt={wrong_timeline_score}, authority={authority_score})."
    )
