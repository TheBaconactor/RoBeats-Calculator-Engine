import pytest

from gear_optimizer.helpers.song_helpers.fg_payload import (
    require_response_surface,
    strip_retired_fg_fields,
)


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
    assert list(require_response_surface(payload)) == SURFACE


def test_config_only_payload_is_invalid():
    payload = {"ForceGreats": {"config": {"NonFever1": 1}}}
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
