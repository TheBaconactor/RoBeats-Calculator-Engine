"""
Quick test for Euphoria (Hard) song to identify scoring discrepancy.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.diagnose_scoring import diagnose_song

# Test the specific song mentioned by the user
song_path = "Songs/Euphoria (Hard) by Geoxor.txt"

if not os.path.exists(song_path):
    print(f"Error: Song file not found: {song_path}")
    print("Please provide the correct path to the song file.")
    sys.exit(1)

print("Testing Euphoria (Hard) scoring...")
print("=" * 60)
print()

result = diagnose_song(song_path)

print()
print("=" * 60)
print("COMPARISON:")
print(f"  Actual Result:   {result.get('Score', 0)}")
print(f"  Expected Result: 40752381")
print(f"  Difference:      {result.get('Score', 0) - 40752381}")
print(f"  Percentage:      {((result.get('Score', 0) / 40752381) - 1) * 100:.2f}%")
