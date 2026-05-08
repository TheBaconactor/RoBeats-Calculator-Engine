"""Deep trace: find the exact mismatch between persisted score and replay."""
import json, sqlite3, sys, math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _unpack_stats_after_load, _force_payload_base_score
from gear_optimizer.pipeline.song_processor import get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact, calculate_score_exact
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.data.db_manager import _build_song_index_for_difficulty
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.solver.scoring_core import lookup_reference_py
from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.utils import safe_int

ref = _get_team_buff_ref_arrays_cached()
diff_idx = {d: _build_song_index_for_difficulty(d) for d in ("Easy", "Normal", "Hard")}
calc_cache = {}

def get_fp(name):
    for d in ("Easy", "Normal", "Hard"):
        marker = f" ({d}) "
        if marker in name:
            fp = PROJECT_ROOT / "Data" / d / f"{name}.txt"
            if fp.exists():
                return str(fp)
            return str(Path(str(diff_idx[d].get(name) or "")))
    return None

cur = sqlite3.connect(str(PROJECT_ROOT / "evolution.db"))
cur.row_factory = sqlite3.Row

# Find first song with a large drift
for r in cur.execute(
    "SELECT song_name, loadout_hash, score, details_json, fg_score "
    "FROM team_buff_loadouts WHERE team_buff='T5' AND details_json IS NOT NULL "
    "ORDER BY random()"
):
    try:
        details_raw = _unpack_stats_after_load(json.loads(r["details_json"]))
    except Exception:
        continue
    stats = details_raw.get("Stats") if isinstance(details_raw, dict) else None
    if not isinstance(stats, dict):
        continue
    fp = get_fp(r["song_name"])
    if not fp:
        continue
    if r["song_name"] not in calc_cache:
        try:
            calc_cache[r["song_name"]] = get_base_calc_song(fp, {})
        except Exception:
            continue
    calc = calc_cache[r["song_name"]]
    per = int(r["score"] or 0)
    rp = int(score_stats_exact(stats, calc, ref))
    d = per - rp
    if abs(d) < 20000:
        continue

    # Found a drifter. Now compare step by step with the exact replay.
    metadata = calc.get("metadata", {}) or {}
    primary = str(metadata.get("Primary Color", "") or "")
    secondary = str(metadata.get("Secondary Color", "") or "")

    pp_raw = safe_int(stats.get("Perfect Points", 0), 0)
    cm_raw = safe_int(stats.get("Combo Multiplier", 0), 0)
    fm_raw = safe_int(stats.get("Fever Multiplier", 0), 0)
    ft_raw = safe_int(stats.get("Fever Time", 0), 0)
    ff_raw = safe_int(stats.get("Fever Fill Rate", 0), 0)
    prim_val = safe_int(stats.get(primary, 0), 0)
    sec_val = safe_int(stats.get(secondary, 0), 0)

    pp_factor = lookup_reference_py(pp_raw, ref["Perfect Points"], TOTAL_ROWS)
    combo_factor = lookup_reference_py(cm_raw, ref["Combo Multiplier"], TOTAL_ROWS)
    fever_factor = lookup_reference_py(fm_raw, ref["Fever Multiplier"], TOTAL_ROWS)
    ft_factor = lookup_reference_py(ft_raw, ref["Fever Time"], TOTAL_ROWS)
    ff_factor = lookup_reference_py(ff_raw, ref["Fever Fill Rate"], TOTAL_ROWS)

    base_value = (prim_val * 2) + sec_val + float(pp_factor)

    print(f"\n=== {r['song_name'][:60]} ===")
    print(f"  Persisted score: {per}  Replay: {rp}  Delta: {d}")
    print(f"  Stats: PP={pp_raw} CM={cm_raw} FM={fm_raw} FT={ft_raw} FF={ff_raw}  {primary}={prim_val} {secondary}={sec_val}")
    print(f"  Ref lookup: PP_factor={pp_factor:.2f} combo={combo_factor:.2f} fever={fever_factor:.2f} ft={ft_factor:.2f} ff={ff_factor:.2f}")
    print(f"  Base value: {base_value:.2f}")
    print(f"  Combo per note: {math.floor(base_value * combo_factor)}  Fever per note: {math.floor(base_value * combo_factor * fever_factor)}")

    # Now check: what does the stored details_json actually contain?
    # Perhaps the Stats were recomputed during persistence and differ from the optimizer's original Stats
    gems = details_raw.get("GemCounts") or details_raw.get("gc") or {}
    if isinstance(gems, list):
        from gear_optimizer.core.gem_defs import GEM_KEYS
        gm = {}
        for i, k in enumerate(GEM_KEYS):
            if i < len(gems):
                gm[k] = int(gems[i] or 0)
        gems = gm

    ft_d = safe_int(details_raw.get("FT", 0), 0)
    ff_d = safe_int(details_raw.get("FF", 0), 0)
    print(f"  Details: FT={ft_d} FF={ff_d}  Gems={gems}")

    # Check the recompute path: did persistence recompute Stats?
    # If Stats differs from base+gems, the replay won't match what the optimizer produced
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
    from gear_optimizer.core.team_buff import team_buff_effect

    # Reconstruct base stats (before gems) backwards from stored Stats
    buff = team_buff_effect("T5", primary or "Rush")
    base_estimate = {}
    for k in stats:
        base_estimate[k] = int(stats.get(k, 0)) - int(buff.get(k, 0))
        if ft_d > 0 or ff_d > 0 or gems.get("Perfect Points", 0) > 0:
            # Rough: gems also affect stats, so this won't perfectly reconstruct
            pass

    # Forward: apply gems to stats without buff to see what would be scored
    stats_no_buff = dict(stats)
    for k in buff:
        if k in stats_no_buff:
            pass  # buff already included in stored stats

    print(f"  Buff: {buff}")
    print(f"  Stored PP already includes buff={pp_raw >= buff.get('Perfect Points',25)}")

    # Check if the score matches when we use the actual optimizer pipeline scoring
    # The key question: does the optimizer pipeline score Stats directly,
    # or does it first compute Stats from base+gems+buff?
    # Pre-refactor: look at the actual scoring call chain in solve_coevolution_genetic

    # Check fg_score column for this row — was FG involved?
    fg_persisted = int(r["fg_score"] or 0)
    if fg_persisted > per:
        print(f"  FG score ({fg_persisted}) > base score ({per}) — FG winner")

    break  # Just trace one

cur.close()
