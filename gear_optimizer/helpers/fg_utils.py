def generate_dynamic_fg_configs(num_sections, non_fever_base, budget=4096):
    """
    Generate a list of FG configs that fits within a global budget.
    Tapers search depth for later sections.
    Matches user preference for approx "25, 15, 8" profile.
    
    Args:
        num_sections: Number of non-fever sections
        non_fever_base: Notes in non-fever section (baseline max)
        budget: Max number of configs to generate (default 4096)
        
    Returns:
        List of tuples, e.g. [(0,), (1,), ...] or [(0,0), (0,1)...]
    """
    if num_sections <= 0:
        return []

    # --- Geometric Decay Strategy ---
    # Tapers search depth for later sections.
    # Matches user preference for approx "25, 15, 8" profile.
    # Cap[i] = Unit * (Decay ^ i)
    # Total Configs = Product(Cap[i]) <= Budget
    
    decay = 0.6
    
    # 1. Calculate 'Unit' base size by solving: Product(Unit * decay^i) = Budget
    # Product = Unit^N * decay^(0+1+...N-1) = Budget
    # Unit^N * decay^(N*(N-1)/2) = Budget
    # Unit = (Budget / decay^(sum_powers)) ^ (1/N)
    
    sum_powers = (num_sections * (num_sections - 1)) / 2
    decay_term = decay ** sum_powers
    
    unit_base = (budget / decay_term) ** (1.0 / num_sections)
    
    caps = []
    actual_base = int(non_fever_base or 0)
    
    for i in range(num_sections):
        # Calculate raw varied cap
        raw_val = unit_base * (decay ** i)
        
        # Soft cap for Section 1 (don't go insane)
        if i == 0:
            raw_val = min(raw_val, 100)
            
        val = int(raw_val)
        
        # Hard cap by available notes
        effective = min(actual_base, val)
        caps.append(effective)

    # Generate ranges
    import itertools
    ranges = [range(c + 1) for c in caps]
    
    # Generate all combinations
    return list(itertools.product(*ranges))
