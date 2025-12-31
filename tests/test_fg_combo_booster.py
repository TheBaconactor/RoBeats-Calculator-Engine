from gear_optimizer.helpers.song_helpers.fg_combo_booster import (
    generate_fg_combo_booster_genomes,
    select_fg_combo_booster_genomes_for_eval,
)
from gear_optimizer.solver.item_registry import ItemRegistry


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update(stats)
    return out


def _key(genome: list[dict]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    gear = tuple((it or {}).get("Name", "") for it in genome[:6])
    minis = tuple(sorted((it or {}).get("Name", "") for it in genome[6:9]))
    return gear, minis


def test_generate_fg_combo_booster_deterministic_and_deduped() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    hat_low = _mk_item("HatLow")
    hat_high = _mk_item("HatHigh", **{"Fever Multiplier": 10})

    fixed_neck = _mk_item("Neck")
    fixed_face = _mk_item("Face")
    fixed_shirt = _mk_item("Shirt")
    fixed_back = _mk_item("Back")
    fixed_pants = _mk_item("Pants")

    mini_1_low = _mk_item("Mini1Low")
    mini_1_high = _mk_item("Mini1High", **{"Fever Fill Rate": 10})
    mini_2 = _mk_item("Mini2")
    mini_3 = _mk_item("Mini3")

    gear_pool = {
        "Hat": [hat_high, hat_low],
        "Neck": [fixed_neck],
        "Face": [fixed_face],
        "Shirt": [fixed_shirt],
        "Back": [fixed_back],
        "Pants": [fixed_pants],
    }
    mini_pool = [mini_1_high, mini_2, mini_3, mini_1_low]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    seed = {
        "BaseScore": 1234,
        "Gear": [hat_low, fixed_neck, fixed_face, fixed_shirt, fixed_back, fixed_pants],
        "Minis": [mini_1_low, mini_2, mini_3],
    }

    out1 = generate_fg_combo_booster_genomes(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=50,
        top_k=8,
        positions_per_seed=2,
    )
    out2 = generate_fg_combo_booster_genomes(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=50,
        top_k=8,
        positions_per_seed=2,
    )

    assert out1 == out2
    assert len(out1) == 3  # all (hat, mini1) combos excluding the unchanged seed

    keys = {_key(g) for g in out1}
    assert len(keys) == len(out1)

    expected_gear_base = ("HatLow", "Neck", "Face", "Shirt", "Back", "Pants")
    expected_minis_base = ("Mini1Low", "Mini2", "Mini3")

    assert (("HatHigh",) + expected_gear_base[1:], expected_minis_base) in keys
    assert (expected_gear_base, ("Mini1High", "Mini2", "Mini3")) in keys
    assert (("HatHigh",) + expected_gear_base[1:], ("Mini1High", "Mini2", "Mini3")) in keys


def test_generate_fg_combo_booster_respects_cap() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {s: [_mk_item(f"{s}A"), _mk_item(f"{s}B", **{"Fever Time": 1})] for s in slots}
    mini_pool = [_mk_item("M1"), _mk_item("M2"), _mk_item("M3"), _mk_item("M4")]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    seed = {
        "Score": 1,
        "Gear": [gear_pool[s][0] for s in slots],
        "Minis": [mini_pool[0], mini_pool[1], mini_pool[2]],
    }

    out = generate_fg_combo_booster_genomes(
        existing_candidates=[seed],
        registry=registry,
        primary_color="Rush",
        secondary_color="",
        max_new=2,
        top_k=8,
        positions_per_seed=2,
    )
    assert len(out) <= 2


def test_select_fg_combo_booster_genomes_for_eval_is_deterministic_and_preserves_mini_diversity() -> None:
    gear_base = [_mk_item(f"G{i}") for i in range(6)]
    gear_fm = [_mk_item("G0H", **{"Fever Multiplier": 5})] + gear_base[1:]
    gear_ft = [gear_base[0], _mk_item("G1H", **{"Fever Time": 5})] + gear_base[2:]

    mini_a = _mk_item("A", **{"Fever Fill Rate": 10})
    mini_b = _mk_item("B")
    mini_c = _mk_item("C")
    mini_d = _mk_item("D", **{"Fever Time": 10})
    mini_e = _mk_item("E", **{"Fever Multiplier": 5})
    mini_f = _mk_item("F")

    def mk_genome(gear: list[dict], minis: list[dict]) -> list[dict]:
        return list(gear[:6]) + list(minis[:3])

    genomes = [
        mk_genome(gear_base, [mini_a, mini_b, mini_c]),
        mk_genome(gear_fm, [mini_a, mini_b, mini_c]),
        mk_genome(gear_ft, [mini_a, mini_b, mini_c]),
        mk_genome(gear_base, [mini_d, mini_e, mini_f]),
        mk_genome(gear_fm, [mini_d, mini_e, mini_f]),
        mk_genome(gear_base, [mini_a, mini_e, mini_f]),
        mk_genome(gear_fm, [mini_a, mini_e, mini_f]),
        mk_genome(gear_base, [mini_b, mini_c, mini_d]),
        mk_genome(gear_fm, [mini_b, mini_c, mini_d]),
        mk_genome(gear_base, [mini_b, mini_e, mini_f]),
    ]

    out1 = select_fg_combo_booster_genomes_for_eval(
        genomes,
        primary_color="Rush",
        secondary_color="",
        max_evals=6,
    )
    out2 = select_fg_combo_booster_genomes_for_eval(
        genomes,
        primary_color="Rush",
        secondary_color="",
        max_evals=6,
    )
    assert out1 == out2
    assert len(out1) == 6

    def mini_key(genome: list[dict]) -> tuple[str, ...]:
        return tuple(sorted((it or {}).get("Name", "") for it in genome[6:9]))

    # The first half is taken as "best-per-mini-team"; this should include unique mini teams.
    mini_keys = [mini_key(g) for g in out1]
    assert len(set(mini_keys[:3])) == 3

    # For a given mini team, we should keep the best (proxy) gear variant.
    abc = ("A", "B", "C")
    abc_selected = [g for g in out1 if mini_key(g) == abc]
    assert abc_selected and (abc_selected[0][0] or {}).get("Name") == "G0H"
