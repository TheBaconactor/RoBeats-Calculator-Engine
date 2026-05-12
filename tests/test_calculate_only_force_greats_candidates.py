from __future__ import annotations

from pathlib import Path

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.legacy import song_processor_adapter as legacy_song_processor


def _build_ref_arrays(stats_table) -> dict:
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            val = 0
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    return ref_arrays


def test_calculate_only_includes_current_loadout_for_fg(monkeypatch, tmp_path):
    """
    Regression guard:

    When MetaFinder is disabled (calculate-only mode), ForceGreatsFinder should still
    evaluate the *current configured loadout* even if no DB candidates exist.
    """
    repo_root = Path(__file__).resolve().parents[1]
    stats_path = repo_root / "Data" / "Gear" / "Stats.txt"
    gears_path = repo_root / "Data" / "Gear" / "Gears.csv"
    minis_path = repo_root / "Data" / "Gear" / "Minis.csv"

    paths = {
        "Easy": str(repo_root / "Data" / "Easy"),
        "Normal": str(repo_root / "Data" / "Normal"),
        "Hard": str(repo_root / "Data" / "Hard"),
        "Gear": str(repo_root / "Data" / "Gear"),
        "Gears": str(gears_path),
        "Minis": str(minis_path),
        "Stats": str(stats_path),
    }

    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    stats_table = read_table(str(stats_path))
    ref_arrays = _build_ref_arrays(stats_table)

    # ForceGreatsFinder enabled, MetaFinder disabled, DB disabled.
    cfg_dict = {
        "IterationEngine": {
            "MetaFinder": "false",
            "ForceGreatsMode": "true",
            "ForceGreatsFinder": "true",
            "ForceGreatsDebug": "false",
            "AutoSelectBuffAndColor": "false",
            "GPU_Mode": "true",
            "GPU_Native_GA": "true",
            "UseEvolutionDB": "false",
            "LoopForever": "false",
            "GA_SearchDepth": "50",
        },
        "TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"},
        "Gear": {
            "Hat": "The Games: Hidden Shine",
            "Neck": "Legendary Vibe Ringleader's Necktie",
            "Face": "Legendary Musketeer's Mask",
            "Shirt": "Legendary Vibe Ringleader's Suit",
            "Back": "Legendary Musketeer's Epaulette",
            "Pant": "Legendary Musketeer's Trousers",
        },
        "Minis": {"1": "Santa's Helper Marsha", "2": "Electroman", "3": "Ringmaster Roxie"},
        "UserInputStatsGems": {
            "perfect_points": "0",
            "combo_multiplier": "0",
            "fever_multiplier": "11",
            "fever_fill": "16",
            "fever_time": "0",
        },
        "ElementalGems": {"Chill": "0", "Flow": "0", "Rush": "0", "Beat": "0", "Vibe": "63"},
    }

    captured = {"n": None, "ga_n": None}

    def _fake_process_force_greats(loadout_entries, *args, **kwargs):
        captured["n"] = len(loadout_entries or {})
        captured["ga_n"] = len(kwargs.get("ga_candidates") or [])
        return []

    song_processor = legacy_song_processor.legacy_song_processor_module()
    monkeypatch.setattr(song_processor, "process_force_greats", _fake_process_force_greats)

    # Use a tiny synthetic song file in the modern tab-separated format to avoid
    # header edge cases (e.g. empty-string metadata fields).
    fp = tmp_path / "calc_only_song.txt"
    fp.write_text(
        "\n".join(
            [
                "Song Name\tCalcOnly Test Song",
                "Difficulty\t1",
                "Primary Color\tRush",
                "Secondary Color\tFlow",
                "Last Note Time\t0.900",
                "Total Notes\t10",
                "Fever Fill\t3",
                "Fever Time\t1.0",
                "Long Notes\t0",
                "",
                "Song Data",
                "0.000\t1\t1\t1",
                "0.100\t1\t1\t1",
                "0.200\t1\t1\t1",
                "0.300\t1\t1\t1",
                "0.400\t1\t1\t1",
                "0.500\t1\t1\t1",
                "0.600\t1\t1\t1",
                "0.700\t1\t1\t1",
                "0.800\t1\t1\t1",
                "0.900\t1\t1\t1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    args = (
        str(fp),
        "CalcOnly Test Song",
        "Hard",
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        False,  # use_evo_db
        False,  # auto_buff
        50,  # ga_depth
        None,  # status_queue
        None,  # parallel_workers
        False,  # fg_debug
    )

    legacy_song_processor.process_song_task(args)
    assert captured["n"] == 0
    assert captured["ga_n"] == 1
