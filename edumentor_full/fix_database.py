"""Fix quiz_results database schema by adding missing topic column."""

import sqlite3
import os

db_path = "data/quiz_results.db"

if not os.path.exists(db_path):
    print(f"❌ Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current schema
cursor.execute("PRAGMA table_info(quiz_results)")
columns = cursor.fetchall()

print("Current columns:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Check if topic column exists
column_names = [col[1] for col in columns]
if 'topic' not in column_names:
    print("\n⚠️  'topic' column is missing!")
    print("Adding 'topic' column...")
    cursor.execute("ALTER TABLE quiz_results ADD COLUMN topic TEXT DEFAULT ''")
    conn.commit()
    print("✅ Successfully added 'topic' column")
else:
    print("\n✅ 'topic' column already exists")

# Verify
cursor.execute("PRAGMA table_info(quiz_results)")
columns = cursor.fetchall()
print("\nUpdated columns:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
print("\n✅ Database check complete!")
