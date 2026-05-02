from __future__ import annotations

import configparser
import json

import pytest

import general_meta.app as gm_app


def test_run_general_meta_raises_when_mini_stats_are_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        gm_app,
        "get_songs_by_elemental_combo",
        lambda _paths: {
            ("Chill", "Vibe"): [
                {"song_name": "Song A", "primary": "Chill", "secondary": "Vibe"},
            ]
        },
    )
    monkeypatch.setattr(gm_app, "read_table", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(gm_app.EvolutionDbManager, "from_env", lambda: object())
    monkeypatch.setattr(
        gm_app,
        "load_all_gears_list",
        lambda _paths: [
            {"Name": "Hat A", "Slot": "Hat"},
            {"Name": "Neck A", "Slot": "Neck"},
            {"Name": "Face A", "Slot": "Face"},
            {"Name": "Shirt A", "Slot": "Shirt"},
            {"Name": "Back A", "Slot": "Back"},
            {"Name": "Pants A", "Slot": "Pants"},
        ],
    )
    # Catalog intentionally omits "Missing Mini".
    monkeypatch.setattr(gm_app, "load_all_minis_list", lambda _paths: [{"Name": "Known Mini"}])

    def _build_rows_for_song(song, **_kwargs):
        song_name = str(song.get("song_name") or "")
        return (
            {},
            {},
            {
                "None": [],
                "T1": [],
                "T5": [
                    {
                        "song_name": song_name,
                        "score": 100,
                        "fg_score": 0,
                        "gear": ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"],
                        "mini_groups": [["Missing Mini"]],
                        "details_json": json.dumps({"GemCounts": {}}),
                    }
                ],
                "T10": [],
                "T20": [],
                "T50": [],
                "T51": [],
            },
        )

    monkeypatch.setattr(gm_app, "_build_replayed_loadout_rows_for_song", _build_rows_for_song)

    with pytest.raises(RuntimeError, match="Missing mini stats.*Missing Mini"):
        gm_app.run_general_meta(configparser.ConfigParser(), {})
