"""One-off verification for LiFE Garden T10 Vibe loadout claim."""
from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.config import load_config
from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import load_csv_db, read_table
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact_with_timeline_trace
from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
from gear_optimizer.solver.timing_envelope import apply_timing_envelope

LOG = PROJECT_ROOT / "debug-eb98cb.log"


def dbg(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    entry = {
        "sessionId": "eb98cb",
        "runId": "verify1",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> int:
    gears = load_csv_db(str(PROJECT_ROOT / "Data/Gear/Gears.csv"), "gear")
    minis = load_csv_db(str(PROJECT_ROOT / "Data/Gear/Minis.csv"), "mini")
    mini_names = ["Roxie", "Electroman", "Santa's Helper Marsha"]

    target = {
        "Perfect Points": 343,
        "Combo Multiplier": 72,
        "Fever Multiplier": 73,
        "Fever Fill Rate": 73,
        "Fever Time": 64,
        "Vibe": 523,
        "Rush": 279,
        "Beat": 16,
        "Chill": 35,
        "Flow": 0,
    }
    pre_t10 = {
        "Perfect Points": 323,
        "Vibe": 498,
    }

    def sum_loadout(gear6: list[str]) -> dict[str, int]:
        stats = {k: 0 for k in target}
        for name in gear6:
            gear = gears.get(name) or {}
            for key in stats:
                stats[key] += int(gear.get(key, 0) or 0)
        for name in mini_names:
            mini = minis.get(name) or {}
            for key in stats:
                stats[key] += int(mini.get(key, 0) or 0)
        return stats

    matches: list[tuple[list[str], int, dict[str, int], dict[str, int]]] = []
    for hat in ["Legendary Vibe Ringleader's Cap", "Legendary Rush Chieftan's Hat"]:
        for face in ["Legendary Rush Chieftan's Mask", "Legendary Vibe Ringleader's Harmonica"]:
            for shirt in ["Legendary Vibe Ringleader's Suit", "Legendary Rush Chieftan's Garb"]:
                for back in ["Legendary Rush Chieftan's Aura Band", "Legendary Vibe Ringleader's Band Kit"]:
                    for pants in ["Legendary Rush Chieftan's Pants", "Legendary Vibe Ringleader's Slacks"]:
                        gear6 = [hat, "Legendary Vibe Ringleader's Necktie", face, shirt, back, pants]
                        base = sum_loadout(gear6)
                        stats = copy.deepcopy(base)
                        stats["Fever Multiplier"] += 22 * GEM_SCALE_FEVER
                        stats["Rush"] += 22 * GEM_STAT_TO_ELEMENT_SCALE
                        stats["Fever Fill Rate"] += 22 * GEM_SCALE_FEVER
                        stats["Vibe"] += 22 * GEM_STAT_TO_ELEMENT_SCALE
                        need_vibe = pre_t10["Vibe"] - stats["Vibe"]
                        ov = (need_vibe) // ELEMENTAL_GEM_SCALE
                        if ov < 0 or need_vibe != ov * ELEMENTAL_GEM_SCALE:
                            continue
                        stats["Vibe"] += ov * ELEMENTAL_GEM_SCALE
                        if stats["Perfect Points"] != pre_t10["Perfect Points"]:
                            continue
                        if stats["Rush"] != target["Rush"]:
                            continue
                        stats["Perfect Points"] += team_buff_effect("T10", "Vibe").get("Perfect Points", 0)
                        stats["Vibe"] += team_buff_effect("T10", "Vibe").get("Vibe", 0)
                        if all(stats.get(k, 0) == target.get(k, 0) for k in target):
                            matches.append((gear6, ov, base, stats))

    dbg(
        "H1",
        "verify_life_garden_t10.py",
        "gear_match_search",
        {
            "count": len(matches),
            "first_gear": matches[0][0] if matches else None,
            "element_gems": matches[0][1] if matches else None,
        },
    )

    cfg_dict = cfg_to_dict(load_config())
    calc_song = get_base_calc_song(str(PROJECT_ROOT / "Data/Normal/LiFE Garden by Yooh.txt"), cfg_dict)
    apply_timing_envelope(calc_song)
    ref_arrays = resolve_exact_replay_ref_arrays(read_table(str(PROJECT_ROOT / "Data/Gear/Stats.txt")))
    ensure_ready()
    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)

    exact = score_stats_exact_with_timeline_trace(target, calc_song, ref_arrays)
    dbg(
        "H2",
        "verify_life_garden_t10.py",
        "exact_score_from_ui_stats",
        {
            "score": exact["score"],
            "optimizer_claim": 27_978_785,
            "game_claim": 27_919_541,
            "delta_optimizer": exact["score"] - 27_978_785,
            "delta_game": exact["score"] - 27_919_541,
            "notes": int(calc_song.get("metadata", {}).get("Total Notes", 0) or 0),
        },
    )

    # H3: UI may show Vibe before team buff (605) while scorer applies T10 separately.
    target_prebuff_vibe = dict(target)
    target_prebuff_vibe["Vibe"] = 605
    exact_prebuff = score_stats_exact_with_timeline_trace(target_prebuff_vibe, calc_song, ref_arrays)
    dbg(
        "H3",
        "verify_life_garden_t10.py",
        "exact_score_prebuff_vibe_no_t10_in_stats",
        {"score": exact_prebuff["score"], "vibe": 605},
    )

    # H5: brute-force vibe/rush around UI values to see which reproduces optimizer claim.
    best = None
    for vibe in range(560, 651, 1):
        for rush in range(170, 241, 1):
            trial = dict(target)
            trial["Vibe"] = vibe
            trial["Rush"] = rush
            score = int(
                score_stats_exact_with_timeline_trace(trial, calc_song, ref_arrays)["score"]
            )
            err = abs(score - 27_978_785)
            if best is None or err < best[0]:
                best = (err, score, vibe, rush)
    dbg(
        "H5",
        "verify_life_garden_t10.py",
        "nearest_vibe_rush_to_optimizer_claim",
        {
            "best_err": best[0] if best else None,
            "best_score": best[1] if best else None,
            "best_vibe": best[2] if best else None,
            "best_rush": best[3] if best else None,
        },
    )

    if matches:
        gear_score = score_stats_exact_with_timeline_trace(matches[0][3], calc_song, ref_arrays)
        dbg(
            "H4",
            "verify_life_garden_t10.py",
            "gear_replay_score",
            {
                "score": gear_score["score"],
                "gear": matches[0][0],
                "element_gems": matches[0][1],
                "gem_budget": 22 + 22 + matches[0][1],
            },
        )
        print("gear", matches[0][0])
        print("element_gems", matches[0][1], "total_gems", 22 + 22 + matches[0][1])
        print("gear_replay_score", gear_score["score"])

    # H6: exact-match scoring stats from optimizer claim inversion.
    exact_match_stats = {
        "Perfect Points": 343,
        "Combo Multiplier": 72,
        "Fever Multiplier": 73,
        "Fever Fill Rate": 73,
        "Fever Time": 64,
        "Vibe": 523,
        "Rush": 279,
        "Beat": 16,
        "Chill": 35,
        "Flow": 0,
    }
    exact_match = score_stats_exact_with_timeline_trace(exact_match_stats, calc_song, ref_arrays)
    dbg(
        "H6",
        "verify_life_garden_t10.py",
        "inverted_exact_match_stats",
        {"score": exact_match["score"], "stats": exact_match_stats},
    )
    print("inverted_exact_match_score", exact_match["score"])

    near_game_stats = dict(exact_match_stats)
    near_game_stats["Vibe"] = 526
    near_game_stats["Rush"] = 269
    near_game = score_stats_exact_with_timeline_trace(near_game_stats, calc_song, ref_arrays)
    dbg(
        "H7",
        "verify_life_garden_t10.py",
        "near_user_game_score_stats",
        {"score": near_game["score"], "stats": near_game_stats, "game_claim": 27_919_541},
    )
    print("near_user_game_score", near_game["score"])

    print("matches", len(matches))
    print("exact_score", exact["score"])
    print("optimizer_claim", 27_978_785)
    print("game_claim", 27_919_541)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
