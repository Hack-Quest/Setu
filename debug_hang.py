import os
import sys
import json
from dotenv import load_dotenv

print("Loading dotenv...")
load_dotenv('config/.env')

print("Testing Gemini Processor...")
from ai_processing.gemini_processor import process_need_text

# test gemini
try:
    print("Sending request to Gemini...")
    res = process_need_text("urgent medical help needed due to 7 scale earthquake")
    print(f"Gemini response: {res}")
except Exception as e:
    print(f"Gemini error: {e}")

print("\nTesting Geocoding...")
from database.geocoding import get_coordinates
try:
    print("Calling get_coordinates('delhi')...")
    coords = get_coordinates("delhi")
    print(f"Coordinates: {coords}")
except Exception as e:
    print(f"Geocoding error: {e}")

print("\nTesting Firestore...")
try:
    print("Importing firestore...")
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    cert_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"Cert path: {cert_path}")
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(cert_path)
        firebase_admin.initialize_app(cred)
        
    db = firestore.client()
    print("Firestore client initialized. Testing write...")
    # NOTE: we won't actually write to avoid polluting, but if it hangs on client, we'll see.
except Exception as e:
    print(f"Firestore error: {e}")

print("\nAll tests finished.")
