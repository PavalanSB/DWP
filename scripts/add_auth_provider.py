"""
Add `auth_provider` column to `users` table if missing. Safe for SQLite and other DBs (simple ALTER).
Backs up sqlite DB file before change.

Run with the project's venv python from the repository root:

.venv\Scripts\python scripts\add_auth_provider.py

"""
import os
import shutil
import sys
from sqlalchemy import create_engine, inspect, text

# Ensure the repo root is on sys.path so config can be imported
ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from config import Config
except Exception as e:
    print("Could not import config.py:", e)
    sys.exit(1)

SQLALCHEMY_DATABASE_URI = Config.SQLALCHEMY_DATABASE_URI

print("Using DB URI:", SQLALCHEMY_DATABASE_URI)

# If sqlite, back up the file first
if SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
    db_path = SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        print(f"SQLite DB file not found at {db_path}")
    else:
        backup = db_path + ".bak"
        shutil.copyfile(db_path, backup)
        print(f"Backed up {db_path} -> {backup}")

engine = create_engine(SQLALCHEMY_DATABASE_URI)
inspector = inspect(engine)

if 'users' not in inspector.get_table_names():
    print("Table 'users' not found in DB. Aborting.")
    sys.exit(1)

cols = [c['name'] for c in inspector.get_columns('users')]
if 'auth_provider' in cols:
    print("Column 'auth_provider' already exists. Nothing to do.")
    sys.exit(0)

print("Adding column 'auth_provider' to 'users' table...")
try:
    with engine.connect() as conn:
        # Use raw ALTER; should work for SQLite/Postgres/MySQL with this syntax for adding a simple column
        conn.execute(text("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) NOT NULL DEFAULT 'local'"))
        conn.commit()
    print("Column added successfully.")
except Exception as e:
    print("Failed to add column:", e)
    print("If using SQLite and the table has complex constraints, consider using a dump/recreate migration or Alembic.")
    sys.exit(2)

print("Done.")
