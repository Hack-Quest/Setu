import os
import requests
import googlemaps
from dotenv import load_dotenv

load_dotenv('config/.env')

def get_coordinates(address: str) -> dict:
    """
    Attempts to geocode an address using Google Maps.
    Automatically falls back to OpenStreetMap if Google fails or is missing a key.
    """
    api_key = os.getenv("GOOGLE_MAPS_KEY")

    # try google maps
    if api_key:
        try:
            client = googlemaps.Client(key=api_key)
            result = client.geocode(address)
            
            if result:
                loc = result[0]["geometry"]["location"]
                # print("Geocoded via Google Maps")
                return {"lat": loc["lat"], "lng": loc["lng"]}
            else:
                print(f"Google Maps found no results for: {address}. Trying OSM...")
                
        except Exception as e:
            print(f"Google Maps API failed ({e}). Falling back to OSM...")
    else:
         print("GOOGLE_MAPS_KEY is missing. Defaulting to OpenStreetMap...")


    # fallback to openstreetmap
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "Setu" 
        }

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status() # Catches HTTP errors
        data = response.json()

        if data:
            # print("Geocoded via OpenStreetMap")
            return {
                "lat": float(data[0]["lat"]), 
                "lng": float(data[0]["lon"])
            }
        else:
            print(f"📍 OSM also found no results for: {address}")
            
    except Exception as e:
        print(f"🚨 OSM Geocoder Error: {e}")


    # If both APIs fail, return None so the database knows it's a bad address
    return {"lat": None, "lng": None}


# --- TEST BLOCK ---
if __name__ == "__main__":
    print("Testing Hybrid Geocoder...\n")
    
    # Test 1: A good address
    address_1 = "PSIT,Kanpur"
    print(f"Searching: {address_1}")
    print(f"Result: {get_coordinates(address_1)}\n")
    
    # Test 2: A terrible address to test the safety net
    address_2 = "asdfghjklqwertyuiop"
    print(f"Searching: {address_2}")
    print(f"Result: {get_coordinates(address_2)}")