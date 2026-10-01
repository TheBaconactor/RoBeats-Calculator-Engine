"""The results database: leaderboard records, its tables, connections and migrations, board rules, reads and writes.

records: typed Loadout / MetaResult / FgResult / Traces.   tables: the version 19 tables and how rows are written.
schema: connections (a writer creates or migrates).        boards: board orders and the merge of new results.
db: reads and writes.                                       v18: the version 18 reader and the migration to 19.
legacy: version 18 shaped views of the records (temporary: stages 8 and 9).
"""
