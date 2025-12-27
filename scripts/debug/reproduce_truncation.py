import sys
import os

# Mock logic from process_song_task
LOADOUTS_PER_SONG_LIMIT = 50

# 1. Create mock candidates: 100 total
# Top 50: High base score (1000+), Low FG
# Bottom 50: Low base score (500), High FG (Target)
ga_candidates = []
for i in range(50):
    ga_candidates.append({"Score": 1000 + i, "data": "Filler"})

# The candidates we care about (at the bottom of base score list)
for i in range(50):
    ga_candidates.append({"Score": 500, "data": "Target", "FG_Potential": True})

print(f"Total candidates from GA: {len(ga_candidates)}")

# 2. Simulate the truncation logic in process_song_task
# ga_candidates = sorted(ga_candidates, key=lambda r: r.get("Score", 0), reverse=True)[:LOADOUTS_PER_SONG_LIMIT]

processed_candidates = ga_candidates
if processed_candidates and len(processed_candidates) > LOADOUTS_PER_SONG_LIMIT:
    processed_candidates = sorted(
        processed_candidates,
        key=lambda r: r.get("Score", 0),
        reverse=True,
    )[:LOADOUTS_PER_SONG_LIMIT]

print(f"Candidates after truncation: {len(processed_candidates)}")

# 3. Check if Target survived
targets_found = [c for c in processed_candidates if c.get("FG_Potential")]
print(f"Targets found: {len(targets_found)}")

if len(targets_found) == 0:
    print("FAIL: High FG/Low Base candidates were truncated.")
else:
    print("SUCCESS: Target candidates preserved.")
