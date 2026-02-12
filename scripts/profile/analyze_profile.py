import pstats
import sys


def analyze(filename="profile_main.prof"):
    original_stdout = sys.stdout
    try:
        with open("analysis.txt", "w") as f:
            # Redirect stdout to file while rendering stats.
            sys.stdout = f

            p = pstats.Stats(filename)
            p.strip_dirs()

            print(f"--- ANALYSIS OF {filename} ---")
            print("\nTOP 50 BY CUMULATIVE TIME (Total Duration):")
            p.sort_stats("cumtime").print_stats(50)

            print("\nTOP 50 BY TOTAL TIME (Self Duration - Hotspots):")
            p.sort_stats("tottime").print_stats(50)

        sys.stdout = original_stdout
        print("Analysis written to analysis.txt")
        return True

    except FileNotFoundError:
        sys.stdout = original_stdout
        print(f"Error: {filename} not found.")
        return False
    except Exception as e:
        sys.stdout = original_stdout
        print(f"Error analyzing stats: {e}")
        return False
    finally:
        sys.stdout = original_stdout


if __name__ == "__main__":
    analyze()
