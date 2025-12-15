import random


def create_genome_functions(
    gear_pool,
    mini_pool,
    gear_rank_cache,
    mini_rank_cache,
    gears_by_name,
    minis_by_name,
    slots,
    optimize_gear,
    optimize_minis,
    fixed_gear,
    fixed_minis,
):
    """
    Create genome factory and manipulation functions.

    Returns closures for creating random/heuristic genomes, reconstructing from DB,
    building seed lists, and mutating genomes.

    Args:
        gear_pool: Dict mapping slot names to gear lists
        mini_pool: List of valid minis
        gear_rank_cache: Dict mapping slots to ranked gear lists
        mini_rank_cache: Ranked list of minis
        gears_by_name: Dict mapping gear names to gear objects
        minis_by_name: Dict mapping mini names to mini objects
        slots: List of gear slot names
        optimize_gear: Whether to optimize gear
        optimize_minis: Whether to optimize minis
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing

    Returns:
        tuple: (create_random_genome, create_heuristic_genome,
                reconstruct_genome_from_db_list, build_seed_list_from_record,
                mutate_genome_once)
    """

    def create_random_genome():
        """Create a random genome from available pools."""
        genome = []
        if optimize_gear:
            for s in slots:
                genome.append(random.choice(gear_pool[s]) if gear_pool[s] else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_pool) >= 3:
                genome.extend(random.sample(mini_pool, 3))
            else:
                genome.extend(random.sample(mini_pool, len(mini_pool)))
                while len(genome) < 9:
                    genome.append({})
        else:
            genome.extend(fixed_minis)
        return genome

    def create_heuristic_genome():
        """Create a genome biased toward high-ranked items."""
        genome = []
        if optimize_gear:
            for s in slots:
                candidates = gear_rank_cache.get(s, [])
                genome.append(random.choice(candidates[:5]) if candidates else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            # Widen sampling from top 10 to top 25 to improve diversity
            # while still biasing toward high-scoring minis.
            # This helps discover synergistic combinations that don't rank
            # highest individually but score well together.
            sample_pool = mini_rank_cache[:25] if len(mini_rank_cache) >= 25 else mini_rank_cache
            if len(sample_pool) >= 3:
                genome.extend(random.sample(sample_pool, 3))
            else:
                genome.extend(random.sample(mini_pool, 3))
        else:
            genome.extend(fixed_minis)
        return genome

    def reconstruct_genome_from_db_list(db_list):
        """Rebuild full stats from just the names in the DB."""
        r_genome = []
        for i in range(6):
            name = db_list[i] if i < len(db_list) else ""
            if name in gears_by_name:
                r_genome.append(gears_by_name[name])
            else:
                r_genome.append({"Name": "(Empty)", "type": slots[i]})
        for i in range(6, 9):
            if i < len(db_list):
                name = db_list[i]
                if name in minis_by_name:
                    r_genome.append(minis_by_name[name])
                else:
                    r_genome.append({"Name": "(Empty)", "type": "Mini"})
            else:
                r_genome.append({"Name": "(Empty)", "type": "Mini"})
        return r_genome

    def build_seed_list_from_record(record):
        """
        Normalize any stored record into a compact list of names for seeding.
        Handles both dict format (with 'Name' key) and plain string names.
        Priority: legacy loadout -> gear + minis.
        """
        if not record:
            return None

        def extract_name(item):
            """Extract name from either a dict or string."""
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""

        if "loadout" in record:
            load = record.get("loadout") or []
            if isinstance(load, list):
                return [extract_name(item) for item in load]

        gear_items = record.get("gear") or []
        mini_items = record.get("minis") or []

        if gear_items or mini_items:
            gear_names = [extract_name(g) for g in gear_items]
            mini_names = [extract_name(m) for m in mini_items]
            return gear_names + mini_names
        return None

    def mutate_genome_once(genome):
        """Soft mutation around a seed genome for DB seeding."""
        g = list(genome)
        mutate_idx = random.randint(0, 8)

        if mutate_idx < 6 and optimize_gear:
            slot_type = slots[mutate_idx]
            if gear_pool[slot_type]:
                g[mutate_idx] = random.choice(gear_pool[slot_type])
        elif mutate_idx >= 6 and optimize_minis:
            # Extract current mini names, handling both dict and string formats
            current_mini_names = set()
            for m in g[6:]:
                if isinstance(m, dict):
                    current_mini_names.add(m.get("Name", ""))
                elif m:
                    current_mini_names.add(str(m))
            candidates = [m for m in mini_pool if m["Name"] not in current_mini_names]
            if candidates:
                g[mutate_idx] = random.choice(candidates)

        return g

    return (
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
    )


