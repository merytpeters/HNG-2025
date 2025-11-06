from typing import Any
import overpass
import re
import httpx
import asyncio


async def extract_service_and_location(message: str):
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


async def get_coordinates(place_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "limit": 1}
    headers = {
        "User-Agent": "MedFinder/1.0 (https://github.com/merytpeters/HNG-2025; contact: merytpeters@gmail.com)"
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params, headers=headers)
            data = response.json()
        if not data:
            return {"error": "Location not found."}
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return {"latitude": lat, "longitude": lon}
    except Exception as e:
        return {"error": f"Request failed: {e}"}


async def find_nearby_services(service, lat, lon):
    lat = float(lat)
    lon = float(lon)
    query = f"""node["amenity"="{service}"](around:10000,{lat},{lon});"""
    print("Overpass Query:", query)
    api = overpass.API(debug=True)

    def sync_query():
        try:
            data: Any = api.get(query, responseformat="json")  # type: ignore
            if not isinstance(data, dict):
                print("Unexpected data type from Overpass:", type(data))
                return []

            elements = data.get("elements", [])
            results = []
            for e in elements:
                tags = e.get("tags", {}) or {}
                addr_parts = []
                for k in (
                    "addr:housenumber",
                    "addr:street",
                    "addr:suburb",
                    "addr:city",
                    "addr:postcode",
                ):
                    v = tags.get(k)
                    if v:
                        addr_parts.append(v)

                location_str = ", ".join(addr_parts) if addr_parts else None

                results.append(
                    {
                        "name": tags.get("name", "Unnamed"),
                        "lat": e.get("lat"),
                        "lon": e.get("lon"),
                        "location": location_str,
                        "tags": tags,
                    }
                )
            print(f"Found {len(results)} {service}(s)")
            return results

        except Exception as e:
            print("Overpass query failed:", e)
            return []

    results = await asyncio.to_thread(sync_query)
    return results


if __name__ == "__main__":
    import sys

    async def main():
        # Allow passing place name on the command line for reproducible tests
        place = sys.argv[1] if len(sys.argv) > 1 else "Delta"
        coords = await get_coordinates(place)
        print(coords)

        service = "pharmacy"
        if isinstance(coords, dict) and "latitude" in coords and "longitude" in coords:
            lat = coords["latitude"]
            lon = coords["longitude"]
        else:
            lat = 33.3926893
            lon = -95.6749486

        nearby = await find_nearby_services(service, lat, lon)
        print(nearby)

    asyncio.run(main())
