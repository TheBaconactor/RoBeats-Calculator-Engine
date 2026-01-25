"""Verify tier definitions and compare NONE vs T5 entries."""
import sqlite3
import json

# Show the tier definitions
print('=== Team Buff Tier Definitions ===')
TIERS = {
    'NONE': {'PP': 0, 'Elem': 0},
    'T1':   {'PP': 25, 'Elem': 35},
    'T5':   {'PP': 25, 'Elem': 30},
    'T10':  {'PP': 20, 'Elem': 25},
    'T15':  {'PP': 15, 'Elem': 20},
}
for tier, vals in TIERS.items():
    print(f"  {tier:4s}: PP +{vals['PP']:2d}, Color Element +{vals['Elem']:2d}")

conn = sqlite3.connect('evolution.db')

# Compare same song in NONE vs T5 in team_buff_loadouts
print()
print('=== Same song in team_buff_loadouts: NONE vs T5 ===')
print('(NONE should have lower PP and no color bonus compared to T5)')
print()

# Find a song that has both NONE and T5 entries
song = conn.execute('''
    SELECT song_name FROM team_buff_loadouts 
    WHERE team_buff = 'NONE' 
    GROUP BY song_name 
    HAVING COUNT(*) > 3 
    LIMIT 1
''').fetchone()[0]

print(f'Song: {song[:60]}...')
print()

for tier in ['NONE', 'T5']:
    row = conn.execute('''
        SELECT team_buff, score, details_json FROM team_buff_loadouts
        WHERE song_name = ? AND team_buff = ?
        ORDER BY score DESC LIMIT 1
    ''', (song, tier)).fetchone()
    if row:
        details = json.loads(row[2]) if row[2] else {}
        stats = details.get('Stats', {})
        pp = stats.get('Perfect Points', 0)
        chill = stats.get('Chill', 0)
        flow = stats.get('Flow', 0)
        rush = stats.get('Rush', 0)
        beat = stats.get('Beat', 0)
        vibe = stats.get('Vibe', 0)
        print(f"{tier:4s} -> PP={pp:3d} | Chill={chill:3d} Flow={flow:3d} Rush={rush:3d} Beat={beat:3d} Vibe={vibe:3d}")

conn.close()
