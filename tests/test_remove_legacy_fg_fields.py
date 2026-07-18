from gear_optimizer.helpers.song_helpers.fg_payload import strip_retired_fg_fields


def test_clean_payload_removes_only_retired_fg_fields():
    cleaned, removed = strip_retired_fg_fields(
        {
            "config": {"keep": True},
            "forced_counts": [1],
            "ForceGreats": {
                "config": {"NonFever1": 1},
                "enabled": True,
                "variant_applied": True,
                "frontier_trace": [
                    {
                        "forced_start_index": 0,
                        "forced_prefix_count": 1,
                        "forced_run_start_index": 0,
                        "forced_run_count": 1,
                    }
                ],
            },
            "response_surface": [0] * 11,
        }
    )

    assert removed == 5
    assert cleaned["config"] == {"keep": True}
    assert cleaned["response_surface"] == [0] * 11
    assert cleaned["ForceGreats"] == {
        "frontier_trace": [
            {
                "forced_start_index": 0,
                "forced_run_start_index": 0,
                "forced_run_count": 1,
            }
        ]
    }
