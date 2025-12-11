
import configparser
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.csv_parser import get_fixed_stats
from gear_optimizer.constants import GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE

def test_gem_pollution():
    # Mock Config with default gems
    cfg = configparser.ConfigParser()
    cfg.add_section("UserInputStatsGems")
    cfg.set("UserInputStatsGems", "fever_time", "50") # 50 gems
    cfg.set("UserInputStatsGems", "fever_fill", "0")
    cfg.set("UserInputStatsGems", "perfect_points", "0")
    cfg.set("UserInputStatsGems", "combo_multiplier", "0")
    cfg.set("UserInputStatsGems", "fever_multiplier", "0")
    
    cfg.add_section("ElementalGems")
    cfg.add_section("TeamContributionBuffConstant")
    
    # Calculate fixed stats
    fixed_stats = get_fixed_stats(cfg)
    
    print("Fixed Stats content:")
    for k, v in fixed_stats.items():
        if v > 0:
            print(f"  {k}: {v}")
            
    # Check if Beat has the 50 gems * 3 = 150 points
    expected_beat = 50 * GEM_STAT_TO_ELEMENT_SCALE
    if fixed_stats.get("Beat", 0) >= expected_beat:
        print(f"\n[CONFIRMED] base_stats_fixed INCLUDES default gems (Beat >= {expected_beat})")
        print("GPU Matcher MUST strip these before adding grid search gems, or we double count.")
    else:
        print("\n[DISPROVED] base_stats_fixed is clean.")

if __name__ == "__main__":
    test_gem_pollution()
