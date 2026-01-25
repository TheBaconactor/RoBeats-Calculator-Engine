import sqlite3, json
c = sqlite3.connect('evolution.db')
rows = c.execute('SELECT details_json FROM loadouts WHERE song_name LIKE "%AI Bomb%" ORDER BY timestamp DESC LIMIT 5').fetchall()
for i, r in enumerate(rows):
    d = json.loads(r[0]) if r[0] else {}
    stats = d.get('Stats', {})
    print(f"Entry {i+1}: Stats empty={not stats}, has_Chill={'Chill' in stats}")
c.close()
