"""
MandiMitra Knowledge Base Setup Script.

This script handles:
1. Creating S3 bucket and uploading documents
2. Creating IAM role for KB
3. Creating OpenSearch Serverless collection (vector store)
4. Creating Bedrock Knowledge Base
5. Adding S3 data source and starting ingestion
6. Associating KB with Supervisor Agent

Run: python backend/knowledge_base/setup_knowledge_base.py
"""

import boto3
import json
import time
import os
import sys

REGION = "us-east-1"
ACCOUNT_ID = "471112620976"
BUCKET_NAME = "mandimitra-knowledge-base-471112620976"
SUPERVISOR_AGENT_ID = "GDSWGCDJIX"
KB_NAME = "MandiMitraKB"
COLLECTION_NAME = "mandimitra-kb"
INDEX_NAME = "mandimitra-index"

EMBEDDING_MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"

KB_DIR = os.path.dirname(os.path.abspath(__file__))

# File -> S3 prefix mapping
FILES = {
    "msp_rates_comprehensive.md": "msp/",
    "crop_calendar_india.md": "crop-calendar/",
    "storage_and_post_harvest.md": "storage/",
    "mandi_guide_india.md": "market/",
}

s3 = boto3.client("s3", region_name=REGION)
iam = boto3.client("iam", region_name=REGION)
bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)
aoss = boto3.client("opensearchserverless", region_name=REGION)


# ─── Step 1: S3 Bucket + Upload ───

def setup_s3():
    """Create bucket and upload documents."""
    print("\n[Step 1] Setting up S3 bucket and uploading documents...")

    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"  Bucket {BUCKET_NAME} exists.")
    except Exception:
        print(f"  Creating bucket {BUCKET_NAME}...")
        s3.create_bucket(Bucket=BUCKET_NAME)

    for filename, prefix in FILES.items():
        filepath = os.path.join(KB_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP: {filename} not found")
            continue
        key = f"{prefix}{filename}"
        s3.upload_file(filepath, BUCKET_NAME, key, ExtraArgs={"ContentType": "text/markdown"})
        size = os.path.getsize(filepath)
        print(f"  Uploaded {filename} ({size} bytes) -> s3://{BUCKET_NAME}/{key}")

    print("  S3 setup complete.")


# ─── Step 2: IAM Role ───

def setup_iam_role():
    """Create IAM role for Knowledge Base."""
    print("\n[Step 2] Setting up IAM role...")
    role_name = "MandiMitraKBRole"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": ACCOUNT_ID},
                    "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:knowledge-base/*"}
                }
            }
        ]
    }

    try:
        role = iam.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]
        print(f"  Role exists: {role_arn}")
    except iam.exceptions.NoSuchEntityException:
        print(f"  Creating role {role_name}...")
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for MandiMitra Bedrock Knowledge Base",
        )
        role_arn = role["Role"]["Arn"]

    # Inline policy: S3 read + Bedrock invoke + OpenSearch Serverless
    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [
                    f"arn:aws:s3:::{BUCKET_NAME}",
                    f"arn:aws:s3:::{BUCKET_NAME}/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel"],
                "Resource": [EMBEDDING_MODEL_ARN]
            },
            {
                "Effect": "Allow",
                "Action": ["aoss:APIAccessAll"],
                "Resource": [f"arn:aws:aoss:{REGION}:{ACCOUNT_ID}:collection/*"]
            }
        ]
    }

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="MandiMitraKBPolicy",
        PolicyDocument=json.dumps(inline_policy),
    )
    print(f"  Role ready: {role_arn}")

    time.sleep(10)  # IAM propagation
    return role_arn


# ─── Step 3: OpenSearch Serverless ───

def setup_opensearch_collection(role_arn):
    """Create OpenSearch Serverless collection for vector store."""
    print("\n[Step 3] Setting up OpenSearch Serverless collection...")

    collection_arn = None

    # Check if collection exists
    try:
        collections = aoss.batch_get_collection(names=[COLLECTION_NAME])
        if collections.get("collectionDetails"):
            c = collections["collectionDetails"][0]
            collection_arn = c["arn"]
            print(f"  Collection exists: {collection_arn} (status: {c['status']})")
            if c["status"] == "ACTIVE":
                return collection_arn
            # Wait for it to become active
            print("  Waiting for collection to become ACTIVE...")
            for i in range(60):
                time.sleep(10)
                collections = aoss.batch_get_collection(names=[COLLECTION_NAME])
                status = collections["collectionDetails"][0]["status"]
                print(f"    [{i*10}s] {status}")
                if status == "ACTIVE":
                    return collection_arn
    except Exception:
        pass

    if not collection_arn:
        # Create encryption policy
        try:
            aoss.create_security_policy(
                name=f"{COLLECTION_NAME}-enc",
                type="encryption",
                policy=json.dumps({
                    "Rules": [{"ResourceType": "collection", "Resource": [f"collection/{COLLECTION_NAME}"]}],
                    "AWSOwnedKey": True
                })
            )
            print("  Encryption policy created.")
        except Exception as e:
            if "ConflictException" in str(type(e).__name__) or "already exists" in str(e).lower():
                print("  Encryption policy exists.")
            else:
                raise

        # Create network policy (allow public access for Bedrock)
        try:
            aoss.create_security_policy(
                name=f"{COLLECTION_NAME}-net",
                type="network",
                policy=json.dumps([{
                    "Rules": [
                        {"ResourceType": "dashboard", "Resource": [f"collection/{COLLECTION_NAME}"]},
                        {"ResourceType": "collection", "Resource": [f"collection/{COLLECTION_NAME}"]}
                    ],
                    "AllowFromPublic": True
                }])
            )
            print("  Network policy created.")
        except Exception as e:
            if "ConflictException" in str(type(e).__name__) or "already exists" in str(e).lower():
                print("  Network policy exists.")
            else:
                raise

        # Create data access policy (allow the KB role and current user)
        try:
            sts = boto3.client("sts", region_name=REGION)
            caller_arn = sts.get_caller_identity()["Arn"]

            aoss.create_access_policy(
                name=f"{COLLECTION_NAME}-access",
                type="data",
                policy=json.dumps([{
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{COLLECTION_NAME}"],
                            "Permission": ["aoss:CreateCollectionItems", "aoss:DeleteCollectionItems",
                                          "aoss:UpdateCollectionItems", "aoss:DescribeCollectionItems"]
                        },
                        {
                            "ResourceType": "index",
                            "Resource": [f"index/{COLLECTION_NAME}/*"],
                            "Permission": ["aoss:CreateIndex", "aoss:DeleteIndex", "aoss:UpdateIndex",
                                          "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument"]
                        }
                    ],
                    "Principal": [role_arn, caller_arn]
                }])
            )
            print("  Data access policy created.")
        except Exception as e:
            if "ConflictException" in str(type(e).__name__) or "already exists" in str(e).lower():
                print("  Data access policy exists.")
            else:
                raise

        # Create collection
        print("  Creating OpenSearch Serverless collection (this takes 2-5 min)...")
        response = aoss.create_collection(
            name=COLLECTION_NAME,
            type="VECTORSEARCH",
        )
        collection_arn = response["createCollectionDetail"]["arn"]
        print(f"  Collection ARN: {collection_arn}")

        # Wait for ACTIVE
        for i in range(60):
            time.sleep(10)
            collections = aoss.batch_get_collection(names=[COLLECTION_NAME])
            if collections.get("collectionDetails"):
                status = collections["collectionDetails"][0]["status"]
                print(f"    [{i*10}s] {status}")
                if status == "ACTIVE":
                    break
        else:
            print("  WARNING: Collection not yet ACTIVE. Check console.")

    return collection_arn


# ─── Step 4: Create Knowledge Base ───

def create_knowledge_base(role_arn, collection_arn):
    """Create Bedrock Knowledge Base."""
    print("\n[Step 4] Creating Bedrock Knowledge Base...")

    # Check if KB already exists
    kbs = bedrock_agent.list_knowledge_bases(maxResults=100)
    for kb_item in kbs.get("knowledgeBaseSummaries", []):
        if kb_item["name"] == KB_NAME:
            kb_id = kb_item["knowledgeBaseId"]
            print(f"  KB already exists: {kb_id}")
            return kb_id

    kb = bedrock_agent.create_knowledge_base(
        name=KB_NAME,
        description="Agricultural intelligence: MSP rates (2024-2027), crop calendars, storage guides, mandi procedures, government schemes for Indian farmers. Covers Kharif and Rabi seasons, 20+ crops, state-wise data.",
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": EMBEDDING_MODEL_ARN
            }
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": collection_arn,
                "vectorIndexName": INDEX_NAME,
                "fieldMapping": {
                    "vectorField": "embedding",
                    "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                    "metadataField": "AMAZON_BEDROCK_METADATA"
                }
            }
        }
    )
    kb_id = kb["knowledgeBase"]["knowledgeBaseId"]
    print(f"  Knowledge Base created: {kb_id}")

    # Wait for KB to become ACTIVE
    for i in range(30):
        time.sleep(5)
        kb_info = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
        status = kb_info["knowledgeBase"]["status"]
        if status == "ACTIVE":
            print(f"  KB status: ACTIVE")
            break
        print(f"    [{i*5}s] KB status: {status}")

    return kb_id


# ─── Step 5: Data Source + Ingestion ───

def setup_data_source(kb_id):
    """Add S3 data source and start ingestion."""
    print("\n[Step 5] Adding S3 data source and starting ingestion...")

    # Check existing data sources
    ds_list = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id, maxResults=10)
    ds_id = None
    for ds_item in ds_list.get("dataSourceSummaries", []):
        if ds_item["name"] == "MandiMitraDocuments":
            ds_id = ds_item["dataSourceId"]
            print(f"  Data source exists: {ds_id}")
            break

    if not ds_id:
        ds = bedrock_agent.create_data_source(
            knowledgeBaseId=kb_id,
            name="MandiMitraDocuments",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {
                    "bucketArn": f"arn:aws:s3:::{BUCKET_NAME}",
                    "inclusionPrefixes": ["msp/", "crop-calendar/", "storage/", "market/"]
                }
            },
            vectorIngestionConfiguration={
                "chunkingConfiguration": {
                    "chunkingStrategy": "FIXED_SIZE",
                    "fixedSizeChunkingConfiguration": {
                        "maxTokens": 300,
                        "overlapPercentage": 20
                    }
                }
            }
        )
        ds_id = ds["dataSource"]["dataSourceId"]
        print(f"  Data source created: {ds_id}")

    # Start ingestion
    print("  Starting ingestion...")
    job = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
    )
    job_id = job["ingestionJob"]["ingestionJobId"]
    print(f"  Ingestion job: {job_id}")

    for i in range(60):
        time.sleep(5)
        status = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id,
        )
        state = status["ingestionJob"]["status"]
        if state == "COMPLETE":
            stats = status["ingestionJob"].get("statistics", {})
            scanned = stats.get("numberOfDocumentsScanned", 0)
            indexed = stats.get("numberOfNewDocumentsIndexed", 0) + stats.get("numberOfModifiedDocumentsIndexed", 0)
            print(f"  Ingestion COMPLETE! Scanned: {scanned}, Indexed: {indexed}")
            return ds_id
        elif state == "FAILED":
            reasons = status["ingestionJob"].get("failureReasons", ["unknown"])
            print(f"  Ingestion FAILED: {reasons}")
            return ds_id
        if i % 6 == 0:
            print(f"    [{i*5}s] {state}")

    print("  Ingestion timed out. Check console.")
    return ds_id


# ─── Step 6: Associate with Agent ───

def associate_with_agent(kb_id):
    """Associate KB with Supervisor Agent and re-prepare."""
    print(f"\n[Step 6] Associating KB with Supervisor Agent {SUPERVISOR_AGENT_ID}...")

    try:
        bedrock_agent.associate_agent_knowledge_base(
            agentId=SUPERVISOR_AGENT_ID,
            agentVersion="DRAFT",
            knowledgeBaseId=kb_id,
            description="Search for MSP rates, crop calendars, post-harvest storage guides, mandi procedures, government schemes, and e-NAM information for Indian farmers. Use this knowledge base to answer questions about agricultural policies, crop seasons, storage methods, and how mandis work.",
            knowledgeBaseState="ENABLED",
        )
        print("  KB associated with agent.")
    except Exception as e:
        if "ConflictException" in str(type(e).__name__):
            print("  KB already associated.")
        else:
            print(f"  Warning: {e}")

    print("  Re-preparing agent...")
    bedrock_agent.prepare_agent(agentId=SUPERVISOR_AGENT_ID)
    print("  Agent preparation initiated (takes ~1-2 min).")


# ─── Main ───

def main():
    print("=" * 60)
    print("MandiMitra Knowledge Base Setup")
    print("=" * 60)

    # Step 1: S3
    setup_s3()

    # Step 2: IAM Role
    role_arn = setup_iam_role()

    # Step 3: OpenSearch Serverless
    collection_arn = setup_opensearch_collection(role_arn)

    # Step 4: Knowledge Base
    kb_id = create_knowledge_base(role_arn, collection_arn)

    # Step 5: Data Source + Ingestion
    ds_id = setup_data_source(kb_id)

    # Step 6: Associate with Agent
    associate_with_agent(kb_id)

    # Save IDs
    ids = {
        "knowledge_base_id": kb_id,
        "data_source_id": ds_id,
        "collection_arn": collection_arn,
        "role_arn": role_arn,
        "bucket": BUCKET_NAME,
        "supervisor_agent_id": SUPERVISOR_AGENT_ID,
    }
    ids_path = os.path.join(KB_DIR, "kb_ids.json")
    with open(ids_path, "w") as f:
        json.dump(ids, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"SETUP COMPLETE!")
    print(f"Knowledge Base ID: {kb_id}")
    print(f"IDs saved to: {ids_path}")
    print(f"\nTest queries:")
    print(f"  - 'Wheat ka MSP kya hai?'")
    print(f"  - 'Soyabean kab boya jata hai?'")
    print(f"  - 'Onion ko kitne din store kar sakte hain?'")
    print(f"  - 'Mandi mein fee kitni lagti hai?'")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
