"""
MandiMitra — Data Ingestion Lambda
Fetches daily commodity prices from data.gov.in Agmarknet API and writes to DynamoDB.

Triggered by: EventBridge (daily at 9:30 PM IST / 4:00 PM UTC) or manual invocation.
Note: Agmarknet mandis finalize daily auction data by 5:00 PM IST (per DMI guidelines).
We schedule ingestion at 9:30 PM IST to ensure all data is fully propagated and available.
"""
import os
import json
import time
import logging
import boto3
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))

TABLE_NAME = os.environ.get("PRICE_TABLE", "MandiMitraPrices")
S3_BUCKET = os.environ.get("S3_BUCKET", "mandimitra-data")

# Updated explicitly with the user's personal key
API_KEY = os.environ.get("DATA_GOV_API_KEY", "579b464db66ec23bdd000001b8ffc391c0f94e996a3cfbde0b1c2e32")
CURRENT_PRICES_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{CURRENT_PRICES_RESOURCE}"


def handler(event, context):
    """Main Lambda handler for data ingestion."""
    table = dynamodb.Table(TABLE_NAME)
    total_records = 0
    errors = []

    logger.info("Starting bulk data ingestion using today's market resource...")
    
    offset = 0
    limit = 1000
    
    while True:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": limit,
            "offset": offset,
        }
        query_string = urllib.parse.urlencode(params)
        url = f"{BASE_URL}?{query_string}"
        
        data = _fetch_with_retry(url, offset)
        if not data:
            break
            
        records = data.get("records", [])
        total = data.get("total", 0)
        
        if not records:
            break
            
        # Write batch to DynamoDB
        count = write_to_dynamodb(table, records)
        total_records += count
        
        logger.info(f"Fetched offset {offset}/{total}. Wrote {count} valid records.")
        
        offset += limit
        if offset >= total:
            break
            
        time.sleep(1) # delay between pagination

    # Store raw data audit log in S3
    try:
        audit_key = f"ingestion-logs/{datetime.utcnow().strftime('%Y-%m-%d')}/summary.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=audit_key,
            Body=json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "total_records": total_records,
                "errors": errors
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
            "errors": errors[:10],
        }
    }
    logger.info(f"Ingestion complete: {total_records} records written to DynamoDB")
    return result


def _fetch_with_retry(url: str, offset: int, max_retries: int = 5, base_delay: float = 3.0) -> dict:
    """Fetch URL with exponential backoff retry on 429 Too Many Requests."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MandiMitra/1.0")
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited (429) at offset={offset}, retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"API request failed at offset={offset}: {e}")
                return None
        except Exception as e:
            logger.error(f"API request failed at offset={offset}: {e}")
            return None
    return None


def write_to_dynamodb(table, records: list) -> int:
    """Transform and batch-write records to DynamoDB, deduplicating by PK+SK."""
    count = 0
    seen_keys = set()

    with table.batch_writer() as batch:
        for record in records:
            try:
                item = transform_record(record)
                if item:
                    key = (item["PK"], item["SK"])
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    batch.put_item(Item=item)
                    count += 1
            except Exception as e:
                logger.warning(f"Skipping bad record: {e}")
                continue

    return count


def transform_record(record: dict) -> dict:
    """Transform an Agmarknet API record to DynamoDB item format."""
    state = (record.get("state") or record.get("State") or "").strip()
    commodity = (record.get("commodity") or record.get("Commodity") or "").strip()
    market = (record.get("market") or record.get("Market") or "").strip().upper()
    arrival_date = record.get("arrival_date") or record.get("Arrival_Date") or ""

    if not market or not arrival_date or not state or not commodity:
        return None

    # Parse date
    try:
        if "/" in str(arrival_date):
            parsed_date = datetime.strptime(str(arrival_date), "%d/%m/%Y")
        elif "-" in str(arrival_date):
            parsed_date = datetime.strptime(str(arrival_date), "%d-%m-%Y")
        else:
            return None
        iso_date = parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        return None

    # Parse prices safely
    min_price = safe_decimal(record.get("min_price") or record.get("Min_Price"))
    max_price = safe_decimal(record.get("max_price") or record.get("Max_Price"))
    modal_price = safe_decimal(record.get("modal_price") or record.get("Modal_Price"))

    if modal_price is None:
        return None

    state_clean = state.upper().replace(" ", "_")
    variety = (record.get("variety") or record.get("Variety") or "UNKNOWN").strip().upper()

    item = {
        "PK": f"{commodity.upper()}#{state_clean}",
        "SK": f"{iso_date}#{market}#{variety}",
        "commodity": commodity,
        "state": state,
        "district": (record.get("district") or record.get("District") or "").strip(),
        "mandi_name": market,
        "arrival_date": iso_date,
        "variety": variety,
        "min_price": min_price if min_price else modal_price,
        "max_price": max_price if max_price else modal_price,
        "modal_price": modal_price,
        "date_commodity": f"{iso_date}#{commodity.upper()}",
        "ingested_at": datetime.utcnow().isoformat(),
    }

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
