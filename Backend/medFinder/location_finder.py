from typing import Any, Dict
import requests
import overpass
import re


def extract_service_and_location(message: str):
    message = message.lower()
    services = ["pharmacy", "hospital", "clinic", "dentist", "laboratory", "eye center"]
    found_service = None
    found_location = None

    for s in services:
        if s in message:
            found_service = s
            break

    match = re.search(r"in ([A-Za-z ]+)", message)
    if match:
        found_location = match.group(1).strip()

    return {"service": found_service, "location": found_location}


def get_coordinates(place_name):
    """Get location from chat"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "limit": 1}
    headers = {
        "User-Agent": "MedFinder/1.0 (https://github.com/merytpeters/HNG-2025; contact: merytpeters@gmail.com)"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            return {"error": "Location not found."}
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return {"latitude": lat, "longitude": lon}
    except requests.RequestException as e:
        return {"error": f"Request failed: {e}"}
    except (ValueError, KeyError) as e:
        return {"error": f"Failed to parse response: {e}"}


def find_nearby_services(service, lat, lon):
    lat = float(lat)
    lon = float(lon)

    api = overpass.API(debug=True)
    query = f"""node["amenity"="{service}"](around:10000,{lat},{lon});"""
    print("Overpass Query:", query)

    try:
        data: Any = api.get(query, responseformat="json")  # type: ignore
        if not isinstance(data, dict):
            print("Unexpected data type from Overpass:", type(data))
            return []

        elements = data.get("elements", [])
        results = [
            {
                "name": e.get("tags", {}).get("name", "Unnamed"),
                "lat": e["lat"],
                "lon": e["lon"],
            }
            for e in elements
        ]
        print(f"Found {len(results)} {service}(s)")
        return results

    except Exception as e:
        print("Overpass query failed:", e)
        return []


if __name__ == "__main__":
    place = "Delta"
    print(get_coordinates(place))
    service = "pharmacy"
    lat = 33.3926893
    lon = -95.6749486
    print(find_nearby_services(service, lat, lon))
