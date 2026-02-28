"""
MandiMitra — Local Data Fetcher
Fetches real mandi price data from data.gov.in and saves to JSON files.

Usage:
    python backend/scripts/fetch_data_local.py

    # With your own API key (recommended):
    DATA_GOV_API_KEY=your_key python backend/scripts/fetch_data_local.py
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime

# data.gov.in API
CURRENT_PRICES_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
HISTORICAL_PRICES_RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE_URL = "https://api.data.gov.in/resource"

API_KEY = os.environ.get(
    "DATA_GOV_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def fetch_with_retry(url, max_retries=3, base_delay=5):
    """Fetch URL with exponential backoff retry on 429."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MandiMitra/1.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                delay = base_delay * (2 ** attempt)
                print(f"    Rate limited, waiting {delay}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
            else:
                print(f"    HTTP Error {e.code}: {e.reason}")
                return None
        except Exception as e:
            print(f"    Error: {e}")
            return None
    print(f"    Max retries exceeded")
    return None


def fetch_current_prices():
    """Fetch today's commodity prices — all available records."""
    print(f"\n{'='*60}")
    print(f"Fetching CURRENT daily prices...")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")
    print(f"{'='*60}")

    all_records = []
    offset = 0
    limit = 500

    while offset < 5000:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": limit,
            "offset": offset,
        }
        query = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/{CURRENT_PRICES_RESOURCE}?{query}"

        data = fetch_with_retry(url)
        if not data:
            break

        records = data.get("records", [])
        total = data.get("total", 0)

        if not records:
            break

        all_records.extend(records)
        offset += limit
        print(f"  Fetched {len(all_records)}/{total}...")

        if offset >= total:
            break
        time.sleep(1)  # Respect rate limits

    print(f"  TOTAL: {len(all_records)} current price records")
    return all_records


def fetch_historical_prices():
    """Fetch historical prices for key commodity-state pairs."""
    print(f"\n{'='*60}")
    print(f"Fetching HISTORICAL prices...")
    print(f"{'='*60}")

    combos = [
        ("Soyabean", "Madhya Pradesh"),
        ("Wheat", "Madhya Pradesh"),
        ("Onion", "Maharashtra"),
        ("Wheat", "Rajasthan"),
        ("Tomato", "Karnataka"),
        ("Potato", "Uttar Pradesh"),
        ("Mustard", "Rajasthan"),
        ("Gram (Chana)", "Madhya Pradesh"),
        ("Cotton", "Gujarat"),
        ("Paddy(Dhan)(Common)", "Punjab"),
        ("Maize", "Bihar"),
        ("Soyabean", "Rajasthan"),
        ("Onion", "Madhya Pradesh"),
        ("Wheat", "Uttar Pradesh"),
        ("Groundnut", "Gujarat"),
    ]

    all_records = []
    for commodity, state in combos:
        print(f"  {commodity} / {state}...", end=" ", flush=True)
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 500,
            "offset": 0,
            "filters[Commodity]": commodity,
            "filters[State]": state,
        }
        query = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/{HISTORICAL_PRICES_RESOURCE}?{query}"

        data = fetch_with_retry(url)
        if data:
            records = data.get("records", [])
            all_records.extend(records)
            print(f"{len(records)} records")
        else:
            print("failed")
        time.sleep(2)  # Be polite to the API

    print(f"  TOTAL: {len(all_records)} historical records")
    return all_records


def transform_to_dynamodb_format(records):
    """Transform API records to DynamoDB item format."""
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

        # Deduplicate
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


def analyze(records, label):
    """Print summary stats."""
    if not records:
        print(f"  No records for {label}")
        return

    states = set()
    commodities = set()
    markets = set()

    for r in records:
        states.add(r.get("state", r.get("State", "")))
        commodities.add(r.get("commodity", r.get("Commodity", "")))
        markets.add(r.get("market", r.get("Market", "")))

    print(f"\n--- {label} ---")
    print(f"  Records:     {len(records)}")
    print(f"  States:      {len(states)}")
    print(f"  Commodities: {len(commodities)}")
    print(f"  Mandis:      {len(markets)}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"MandiMitra Data Fetcher")
    print(f"Output: {OUTPUT_DIR}")

    current = fetch_current_prices()
    analyze(current, "Current")

    historical = fetch_historical_prices()
    analyze(historical, "Historical")

    # Combine and transform
    all_records = current + historical
    items = transform_to_dynamodb_format(all_records)

    # Save files
    for name, data in [
        ("current_prices_raw.json", current),
        ("historical_prices_raw.json", historical),
        ("dynamodb_items.json", items),
    ]:
        path = os.path.join(OUTPUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  Saved {name} ({len(data)} records)")

    # Sample output
    if items:
        print(f"\n--- Sample Items ---")
        for item in items[:5]:
            print(f"  {item['commodity']} @ {item['mandi_name']} ({item['state']})")
            print(f"    Modal: Rs.{item['modal_price']} | Min: Rs.{item['min_price']} | Max: Rs.{item['max_price']} | {item['arrival_date']}")

    print(f"\n{'='*60}")
    print(f"DONE — {len(items)} DynamoDB-ready items from {len(all_records)} raw records")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
