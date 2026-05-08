import os, datetime, sqlite3
from pathlib import Path
dbs = sorted(Path('.').glob('evolution*.db'), key=lambda p: p.stat().st_size, reverse=True)
for f in dbs[:10]:
    st = f.stat()
    try:
        c = sqlite3.connect(str(f))
        n = c.execute('SELECT COUNT(*) FROM team_buff_loadouts WHERE team_buff=?', ('T5',)).fetchone()[0]
        s = c.execute('SELECT COUNT(DISTINCT song_name) FROM team_buff_loadouts WHERE team_buff=?', ('T5',)).fetchone()[0]
        rows_info = f'{n:,} rows, {s:,} songs'
        c.close()
    except Exception as e:
        rows_info = str(e)
    ts = datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    print(f'{st.st_size:>14,}  {ts}  {f.name:<25}  {rows_info}')
