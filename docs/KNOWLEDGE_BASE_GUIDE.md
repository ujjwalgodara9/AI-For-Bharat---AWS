# MandiMitra — Bedrock Knowledge Base Setup Guide

## What Is a Bedrock Knowledge Base?

A **Bedrock Knowledge Base** enables **Retrieval-Augmented Generation (RAG)** — the agent retrieves relevant documents from a vector database before answering, rather than relying only on its training data or tool calls.

**Without Knowledge Base (current):**
```
User: "What is the MSP for Wheat 2025-26?"
→ Agent calls get_msp() tool → DynamoDB lookup → hardcoded in constants.py
```

**With Knowledge Base:**
```
User: "What MSP circular applies to Wheat post-kharif 2025?"
→ Agent searches Knowledge Base → finds "Cabinet approves MSP for KMS 2025-26" PDF
→ Extracts: "Wheat MSP raised to ₹2,275/quintal, increase of ₹150 from last year"
→ Cites the official source
```

---

## What Should Be in the Knowledge Base for MandiMitra?

### Priority 1: Government MSP & Policy Documents

| Document | Source | Why |
|----------|--------|-----|
| MSP circulars (2022–2026) | CACP, MoAFW | Historical MSP trends, crops covered, seasonal breakdown |
| Agmarknet DMI guidelines | agmarknet.gov.in | How prices are reported, mandi timing, data quality standards |
| PM-KISAN scheme docs | pmkisan.gov.in | Farmer eligibility, payment schedule, registration |
| e-NAM integration guide | enam.gov.in | How APMC mandis connect to national market |
| APMC Act state variations | Various state portals | Different states have different mandi regulations |

### Priority 2: Crop & Market Knowledge

| Document | Source | Why |
|----------|--------|-----|
| Kharif/Rabi crop calendar | ICAR | When each crop is sown/harvested — informs sell timing |
| Commodity variety guides | ICAR/SAUs | Wheat (Lokwan, Mill Quality), Soyabean (Yellow), Rice varieties |
| Storage & grading standards | FCI, Warehousing Corp. | How to grade crops, storage requirements for MSP procurement |
| Market intelligence reports | NAFED, NCDEX | Weekly/monthly commodity outlook |
| Mandi fee structure | State APMC boards | What % is charged as mandi tax per state |

### Priority 3: Agricultural Best Practices

| Document | Source | Why |
|----------|--------|-----|
| Post-harvest loss reduction | ICAR-NRC | Storage tips, moisture content, packaging |
| Transport & packaging guide | SFAC | Reducing spoilage during transit |
| Cooperative society guide | MoC | How farmer cooperatives can negotiate better prices |

---

## Step-by-Step: Creating a Bedrock Knowledge Base

### Prerequisites
1. AWS account with Bedrock access (us-east-1)
2. S3 bucket to store source documents
3. Amazon OpenSearch Serverless (for vector store) — OR S3 Vectors (simpler, cheaper)

### Step 1: Prepare Documents (S3)

```bash
# Create dedicated S3 bucket for Knowledge Base documents
aws s3 mb s3://mandimitra-knowledge-base-471112620976 --region us-east-1

# Create directory structure
# s3://mandimitra-knowledge-base-471112620976/
#   msp/           — MSP circulars
#   crop-calendar/ — Sowing/harvesting schedules
#   market/        — Market analysis reports
#   schemes/       — Government scheme documents
#   storage/       — Post-harvest storage guides
```

**Upload documents:**
```bash
# MSP rates table (create a markdown/PDF)
aws s3 cp msp_2025_26.pdf s3://mandimitra-knowledge-base-471112620976/msp/

# Or create a structured text file:
cat > msp_rates_2025_26.txt << 'EOF'
Government Minimum Support Prices (MSP) 2025-26
Approved by Cabinet Committee on Economic Affairs (CCEA)

Kharif Crops 2025-26:
- Paddy (Common): Rs. 2,300/quintal (+Rs. 117 from 2024-25)
- Paddy (Grade A): Rs. 2,320/quintal
- Jowar (Hybrid): Rs. 3,371/quintal
- Jowar (Maldandi): Rs. 3,421/quintal
- Bajra: Rs. 2,625/quintal (+Rs. 125)
- Ragi: Rs. 4,290/quintal
- Maize: Rs. 2,225/quintal
- Arhar/Tur: Rs. 7,550/quintal
- Moong: Rs. 8,682/quintal
- Urad: Rs. 7,400/quintal
- Groundnut: Rs. 6,783/quintal
- Sunflower: Rs. 7,280/quintal
- Soyabean (Yellow): Rs. 4,892/quintal (+Rs. 292)
- Sesamum: Rs. 9,267/quintal
- Nigerseed: Rs. 8,717/quintal
- Cotton (Medium staple): Rs. 7,121/quintal
- Cotton (Long staple): Rs. 7,521/quintal

Rabi Crops 2025-26:
- Wheat: Rs. 2,275/quintal (+Rs. 150)
- Barley: Rs. 1,735/quintal
- Gram/Chana: Rs. 5,440/quintal
- Lentil (Masur): Rs. 6,700/quintal
- Rapeseed/Mustard: Rs. 5,650/quintal
- Safflower: Rs. 5,800/quintal

Source: CACP Recommendation, CCEA Approval 2025
Valid for: Kharif Marketing Season 2025-26, Rabi Marketing Season 2025-26
EOF
aws s3 cp msp_rates_2025_26.txt s3://mandimitra-knowledge-base-471112620976/msp/
```

### Step 2: Create OpenSearch Serverless Collection (Vector Store)

```bash
# Create encryption policy
aws opensearchserverless create-security-policy \
  --name mandimitra-kb-encryption \
  --type encryption \
  --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/mandimitra-kb"]}],"AWSOwnedKey":true}' \
  --region us-east-1

# Create network policy
aws opensearchserverless create-security-policy \
  --name mandimitra-kb-network \
  --type network \
  --policy '[{"Rules":[{"ResourceType":"dashboard","Resource":["collection/mandimitra-kb"]},{"ResourceType":"collection","Resource":["collection/mandimitra-kb"]}],"AllowFromPublic":true}]' \
  --region us-east-1

# Create collection
aws opensearchserverless create-collection \
  --name mandimitra-kb \
  --type VECTORSEARCH \
  --region us-east-1
# Save the collectionId from response!
```

**Simpler alternative: Use Bedrock's managed vector store (recommended for hackathon):**
> When creating Knowledge Base in console, select "Amazon OpenSearch Serverless" and let AWS create it automatically.

### Step 3: Create Knowledge Base via Console (Recommended)

1. Go to **Amazon Bedrock → Knowledge Bases → Create Knowledge Base**
2. Name: `MandiMitraKB`
3. IAM Role: create new (auto-generated)
4. Data source: Amazon S3 → `s3://mandimitra-knowledge-base-471112620976/`
5. Embeddings model: **Amazon Titan Text Embeddings v2** (free, no extra cost)
6. Vector store: **Amazon OpenSearch Serverless** → Let AWS create new collection
7. Click Create → wait ~5 minutes for initial sync

### Step 4: Create Knowledge Base via CLI

```python
import boto3

bedrock_agent = boto3.client("bedrock-agent", region_name="us-east-1")

# Step 4a: Create the Knowledge Base
kb = bedrock_agent.create_knowledge_base(
    name="MandiMitraKB",
    description="Agricultural price intelligence, MSP circulars, crop calendars, market data",
    roleArn="arn:aws:iam::471112620976:role/MandiMitraBedrockAgentRole",
    knowledgeBaseConfiguration={
        "type": "VECTOR",
        "vectorKnowledgeBaseConfiguration": {
            "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
        }
    },
    storageConfiguration={
        "type": "OPENSEARCH_SERVERLESS",
        "opensearchServerlessConfiguration": {
            "collectionArn": "arn:aws:aoss:us-east-1:471112620976:collection/<your-collection-id>",
            "vectorIndexName": "mandimitra-index",
            "fieldMapping": {
                "vectorField": "embedding",
                "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                "metadataField": "AMAZON_BEDROCK_METADATA"
            }
        }
    }
)
kb_id = kb["knowledgeBase"]["knowledgeBaseId"]
print(f"Knowledge Base ID: {kb_id}")

# Step 4b: Add S3 data source
ds = bedrock_agent.create_data_source(
    knowledgeBaseId=kb_id,
    name="MandiMitraDocuments",
    dataSourceConfiguration={
        "type": "S3",
        "s3Configuration": {
            "bucketArn": "arn:aws:s3:::mandimitra-knowledge-base-471112620976",
            "inclusionPrefixes": ["msp/", "crop-calendar/", "market/", "schemes/", "storage/"]
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

# Step 4c: Start ingestion (sync documents into vector store)
job = bedrock_agent.start_ingestion_job(
    knowledgeBaseId=kb_id,
    dataSourceId=ds_id,
)
print(f"Ingestion job: {job['ingestionJob']['ingestionJobId']}")
```

### Step 5: Associate Knowledge Base with Supervisor Agent

```python
# Associate KB with MandiMitra Supervisor
bedrock_agent.associate_agent_knowledge_base(
    agentId="GDSWGCDJIX",
    agentVersion="DRAFT",
    knowledgeBaseId=kb_id,
    description="Search for MSP rates, crop calendars, market guides, government scheme documents",
    knowledgeBaseState="ENABLED",
)
# Then re-prepare the agent
bedrock_agent.prepare_agent(agentId="GDSWGCDJIX")
```

---

## What Changes in the Agent After Knowledge Base

**Before (tool-only):**
```
User: "What is the MSP for Soyabean and has it changed from last year?"
Agent: calls get_msp("Soyabean") → returns ₹4,892 → no historical context
```

**After (tool + Knowledge Base):**
```
User: "What is the MSP for Soyabean and has it changed from last year?"
Agent:
  1. Searches KB → finds "MSP 2025-26: Soyabean ₹4,892 (+₹292 from 2024-25)"
  2. Calls get_msp() for confirmation
  → "Soyabean MSP is ₹4,892/quintal for 2025-26, an increase of ₹292 from last year's ₹4,600."
```

**New queries enabled:**
- "Which crops got the highest MSP increase this year?"
- "When is the best month to sell Mustard in Rajasthan based on harvest season?"
- "What are the storage requirements for Wheat for FCI procurement?"
- "What is the mandi fee percentage in Maharashtra?"
- "How do I register my produce with e-NAM?"

---

## Cost Estimate (AWS Free Tier)

| Component | Pricing | Monthly Estimate |
|-----------|---------|-----------------|
| OpenSearch Serverless | $0.24/OCU/hr | ~$5–15/month (minimum 0.5 OCU) |
| Titan Text Embeddings v2 | $0.00002/1K tokens | ~$0.01 for initial ingestion |
| Knowledge Base queries | Included in agent calls | $0 extra |
| S3 storage | $0.023/GB | <$0.01 for documents |

> **For hackathon demo:** OpenSearch Serverless has no free tier. Estimated $5–15/month.
> **Alternative:** Use Bedrock's "Quick Create" which uses a managed vector store (saves setup time).

---

## Quick-Start: What to Do Right Now

### Option A: Minimal (1 hour, for demo)

1. Create `msp_rates_2025_26.txt` with all MSP data (above template)
2. Create `crop_calendar.txt` with sowing/harvest months for 20 crops
3. Upload both to S3
4. Create Knowledge Base in console (Quick Create)
5. Associate with Supervisor agent
6. Test: "Wheat ka MSP kya hai aur kab badhega?"

### Option B: Full (2–3 hours, for production)

1. Download PDFs from CACP website (MSP circulars 2022–2026)
2. Download e-NAM farmer guide PDF
3. Create structured markdown for crop calendars, storage guides
4. Create Knowledge Base with proper chunking (300 tokens, 20% overlap)
5. Set up scheduled re-sync (Lambda trigger on S3 upload)
6. Add Knowledge Base to both Supervisor AND NegotiationAgent

### Option C: Knowledge Base + Web Search (v2 roadmap)

- Add `ActionGroups.AMAZON_BEDROCK_WEB_CRAWLER` data source
- KB auto-crawls agmarknet.gov.in weekly for updates
- No manual document upload needed

---

## Documents to Create Right Now (Templates)

These are the minimum needed for a meaningful demo:

### 1. msp_2025_26.md (create locally → upload to S3)
Use the MSP data already in `backend/lambdas/shared/constants.py` (`MSP_RATES` dict) but add:
- Year-over-year change
- Crop category (Kharif/Rabi)
- Procurement agency (FCI, NAFED, State procurement)

### 2. crop_calendar_india.md
Use `CROP_SEASONS` dict in `constants.py` to create a farmer-friendly guide:
- Sowing months per state
- Harvest months per state
- "Best sell window" (1–2 months after harvest, before next crop arrives)

### 3. mandi_guide.md
- How APMC mandis work
- What fees are charged (typically 1.5–3% of trade value)
- How to interpret arrival_date vs actual price
- How Agmarknet reports prices

### 4. storage_tips.md
- Wheat: can store 6–12 months in sealed bags, moisture <14%
- Soyabean: 3–6 months in cool dry storage, moisture <10%
- Onion: 3–4 months in well-ventilated storage
- Tomato: 5–7 days ambient, 2–3 weeks cold storage
- (Use PERISHABILITY_INDEX from constants.py as source)

---

## Files to Create in This Repository

```
backend/knowledge_base/
├── msp_rates_2025_26.md        # MSP with year-over-year changes
├── crop_calendar_india.md      # Sowing/harvest calendar per crop
├── mandi_guide.md              # How APMC mandis work
├── storage_tips.md             # Post-harvest storage by crop
├── scheme_summary.md           # PM-KISAN, e-NAM, PMFBY overview
└── upload_to_s3.py             # Script to upload all to S3
```

---

*This guide was generated based on the current MandiMitra architecture (March 1, 2026).*
*See also: [AWS_AUDIT.md](../AWS_AUDIT.md) for full resource inventory.*
