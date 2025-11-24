#!/usr/bin/env python
import os
import sys
import json
from pathlib import Path
from collections import deque

BIN_DIR = Path("bin")
CACHE_FILE = BIN_DIR / "paths_cache.json"
BUILD_DIR = Path("bin/build")
PROJECT_ROOT = Path(__file__).resolve().parent

def save_cache(data):
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(f"Cache load warning: {exc}")
    return {}


# Updated find_locations function: now it starts scanning from the parent directory of PROJECT_ROOT.
def find_locations():
    results = {k: "" for k in ["Easy", "Normal", "Hard", "Gear", "Stats"]}
    targets_dirs = set(["Easy", "Normal", "Hard"])
    targets_files = set(["Gear.csv", "Stats.txt"])
    # Start scanning from the parent directory so that sibling folders (and their subdirectories) are included.
    base_dir = PROJECT_ROOT.parent if PROJECT_ROOT.parent != PROJECT_ROOT else PROJECT_ROOT
    queue = deque([base_dir])
    visited = {str(base_dir.resolve())}
    while queue and (targets_dirs or targets_files):
        curr = queue.popleft()
        try:
            for entry in os.scandir(curr):
                try:
                    p = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in targets_dirs:
                            results[entry.name] = str(p.resolve())
                            targets_dirs.remove(entry.name)
                        if str(p.resolve()) not in visited:
                            visited.add(str(p.resolve()))
                            queue.append(p)
                    elif entry.is_file(follow_symlinks=False):
                        if entry.name in targets_files:
                            key = entry.name.split('.')[0]
                            results[key] = str(p.resolve())
                            targets_files.remove(entry.name)
                    if not targets_dirs and not targets_files:
                        break
                except Exception:
                    continue
        except Exception:
            continue
    return results

# Updated file_format_ok function: reads line-by-line (stripping BOM and extra spaces)
def file_format_ok(p):
    reqs = ["Song Name", "Difficulty", "Primary Color", "Secondary Color", "Last Note Time", "Total Notes", "Fever Fill", "Fever Time", "Long Notes"]
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        lines = [line.lstrip('\ufeff').strip() for line in lines if line.strip()]
        return all(any(line.startswith(r) for line in lines) for r in reqs)
    except Exception:
        return False

def parse_song(p):
    fields = ["Song Name", "Difficulty", "Primary Color", "Secondary Color", "Last Note Time", "Total Notes", "Fever Fill", "Fever Time", "Long Notes"]
    res = {f: "0" for f in fields}
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                for field in fields:
                    if line.startswith(field):
                        res[field] = line[len(field):].strip(" :\t")
                        break
    except Exception:
        pass
    return res

# Updated formatting function: outputs tab-separated values (TSV)
def fmt_table(hdr, rows):
    lines = []
    lines.append("\t".join(str(x) for x in hdr))
    for r in rows:
        lines.append("\t".join(str(x) for x in r))
    return "\n".join(lines)

def build_songs_list(key, folder_path, build_folder, cache):
    marker = build_folder / f".songs_build_{key}.done"
    if marker.exists():
        print(f"Songs build for '{key}' already done.")
        return
    txts = list(Path(folder_path).glob("*.txt"))
    rows = []
    # Updated header: the extra "Link" column has been removed.
    hdr = ["Difficulty", "Song Name", "Primary Color", "Secondary Color", "Total Notes", "Last Note Time", "Fever Fill", "Fever Time", "Long Notes"]
    for txt in txts:
        if not file_format_ok(txt):
            print(f"Skipping {txt} (format issue).")
            continue
        info = parse_song(txt)
        if info["Song Name"] == "???" or info["Difficulty"] == "???":
            print(f"Skipping {txt} (missing fields).")
            continue
        # Build row without the Link column.
        rows.append([info['Difficulty'], info['Song Name'], info['Primary Color'], info['Secondary Color'],
                     info['Total Notes'], info['Last Note Time'], info['Fever Fill'], info['Fever Time'], info['Long Notes']])
    if len(rows) < 25:
        print(f"Not enough valid files in '{folder_path}' for key '{key}'.")
        return
    table = fmt_table(hdr, rows)
    build_file = build_folder / f"Songs_Optimizer_Build_{key}.txt"
    with build_file.open("w", encoding="utf-8") as f:
        f.write(table + "\n")
    print(f"Built {build_file} with {len(rows)} entries.")
    cache[f"Build_{key}"] = str(build_file.resolve())
    marker.touch()

def build_all_songs(cache):
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for k in ["Easy", "Normal", "Hard"]:
        fp = cache.get(k, "")
        if fp and Path(fp).is_dir():
            build_songs_list(k, fp, BUILD_DIR, cache)
        else:
            print(f"Folder for {k} not found in cache/disk.")
    save_cache(cache)

def cache_data_paths(force=False):
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    marker = BUILD_DIR / ".data_paths_cached"
    if force and marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass
    cache = load_cache()
    if (
        not force
        and (
            marker.exists()
            or all(cache.get(k, "") for k in ["Easy", "Normal", "Hard", "Gear", "Stats"])
        )
    ):
        print("Data paths cached; skipping scan.")
        return
    print("Scanning for data paths...")
    locs = find_locations()
    if not locs:
        print("No target folders/files found; skipping caching.")
        return
    cache.update(locs)
    save_cache(cache)
    build_all_songs(cache)
    marker.touch()
    print("Data paths cached and song lists built.")

def main():
    args = {arg.lower() for arg in sys.argv[1:]}
    force_rebuild = ("--force" in args) or ("-f" in args)
    print("Interpreter:", sys.executable, sys.implementation.name, sys.version)
    if force_rebuild:
        print("Force rebuild requested; clearing cached markers.")
    cache_data_paths(force=force_rebuild)


if __name__ == "__main__":
    main()
