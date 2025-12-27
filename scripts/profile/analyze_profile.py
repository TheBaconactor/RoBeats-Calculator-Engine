import pstats
import sys

def analyze(filename="profile_main.prof"):
    try:
        with open("analysis.txt", "w") as f:
            # Redirect stdout to file
            original_stdout = sys.stdout
            sys.stdout = f
            
            p = pstats.Stats(filename)
            p.strip_dirs()
            
            print(f"--- ANALYSIS OF {filename} ---")
            print("\nTOP 50 BY CUMULATIVE TIME (Total Duration):")
            p.sort_stats("cumtime").print_stats(50)
            
            print("\nTOP 50 BY TOTAL TIME (Self Duration - Hotspots):")
            p.sort_stats("tottime").print_stats(50)
            
            # Reset stdout
            sys.stdout = original_stdout
            
        print("Analysis written to analysis.txt")
        
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
    except Exception as e:
        print(f"Error analyzing stats: {e}")

if __name__ == "__main__":
    analyze()
