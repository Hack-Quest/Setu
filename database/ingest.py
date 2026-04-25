import pandas as pd
from datetime import datetime
from google.cloud import firestore
import os

PROJECT_ID = "project-ecb78041-2b9f-43b6-a06"

# ✅ Uses Application Default Credentials — run `gcloud auth application-default login` locally.
db = firestore.Client(project=PROJECT_ID)
print("✅ Firestore Authenticated via ADC")

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
    
    # ✅ CRITICAL FIXES
    "skills": [s.strip().lower() for s in str(row['Skills']).split(',')],
    "ngo_verified": True,              # 🔥 REQUIRED
    "available": True,                 # 🔥 REQUIRED
    
    # ✅ FLAT COORDINATES (VERY IMPORTANT)
    "lat": float(row['Latitude']),
    "lng": float(row['Longitude']),
    
    # Optional but fine
    "specialty": str(row['Specialty']).upper(),
    "ngo_affiliation": str(row['NGO_Affiliation']),
    "verification_code": str(row['Verification_Code']),
    
    "registered_at": datetime.utcnow().isoformat(),
    "active_assignments": 0
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