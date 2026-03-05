"""
MandiMitra — India-Scale Data Fetcher
Strategy: query by STATE+DATE (no commodity filter) to capture ALL commodities.
This gets every mandi record for each state per day — far more efficient.

Target: 14 states × 7 days = 98 query chains → potentially 100k+ records

Usage:
    python fetch_all_india.py [--days N] [--states STATE1,STATE2]

Requirements:
    pip install boto3
    AWS credentials configured
"""
import os
import sys
import json
import time
import logging
import urllib.request
import urllib.parse
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("fetch_all_india.log", encoding="utf-8"),
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
DAYS_BACK = int(os.environ.get("DAYS_BACK", "7"))
PAGE_SIZE = 500
MAX_RECORDS_PER_QUERY = 10000  # 20 pages × 500 = 10k records per state-date

# All major agricultural states
ALL_STATES = [
    "Madhya Pradesh", "Rajasthan", "Maharashtra", "Uttar Pradesh",
    "Gujarat", "Karnataka", "Punjab", "Haryana", "Andhra Pradesh",
    "Telangana", "Tamil Nadu", "Bihar", "West Bengal", "Chhattisgarh",
    "Odisha", "Jharkhand", "Kerala", "Assam", "Himachal Pradesh",
    "Uttarakhand", "Jammu and Kashmir",
]

# Broad commodity set — any not in this set still gets stored, this just provides
# consistent naming for known aliases
COMMODITY_ALIASES = {
    "Arhar (Tur/Red Gram)(Whole)": "Arhar",
    "Arhar Dal (Tur Dal)": "Arhar Dal",
    "Bengal Gram (Gram)(Whole)": "Chana",
    "Bengal Gram Dal (Chana Dal)": "Chana Dal",
    "Black Gram (Urd Beans)(Whole)": "Urad",
    "Black Gram Dal (Urd Dal)": "Urad Dal",
    "Green Gram (Moong)(Whole)": "Moong",
    "Green Gram Dal (Moong Dal)": "Moong Dal",
    "Onion": "Onion",
    "Potato": "Potato",
    "Tomato": "Tomato",
    "Wheat": "Wheat",
    "Paddy (Common)": "Rice",
    "Paddy": "Rice",
    "Rice": "Rice",
    "Rapeseed &amp; Mustard": "Mustard",
    "Rapeseed & Mustard": "Mustard",
    "Rape Seed": "Mustard",
    "Mustard": "Mustard",
    "Soyabean": "Soyabean",
    "Maize": "Maize",
    "Cotton": "Cotton",
    "Bajra (Pearl Millet/Cumbu)": "Bajra",
    "Bajra": "Bajra",
    "Jowar (Sorghum)": "Jowar",
    "Jowar": "Jowar",
    "Groundnut": "Groundnut",
    "Groundnut (With Shell)": "Groundnut",
    "Turmeric": "Turmeric",
    "Dry Chillies": "Red Chilli",
    "Red Chilli": "Red Chilli",
    "Coriander (Leaves)": "Coriander",
    "Coriander": "Coriander",
    "Cumin Seed (Jeera)": "Cumin",
    "Cumin": "Cumin",
    "Garlic": "Garlic",
    "Sunflower Seed": "Sunflower",
    "Lentil (Masur)(Whole)": "Masur",
    "Masur Dal": "Masur Dal",
    "Ginger (Dry)": "Ginger",
    "Ginger": "Ginger",
    "Bitter Gourd": "Bitter Gourd",
    "Brinjal": "Brinjal",
    "Cabbage": "Cabbage",
    "Cauliflower": "Cauliflower",
    "Lady Finger (Bhindi)": "Bhindi",
    "Peas (Dry)": "Peas",
    "Pumpkin": "Pumpkin",
    "Sweet Potato": "Sweet Potato",
    "Water Melon": "Watermelon",
    "Banana": "Banana",
    "Lemon": "Lemon",
    "Mango": "Mango",
    "Orange": "Orange",
    "Pomegranate": "Pomegranate",
    "Grapes": "Grapes",
    "Guava": "Guava",
    "Papaya": "Papaya",
}

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)


def normalize_commodity(raw_name: str) -> str:
    """Normalize commodity name using aliases, else clean and return as-is."""
    if raw_name in COMMODITY_ALIASES:
        return COMMODITY_ALIASES[raw_name]
    # Clean HTML entities
    clean = raw_name.replace("&amp;", "&").strip()
    return COMMODITY_ALIASES.get(clean, clean)


def fetch_state_date(state: str, date_str: str) -> list:
    """
    Fetch ALL records for a given state and date using pagination.
    Queries by state+date only — no commodity filter — to get everything.
    """
    records = []
    offset = 0

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": PAGE_SIZE,
        "offset": 0,
        "filters[state.keyword]": state,
        "filters[arrival_date]": date_str,
    }

    while offset < MAX_RECORDS_PER_QUERY:
        params["offset"] = offset
        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MandiMitra/2.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.warning(f"Rate limited on {state}/{date_str} offset={offset}. Sleeping 60s...")
                time.sleep(60)
                continue
            logger.warning(f"HTTP {e.code} for {state}/{date_str} offset={offset}")
            break
        except Exception as e:
            logger.warning(f"Error {state}/{date_str} offset={offset}: {e}")
            time.sleep(5)
            break

        batch = data.get("records", [])
        if not batch:
            break
        records.extend(batch)

        total = int(data.get("total", 0))
        offset += len(batch)
        if len(batch) < PAGE_SIZE or offset >= total:
            break

        time.sleep(0.2)  # gentle rate limiting

    return records


def safe_decimal(value):
    if value is None:
        return None
    try:
        d = Decimal(str(value).replace(",", "").strip())
        return None if (d.is_nan() or d.is_infinite()) else d
    except Exception:
        return None


def transform(record: dict) -> dict | None:
    """Transform a raw Agmarknet API record into DynamoDB item format."""
    market = (record.get("market") or "").strip().upper()
    raw_date = record.get("arrival_date", "")
    raw_commodity = (record.get("commodity") or "").strip()
    raw_state = (record.get("state") or "").strip()

    if not market or not raw_date or not raw_commodity or not raw_state:
        return None

    commodity = normalize_commodity(raw_commodity)
    state = raw_state

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

    # Sanity check: modal within reasonable range
    if modal < Decimal("1") or modal > Decimal("500000"):
        return None

    # If min/max present, modal should be in range (5% tolerance)
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
        "ingested_at": datetime.utcnow().isoformat(),
    }
    arrivals = safe_decimal(record.get("arrivals_tonnes"))
    if arrivals is not None:
        item["arrivals_tonnes"] = arrivals
    return item


def write_items(items: list) -> int:
    """Deduplicate by PK+SK and write to DynamoDB."""
    deduped: dict = {}
    for item in items:
        key = f"{item['PK']}|{item['SK']}"
        deduped[key] = item

    count = 0
    # Use batch_writer for efficiency
    with table.batch_writer() as batch:
        for item in deduped.values():
            try:
                batch.put_item(Item=item)
                count += 1
            except Exception as e:
                logger.warning(f"Write error: {e}")
    return count


def process_state_date(state: str, date_str: str) -> tuple:
    """Fetch and write all records for one state+date. Returns (state, date, count)."""
    raw_records = fetch_state_date(state, date_str)
    if not raw_records:
        return (state, date_str, 0)

    items = []
    for rec in raw_records:
        t = transform(rec)
        if t:
            items.append(t)

    if not items:
        return (state, date_str, 0)

    written = write_items(items)
    return (state, date_str, written)


def get_current_count() -> int:
    """Get total item count in DynamoDB table."""
    total = 0
    paginator = dynamodb.meta.client.get_paginator("scan")
    for page in paginator.paginate(TableName=TABLE_NAME, Select="COUNT"):
        total += page["Count"]
    return total


def main():
    today = datetime.utcnow()
    dates = []
    for i in range(DAYS_BACK):
        d = today - timedelta(days=i)
        dates.append(d.strftime("%d/%m/%Y"))

    logger.info(f"{'='*70}")
    logger.info(f"MandiMitra India-Scale Data Fetcher")
    logger.info(f"Strategy: STATE+DATE query (captures all commodities)")
    logger.info(f"Dates: {dates}")
    logger.info(f"States: {len(ALL_STATES)} — {', '.join(ALL_STATES)}")
    logger.info(f"Total query chains: {len(dates) * len(ALL_STATES)}")
    logger.info(f"Max records per chain: {MAX_RECORDS_PER_QUERY}")
    logger.info(f"{'='*70}")

    start_count = get_current_count()
    logger.info(f"DynamoDB start count: {start_count:,} items")

    grand_total = 0
    work_items = [(state, date) for date in dates for state in ALL_STATES]

    # Process with limited parallelism (3 workers to avoid rate limits)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_state_date, s, d): (s, d) for s, d in work_items}
        done = 0
        for future in as_completed(futures):
            state, date_str, count = future.result()
            done += 1
            if count > 0:
                logger.info(f"[{done}/{len(work_items)}] {state:25s} | {date_str} | {count:4d} records")
            else:
                logger.debug(f"[{done}/{len(work_items)}] {state:25s} | {date_str} | no data")
            grand_total += count

    end_count = get_current_count()
    logger.info(f"\n{'='*70}")
    logger.info(f"DONE! Written this run: {grand_total:,}")
    logger.info(f"DynamoDB total: {start_count:,} → {end_count:,} (+{end_count - start_count:,})")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    main()
