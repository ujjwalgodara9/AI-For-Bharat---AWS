"""
MandiMitra — Price Query Lambda
Direct price lookup endpoint (bypasses Bedrock Agent for fast simple queries).
Also serves as Action Group Lambda for Bedrock Agent tool calls.
"""
import os
import json
import logging
import sys

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.dynamodb_utils import (
    query_prices, query_mandi_prices, get_price_trend, get_msp,
    get_nearby_mandis, calculate_net_realization,
    get_sell_recommendation_data,
    list_available_commodities, list_available_mandis, list_available_states
)
from shared.constants import MANDI_COORDINATES

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Handles both:
    1. API Gateway direct calls (GET /api/prices/{commodity})
    2. Bedrock Agent Action Group invocations
    """
    # Check if this is a Bedrock Agent Action Group call
    if "actionGroup" in event:
        return handle_agent_action(event)

    # Otherwise, handle as API Gateway request
    return handle_api_request(event)


def handle_api_request(event):
    """Handle direct API Gateway request."""
    path_params = event.get("pathParameters", {}) or {}
    query_params = event.get("queryStringParameters", {}) or {}

    commodity = path_params.get("commodity", "").strip()
    if not commodity:
        return api_response(400, {"error": "commodity path parameter is required"})

    state = query_params.get("state", "Madhya Pradesh")
    mandi = query_params.get("mandi", None)
    days = int(query_params.get("days", "7"))

    # Fetch prices
    prices = query_prices(commodity, state, mandi, days)

    # Fetch trend
    trend = get_price_trend(commodity, state, mandi or "", days)

    # Fetch MSP
    msp = get_msp(commodity)

    return api_response(200, {
        "commodity": commodity,
        "state": state,
        "mandi": mandi,
        "days": days,
        "prices": prices[-20:],  # Last 20 entries
        "trend": trend,
        "msp": msp,
        "record_count": len(prices),
    })


def handle_agent_action(event):
    """Handle Bedrock Agent Action Group invocation."""
    action_group = event.get("actionGroup", "")
    function = event.get("function", "")
    parameters = event.get("parameters", [])

    # Convert parameters list to dict
    params = {p["name"]: p["value"] for p in parameters}

    logger.info(f"Agent action: {action_group}/{function} params={params}")

    try:
        if function == "query_mandi_prices":
            commodity = params.get("commodity", "")
            state = params.get("state", "Madhya Pradesh")
            mandi = params.get("mandi", None)
            days = int(params.get("days", "7"))

            prices = query_prices(commodity, state, mandi, days)
            trend = get_price_trend(commodity, state, mandi or "", days)
            msp = get_msp(commodity)

            result = {
                "prices": prices[-10:],
                "trend": trend,
                "msp": msp,
                "record_count": len(prices),
            }

        elif function == "get_nearby_mandis":
            lat = float(params.get("latitude", "22.7196"))
            lon = float(params.get("longitude", "75.8577"))
            radius = float(params.get("radius_km", "100"))
            commodity = params.get("commodity", "")

            mandis = get_nearby_mandis(lat, lon, radius, commodity)

            # Calculate net realization for each
            for m in mandis:
                if m.get("modal_price"):
                    m["net_realization"] = calculate_net_realization(
                        m["modal_price"], m["distance_km"]
                    )

            result = {"nearby_mandis": mandis[:10]}

        elif function == "get_price_trend":
            commodity = params.get("commodity", "")
            state = params.get("state", "Madhya Pradesh")
            mandi = params.get("mandi", "")
            days = int(params.get("days", "30"))

            result = get_price_trend(commodity, state, mandi, days)

        elif function == "get_msp":
            commodity = params.get("commodity", "")
            result = get_msp(commodity)

        elif function == "calculate_transport_cost":
            origin_lat = float(params.get("origin_lat", "0"))
            origin_lon = float(params.get("origin_lon", "0"))
            dest_mandi = params.get("dest_mandi", "")
            quantity = float(params.get("quantity_qtl", "1"))

            if dest_mandi in MANDI_COORDINATES:
                d_lat, d_lon = MANDI_COORDINATES[dest_mandi]
                from shared.dynamodb_utils import haversine_distance
                distance = haversine_distance(origin_lat, origin_lon, d_lat, d_lon)
                cost_per_qtl = round(distance * 0.8, 2)
                result = {
                    "mandi": dest_mandi,
                    "distance_km": distance,
                    "cost_per_quintal": cost_per_qtl,
                    "total_cost": round(cost_per_qtl * quantity, 2),
                }
            else:
                result = {"error": f"Mandi '{dest_mandi}' coordinates not found"}

        elif function == "get_all_prices_at_mandi":
            mandi = params.get("mandi", "")
            days = int(params.get("days", "7"))

            prices = query_mandi_prices(mandi, days)

            # Group by commodity
            by_commodity = {}
            for p in prices:
                comm = p.get("commodity", "Unknown")
                if comm not in by_commodity or p.get("modal_price", 0) > by_commodity[comm].get("modal_price", 0):
                    by_commodity[comm] = {
                        "commodity": comm,
                        "modal_price": p.get("modal_price"),
                        "min_price": p.get("min_price"),
                        "max_price": p.get("max_price"),
                        "arrival_date": p.get("arrival_date"),
                        "variety": p.get("variety", ""),
                    }

            result = {
                "mandi": mandi.upper(),
                "commodities_count": len(by_commodity),
                "prices": list(by_commodity.values()),
                "total_records": len(prices),
            }

        elif function == "list_available_commodities":
            state = params.get("state", "")
            commodities = list_available_commodities(state if state else None)
            result = {
                "commodities": commodities,
                "count": len(commodities),
                "state_filter": state or "all states",
            }

        elif function == "list_available_mandis":
            state = params.get("state", "")
            mandis = list_available_mandis(state if state else None)
            result = {
                "mandis": mandis,
                "count": len(mandis),
                "state_filter": state or "all states",
            }

        elif function == "list_available_states":
            states = list_available_states()
            result = {
                "states": states,
                "count": len(states),
            }

        elif function == "get_sell_recommendation":
            commodity = params.get("commodity", "")
            state = params.get("state", "Madhya Pradesh")
            lat = float(params.get("latitude", "22.7196"))
            lon = float(params.get("longitude", "75.8577"))
            quantity = float(params.get("quantity_qtl", "10"))
            storage = params.get("storage_available", "false").lower() == "true"

            result = get_sell_recommendation_data(
                commodity, state, lat, lon, quantity, storage
            )

        else:
            result = {"error": f"Unknown function: {function}"}

        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "function": function,
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": json.dumps(result, ensure_ascii=False)
                        }
                    }
                }
            }
        }

    except Exception as e:
        logger.error(f"Action group error: {e}", exc_info=True)
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "function": function,
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": json.dumps({"error": str(e)})
                        }
                    }
                }
            }
        }


def api_response(status_code: int, body: dict) -> dict:
    """Format response for API Gateway."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
