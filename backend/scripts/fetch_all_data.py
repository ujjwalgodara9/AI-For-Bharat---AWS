"""
MandiMitra — Aggressive data fetcher
Fetches ALL available current daily prices from data.gov.in API.
Demo API key returns max 10 per request, so we paginate by 10.

Usage:
    python backend/scripts/fetch_all_data.py
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://api.data.gov.in/resource"
CURRENT_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
API_KEY = os.environ.get(
    "DATA_GOV_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
PAGE_SIZE = 10  # Demo key returns max 10 per request


def fetch(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MandiMitra/1.0")
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 * (2 ** attempt))
            else:
                return None
        except Exception:
            time.sleep(1)
    return None


def fetch_page(offset=0):
    """Fetch a page of current prices."""
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 500,
        "offset": offset,
    }
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/{CURRENT_RESOURCE}?{query}"
    return fetch(url)


def fetch_page_for_state(state, offset=0):
    """Fetch a page filtered by state."""
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 500,
        "offset": offset,
        "filters[state]": state,
    }
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/{CURRENT_RESOURCE}?{query}"
    return fetch(url)


def transform(records):
    """Transform raw API records to DynamoDB format."""
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
            date_str = str(arrival_date)
            if "/" in date_str:
                parsed = datetime.strptime(date_str, "%d/%m/%Y")
            elif "-" in date_str:
                if len(date_str.split("-")[0]) == 4:
                    parsed = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    parsed = datetime.strptime(date_str, "%d-%m-%Y")
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


def fetch_all_for_state(state):
    """Fetch all records for a given state using pagination."""
    records = []
    offset = 0

    # Get total for this state
    first = fetch_page_for_state(state, 0)
    if not first:
        return state, records

    total = int(first.get("total", 0))
    page_records = first.get("records", [])
    records.extend(page_records)
    got = len(page_records)

    if got == 0:
        return state, records

    offset = got
    while offset < total and offset < 2000:  # Cap at 2000 per state
        data = fetch_page_for_state(state, offset)
        if not data:
            break
        page_records = data.get("records", [])
        if not page_records:
            break
        records.extend(page_records)
        offset += len(page_records)
        time.sleep(0.3)

    return state, records


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_records = []

    # First, get the list of states from an unfiltered call
    print("Fetching initial data to discover states...")
    first = fetch_page(0)
    if not first:
        print("ERROR: Cannot reach API")
        sys.exit(1)

    total = int(first.get("total", 0))
    print(f"Total available in API: {total} records")

    # Discover states from first few pages
    all_states = set()
    initial_records = first.get("records", [])
    all_records.extend(initial_records)
    for r in initial_records:
        s = r.get("state", "")
        if s:
            all_states.add(s)

    # Fetch a few more unfiltered pages to discover more states
    for off in range(10, 200, 10):
        data = fetch_page(off)
        if data:
            recs = data.get("records", [])
            all_records.extend(recs)
            for r in recs:
                s = r.get("state", "")
                if s:
                    all_states.add(s)
            if not recs:
                break
        time.sleep(0.3)

    # Also add known major agricultural states
    known_states = [
        "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
        "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
        "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
        "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
        "Uttarakhand", "West Bengal", "Chandigarh", "Delhi",
        "Jammu and Kashmir", "Puducherry",
    ]
    all_states.update(known_states)

    print(f"Will query {len(all_states)} states...")

    # Fetch all records state by state
    for state in sorted(all_states):
        print(f"  {state}...", end=" ", flush=True)
        _, records = fetch_all_for_state(state)
        new_count = 0
        for r in records:
            if r not in all_records:
                all_records.append(r)
                new_count += 1
        print(f"{len(records)} records ({new_count} new)")
        time.sleep(0.5)

    print(f"\nTotal raw records fetched: {len(all_records)}")

    # Transform
    items = transform(all_records)
    print(f"DynamoDB items (deduplicated): {len(items)}")

    # Save
    path = os.path.join(OUTPUT_DIR, "dynamodb_items_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Saved to {path}")

    # Stats
    states = set(i["state"] for i in items)
    commodities = set(i["commodity"] for i in items)
    mandis = set(i["mandi_name"] for i in items)
    dates = set(i["arrival_date"] for i in items)
    print(f"\nStats:")
    print(f"  States: {len(states)}")
    for s in sorted(states):
        count = sum(1 for i in items if i["state"] == s)
        print(f"    {s}: {count} records")
    print(f"  Commodities: {len(commodities)}")
    print(f"  Mandis: {len(mandis)}")
    print(f"  Date range: {min(dates)} to {max(dates)}")
    print(f"  Total items: {len(items)}")


if __name__ == "__main__":
    main()
