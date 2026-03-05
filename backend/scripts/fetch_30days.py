"""
MandiMitra — 30-Day Historical Data Fetcher
Fetches last 30 days commodity prices using COMMODITY+STATE+DATE approach
(more reliable than state-only queries; avoids rate limit issues).

Additions over fetch_7days.py:
  - 30 days back (vs 7)
  - 28 commodities (vs 20)
  - 21 states (vs 14)
  - Better dedup and error handling
  - Rate limit backoff

Usage:
    python fetch_30days.py [--days 30]

Note: This takes 20-40 minutes to run (28 × 21 × 30 = 17,640 API calls max).
      Use DAYS_BACK=7 for a quick refresh.
"""
import os
import sys
import json
import time
import logging
import urllib.request
import urllib.parse
import boto3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("fetch_30days.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
API_KEY = os.environ.get(
    "DATA_GOV_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
)
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
TABLE_NAME = "MandiMitraPrices"
AWS_REGION = "us-east-1"
DAYS_BACK = int(os.environ.get("DAYS_BACK", "30"))
PAGE_SIZE = 500
MAX_PAGES = 4  # 4 × 500 = 2000 records per commodity-state-date (safe limit)

# Extended commodity list — 28 crops covering all major Indian markets
COMMODITIES = [
    # Cereals
    "Wheat", "Rice", "Maize", "Bajra", "Jowar",
    # Oilseeds
    "Soyabean", "Mustard", "Groundnut", "Sunflower",
    # Pulses
    "Chana", "Moong", "Urad", "Arhar", "Masur",
    # Cash crops
    "Cotton", "Sugarcane",
    # Vegetables
    "Onion", "Tomato", "Potato", "Garlic", "Ginger",
    # Spices
    "Turmeric", "Red Chilli", "Coriander", "Cumin",
    # Others
    "Banana", "Mango", "Pomegranate",
]

# All major agricultural states — 21 states
STATES = [
    "Madhya Pradesh", "Rajasthan", "Maharashtra", "Uttar Pradesh",
    "Gujarat", "Karnataka", "Punjab", "Haryana", "Andhra Pradesh",
    "Telangana", "Tamil Nadu", "Bihar", "West Bengal", "Chhattisgarh",
    "Odisha", "Jharkhand", "Kerala", "Assam",
    "Himachal Pradesh", "Uttarakhand", "Delhi",
]

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)
_rate_limited_count = [0]


def fetch_for_date(commodity: str, state: str, date_str: str) -> list:
    """Fetch records for specific commodity+state+date combination."""
    records = []
    offset = 0

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": PAGE_SIZE,
        "offset": 0,
        "filters[state.keyword]": state,
        "filters[commodity]": commodity,
        "filters[arrival_date]": date_str,
    }

    for page in range(MAX_PAGES):
        params["offset"] = offset
        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MandiMitra/2.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                _rate_limited_count[0] += 1
                wait = min(30 * _rate_limited_count[0], 120)
                logger.warning(f"Rate limited (#{_rate_limited_count[0]}). Sleeping {wait}s...")
                time.sleep(wait)
                # Retry same page once
                try:
                    with urllib.request.urlopen(req, timeout=25) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                except Exception as e2:
                    logger.warning(f"Retry failed: {e2}")
                    break
            else:
                logger.debug(f"HTTP {e.code}: {commodity}/{state}/{date_str}")
                break
        except Exception as e:
            logger.debug(f"Error {commodity}/{state}/{date_str}: {e}")
            break

        batch = data.get("records", [])
        if not batch:
            break
        records.extend(batch)

        total = int(data.get("total", 0))
        offset += len(batch)
        if len(batch) < PAGE_SIZE or offset >= total:
            break

        time.sleep(0.15)  # gentle pacing

    # Reset rate limit counter on successful run
    if _rate_limited_count[0] > 0:
        _rate_limited_count[0] = max(0, _rate_limited_count[0] - 1)

    return records


def safe_decimal(value):
    if value is None:
        return None
    try:
        d = Decimal(str(value).replace(",", "").strip())
        return None if (d.is_nan() or d.is_infinite()) else d
    except Exception:
        return None


def transform(record: dict, commodity: str, state: str) -> dict | None:
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

    if parsed > datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1):
        return None

    modal = safe_decimal(record.get("modal_price"))
    if modal is None or modal < Decimal("1") or modal > Decimal("500000"):
        return None

    min_p = safe_decimal(record.get("min_price"))
    max_p = safe_decimal(record.get("max_price"))

    if min_p is not None and max_p is not None and min_p < max_p:
        tol = Decimal("0.05")
        if modal < min_p * (1 - tol) or modal > max_p * (1 + tol):
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
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    arrivals = safe_decimal(record.get("arrivals_tonnes"))
    if arrivals is not None:
        item["arrivals_tonnes"] = arrivals
    return item


# In-memory dedup set for this run
_seen_keys: set = set()


def write_batch(items: list) -> int:
    """Deduplicate by PK+SK (globally within this run) and write."""
    new_items = []
    for item in items:
        key = f"{item['PK']}|{item['SK']}"
        if key not in _seen_keys:
            _seen_keys.add(key)
            new_items.append(item)

    count = 0
    with table.batch_writer() as batch:
        for item in new_items:
            try:
                batch.put_item(Item=item)
                count += 1
            except Exception as e:
                logger.warning(f"Write error: {e}")
    return count


def get_current_count() -> int:
    total = 0
    paginator = dynamodb.meta.client.get_paginator("scan")
    for page in paginator.paginate(TableName=TABLE_NAME, Select="COUNT"):
        total += page["Count"]
    return total


def main():
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    dates = [(today - timedelta(days=i)).strftime("%d/%m/%Y") for i in range(DAYS_BACK)]

    total_combos = len(COMMODITIES) * len(STATES) * len(dates)
    logger.info(f"{'='*70}")
    logger.info(f"MandiMitra 30-Day Historical Fetcher")
    logger.info(f"Commodities: {len(COMMODITIES)} | States: {len(STATES)} | Days: {DAYS_BACK}")
    logger.info(f"Max API calls: {total_combos:,}")
    logger.info(f"{'='*70}")

    start_count = get_current_count()
    logger.info(f"DynamoDB start count: {start_count:,} items")

    grand_total = 0
    done = 0

    for date_str in dates:
        date_total = 0
        for state in STATES:
            for commodity in COMMODITIES:
                done += 1
                raw = fetch_for_date(commodity, state, date_str)
                if not raw:
                    continue

                items = [t for rec in raw if (t := transform(rec, commodity, state))]
                if items:
                    written = write_batch(items)
                    date_total += written
                    grand_total += written
                    logger.info(f"[{done}/{total_combos}] {commodity:12s} | {state:20s} | {date_str} | {written:3d}")

                # Progress report every 100 combos
                if done % 100 == 0:
                    logger.info(f">>> Progress: {done}/{total_combos} done, {grand_total:,} total written so far")

        if date_total > 0:
            logger.info(f"=== Date {date_str} total: {date_total} records ===")

    end_count = get_current_count()
    logger.info(f"\n{'='*70}")
    logger.info(f"DONE! Written this run: {grand_total:,}")
    logger.info(f"DynamoDB total: {start_count:,} → {end_count:,} (+{end_count - start_count:,})")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    main()
