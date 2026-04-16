import requests
import os
from dotenv import load_dotenv
from database.firestore_client import db

# Load your secret token
load_dotenv('config/.env')
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "your-fallback-token-here")

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Authorization": f"Bearer {SECRET_TOKEN}"}

print("🚀 Testing Volunteer Registration with Auth Fields...\n")

# 1. The payload with a plain-text password
payload = {
    "name": "Anshika (Security Test)",
    "email": "anshi.test@setu.ai",
    "password": "HackathonPassword2026!",
    "phone": "+91-9998887776",
    "location": "Delhi",
    "skills": ["logistics", "comms"]
}

print("📤 SENDING PAYLOAD TO API:")
for key, value in payload.items():
    if key == "password":
        print(f"   {key}: {value} ⚠️ (PLAIN TEXT)")
    else:
        print(f"   {key}: {value}")

# 2. Make the HTTP POST request to your FastAPI server
try:
    response = requests.post(f"{BASE_URL}/volunteer", json=payload, headers=HEADERS)

    if response.status_code == 200:
        print(f"\n✅ API RESPONSE: {response.json()}")
        
        # 3. Fetch straight from Firestore to verify the hash was created
        print("\n🔍 FETCHING FROM FIRESTORE (Database Truth)...")
        
        # Querying the volunteer by the email we just sent
        docs = db.collection("volunteers").where("email", "==", payload["email"]).stream()
        
        found = False
        for doc in docs:
            found = True
            db_data = doc.to_dict()
            print(f"\n📄 Document ID: {doc.id}")
            print(f"   Name: {db_data.get('name')}")
            print(f"   Email: {db_data.get('email')}")
            
            # The moment of truth!
            print(f"   Password Hash: {db_data.get('password_hash')} 🔒 (SECURE!)")
            print(f"   Raw 'password' field exists in DB?: {'password' in db_data} (Should be False!)")
            print(f"   Available Status: {db_data.get('available')}")
            
        if not found:
            print("❌ Could not find the volunteer in the database. Did it save?")
            
    else:
        print(f"\n❌ API Request failed! Status Code: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n🚨 Error connecting to API: {e}")
    print("Did you remember to start your FastAPI server? (uvicorn main:app --reload)")