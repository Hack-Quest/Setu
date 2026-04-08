import requests

def get_coordinates(address: str) -> dict:
    """
    Text address to maps using OpenStreetMap
    Alternate till google geocoding api issue gets fixed
    """

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q" : address,
            "format" : "json",
            "limit" : 1
        }

        headers={
            "User-Agent":"SetuApp"
        }

        response = requests.get(url, params=params, headers=headers)
        data = response.json()

        if data:
            return {
                "lat": float(data[0]["lat"]),
                "lng": float(data[0]["lon"])
            }
        else:
            print(f"No result for {address}")

    except Exception as e:
        print(f"Geocoder Error: {e}")

    # Default fallback coordinates (India Gate)
    return {"lat": 26.8467, "lng": 80.9462}

# --- TEST BLOCK ---
if __name__ == "__main__":
    print("Testing Free Geocoder...")
    test_address = "Kanpur, Uttar Pradesh"
    coords = get_coordinates(test_address)
    print(f"Result for '{test_address}': {coords}")
