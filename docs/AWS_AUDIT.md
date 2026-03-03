# MandiMitra — AWS Resource Audit
**Audit Date:** March 1, 2026
**Account:** 471112620976
**Region:** us-east-1
**Auditor:** Claude Code (automated + manual verification)

---

## Summary

| Service | Resources | Status |
|---------|-----------|--------|
| Amazon Bedrock Agents | 5 agents (1 supervisor + 4 sub-agents) | ✅ PREPARED |
| AWS Lambda | 3 functions | ✅ Active |
| Amazon DynamoDB | 1 table, 2 GSIs | ✅ Active, ~5,177 items |
| Amazon API Gateway | 1 HTTP API, 2 routes | ✅ Live |
| Amazon CloudFront | 1 distribution | ✅ Deployed |
| Amazon S3 | 2 buckets | ✅ Active |
| Amazon EventBridge | 0 rules | ❌ NOT CONFIGURED |
| AWS IAM | 2 roles | ✅ Active |
| Amazon Bedrock Guardrails | 0 guardrails | ❌ EMPTY |
| LangFuse (external) | 1 project | ✅ Active (cloud.langfuse.com) |

---

## 1. Amazon Bedrock Agents

### 1.1 Supervisor Agent — MandiMitra

| Field | Value |
|-------|-------|
| Agent ID | GDSWGCDJIX |
| Agent Name | MandiMitra |
| Foundation Model | amazon.nova-pro-v1:0 |
| Status | PREPARED |
| Collaboration Mode | **SUPERVISOR** (multi-agent enabled) |
| Region | us-east-1 |
| Role ARN | arn:aws:iam::471112620976:role/MandiMitraBedrockAgentRole |
| Idle Session TTL | 1800 seconds (30 min) |

**Aliases:**

| Alias ID | Name | Points To | Status | Used By |
|----------|------|-----------|--------|---------|
| TSTALIASID | AgentTestAlias | DRAFT (always latest) | PREPARED | **mandimitra-chat Lambda (ACTIVE)** |
| BM6JROSWME | prod | Version 1 (Feb 27 baseline) | PREPARED | Not in use (legacy) |

**Action Groups on Supervisor (own tools — still active in SUPERVISOR mode):**

| Group ID | Name | Status | Functions |
|----------|------|--------|-----------|
| KYYMTPXMWY | BrowseTools | ENABLED | list_available_commodities, list_available_mandis, list_available_states |
| ASGXYH4STL | MandiTools | ENABLED | get_all_prices_at_mandi, get_mandi_profile |
| REC9WFZCNW | PriceIntelligenceTools | ENABLED | query_mandi_prices, get_nearby_mandis, get_price_trend, get_msp, get_sell_recommendation |
| MIYZDHRQ9H | WeatherTools | ENABLED | get_weather_advisory |

**Sub-Agent Collaborators (SUPERVISOR routes to these):**

| Collaborator Name | Sub-Agent ID | Alias ID | Alias ARN |
|-------------------|-------------|----------|-----------|
| PriceIntelligenceAgent | CAEJ90IYS6 | 7YU2OMSRBQ | arn:aws:bedrock:us-east-1:471112620976:agent-alias/CAEJ90IYS6/7YU2OMSRBQ |
| SellAdvisoryAgent | CCYSN80MGN | HPMZYLQZU3 | arn:aws:bedrock:us-east-1:471112620976:agent-alias/CCYSN80MGN/HPMZYLQZU3 |
| NegotiationAgent | UZRXDX75NR | TFQ24DRCOW | arn:aws:bedrock:us-east-1:471112620976:agent-alias/UZRXDX75NR/TFQ24DRCOW |
| WeatherAgent | XE43VNHO3T | YUSEVJPMWJ | arn:aws:bedrock:us-east-1:471112620976:agent-alias/XE43VNHO3T/YUSEVJPMWJ |

---

### 1.2 Sub-Agent: MandiMitra-PriceIntelligence

| Field | Value |
|-------|-------|
| Agent ID | CAEJ90IYS6 |
| Model | amazon.nova-pro-v1:0 |
| Status | PREPARED |
| Collaboration | DISABLED (leaf agent) |
| Live Alias | 7YU2OMSRBQ → Version 1 |

**Action Groups:**

| Group ID | Name | Status | Functions (5) |
|----------|------|--------|---------------|
| CEJXKNQW30 | PriceIntelligenceTools | ENABLED | query_mandi_prices, get_nearby_mandis, get_price_trend, get_msp, calculate_transport_cost |

---

### 1.3 Sub-Agent: MandiMitra-SellAdvisory

| Field | Value |
|-------|-------|
| Agent ID | CCYSN80MGN |
| Model | amazon.nova-pro-v1:0 |
| Status | PREPARED |
| Collaboration | DISABLED (leaf agent) |
| Live Alias | HPMZYLQZU3 → Version 1 |

**Action Groups:**

| Group ID | Name | Status | Functions (1, max 5 params enforced) |
|----------|------|--------|--------------------------------------|
| GNERDSXL60 | SellAdvisoryTools | ENABLED | get_sell_recommendation(commodity, state, latitude, longitude, quantity_qtl) |

> **Note:** Bedrock enforces max 5 parameters per function. `storage_available` parameter was removed to comply.

---

### 1.4 Sub-Agent: MandiMitra-Negotiation

| Field | Value |
|-------|-------|
| Agent ID | UZRXDX75NR |
| Model | amazon.nova-pro-v1:0 |
| Status | PREPARED |
| Collaboration | DISABLED (leaf agent) |
| Live Alias | TFQ24DRCOW → Version 1 |

**Action Groups:**

| Group ID | Name | Status | Functions (4) |
|----------|------|--------|---------------|
| EJIJRAT3XX | NegotiationTools | ENABLED | query_mandi_prices, get_msp, get_nearby_mandis, get_price_trend |

---

### 1.5 Sub-Agent: MandiMitra-Weather

| Field | Value |
|-------|-------|
| Agent ID | XE43VNHO3T |
| Model | amazon.nova-pro-v1:0 |
| Status | PREPARED |
| Collaboration | DISABLED (leaf agent) |
| Live Alias | YUSEVJPMWJ → Version 1 |

**Action Groups:**

| Group ID | Name | Status | Functions (1) |
|----------|------|--------|---------------|
| MSWQG140NA | WeatherTools | ENABLED | get_weather_advisory(location, latitude?, longitude?) |

---

### 1.6 Bedrock Guardrails

| Status | Detail |
|--------|--------|
| ❌ EMPTY | `list-guardrails` returns 0 results. No content filtering or hallucination guardrails are active. README previously claimed guardrails were active — **this is incorrect**. |

**Risk:** No guardrail protection against price hallucinations, PII, or toxic content in agent responses.

---

## 2. AWS Lambda

### 2.1 mandimitra-chat

| Field | Value |
|-------|-------|
| Runtime | Python 3.12 |
| Timeout | 29 seconds |
| Memory | 512 MB |
| Last Modified | 2026-03-01T13:13:23Z |
| Handler | handler.handler |
| Role | MandiMitraLambdaRole |

**Environment Variables:**

| Variable | Value |
|----------|-------|
| BEDROCK_AGENT_ID | GDSWGCDJIX |
| BEDROCK_AGENT_ALIAS_ID | TSTALIASID |
| LANGFUSE_HOST | https://cloud.langfuse.com |
| LANGFUSE_PUBLIC_KEY | pk-lf-c302cefb-95bc-4ca5-a796-625d20c71c57 |
| LANGFUSE_SECRET_KEY | sk-lf-ee5d287c-\*\*\*\* (redacted) |

**Purpose:** Receives user chat messages from API Gateway. Augments message with GPS context. Invokes Bedrock Supervisor Agent (TSTALIASID → DRAFT). Collects streaming response with 3-level fallback. Sends trace to LangFuse.

---

### 2.2 mandimitra-price-query

| Field | Value |
|-------|-------|
| Runtime | Python 3.12 |
| Timeout | 30 seconds |
| Memory | 256 MB |
| Last Modified | 2026-03-01T14:01:33Z |
| Handler | handler.handler |
| Role | MandiMitraLambdaRole |

**Environment Variables:**

| Variable | Value |
|----------|-------|
| PRICE_TABLE | MandiMitraPrices |
| AWS_REGION_NAME | us-east-1 |

**Purpose:** Serves as Action Group executor for ALL 5 Bedrock agents. Handles 13+ tool functions:
- Price queries (DynamoDB lookups with 4-level fallback)
- Sell recommendation (nearby mandis + trend + MSP + weather + season)
- Weather advisory (Open-Meteo API)
- Browse functions (list commodities/mandis/states)
- Transport cost calculation (Haversine)

**Zip structure (critical):** `handler.py` at root + `shared/` subdirectory with `dynamodb_utils.py`, `constants.py`, `weather_utils.py`, `__init__.py`.

---

### 2.3 mandimitra-data-ingestion

| Field | Value |
|-------|-------|
| Runtime | Python 3.12 |
| Timeout | 900 seconds (15 min) |
| Memory | 512 MB |
| Last Modified | 2026-03-01T10:31:19Z |
| Handler | handler.handler |
| Role | MandiMitraLambdaRole |

**Environment Variables:**

| Variable | Value |
|----------|-------|
| PRICE_TABLE | MandiMitraPrices |
| S3_BUCKET | mandimitra-data |
| DATA_GOV_API_KEY | (set, redacted) |

**Purpose:** Fetches daily commodity prices from Agmarknet via data.gov.in API. Transforms records (validates prices, dates). Batch-writes to DynamoDB. Writes audit log to S3.

**Trigger:** ❌ **NO EventBridge schedule configured.** Must be invoked manually or by fixing this gap (see Section 7).

---

## 3. Amazon DynamoDB

### 3.1 MandiMitraPrices

| Field | Value |
|-------|-------|
| Table Name | MandiMitraPrices |
| Status | ACTIVE |
| Billing Mode | PAY_PER_REQUEST |
| Item Count | ~5,177 (as of 2026-03-01) |
| Table Size | ~1.16 MB |
| Region | us-east-1 |
| ARN | arn:aws:dynamodb:us-east-1:471112620976:table/MandiMitraPrices |

**Schema:**

| Key | Type | Example |
|-----|------|---------|
| PK (Partition Key) | String | `WHEAT#MADHYA_PRADESH` |
| SK (Sort Key) | String | `2026-03-01#INDORE APMC` |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| commodity | String | Commodity name (e.g., "Wheat") |
| state | String | State name (e.g., "Madhya Pradesh") |
| district | String | District name (e.g., "Indore") |
| mandi_name | String | APMC market name UPPERCASE |
| arrival_date | String | ISO date YYYY-MM-DD |
| variety | String | Crop variety |
| min_price | Number (Decimal) | Minimum price ₹/quintal |
| max_price | Number (Decimal) | Maximum price ₹/quintal |
| modal_price | Number (Decimal) | Modal (most common) price ₹/quintal |
| date_commodity | String | `{date}#{COMMODITY}` — for GSI |
| ingested_at | String | ISO timestamp of ingestion |
| arrivals_tonnes | Number (optional) | Arrivals in tonnes if available |

**Global Secondary Indexes:**

| Index Name | Partition Key | Sort Key | Purpose |
|------------|---------------|----------|---------|
| DATE-INDEX | arrival_date | PK | Query all prices for a date |
| MANDI-INDEX | mandi_name | date_commodity | Query all commodities at a mandi |

**Data Coverage:**
- 20 commodities: Wheat, Soyabean, Onion, Tomato, Potato, Mustard, Chana, Maize, Cotton, Rice, Garlic, Moong, Urad, Bajra, Jowar, Groundnut, Turmeric, Red Chilli, Coriander, Cumin
- 14 states: Madhya Pradesh, Rajasthan, Maharashtra, Uttar Pradesh, Gujarat, Karnataka, Punjab, Haryana, Andhra Pradesh, Telangana, Tamil Nadu, Bihar, West Bengal, Chhattisgarh
- Date range: Feb 23–Mar 1, 2026 (7 days)
- 60+ APMC mandis with GPS coordinates in constants.py

**Data Source:** Agmarknet via data.gov.in (resource ID: `9ef84268-d588-465a-a308-a864a43d0070`)

---

## 4. Amazon API Gateway

### 4.1 MandiMitraAPI

| Field | Value |
|-------|-------|
| API ID | skwsw8qk22 |
| Name | MandiMitraAPI |
| Type | HTTP API (v2) |
| Stage | prod |
| Base URL | https://skwsw8qk22.execute-api.us-east-1.amazonaws.com/prod |

**Routes:**

| Method | Path | Lambda | Purpose |
|--------|------|--------|---------|
| POST | /api/chat | mandimitra-chat | Chat endpoint |
| GET | /api/prices/{commodity} | mandimitra-price-query | Direct price query |
| OPTIONS | /* | (CORS preflight) | CORS support |

**CORS Configuration:**
- Allow-Origin: `*`
- Allow-Headers: `Content-Type, Authorization`
- Allow-Methods: `POST, OPTIONS`

---

## 5. Amazon CloudFront

### 5.1 MandiMitra CDN

| Field | Value |
|-------|-------|
| Distribution ID | E1FOPZ17Q7P6CF |
| Domain | d2mtfau3fvs243.cloudfront.net |
| Status | Deployed |
| Price Class | PriceClass_All (global edge) |
| HTTP/2 | Enabled |
| HTTP→HTTPS | Redirect |
| Origin | mandimitra-frontend-471112620976.s3-website-us-east-1.amazonaws.com |

**Purpose:** Provides HTTPS (required for Web Speech API / voice input and Geolocation API / GPS). S3 static hosting only supports HTTP; CloudFront adds free SSL/TLS.

---

## 6. Amazon S3

### 6.1 mandimitra-frontend-471112620976

| Field | Value |
|-------|-------|
| Created | 2026-02-28 |
| Purpose | Static website hosting — Next.js 14 SSG build |
| Website URL | http://mandimitra-frontend-471112620976.s3-website-us-east-1.amazonaws.com |
| Public Access | Enabled (required for static website) |
| Served via | CloudFront d2mtfau3fvs243.cloudfront.net (HTTPS) |

### 6.2 mandimitra-deployment-471112620976

| Field | Value |
|-------|-------|
| Created | 2026-02-27 |
| Purpose | Lambda deployment zip packages |
| Contents | chat_handler.zip, price_query.zip, data_ingestion.zip |

---

## 7. Amazon EventBridge

### ❌ CRITICAL GAP — No Rules Configured

| Check | Result |
|-------|--------|
| Rules in us-east-1 | **0 rules found** |
| Daily ingestion schedule | **MISSING** |

**Impact:** The `mandimitra-data-ingestion` Lambda has no scheduled trigger. The README and WORKLOG claim "Daily at 9:30 PM IST (4:00 PM UTC)" — this **does not exist** in AWS. Data must be ingested manually.

**Fix required:**
```bash
aws events put-rule \
  --name mandimitra-daily-ingestion \
  --schedule-expression "cron(0 16 * * ? *)" \
  --state ENABLED \
  --region us-east-1

aws events put-targets \
  --rule mandimitra-daily-ingestion \
  --targets "Id=ingestion,Arn=arn:aws:lambda:us-east-1:471112620976:function:mandimitra-data-ingestion,Input={\"days_back\":1}" \
  --region us-east-1

# Add Lambda permission for EventBridge
aws lambda add-permission \
  --function-name mandimitra-data-ingestion \
  --statement-id EventBridgeDailyInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:471112620976:rule/mandimitra-daily-ingestion \
  --region us-east-1
```

---

## 8. AWS IAM

### 8.1 MandiMitraLambdaRole

| Field | Value |
|-------|-------|
| Role Name | MandiMitraLambdaRole |
| Type | Lambda execution role |
| Trust Policy | lambda.amazonaws.com |

**Attached Policies:**

| Policy | Access Level | Notes |
|--------|-------------|-------|
| AWSLambdaBasicExecutionRole | CloudWatch Logs write | Required for Lambda logging |
| AmazonDynamoDBFullAccess | DynamoDB full access | ⚠️ Overprivileged — should be table-scoped |
| AmazonS3FullAccess | S3 full access | ⚠️ Overprivileged — should be bucket-scoped |
| AmazonBedrockFullAccess | Bedrock full access | ⚠️ Overprivileged — should be agent-invoke only |

**Recommendation for production:** Replace AWS-managed full-access policies with resource-scoped inline policies.

---

### 8.2 MandiMitraBedrockAgentRole

| Field | Value |
|-------|-------|
| Role Name | MandiMitraBedrockAgentRole |
| Type | Bedrock Agent execution role |
| Trust Policy | bedrock.amazonaws.com |

**Attached Policies:**

| Policy | Notes |
|--------|-------|
| AmazonBedrockFullAccess | Allows agent to call Lambda, Bedrock models |

---

## 9. Observability & Monitoring

### 9.1 Amazon CloudWatch

| Resource | Log Group | Retention |
|----------|-----------|-----------|
| mandimitra-chat | /aws/lambda/mandimitra-chat | Default (never expire) |
| mandimitra-price-query | /aws/lambda/mandimitra-price-query | Default |
| mandimitra-data-ingestion | /aws/lambda/mandimitra-data-ingestion | Default |

**No CloudWatch Alarms, Dashboards, or Metrics configured.**

---

### 9.2 LangFuse (External Observability)

| Field | Value |
|-------|-------|
| Provider | LangFuse Cloud (cloud.langfuse.com) |
| SDK Version | langfuse==2.60.10 (pinned <3.0.0) |
| Status | ✅ Active — traces every agent invocation |
| Project | MandiMitra |
| Integration | mandimitra-chat Lambda sends spans on each call |

**What is traced per call:**
- Full session trace (session_id)
- Each agent step as a span: preprocessing, reasoning, tool_call, observation, model_output
- Latency per step
- Token counts (input/output)
- Errors

---

## 10. Gaps & Recommendations

| # | Gap | Severity | Fix |
|---|-----|----------|-----|
| 1 | **EventBridge schedule missing** | 🔴 HIGH | Create daily cron rule at 4:00 PM UTC → mandimitra-data-ingestion |
| 2 | **Bedrock Guardrails empty** | 🟡 MEDIUM | Create guardrail: block price hallucinations, add topic filter |
| 3 | **IAM overprivileged** | 🟡 MEDIUM | Replace FullAccess policies with scoped policies |
| 4 | **No CloudWatch alarms** | 🟡 MEDIUM | Add alarms for Lambda errors, throttles, DynamoDB errors |
| 5 | **prod alias (BM6JROSWME) stale** | 🟢 LOW | Update prod alias to include SUPERVISOR collaboration config |
| 6 | **S3 data bucket missing** | 🟢 LOW | mandimitra-data bucket (for audit logs) may not exist |
| 7 | **No WAF on CloudFront** | 🟢 LOW | Add AWS WAF for production rate limiting |
| 8 | **Lambda cold start latency** | 🟢 LOW | Add provisioned concurrency for mandimitra-chat |

---

## 11. Architecture Diagram (Current State)

```
Internet User (Farmer's Phone — Hindi/Voice/GPS)
        │
        ▼
CloudFront HTTPS CDN (E1FOPZ17Q7P6CF)
d2mtfau3fvs243.cloudfront.net
        │
        ▼
S3 Static Website (mandimitra-frontend-471112620976)
Next.js 14 PWA — SSG export
        │ POST /api/chat
        ▼
API Gateway HTTP (skwsw8qk22)
POST /api/chat ──────────────────────────────┐
GET /api/prices/{commodity}                  │
        │                                    │
        ▼                                    ▼
mandimitra-chat Lambda              mandimitra-price-query Lambda
(TSTALIASID → GDSWGCDJIX DRAFT)     (Direct API endpoint)
        │ invoke_agent
        ▼
╔══════════════════════════════════════════════════╗
║  Bedrock SUPERVISOR: MandiMitra (GDSWGCDJIX)    ║
║  Model: Nova Pro | Mode: SUPERVISOR              ║
║  Own Action Groups: Browse, Mandi, PriceIntel,  ║
║                     Weather (direct tools)       ║
╠══════════════════════════════════════════════════╣
║  Routes to sub-agents:                           ║
║  ┌──────────────────────────────────────────┐   ║
║  │ PriceIntelligenceAgent (CAEJ90IYS6)      │   ║
║  │ → PriceIntelligenceTools                 │   ║
║  │   (query_mandi_prices, nearby, trend,    │   ║
║  │    msp, transport_cost)                  │   ║
║  ├──────────────────────────────────────────┤   ║
║  │ SellAdvisoryAgent (CCYSN80MGN)           │   ║
║  │ → SellAdvisoryTools                      │   ║
║  │   (get_sell_recommendation)              │   ║
║  ├──────────────────────────────────────────┤   ║
║  │ NegotiationAgent (UZRXDX75NR)            │   ║
║  │ → NegotiationTools                       │   ║
║  │   (prices, msp, nearby, trend)           │   ║
║  ├──────────────────────────────────────────┤   ║
║  │ WeatherAgent (XE43VNHO3T)                │   ║
║  │ → WeatherTools                           │   ║
║  │   (get_weather_advisory)                 │   ║
║  └──────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════╝
        │ (all sub-agent tool calls)
        ▼
mandimitra-price-query Lambda
(Action Group executor for all 5 agents)
        │
    ┌───┴────────────────────────┐
    ▼                            ▼
DynamoDB                   Open-Meteo API
MandiMitraPrices           (Weather forecast)
~5,177 items               Free, no key needed
2 GSIs

Data pipeline (manual only — EventBridge MISSING):
data.gov.in Agmarknet API
        │
        ▼
mandimitra-data-ingestion Lambda
(900s timeout, triggered manually)
        │
        ▼
DynamoDB + S3 audit log
```

---

*Generated by Claude Code — automated boto3 API audit + manual verification.*
*Cross-referenced with: CloudWatch logs, Lambda test invocations, Bedrock agent API responses.*
