from __future__ import annotations

from types import SimpleNamespace

import pytest

from gear_optimizer.helpers.song_helpers import team_buff_tiers
from gear_optimizer.pipeline import post_processor_persist
from gear_optimizer.solver.native_inflight_fg_payload import build_deferred_post_payload
from tests.native_song_factory import make_native_song


def _custom_catalogs() -> tuple[dict[str, dict], dict[str, dict]]:
    gears = {
        f"Website Gear {index}": {
            "Name": f"Website Gear {index}",
            "type": f"Slot {index}",
            "Perfect Points": index,
        }
        for index in range(1, 8)
    }
    minis = {
        f"Website Mini {index}": {
            "Name": f"Website Mini {index}",
            "type": "Mini",
            "Perfect Points": index + 10,
        }
        for index in range(1, 5)
    }
    return gears, minis


def test_entry_loadout_items_resolves_custom_request_catalog_without_csv(monkeypatch):
    gears, minis = _custom_catalogs()
    gear_names = list(gears)[:6]
    mini_names = list(minis)[:3]
    monkeypatch.setattr(
        team_buff_tiers,
        "get_gears_by_name_cached",
        lambda: (_ for _ in ()).throw(AssertionError("CSV gear catalog must not be consulted")),
    )
    monkeypatch.setattr(
        team_buff_tiers,
        "get_minis_by_name_cached",
        lambda: (_ for _ in ()).throw(AssertionError("CSV mini catalog must not be consulted")),
    )

    items = team_buff_tiers._entry_loadout_items(
        {
            "loadout_hash": "website-only",
            "gear": gear_names,
            "minis": mini_names,
        },
        gears_by_name=gears,
        minis_by_name=minis,
    )

    assert [item["Name"] for item in items] == gear_names + mini_names


def test_deferred_post_payload_carries_only_referenced_request_items():
    gears, minis = _custom_catalogs()
    gear_names = list(gears)[:6]
    mini_names = list(minis)[:3]
    candidate = {
        "Score": 123,
        "BaseScore": 123,
        "Gear": gear_names,
        "Minis": mini_names,
        "Data": {"Stats": {"Perfect Points": 123}},
    }
    song = make_native_song(
        song_name="Website-only catalog",
        task_key="website-only-catalog",
        db_key="website-only-catalog",
        gears_by_name=gears,
        minis_by_name=minis,
        base_candidates=[candidate],
        fg_surface_prepared=True,
        best_data=candidate["Data"],
        best_gear=gear_names,
        best_minis=mini_names,
        fg_variants=[],
    )

    payload = build_deferred_post_payload(song)

    assert set(payload["gears_by_name"]) == set(gear_names)
    assert set(payload["minis_by_name"]) == set(mini_names)
    assert "Website Gear 7" not in payload["gears_by_name"]
    assert "Website Mini 4" not in payload["minis_by_name"]


def test_deferred_post_payload_fails_on_unresolved_request_identity():
    gears, minis = _custom_catalogs()
    gear_names = list(gears)[:6]
    mini_names = list(minis)[:3]
    del gears[gear_names[-1]]
    song = make_native_song(
        gears_by_name=gears,
        minis_by_name=minis,
        base_candidates=[
            {
                "Score": 123,
                "Gear": gear_names,
                "Minis": mini_names,
                "Data": {"Stats": {"Perfect Points": 123}},
            }
        ],
        fg_surface_prepared=True,
        best_data={"Score": 123},
        best_gear=gear_names,
        best_minis=mini_names,
        fg_variants=[],
    )

    with pytest.raises(ValueError, match="cannot resolve request-local gear identities"):
        build_deferred_post_payload(song)


def test_post_persist_threads_request_catalogs_into_replay_context(monkeypatch):
    gears, minis = _custom_catalogs()
    captured = {}

    def _capture(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(post_processor_persist, "canonicalize_and_assemble", _capture)
    context = SimpleNamespace(build_details=lambda data: data)
    item = {
        "calc_song": {"metadata": {}},
        "ref_arrays": {"Perfect Points": [1]},
        "cfg_dict": {},
        "gears_by_name": gears,
        "minis_by_name": minis,
    }

    assert post_processor_persist.build_post_persist_entries(item, db_payload={}, context=context) == []
    replay_context = captured["replay_ctx"]
    assert replay_context.gears_by_name is gears
    assert replay_context.minis_by_name is minis
