import json
import queue
import sys
import threading

from tests.native_song_factory import make_native_song


_REPLAY_GEAR = [
    "Juggernaut's Goggles",
    "Kagan's Cowboy Pants",
    "Chroma's Pixel Mage Hat",
    "Tobu's Sweet Shades",
    "Landino's Fro'",
    "Onii's Otaku Beanie",
]
_REPLAY_MINIS = ["t+pazolite", "Trailblazing Trance Zara", "Halloween Witch Teresa"]


def _ref_arrays() -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS

    rows = int(TOTAL_ROWS) + 1
    return {
        "Perfect Points": [1.0] * rows,
        "Combo Multiplier": [1.0] * rows,
        "Fever Multiplier": [1.0] * rows,
        "Fever Fill Rate": [1.0] * rows,
        "Fever Time": [1.0] * rows,
    }


def _prebuild_timeline_frontier(calc_song: dict, ref_arrays: dict) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    apply_timing_envelope(calc_song)
    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)


def _materialize_gpu_runtime_on_main_thread() -> None:
    if sys.platform != "darwin":
        return
    from gear_optimizer.solver.taichi_gem import api as gpu_api
    from gear_optimizer.solver.taichi_gem.runtime import ti

    gpu_api.ensure_ready()
    ti.sync()


def test_post_processor_deferred_native_save_persists_exact_replay_authority(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.pipeline import post_processor
    from gear_optimizer.solver import native_inflight_fg_payload as result_events
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    db_path = tmp_path / "post_processor_exact_authority.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    calc_song = {
        "metadata": {
            "Song Name": "pytest_post_processor_exact_authority",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0], "note_types": [0], "lanes": [0]},
    }
    ref_arrays = _ref_arrays()
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 5,
    }
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    raw_exact_score = int(score_stats_exact(stats, calc_song, ref_arrays))
    inflated_score = raw_exact_score + 12345

    monkeypatch.setattr(
        result_events,
        "materialize_candidate_names",
        lambda candidate, *, registry=None, mutate=False: (
            list(candidate.get("Gear") or []),
            list(candidate.get("Minis") or []),
        ),
    )
    monkeypatch.setattr(post_processor, "print_results", lambda *_args, **_kwargs: None)

    song = make_native_song(
        song_name="pytest_post_processor_exact_authority",
        task_key="pytest_post_processor_exact_authority",
        ga_seed=789,
        db_key="pytest_post_processor_exact_authority",
        fp="Data/Hard/pytest_post_processor_exact_authority.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        fg_debug=False,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        ga_candidates=[],
        best_data={
            "Score": inflated_score,
            "BaseScore": inflated_score,
            "Stats": dict(stats),
            "Selected Element": "Rush",
        },
        best_gear=list(_REPLAY_GEAR),
        best_minis=list(_REPLAY_MINIS),
        current_gear_list=[],
        current_mini_list=[],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record=None,
        attempt_lifetime=0,
        prev_attempts_first=0,
        db_best_fg_score=0,
    )

    payload = result_events.build_deferred_post_payload(song)
    # Production performs this startup barrier before the post-processing thread
    # exists; preserve that required macOS/MoltenVK ordering in the integration test.
    _materialize_gpu_runtime_on_main_thread()
    result_queue: queue.Queue = queue.Queue()
    worker = threading.Thread(
        target=post_processor.run_post_processor,
        args=(result_queue, 1),
        daemon=True,
    )

    worker.start()
    result_queue.put(payload)
    result_queue.put(None)
    worker.join(timeout=15.0)

    assert not worker.is_alive()

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, details_json "
            "FROM team_buff_loadouts "
            "WHERE song_name = ? AND team_buff = 'T5'",
            ("pytest_post_processor_exact_authority",),
        ).fetchone()

    assert row is not None
    stored_details = _unpack_stats_after_load(json.loads(str(row["details_json"] or "{}"))) or {}
    stored_stats = dict(stored_details.get("Stats") or {})

    assert stored_stats
    assert stored_stats != stats
    assert int(row["score"]) != inflated_score
    assert int(row["score"]) == int(score_stats_exact(stored_stats, calc_song, ref_arrays))


def test_post_processor_fg_update_path_canonicalizes_before_save(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.pipeline import post_processor

    db_path = tmp_path / "post_processor_fg_update_authority.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert ref_arrays
    calc_song = get_base_calc_song("Data/Hard/00 (Hard) by garlagan.txt", {})
    _prebuild_timeline_frontier(calc_song, ref_arrays)

    force_payload = {
        "Score": 32521173,
        "FT": 1,
        "FF": 15,
        "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 13,
            "Element": 61,
        },
        "Selected Element": "Rush",
        "BaseScore": 32518595,
        "BaseStats": {
            "Perfect Points": 40,
            "Combo Multiplier": 50,
            "Fever Multiplier": 37,
            "Fever Time": 28,
            "Fever Fill Rate": 19,
            "Beat": 0,
            "Vibe": 44,
            "Rush": 321,
            "Flow": 29,
            "Chill": 33,
        },
        "ForceGreats": {"final_score": 32521173},
        "response_surface": [4294967295, 4294967295, 4294967295, 15, 0, 0, 0, 0, 1090, 0, 0],
    }

    from gear_optimizer.helpers.song_helpers.persistence_payload import normalize_force_payload
    from gear_optimizer.core.stats_calculator import compute_full_stats
    from gear_optimizer.core.team_buff import team_buff_effect
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.data.mini_ascension import materialize_minis_for_song

    force_norm = normalize_force_payload(dict(force_payload))
    base_stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Chill": 0,
        "Flow": 0,
        "Rush": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    for stat_name, delta in team_buff_effect("T5", "Rush").items():
        base_stats[stat_name] = int(base_stats.get(stat_name, 0)) + int(delta)
    _materialized_minis, minis_by_name, _context = materialize_minis_for_song(
        minis_by_name=get_minis_by_name_cached(),
        song_name="pytest_post_processor_fg_update_authority",
        primary_color="Rush",
        secondary_color="Rush",
    )
    canonical_stats = compute_full_stats(
        _REPLAY_GEAR,
        _REPLAY_MINIS,
        {},
        "Rush",
        get_gears_by_name_cached(),
        minis_by_name,
        base_stats,
    )
    expected_base = 19_000_000
    expected_fg = 20_000_000

    canonicalize_calls = []

    def _canonicalize(entries, *, calc_song, ref_arrays):
        canonicalize_calls.append((entries, calc_song, ref_arrays))
        entry = dict(entries[0])
        details = dict(entry["details"])
        details["GemCounts"] = {}
        details["FT"] = 0
        details["FF"] = 0
        details["Stats"] = dict(canonical_stats)
        force = dict(force_norm)
        force["GemCounts"] = {}
        force["FT"] = 0
        force["FF"] = 0
        force["Stats"] = dict(canonical_stats)
        force["BaseStats"] = dict(canonical_stats)
        force["BaseScore"] = expected_base
        force["Score"] = expected_fg
        force["ForceGreats"] = {
            "final_score": expected_fg,
            "raw_fever_fill": 1.0,
            "real_fever_time": 1.0,
            "frontier_trace": [
                {
                    "section": 1,
                    "activation_index": 0,
                    "fever_end_index": 1,
                    "forced_start_index": 0,
                    "forced_run_start_index": 0,
                    "forced_run_count": 0,
                }
            ],
        }
        entry["details"] = details
        entry["force"] = force
        entry["score"] = expected_base
        entry["fg_base_score"] = expected_base
        entry["fg_score"] = expected_fg
        return [entry]

    monkeypatch.setattr(post_processor, "print_results", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.persistence_authority.canonicalize_authoritative_fg_entries",
        _canonicalize,
    )
    monkeypatch.setattr(
        "gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached",
        lambda: ref_arrays,
    )

    result_queue: queue.Queue = queue.Queue()
    worker = threading.Thread(
        target=post_processor.run_post_processor,
        args=(result_queue, 1),
        daemon=True,
    )
    worker.start()
    result_queue.put(
        {
            "_fg_update": True,
            "song": "pytest_post_processor_fg_update_authority",
            "db_key": "pytest_post_processor_fg_update_authority",
            "file_path": "Data/Hard/00 (Hard) by garlagan.txt",
            "cfg_dict": {"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
            "ref_arrays": ref_arrays,
            "persist_entries": [
                {
                    "score": 32518595,
                    "fg_score": 32521173,
                    "fg_base_score": 32518595,
                    "gear": list(_REPLAY_GEAR),
                    "minis": list(_REPLAY_MINIS),
                    "details": {
                        "Stats": {
                            "Perfect Points": 40,
                            "Combo Multiplier": 50,
                            "Fever Multiplier": 76,
                            "Fever Time": 31,
                            "Fever Fill Rate": 64,
                            "Beat": 3,
                            "Vibe": 89,
                            "Rush": 726,
                            "Flow": 29,
                            "Chill": 33,
                        },
                        "SelectedElement": "Rush",
                        "PrimaryColor": "Rush",
                        "SecondaryColor": "Rush",
                    },
                    "force": force_payload,
                    "_deferred_fg_update": True,
                }
            ],
        }
    )
    result_queue.put(None)
    worker.join(timeout=15.0)

    assert not worker.is_alive()
    assert len(canonicalize_calls) == 1

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json "
            "FROM team_buff_fg_loadouts "
            "WHERE song_name = ? AND team_buff = 'T5'",
            ("pytest_post_processor_fg_update_authority",),
        ).fetchone()

    assert row is not None
    stored_details = json.loads(str(row["details_json"] or "{}"))
    stored_force = json.loads(str(row["force_details_json"] or "{}"))
    assert int(row["score"]) == expected_base
    assert int(row["fg_score"]) == expected_fg
    assert int(stored_details["BaseScore"]) == expected_base
    assert int(stored_force["BaseScore"]) == expected_base
    assert int(stored_force["Score"]) == expected_fg
