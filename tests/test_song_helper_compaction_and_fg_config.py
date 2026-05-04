from gear_optimizer.helpers.song_helpers.fg_config import extract_fg_config, has_valid_fg_config
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_item_names, compact_prev_record


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
