from gear_optimizer.solver.native_inflight_types import make_native_song

import pytest


def test_process_force_greats_gpu_failure_raises_without_cpu_fallback(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import core

    monkeypatch.setenv("FG_INPROCESS_EXECUTOR", "0")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("gpu path failed")

    def _fake_cpu(**kwargs):
        return []

    monkeypatch.setattr(core, "process_force_greats_gpu_finder", _boom)
    monkeypatch.setattr(core, "_process_force_greats_cpu", _fake_cpu)

    class _Registry:
        @staticmethod
        def decode_names(ids):
            return [f"I{int(x)}" for x in ids[:9]]

    ga_candidates = [
        {
            "BaseScore": 321,
            "GenomeIDs": [1, 2, 3, 4, 5, 6, 9, 8, 7],
            "Data": {
                "BaseStats": {"Perfect Points": 5, "Rush": 7},
                "GemCounts": {"Perfect Points": 1},
                "FT": 1,
                "FF": 2,
                "Selected Element": "Rush",
            },
        }
    ]

    with pytest.raises(RuntimeError, match="gpu path failed"):
        core.process_force_greats(
            loadout_entries={},
            manual_force_greats=False,
            force_greats_finder=True,
            force_greats_config=[],
            calc_song={"metadata": {}, "song_data": {}},
            ref_arrays={},
            meta_primary_color="Rush",
            build_details_fn=lambda data: {"Stats": (data or {}).get("Stats", {})},
            use_gpu=True,
            ga_candidates=ga_candidates,
            ga_registry=_Registry(),
        )


def test_prepare_fg_job_sync_uses_db_only_entries_for_gpu_finder(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_stages as stages

    seen = {"ga_n": None}

    def _fake_build_loadout_entries(
        found_song_name,
        ga_candidates,
        db_loadouts_limit,
        gears_by_name,
        minis_by_name,
        build_details_fn,
        team_buff="T5",
        db_loadouts_full=None,
        allow_db_query=True,
        materialize_ga_details=True,
        ga_registry=None,
    ):
        seen["ga_n"] = len(ga_candidates or [])
        return {}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_loadouts_full=None,
        db_loadouts_future=None,
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        force_greats_finder=True,
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert seen["ga_n"] == 0
    assert song.runtime.fg.fg_direct_ga_candidates is True
    assert len(song.runtime.decode.ga_candidates or []) == 1


def test_process_force_greats_forwards_direct_ga_candidates(monkeypatch):
    from gear_optimizer.helpers.song_helpers.force_greats import core

    monkeypatch.setenv("FG_INPROCESS_EXECUTOR", "0")

    seen: list[tuple[int, object]] = []
    registry = object()

    def _fake_gpu_finder(
        loadout_entries,
        force_greats_finder,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        use_gpu=False,
        fg_search_radius=None,
        perf_timing=False,
        gpu_client=None,
        ga_candidates=None,
        ga_registry=None,
    ):
        _ = (
            loadout_entries,
            force_greats_finder,
            ref_arrays,
            meta_primary_color,
            use_gpu,
            fg_search_radius,
            perf_timing,
            gpu_client,
            ga_registry,
        )
        seen.append((len(list(ga_candidates or [])), ga_registry))
        return [
            {
                "data": {
                    "Score": 100 + len(seen),
                    "BaseScore": 90,
                    "ForceGreats": {"config": {"NonFever1": 1}},
                },
                "gear": [f"G{len(seen)}"],
                "minis": [f"M{len(seen)}"],
                "score": 90,
                "fg_score": 100 + len(seen),
            }
        ]

    monkeypatch.setattr(core, "process_force_greats_gpu_finder", _fake_gpu_finder)

    ga_candidates = [
        {
            "Gear": ["A"],
            "Minis": ["B"],
            "BaseScore": 90,
            "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
        }
    ]

    out = core.process_force_greats(
        loadout_entries={},
        manual_force_greats=False,
        force_greats_finder=True,
        force_greats_config=[],
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        meta_primary_color="Rush",
        build_details_fn=lambda data: data,
        use_gpu=True,
        ga_candidates=ga_candidates,
        ga_registry=registry,
    )

    assert seen == [(1, registry)]
    assert len(out) == 1
    assert int(out[0]["fg_score"]) == 101
    assert out[0]["gear"] == ["G1"]
    assert out[0]["minis"] == ["M1"]
