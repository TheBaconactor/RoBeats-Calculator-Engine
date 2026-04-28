def test_taichi_api_no_longer_exports_ga_to_fg_stat_staging():
    from gear_optimizer.solver.taichi_gem import api as taichi_api

    assert not hasattr(taichi_api, "ga_stage_genome_base_stats_from_fg_candidates_table")
