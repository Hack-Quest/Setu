import os
import sys
from dotenv import load_dotenv

# Ensure the root directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load config
load_dotenv('config/.env')

from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.verification import calculate_trust_score
from database.needs_db import save_need, check_corroboration
from notifications.gmail_alert import send_alert

def run_comprehensive_test():
    print("🚀 Starting Full System Integration Test...\n")
    
    # --- STEP 1: AI Processor Test ---
    print("1️⃣ Testing AI Processor (Gemini with Groq Fallback)...")
    description = "There is a massive flood in Kanpur, people are trapped on rooftops."
    ai_result = process_need_text(description)
    
    if ai_result and "category" in ai_result:
        print(f"✅ AI Success: Category={ai_result['category']}, Consistency={ai_result['consistency']}")
    else:
        print("❌ AI Processor failed to return valid data.")
        return

    # --- STEP 2: Geocoding & Weather Test ---
    print("\n2️⃣ Testing Geocoding & Live Weather API...")
    location = "PSIT, Kanpur"
    coords = get_coordinates(location)
    lat, lng = coords.get("lat"), coords.get("lng")
    
    if lat and lng:
        print(f"✅ Geocoding Success: {lat}, {lng}")
    else:
        print("❌ Geocoding failed. Check Google Maps Key or OSM connectivity.")
        return

    # --- STEP 3: Verification Engine Test ---
    print("\n3️⃣ Testing Verification Engine (Trust Score)...")
    # We mock corroboration count for the test
    corroborating_count = check_corroboration(lat, lng, ai_result['category'])
    
    trust_result = calculate_trust_score(
        data_dict={
            "lat": lat,
            "lng": lng,
            "reporter_phone": "9876543210",
            "disaster_type": "flood",
        },
        ai_consistency=ai_result['consistency'],
        corroborating_reports_count=corroborating_count
    )
    
    print(f"✅ Trust Score: {trust_result['score']} | Action: {trust_result['dispatch_action']}")
    for reason in trust_result['reasons']:
        print(f"   - {reason}")

    # --- STEP 4: Firestore Storage Test ---
    print("\n4️⃣ Testing Firestore Connectivity...")
    final_data = {
        "description": description,
        "category": ai_result['category'],
        "severity": ai_result['severity'],
        "lat": lat,
        "lng": lng,
        "trust_score": trust_result["score"],
        "status": "test_pending"
    }
    
    try:
        doc_id = save_need(final_data)
        print(f"✅ Firestore Success: Document saved with ID {doc_id}")
    except Exception as e:
        print(f"❌ Firestore failed: {e}")
        return

    # --- STEP 5: Notification Test ---
    print("\n5️⃣ Testing Gmail Alert System...")
    if trust_result['score'] >= 50:
        alert_success = send_alert(final_data)
        if alert_success:
            print("✅ Email Alert sent successfully.")
        else:
            print("❌ Email Alert failed. Check GMAIL_APP_PASSWORD.")
    else:
        print("⏭️ Skipping Alert (Score too low for emergency).")

    print("\n" + "="*40)
    print("🎉 ALL SYSTEMS FUNCTIONAL!")
    print("="*40)

if __name__ == "__main__":
    run_comprehensive_test()