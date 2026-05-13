import json
import sqlite3
from pathlib import Path

import pytest


def _entry(*, score: int, fg_score: int = 0) -> dict:
    return {
        "score": int(score),
        "fg_score": int(fg_score),
        "gear": ["Test Hat"],
        "minis": ["Test Mini"],
        "details": {
            "Stats": {
                "Perfect Points": 100,
                "Combo Multiplier": 100,
                "Fever Multiplier": 100,
                "Fever Fill Rate": 100,
                "Fever Time": 100,
                "Chill": 10,
                "Vibe": 10,
                "Beat": 10,
                "Flow": 10,
                "Rush": 10,
            },
            "GemCounts": {},
            "PrimaryColor": "Rush",
            "SecondaryColor": "Flow",
            "SelectedElement": "Rush",
        },
        "force": None,
    }


def _seed_legacy_json_db(db_path: Path, *, user_version: int) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE songs (
                name TEXT PRIMARY KEY,
                best_score INTEGER DEFAULT 0,
                best_fg_score INTEGER DEFAULT 0,
                last_updated REAL
            );

            CREATE TABLE team_buff_loadouts (
                song_name TEXT,
                team_buff TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER DEFAULT 0,
                gear_json TEXT,
                minis_json TEXT,
                details_json TEXT,
                force_details_json TEXT,
                timestamp REAL,
                PRIMARY KEY (song_name, team_buff, loadout_hash)
            );

            CREATE TABLE team_buff_fg_loadouts (
                song_name TEXT,
                team_buff TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER,
                gear_json TEXT,
                minis_json TEXT,
                details_json TEXT,
                force_details_json TEXT,
                timestamp REAL,
                PRIMARY KEY (song_name, team_buff, loadout_hash)
            );
            """
        )
        conn.execute(f"PRAGMA user_version = {int(user_version)}")
        conn.execute(
            "INSERT INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            ("Legacy Song", 1234, 0, 0.0),
        )
        conn.execute(
            """
            INSERT INTO team_buff_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Legacy Song",
                "T5",
                "legacy_hash",
                1234,
                0,
                json.dumps(["Hat A"]),
                json.dumps([["Mini A", "Mini B"]]),
                json.dumps({"tag": "legacy"}),
                None,
                0.0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_evolution_db_manager_from_env_uses_evolution_db_path(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.delenv("EVOLUTION_OVERLAY_DB_PATH", raising=False)
    monkeypatch.delenv("METAFINDER_EVOLUTION_OVERLAY_DB", raising=False)

    db = EvolutionDbManager.from_env()
    assert db.db_path == str(db_path)
    assert db.overlay_db_path is None


def test_evolution_db_manager_from_env_include_overlay_wires_overlay_path(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "evolution.db"
    overlay = tmp_path / "overlay.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("EVOLUTION_OVERLAY_DB_PATH", str(overlay))

    db = EvolutionDbManager.from_env(include_overlay=True)
    assert db.db_path == str(db_path)
    assert db.overlay_db_path == str(overlay)


@pytest.mark.parametrize("user_version", [17, 18])
def test_init_db_backfills_legacy_json_rows_to_compact_blobs(tmp_path: Path, monkeypatch, user_version: int):
    from gear_optimizer.data.database import get_best_loadouts, init_db

    db_path = tmp_path / f"legacy_v{user_version}.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    _seed_legacy_json_db(db_path, user_version=user_version)

    init_db()

    conn = sqlite3.connect(str(db_path))
    try:
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(team_buff_loadouts)").fetchall()}
        assert "gear_ids_blob" in columns
        assert "minis_ids_blob" in columns

        row = conn.execute(
            "SELECT gear_ids_blob, minis_ids_blob FROM team_buff_loadouts WHERE song_name = ? AND team_buff = ?",
            ("Legacy Song", "T5"),
        ).fetchone()
        assert row is not None
        assert row[0] is not None
        assert row[1] is not None
    finally:
        conn.close()

    rows = get_best_loadouts("Legacy Song", limit=5, team_buff="T5", allow_fallback=False, db_path=str(db_path))
    assert len(rows) == 1
    assert rows[0]["gear"] == ["Hat A"]
    assert rows[0]["mini_groups"] == [["Mini A", "Mini B"]]


def test_get_song_catalog_defaults_to_resolved_baseline_team_buff(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.database import init_db, save_loadouts_batch
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "baseline_t5.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T10"},
        },
    )
    init_db()
    save_loadouts_batch("Catalog Song", [_entry(score=4321)], team_buff="T5")

    db = EvolutionDbManager.from_env()
    catalog = db.get_song_catalog()

    assert catalog["team_buff"] == "T5"
    assert catalog["songs"] == [
        {
            "song_name": "Catalog Song",
            "difficulty": "Normal",
            "base_ranks": [1],
            "fg_ranks": [],
            "leaderboards": ["base"],
        }
    ]


def test_get_best_loadouts_does_not_read_legacy_t15_rows_when_requesting_t20(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.database import get_best_loadouts, get_db_connection, init_db, save_loadouts_batch

    db_path = tmp_path / "legacy_t15_alias.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()
    save_loadouts_batch("Alias Song", [_entry(score=4321)], team_buff="T20")

    conn = get_db_connection(str(db_path))
    try:
        conn.execute(
            "UPDATE team_buff_loadouts SET team_buff = 'T15' WHERE song_name = ?",
            ("Alias Song",),
        )
        conn.commit()
    finally:
        conn.close()

    rows = get_best_loadouts("Alias Song", limit=5, team_buff="T20", allow_fallback=False, db_path=str(db_path))

    assert rows == []


def test_get_song_catalog_does_not_read_legacy_t15_rows_when_baseline_is_t20(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "catalog_legacy_t15_alias.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()
    save_loadouts_batch("Catalog Alias Song", [_entry(score=2468)], team_buff="T20")

    conn = get_db_connection(str(db_path))
    try:
        conn.execute(
            "UPDATE team_buff_loadouts SET team_buff = 'T15' WHERE song_name = ?",
            ("Catalog Alias Song",),
        )
        conn.commit()
    finally:
        conn.close()

    db = EvolutionDbManager.from_env()
    catalog = db.get_song_catalog(team_buff="T20")

    assert catalog["team_buff"] == "T20"
    assert catalog["songs"] == []


def test_save_loadouts_batch_persists_under_explicit_baseline_team_buff(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch

    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song = "pytest_baseline_team_buff"
    save_loadouts_batch(song, [_entry(score=1234)], team_buff="T10")

    conn = get_db_connection(str(db_path))
    try:
        row = conn.execute(
            "SELECT team_buff, score FROM team_buff_loadouts WHERE song_name = ? LIMIT 1",
            (song,),
        ).fetchone()
        assert row is not None
        assert str(row["team_buff"]) == "T10"
        assert int(row["score"]) == 1234
    finally:
        conn.close()


def test_db_manager_compute_team_buff_tier_leaderboards_on_demand_uses_native_baseline(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.database import init_db, save_loadouts_batch
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "compact_t5.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()
    save_loadouts_batch("OnDemand Song", [_entry(score=1234)], team_buff="T5")

    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T10", "TeamColor": "Rush"},
        },
    )
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: {"Perfect Points": []})
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda _song_file, _cfg_dict: {"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
    )
    monkeypatch.setattr("gear_optimizer.data.song_io.clone_calc_song", lambda calc_song: dict(calc_song))

    captured: dict[str, object] = {}

    def fake_compute(*, entries, calc_song, ref_arrays, cfg_dict, limit, tiers, target_team_color_override):
        captured["entries"] = list(entries)
        captured["cfg_dict"] = dict(cfg_dict)
        captured["tiers"] = tuple(tiers)
        captured["target_team_color_override"] = target_team_color_override
        return {"tiers": {"T5": {"base_top51": [{"score": 1234, "fg_score": 1234}]}}}

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.compute_team_buff_tier_leaderboards",
        fake_compute,
    )

    db = EvolutionDbManager.from_env()
    out = db.compute_team_buff_tier_leaderboards_on_demand("OnDemand Song", song_file="dummy.txt", tiers=("T5",))

    assert captured["entries"]
    assert captured["tiers"] == ("T5",)
    assert out["tiers"]["T5"]["base_top51"][0]["score"] == 1234


def test_db_manager_on_demand_replay_canonicalizes_baseline_seed_rows(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "canonical_seed.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"},
        },
    )
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: {"Perfect Points": [0]})
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda _song_file, _cfg_dict: {"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}, "song_data": {}},
    )
    monkeypatch.setattr("gear_optimizer.data.song_io.clone_calc_song", lambda calc_song: dict(calc_song))

    requested_limits: list[int] = []

    def _fake_get_best_loadouts(self, _song_name, **kwargs):
        requested_limits.append(int(kwargs.get("limit", 0) or 0))
        return [{"score": 77477622, "fg_score": 0, "gear": ["G1"], "minis": ["M1"], "details": {"Stats": {"Rush": 1}}}]

    monkeypatch.setattr(EvolutionDbManager, "get_best_loadouts", _fake_get_best_loadouts)

    def _fake_canonicalize(entries, **kwargs):
        out = [dict(entry) for entry in entries]
        out[0]["score"] = 64849540
        return out

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.baseline_replay.canonicalize_baseline_persist_entries",
        _fake_canonicalize,
    )

    captured: dict[str, object] = {}

    def fake_compute(*, entries, calc_song, ref_arrays, cfg_dict, limit, tiers, target_team_color_override):
        captured["entries"] = list(entries)
        return {"tiers": {"T5": {"base_top51": [{"score": int(entries[0].get("score", 0) or 0)}]}}}

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.compute_team_buff_tier_leaderboards",
        fake_compute,
    )

    db = EvolutionDbManager.from_env()
    db.compute_team_buff_tier_leaderboards_on_demand("Canonical Seed Song", song_file="dummy.txt", tiers=("T5",), limit=51)

    assert requested_limits == [408]
    assert captured["entries"][0]["score"] == 64849540


def test_db_manager_get_leaderboard_entry_uses_native_baseline_team_buff(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.database import init_db, save_loadouts_batch
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "compact_t5.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()
    save_loadouts_batch("Leaderboard Song", [_entry(score=2222)], team_buff="T5")

    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T10", "TeamColor": "Rush"},
        },
    )
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: {"Perfect Points": []})
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda _song_file, _cfg_dict: {"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
    )
    monkeypatch.setattr("gear_optimizer.data.song_io.clone_calc_song", lambda calc_song: dict(calc_song))

    captured: dict[str, object] = {}

    def fake_build(*, entries, calc_song, ref_arrays, cfg_dict, limit, tiers, target_team_color_override):
        captured["entries"] = list(entries)
        captured["tiers"] = tuple(tiers)
        return {"T5": [{"score": 2222, "fg_score": 2222}]}

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.build_team_buff_tier_db_batches",
        fake_build,
    )

    db = EvolutionDbManager.from_env()
    monkeypatch.setattr(EvolutionDbManager, "resolve_song_file", lambda self, _song_name: "dummy.txt")

    out = db.get_leaderboard_entry("Leaderboard Song", tier="T5", leaderboard="base", rank=1)

    assert captured["entries"]
    assert captured["tiers"] == ("T5",)
    assert out is not None
    assert out["song_name"] == "Leaderboard Song"
    assert out["tier"] == "T5"
    assert out["score"] == 2222


def test_db_manager_frontend_song_payload_returns_top_lists_and_context(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "frontend_payload.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setattr(EvolutionDbManager, "resolve_song_file", lambda self, _song_name: "Data/Hard/Payload.txt")

    captured: dict[str, object] = {}

    def fake_compute(self, song_name, *, song_file, tiers, limit, element, team_color):
        captured.update(
            {
                "song_name": song_name,
                "song_file": song_file,
                "tiers": tuple(tiers),
                "limit": limit,
                "element": element,
                "team_color": team_color,
            }
        )
        return {
            "meta": {
                "target_team_color": "Rush",
                "primary_color": "Rush",
                "secondary_color": "Flow",
            },
            "tiers": {
                "T10": {
                    "base_top51": [
                        {
                            "loadout_hash": "base-a",
                            "score": 200,
                            "details": {"hitsim_offset_deltas_ms": [3, -1]},
                        }
                    ],
                    "fg_top51": [
                        {
                            "loadout_hash": "fg-a",
                            "score": 200,
                            "fg_score": 250,
                            "details": {"hitsim_offset_deltas_ms": [3, -1]},
                            "force": {"ForceGreats": {"hitsim_offset_delta_ms": 5}},
                            "force_config": {"NonFever1": 2},
                        }
                    ],
                }
            },
        }

    monkeypatch.setattr(EvolutionDbManager, "compute_team_buff_tier_leaderboards_on_demand", fake_compute)

    db = EvolutionDbManager.from_env()
    out = db.get_frontend_song_payload(
        "Payload Song (Hard) by Mapper",
        tier="T10",
        limit=50,
        element="secondary",
    )

    assert captured["song_file"] == "Data/Hard/Payload.txt"
    assert captured["tiers"] == ("T10",)
    assert captured["element"] == "secondary"
    assert out is not None
    assert out["song_name"] == "Payload Song (Hard) by Mapper"
    assert out["difficulty"] == "Hard"
    assert out["tier"] == "T10"
    assert out["team_color"] == "Rush"
    assert out["base_top50"][0]["hitsim_offset_deltas_ms"] == [3, -1]
    assert out["fg_top50"][0]["force_sections"] == [
        {"section": 1, "key": "NonFever1", "forced_greats": 2}
    ]
    assert out["fg_top50"][0]["hitsim_offset_deltas_ms"] == [5]
    assert out["fg_top50"][0]["base_hitsim_offset_deltas_ms"] == [3, -1]
    assert out["fg_top50"][0]["fg_hitsim_offset_deltas_ms"] == [5]


def test_db_manager_get_leaderboard_entry_uses_fg_base_score_context(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "leaderboard_ctx.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"},
        },
    )
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: {"Perfect Points": []})
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda _song_file, _cfg_dict: {"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
    )
    monkeypatch.setattr("gear_optimizer.data.song_io.clone_calc_song", lambda calc_song: dict(calc_song))

    monkeypatch.setattr(EvolutionDbManager, "resolve_song_file", lambda self, _song_name: "dummy.txt")
    monkeypatch.setattr(
        EvolutionDbManager,
        "get_best_loadouts",
        lambda self, _song_name, **kwargs: [{"score": 100, "fg_score": 95}],
    )
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.build_team_buff_tier_db_batches",
        lambda **kwargs: {
            "T5": [
                {
                    "score": 100,
                    "fg_base_score": 90,
                    "fg_score": 95,
                    "gear": [],
                    "minis": [],
                    "details": {},
                    "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
                },
                {
                    "score": 110,
                    "fg_base_score": 0,
                    "fg_score": 105,
                    "gear": [],
                    "minis": [],
                    "details": {},
                    "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
                },
            ]
        },
    )

    db = EvolutionDbManager.from_env()
    out = db.get_leaderboard_entry("FG Context Song", tier="T5", leaderboard="fg", rank=1)

    assert out is not None
    assert out["song_name"] == "FG Context Song"
    assert out["tier"] == "T5"
    assert int(out["fg_score"] or 0) == 95
    assert int(out["fg_base_score"] or 0) == 90


def test_db_manager_get_leaderboard_entry_keeps_derived_tier_fg_row_visible(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "leaderboard_derived_fg.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"},
        },
    )
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: {"Perfect Points": []})
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda _song_file, _cfg_dict: {"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
    )
    monkeypatch.setattr("gear_optimizer.data.song_io.clone_calc_song", lambda calc_song: dict(calc_song))
    monkeypatch.setattr(EvolutionDbManager, "resolve_song_file", lambda self, _song_name: "dummy.txt")
    monkeypatch.setattr(
        EvolutionDbManager,
        "get_best_loadouts",
        lambda self, _song_name, **kwargs: [{"score": 100, "fg_score": 130, "fg_base_score": 140}],
    )
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.build_team_buff_tier_db_batches",
        lambda **kwargs: {
            "T10": [
                {
                    "score": 110,
                    "fg_base_score": 110,
                    "source_fg_base_score": 140,
                    "fg_score": 120,
                    "gear": [],
                    "minis": [],
                    "details": {},
                    "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
                }
            ]
        },
    )

    db = EvolutionDbManager.from_env()
    out = db.get_leaderboard_entry("Derived FG Song", tier="T10", leaderboard="fg", rank=1)

    assert out is not None
    assert out["song_name"] == "Derived FG Song"
    assert out["tier"] == "T10"
    assert int(out["score"] or 0) == 110
    assert int(out["fg_score"] or 0) == 120
    assert int(out["fg_base_score"] or 0) == 110
    assert int(out["source_fg_base_score"] or 0) == 140


def test_db_manager_get_leaderboard_entry_strict_sanity_output_preserves_source_scores(
    tmp_path: Path, monkeypatch
):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "leaderboard_strict_sanity.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"},
        },
    )
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: {"Perfect Points": []})
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda _song_file, _cfg_dict: {"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
    )
    monkeypatch.setattr("gear_optimizer.data.song_io.clone_calc_song", lambda calc_song: dict(calc_song))
    monkeypatch.setattr(EvolutionDbManager, "resolve_song_file", lambda self, _song_name: "dummy.txt")
    monkeypatch.setattr(
        EvolutionDbManager,
        "get_best_loadouts",
        lambda self, _song_name, **kwargs: [
            {"score": 100, "fg_score": 120, "fg_base_score": 90, "gear": ["G1"], "minis": ["M1"], "details": {}},
            {"score": 101, "fg_score": 0, "gear": ["G2"], "minis": ["M2"], "details": {}},
        ],
    )

    captured: dict[str, object] = {}

    def fake_build(*, entries, calc_song, ref_arrays, cfg_dict, limit, tiers, target_team_color_override):
        captured["tiers"] = tuple(tiers)
        captured["target_team_color_override"] = target_team_color_override
        return {
            "T20": [
                {
                    "loadout_hash": "hash-a",
                    "score": 320,
                    "fg_score": 350,
                    "fg_base_score": 320,
                    "source_score": 100,
                    "source_fg_base_score": 90,
                    "source_fg_score": 120,
                    "gear": ["G1"],
                    "minis": ["M1"],
                    "details": {"Stats": {"Flow": 75}},
                    "force": {
                        "Score": 350,
                        "ForceGreats": {
                            "config": {"NonFever1": 1},
                            "final_score": 350,
                        },
                    },
                },
                {
                    "loadout_hash": "hash-b",
                    "score": 330,
                    "fg_score": 0,
                    "fg_base_score": 0,
                    "source_score": 101,
                    "gear": ["G2"],
                    "minis": ["M2"],
                    "details": {"Stats": {"Flow": 88}},
                    "force": None,
                },
            ]
        }

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.build_team_buff_tier_db_batches",
        fake_build,
    )

    db = EvolutionDbManager.from_env()
    base_out = db.get_leaderboard_entry("Strict Sanity Song", tier="T20", leaderboard="base", rank=1, team_color="Flow")
    fg_out = db.get_leaderboard_entry("Strict Sanity Song", tier="T20", leaderboard="fg", rank=1, team_color="Flow")

    assert captured["tiers"] == ("T20",)
    assert captured["target_team_color_override"] == "Flow"

    assert base_out is not None
    assert base_out["leaderboard"] == "base"
    assert base_out["tier"] == "T20"
    assert base_out["loadout_hash"] == "hash-b"
    assert int(base_out["score"] or 0) == 330
    assert int(base_out["source_score"] or 0) == 101
    assert int(base_out["details"]["Stats"]["Flow"] or 0) == 88

    assert fg_out is not None
    assert fg_out["leaderboard"] == "fg"
    assert fg_out["tier"] == "T20"
    assert fg_out["loadout_hash"] == "hash-a"
    assert int(fg_out["score"] or 0) == 320
    assert int(fg_out["fg_base_score"] or 0) == 320
    assert int(fg_out["fg_score"] or 0) == 350
    assert int(fg_out["source_score"] or 0) == 100
    assert int(fg_out["source_fg_base_score"] or 0) == 90
    assert int(fg_out["source_fg_score"] or 0) == 120
    assert int(fg_out["details"]["Stats"]["Flow"] or 0) == 75
    assert int(fg_out["force"]["Score"] or 0) == 350
    assert int(fg_out["force"]["ForceGreats"]["final_score"] or 0) == 350


def test_db_manager_get_leaderboard_entry_breaks_ties_by_loadout_hash(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "leaderboard_ties.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setattr("gear_optimizer.core.config.load_config", lambda: object())
    monkeypatch.setattr(
        "gear_optimizer.core.utils.cfg_to_dict",
        lambda _cfg: {
            "IterationEngine": {},
            "TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"},
        },
    )
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: {"Perfect Points": []})
    monkeypatch.setattr(
        "gear_optimizer.data.song_io.get_base_calc_song",
        lambda _song_file, _cfg_dict: {"metadata": {"Primary Color": "Rush", "Secondary Color": "Flow"}},
    )
    monkeypatch.setattr("gear_optimizer.data.song_io.clone_calc_song", lambda calc_song: dict(calc_song))
    monkeypatch.setattr(EvolutionDbManager, "resolve_song_file", lambda self, _song_name: "dummy.txt")
    monkeypatch.setattr(
        EvolutionDbManager,
        "get_best_loadouts",
        lambda self, _song_name, **kwargs: [{"score": 100, "fg_score": 100}],
    )
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.team_buff_tiers.build_team_buff_tier_db_batches",
        lambda **kwargs: {
            "T5": [
                {"loadout_hash": "b_hash", "score": 100, "fg_score": 100, "gear": [], "minis": [], "details": {}},
                {"loadout_hash": "a_hash", "score": 100, "fg_score": 100, "gear": [], "minis": [], "details": {}},
            ]
        },
    )

    db = EvolutionDbManager.from_env()
    out = db.get_leaderboard_entry("Tie Song", tier="T5", leaderboard="base", rank=1)

    assert out is not None
    assert out["loadout_hash"] == "a_hash"
