from gear_optimizer.helpers.song_helpers.fg_config import extract_fg_config, has_valid_fg_config
from gear_optimizer.helpers.song_helpers.payload_compaction import (
    compact_item_names,
    compact_loadout_entries,
    compact_prev_record,
)
from gear_optimizer.helpers.song_helpers.persistence_entry_selection import build_retained_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence_payload import make_build_details_fn


def test_extract_fg_config_from_result_entry_data():
    entry = {"data": {"ForceGreats": {"config": {"0": 1, "1": 0}}}}
    assert extract_fg_config(entry) == {"0": 1, "1": 0}
    assert has_valid_fg_config(entry) is True


def test_extract_fg_config_from_force_payload():
    force_payload = {"ForceGreats": {"config": {"0": 0, "1": 2}}}
    assert extract_fg_config(force_payload) == {"0": 0, "1": 2}
    assert has_valid_fg_config(force_payload) is True


def test_has_valid_fg_config_rejects_zero_or_missing_configs():
    assert has_valid_fg_config({"ForceGreats": {"config": {"0": 0, "1": 0}}}) is False
    assert has_valid_fg_config({"ForceGreats": {"config": {}}}) is False
    assert has_valid_fg_config({}) is False


def test_compact_item_names_and_prev_record_drop_empty_when_requested():
    record = {
        "gear": [{"Name": "G1"}, {"Name": ""}, "G2", None],
        "minis": [{"Name": "M1"}, "", "M2"],
        "loadout": ["A", None, "C"],
        "force": {"gear": ["", "G"], "minis": [None, "M"]},
    }

    assert compact_item_names(record["gear"], drop_empty=True) == ["G1", "G2"]
    compacted = compact_prev_record(record, drop_empty_item_names=True)
    assert compacted["gear"] == ["G1", "G2"]
    assert compacted["minis"] == ["M1", "M2"]
    assert compacted["loadout"] == ["A", "", "C"]
    assert compacted["force"]["gear"] == ["", "G"]
    assert compacted["force"]["minis"] == ["", "M"]


def test_compact_loadout_entries_preserves_eval_data_for_deferred_replay():
    eval_data = {
        "FT": 1,
        "FF": 2,
        "GemCounts": {"Perfect Points": 1},
        "Stats": {"Perfect Points": 12},
        "Selected Element": "Rush",
    }
    entries = {
        "hash-1": {
            "score": 123,
            "gear": [{"Name": "G1"}],
            "minis": [{"Name": "M1"}],
            "details": {},
            "eval_data": eval_data,
            "fg_base_score": 100,
        }
    }

    compacted = compact_loadout_entries(entries)

    assert compacted["hash-1"]["gear"] == ["G1"]
    assert compacted["hash-1"]["minis"] == ["M1"]
    assert compacted["hash-1"]["details"] == {}
    assert compacted["hash-1"]["eval_data"] == eval_data
    assert compacted["hash-1"]["fg_base_score"] == 100

    build_details = make_build_details_fn("Rush", "Beat", "Hard")
    retained = build_retained_loadout_entries(compacted, build_details)

    assert retained[0]["details"]["Stats"] == {"Perfect Points": 12}
