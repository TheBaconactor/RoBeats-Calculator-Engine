import pytest

from gear_optimizer.helpers.song_helpers.fg_payload import (
    has_valid_fg_payload,
    require_response_surface,
    strip_retired_fg_fields,
)
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_item_names, compact_prev_record


SURFACE = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


@pytest.mark.parametrize(
    "payload",
    [
        {"response_surface": SURFACE},
        {"ForceGreats": {"response_surface": SURFACE}},
        {"data": {"response_surface": SURFACE}},
        {"force": {"response_surface": SURFACE}},
    ],
)
def test_response_surface_is_the_fg_payload_authority(payload):
    assert has_valid_fg_payload(payload) is True
    assert list(require_response_surface(payload)) == SURFACE


def test_config_only_payload_is_invalid():
    payload = {"ForceGreats": {"config": {"NonFever1": 1}}}
    assert has_valid_fg_payload(payload) is False
    with pytest.raises(ValueError, match="response_surface"):
        require_response_surface(payload)


def test_retired_fields_are_stripped_from_nested_persistence_payloads():
    cleaned, removed = strip_retired_fg_fields(
        {
            "TimelineFrontier": {"frontier_trace": [{"forced_prefix_count": 4}]},
            "ForceGreats": {
                "config": {"NonFever1": 4},
                "enabled": True,
                "variant_applied": True,
                "frontier_trace": [{"forced_counts": [4, 0]}],
            },
            "config": {"unrelated": "kept"},
        }
    )

    assert removed == 5
    assert cleaned == {
        "TimelineFrontier": {"frontier_trace": [{}]},
        "ForceGreats": {"frontier_trace": [{}]},
        "config": {"unrelated": "kept"},
    }


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
