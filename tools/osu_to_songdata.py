#!/usr/bin/env python3
"""
osu! Beatmap to RoBeats Song Data Converter

Converts osu! mania beatmap format (.osu files) to the custom song data format
used by the RoBeats calculator.

Usage:
    python osu_to_songdata.py <input.osu> [output.txt]
    
If no output file is specified, prints to stdout.
"""

import sys
import re
from pathlib import Path
from typing import Optional


# =============================================================================
# CONFIGURATION - Manually edit these values for each song
# =============================================================================
MANUAL_CONFIG = {
    "song_name": "Song Name (Difficulty) by Artist",
    "difficulty": 30,
    "primary_color": "Vibe",      # None, Chill, Vibe, Beat, Flow, Rush
    "secondary_color": "Flow",    # None, Chill, Vibe, Beat, Flow, Rush
    "fever_fill": 0,              # Will be calculated if 0
    "fever_time": 0.0,            # Will be calculated if 0
    "vip": False,
    "remix": False,
}


# =============================================================================
# OSU FORMAT CONSTANTS
# =============================================================================
# osu! mania lane positions (4K mode)
# x positions typically: 64, 192, 320, 448
OSU_LANE_BOUNDARIES = [128, 256, 384]  # Boundaries between lanes

# Hit object type flags
HIT_CIRCLE = 1
HOLD_NOTE = 128


def x_to_lane(x: int) -> int:
    """Convert osu! x-coordinate to lane number (1-4)."""
    if x < OSU_LANE_BOUNDARIES[0]:
        return 1
    elif x < OSU_LANE_BOUNDARIES[1]:
        return 2
    elif x < OSU_LANE_BOUNDARIES[2]:
        return 3
    else:
        return 4


def parse_timing_points(lines: list[str]) -> list[tuple[float, float]]:
    """
    Parse [TimingPoints] section from osu! format.
    
    Format: offset,beatLength,meter,sampleSet,sampleIndex,volume,uninherited,effects
    
    Returns list of (time_seconds, beat_length_ms) tuples for uninherited timing points.
    """
    timing_points = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
            
        parts = line.split(",")
        if len(parts) < 2:
            continue
            
        try:
            offset_ms = float(parts[0])
            beat_length = float(parts[1])
            
            # Check if uninherited (inherited points have negative beat_length)
            uninherited = True
            if len(parts) >= 7:
                uninherited = parts[6] == "1"
            
            # Only include uninherited timing points (actual BPM changes)
            # Inherited points (negative beat_length) are slider velocity changes
            if uninherited and beat_length > 0:
                time_sec = offset_ms / 1000.0
                timing_points.append((time_sec, beat_length))
                
        except (ValueError, IndexError):
            continue
    
    return timing_points


def parse_hit_objects(lines: list[str]) -> list[dict]:
    """
    Parse [HitObjects] section from osu! format.
    
    Format: x,y,time,type,hitSound,extras...
    For hold notes: x,y,time,type,hitSound,endTime:extras...
    
    Returns list of note dictionaries with time, lane, and type info.
    """
    notes = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
            
        parts = line.split(",")
        if len(parts) < 5:
            continue
            
        try:
            x = int(parts[0])
            time_ms = int(parts[2])
            obj_type = int(parts[3])
            
            lane = x_to_lane(x)
            time_sec = time_ms / 1000.0
            
            # Determine note type
            # Type 1 = normal note, Type 2 = long note (hold)
            if obj_type & HOLD_NOTE:
                # Hold note - extract end time from extras
                note_type = 2  # Long note
                # End time is in the last field before the colon-separated extras
                if len(parts) >= 6:
                    extras = parts[5].split(":")
                    if extras:
                        try:
                            end_time_ms = int(extras[0])
                            # Store duration info (not used in current format but available)
                        except ValueError:
                            pass
            else:
                note_type = 1  # Normal note
            
            notes.append({
                "time": time_sec,
                "lane": lane,
                "type": note_type,
            })
            
        except (ValueError, IndexError):
            continue
    
    # Sort by time, then by lane for consistent ordering
    notes.sort(key=lambda n: (n["time"], n["lane"]))
    
    return notes


def parse_osu_file(filepath: str) -> tuple[list[tuple[float, float]], list[dict], dict]:
    """
    Parse an osu! file and extract timing points and hit objects.
    
    Returns (timing_points, notes, metadata).
    """
    timing_lines = []
    hitobj_lines = []
    metadata = {}
    
    current_section = None
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            
            # Section headers
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                continue
            
            # Metadata parsing
            if current_section == "Metadata":
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip()
            
            elif current_section == "Difficulty":
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip()
            
            elif current_section == "TimingPoints":
                timing_lines.append(line)
            
            elif current_section == "HitObjects":
                hitobj_lines.append(line)
    
    timing_points = parse_timing_points(timing_lines)
    notes = parse_hit_objects(hitobj_lines)
    
    return timing_points, notes, metadata


def calculate_bpm(timing_points: list[tuple[float, float]]) -> int:
    """Calculate primary BPM from timing points."""
    if not timing_points:
        return 0
    
    # Use the first timing point's beat length to calculate BPM
    beat_length_ms = timing_points[0][1]
    if beat_length_ms <= 0:
        return 0
    
    bpm = 60000.0 / beat_length_ms
    return round(bpm)


def count_long_notes(notes: list[dict]) -> int:
    """Count the number of long/hold notes."""
    return sum(1 for n in notes if n["type"] == 2)


def format_output(
    timing_points: list[tuple[float, float]],
    notes: list[dict],
    config: dict,
    osu_metadata: dict,
) -> str:
    """
    Format the parsed data into the target song data format.
    """
    lines = []
    
    # Calculate derived values
    total_notes = len(notes)
    long_notes = count_long_notes(notes)
    last_note_time = notes[-1]["time"] if notes else 0.0
    bpm = calculate_bpm(timing_points)
    
    # Estimate song length (last note + a small buffer)
    song_length = last_note_time + 0.2 if notes else 0.0
    
    # Fever fill estimation (roughly 32% of notes for typical gameplay)
    fever_fill = config.get("fever_fill", 0)
    if fever_fill == 0:
        fever_fill = int(total_notes * 0.32)
    
    # Fever time estimation
    fever_time = config.get("fever_time", 0.0)
    if fever_time == 0.0:
        fever_time = song_length * 0.15  # Rough estimate
    
    # Get song name from config or osu metadata
    song_name = config.get("song_name", "")
    if song_name == "Song Name (Difficulty) by Artist" and osu_metadata:
        title = osu_metadata.get("Title", "Unknown")
        artist = osu_metadata.get("Artist", "Unknown")
        version = osu_metadata.get("Version", "")
        song_name = f"{title} ({version}) by {artist}" if version else f"{title} by {artist}"
    
    # === HEADER SECTION ===
    lines.append(f"Song Name\t{song_name}")
    lines.append(f"Difficulty\t{config.get('difficulty', 0)}")
    lines.append(f"Primary Color\t{config.get('primary_color', 'None')}")
    lines.append(f"Secondary Color\t{config.get('secondary_color', 'None')}")
    lines.append(f"Last Note Time\t{last_note_time:.3f}")
    lines.append(f"Total Notes\t{total_notes}")
    lines.append(f"Fever Fill\t{fever_fill}")
    lines.append(f"Fever Time\t{fever_time:.6f}")
    lines.append(f"Long Notes\t{long_notes}")
    lines.append(f"BPM\t{bpm}")
    lines.append(f"Song Length\t{song_length:.9f}")
    lines.append("")
    
    # === TIMING POINTS SECTION ===
    lines.append("Timing Points")
    for time_sec, beat_length in timing_points:
        # Output each timing point twice (matching the example format)
        lines.append(f"{time_sec:.3f}\t{beat_length:.4f}")
        lines.append(f"{time_sec:.3f}\t{beat_length:.4f}")
    lines.append("")
    lines.append("")
    
    # === SONG DATA SECTION ===
    lines.append("Song Data")
    for idx, note in enumerate(notes, start=1):
        # Format: time  note_index  lane  type
        lines.append(f"{note['time']:.3f}\t{idx}\t{note['lane']}\t{note['type']}")
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Please provide an input .osu file path.")
        print("\nAlternatively, you can edit MANUAL_CONFIG in this script and run:")
        print("  python osu_to_songdata.py input.osu output.txt")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_path).exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    print(f"Parsing: {input_path}")
    timing_points, notes, osu_metadata = parse_osu_file(input_path)
    
    print(f"  Found {len(timing_points)} timing points")
    print(f"  Found {len(notes)} hit objects")
    
    if osu_metadata:
        print(f"  Title: {osu_metadata.get('Title', 'Unknown')}")
        print(f"  Artist: {osu_metadata.get('Artist', 'Unknown')}")
    
    # Format output
    output = format_output(timing_points, notes, MANUAL_CONFIG, osu_metadata)
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nOutput written to: {output_path}")
    else:
        print("\n" + "=" * 60)
        print(output)


if __name__ == "__main__":
    main()
