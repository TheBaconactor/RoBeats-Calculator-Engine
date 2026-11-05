import pytest

from gear_optimizer.store.fg_payload import (
    require_response_surface,
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


