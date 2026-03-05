import pstats
import sys


def analyze(prof_file):
    p = pstats.Stats(prof_file)
    p.strip_dirs()
    p.sort_stats("cumulative")
    print("=== TOP CUMULATIVE TIME ===")
    p.print_stats(30)

    print("\n=== TOP SELF TIME ===")
    p.sort_stats("time")
    p.print_stats(30)

    print("\n=== FORCE GREATS SPECIFIC ===")
    p.sort_stats("cumulative")
    p.print_stats("force_greats")

    print("\n=== FG CALLEES (What is FG spending time on?) ===")
    p.print_callees("solve_force_greats_finder_gpu")

    print("\n=== GA CALLEES (What is GA spending time on?) ===")
    p.print_callees("solve_genomes_with_ftff")


if __name__ == "__main__":
    analyze("main_opt.prof")
