import pandas as pd
from datetime import datetime
from google.cloud import firestore
import os
from google.cloud import firestore
from google.oauth2 import service_account

KEY_PATH = os.path.join(os.getcwd(), 'config', 'serviceAccountKey.json')

if os.path.exists(KEY_PATH):
    credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
    db = firestore.Client(credentials=credentials, project=credentials.project_id)
    print("✅ Firestore Authenticated using Service Account Key")
else:
    print(f"❌ ERROR: Key not found at {KEY_PATH}")
    # Fallback to default (which is currently failing)
    db = firestore.Client()

def ingest_pros(file_path):
    # Read the generated Excel
    df = pd.read_excel(r"C:\Users\mudit\Downloads\Setu_Verified_Responders.xlsx")
    
    # Counter for logs
    count = 0
    
    for _, row in df.iterrows():
        # Prepare the Tier 1 Professional Profile
        volunteer_data = {
            "name": str(row['Name']),
            "phone": str(row['Phone']),
            "specialty": str(row['Specialty']).upper(),
            "skills": [s.strip() for s in str(row['Skills']).split(',')],
            "ngo_affiliation": str(row['NGO_Affiliation']),
            "verification_code": str(row['Verification_Code']),
            "is_verified": True,  # Explicitly True for Tier 1
            "status": "available",
            "location": {
                "lat": float(row['Latitude']),
                "lng": float(row['Longitude'])
            },
            "last_active": datetime.utcnow().isoformat(),
            "total_missions": 0,
            "is_on_mission": False
        }
        
        # 2. Inject into Firestore
        # Using Phone as document ID to prevent duplicates if you run it twice
        db.collection("volunteers").document(volunteer_data["phone"]).set(volunteer_data)
        count += 1
        print(f"🎖️ [{count}] Injected NGO Pro: {volunteer_data['name']} ({volunteer_data['specialty']})")

    print(f"\n✅ Successfully seeded {count} Verified Responders into Firestore.")

if __name__ == "__main__":
    # Ensure 'pandas' and 'openpyxl' are installed: pip install pandas openpyxl
    ingest_pros('Setu_Verified_Responders.xlsx')