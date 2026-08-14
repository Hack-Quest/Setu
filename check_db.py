from database.postgres_client import get_db_cursor

def test_tables():
    tables_to_test = ["otps", "ngos", "volunteers_auth", "volunteers", "needs_reports", "assignments"]
    for table in tables_to_test:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"Table '{table}' has {count} rows.")
        except Exception as e:
            print(f"Failed to query '{table}': {e}")

if __name__ == "__main__":
    test_tables()
