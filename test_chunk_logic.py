
def calculate_chunk(n_genomes, n_ftff, target=2_000_000):
    n_work_items = n_genomes * n_ftff
    # Simulate the NEW logic in api.py
    # ratio = TARGET_THREADS_PER_KERNEL // max(1, n_work_items)
    # cfg_chunk = max(1, ratio)
    
    val1 = target // max(1, n_work_items)
    cfg_chunk = max(1, val1)
    
    total_threads = n_work_items * cfg_chunk
    
    print(f"Genomes: {n_genomes}")
    print(f"FT/FF Pairs: {n_ftff}")
    print(f"Work Items: {n_work_items:,}")
    print(f"Target: {target:,}")
    print(f"Calculated Chunk: {cfg_chunk}")
    print(f"Total Threads: {total_threads:,}")
    print(f"Over Target Ratio: {total_threads / target:.2f}x")

print("--- Scenario 1: Single Genome ---")
calculate_chunk(1, 4000)

print("\n--- Scenario 2: 110 Genomes (User case) ---")
calculate_chunk(110, 4000)

print("\n--- Scenario 3: 50 Genomes ---")
calculate_chunk(50, 4000)
