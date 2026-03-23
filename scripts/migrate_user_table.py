import sqlite3
import os
from dotenv import load_dotenv

def get_db_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir, '.env'))
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('sqlite:///'):
        db_file = db_url.replace('sqlite:///', '')
        path = os.path.join(base_dir, 'instance', db_file)
        if not os.path.exists(path):
            path = os.path.join(base_dir, db_file)
        return path
    return os.path.join(base_dir, 'instance', 'dwp.db')

def migrate():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Creating new one if app.py is run.")
        return
        
    print(f"Using database: {db_path}")
    conn = sqlite3.connect(db_path)
    
    cursor = conn.cursor()
    
    # Check existing columns in 'users' table
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'failed_login_attempts' not in columns:
        print("Adding failed_login_attempts column...")
        cursor.execute("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
        
    if 'is_locked' not in columns:
        print("Adding is_locked column...")
        cursor.execute("ALTER TABLE users ADD COLUMN is_locked BOOLEAN DEFAULT 0")
        
    if 'is_admin' not in columns:
        print("Adding is_admin column...")
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
