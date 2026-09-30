import sqlite3

import pytest

from gear_optimizer.gamedata import MINI_ASCENSION_VERSION
from gear_optimizer.store import db, schema, v18
from tests.store_support import V18Writer

ST = [85, 71, 69, 76, 18, 0, 716, 30, 78, 167]
TRACE = {"frontier_trace": [{"next_state": 1}], "response_surface": [1, 2]}
FG_TRACE = {"frontier_trace": [{"next_state": 2}], "raw_fever_fill": 1.5}
GEAR = ["Helmet", "Vest"]
MINIS = [["Chroma", "Chroma Twin"], ["Marie"]]


def _meta_details(**extra):
    details = {
        "FT": 6,
        "FF": 1,
        "st": ST,
        "gc": [0, 10, 10, 63],
        "se": "Flow",
        "pc": "Flow",
        "sc": "Vibe",
        "TimelineFrontier": TRACE,
        "Mini Ascension Materialized": True,
        "Mini Ascension Source Version": MINI_ASCENSION_VERSION,
        "Mini Ascension Materialized Song": "Old Song Name",
        "Mini Ascension Materialized Primary Color": "Flow",
        "Mini Ascension Materialized Secondary Color": "Vibe",
    }
    details.update(extra)
    return details


def _fg_details(score):
    return {
        "FT": 5,
        "FF": 2,
        "st": ST,
        "gc": [1, 9, 11, 60],
        "se": "Flow",
        "pc": "Flow",
        "sc": "Vibe",
        "BaseScore": score,
    }


def _fg_payload(score, fg_score, **extra):
    payload = {
        "Score": fg_score,
        "BaseScore": score,
        "FT": 5,
        "FF": 2,
        "SelectedElement": "Flow",
        "Selected Element": "Flow",
        "GemCounts": {"Perfect Points": 1, "Combo Multiplier": 9, "Fever Multiplier": 11, "Element": 60},
        "BaseStats": dict(
            zip(
                (
                    "Perfect Points",
                    "Combo Multiplier",
                    "Fever Multiplier",
                    "Fever Fill Rate",
                    "Fever Time",
                    "Chill",
                    "Flow",
                    "Rush",
                    "Beat",
                    "Vibe",
                ),
                ST,
            )
        ),
        "response_surface": list(range(11)),
        "ForceGreats": {"final_score": fg_score, **FG_TRACE},
        "GenomeIDs": [1, 2],
        "RawGASearchScore": score,
        "_ga_gpu_run_idx": 0,
        "_ga_gpu_row_idx": 3,
    }
    payload.update(extra)
    return payload


@pytest.fixture
def v18_db(tmp_path):
    path = tmp_path / "evolution.db"
    w = V18Writer(path)
    w.song("Song A")
    w.meta(
        "Song A",
        "twin",
        1000,
        1500,
        GEAR,
        MINIS,
        _meta_details(
            GemCounts={"Perfect Points": 0, "Combo Multiplier": 10, "Fever Multiplier": 10, "Element": 63},
            # A twin's copy of its FG result (the FG row carries it; witness timings rounded differently).
            ForceGreats={"final_score": 1500, "frontier_trace": [{"fg": 1.0001}]},
        ),
        timestamp=1_700_000_010,
    )
    w.fg("Song A", "twin", 990, 1500, GEAR, MINIS, _fg_details(990), _fg_payload(990, 1500), timestamp=1_700_000_020)
    w.meta("Song A", "never-fg", 900, 0, GEAR[:1], MINIS, _meta_details())
    # Its FG row was pruned; the meta row's copy is the only record of its FG result.
    w.meta("Song A", "stale-fg", 800, 950, GEAR[1:], MINIS, _meta_details(ForceGreats={"final_score": 950, **FG_TRACE}))
    w.fg(
        "Song A",
        "fg-only",
        700,
        1200,
        GEAR,
        MINIS[:1],
        _fg_details(700),
        _fg_payload(700, 1200, Genome=[1], Details={}),
    )
    w.close()
    return path


def test_every_loadout_migrates_with_a_single_score_and_both_results(v18_db):
    conn = sqlite3.connect(v18_db)
    report = v18.migrate(conn, keep_v18_tables=False)
    conn.close()
    assert (report.songs, report.meta_rows, report.fg_rows, report.loadouts, report.twins) == (1, 3, 2, 4, 1)
    assert report.paired_score_conflicts == [("Song A", "twin", 1000, 990)]
    assert report.fg_replays == 1
    reader = schema.connect(v18_db)
    got = {x.loadout_hash: x for x in db.iter_board(reader, "meta", tier="T5")}
    got.update({x.loadout_hash: x for x in db.iter_board(reader, "fg", tier="T5")})
    twin = got["twin"]
    assert (twin.score, twin.fg_score, twin.gear, twin.minis) == (
        1000,
        1500,
        tuple(GEAR),
        (("Chroma", "Chroma Twin"), ("Marie",)),
    )
    assert (twin.primary, twin.secondary, twin.mini_ascension) == ("Flow", "Vibe", MINI_ASCENSION_VERSION)
    assert (twin.meta.element, twin.meta.gems, twin.meta.stats, twin.meta.updated) == (
        "Flow",
        (0, 10, 10, 6, 1, 63),
        tuple(ST),
        1_700_000_010,
    )
    assert (twin.fg.gems, twin.fg.surface, twin.fg.updated) == ((1, 9, 11, 5, 2, 60), tuple(range(11)), 1_700_000_020)
    assert (got["never-fg"].fg_score, got["stale-fg"].fg_score) == (None, 950)
    assert (got["stale-fg"].fg, got["stale-fg"].on_meta, got["stale-fg"].on_fg) == (None, True, False)
    assert (twin.on_meta, twin.on_fg) == (True, True)
    fg_only = got["fg-only"]
    assert (fg_only.meta, fg_only.score, fg_only.fg_score, fg_only.mini_ascension) == (None, 700, 1200, None)
    assert (fg_only.on_meta, fg_only.on_fg) == (False, True)
    traces = db.load_traces(reader, "Song A", "T5", ["twin", "fg-only", "stale-fg", "never-fg"])
    assert traces["twin"].meta == TRACE and traces["twin"].fg == FG_TRACE and traces["fg-only"].meta is None
    # The pruned loadout keeps its FG replay; a loadout never evaluated for FG has none.
    assert (traces["stale-fg"].fg, traces["never-fg"].fg) == (FG_TRACE, None)
    assert db.last_updated(reader) == {"Song A": 1_700_000_000.5}
    tables = {r[0] for r in reader.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tables == {"songs", "loadouts"}


def test_the_migrated_schema_is_the_fresh_schema(v18_db, tmp_path):
    conn = schema.connect(v18_db, write=True)  # a writer migrates a version 18 database itself
    conn.close()
    fresh = tmp_path / "fresh.db"
    schema.connect(fresh, write=True).close()
    ddl = lambda path: sorted(sqlite3.connect(path).execute("SELECT type, name, sql FROM sqlite_master"))  # noqa: E731
    assert ddl(v18_db) == ddl(fresh)


def test_kept_v18_tables_stay_readable_until_dropped(v18_db):
    conn = sqlite3.connect(v18_db)
    v18.migrate(conn, keep_v18_tables=True)
    assert conn.execute("SELECT COUNT(*) FROM team_buff_loadouts").fetchone()[0] == 3
    assert conn.execute("SELECT name, last_updated FROM songs").fetchall() == [("Song A", 1_700_000_000.5)]
    conn.execute("BEGIN")
    v18.drop_v18_tables(conn)
    conn.commit()
    assert {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")} == {"songs", "loadouts"}


def test_an_unknown_stored_key_stops_the_migration_and_changes_nothing(tmp_path):
    path = tmp_path / "evolution.db"
    w = V18Writer(path)
    w.song("Song A")
    w.meta("Song A", "odd", 900, 0, GEAR, MINIS, _meta_details(Surprise=1))
    w.close()
    conn = sqlite3.connect(path)
    with pytest.raises(ValueError, match="meta details keys"):
        v18.migrate(conn, keep_v18_tables=False)
    assert schema.user_version(conn) == 18
    assert conn.execute("SELECT COUNT(*) FROM team_buff_loadouts").fetchone()[0] == 1
    assert "loadouts" not in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def test_a_meta_rows_fg_copy_must_score_the_rows_fg_score(tmp_path):
    path = tmp_path / "evolution.db"
    w = V18Writer(path)
    w.song("Song A")
    w.meta("Song A", "odd", 900, 950, GEAR, MINIS, _meta_details(ForceGreats={"final_score": 940, **FG_TRACE}))
    w.close()
    with pytest.raises(ValueError, match="FG copy scores 940"):
        v18.migrate(sqlite3.connect(path), keep_v18_tables=False)


def test_retired_fg_configuration_fields_are_stripped(tmp_path):
    path = tmp_path / "evolution.db"
    w = V18Writer(path)
    w.song("Song A")
    retired = {"final_score": 1200, **FG_TRACE, "config": {"NonFever1": 2}, "forced_counts": [5, 1]}
    payload = _fg_payload(700, 1200, ForceGreats=retired, forced_counts=[5, 1])
    w.fg("Song A", "old-job", 700, 1200, GEAR, MINIS, _fg_details(700), payload)
    w.close()
    conn = sqlite3.connect(path)
    report = v18.migrate(conn, keep_v18_tables=False)
    conn.close()
    assert report.retired_fields == 3
    reader = schema.connect(path)
    assert db.load_traces(reader, "Song A", "T5", ["old-job"])["old-job"].fg == FG_TRACE


def test_lenient_migration_keeps_the_payload_and_dates_undated_songs(tmp_path):
    path = tmp_path / "evolution.db"
    w = V18Writer(path)
    w.conn.execute("INSERT INTO songs VALUES ('Song A', 1, 1, NULL, 0, 0)")
    details = {**_fg_details(700), "st": [1] * 10}  # an older job database's stats copy
    w.fg("Song A", "old-job", 700, 1200, GEAR, MINIS, details, _fg_payload(700, 1200), timestamp=1_700_000_042)
    w.close()
    with pytest.raises(ValueError, match="songs without last_updated"):
        v18.migrate(sqlite3.connect(path), keep_v18_tables=False)
    conn = sqlite3.connect(path)
    report = v18.migrate(conn, keep_v18_tables=False, lenient=True)
    conn.close()
    assert report.copy_disagreements == [("Song A", "old-job", ["details st"])]
    assert report.songs_without_update == ["Song A"]
    reader = schema.connect(path)
    (x,) = db.iter_board(reader, "fg", tier="T5")
    assert x.fg.stats == tuple(ST) and db.last_updated(reader) == {"Song A": 1_700_000_042.0}


def test_disagreeing_copies_stop_the_migration(tmp_path):
    path = tmp_path / "evolution.db"
    w = V18Writer(path)
    w.song("Song A")
    w.fg("Song A", "bad", 700, 1200, GEAR, MINIS, _fg_details(700), _fg_payload(700, 1200, Score=1199))
    w.close()
    with pytest.raises(ValueError, match="FG copies differ"):
        v18.migrate(sqlite3.connect(path), keep_v18_tables=False)
