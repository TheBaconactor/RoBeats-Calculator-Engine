
import sys
import os
import json
import sqlite3
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries, build_db_payload
from gear_optimizer.data.database import get_db_connection, get_evolution_db_path, init_db

# 1. Initialize DB (User cleared it, so likely need to ensure tables exist or just connect)
db_path = get_evolution_db_path()
init_db() # Ensure schema exists
conn = get_db_connection(db_path)

print(f"Database: {db_path}")

# 2. Mock Data representing a result with Force Greats
# This simulates what comes out of the solver after my changes
mock_fg_info = {
    "enabled": True,
    "algo_version": 3,
    "config": {"NonFever1": 15},
    "final_score": 900000, # Penalized
    "score_penalty": 100000,
    "fill_penalty": 0,
    "total_penalty": 100000,
    # base_score IS MISSING HERE (as per my change)
}

mock_variant = {
    "Score": 900000, # Penalized score
    "BaseScore": 1000000, # Original Base Score (Unpenalized)
    "Stats": {"Perfect Points": 100},
    "GemCounts": {},
    "FT": 0, "FF": 0,
    "ForceGreats": {**mock_fg_info, "variant_applied": True}
}

mock_gear = [{"Name": "Headphones"}]
mock_minis = [{"Name": "Mini1"}]

def mock_build_details(data):
    return data  # Just return data as details

# 3. Build DB Persistence Payload
# This exercises the modified persistence.py logic
payload = build_db_payload(
    best_data=mock_variant, # Use the FG variant as the "Best" result
    best_gear=mock_gear,
    best_minis=mock_minis,
    prev_record=None, # First run
    attempt_lifetime=1,
    prev_attempts_first=0,
    fg_variants=[{
        "score": 900000, 
        "gear": mock_gear, 
        "minis": mock_minis, 
        "data": mock_variant
    }],
    build_details_fn=mock_build_details
)

entries = build_persistence_entries(
    db_payload=payload,
    ga_candidates=[],
    loadout_entries=None,
    build_details_fn=mock_build_details
)

# 4. Insert into DB manually to mimic saving
song_name = "Ice Angel (Easy)"
cursor = conn.cursor()

# We need to insert into 'songs' and 'loadouts'
# Update songs table
best_score = 0
best_fg_score = 0

for entry in entries:
    score = entry['score']
    fg_score = entry['fg_score']
    force_json = json.dumps(entry['force']) if entry['force'] else None
    details_json = json.dumps(entry['details'])
    
    # Simple insert
    cursor.execute("""
        INSERT INTO loadouts (song_name, score, fg_score, force_details_json, details_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (song_name, score, fg_score, force_json, details_json, 123456789))
    
    if score > best_score: best_score = score
    if fg_score > best_fg_score: best_fg_score = fg_score

# Update songs table
cursor.execute("""
    INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated)
    VALUES (?, ?, ?, ?)
""", (song_name, best_score, best_fg_score, 123456789))

conn.commit()

# 5. Verify
print("\n=== VERIFICATION ===")
cursor.execute("SELECT * FROM loadouts WHERE song_name=?", (song_name,))
row = cursor.fetchone()
if row:
    print(f"Row Score (Base): {row['score']}")
    print(f"Row FG Score: {row['fg_score']}")
    print(f"Row Force Details: {row['force_details_json']}")
    
    if row['force_details_json']:
        fd = json.loads(row['force_details_json'])
        if 'ForceGreats' in fd:
            fg = fd['ForceGreats']
            if 'base_score' in fg:
                print("❌ FAIL: base_score found in ForceGreats JSON!")
            else:
                print("✅ PASS: base_score NOT found in ForceGreats JSON.")
        else:
             # It might be flat if I mocked it that way? No, persistence uses 'force' object.
             # Wait, persistence uses the 'force' object which is usually the 'details' dict from the FG variant?
             # No, details is separate.
             # In persistence: `updated_payload["force"] = { ... "details": matching_fg.get("details", {}) }`
             # So the stored JSON is the 'details' dict of the FG mock.
             # My mock details IS the mock_variant data.
             # So it should contain 'ForceGreats'.
             if 'base_score' in fd: # Check top level too just in case
                  print("❌ FAIL: base_score found in root JSON!")
             pass

    # Check Score Column Value
    # Should be 1,000,000 (Base) NOT 900,000 (Penalized)
    if row['score'] == 1000000:
        print("✅ PASS: Score column contains Unpenalized Base Score (1,000,000)")
    else:
        print(f"❌ FAIL: Score column contains {row['score']} (Expected 1,000,000)")

conn.close()
