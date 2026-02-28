"""
MandiMitra — DynamoDB utility functions shared across Lambdas.
"""
import os
import math
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from .constants import (
    PRICE_TABLE_NAME, MANDI_COORDINATES, TRANSPORT_COST_PER_QTL_PER_KM,
    MSP_RATES, PERISHABILITY_INDEX, STORAGE_COST_PER_DAY
)

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
table = dynamodb.Table(os.environ.get("PRICE_TABLE", PRICE_TABLE_NAME))


def query_prices(commodity: str, state: str, mandi: str = None, days: int = 7) -> list:
    """Query mandi prices for a commodity in a state, optionally filtered by mandi.
    If no recent data found, automatically falls back to searching all historical data.
    """
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    if days <= 0:
        start_date = "2000-01-01"  # Fetch all historical data
    else:
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    state_clean = state.upper().replace(" ", "_")
    pk = f"{commodity.upper()}#{state_clean}"

    if mandi:
        # Query specific mandi within date range
        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").between(
                f"{start_date}#{mandi.upper()}",
                f"{end_date}#{mandi.upper()}~"  # ~ sorts after all chars
            )
        )
    else:
        # Query all mandis in this state for this commodity
        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").between(
                f"{start_date}#",
                f"{end_date}#~"
            )
        )

    items = response.get("Items", [])

    # Fallback: if no recent data found, search all available data
    if not items and days > 0:
        fallback_pk = f"{commodity.strip().upper()}#{state.strip().upper().replace(' ', '_')}"
        fallback_response = table.query(
            KeyConditionExpression=Key("PK").eq(fallback_pk),
            ScanIndexForward=False,  # newest first
            Limit=20,
        )
        items = fallback_response.get("Items", [])

    # Convert Decimal to float for JSON serialization
    return [_decimal_to_float(item) for item in items]


def query_mandi_prices(mandi: str, days: int = 7) -> list:
    """Query all commodity prices for a specific mandi using GSI-1."""
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = table.query(
        IndexName="MANDI-INDEX",
        KeyConditionExpression=Key("mandi_name").eq(mandi.upper()) & Key("date_commodity").between(
            f"{start_date}#",
            f"{end_date}#~"
        )
    )
    return [_decimal_to_float(item) for item in response.get("Items", [])]


def get_nearby_mandis(lat: float, lon: float, radius_km: float, commodity: str = None) -> list:
    """Find mandis within radius_km of given coordinates."""
    nearby = []
    for mandi_name, (m_lat, m_lon) in MANDI_COORDINATES.items():
        dist = haversine_distance(lat, lon, m_lat, m_lon)
        if dist <= radius_km:
            entry = {
                "mandi": mandi_name,
                "distance_km": round(dist, 1),
                "latitude": m_lat,
                "longitude": m_lon,
            }
            # Optionally fetch latest price for this mandi
            if commodity:
                prices = query_prices(commodity, state="", mandi=mandi_name, days=3)
                if prices:
                    latest = max(prices, key=lambda x: x.get("SK", ""))
                    entry["modal_price"] = latest.get("modal_price")
                    entry["min_price"] = latest.get("min_price")
                    entry["max_price"] = latest.get("max_price")
                    entry["date"] = latest.get("arrival_date", "")
            nearby.append(entry)

    nearby.sort(key=lambda x: x["distance_km"])
    return nearby


def calculate_net_realization(price_per_qtl: float, distance_km: float, quantity_qtl: float = 1) -> float:
    """Calculate net price after transport costs."""
    transport_cost = distance_km * TRANSPORT_COST_PER_QTL_PER_KM
    return round(price_per_qtl - transport_cost, 2)


def get_price_trend(commodity: str, state: str, mandi: str, days: int = 30) -> dict:
    """Compute price trend statistics."""
    prices = query_prices(commodity, state, mandi, days)
    if not prices:
        return {"trend": "no_data", "data_points": 0}

    modal_prices = [p["modal_price"] for p in prices if p.get("modal_price")]
    if len(modal_prices) < 2:
        return {"trend": "insufficient_data", "data_points": len(modal_prices)}

    latest = modal_prices[-1]
    oldest = modal_prices[0]
    avg = sum(modal_prices) / len(modal_prices)
    change_pct = round(((latest - oldest) / oldest) * 100, 2)

    # Standard deviation for volatility
    variance = sum((p - avg) ** 2 for p in modal_prices) / len(modal_prices)
    std_dev = math.sqrt(variance)
    volatility = "low" if std_dev < avg * 0.05 else ("high" if std_dev > avg * 0.15 else "medium")

    if change_pct > 2:
        direction = "rising"
    elif change_pct < -2:
        direction = "falling"
    else:
        direction = "stable"

    return {
        "trend": direction,
        "change_pct": change_pct,
        "current_price": latest,
        "avg_price": round(avg, 2),
        "std_dev": round(std_dev, 2),
        "volatility": volatility,
        "data_points": len(modal_prices),
        "min_in_period": min(modal_prices),
        "max_in_period": max(modal_prices),
    }


def get_msp(commodity: str) -> dict:
    """Get MSP for a commodity (case-insensitive)."""
    # Try exact match first, then case-insensitive
    msp = MSP_RATES.get(commodity)
    if msp is None:
        for key, val in MSP_RATES.items():
            if key.lower() == commodity.lower():
                msp = val
                commodity = key  # Use canonical name
                break
    return {
        "commodity": commodity,
        "msp": msp,
        "year": "2025-26",
        "has_msp": msp is not None,
    }


def get_sell_recommendation_data(commodity: str, state: str, lat: float, lon: float, quantity: float, storage_available: bool) -> dict:
    """Gather all data needed for sell recommendation."""
    # Get nearby mandis with prices
    nearby = get_nearby_mandis(lat, lon, radius_km=150, commodity=commodity)

    # Get trend
    trend = get_price_trend(commodity, state, nearby[0]["mandi"] if nearby else "", days=30)

    # Get MSP
    msp = get_msp(commodity)

    # Get perishability
    perish = PERISHABILITY_INDEX.get(commodity, 3)

    # Get storage cost
    storage_cost = STORAGE_COST_PER_DAY.get(commodity, STORAGE_COST_PER_DAY["default"])

    # Calculate net realization for each mandi
    for m in nearby:
        if m.get("modal_price"):
            m["net_realization"] = calculate_net_realization(
                m["modal_price"], m["distance_km"], quantity
            )
            m["transport_cost_per_qtl"] = round(m["distance_km"] * TRANSPORT_COST_PER_QTL_PER_KM, 2)

    # Sort by net realization
    mandis_with_prices = [m for m in nearby if m.get("net_realization")]
    mandis_with_prices.sort(key=lambda x: x["net_realization"], reverse=True)

    return {
        "commodity": commodity,
        "quantity_qtl": quantity,
        "nearby_mandis": mandis_with_prices[:10],
        "best_mandi": mandis_with_prices[0] if mandis_with_prices else None,
        "trend": trend,
        "msp": msp,
        "perishability_index": perish,
        "storage_cost_per_day": storage_cost,
        "storage_available": storage_available,
    }


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates in km."""
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def _decimal_to_float(item: dict) -> dict:
    """Convert DynamoDB Decimal types to Python floats."""
    converted = {}
    for k, v in item.items():
        if isinstance(v, Decimal):
            converted[k] = float(v)
        elif isinstance(v, dict):
            converted[k] = _decimal_to_float(v)
        else:
            converted[k] = v
    return converted
