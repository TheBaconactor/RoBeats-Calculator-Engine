def generate_dynamic_fg_configs(num_sections, non_fever_base, budget=None, gap=None, fever_activations=None):
    """
    Generate a list of FG configs with dynamic caps based on gap.
    
    Uses gap (total_notes - last_fever_end) to limit search space:
    - If gap <= 0: no opportunity (overshoot or at end), return [(0,0,...)] only
    - Otherwise: cap each section by gap (no need to overshoot)
    - Sections beyond fever_activations get cap=0 (no benefit)
    
    Args:
        num_sections: Number of non-fever sections
        non_fever_base: Notes in non-fever section (hard cap by available notes)
        budget: Ignored (kept for API compatibility)
        gap: Gap value (total_notes - last_fever_end). Required for optimal capping.
        fever_activations: Count of fever windows. Sections beyond this get cap=0.
        
    Returns:
        List of tuples, e.g. [(0,), (1,), ...] or [(0,0), (0,1)...]
    """
    if num_sections <= 0:
        return []

    # Hard cap fallbacks to prevent config explosion
    # Section 1 can have more FG than section 2, etc. (diminishing returns)
    MAX_SECTION_CAPS = [50, 30, 15, 10, 8, 6, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4]
    
    caps = []
    actual_base = int(non_fever_base or 0)
    
    # If gap is provided and <= 0, no opportunity - return zero config only
    if gap is not None and gap <= 0:
        return [tuple([0] * num_sections)]
    
    # Compute caps per section
    for i in range(num_sections):
        # Sections beyond fever_activations get cap=0 (no benefit from FG there)
        if fever_activations is not None and i >= fever_activations:
            caps.append(0)
            continue
        
        # Get hard cap for this section (diminishing per section)
        hard_cap = MAX_SECTION_CAPS[i] if i < len(MAX_SECTION_CAPS) else 4
        
        # Dynamic cap based on gap (no need to shift more than gap)
        if gap is not None:
            effective = min(actual_base, gap, hard_cap)
        else:
            # Fallback if gap not provided - use hard cap
            effective = min(actual_base, hard_cap)
        
        caps.append(effective)

    # Generate ranges
    import itertools
    ranges = [range(c + 1) for c in caps]
    
    # Generate all combinations
    return list(itertools.product(*ranges))

