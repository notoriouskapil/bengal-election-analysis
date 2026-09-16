"""
Load data/clean/ into SQLite. Drops and rebuilds every table.

    python src/load_db.py
"""

from pathlib import Path
import sqlite3
import pandas as pd

ROOT  = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
DB    = ROOT / "bengal_elections.db"

TABLES = {
    "constituencies": "constituencies.csv",
    "results":        "results.csv",
    "winners":        "winners.csv",
    "nota":           "nota.csv",
    "electorate":     "electorate.csv",
    "seat_status":    "seat_status.csv",
    "name_flags":     "name_flags.csv",
}

if DB.exists():
    DB.unlink()

conn = sqlite3.connect(DB)
conn.executescript((ROOT / "sql" / "schema.sql").read_text())

print(f"Loading {DB.name}")
for table, filename in TABLES.items():
    df = pd.read_csv(CLEAN / filename)
    df.to_sql(table, conn, if_exists="append", index=False)
    print(f"  {table:<16} {len(df):>5} rows")

conn.commit()

print("\nSanity check - seats won by party")
q = """
SELECT w.winner_party AS party,
       SUM(CASE WHEN w.year = 2021 THEN 1 ELSE 0 END) AS seats_2021,
       SUM(CASE WHEN w.year = 2026 THEN 1 ELSE 0 END) AS seats_2026
FROM winners w
GROUP BY w.winner_party
HAVING seats_2021 + seats_2026 > 1
ORDER BY seats_2026 DESC, seats_2021 DESC
"""
print(pd.read_sql(q, conn).to_string(index=False))

print("\nSanity check - turnout and seats by region, 2026")
q = """
SELECT c.region,
       COUNT(*)                        AS seats,
       ROUND(AVG(e.turnout_pct), 2)    AS avg_turnout,
       SUM(CASE WHEN w.winner_party = 'BJP' THEN 1 ELSE 0 END) AS bjp,
       SUM(CASE WHEN w.winner_party = 'TMC' THEN 1 ELSE 0 END) AS tmc
FROM v_winners w
JOIN constituencies c ON c.ac_no = w.ac_no
JOIN electorate    e ON e.ac_no = w.ac_no AND e.year = w.year
WHERE w.year = 2026
GROUP BY c.region
ORDER BY seats DESC
"""
print(pd.read_sql(q, conn).to_string(index=False))

conn.close()
print(f"\nReady: {DB}")
