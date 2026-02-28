"""
MandiMitra — Fetch more data with targeted commodity/state queries.
Uses the demo API key with careful rate limiting to get recent data.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime

BASE_URL = "https://api.data.gov.in/resource"
CURRENT_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
HISTORICAL_RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
API_KEY = os.environ.get(
    "DATA_GOV_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def fetch(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MandiMitra/1.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                delay = 8 * (2 ** attempt)
                print(f"    Rate limited, waiting {delay}s...")
                time.sleep(delay)
            else:
                print(f"    HTTP {e.code}")
                return None
        except Exception as e:
            print(f"    Error: {e}")
            return None
    return None


def fetch_current_filtered(commodity=None, state=None):
    """Fetch current prices with specific filters."""
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 500,
        "offset": 0,
    }
    if commodity:
        params["filters[commodity]"] = commodity
    if state:
        params["filters[state]"] = state

    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/{CURRENT_RESOURCE}?{query}"
    return fetch(url)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Key commodity-state combos for demo
    targets = [
        ("Wheat", "Madhya Pradesh"),
        ("Wheat", "Rajasthan"),
        ("Wheat", "Uttar Pradesh"),
        ("Wheat", "Punjab"),
        ("Wheat", "Haryana"),
        ("Soyabean", "Madhya Pradesh"),
        ("Soyabean", "Rajasthan"),
        ("Soyabean", "Maharashtra"),
        ("Onion", "Maharashtra"),
        ("Onion", "Madhya Pradesh"),
        ("Onion", "Rajasthan"),
        ("Tomato", "Karnataka"),
        ("Tomato", "Madhya Pradesh"),
        ("Potato", "Uttar Pradesh"),
        ("Potato", "West Bengal"),
        ("Mustard", "Rajasthan"),
        ("Mustard", "Madhya Pradesh"),
        ("Cotton", "Gujarat"),
        ("Cotton", "Maharashtra"),
        ("Maize", "Bihar"),
        ("Maize", "Madhya Pradesh"),
        ("Rice", "Punjab"),
        ("Rice", "Uttar Pradesh"),
        ("Gram", "Madhya Pradesh"),
        ("Gram", "Rajasthan"),
        ("Garlic", "Madhya Pradesh"),
        ("Garlic", "Rajasthan"),
        ("Groundnut", "Gujarat"),
        ("Groundnut", "Rajasthan"),
        ("Bajra", "Rajasthan"),
    ]

    all_records = []

    # Also fetch unfiltered current prices (whatever's available today)
    print("Fetching unfiltered current prices...")
    data = fetch_current_filtered()
    if data:
        records = data.get("records", [])
        all_records.extend(records)
        total = data.get("total", 0)
        print(f"  Got {len(records)} records (total available: {total})")
    time.sleep(3)

    # Fetch targeted combos from historical data
    print(f"\nFetching {len(targets)} targeted historical combos...")
    for commodity, state in targets:
        print(f"  {commodity} / {state}...", end=" ", flush=True)
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 100,
            "offset": 0,
            "filters[Commodity]": commodity,
            "filters[State]": state,
        }
        query = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/{HISTORICAL_RESOURCE}?{query}"

        data = fetch(url)
        if data:
            records = data.get("records", [])
            all_records.extend(records)
            print(f"{len(records)} records")
        else:
            print("failed")
        time.sleep(3)  # Generous delay for demo key

    print(f"\nTotal raw records: {len(all_records)}")

    # Transform to DynamoDB format
    items = transform(all_records)
    print(f"DynamoDB items: {len(items)}")

    # Save
    path = os.path.join(OUTPUT_DIR, "dynamodb_items.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Saved to {path}")

    # Stats
    states = set(i["state"] for i in items)
    commodities = set(i["commodity"] for i in items)
    mandis = set(i["mandi_name"] for i in items)
    print(f"\nStats: {len(states)} states, {len(commodities)} commodities, {len(mandis)} mandis")

    # Sample
    print("\nSample items:")
    for item in items[:5]:
        print(f"  {item['commodity']} @ {item['mandi_name']} ({item['state']}) = Rs.{item['modal_price']} on {item['arrival_date']}")


def transform(records):
    items = []
    seen = set()

    for r in records:
        state = (r.get("state", r.get("State", "")) or "").strip()
        market = (r.get("market", r.get("Market", "")) or "").strip().upper()
        commodity = (r.get("commodity", r.get("Commodity", "")) or "").strip()
        district = (r.get("district", r.get("District", "")) or "").strip()
        variety = (r.get("variety", r.get("Variety", "")) or "").strip()
        arrival_date = r.get("arrival_date", r.get("Arrival_Date", ""))
        min_price = r.get("min_price", r.get("Min_Price"))
        max_price = r.get("max_price", r.get("Max_Price"))
        modal_price = r.get("modal_price", r.get("Modal_Price"))

        if not market or not commodity or not modal_price:
            continue

        try:
            if "/" in str(arrival_date):
                parsed = datetime.strptime(str(arrival_date), "%d/%m/%Y")
            elif "-" in str(arrival_date):
                parsed = datetime.strptime(str(arrival_date), "%d-%m-%Y")
            else:
                continue
            iso_date = parsed.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        try:
            modal_p = float(str(modal_price))
            min_p = float(str(min_price)) if min_price else modal_p
            max_p = float(str(max_price)) if max_price else modal_p
        except (ValueError, TypeError):
            continue

        state_clean = state.upper().replace(" ", "_")
        pk = f"{commodity.upper()}#{state_clean}"
        sk = f"{iso_date}#{market}"

        key = f"{pk}|{sk}"
        if key in seen:
            continue
        seen.add(key)

        items.append({
            "PK": pk,
            "SK": sk,
            "commodity": commodity,
            "state": state,
            "district": district,
            "mandi_name": market,
            "arrival_date": iso_date,
            "variety": variety,
            "min_price": min_p,
            "max_price": max_p,
            "modal_price": modal_p,
            "date_commodity": f"{iso_date}#{commodity.upper()}",
        })

    return items


if __name__ == "__main__":
    main()
