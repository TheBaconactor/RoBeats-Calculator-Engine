import sqlite3

conn = sqlite3.connect('evolution.db')
c = conn.cursor()

# Count entries per tier in unified view
counts = c.execute('SELECT team_buff, COUNT(*) FROM fg_loadouts_unified GROUP BY team_buff ORDER BY team_buff').fetchall()
print('FG tier counts in unified view:')
for tier, count in counts:
    print(f'  {tier:4s}: {count:,} entries')

total = sum(cnt for _, cnt in counts)
print(f'\nTotal: {total:,} entries')

# Get source counts
legacy = c.execute('SELECT COUNT(*) FROM fg_loadouts').fetchone()[0]
tiered = c.execute('SELECT COUNT(*) FROM team_buff_fg_loadouts').fetchone()[0]

print(f'\nSource breakdown:')
print(f'  fg_loadouts (legacy): {legacy:,}')
print(f'  team_buff_fg_loadouts: {tiered:,}')
print(f'  Union total: {legacy + tiered:,}')
print(f'  Unified view: {total:,}')
print(f'  Deduplication working: {"✓" if total < legacy + tiered else "✗"}')

conn.close()
