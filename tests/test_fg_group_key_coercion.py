import pytest


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "abc",
        (),
        (1, 2),
        (1, 2, 3, 4),
        {},
        {"a": 1},
        object(),
    ],
)
def test_coerce_fg_group_key_rejects_invalid_shapes(value):
    from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import _coerce_fg_group_key

    assert _coerce_fg_group_key(value) is None


def test_coerce_fg_group_key_normalizes_tuple_or_list():
    from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import _coerce_fg_group_key

    assert _coerce_fg_group_key(("Rush", "2", "5")) == ("Rush", 2, 5)
    assert _coerce_fg_group_key(["Beat", 3, 7]) == ("Beat", 3, 7)

