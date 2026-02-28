# Design Document - MandiMitra: Agentic Market Intelligence Copilot for Agri-Commerce

## 1. System Architecture Overview

MandiMitra follows a **multi-agent agentic architecture** built on AWS services, with Amazon Bedrock Agents at the core orchestrating specialized AI agents that each handle a distinct domain of market intelligence.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│        (Next.js 14 SSG on S3 — Mobile-First PWA)               │
│         Hindi / English / Code-Mixed Conversational UI          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (API Gateway)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                            │
│             (Amazon Bedrock Agents — Nova Pro)                  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Price    │  │  Sell    │  │Negotiation│  │  Weather-     │  │
│  │  Intel    │  │ Advisory │  │   Prep    │  │  Market       │  │
│  │  Agent    │  │  Agent   │  │   Agent   │  │  Agent        │  │
│  └────┬─────┘  └────┬─────┘  └────┬──────┘  └──────┬────────┘  │
│       │              │             │                │            │
│  ┌────▼──────────────▼─────────────▼────────────────▼────────┐  │
│  │                    TOOL LAYER                              │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │Agmarknet│ │ Weather  │ │ Distance │ │  DynamoDB    │  │  │
│  │  │  API    │ │   API    │ │Calculator│ │  Query Tool  │  │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌──────────────┐ ┌────────┐ ┌──────────────────┐
     │  DynamoDB    │ │   S3   │ │ Bedrock Knowledge │
     │ (Price Data) │ │ (Docs) │ │   Bases (RAG)    │
     └──────────────┘ └────────┘ └──────────────────┘
```

---

## 2. Component Design

### 2.1 Data Ingestion Pipeline

**Purpose:** Automated daily pipeline to fetch, transform, and store mandi price data.

**Architecture:**
```
EventBridge (Daily 6 AM IST)
    → Lambda: fetch_agmarknet_data()
        → Fetch CSV/API from data.gov.in Agmarknet
        → Parse and validate records
        → Transform to DynamoDB schema
        → Batch write to DynamoDB
        → Store raw CSV in S3 (audit trail)
    → Lambda: fetch_weather_data()
        → Fetch IMD district-level forecasts
        → Store in DynamoDB weather table
    → Lambda: compute_derived_metrics()
        → Calculate 7/30/90-day moving averages
        → Detect anomalies (Z-score > 2)
        → Flag significant price movements
        → Write to DynamoDB analytics table
```

**DynamoDB Schema — Price Data Table:**

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String | `COMMODITY#STATE` (e.g., `SOYABEAN#MADHYA_PRADESH`) |
| SK | String | `DATE#MANDI` (e.g., `2026-02-15#INDORE`) |
| min_price | Number | Minimum traded price (₹/quintal) |
| max_price | Number | Maximum traded price (₹/quintal) |
| modal_price | Number | Modal (most frequent) price |
| arrivals_tonnes | Number | Quantity arrived at mandi |
| variety | String | Crop variety |
| district | String | District name |
| latitude | Number | Mandi geo-coordinate |
| longitude | Number | Mandi geo-coordinate |
| ma_7d | Number | 7-day moving average |
| ma_30d | Number | 30-day moving average |
| anomaly_flag | Boolean | True if price deviation > 2 std dev |

**GSI-1:** `MANDI-INDEX` — PK: `MANDI_NAME`, SK: `DATE#COMMODITY` (for mandi-centric queries)
**GSI-2:** `DATE-INDEX` — PK: `DATE`, SK: `COMMODITY#STATE` (for daily market summaries)

### 2.2 Orchestrator Agent (Amazon Bedrock Agents)

**Purpose:** Central coordinator that receives user queries, determines intent, and orchestrates specialist agents.

**Design:**
- Built on Amazon Bedrock Agents with Nova Pro as the foundation model
- Uses a system prompt that defines the orchestration logic
- Maintains conversation state within session
- Routes to specialist agents based on classified intent

**Intent Classification:**

| User Intent | Routed To | Example Query |
|-------------|-----------|---------------|
| Price lookup | Price Intelligence Agent | "गेहूं का भाव क्या है?" |
| Price comparison | Price Intelligence Agent | "Which mandi has best soyabean price near Indore?" |
| Sell/hold decision | Sell Advisory Agent | "Should I sell my onions now or wait?" |
| Negotiation prep | Negotiation Prep Agent | "Give me a price brief for mustard in Kota" |
| Weather impact | Weather-Market Agent | "Will rain affect tomato prices?" |
| Complex / multi-step | Sequential orchestration | "मेरे पास 50 क्विंटल सोयाबीन है, कहाँ बेचूं?" |

**Orchestration Flow for Complex Queries:**
```
User: "मेरे पास 50 क्विंटल सोयाबीन है, कहाँ बेचूं?"
(I have 50 quintals of soyabean, where should I sell?)

Step 1: Orchestrator classifies → multi-step sell advisory
Step 2: Price Intel Agent → fetches soyabean prices across nearby mandis
Step 3: Weather-Market Agent → checks if weather events may impact prices
Step 4: Sell Advisory Agent → combines price data + weather + quantity 
        → calculates net realization per mandi (price - transport cost)
        → recommends: "Sell at Indore Mandi (₹4,850/q) — ₹320 higher net 
           realization than Ujjain after transport costs. Prices trending up 
           2% this week. If you can hold 5 days, forecast suggests ₹4,920."
Step 5: Orchestrator formats response in Hindi → returns to user
```

### 2.3 Price Intelligence Agent

**Tools Available:**
- `query_mandi_prices(commodity, state, date_range)` → DynamoDB query
- `get_nearby_mandis(latitude, longitude, radius_km)` → DynamoDB geo-query
- `calculate_transport_cost(origin_lat, origin_lon, dest_lat, dest_lon, quantity_quintals)` → Lambda function
- `get_msp(commodity, year)` → S3/Knowledge Base lookup

**Agent Prompt (Condensed):**
```
You are the Price Intelligence Agent for MandiMitra. Your role is to provide 
accurate, data-driven mandi price analysis. 

RULES:
- Always cite the data source and timestamp with every price you mention
- Never hallucinate prices — if data is unavailable, say so clearly
- When comparing mandis, always factor in transportation costs
- Present prices in ₹/quintal (the standard Indian unit)
- Flag anomalies and explain likely causes
- Respond in the same language the user used
```

### 2.4 Sell Advisory Agent

**Decision Logic:**
```
Input: commodity, quantity, location, storage_available (boolean), 
       storage_days_max, urgency

1. Fetch current prices + 30-day trend from Price Intel Agent
2. Fetch weather forecast from Weather-Market Agent
3. Compute:
   - trend_direction: rising / falling / stable
   - volatility: low / medium / high (std dev of last 30 days)
   - perishability_index: 1-10 (pre-configured per commodity)
   - storage_cost_per_day: ₹/quintal (pre-configured)
   - weather_impact_score: -1 to +1

4. Decision Matrix:
   IF trend_direction == rising AND perishability_index < 5 AND storage_available:
       → RECOMMEND: "Hold for {optimal_days} days. Forecast: +{x}%"
   ELIF trend_direction == falling OR perishability_index >= 7:
       → RECOMMEND: "Sell now at {best_mandi}. Prices declining."
   ELIF volatility == high:
       → RECOMMEND: "Market volatile. Sell 50% now, hold 50%."
   ELSE:
       → RECOMMEND: "Sell at {best_net_price_mandi}. Stable market."

5. Always include: confidence level (%), reasoning, alternative options
```

### 2.5 Negotiation Prep Agent

**Output Format — Price Brief:**
```
╔══════════════════════════════════════════════════╗
║          MandiMitra Price Brief                  ║
║          सोयाबीन — 15 Feb 2026                   ║
╠══════════════════════════════════════════════════╣
║ MSP Reference:        ₹4,892/quintal            ║
║ Your Mandi (Indore):  ₹4,850/quintal (modal)    ║
║ Best Nearby Mandi:    ₹5,020 (Dewas, 38km)      ║
║ 7-Day Trend:          ▲ +2.3%                   ║
║ Quality-Adjusted Range: ₹4,700 — ₹5,100         ║
║                                                  ║
║ Fair Price Estimate:  ₹4,920 — ₹5,050           ║
║ (based on grade, arrivals, trend)               ║
╠══════════════════════════════════════════════════╣
║ Data Source: Agmarknet | Generated: 15-Feb-2026  ║
╚══════════════════════════════════════════════════╝
```

### 2.6 Bedrock Knowledge Base (RAG)

**Document Corpus:**
- APMC Act guidelines and recent reforms (eNAM, APMC bypass rules)
- MSP policy documents for all Kharif and Rabi crops
- ICAR crop-wise best practices for post-harvest handling
- PM-KISAN, PMFBY scheme eligibility and application guides
- Government warehouse and cold storage directory

**Configuration:**
- Amazon S3 bucket: `mandimitra-knowledge-base/`
- Bedrock Knowledge Base with chunking strategy: fixed 300-token chunks with 50-token overlap
- Embedding model: Amazon Titan Embeddings v2
- Vector store: Amazon OpenSearch Serverless

---

## 3. Frontend Design

### 3.1 Technology Stack
- **Framework:** Next.js 14 (SSG with `output: "export"` for S3 static hosting)
- **Styling:** Tailwind CSS (mobile-first utilities)
- **State Management:** React useState hooks
- **Deployment:** S3 Static Website Hosting (mandimitra-frontend-471112620976)
- **PWA:** manifest.json + service worker for offline/installable

### 3.2 UI Components

**Chat Interface (Primary):**
- WhatsApp-style chat bubbles (familiar UX for Indian users)
- Voice input button (uses Web Speech API → text → Bedrock)
- Language toggle: हिंदी / English
- Quick action buttons: "Check Price", "Best Mandi", "Price Brief"

**Dashboard View (Secondary — for FPO users):**
- Commodity price cards with sparkline trends
- Map view: nearby mandis with color-coded prices (green = above avg, red = below)
- Alerts panel: anomalies, weather impacts, MSP updates

### 3.3 Mobile-First Constraints
- Max initial bundle: 300KB (gzipped)
- Works on Chrome Android 80+ (covers 95% of Indian smartphone users)
- Offline-capable: last viewed prices cached in localStorage
- Large touch targets (min 48x48px) per Material Design accessibility guidelines

---

## 4. API Design

### 4.1 REST Endpoints (API Gateway + Lambda)

```
POST /api/chat
  Body: { "message": "string", "language": "hi|en", "session_id": "string" }
  Response: { "response": "string", "agent_trace": [...], "data": {...} }

GET /api/prices/{commodity}
  Query: ?state=MP&mandi=INDORE&days=30
  Response: { "prices": [...], "trend": {...}, "anomalies": [...] }

GET /api/mandis/nearby
  Query: ?lat=22.71&lon=75.85&radius_km=100&commodity=SOYABEAN
  Response: { "mandis": [...], "best_price_mandi": {...} }

POST /api/price-brief
  Body: { "commodity": "string", "mandi": "string", "language": "hi|en" }
  Response: { "brief_text": "string", "brief_pdf_url": "string" }

GET /api/weather-impact/{commodity}
  Query: ?state=MP&district=INDORE
  Response: { "forecast": {...}, "price_impact_estimate": {...} }
```

---

## 5. Security Design

| Layer | Mechanism |
|-------|-----------|
| Transport | TLS 1.2+ enforced on API Gateway |
| Authentication | API Key (MVP) → Cognito (production) |
| Authorization | IAM roles with least-privilege for Lambda functions |
| Data at Rest | DynamoDB encryption (AWS managed keys) |
| Input Validation | API Gateway request validators + Lambda input sanitization |
| LLM Safety | Bedrock Guardrails: block PII generation, enforce factual grounding |
| Rate Limiting | API Gateway throttling: 100 req/sec per API key |

---

## 6. Monitoring & Observability

| Metric | Tool | Alert Threshold |
|--------|------|-----------------|
| API latency (p99) | CloudWatch | > 10 seconds |
| Lambda errors | CloudWatch Alarms | > 5% error rate |
| Bedrock token usage | CloudWatch + Billing | > ₹500/day |
| Data freshness | Custom metric | Data > 24 hours stale |
| Agent trace failures | CloudWatch Logs | Any tool invocation failure |
| DynamoDB throttling | CloudWatch | Any throttle event |

---

## 7. Cost Estimation (MVP — 1,000 DAU)

| Service | Monthly Estimate |
|---------|-----------------|
| Amazon Bedrock (Nova Pro — ~50K queries × 1K tokens avg) | ₹4,000 |
| DynamoDB (on-demand, ~5GB storage, ~500K reads/month) | ₹800 |
| Lambda (100K invocations, 256MB, avg 3s) | ₹200 |
| S3 (10GB storage + transfer) | ₹100 |
| API Gateway (100K requests) | ₹300 |
| CloudWatch (logs + metrics) | ₹200 |
| Bedrock Knowledge Base (OpenSearch Serverless) | ₹3,000 |
| **Total** | **~₹8,600/month** |

---

## 8. Future Enhancements (Post-Hackathon Roadmap)

1. **WhatsApp Integration** — via Twilio/Meta Business API for zero-download reach
2. **Crop Photo Analysis** — upload crop photo → quality grading → price adjustment
3. **FPO Dashboard** — aggregated analytics, bulk sell coordination, demand matching
4. **eNAM Integration** — direct online mandi trading from within MandiMitra
5. **Credit Linkage** — connect farmers to Kisan Credit Card and warehouse receipt financing
6. **Multi-State Expansion** — add support for Tamil, Telugu, Marathi, Gujarati, Punjabi
7. **Satellite Data** — integrate NDVI/crop health data for yield-adjusted forecasting
