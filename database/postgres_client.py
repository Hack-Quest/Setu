import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from contextlib import contextmanager
from urllib.parse import urlparse, unquote

# Load configuration from config/.env
load_dotenv(dotenv_path="config/.env")

DATABASE_URL = os.getenv("SUPABASE_DB_URL")

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "SUPABASE_DB_URL is not set. Please add it to your config/.env file."
            )
        try:
            print("[INFO] Initializing PostgreSQL Connection Pool...", flush=True)
            
            # Robustly parse connection string to handle special characters (like '@') in passwords
            parsed = urlparse(DATABASE_URL)
            conn_params = {
                "user": unquote(parsed.username) if parsed.username else None,
                "password": unquote(parsed.password) if parsed.password else None,
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip('/') if parsed.path else None,
            }
            # Remove None values
            conn_params = {k: v for k, v in conn_params.items() if v is not None}
            
            # Set SSL mode if using a hosted database like Supabase
            # psycopg2 uses 'sslmode' connection parameter
            if "sslmode" in parsed.query:
                # Extract sslmode from query parameters if present
                from urllib.parse import parse_qs
                queries = parse_qs(parsed.query)
                if "sslmode" in queries:
                    conn_params["sslmode"] = queries["sslmode"][0]
            else:
                # Default to require ssl for cloud database URLs
                if parsed.hostname and not parsed.hostname.startswith(("localhost", "127.0.0.1")):
                    conn_params["sslmode"] = "require"

            # Threaded pool is safe for multi-threaded FastAPI servers
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                **conn_params
            )
            print("[OK] PostgreSQL Connection Pool initialized successfully.", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to initialize connection pool: {e}", flush=True)
            raise e
    return _pool

@contextmanager
def get_db_connection():
    pool_obj = get_pool()
    conn = pool_obj.getconn()
    try:
        yield conn
    finally:
        pool_obj.putconn(conn)

@contextmanager
def get_db_cursor(commit=False, dict_cursor=True):
    """
    Helper context manager to fetch database cursor.
    Uses RealDictCursor by default to return records as standard Python dicts,
    ensuring compatibility with existing model formats.
    """
    cursor_factory = RealDictCursor if dict_cursor else None
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            if commit:
                conn.rollback()
            raise e
        finally:
            cursor.close()
