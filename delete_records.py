import sqlite3
conn = sqlite3.connect('evolution.db')
conn.execute("DELETE FROM loadouts WHERE song_name LIKE '%Take Your Time%'")
conn.commit()
print('Deleted Take Your Time records')
conn.close()
