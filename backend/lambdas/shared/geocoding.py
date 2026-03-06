"""
Geocoding utility for MandiMitra.
Uses free Nominatim (OpenStreetMap) API to resolve mandi/city names to coordinates.
Falls back to hardcoded MANDI_COORDINATES when API is unavailable.
"""
import logging
import urllib.request
import urllib.parse
import json
from functools import lru_cache

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MandiMitra/1.0 (agricultural-market-app)"


@lru_cache(maxsize=256)
def geocode_location(location_name: str, state: str = None) -> tuple:
    """
    Geocode a location name to (latitude, longitude) using Nominatim.

    Args:
        location_name: City, mandi, or place name (e.g., "Hanumangarh")
        state: Optional state for disambiguation (e.g., "Rajasthan")

    Returns:
        (latitude, longitude) tuple, or None if not found.
    """
    query = location_name.strip()
    if state:
        query = f"{query}, {state}, India"
    else:
        query = f"{query}, India"

    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "in",
    })
    url = f"{NOMINATIM_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                logger.info(f"Geocoded '{location_name}' → ({lat}, {lon})")
                return (lat, lon)
    except Exception as e:
        logger.warning(f"Geocoding failed for '{location_name}': {e}")

    return None


def get_coordinates(location_name: str, state: str = None, fallback_dict: dict = None) -> tuple:
    """
    Get coordinates for a location. Tries:
    1. Hardcoded fallback_dict (fast, no network)
    2. Nominatim geocoding API (handles any location)

    Args:
        location_name: City or mandi name
        state: Optional state for disambiguation
        fallback_dict: Dict of {name: (lat, lon)} for fast lookup (e.g., MANDI_COORDINATES)

    Returns:
        (latitude, longitude) tuple, or None if not found.
    """
    # Try hardcoded lookup first (fast, no network call)
    if fallback_dict:
        # Try exact match (title case)
        coords = fallback_dict.get(location_name.strip().title())
        if coords:
            return coords
        # Try case-insensitive match
        name_lower = location_name.strip().lower()
        for key, val in fallback_dict.items():
            if key.lower() == name_lower:
                return val

    # Fall back to geocoding API
    return geocode_location(location_name, state)
