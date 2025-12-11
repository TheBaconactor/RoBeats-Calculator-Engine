
import sys
import os
import configparser

sys.path.append(os.getcwd())

from gear_optimizer.config import RunConfig
from gear_optimizer.utils import cfg_to_dict, cfg_from_dict

def main():
    print("--- Debugging Auto Buff Config ---")
    
    # 1. Read Raw Config
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")
    
    raw_val = cfg.get("IterationEngine", "AutoSelectBuffAndColor", fallback="NOT FOUND")
    print(f"Raw Config Value: '{raw_val}'")
    
    # 2. Parse via RunConfig
    run_config = RunConfig.from_cfg(cfg)
    print(f"RunConfig.auto_buff: {run_config.auto_buff}")
    
    if not run_config.auto_buff:
        print("\n[FAILURE] AutoBuff is FALSE despite being set in INI (if printed TRUE above).")
        print("Possible causes: Section mismatch, boolean parsing error.")
    else:
        print("\n[SUCCESS] AutoBuff is defined and parsed as TRUE.")
        
    # 3. Check Section Existence
    if not cfg.has_section("IterationEngine"):
        print("[ERROR] 'IterationEngine' section missing in config object!")
        
    # print(f"Sections found: {cfg.sections()}") # Noisy

if __name__ == "__main__":
    main()
