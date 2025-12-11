"""
Quick CPU vs GPU parity check for the gem solver batch path.

This script builds a small synthetic song and compares:
1) CPU solve_best_fever_combination (use_gpu=False)
2) GPU score_batch_gpu (single-item batch)

It prints the score/FT/FF/GemCounts/Selected Element for both paths.
"""

import numpy as np

from gear_optimizer import scoring
from gear_optimizer.constants import (
    TOTAL_ROWS,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
)
from gear_optimizer.utils import empty_stats


def build_refs():
    ref_pp = np.arange(TOTAL_ROWS + 1, dtype=np.float32) * 5.0
    ref_cm = np.linspace(1.0, 4.0, TOTAL_ROWS + 1, dtype=np.float32)
    ref_fm = np.linspace(1.0, 4.0, TOTAL_ROWS + 1, dtype=np.float32)
    ref_ft = np.linspace(1.0, 3.0, TOTAL_ROWS + 1, dtype=np.float32)
    ref_ff = np.linspace(1.0, 3.0, TOTAL_ROWS + 1, dtype=np.float32)
    return {
        "Perfect Points": ref_pp,
        "Combo Multiplier": ref_cm,
        "Fever Multiplier": ref_fm,
        "Fever Time": ref_ft,
        "Fever Fill Rate": ref_ff,
    }


def main():
    ref_arrays = build_refs()

    # Synthetic song: 120 notes, 0.5s apart
    timestamps = np.arange(120, dtype=np.float32) * 0.5
    calc_song = {
        "metadata": {
            "Song Name": "ParityTest",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {
            "timestamps": timestamps,
        },
    }

    # Base stats (non-zero to exercise gem logic)
    stats = empty_stats()
    stats.update(
        {
            "Perfect Points": 20,
            "Combo Multiplier": 10,
            "Fever Multiplier": 5,
            "Fever Time": 60,
            "Fever Fill Rate": 55,
            "Rush": 80,
            "Flow": 40,
            "Chill": 15,
            "Beat": 25,
            "Vibe": 30,
        }
    )

    selected_color = "Rush"
    total_budget = 90

    override_cfg = {
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "selected_color": selected_color,
        "static_elem_input": 0,
        "use_gpu": False,  # CPU path
    }

    cpu_res = scoring.solve_best_fever_combination(
        cfg=None,
        initial_stats=stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=override_cfg,
    )

    # GPU batch (single item)
    genomes_data = [
        {
            "stats": stats,
            "metadata": calc_song["metadata"],
            "song_data": calc_song["song_data"],
            "song_id": 0,
            "budget": total_budget,
            "selected_color": selected_color,
        }
    ]
    gpu_res = scoring.score_batch_gpu(genomes_data, ref_arrays)[0]

    def fmt(res):
        return {
            "Score": res["Score"],
            "FT": res.get("FT"),
            "FF": res.get("FF"),
            "GemCounts": res.get("GemCounts"),
            "Selected": res.get("Selected Element"),
        }

    print("CPU:", fmt(cpu_res))
    print("GPU:", fmt(gpu_res))

    # Quick diffs
    if cpu_res["Score"] != gpu_res["Score"]:
        print("DIFF: score", gpu_res["Score"] - cpu_res["Score"])
    if cpu_res["FT"] != gpu_res["FT"] or cpu_res["FF"] != gpu_res["FF"]:
        print("DIFF: FT/FF", cpu_res["FT"], cpu_res["FF"], "vs", gpu_res["FT"], gpu_res["FF"])
    if cpu_res["GemCounts"] != gpu_res["GemCounts"]:
        print("DIFF: GemCounts", cpu_res["GemCounts"], "vs", gpu_res["GemCounts"])
    if cpu_res["Selected Element"] != gpu_res["Selected Element"]:
        print("DIFF: Selected", cpu_res["Selected Element"], "vs", gpu_res["Selected Element"])


if __name__ == "__main__":
    main()

