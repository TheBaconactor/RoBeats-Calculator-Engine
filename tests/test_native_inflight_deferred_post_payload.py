from gear_optimizer.solver.native_inflight_types import make_native_song


def test_native_inflight_deferred_post_payload_keeps_replay_context_when_fg_debug_disabled(monkeypatch):
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator

    calc_song = {
        "metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"},
        "song_data": {"timestamps": [0.0], "note_types": [1]},
    }
    ref_arrays = {"Perfect Points": [0], "Combo Multiplier": [1.0], "Fever Multiplier": [1.0]}
    ga_candidates = [
        {
            "Score": 111,
            "BaseScore": 111,
            "Gear": ["G1"],
            "Minis": ["M1"],
            "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            "_fg_priority": 7,
            "loadout_hash": "hash-1",
        }
    ]

    monkeypatch.setattr(
        orchestrator,
        "select_effective_unique_ga_candidates",
        lambda candidates, **_kwargs: list(candidates),
    )
    monkeypatch.setattr(
        orchestrator,
        "materialize_candidate_names",
        lambda candidate, *, registry=None, mutate=False: (
            list(candidate.get("Gear") or []),
            list(candidate.get("Minis") or []),
        ),
    )

    song = make_native_song(
        song_name="pytest_native_deferred_post",
        task_key="pytest_native_deferred_post",
        ga_seed=123,
        db_key="pytest_native_deferred_post",
        fp="Data/Hard/pytest_native_deferred_post.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        use_evo_db=True,
        fg_debug=False,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        ga_candidates=ga_candidates,
        best_data={"Score": 111, "BaseScore": 111, "Stats": {"Perfect Points": 1}},
        best_gear=["G1"],
        best_minis=["M1"],
        current_gear_list=["CurrentGear"],
        current_mini_list=["CurrentMini"],
        enable_gear=True,
        enable_mini=True,
        manual_force_greats=True,
        force_greats_finder=False,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record={"score": 100},
        attempt_lifetime=9,
        prev_attempts_first=2,
        db_best_fg_score=105,
    )

    payload = orchestrator._build_deferred_post_payload(song, persist_pending_fg_job=True)

    assert payload["_deferred_post"] is True
    assert payload["_pending_fg_job"] is True
    assert payload["_persist_pending_fg_job"] is True
    assert payload["fg_debug"] is False
    assert payload["calc_song"] is calc_song
    assert payload["ref_arrays"] is ref_arrays
    assert payload["best_data"]["BaseScore"] == 111
    assert payload["ga_candidates"] == [
        {
            "Score": 111,
            "BaseScore": 111,
            "Gear": ["G1"],
            "Minis": ["M1"],
            "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            "_fg_priority": 7,
            "loadout_hash": "hash-1",
        }
    ]


def test_native_inflight_deferred_post_payload_uses_inline_fg_as_authority(monkeypatch):
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator

    monkeypatch.setattr(
        orchestrator,
        "select_effective_unique_ga_candidates",
        lambda candidates, **_kwargs: list(candidates),
    )
    monkeypatch.setattr(
        orchestrator,
        "materialize_candidate_names",
        lambda candidate, *, registry=None, mutate=False: (
            list(candidate.get("Gear") or []),
            list(candidate.get("Minis") or []),
        ),
    )

    song = make_native_song(
        song_name="pytest_native_deferred_post_inline_fg",
        task_key="pytest_native_deferred_post_inline_fg",
        ga_seed=321,
        db_key="pytest_native_deferred_post_inline_fg",
        fp="Data/Hard/pytest_native_deferred_post_inline_fg.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        use_evo_db=True,
        fg_debug=False,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={"Perfect Points": []},
        ga_candidates=[
            {
                "Score": 111,
                "BaseScore": 111,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        best_data={"Score": 111, "BaseScore": 111, "Stats": {"Perfect Points": 1}},
        best_gear=["G1"],
        best_minis=["M1"],
        force_greats_finder=True,
        fg_variants=[
            {
                "score": 111,
                "base_score": 111,
                "fg_score": 130,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record={"score": 100},
        attempt_lifetime=3,
        prev_attempts_first=2,
        db_best_fg_score=105,
    )

    payload = orchestrator._build_deferred_post_payload(song, persist_pending_fg_job=True)

    assert payload["_pending_fg_job"] is False
    assert payload["_persist_pending_fg_job"] is False
    assert int(payload["fg_variants"][0]["fg_score"]) == 130


def test_native_inflight_fg_inside_ga_runs_without_deferred_fg_update(monkeypatch):
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator

    calls: dict[str, object] = {}
    gpu_client = object()

    def _fake_run_fg_job_sync(song, *, gpu_client, post_sender, progress_cb, progress_tracker):
        calls["gpu_client"] = gpu_client
        calls["post_sender"] = post_sender
        calls["progress_cb"] = progress_cb
        calls["progress_tracker"] = progress_tracker
        song.runtime.fg.fg_variants = [
            {
                "score": 111,
                "base_score": 111,
                "fg_score": 130,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ]

    monkeypatch.setattr(orchestrator, "_run_fg_job_sync", _fake_run_fg_job_sync)

    song = make_native_song(
        song_name="pytest_native_inline_fg_runner",
        task_key="pytest_native_inline_fg_runner",
        db_key="pytest_native_inline_fg_runner",
        force_greats_finder=True,
        fg_variants=None,
    )

    orchestrator._score_fg_inside_ga(song, gpu_client=gpu_client)

    assert calls["gpu_client"] is gpu_client
    assert calls["post_sender"] is None
    assert calls["progress_cb"] is None
    assert calls["progress_tracker"] is None
    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 130


def test_native_inflight_deferred_post_payload_keeps_persistence_on_exact_replay_authority(monkeypatch):
    from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries
    from gear_optimizer.solver import native_inflight_orchestrator as orchestrator
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0]},
    }
    ref_arrays = {
        "Perfect Points": [1.0] * 1001,
        "Combo Multiplier": [1.0] * 1001,
        "Fever Multiplier": [1.0] * 1001,
        "Fever Fill Rate": [1.0] * 1001,
        "Fever Time": [1.0] * 1001,
    }
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 5,
    }
    raw_exact_score = int(score_stats_exact(stats, calc_song, ref_arrays))
    inflated_score = raw_exact_score + 12345

    monkeypatch.setattr(
        orchestrator,
        "select_effective_unique_ga_candidates",
        lambda candidates, **_kwargs: list(candidates),
    )
    monkeypatch.setattr(
        orchestrator,
        "materialize_candidate_names",
        lambda candidate, *, registry=None, mutate=False: (
            list(candidate.get("Gear") or []),
            list(candidate.get("Minis") or []),
        ),
    )

    song = make_native_song(
        song_name="pytest_native_deferred_post_exact_authority",
        task_key="pytest_native_deferred_post_exact_authority",
        ga_seed=456,
        db_key="pytest_native_deferred_post_exact_authority",
        fp="Data/Hard/pytest_native_deferred_post_exact_authority.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        use_evo_db=True,
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
        best_gear=["G1"],
        best_minis=["M1"],
        current_gear_list=[],
        current_mini_list=[],
        enable_gear=True,
        enable_mini=True,
        manual_force_greats=False,
        force_greats_finder=False,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record=None,
        attempt_lifetime=0,
        prev_attempts_first=0,
        db_best_fg_score=0,
    )

    payload = orchestrator._build_deferred_post_payload(song, persist_pending_fg_job=False)
    persist_entries = build_persistence_entries(
        {
            "score": int(payload["best_data"]["Score"]),
            "fg_score": 0,
            "gear": list(payload["best_gear"]),
            "minis": list(payload["best_minis"]),
            "details": {"Stats": dict(stats), "Selected Element": "Rush"},
            "force": None,
        },
        payload["ga_candidates"],
        None,
        lambda data: dict(data),
        calc_song=payload["calc_song"],
        ref_arrays=payload["ref_arrays"],
        cfg_dict=payload["cfg_dict"],
    )

    assert len(persist_entries) == 1
    persisted = persist_entries[0]
    persisted_stats = dict((persisted.get("details") or {}).get("Stats") or {})

    assert persisted["gear"] == ["G1"]
    assert persisted["minis"] == ["M1"]
    assert persisted["fg_score"] == 0
    assert persisted["force"] is None
    assert persisted["score"] != inflated_score
    assert persisted["score"] == int(score_stats_exact(persisted_stats, payload["calc_song"], payload["ref_arrays"]))
