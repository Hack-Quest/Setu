from database.firestore_client import db

def test_collections():
    collections_to_test = ["needs", "reports", "needs_reports", "emergency_reports"]
    for col in collections_to_test:
        docs = list(db.collection(col).stream())
        print(f"Collection '{col}' has {len(docs)} documents.")

if __name__ == "__main__":
    test_collections()
