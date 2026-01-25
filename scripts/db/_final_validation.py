"""
Final DB validation before shipping to frontend.
Verifies all critical aspects are working correctly.
"""
import sqlite3

def check_db():
    conn = sqlite3.connect('evolution.db')
    c = conn.cursor()
    
    print("=" * 60)
    print("FINAL DB VALIDATION FOR FRONTEND")
    print("=" * 60)
    
    # 1. Schema version
    version = c.execute('PRAGMA user_version').fetchone()[0]
    print(f"\n1. Schema Version: {version}")
    print(f"   {'✓' if version == 12 else '✗'} Expected: 12")
    
    # 2. Unified view exists
    view_exists = c.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='fg_loadouts_unified'").fetchone()
    print(f"\n2. Unified View: {'✓ Exists' if view_exists else '✗ Missing'}")
    
    # 3. Deduplication working
    legacy_count = c.execute('SELECT COUNT(*) FROM fg_loadouts').fetchone()[0]
    tiered_count = c.execute('SELECT COUNT(*) FROM team_buff_fg_loadouts').fetchone()[0]
    unified_count = c.execute('SELECT COUNT(*) FROM fg_loadouts_unified').fetchone()[0]
    duplicates_removed = (legacy_count + tiered_count) - unified_count
    
    print(f"\n3. Deduplication:")
    print(f"   Legacy (fg_loadouts): {legacy_count:,}")
    print(f"   Tiered (team_buff_fg_loadouts): {tiered_count:,}")
    print(f"   Union total: {legacy_count + tiered_count:,}")
    print(f"   Unified view: {unified_count:,}")
    print(f"   Duplicates removed: {duplicates_removed:,}")
    print(f"   {'✓' if duplicates_removed > 0 else '✗'} Working")
    
    # 4. Tier breakdown for sample song
    sample = c.execute('SELECT DISTINCT song_name FROM team_buff_fg_loadouts LIMIT 1').fetchone()
    if sample:
        song = sample[0]
        tiers = c.execute('''
            SELECT DISTINCT team_buff 
            FROM fg_loadouts_unified 
            WHERE song_name = ? 
            ORDER BY team_buff
        ''', (song,)).fetchall()
        
        print(f"\n4. Tier Breakdown (sample: {song[:50]}...):")
        tier_names = [t[0] for t in tiers]
        expected = ['NONE', 'T1', 'T10', 'T15', 'T5']
        missing = set(expected) - set(tier_names)
        extra = set(tier_names) - set(expected)
        
        print(f"   Tiers present: {', '.join(tier_names)}")
        print(f"   {'✓' if not missing else '✗'} All expected tiers present")
        if missing:
            print(f"   Missing: {', '.join(missing)}")
        if extra:
            print(f"   Extra: {', '.join(extra)}")
    
    # 5. team_buff column exists in fg_loadouts
    columns = c.execute("PRAGMA table_info(fg_loadouts)").fetchall()
    has_team_buff = any(col[1] == 'team_buff' for col in columns)
    print(f"\n5. fg_loadouts.team_buff column: {'✓ Exists' if has_team_buff else '✗ Missing'}")
    
    # 6. Verify no NULL team_buff in unified view
    null_count = c.execute('SELECT COUNT(*) FROM fg_loadouts_unified WHERE team_buff IS NULL').fetchone()[0]
    print(f"\n6. NULL team_buff check: {'✓ None' if null_count == 0 else f'✗ {null_count} NULL entries'}")
    
    # 7. Tier distribution
    tier_counts = c.execute('''
        SELECT team_buff, COUNT(*) 
        FROM fg_loadouts_unified 
        GROUP BY team_buff 
        ORDER BY team_buff
    ''').fetchall()
    
    print(f"\n7. Tier Distribution:")
    for tier, count in tier_counts:
        print(f"   {tier:4s}: {count:,} entries")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    check_db()
