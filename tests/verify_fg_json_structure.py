
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.solver.scoring import apply_force_greats_to_result
from gear_optimizer.helpers.song_helpers.persistence import build_persistence_entries

# Mock data
mock_data_dict = {
    "Score": 1000000,
    "Stats": {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
    },
    "GemCounts": {},
    # Mocking what evaluate_force_greats would return
}

# We need to mock evaluate_force_greats or run it.
# Easier to just inspect apply_force_greats_to_result output if we can run it.
# However, running it requires a valid song object + ref arrays.

# Let's try running a test that calls apply_force_greats_to_result and inspect the output.
# Or better, just inspect the diffs again to be sure? No, runtime verification is best.

# Actually, I can rely on test_fg_performance.py but I want to specifically check the structure.
# Let's modify test_fg_performance.py to assert that 'base_score' is NOT in the FG dict.

pass
