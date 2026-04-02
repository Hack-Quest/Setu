import googlemaps
import os
from dotenv import load_dotenv

load_dotenv('config/.env')

api_key = os.getenv("GOOGLE_MAPS_KEY")
client = googlemaps.Client(key=api_key) if api_key else None

def get_coordinates(address: str) -> dict:
    """
    Converts a text address into latitude and longitude using Google Maps.
    """
    if not client:
        print("Warning: GOOGLE_MAPS_KEY is missing. Add it to config/.env later.")
        return {"lat": None, "lng": None}

    try:
        result = client.geocode(address)
        
        if result:
            loc = result[0]["geometry"]["location"]
            return {"lat": loc["lat"], "lng": loc["lng"]}
        else:
            print(f"📍 Google Maps found no results for: {address}")
            
    except Exception as e:
        print(f"🚨 Google Maps API Error: {e}")
        
    return {"lat": None, "lng": None}


# --- TEST BLOCK ---
if __name__ == "__main__":
    print("Testing Geocoder...")
    test_address = "India Gate, New Delhi"
    coords = get_coordinates(test_address)
    print(f"Result for '{test_address}': {coords}")