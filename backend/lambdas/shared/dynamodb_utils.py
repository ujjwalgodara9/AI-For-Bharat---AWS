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
    MSP_RATES, PERISHABILITY_INDEX, STORAGE_COST_PER_DAY,
    STORAGE_TIPS, CROP_SEASONS, WEATHER_STORAGE_IMPACT,
    COMMODITY_TRANSLATIONS
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
        mandi_upper = mandi.upper().strip()
        # Query specific mandi within date range
        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").between(
                f"{start_date}#{mandi_upper}",
                f"{end_date}#{mandi_upper}~"
            )
        )
        items = response.get("Items", [])

        # Fallback: try with APMC suffix
        if not items:
            for suffix in [" APMC", "(GRAIN)", "(F&V)"]:
                candidate = f"{mandi_upper}{suffix}"
                response = table.query(
                    KeyConditionExpression=Key("PK").eq(pk) & Key("SK").between(
                        f"{start_date}#{candidate}",
                        f"{end_date}#{candidate}~"
                    )
                )
                items = response.get("Items", [])
                if items:
                    break

        # Fallback: search without date filter
        if not items:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(pk),
                ScanIndexForward=False,
                Limit=20,
            )
            all_items = response.get("Items", [])
            # Filter by mandi name containing the search term
            items = [i for i in all_items if mandi_upper in i.get("mandi_name", "")]
            if not items:
                # Try district match
                items = [i for i in all_items if mandi.strip().lower() in i.get("district", "").lower()]
            if not items:
                items = all_items  # Return whatever we have for this commodity+state
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
            ScanIndexForward=False,
            Limit=20,
        )
        items = fallback_response.get("Items", [])

    # Convert Decimal to float for JSON serialization
    return [_decimal_to_float(item) for item in items]


def query_mandi_prices(mandi: str, days: int = 7) -> list:
    """Query all commodity prices for a specific mandi using GSI-1.
    Falls back to district-level search and then all historical data."""
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    mandi_upper = mandi.upper().strip()

    # Try exact mandi name match first
    response = table.query(
        IndexName="MANDI-INDEX",
        KeyConditionExpression=Key("mandi_name").eq(mandi_upper) & Key("date_commodity").between(
            f"{start_date}#",
            f"{end_date}#~"
        )
    )
    items = response.get("Items", [])

    # Fallback 1: try with common suffixes (APMC, F&V, etc.)
    if not items:
        for suffix in ["", " APMC", "(GRAIN)", "(F&V)"]:
            candidate = f"{mandi_upper}{suffix}"
            response = table.query(
                IndexName="MANDI-INDEX",
                KeyConditionExpression=Key("mandi_name").eq(candidate),
                ScanIndexForward=False,
                Limit=50,
            )
            items = response.get("Items", [])
            if items:
                break

    # Fallback 2: search by district (full table scan with filter — no Limit)
    if not items:
        scan_kwargs = {
            "FilterExpression": Attr("district").eq(mandi.strip()) | Attr("district").eq(mandi.strip().title()),
        }
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        # Paginate scan if needed
        while not items and "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

    # Fallback 3: partial mandi name match via scan
    if not items:
        scan_kwargs = {
            "FilterExpression": Attr("mandi_name").contains(mandi_upper),
        }
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        while not items and "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

    return [_decimal_to_float(item) for item in items]


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
            # Optionally fetch latest price for this mandi using MANDI-INDEX GSI
            if commodity:
                mandi_prices = query_mandi_prices(mandi_name, days=3)
                # Filter to the specific commodity
                commodity_prices = [
                    p for p in mandi_prices
                    if p.get("commodity", "").upper() == commodity.upper()
                ]
                if commodity_prices:
                    latest = max(commodity_prices, key=lambda x: x.get("arrival_date", ""))
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


def _predict_prices(daily_prices: list) -> list:
    """Simple linear regression on daily prices to predict next 1-3 days."""
    if len(daily_prices) < 3:
        return []

    # x = day index, y = price
    n = len(daily_prices)
    xs = list(range(n))
    ys = [p["price"] for p in daily_prices]

    # Linear regression: y = mx + b
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return []

    m = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - m * sum_x) / n

    # Predict next 1-3 days
    last_date = datetime.strptime(daily_prices[-1]["date"], "%Y-%m-%d")
    predictions = []
    for i in range(1, 4):
        pred_price = round(m * (n - 1 + i) + b, 2)
        pred_date = (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
        predictions.append({"date": pred_date, "predicted_price": max(pred_price, 0)})

    return predictions


def _get_season_context(commodity: str) -> dict:
    """Determine current season context for a commodity."""
    current_month = datetime.utcnow().month
    season = CROP_SEASONS.get(commodity, {})

    if not season:
        return {"is_harvest": False, "is_sowing": False, "season_type": "Unknown", "note": "Season data not available"}

    is_harvest = current_month in season.get("harvest", [])
    is_sowing = current_month in season.get("sowing", [])

    if is_harvest:
        note = f"Peak harvest season for {commodity} ({season['type']}). High supply in mandis — prices typically under pressure."
        note_hi = f"{commodity} की कटाई का मौसम ({season['type']})। मंडी में आवक ज्यादा — भाव पर दबाव रहता है।"
    elif is_sowing:
        note = f"Sowing season for {commodity}. Off-season supply — prices may hold steady or rise."
        note_hi = f"{commodity} की बुवाई का मौसम। ऑफ-सीज़न आपूर्ति — भाव स्थिर या बढ़ सकते हैं।"
    else:
        note = f"Normal season for {commodity} ({season['type']}). Regular market conditions."
        note_hi = f"{commodity} के लिए सामान्य मौसम ({season['type']})। नियमित बाज़ार स्थिति।"

    return {
        "is_harvest": is_harvest,
        "is_sowing": is_sowing,
        "season_type": season.get("type", "Unknown"),
        "note": note,
        "note_hi": note_hi,
    }


def _assess_weather_storage_risk(weather_data: dict, commodity: str) -> dict:
    """Assess how weather affects crop storage and shelf life."""
    if not weather_data or "error" in weather_data:
        return {"condition": "normal", "shelf_life_factor": 1.0, "risk_note": "Weather data not available", "risk_note_hi": "मौसम डेटा उपलब्ध नहीं"}

    advisory = weather_data.get("advisory", {})
    total_rain = advisory.get("total_rain_5d", 0)
    forecast = weather_data.get("forecast", [])

    # Determine max temperature in next 5 days
    max_temp = 0
    min_temp = 100
    for day in forecast:
        max_temp = max(max_temp, day.get("max_temp", 0))
        min_temp = min(min_temp, day.get("min_temp", 100))

    # Classify weather condition
    if total_rain > 50 or max_temp > 42:
        condition = "high_rain" if total_rain > 50 else "high_heat"
    elif total_rain > 20 or max_temp > 38:
        condition = "moderate_rain" if total_rain > 20 else "high_heat"
    elif min_temp < 5:
        condition = "cold"
    else:
        condition = "normal"

    impact = WEATHER_STORAGE_IMPACT.get(condition, WEATHER_STORAGE_IMPACT["normal"])

    return {
        "condition": condition,
        "shelf_life_factor": impact["shelf_life_factor"],
        "risk_note": impact["risk"],
        "risk_note_hi": impact.get("risk_hi", impact["risk"]),
        "total_rain_5d": round(total_rain, 1),
        "max_temp_5d": round(max_temp, 1),
        "min_temp_5d": round(min_temp, 1),
    }


def get_sell_recommendation_data(commodity: str, state: str, lat: float, lon: float,
                                  quantity: float, storage_available: bool,
                                  weather_data: dict = None) -> dict:
    """Comprehensive sell recommendation with price prediction, weather, season, and storage advice."""
    # 1. Get nearby mandis with prices
    nearby = get_nearby_mandis(lat, lon, radius_km=150, commodity=commodity)

    # 2. Get 7-day price history for daily breakdown
    best_mandi_name = nearby[0]["mandi"] if nearby else ""
    prices_7d = query_prices(commodity, state, best_mandi_name, days=7)

    # Build daily price array (group by date, take modal price)
    daily_map = {}
    for p in prices_7d:
        d = p.get("arrival_date", "")
        mp = p.get("modal_price")
        if d and mp:
            if d not in daily_map or mp > daily_map[d]:
                daily_map[d] = mp
    daily_prices = sorted([{"date": d, "price": p} for d, p in daily_map.items()], key=lambda x: x["date"])

    # 3. Price prediction (linear regression on 7-day data)
    predicted_prices = _predict_prices(daily_prices)
    prediction_direction = "stable"
    if predicted_prices and daily_prices:
        current = daily_prices[-1]["price"]
        predicted = predicted_prices[0]["predicted_price"]
        change = ((predicted - current) / current) * 100 if current > 0 else 0
        if change > 1.5:
            prediction_direction = "rising"
        elif change < -1.5:
            prediction_direction = "falling"

    # 4. Get 30-day trend
    trend = get_price_trend(commodity, state, best_mandi_name, days=30)

    # 5. Get MSP
    msp = get_msp(commodity)

    # 6. Season context
    season_context = _get_season_context(commodity)

    # 7. Weather storage risk
    weather_risk = _assess_weather_storage_risk(weather_data, commodity)

    # 8. Perishability and base shelf life
    perish = PERISHABILITY_INDEX.get(commodity, 3)
    base_shelf_life = {
        1: 180, 2: 90, 3: 60, 4: 30, 5: 14, 6: 10, 7: 7, 8: 5, 9: 3, 10: 1
    }.get(perish, 30)

    # 9. Weather-adjusted shelf life
    weather_factor = weather_risk.get("shelf_life_factor", 1.0)
    adjusted_shelf_life = max(1, int(base_shelf_life * weather_factor))

    # 10. Storage cost
    storage_cost = STORAGE_COST_PER_DAY.get(commodity, STORAGE_COST_PER_DAY["default"])

    # 11. Calculate net realization for each mandi
    for m in nearby:
        if m.get("modal_price"):
            m["net_realization"] = calculate_net_realization(
                m["modal_price"], m["distance_km"], quantity
            )
            m["transport_cost_per_qtl"] = round(m["distance_km"] * TRANSPORT_COST_PER_QTL_PER_KM, 2)

    mandis_with_prices = sorted(
        [m for m in nearby if m.get("net_realization")],
        key=lambda x: x["net_realization"], reverse=True
    )

    # 12. Recommended hold days (considers trend, prediction, weather, season)
    recommended_hold_days = 0
    trend_dir = trend.get("trend", "no_data")

    if storage_available and adjusted_shelf_life > 1:
        if trend_dir == "rising" or prediction_direction == "rising":
            recommended_hold_days = min(int(adjusted_shelf_life * 0.3), 15)
        elif trend_dir == "stable" and perish <= 3:
            recommended_hold_days = min(int(adjusted_shelf_life * 0.2), 10)

        # Reduce hold if harvest season (oversupply → prices may drop)
        if season_context.get("is_harvest") and recommended_hold_days > 0:
            recommended_hold_days = max(1, recommended_hold_days // 2)

        # Don't recommend hold if weather is bad for storage
        if weather_risk["condition"] in ("high_rain", "high_heat") and perish >= 5:
            recommended_hold_days = 0

    total_storage_cost = storage_cost * recommended_hold_days * quantity if recommended_hold_days > 0 else 0

    # 13. Storage tips
    tips = STORAGE_TIPS.get(commodity, {
        "method": "Store in dry, ventilated area.",
        "warehouse": False,
        "ideal_temp": "25-30°C",
        "humidity": "<65%",
        "method_hi": "सूखी, हवादार जगह में रखें।",
    })
    warehouse_recommended = tips.get("warehouse", False) and recommended_hold_days > 3 and storage_available

    # 14. Build factual reasoning
    reasons = []
    reasons_hi = []

    # Price trend reason
    if trend_dir == "rising":
        reasons.append(f"Price trending UP {abs(trend.get('change_pct', 0)):.1f}% over 30 days")
        reasons_hi.append(f"पिछले 30 दिनों में भाव {abs(trend.get('change_pct', 0)):.1f}% बढ़ा")
    elif trend_dir == "falling":
        reasons.append(f"Price trending DOWN {abs(trend.get('change_pct', 0)):.1f}% over 30 days")
        reasons_hi.append(f"पिछले 30 दिनों में भाव {abs(trend.get('change_pct', 0)):.1f}% गिरा")
    elif trend_dir == "stable":
        reasons.append("Price stable over 30 days")
        reasons_hi.append("पिछले 30 दिनों में भाव स्थिर")

    # Prediction reason
    if predicted_prices:
        pred = predicted_prices[0]["predicted_price"]
        cur = daily_prices[-1]["price"] if daily_prices else 0
        if cur > 0:
            pct = ((pred - cur) / cur) * 100
            reasons.append(f"Tomorrow's predicted price: Rs.{pred:.0f} ({pct:+.1f}%)")
            reasons_hi.append(f"कल का अनुमानित भाव: ₹{pred:.0f} ({pct:+.1f}%)")

    # Season reason
    reasons.append(season_context["note"])
    reasons_hi.append(season_context["note_hi"])

    # Weather reason
    if weather_risk["condition"] != "normal":
        reasons.append(f"Weather alert: {weather_risk['risk_note']}")
        reasons_hi.append(f"मौसम चेतावनी: {weather_risk['risk_note_hi']}")
    else:
        reasons.append("Weather conditions normal — safe for storage and transport")
        reasons_hi.append("मौसम सामान्य — भंडारण और ढुलाई के लिए सुरक्षित")

    # MSP reason
    if msp.get("has_msp") and mandis_with_prices:
        best_price = mandis_with_prices[0].get("modal_price", 0)
        msp_val = msp["msp"]
        if best_price > msp_val:
            reasons.append(f"Current price Rs.{best_price:.0f} is ABOVE MSP Rs.{msp_val}")
            reasons_hi.append(f"मौजूदा भाव ₹{best_price:.0f} MSP ₹{msp_val} से ऊपर है")
        else:
            reasons.append(f"Current price Rs.{best_price:.0f} is BELOW MSP Rs.{msp_val}")
            reasons_hi.append(f"मौजूदा भाव ₹{best_price:.0f} MSP ₹{msp_val} से नीचे है")

    # Shelf life reason
    if adjusted_shelf_life != base_shelf_life:
        reasons.append(f"Shelf life reduced from {base_shelf_life} to {adjusted_shelf_life} days due to weather")
        reasons_hi.append(f"मौसम के कारण शेल्फ लाइफ {base_shelf_life} से घटकर {adjusted_shelf_life} दिन हुई")

    return {
        "commodity": commodity,
        "quantity_qtl": quantity,
        "nearby_mandis": mandis_with_prices[:10],
        "best_mandi": mandis_with_prices[0] if mandis_with_prices else None,
        "trend": trend,
        "msp": msp,
        "perishability_index": perish,
        "shelf_life_days": base_shelf_life,
        "shelf_life_adjusted": adjusted_shelf_life,
        "recommended_hold_days": recommended_hold_days,
        "storage_cost_per_day": storage_cost,
        "total_storage_cost_if_held": round(total_storage_cost, 2),
        "storage_available": storage_available,
        # New fields
        "daily_prices": daily_prices,
        "predicted_prices": predicted_prices,
        "prediction_direction": prediction_direction,
        "season_context": season_context,
        "weather_risk": weather_risk,
        "storage_tips": {
            "method": tips.get("method", ""),
            "method_hi": tips.get("method_hi", ""),
            "warehouse_recommended": warehouse_recommended,
            "ideal_temp": tips.get("ideal_temp", ""),
            "humidity": tips.get("humidity", ""),
        },
        "reasons": reasons,
        "reasons_hi": reasons_hi,
    }


def list_available_commodities(state: str = None) -> list:
    """List all unique commodities available in the database, optionally filtered by state."""
    commodities = set()
    scan_kwargs = {"ProjectionExpression": "commodity, #s",
                   "ExpressionAttributeNames": {"#s": "state"}}

    if state:
        scan_kwargs["FilterExpression"] = Attr("state").eq(state)

    response = table.scan(**scan_kwargs)
    for item in response.get("Items", []):
        commodities.add(item.get("commodity", ""))

    # Handle pagination
    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            commodities.add(item.get("commodity", ""))

    return sorted([c for c in commodities if c])


def list_available_mandis(state: str = None) -> list:
    """List all unique mandis available in the database, optionally filtered by state."""
    mandis = {}  # mandi_name -> {state, district}
    scan_kwargs = {"ProjectionExpression": "mandi_name, #s, district",
                   "ExpressionAttributeNames": {"#s": "state"}}

    if state:
        scan_kwargs["FilterExpression"] = Attr("state").eq(state)

    response = table.scan(**scan_kwargs)
    for item in response.get("Items", []):
        name = item.get("mandi_name", "")
        if name and name not in mandis:
            mandis[name] = {
                "mandi": name,
                "state": item.get("state", ""),
                "district": item.get("district", ""),
            }

    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            name = item.get("mandi_name", "")
            if name and name not in mandis:
                mandis[name] = {
                    "mandi": name,
                    "state": item.get("state", ""),
                    "district": item.get("district", ""),
                }

    return sorted(mandis.values(), key=lambda x: (x["state"], x["mandi"]))


def list_available_states() -> list:
    """List all unique states available in the database."""
    states = set()
    scan_kwargs = {"ProjectionExpression": "#s",
                   "ExpressionAttributeNames": {"#s": "state"}}

    response = table.scan(**scan_kwargs)
    for item in response.get("Items", []):
        states.add(item.get("state", ""))

    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            states.add(item.get("state", ""))

    return sorted([s for s in states if s])


def list_commodities_with_translations(state: str = None) -> list:
    """Return commodities available in DB for a state, with Hindi translations."""
    commodities = list_available_commodities(state)
    result = []
    for c in commodities:
        result.append({
            "en": c,
            "hi": COMMODITY_TRANSLATIONS.get(c, c),
        })
    return result


def get_mandi_profile(mandi: str, days: int = 7) -> dict:
    """Get comprehensive mandi profile — all commodities, prices, and metadata."""
    mandi_upper = mandi.upper().strip()

    # Query using MANDI-INDEX GSI
    try:
        response = table.query(
            IndexName="MANDI-INDEX",
            KeyConditionExpression=Key("mandi_name").eq(mandi_upper),
            ScanIndexForward=False,
            Limit=100,
        )
        items = response.get("Items", [])
    except Exception:
        items = []

    # Fallback: try with APMC suffix and partial match
    if not items:
        for suffix in [" APMC", "(GRAIN)", "(F&V)"]:
            try:
                response = table.query(
                    IndexName="MANDI-INDEX",
                    KeyConditionExpression=Key("mandi_name").eq(f"{mandi_upper}{suffix}"),
                    ScanIndexForward=False,
                    Limit=100,
                )
                items = response.get("Items", [])
                if items:
                    break
            except Exception:
                continue

    if not items:
        # Full scan fallback with partial match
        response = table.scan(
            FilterExpression=Attr("mandi_name").contains(mandi_upper) |
                           Attr("district").eq(mandi.strip()),
            Limit=200,
        )
        items = response.get("Items", [])

    items = [_decimal_to_float(i) for i in items]

    # Group by commodity and get latest price
    commodity_prices = {}
    for item in items:
        commodity = item.get("commodity", "")
        if commodity not in commodity_prices or item.get("arrival_date", "") > commodity_prices[commodity].get("arrival_date", ""):
            commodity_prices[commodity] = item

    # Sort by modal_price descending
    sorted_commodities = sorted(
        commodity_prices.values(),
        key=lambda x: x.get("modal_price", 0),
        reverse=True
    )

    # Get mandi metadata
    first_item = items[0] if items else {}
    mandi_name = first_item.get("mandi_name", mandi_upper)
    district = first_item.get("district", "")
    state = first_item.get("state", "")
    coords = MANDI_COORDINATES.get(mandi.strip().title(), None)

    return {
        "mandi_name": mandi_name,
        "district": district,
        "state": state,
        "coordinates": {"latitude": coords[0], "longitude": coords[1]} if coords else None,
        "total_commodities_traded": len(sorted_commodities),
        "commodities": sorted_commodities[:20],
        "data_source": "Agmarknet (data.gov.in)",
        "agmarknet_info": {
            "portal": "https://agmarknet.gov.in",
            "data_api": "https://data.gov.in",
            "update_schedule": "Daily by 5:00 PM IST (per DMI guidelines)",
            "coverage": "2000+ APMC mandis across India",
            "fields": "commodity, variety, min_price, max_price, modal_price, arrival_date",
        },
        "total_records_found": len(items),
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
