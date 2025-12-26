"""
Test genome reconstruction optimization for correctness and performance.

This ensures the optimized reconstruction produces identical results to the original.
"""
import os
import sys
import numpy as np
import pytest
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockRegistry:
    """Simple mock registry for testing."""
    def __init__(self):
        self.items = []
        # Create test items
        for i in range(15):
            self.items.append({
                "Name": f"TestItem{i}",
                "Type": "Gear" if i < 10 else "Mini",
                "Perfect Points": i * 5,
                "Combo Multiplier": i * 3,
                "Fever Multiplier": i * 4,
                "Fever Time": i * 2,
                "Fever Fill Rate": i * 6,
                "Chill": i,
                "Flow": i,
                "Rush": i,
                "Beat": i,
                "Vibe": i,
            })
    
    def decode_genome(self, genome_ids):
        """Decode genome from indices."""
        return [self.items[idx] for idx in genome_ids]


def create_mock_registry():
    """Create a mock registry with test items."""
    return MockRegistry()


def mock_genome_reconstruction_original(
    scores, results, full_pop_indices, registry, 
    base_stats_fixed, cfg_data, top_indices, limit=50
):
    """
    Original genome reconstruction logic (baseline).
    
    This is the CURRENT implementation from genetic.py:329-409
    """
    SKIP_ITEM_KEYS = {"Name", "Type", "Rarity", "Description"}
    GEM_SCALE_NORMAL = 1
    GEM_SCALE_FEVER = 3
    GEM_STAT_TO_ELEMENT_SCALE = 6
    ELEMENTAL_GEM_SCALE = 6
    
    all_evaluated = []
    
    for idx in top_indices:
        score_val = int(scores[idx])
        if score_val <= 0:
            continue
        
        genome_ids = full_pop_indices[idx]
        genome = registry.decode_genome(genome_ids)
        
        res_row = results[idx]
        g_ft = int(res_row[1])
        g_ff = int(res_row[2])
        g_pp = int(res_row[3])
        g_cm = int(res_row[4])
        g_fm = int(res_row[5])
        g_ov = int(res_row[6])
        
        # SLOW: Dict copy every iteration
        current_stats = base_stats_fixed.copy()
        
        # SLOW: Nested loops with dict operations
        for item in genome:
            for k, v in item.items():
                if k not in SKIP_ITEM_KEYS:
                    current_stats[k] = current_stats.get(k, 0) + v
        
        # SLOW: Many dict.get() calls
        current_stats["Perfect Points"] = current_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
        current_stats["Combo Multiplier"] = current_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
        current_stats["Fever Multiplier"] = current_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
        current_stats["Fever Time"] = current_stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
        current_stats["Fever Fill Rate"] = current_stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER
        current_stats["Chill"] = current_stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
        current_stats["Flow"] = current_stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
        current_stats["Rush"] = current_stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
        current_stats["Beat"] = current_stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
        current_stats["Vibe"] = current_stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE
        
        sel_color = cfg_data.get("selected_color", "")
        if sel_color:
            current_stats[sel_color] = current_stats.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE
        
        cand_data = {
            "Score": score_val,
            "BaseScore": score_val,
            "Genome": genome,
            "Stats": current_stats,
            "GemCounts": {
                "Perfect Points": g_pp,
                "Combo Multiplier": g_cm,
                "Fever Multiplier": g_fm,
                "Element": g_ov,
            }
        }
        all_evaluated.append(cand_data)
        
        if len(all_evaluated) >= limit:
            break
    
    return all_evaluated


def mock_genome_reconstruction_optimized(
    scores, results, full_pop_indices, registry,
    base_stats_fixed, cfg_data, top_indices, limit=50
):
    """
    Optimized genome reconstruction logic (NEW).
    
    This is the PROPOSED implementation with optimizations.
    Preserves original iteration order while optimizing dict operations.
    """
    SKIP_ITEM_KEYS = {"Name", "Type", "Rarity", "Description"}
    GEM_SCALE_NORMAL = 1
    GEM_SCALE_FEVER = 3
    GEM_STAT_TO_ELEMENT_SCALE = 6
    ELEMENTAL_GEM_SCALE = 6
    
    # Optimization 1: Pre-compute base values (once instead of per-iteration)
    base_pp = base_stats_fixed.get("Perfect Points", 0)
    base_cm = base_stats_fixed.get("Combo Multiplier", 0)
    base_fm = base_stats_fixed.get("Fever Multiplier", 0)
    base_ft = base_stats_fixed.get("Fever Time", 0)
    base_ff = base_stats_fixed.get("Fever Fill Rate", 0)
    base_chill = base_stats_fixed.get("Chill", 0)
    base_flow = base_stats_fixed.get("Flow", 0)
    base_rush = base_stats_fixed.get("Rush", 0)
    base_beat = base_stats_fixed.get("Beat", 0)
    base_vibe = base_stats_fixed.get("Vibe", 0)
    
    sel_color = cfg_data.get("selected_color", "")
    
    all_evaluated = []
    
    # Keep original iteration order (don't re-sort!)
    for idx in top_indices:
        score_val = int(scores[idx])
        if score_val <= 0:
            continue
        
        genome = registry.decode_genome(full_pop_indices[idx])
        res_row = results[idx]
        
        g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = (
            int(res_row[1]), int(res_row[2]), int(res_row[3]),
            int(res_row[4]), int(res_row[5]), int(res_row[6])
        )
        
        # Optimization 2: Accumulate item stats efficiently
        item_pp = item_cm = item_fm = item_ft = item_ff = 0
        item_chill = item_flow = item_rush = item_beat = item_vibe = 0
        
        for item in genome:
            item_pp += item.get("Perfect Points", 0)
            item_cm += item.get("Combo Multiplier", 0)
            item_fm += item.get("Fever Multiplier", 0)
            item_ft += item.get("Fever Time", 0)
            item_ff += item.get("Fever Fill Rate", 0)
            item_chill += item.get("Chill", 0)
            item_flow += item.get("Flow", 0)
            item_rush += item.get("Rush", 0)
            item_beat += item.get("Beat", 0)
            item_vibe += item.get("Vibe", 0)
        
        # Optimization 3: Build dict directly (no .copy(), no repeated .get())
        current_stats = {
            "Perfect Points": base_pp + item_pp + g_pp * GEM_SCALE_NORMAL,
            "Combo Multiplier": base_cm + item_cm + g_cm * GEM_SCALE_NORMAL,
            "Fever Multiplier": base_fm + item_fm + g_fm * GEM_SCALE_FEVER,
            "Fever Time": base_ft + item_ft + g_ft * GEM_SCALE_FEVER,
            "Fever Fill Rate": base_ff + item_ff + g_ff * GEM_SCALE_FEVER,
            "Chill": base_chill + item_chill + g_pp * GEM_STAT_TO_ELEMENT_SCALE,
            "Flow": base_flow + item_flow + g_cm * GEM_STAT_TO_ELEMENT_SCALE,
            "Rush": base_rush + item_rush + g_fm * GEM_STAT_TO_ELEMENT_SCALE,
            "Beat": base_beat + item_beat + g_ft * GEM_STAT_TO_ELEMENT_SCALE,
            "Vibe": base_vibe + item_vibe + g_ff * GEM_STAT_TO_ELEMENT_SCALE,
        }
        
        if sel_color:
            # NOTE: This OVERWRITES the value, not adds to it!
            # Original line 102: current_stats[sel_color] = current_stats.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE
            # This gets the COMPUTED value (base + items + gem contrib) and then OVERWRITES it
            current_stats[sel_color] = current_stats[sel_color] + g_ov * ELEMENTAL_GEM_SCALE
        

        cand_data = {
            "Score": score_val,
            "BaseScore": score_val,
            "Genome": genome,
            "Stats": current_stats,
            "GemCounts": {
                "Perfect Points": g_pp,
                "Combo Multiplier": g_cm,
                "Fever Multiplier": g_fm,
                "Element": g_ov,
            }
        }
        all_evaluated.append(cand_data)
        
        if len(all_evaluated) >= limit:
            break
    
    return all_evaluated


@pytest.fixture
def test_data():
    """Create test data for reconstruction."""
    registry = create_mock_registry()
    
    # Create mock population results
    n_genomes = 100
    scores = np.random.randint(-10, 1000, n_genomes)
    
    # Create mock results array (genome_id, g_ft, g_ff, g_pp, g_cm, g_fm, g_ov)
    results = np.zeros((n_genomes, 7), dtype=np.int32)
    results[:, 1:] = np.random.randint(0, 30, (n_genomes, 6))
    
    # Create mock genome indices
    full_pop_indices = np.random.randint(0, 15, (n_genomes, 9), dtype=np.int32)
    
    # Base stats
    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 50,
        "Fever Multiplier": 75,
        "Fever Time": 60,
        "Fever Fill Rate": 80,
        "Chill": 10,
        "Flow": 15,
        "Rush": 20,
        "Beat": 12,
        "Vibe": 18,
    }
    
    cfg_data = {"selected_color": "Rush"}
    
    top_indices = np.arange(n_genomes)
    
    return {
        "registry": registry,
        "scores": scores,
        "results": results,
        "full_pop_indices": full_pop_indices,
        "base_stats_fixed": base_stats,  # Fixed parameter name
        "cfg_data": cfg_data,
        "top_indices": top_indices,
    }


def test_reconstruction_correctness(test_data):
    """Verify optimized version produces identical results to original."""
    # Run both versions
    original = mock_genome_reconstruction_original(**test_data)
    optimized = mock_genome_reconstruction_optimized(**test_data)
    
    # Should produce same number of results
    assert len(original) == len(optimized)
    
    # Compare each result
    for i, (orig, opt) in enumerate(zip(original, optimized)):
        assert orig["Score"] == opt["Score"], f"Score mismatch at {i}"
        assert orig["BaseScore"] == opt["BaseScore"], f"BaseScore mismatch at {i}"
        
        # Compare stats dicts
        for key in orig["Stats"]:
            assert orig["Stats"][key] == opt["Stats"][key], \
                f"Stats['{key}'] mismatch at {i}: {orig['Stats'][key]} != {opt['Stats'][key]}"
        
        # Compare gem counts
        for key in orig["GemCounts"]:
            assert orig["GemCounts"][key] == opt["GemCounts"][key], \
                f"GemCounts['{key}'] mismatch at {i}"


def test_reconstruction_performance(test_data):
    """Benchmark performance improvement."""
    
    # Run manually to compare (pytest-benchmark would be better)
    import time
    
    # Warm up caches/JIT and reduce first-run noise
    for _ in range(10):
        mock_genome_reconstruction_original(**test_data)
        mock_genome_reconstruction_optimized(**test_data)

    def _time(fn, loops: int, repeats: int = 5) -> float:
        samples = []
        for _ in range(repeats):
            start = time.perf_counter()
            for _ in range(loops):
                fn(**test_data)
            samples.append(time.perf_counter() - start)
        samples.sort()
        return samples[len(samples) // 2]  # median

    # Original timing
    orig_time = _time(mock_genome_reconstruction_original, loops=100)
    
    # Optimized timing  
    opt_time = _time(mock_genome_reconstruction_optimized, loops=100)
    
    speedup = orig_time / opt_time
    print(f"\n  Original: {orig_time*1000:.2f}ms")
    print(f"  Optimized: {opt_time*1000:.2f}ms")
    print(f"  Speedup: {speedup:.2f}x")
    
    # Performance thresholds are inherently environment-dependent; enforce that
    # the optimized path is meaningfully faster without flaking under load.
    assert opt_time <= orig_time * 0.95, (
        f"Expected optimized to be at least ~5% faster, got {speedup:.2f}x"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
