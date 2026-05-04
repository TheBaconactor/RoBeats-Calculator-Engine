from gear_optimizer.helpers.song_helpers.force_greats import result_application


def test_collect_gpu_results_by_signature_builds_compact_force_payload():
    sig_results, elapsed = result_application.collect_gpu_results_by_signature(
        pending_sigs=["sig-a"],
        pending=[
            {
                "Perfect Points": 100,
                "Combo Multiplier": 100,
                "Fever Multiplier": 100,
                "Fever Fill Rate": 100,
                "Fever Time": 100,
                "Rush": 100,
            }
        ],
        sel_color="Rush",
        n_sections=2,
        max_per_section=2,
        counts_list=[(1, 0)],
        fg_scorer=None,
        result_final=[1200],
        result_base=[1000],
        result_cfg_idx=[0],
        result_cfg_counts=None,
        result_ft=[9],
        result_ff=[18],
        result_g_pp=[1],
        result_g_cm=[0],
        result_g_fm=[0],
        result_g_ov=[0],
        perf=False,
        materialize_stats=False,
    )

    assert elapsed == 0.0
    assert list(sig_results.keys()) == ["sig-a"]
    row = sig_results["sig-a"]
    assert row["fg_score"] == 1200
    assert row["base_score"] == 1000
    force = row["force"]
    assert force["BaseScore"] == 1000
    assert force["Score"] == 1200
    assert force["GemCounts"] == {
        "Perfect Points": 1,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Element": 0,
    }
    assert "Stats" not in force
    assert (force["ForceGreats"]["config"] or {}) == {"NonFever1": 1, "NonFever2": 0}


def test_apply_signature_result_to_entry_updates_candidate_ref():
    sig_result = {
        "fg_score": 1200,
        "base_score": 1000,
        "force": {
            "BaseScore": 1000,
            "Score": 1200,
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }
    candidate_ref = {}
    entry = {
        "score": 1000,
        "_candidate_ref": candidate_ref,
    }

    result_application.apply_signature_result_to_entry(entry=entry, sig_result=sig_result)

    assert entry["base_score"] == 1000
    assert entry["fg_score"] == 1200
    assert entry["force"]["Score"] == 1200
    assert candidate_ref["fg_score"] == 1200
    assert candidate_ref["force"]["Score"] == 1200
    assert candidate_ref["_entry_ref"] is entry


def test_collect_gpu_results_by_signature_decodes_plateau_representative_flags():
    class _FakeScorer:
        @staticmethod
        def get_fever_params(_ft_stat, _ff_stat):
            # raw_fill=33.3 => for fp=2, both k=4 and k=5 are on the same plateau.
            return (34, 0.0, 0, 33.3)

    # Encoded cfg count: fp_target=2 with rep flag set (k+1 representative).
    encoded_cfg = 64 + 2
    sig_results, _elapsed = result_application.collect_gpu_results_by_signature(
        pending_sigs=["sig-rep"],
        pending=[
            {
                "Perfect Points": 100,
                "Combo Multiplier": 100,
                "Fever Multiplier": 100,
                "Fever Fill Rate": 100,
                "Fever Time": 100,
                "Rush": 100,
            }
        ],
        sel_color="Rush",
        n_sections=1,
        max_per_section=8,
        counts_list=[],
        fg_scorer=_FakeScorer(),
        result_final=[1500],
        result_base=[1400],
        result_cfg_idx=[0],
        result_cfg_counts=[[encoded_cfg]],
        result_ft=[0],
        result_ff=[0],
        result_g_pp=[0],
        result_g_cm=[0],
        result_g_fm=[0],
        result_g_ov=[0],
        perf=False,
        materialize_stats=False,
    )

    row = sig_results["sig-rep"]
    cfg = (row["force"]["ForceGreats"]["config"] or {})
    assert int(cfg.get("NonFever1", 0)) == 5
