def test_ga_evolution_settings_do_not_expose_legacy_cache_hit_search_mode():
    """
    Cache-hit driven generation extension/mutation boosts were a hidden second
    GA mode. The invariant is that the parsed GA evolution policy has no field
    that can select that alternate behavior.
    """
    from dataclasses import fields

    from gear_optimizer.data.models import GAEvolutionSettings

    assert [field.name for field in fields(GAEvolutionSettings)] == [
        "memetic_elites",
        "memetic_steps",
        "memetic_top_gear",
        "memetic_top_minis",
        "multi_start",
        "gear_rank_max",
        "mini_rank_max",
    ]
