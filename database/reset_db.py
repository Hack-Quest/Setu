import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.postgres_client import get_db_cursor

def reset_db():
    load_dotenv(dotenv_path="config/.env")
    tables = ["assignments", "needs_reports", "volunteers", "volunteers_auth", "ngos", "otps"]
    
    print("[INFO] Resetting database state by truncating all tables...", flush=True)
    try:
        with get_db_cursor(commit=True, dict_cursor=False) as cur:
            for t in tables:
                cur.execute(f"TRUNCATE TABLE {t} CASCADE;")
        print("[OK] Database tables truncated successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to truncate tables: {e}", flush=True)

if __name__ == "__main__":
    reset_db()
