from gear_optimizer.helpers.song_helpers.force_greats import entry_utils


def test_fg_group_meta_from_eval_data_returns_cached_meta_without_rebuild(monkeypatch):
    cached = {
        "selected_element": "Rush",
        "center_ft": 4,
        "center_ff": 6,
        "skip": False,
        "n_sections": 3,
        "max_per_section": 8,
        "group_key": ("Rush", 3, 8),
        "signature": ("sig",),
        "fg_proxy_score": 42,
    }
    eval_data = {
        "BaseStats": {"Perfect Points": 1},
        "Selected Element": "Rush",
        "_fg_group_meta": cached,
    }

    def _boom(**_kwargs):
        raise AssertionError("cached FG group metadata should be reused")

    monkeypatch.setattr(entry_utils, "build_fg_group_meta", _boom)

    out = entry_utils.fg_group_meta_from_eval_data(
        eval_data,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        meta_primary_color="Rush",
        primary_color="Rush",
        secondary_color="Flow",
    )

    assert out is cached
