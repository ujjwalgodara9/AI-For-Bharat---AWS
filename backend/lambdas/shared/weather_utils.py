"""
MandiMitra — Weather utilities using Open-Meteo API (free, no key needed).
Provides agricultural weather advisory for farmers.
"""
import json
import urllib.request
import urllib.parse
from .constants import MANDI_COORDINATES
from .geocoding import get_coordinates


# WMO weather codes to descriptions
WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def get_weather_advisory(location: str, latitude: float = None, longitude: float = None) -> dict:
    """Get 5-day weather forecast + agricultural advisory for a location."""
    # Resolve coordinates
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
    else:
        coords = get_coordinates(location, fallback_dict=MANDI_COORDINATES)
        if coords:
            lat, lon = coords
        else:
            return {"error": f"Location '{location}' not found. Try a major city name."}

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "current_weather": "true",
        "timezone": "Asia/Kolkata",
        "forecast_days": 5,
    }

    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "MandiMitra/1.0")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Weather API error: {str(e)}"}

    current = data.get("current_weather", {})
    daily = data.get("daily", {})

    # Build forecast
    forecast = []
    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    codes = daily.get("weathercode", [])
    wind = daily.get("windspeed_10m_max", [])

    for i in range(len(dates)):
        forecast.append({
            "date": dates[i],
            "max_temp": max_temps[i] if i < len(max_temps) else None,
            "min_temp": min_temps[i] if i < len(min_temps) else None,
            "precipitation_mm": precip[i] if i < len(precip) else 0,
            "weather": WMO_CODES.get(codes[i] if i < len(codes) else 0, "Unknown"),
            "wind_kmh": wind[i] if i < len(wind) else 0,
        })

    # Generate agricultural advisory
    advisory = generate_agri_advisory(forecast, current)

    return {
        "location": location,
        "current": {
            "temperature": current.get("temperature"),
            "windspeed": current.get("windspeed"),
            "weather": WMO_CODES.get(current.get("weathercode", 0), "Unknown"),
        },
        "forecast": forecast,
        "advisory": advisory,
    }


def generate_agri_advisory(forecast: list, current: dict) -> dict:
    """Generate agricultural advisory based on weather forecast."""
    alerts = []
    recommendations = []
    sell_impact = "neutral"

    total_rain = sum(f.get("precipitation_mm", 0) or 0 for f in forecast)
    max_temp = max((f.get("max_temp", 0) or 0 for f in forecast), default=0)
    min_temp = min((f.get("min_temp", 99) or 99 for f in forecast), default=99)
    has_storm = any("storm" in f.get("weather", "").lower() for f in forecast)
    has_heavy_rain = any((f.get("precipitation_mm", 0) or 0) > 20 for f in forecast)

    # Rain alerts
    if total_rain > 50:
        alerts.append("Heavy rainfall expected in next 5 days")
        recommendations.append("Sell perishable crops (tomato, onion) immediately before rain")
        recommendations.append("Ensure proper storage for grains — keep dry")
        sell_impact = "sell_perishable_now"
    elif total_rain > 20:
        alerts.append("Moderate rainfall expected")
        recommendations.append("Plan mandi visits on dry days")
        recommendations.append("Cover stored crops with tarpaulin")
    elif total_rain < 2:
        recommendations.append("Dry weather — good conditions for transport to mandi")

    # Temperature alerts
    if max_temp > 42:
        alerts.append(f"Extreme heat alert: up to {max_temp}°C")
        recommendations.append("Transport crops early morning to avoid heat damage")
        recommendations.append("Perishable crops may spoil faster — sell quickly")
        sell_impact = "sell_perishable_now"
    elif max_temp > 38:
        alerts.append(f"High temperature: up to {max_temp}°C")
        recommendations.append("Irrigate crops in evening hours")

    if min_temp < 5:
        alerts.append(f"Cold weather alert: down to {min_temp}°C")
        recommendations.append("Protect crops from frost — use covering")

    # Storm alerts
    if has_storm:
        alerts.append("Thunderstorm warning")
        recommendations.append("Avoid open field work during storms")
        recommendations.append("Harvest ready crops before the storm if possible")
        sell_impact = "urgent_harvest"

    if has_heavy_rain:
        recommendations.append("Roads may be affected — check mandi access routes")

    if not alerts:
        alerts.append("Weather looks favorable for next 5 days")

    if not recommendations:
        recommendations.append("Good weather for mandi visits and crop transport")
        recommendations.append("Normal farming operations can continue")

    return {
        "alerts": alerts,
        "recommendations": recommendations,
        "sell_impact": sell_impact,
        "total_rain_5d": round(total_rain, 1),
        "temp_range": f"{min_temp}°C to {max_temp}°C",
    }
