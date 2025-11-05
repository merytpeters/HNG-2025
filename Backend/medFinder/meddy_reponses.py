from .location_finder import (
    extract_service_and_location,
    get_coordinates,
    find_nearby_services,
)


async def meddy_reply(message: str) -> str:
    data = await extract_service_and_location(message)

    if not data["service"]:
        return "Please tell me what service you're looking for — a pharmacy, hospital, or clinic?"
    if not data["location"]:
        return f"Where would you like to find a {data['service']}?"

    coords = await get_coordinates(data["location"])
    if "error" in coords:
        return "Sorry, I couldn't find that location."

    lat, lon = coords["latitude"], coords["longitude"]
    places = await find_nearby_services(data["service"], lat, lon)

    if not places:
        return f"Sorry, I couldn't find any {data['service']} near {data['location']}."

    msg = f"Here are {len(places)} {data['service']}s near {data['location']}:\n"
    for p in places[:5]:
        msg += f"- {p['name']} ({p['lat']}, {p['lon']})\n"
    return msg
