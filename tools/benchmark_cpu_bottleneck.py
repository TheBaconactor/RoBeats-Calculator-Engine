
import time
import random
import cProfile
import pstats
from io import StringIO

# Mock constants
GA_POPULATION_SIZE = 2000
SKIP_ITEM_KEYS = {"Name", "type", "rarity", "id"}

# Mock Gear Item
def create_mock_item(name):
    return {
        "Name": name,
        "type": "Hat",
        "Perfect Points": 10,
        "Combo Multiplier": 2,
        "Fever Multiplier": 5,
        "Rush": 20,
        "Chill": 10,
        "Flow": 0,
        "Beat": 5,
        "Vibe": 0,
        "Fever Time": 1,
        "Fever Fill Rate": 1
    }

def main():
    print("Preparing mock data...")
    # Create a population of 2000 genomes (each 9 items)
    population = []
    for i in range(GA_POPULATION_SIZE):
        genome = [create_mock_item(f"Item_{j}") for j in range(9)]
        population.append(genome)

    print(f"Population size: {len(population)}")
    
    base_stats_fixed = {
        "Perfect Points": 100,
        "Combo Multiplier": 200,
        "Fever Multiplier": 150,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
        "Rush": 0, "Chill": 0, "Flow": 0, "Beat": 0, "Vibe": 0
    }

    print("\n--- Benchmarking Stat Aggregation ---")
    start_time = time.perf_counter()
    
    # Simulate the loop in evaluate_population_parallel
    for _ in range(5): # Run 5 generations to get average
        keys_to_calc = population # All need calc
        
        pr = cProfile.Profile()
        pr.enable()
        
        batch_payloads = []
        for genome in keys_to_calc:
            current_stats = base_stats_fixed.copy()
            cs = current_stats
            cs_get = cs.get
            for item in genome:
                for k, v in item.items():
                    if k not in SKIP_ITEM_KEYS:
                        cs[k] = cs_get(k, 0) + v
            # Mock payload creation
            batch_payloads.append({})
            
        pr.disable()
        
    end_time = time.perf_counter()
    avg_time = (end_time - start_time) / 5.0
    print(f"Average time per generation (Aggregation only): {avg_time:.4f}s")
    
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())

    print("\n--- Benchmarking Population Build (Mock) ---")
    # Simulate build_initial_population cost
    start_time = time.perf_counter()
    new_pop = []
    # Create random genomes
    for _ in range(GA_POPULATION_SIZE):
        g = [create_mock_item("Random") for _ in range(9)] # Allocating lists/dicts
        new_pop.append(g)
    end_time = time.perf_counter()
    print(f"Time to build population: {end_time - start_time:.4f}s")

if __name__ == "__main__":
    main()
