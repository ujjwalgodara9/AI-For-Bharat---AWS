"""
MandiMitra — 7-Day Historical Data Fetcher
Fetches commodity prices for each of the last 7 days explicitly using
the Agmarknet API's arrival_date filter. Writes directly to DynamoDB.

Usage:
    python fetch_7days.py

Requirements:
    pip install boto3
    AWS credentials configured (aws configure or IAM role)
    DATA_GOV_API_KEY env var set, or hardcode below
"""
import os
import json
import math
import logging
import urllib.request
import urllib.parse
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("DATA_GOV_API_KEY", "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b")
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
TABLE_NAME = "MandiMitraPrices"
AWS_REGION = "us-east-1"
DAYS_BACK = 7

COMMODITIES = [
    "Wheat", "Soyabean", "Onion", "Tomato", "Potato",
    "Mustard", "Chana", "Maize", "Cotton", "Rice",
    "Garlic", "Moong", "Urad", "Bajra", "Jowar",
    "Groundnut", "Turmeric", "Red Chilli", "Coriander", "Cumin",
]

STATES = [
    "Madhya Pradesh", "Rajasthan", "Maharashtra",
    "Uttar Pradesh", "Gujarat", "Karnataka",
    "Punjab", "Haryana", "Andhra Pradesh",
    "Telangana", "Tamil Nadu", "Bihar", "West Bengal", "Chhattisgarh",
]
# ────────────────────────────────────────────────────────────────────────────

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)


def fetch_for_date(commodity: str, state: str, date_str: str) -> list:
    """Fetch records for a specific date (format: DD/MM/YYYY)."""
    records = []
    offset = 0
    limit = 500

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit,
        "offset": 0,
        "filters[state.keyword]": state,
        "filters[commodity]": commodity,
        "filters[arrival_date]": date_str,  # explicit date filter
    }

    while True:
        params["offset"] = offset
        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MandiMitra-Fetch/1.0")
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"API error {commodity}/{state}/{date_str} offset={offset}: {e}")
            break

        batch = data.get("records", [])
        if not batch:
            break
        records.extend(batch)

        total = data.get("total", 0)
        offset += limit
        if offset >= total or offset >= 2000:
            break

    return records


def safe_decimal(value):
    if value is None:
        return None
    try:
        d = Decimal(str(value))
        return None if (d.is_nan() or d.is_infinite()) else d
    except Exception:
        return None


def transform(record: dict, commodity: str, state: str) -> dict:
    market = (record.get("market") or "").strip().upper()
    raw_date = record.get("arrival_date", "")
    if not market or not raw_date:
        return None

    try:
        if "/" in raw_date:
            parsed = datetime.strptime(raw_date, "%d/%m/%Y")
        elif "-" in raw_date:
            parsed = datetime.strptime(raw_date, "%d-%m-%Y")
        else:
            return None
        iso_date = parsed.strftime("%Y-%m-%d")
    except ValueError:
        return None

    # Skip future dates
    if parsed > datetime.utcnow() + timedelta(days=1):
        return None

    modal = safe_decimal(record.get("modal_price"))
    if modal is None:
        return None

    min_p = safe_decimal(record.get("min_price"))
    max_p = safe_decimal(record.get("max_price"))

    # Validate modal is within min/max (5% tolerance)
    if min_p is not None and max_p is not None:
        tol = Decimal("0.05")
        if modal < min_p * (1 - tol) or modal > max_p * (1 + tol):
            return None

    # Realistic price range
    for p in [min_p, max_p, modal]:
        if p is not None and (p < 1 or p > 500000):
            return None

    state_clean = state.upper().replace(" ", "_")
    variety = (record.get("variety") or "UNKNOWN").strip().upper()
    item = {
        "PK": f"{commodity.upper()}#{state_clean}",
        "SK": f"{iso_date}#{market}#{variety}",
        "commodity": commodity,
        "state": state,
        "district": (record.get("district") or "").strip(),
        "mandi_name": market,
        "arrival_date": iso_date,
        "variety": variety,
        "min_price": min_p,
        "max_price": max_p,
        "modal_price": modal,
        "date_commodity": f"{iso_date}#{commodity.upper()}",
        "ingested_at": datetime.utcnow().isoformat(),
    }
    arrivals = safe_decimal(record.get("arrivals_tonnes"))
    if arrivals is not None:
        item["arrivals_tonnes"] = arrivals
    return item


def write_batch(items: list) -> int:
    # Deduplicate by PK+SK — same key can't appear twice in one batch
    deduped: dict = {}
    for item in items:
        key = f"{item['PK']}|{item['SK']}"
        deduped[key] = item
    unique_items = list(deduped.values())

    count = 0
    # Write individually to avoid batch duplicate issues
    for item in unique_items:
        try:
            table.put_item(Item=item)
            count += 1
        except Exception as e:
            logger.warning(f"Write error: {e}")
    return count


def main():
    # Build list of last DAYS_BACK dates in DD/MM/YYYY format
    today = datetime.utcnow()
    dates = []
    for i in range(DAYS_BACK):
        d = today - timedelta(days=i)
        dates.append(d.strftime("%d/%m/%Y"))

    logger.info(f"Fetching data for dates: {dates}")
    logger.info(f"Commodities: {len(COMMODITIES)}, States: {len(STATES)}")
    logger.info(f"Total API calls: {len(dates) * len(COMMODITIES) * len(STATES)} (max)")

    grand_total = 0
    skipped = 0

    for date_str in dates:
        date_total = 0
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing date: {date_str}")
        for state in STATES:
            for commodity in COMMODITIES:
                raw = fetch_for_date(commodity, state, date_str)
                if not raw:
                    continue

                items = []
                for rec in raw:
                    t = transform(rec, commodity, state)
                    if t:
                        items.append(t)
                    else:
                        skipped += 1

                if items:
                    written = write_batch(items)
                    date_total += written
                    logger.info(f"  {commodity:15s} | {state:20s} | {date_str} | {written:3d} records")

        grand_total += date_total
        logger.info(f"Date {date_str} total: {date_total} records written")

    logger.info(f"\n{'='*60}")
    logger.info(f"DONE. Total written: {grand_total} | Skipped (bad data): {skipped}")


if __name__ == "__main__":
    main()
