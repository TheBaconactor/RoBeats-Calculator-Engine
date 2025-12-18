
import os
import sys

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
    target = r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\Data\Normal\00 by garlagan.txt"
    if os.path.exists(target):
        count_note_types(target)
    else:
        print("File not found.")
