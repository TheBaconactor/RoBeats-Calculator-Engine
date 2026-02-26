import gear_optimizer.helpers.song_helpers.fg_combo_booster as fcb
from gear_optimizer.solver.item_registry import ItemRegistry


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _build_registry_and_seed():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {s: [_mk_item(f"{s}A"), _mk_item(f"{s}B", **{"Fever Time": 1})] for s in slots}
    mini_pool = [_mk_item("M1"), _mk_item("M2"), _mk_item("M3"), _mk_item("M4")]
    registry = ItemRegistry(gear_pool, mini_pool, slots)
    seed = {
        "Score": 1,
        "Gear": [gear_pool[s][0] for s in slots],
        "Minis": [mini_pool[0], mini_pool[1], mini_pool[2]],
    }
    return registry, seed


def test_multi_axis_slot_cache_reuses_precomputed_slot_maps(monkeypatch):
    registry, seed = _build_registry_and_seed()
    fcb._clear_fg_combo_booster_slot_cache_for_tests()
    monkeypatch.setenv("FG_COMBO_BOOSTER_SLOT_CACHE", "1")

    calls = {"n": 0}
    orig = fcb._build_interesting_items_by_slot_multi_axis

    def _counting(*args, **kwargs):
        calls["n"] += 1
        return orig(*args, **kwargs)

    monkeypatch.setattr(fcb, "_build_interesting_items_by_slot_multi_axis", _counting)

    out1 = fcb.generate_fg_combo_booster_genomes_multi_axis(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=64,
        top_k=8,
    )
    out2 = fcb.generate_fg_combo_booster_genomes_multi_axis(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=64,
        top_k=8,
    )

    assert out1 == out2
    assert calls["n"] == 1


def test_slot_cache_toggle_preserves_multi_axis_results(monkeypatch):
    registry, seed = _build_registry_and_seed()

    fcb._clear_fg_combo_booster_slot_cache_for_tests()
    monkeypatch.setenv("FG_COMBO_BOOSTER_SLOT_CACHE", "0")
    out_uncached = fcb.generate_fg_combo_booster_genomes_multi_axis(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="Flow",
        max_new=64,
        top_k=8,
    )

    fcb._clear_fg_combo_booster_slot_cache_for_tests()
    monkeypatch.setenv("FG_COMBO_BOOSTER_SLOT_CACHE", "1")
    out_cached = fcb.generate_fg_combo_booster_genomes_multi_axis(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="Flow",
        max_new=64,
        top_k=8,
    )

    assert out_uncached == out_cached
