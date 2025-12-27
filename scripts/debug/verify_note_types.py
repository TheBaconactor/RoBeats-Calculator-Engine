import argparse
import os
from pathlib import Path

def count_note_types(filepath):
    print(f"Scanning {filepath}...")
    type_counts = {}
    total_lines = 0
    in_data = False
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line == "Song Data":
                in_data = True
                continue
            if not in_data:
                continue
            if not line:
                continue
            
            # Assuming format: Time ID Lane Type
            parts = line.split('\t')
            if len(parts) >= 4:
                try:
                    t = int(parts[3])
                    type_counts[t] = type_counts.get(t, 0) + 1
                    total_lines += 1
                except ValueError:
                    pass
            elif len(parts) >= 2:
                 # Some formats might differ
                 pass

    print(f"Total Note Lines: {total_lines}")
    print("Type Counts:")
    for t in sorted(type_counts.keys()):
        print(f"Type {t}: {type_counts[t]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count note types in a RoBeats song .txt file.")
    parser.add_argument("song_file", nargs="?", help="Path to song .txt (defaults to first file under Data/Normal)")
    args = parser.parse_args()

    target: Path | None
    if args.song_file:
        target = Path(args.song_file)
    else:
        repo_root = Path(__file__).resolve().parents[2]
        data_root = repo_root / "Data" / "Normal"
        try:
            target = next(data_root.rglob("*.txt"), None) if data_root.exists() else None
        except Exception:
            target = None

    if target and target.exists():
        count_note_types(str(target))
    else:
        print("File not found. Provide a path like: python scripts/debug/verify_note_types.py Data/Normal/<song>.txt")
