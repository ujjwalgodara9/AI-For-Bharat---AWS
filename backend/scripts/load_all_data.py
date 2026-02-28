"""
MandiMitra — Load ALL fetched data into DynamoDB
Reads data/dynamodb_items_all.json and batch-writes to MandiMitraPrices table.

Usage:
    python backend/scripts/load_all_data.py
"""
import json
import os
import sys
import time

try:
    import boto3
except ImportError:
    print("Installing boto3...")
    os.system(f"{sys.executable} -m pip install boto3 -q")
    import boto3

TABLE_NAME = "MandiMitraPrices"
REGION = "us-east-1"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "dynamodb_items_all.json")


def convert_to_dynamodb_item(item):
    """Convert a plain dict to DynamoDB item format."""
    ddb_item = {}
    for key, value in item.items():
        if isinstance(value, str):
            ddb_item[key] = {"S": value}
        elif isinstance(value, (int, float)):
            ddb_item[key] = {"N": str(value)}
        elif value is None:
            ddb_item[key] = {"NULL": True}
        else:
            ddb_item[key] = {"S": str(value)}
    return ddb_item


def main():
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found. Run fetch_all_data.py first.")
        sys.exit(1)

    print(f"Loading data from {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Found {len(items)} items to load")

    dynamodb = boto3.client("dynamodb", region_name=REGION)

    # Batch write (max 25 items per batch)
    batch_size = 25
    loaded = 0
    failed = 0

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        request_items = []

        for item in batch:
            ddb_item = convert_to_dynamodb_item(item)
            request_items.append({"PutRequest": {"Item": ddb_item}})

        try:
            response = dynamodb.batch_write_item(
                RequestItems={TABLE_NAME: request_items}
            )

            # Handle unprocessed items with retry
            unprocessed = response.get("UnprocessedItems", {}).get(TABLE_NAME, [])
            retries = 0
            while unprocessed and retries < 3:
                retries += 1
                time.sleep(1)
                response = dynamodb.batch_write_item(
                    RequestItems={TABLE_NAME: unprocessed}
                )
                unprocessed = response.get("UnprocessedItems", {}).get(TABLE_NAME, [])

            loaded += len(batch) - len(unprocessed)
            failed += len(unprocessed)

            if loaded % 500 == 0 or i + batch_size >= len(items):
                print(f"  Loaded {loaded}/{len(items)}...")

        except Exception as e:
            print(f"  Error at batch {i}: {e}")
            failed += len(batch)
            time.sleep(2)

    print(f"\nDone: {loaded} loaded, {failed} failed out of {len(items)} total")

    # Quick verification
    print("\nVerifying...")
    scan = dynamodb.scan(TableName=TABLE_NAME, Select="COUNT")
    print(f"  Total items in DynamoDB: {scan['Count']}")


if __name__ == "__main__":
    main()
