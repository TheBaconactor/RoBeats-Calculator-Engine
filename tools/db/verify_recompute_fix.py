"""Verify the fix: prove old code would corrupt Stats on persistence."""
import json, os, sys, tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import init_db, save_loadouts_batch, get_db_connection, _unpack_stats_after_load
from gear_optimizer.core.team_buff import team_buff_effect

db_dir = tempfile.mkdtemp()
db_path = os.path.join(db_dir, "test.db")
os.environ["EVOLUTION_DB_PATH"] = db_path
init_db()

original_stats = {
    "Perfect Points": 47, "Combo Multiplier": 60, "Fever Multiplier": 77,
    "Fever Fill Rate": 42, "Fever Time": 36, "Flow": 200, "Rush": 400,
}
details = {
    "FT": 0, "FF": 0,
    "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 11, "Element": 63},
    "Stats": dict(original_stats),
    "SelectedElement": "Rush", "PrimaryColor": "Rush", "SecondaryColor": "Flow", "Difficulty": "Hard",
}

save_loadouts_batch("fix_verify", [
    {"score": 5000, "fg_score": 0, "gear": ["G1","G2","G3","G4","G5","G6"],
     "minis": ["M1","M2","M3"], "details": dict(details), "force": None},
])

conn = get_db_connection(db_path)
conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
row = conn.execute(
    "SELECT details_json FROM team_buff_loadouts WHERE song_name=?", ("fix_verify",)
).fetchone()
stored = _unpack_stats_after_load(json.loads(row["details_json"]))
stored_stats = stored.get("Stats", {})

all_ok = True
for k in sorted(original_stats):
    o = original_stats[k]
    s = stored_stats.get(k)
    ok = o == s
    status = "OK" if ok else "CORRUPTED"
    if not ok:
        all_ok = False
    print(f"  {k:25s}  original={o:>5}  stored={s:>5}  [{status}]")

print(f"\nAll Stats preserved: {all_ok}")

# Now show what the OLD code path would have done
# The old code called _recompute_stats_in_details_for_persistence on every write
# when can_recompute was true, even when Stats were already valid.
# That recompute path uses compute_full_stats which can produce different results
# due to mini equivalence group canonicalization and TeamBuff layering differences.

# Load the old version from git to compare
import subprocess
result = subprocess.run(
    ["git", "show", "2838c91a:gear_optimizer/data/database.py"],
    capture_output=True, text=True, cwd=str(PROJECT_ROOT),
)
old_code = result.stdout

# Extract the _recompute_stats_in_details_for_persistence function from old code
start = old_code.find("def _recompute_stats_in_details_for_persistence")
end = old_code.find("\ndef ", start + 1)
if end == -1:
    end = len(old_code)
func_code = old_code[start:end]

# Execute the old function
old_ns = {}
exec(func_code, old_ns)
old_recompute = old_ns["_recompute_stats_in_details_for_persistence"]

recomputed = old_recompute(
    dict(details), gear_names_local=["G1","G2","G3","G4","G5","G6"],
    mini_names_local=["M1","M2","M3"], team_color="Rush",
)
recomp_stats = recomputed.get("Stats", {})

print("\n--- What OLD CODE would have stored ---")
any_diff = False
for k in sorted(original_stats):
    o = original_stats[k]
    r = recomp_stats.get(k, "???")
    diff = o != r
    if diff:
        any_diff = True
        status = f"DIFFERS by {r - o:+d}" if isinstance(r, int) else "MISSING"
    else:
        status = "OK"
    print(f"  {k:25s}  original={o:>5}  recomputed={str(r):>10}  [{status}]")

print(f"\nOld code would corrupt Stats: {any_diff}")
print(f"Verdict: {'REGRESSION FIXED' if all_ok and any_diff else 'NEEDS MORE INVESTIGATION'}")

conn.close()
