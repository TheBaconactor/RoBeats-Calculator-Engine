from gear_optimizer.helpers.song_helpers.fg_combo_booster import generate_fg_combo_booster_genomes_multi_axis
from gear_optimizer.solver.item_registry import ItemRegistry


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _key(genome: list[dict]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    gear = tuple((it or {}).get("Name", "") for it in genome[:6])
    minis = tuple(sorted((it or {}).get("Name", "") for it in genome[6:9]))
    return gear, minis


def test_generate_fg_combo_booster_multi_axis_deterministic_and_deduped() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    hat_a = _mk_item("HatA", **{"Fever Multiplier": 1})
    hat_b = _mk_item("HatB", **{"Fever Multiplier": 10})
    neck_a = _mk_item("NeckA", **{"Fever Time": 1})
    neck_b = _mk_item("NeckB", **{"Fever Time": 10})
    face = _mk_item("Face")
    shirt = _mk_item("Shirt")
    back = _mk_item("Back")
    pants_a = _mk_item("PantsA", **{"Fever Fill Rate": 1})
    pants_b = _mk_item("PantsB", **{"Fever Fill Rate": 10})

    mini_a = _mk_item("MiniA", **{"Fever Fill Rate": 1})
    mini_b = _mk_item("MiniB", **{"Fever Fill Rate": 10})
    mini_c = _mk_item("MiniC")
    mini_d = _mk_item("MiniD")

    gear_pool = {
        "Hat": [hat_a, hat_b],
        "Neck": [neck_a, neck_b],
        "Face": [face],
        "Shirt": [shirt],
        "Back": [back],
        "Pants": [pants_a, pants_b],
    }
    mini_pool = [mini_a, mini_b, mini_c, mini_d]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    seed = {
        "BaseScore": 1234,
        "Gear": [hat_a, neck_a, face, shirt, back, pants_a],
        "Minis": [mini_a, mini_c, mini_d],
    }

    out1 = generate_fg_combo_booster_genomes_multi_axis(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=200,
        top_k=8,
    )
    out2 = generate_fg_combo_booster_genomes_multi_axis(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=200,
        top_k=8,
    )

    assert out1 == out2

    keys = {_key(g) for g in out1}
    assert len(keys) == len(out1)


def test_generate_fg_combo_booster_multi_axis_respects_cap() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {s: [_mk_item(f"{s}A"), _mk_item(f"{s}B", **{"Fever Time": 1})] for s in slots}
    mini_pool = [_mk_item("M1"), _mk_item("M2"), _mk_item("M3"), _mk_item("M4")]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    seed = {
        "Score": 1,
        "Gear": [gear_pool[s][0] for s in slots],
        "Minis": [mini_pool[0], mini_pool[1], mini_pool[2]],
    }

    out = generate_fg_combo_booster_genomes_multi_axis(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=3,
        top_k=8,
    )
    assert len(out) <= 3

