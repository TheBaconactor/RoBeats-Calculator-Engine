from gear_optimizer.core.team_buff import team_buff_effect, team_buff_query_values


def test_team_buff_effect_matches_rank_cutoff_table():
    assert team_buff_effect("NONE", "Rush") == {}
    assert team_buff_effect("T1", "Rush") == {"Perfect Points": 25, "Rush": 35}
    assert team_buff_effect("T5", "Rush") == {"Perfect Points": 25, "Rush": 30}
    assert team_buff_effect("T10", "Rush") == {"Perfect Points": 20, "Rush": 25}
    assert team_buff_effect("T20", "Rush") == {"Perfect Points": 15, "Rush": 20}
    assert team_buff_effect("T50", "Rush") == {"Perfect Points": 10, "Rush": 15}
    assert team_buff_effect("T51", "Rush") == {"Perfect Points": 5, "Rush": 10}


def test_team_buff_queries_use_canonical_keys_only():
    assert team_buff_query_values("T20") == ("T20",)
    assert team_buff_query_values("T51") == ("T51",)
