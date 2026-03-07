"""
Upload MandiMitra Knowledge Base documents to S3.
Run: python backend/knowledge_base/upload_to_s3.py
"""

import boto3
import os
import sys

BUCKET_NAME = "mandimitra-knowledge-base-471112620976"
REGION = "us-east-1"
KB_DIR = os.path.dirname(os.path.abspath(__file__))

# Map files to S3 prefixes
FILES = {
    "msp_rates_comprehensive.md": "msp/",
    "crop_calendar_india.md": "crop-calendar/",
    "storage_and_post_harvest.md": "storage/",
    "mandi_guide_india.md": "market/",
}


def main():
    s3 = boto3.client("s3", region_name=REGION)

    # Create bucket if it doesn't exist
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket {BUCKET_NAME} exists.")
    except Exception:
        print(f"Creating bucket {BUCKET_NAME}...")
        s3.create_bucket(Bucket=BUCKET_NAME)
        print("Bucket created.")

    # Upload each file
    for filename, prefix in FILES.items():
        filepath = os.path.join(KB_DIR, filename)
        if not os.path.exists(filepath):
            print(f"SKIP: {filename} not found")
            continue

        key = f"{prefix}{filename}"
        print(f"Uploading {filename} -> s3://{BUCKET_NAME}/{key}")
        s3.upload_file(
            filepath,
            BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": "text/markdown"},
        )
        print(f"  Done ({os.path.getsize(filepath)} bytes)")

    print(f"\nAll files uploaded to s3://{BUCKET_NAME}/")
    print("Prefixes: msp/, crop-calendar/, storage/, market/")


if __name__ == "__main__":
    main()
