def generate_dynamic_fg_configs(num_sections, non_fever_base, budget=None):
    """
    Generate a list of FG configs with explicit caps per section.
    
    Args:
        num_sections: Number of non-fever sections
        non_fever_base: Notes in non-fever section (hard cap by available notes)
        budget: Ignored (kept for API compatibility)
        
    Returns:
        List of tuples, e.g. [(0,), (1,), ...] or [(0,0), (0,1)...]
    """
    if num_sections <= 0:
        return []

    # Explicit caps per section (user preference: 50, 35, 15, ...)
    SECTION_CAPS = [50, 35, 15, 10, 8, 6, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4]
    
    caps = []
    actual_base = int(non_fever_base or 0)
    
    for i in range(num_sections):
        # Get explicit cap for this section (or use fallback for sections beyond list)
        explicit_cap = SECTION_CAPS[i] if i < len(SECTION_CAPS) else 4
        
        # Hard cap by available notes
        effective = min(actual_base, explicit_cap)
        caps.append(effective)

    # Generate ranges
    import itertools
    ranges = [range(c + 1) for c in caps]
    
    # Generate all combinations
    return list(itertools.product(*ranges))

