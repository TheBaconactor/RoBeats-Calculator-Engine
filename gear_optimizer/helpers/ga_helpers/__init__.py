"""
GA Helpers Package - Genetic Algorithm Helper Functions.

This package splits the monolithic ga_helpers.py (1,368 lines) into 6 focused modules:
1. pool_initialization.py - Gear and mini pool setup with dominance pruning
2. genome_factory.py - Genome creation and manipulation functions
3. evaluation.py - Genome evaluation with caching and parallel processing
4. local_search.py - Hill-climbing local search for genome refinement
5. population.py - Population initialization, crossover, and mutation
6. diversity.py - Diversity metrics and dynamic mutation

This __init__.py provides backward-compatible imports so existing code continues to work.
"""

# Import from pool_initialization
try:
    from .pool_initialization import initialize_pools
except ImportError:
    pass

# Import from genome_factory
try:
    from .genome_factory import create_genome_functions
except ImportError:
    pass

# Import from evaluation
try:
    from .evaluation import (
        create_evaluation_functions,
        evaluate_population_parallel,
    )
except ImportError:
    pass

# Import from local_search
try:
    from .local_search import create_local_search_function
except ImportError:
    pass

# Import from population
try:
    from .population import (
        build_initial_population,
        perform_crossover_mutation,
    )
except ImportError:
    pass

# Import from diversity
try:
    from .diversity import (
        update_mutation_and_diversity,
        compute_dynamic_mutation,
    )
except ImportError:
    pass

# Export all public names for backward compatibility
__all__ = [
    # Pool initialization
    "initialize_pools",
    # Genome factory
    "create_genome_functions",
    # Evaluation
    "create_evaluation_functions",
    "evaluate_population_parallel",
    # Local search
    "create_local_search_function",
    # Population
    "build_initial_population",
    "perform_crossover_mutation",
    # Diversity
    "update_mutation_and_diversity",
    "compute_dynamic_mutation",
]
