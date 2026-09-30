"""The results database: leaderboard records, the schema and its migrations, board rules, reads and writes.

records: typed Loadout / MetaResult / FgResult / Traces.   schema: version 19, connections.
boards: board orders and the merge of new results.         db: reads and writes.
v18: the version 18 reader and the migration to 19.        entries: pipeline result dicts -> candidates.
"""
