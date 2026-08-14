import pandas as pd
from datetime import datetime, timezone
from database.volunteers_db import save_volunteer
from database.postgres_client import get_db_cursor
import os

def ingest_pros(file_path):
    # Read the generated Excel
    df = pd.read_excel(file_path)

    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.replace(" ", "_")

    # Counter for logs
    count = 0
    
    for _, row in df.iterrows():
        # Prepare the Tier 1 Professional Profile
        volunteer_data = {
            "name": str(row['Name']),
            "phone": str(row['Phone']),
            "skills": [s.strip().lower() for s in str(row['Skills']).split(',')],
            "ngo_verified": True,              # REQUIRED
            "available": True,                 # REQUIRED
            "lat": float(row['Latitude']),
            "lng": float(row['Longitude']),
            "specialty": str(row['Specialty']).upper(),
            "ngo_affiliation": str(row['NGO_Affiliation']),
            "verification_code": str(row['Verification_Code']),
            "registered_at": datetime.now(timezone.utc),
            "active_assignments": 0
        }
        
        # 2. Inject into Supabase PostgreSQL
        save_volunteer(volunteer_data)
        count += 1
        print(f"🎖️ [{count}] Injected NGO Pro: {volunteer_data['name']} ({volunteer_data['specialty']})")

    print(f"\n✅ Successfully seeded {count} Verified Responders into Supabase PostgreSQL.")

if __name__ == "__main__":
    # Ensure 'pandas' and 'openpyxl' are installed: pip install pandas openpyxl
    ingest_pros('Setu_Verified_Responders.xlsx')