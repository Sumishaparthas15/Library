

import sqlite3, os

# Base directory path
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "library.db")

# Delete the old database file if it exists
if os.path.exists(DB):
    os.remove(DB)
    print("🗑️ Old database removed.")

# Create a new empty database
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Run schema script to create empty tables
with open(os.path.join(BASE, "init_schema.sql")) as f:
    cur.executescript(f.read())

conn.commit()
conn.close()

print("✅ Empty database created at", DB)
