"""Score the frontend-authoritative stats to isolate scoring vs search bugs."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gear_optimizer.core.config import load_config
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact
from gear_optimizer.solver.scoring_core import fast_calculate_score
from gear_optimizer.pipeline.song_processor import get_base_calc_song, clone_calc_song

cfg = load_config("config.ini")
cfg_dict = cfg_to_dict(cfg)
paths = {}

calc_song = get_base_calc_song("Data/Hard/00 (Hard) by garlagan.txt", cfg_dict)
calc_song = clone_calc_song(calc_song)

# Frontend-authoritative stats (with T5 Rush buff, 90 gems)
# PP=386 means 27 from gear/minis + 359... no wait:
# Frontend shows "27 + 25" for PP = 386 total. That's 386 total PP.
# FM=13 gems, FF=18 gems, FT=1 gem, Rush++=58 gems = 90 total
stats = {
    "Perfect Points": 386,
    "Combo Multiplier": 66,
    "Fever Multiplier": 74,
    "Fever Time": 31,
    "Fever Fill Rate": 61,
    "Rush": 733,
    "Chill": 0,
    "Vibe": 115,
    "Beat": 18,
    "Flow": 0,
}

print("Frontend-authoritative stats:", json.dumps(stats, indent=2))

# Build ref_arrays from stats table
stats_table = read_table(str(paths.get("Stats", "") or ""))
from gear_optimizer.core.constants import TOTAL_ROWS
import numpy as np
stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
ref_arrays = {}
for i, name in enumerate(stat_names):
    tmp = []
    for v in range(int(TOTAL_ROWS) + 1):
        lookup_index = int(TOTAL_ROWS) - int(v)
        try:
            val = float(stats_table[lookup_index][i]) if stats_table else 0.0
        except Exception:
            val = 0.0
        tmp.append(val)
    ref_arrays[name] = np.asarray(tmp, dtype=np.float32)

score = score_stats_exact(stats, calc_song, ref_arrays)
print(f"\nExact score: {score:,}")
print(f"Frontend claims: 34,253,930")
print(f"Delta: {34_253_930 - score:+,}")
