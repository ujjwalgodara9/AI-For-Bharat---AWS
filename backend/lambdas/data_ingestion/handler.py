"""
MandiMitra — Data Ingestion Lambda
Fetches daily commodity prices from data.gov.in Agmarknet API and writes to DynamoDB.

Triggered by: EventBridge (daily at 9:30 PM IST / 4:00 PM UTC) or manual invocation.
Note: Agmarknet mandis finalize daily auction data by 5:00 PM IST (per DMI guidelines).
We schedule ingestion at 9:30 PM IST to ensure all data is fully propagated and available.
"""
import os
import json
import math
import logging
import boto3
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))

TABLE_NAME = os.environ.get("PRICE_TABLE", "MandiMitraPrices")
S3_BUCKET = os.environ.get("S3_BUCKET", "mandimitra-data")
API_KEY = os.environ.get("DATA_GOV_API_KEY", "")
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

# Commodities and states to fetch
COMMODITIES = [
    "Wheat", "Soyabean", "Onion", "Tomato", "Potato",
    "Mustard", "Chana", "Maize", "Cotton", "Rice",
    "Garlic", "Moong", "Urad", "Bajra", "Jowar",
]

STATES = [
    "Madhya Pradesh", "Rajasthan", "Maharashtra",
    "Uttar Pradesh", "Gujarat", "Karnataka",
    "Punjab", "Haryana", "Andhra Pradesh",
]


def handler(event, context):
    """Main Lambda handler for data ingestion.

    Recommended schedule: 9:30 PM IST (4:00 PM UTC) daily.
    Agmarknet mandis finalize auction data by 5:00 PM IST per DMI guidelines.
    """
    table = dynamodb.Table(TABLE_NAME)
    total_records = 0
    errors = []

    # Determine date range: today's data by default, or from event
    target_date = event.get("date", datetime.utcnow().strftime("%d/%m/%Y"))
    days_back = event.get("days_back", 1)

    logger.info(f"Starting data ingestion for date={target_date}, days_back={days_back}")

    for state in STATES:
        for commodity in COMMODITIES:
            try:
                records = fetch_from_agmarknet(commodity, state, days_back)
                if records:
                    count = write_to_dynamodb(table, records, commodity, state)
                    total_records += count
                    logger.info(f"Wrote {count} records for {commodity} in {state}")
            except Exception as e:
                error_msg = f"Error fetching {commodity}/{state}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

    # Store raw data audit log in S3
    try:
        audit_key = f"ingestion-logs/{datetime.utcnow().strftime('%Y-%m-%d')}/summary.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=audit_key,
            Body=json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "total_records": total_records,
                "errors": errors,
                "states": len(STATES),
                "commodities": len(COMMODITIES),
            }),
            ContentType="application/json",
        )
    except Exception as e:
        logger.warning(f"Could not write audit log to S3: {e}")

    result = {
        "statusCode": 200,
        "body": {
            "message": "Data ingestion complete",
            "total_records": total_records,
            "errors_count": len(errors),
            "errors": errors[:10],  # Limit error list
        }
    }
    logger.info(f"Ingestion complete: {total_records} records, {len(errors)} errors")
    return result


def fetch_from_agmarknet(commodity: str, state: str, days_back: int = 1) -> list:
    """Fetch commodity price data from data.gov.in API."""
    all_records = []
    offset = 0
    limit = 500

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit,
        "offset": offset,
        "filters[state.keyword]": state,
        "filters[commodity]": commodity,
    }

    while True:
        params["offset"] = offset
        query_string = urllib.parse.urlencode(params)
        url = f"{BASE_URL}?{query_string}"

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MandiMitra/1.0")
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"API request failed for {commodity}/{state} offset={offset}: {e}")
            break

        records = data.get("records", [])
        if not records:
            break

        all_records.extend(records)

        # Check if there are more pages
        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break

        # Safety: don't fetch more than 2000 records per commodity/state
        if offset >= 2000:
            break

    return all_records


def write_to_dynamodb(table, records: list, commodity: str, state: str) -> int:
    """Transform and batch-write records to DynamoDB."""
    count = 0

    with table.batch_writer() as batch:
        for record in records:
            try:
                item = transform_record(record, commodity, state)
                if item:
                    batch.put_item(Item=item)
                    count += 1
            except Exception as e:
                logger.warning(f"Skipping bad record: {e}")
                continue

    return count


def transform_record(record: dict, commodity: str, state: str) -> dict:
    """Transform an Agmarknet API record to DynamoDB item format."""
    market = (record.get("market") or "").strip().upper()
    arrival_date = record.get("arrival_date", "")

    if not market or not arrival_date:
        return None

    # Parse date: format from API is "dd/mm/yyyy" or "dd-mm-yyyy"
    try:
        if "/" in arrival_date:
            parsed_date = datetime.strptime(arrival_date, "%d/%m/%Y")
        elif "-" in arrival_date:
            parsed_date = datetime.strptime(arrival_date, "%d-%m-%Y")
        else:
            return None
        iso_date = parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        return None

    # Parse prices safely
    min_price = safe_decimal(record.get("min_price"))
    max_price = safe_decimal(record.get("max_price"))
    modal_price = safe_decimal(record.get("modal_price"))

    if modal_price is None:
        return None  # Skip records without a modal price

    # Data accuracy validation
    # Rule 1: modal_price must be between min and max (with 5% tolerance)
    if min_price is not None and max_price is not None:
        tolerance = Decimal("0.05")
        min_bound = min_price * (1 - tolerance)
        max_bound = max_price * (1 + tolerance)
        if modal_price < min_bound or modal_price > max_bound:
            logger.warning(f"Skipping record: modal_price {modal_price} outside min-max range [{min_price}, {max_price}] for {market}")
            return None

    # Rule 2: prices must be positive and realistic (₹1 to ₹5,00,000 per quintal)
    for price_val in [min_price, max_price, modal_price]:
        if price_val is not None and (price_val < 1 or price_val > 500000):
            logger.warning(f"Skipping record: unrealistic price {price_val} for {market}")
            return None

    # Rule 3: date must not be in the future
    if parsed_date > datetime.utcnow() + timedelta(days=1):
        logger.warning(f"Skipping record: future date {iso_date} for {market}")
        return None

    state_clean = state.upper().replace(" ", "_")

    item = {
        "PK": f"{commodity.upper()}#{state_clean}",
        "SK": f"{iso_date}#{market}",
        "commodity": commodity,
        "state": state,
        "district": (record.get("district") or "").strip(),
        "mandi_name": market,
        "arrival_date": iso_date,
        "variety": (record.get("variety") or "").strip(),
        "min_price": min_price,
        "max_price": max_price,
        "modal_price": modal_price,
        "date_commodity": f"{iso_date}#{commodity.upper()}",  # For GSI-1
        "ingested_at": datetime.utcnow().isoformat(),
    }

    # Add arrivals if available
    arrivals = safe_decimal(record.get("arrivals_tonnes"))
    if arrivals is not None:
        item["arrivals_tonnes"] = arrivals

    return item


def safe_decimal(value) -> Decimal:
    """Safely convert a value to Decimal for DynamoDB."""
    if value is None:
        return None
    try:
        d = Decimal(str(value))
        if d.is_nan() or d.is_infinite():
            return None
        return d
    except Exception:
        return None
