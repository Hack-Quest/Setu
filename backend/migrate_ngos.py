import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.firestore_client import db

def migrate_ngos():
    docs = db.collection("ngos").stream()
    count = 0
    for doc in docs:
        data = doc.to_dict()
        updates = {}
        
        # Check if legacy name exists and ngo_name doesn't
        if "name" in data and "ngo_name" not in data:
            updates["owner_name"] = data["name"]
            # If there was some other organization mapping, try to use it, else generic
            updates["ngo_name"] = data.get("organization_name", data.get("organization", "Unnamed NGO (Needs Update)"))
            
        if updates:
            db.collection("ngos").document(doc.id).update(updates)
            print(f"Migrated NGO {doc.id} -> owner_name: {updates.get('owner_name')}, ngo_name: {updates.get('ngo_name')}")
            count += 1
            
    print(f"Migration complete. Updated {count} NGOs.")

if __name__ == "__main__":
    migrate_ngos()
