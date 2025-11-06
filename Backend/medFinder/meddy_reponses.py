from .location_finder import (
    extract_service_and_location,
    get_coordinates,
    find_nearby_services,
)


def _pluralize(noun: str) -> str:
    """Return a simple English plural form of `noun`.

    Rules covered (simple):
    - words ending with 'y' preceded by a consonant -> replace 'y' with 'ies' (pharmacy -> pharmacies)
    - words ending with s, x, z, ch, sh -> add 'es' (bus -> buses)
    - otherwise add 's'

    This is intentionally small — for full coverage use a proper i18n/pluralization library.
    """
    n = noun.strip()
    if not n:
        return noun

    lower = n.lower()
    if lower.endswith(("ch", "sh")) or lower.endswith(("s", "x", "z")):
        return n + "es"
    if lower.endswith("y") and len(n) > 1 and lower[-2] not in "aeiou":
        return n[:-1] + "ies"
    return n + "s"


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
        return f"Sorry, I couldn't find any {data['service']} near {data['location']}. Could you repeat the location please ? Or be more specific"

    total = len(places)
    limit = 10
    shown = min(total, limit)

    service_label = _pluralize(data["service"])

    if total == 0:
        return (
            f"Sorry — I couldn't find any {service_label} within the immediate area around "
            f"{data['location']}. Try a more specific address or landmark, check the spelling, "
            f"or ask me to search a wider area."
        )

    msg = f"Here are {shown} of {total} {service_label} near {data['location']}:\n"

    for p in places[:limit]:
        name = p.get("name") or p.get("tags", {}).get("name") or "unnamed"
        location_text = (
            p.get("location")
            or p.get("tags", {}).get("addr:street")
            or p.get("tags", {}).get("addr:city")
            or ""
        )
        lat_p = p.get("lat") or p.get("latitude") or p.get("y") or "?"
        lon_p = p.get("lon") or p.get("longitude") or p.get("x") or "?"
        if location_text:
            msg += f"- {name} — {location_text} ({lat_p}, {lon_p})\n"
        else:
            msg += f"- {name} ({lat_p}, {lon_p})\n"

    if total > shown:
        msg += f"...and {total - shown} more not shown.\n"

    return msg
