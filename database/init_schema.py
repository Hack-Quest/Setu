import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.postgres_client import get_db_cursor

def init_schema():
    load_dotenv(dotenv_path="config/.env")
    sql_path = os.path.join("database", "schema.sql")
    
    if not os.path.exists(sql_path):
        print(f"Error: {sql_path} does not exist.")
        sys.exit(1)
        
    with open(sql_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    print("[INFO] Connecting to Supabase PostgreSQL database and running schema initialization...", flush=True)
    try:
        # dict_cursor=False is used because we don't need dictionary cursor for DD/schema creation
        with get_db_cursor(commit=True, dict_cursor=False) as cur:
            cur.execute(schema_sql)
        print("[OK] SUCCESS: Supabase PostgreSQL connection verified and schema initialized successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to connect or initialize database: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    init_schema()
