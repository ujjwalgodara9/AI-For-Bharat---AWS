# MandiMitra — Architecture & Code Flow

## System Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │           USER (Farmer's Phone)             │
                    │    Browser / WhatsApp-style Chat UI         │
                    └──────────────────┬──────────────────────────┘
                                       │ HTTPS + GPS coords
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │         S3 Static Website Hosting           │
                    │     Next.js 14 + Tailwind CSS (SSG)         │
                    │   mandimitra-frontend-471112620976           │
                    └──────────────────┬──────────────────────────┘
                                       │ POST /api/chat
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │          API Gateway (REST)                 │
                    │         skwsw8qk22 / prod stage            │
                    │  POST /api/chat  →  mandimitra-chat        │
                    │  GET /api/prices/{commodity}  →  price-query│
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────────────┐
                    │                  ▼                          │
                    │    mandimitra-chat (Lambda)                 │
                    │    ┌────────────────────────────┐           │
                    │    │ 1. Parse user message       │           │
                    │    │ 2. Inject GPS + language     │           │
                    │    │ 3. Invoke Bedrock Agent      │           │
                    │    │ 4. Collect response + traces │           │
                    │    │ 5. Return JSON to frontend   │           │
                    │    └─────────────┬──────────────┘           │
                    │                  │                          │
                    │                  ▼                          │
                    │    Amazon Bedrock Agent (Nova Pro)          │
                    │    Agent ID: GDSWGCDJIX                    │
                    │    ┌────────────────────────────┐           │
                    │    │ 1. Classify intent           │           │
                    │    │ 2. Select tool/function      │           │
                    │    │ 3. Call Action Group Lambda   │           │
                    │    │ 4. Process tool output        │           │
                    │    │ 5. Generate Hindi response    │           │
                    │    └─────────────┬──────────────┘           │
                    │                  │                          │
                    │    ┌─────────────┼──────────────┐           │
                    │    │             ▼              │           │
                    │    │  mandimitra-price-query    │           │
                    │    │  (Action Group Lambda)     │           │
                    │    │  6 functions:              │           │
                    │    │  - query_mandi_prices      │           │
                    │    │  - get_nearby_mandis       │           │
                    │    │  - get_price_trend         │           │
                    │    │  - get_msp                 │           │
                    │    │  - get_sell_recommendation │           │
                    │    │  - get_all_prices_at_mandi │           │
                    │    └─────────────┬──────────────┘           │
                    │                  │                          │
                    │                  ▼                          │
                    │    DynamoDB: MandiMitraPrices               │
                    │    PK: COMMODITY#STATE                      │
                    │    SK: DATE#MANDI                           │
                    │    GSI-1 (MANDI-INDEX): mandi_name          │
                    │    GSI-2 (DATE-INDEX): arrival_date          │
                    └─────────────────────────────────────────────┘
```

## Data Flow — Chat Message

```
User types: "wheat ka bhav MP mein"
     │
     ▼
Frontend (page.tsx)
  ├── Gets GPS from browser: {lat: 22.71, lon: 75.85}
  ├── POST /api/chat {message, language: "hi", latitude, longitude, session_id}
     │
     ▼
API Gateway → mandimitra-chat Lambda (handler.py)
  ├── Parses body: message, language, lat, lon
  ├── Builds augmented message:
  │   "[Respond in Hindi] [User GPS: lat=22.71, lon=75.85] wheat ka bhav MP mein"
  ├── Calls bedrock_agent_runtime.invoke_agent()
     │
     ▼
Bedrock Agent (Nova Pro model)
  ├── Pre-processing: classifies intent → PRICE_CHECK
  ├── Reasoning: "Need wheat prices in Madhya Pradesh"
  ├── Tool call: PriceIntelligenceTools/query_mandi_prices
  │   params: {commodity: "wheat", state: "Madhya Pradesh"}
     │
     ▼
mandimitra-price-query Lambda (handle_agent_action)
  ├── Calls query_prices("wheat", "Madhya Pradesh")
  │   → DynamoDB query: PK="WHEAT#MADHYA_PRADESH", SK between dates
  ├── Calls get_price_trend("wheat", "Madhya Pradesh")
  ├── Calls get_msp("wheat") → ₹2275
  ├── Returns JSON: {prices: [...], trend: {...}, msp: {...}}
     │
     ▼
Bedrock Agent processes tool output
  ├── Generates Hindi response with prices, trend, MSP
  ├── Returns response in <answer> tags
     │
     ▼
Chat Lambda collects response
  ├── Primary: chunk bytes from completion stream
  ├── Fallback 1: extract from trace's <answer> tag
  ├── Fallback 2: retry without traces
  ├── Returns: {response, session_id, agent_trace, latency_seconds}
     │
     ▼
Frontend renders ChatBubble with Hindi response
  └── Agent trace expandable in UI
```

## File Structure & Purpose

```
hackathon/
├── frontend/                          # Next.js 14 + Tailwind CSS
│   ├── app/
│   │   ├── page.tsx                   # Main chat page
│   │   │   - State: messages, language, sessionId, userLocation
│   │   │   - GPS detection on mount via navigator.geolocation
│   │   │   - sendMessage() → POST /api/chat with location
│   │   │   - Fallback demo mode when API_BASE not set
│   │   │
│   │   ├── components/
│   │   │   ├── ChatHeader.tsx         # App header with language toggle + location indicator
│   │   │   ├── ChatBubble.tsx         # Message bubbles + expandable agent trace panel
│   │   │   ├── ChatInput.tsx          # Text input + voice mic (Web Speech API)
│   │   │   ├── QuickActions.tsx       # Quick action buttons (4 flows)
│   │   │   ├── TypingIndicator.tsx    # Animated thinking dots
│   │   │   └── WelcomeScreen.tsx      # Welcome screen with feature cards
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client, interfaces (ChatMessage, ChatResponse, etc.)
│   │   │   └── voice.ts              # Web Speech API wrapper for Hindi/English
│   │   │
│   │   ├── layout.tsx                 # Root layout (metadata, fonts)
│   │   └── globals.css                # Tailwind + custom styles
│   │
│   ├── .env.local                     # NEXT_PUBLIC_API_URL=https://skwsw8qk22...
│   ├── next.config.mjs                # output: "export" for S3 static hosting
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/
│   ├── lambdas/
│   │   ├── chat_handler/
│   │   │   └── handler.py             # Chat endpoint Lambda
│   │   │       - handler(): API Gateway entry point
│   │   │       - invoke_agent(): Calls Bedrock Agent with message + GPS
│   │   │       - extract_trace(): Parses trace events for UI
│   │   │       - Fallback chain: chunk → trace answer → retry
│   │   │
│   │   ├── price_query/
│   │   │   └── handler.py             # Price query + Bedrock Action Group Lambda
│   │   │       - handle_api_request(): Direct GET /api/prices/{commodity}
│   │   │       - handle_agent_action(): Bedrock Agent tool invocations
│   │   │       - 7 functions: query_mandi_prices, get_nearby_mandis,
│   │   │         get_price_trend, get_msp, calculate_transport_cost,
│   │   │         get_sell_recommendation, get_all_prices_at_mandi
│   │   │
│   │   ├── data_ingestion/
│   │   │   └── handler.py             # Data ingestion Lambda
│   │   │       - Fetches from data.gov.in API
│   │   │       - Transforms to DynamoDB format
│   │   │       - Batch writes to MandiMitraPrices table
│   │   │
│   │   └── shared/                    # Shared modules (bundled with each Lambda)
│   │       ├── __init__.py
│   │       ├── dynamodb_utils.py      # DynamoDB query functions
│   │       │   - query_prices(commodity, state, mandi, days)
│   │       │     → PK query with date range, fallback to all history
│   │       │   - query_mandi_prices(mandi, days)
│   │       │     → GSI-1 (MANDI-INDEX) query for all commodities
│   │       │   - get_nearby_mandis(lat, lon, radius, commodity)
│   │       │     → Haversine distance calc from MANDI_COORDINATES
│   │       │   - get_price_trend(commodity, state, mandi, days)
│   │       │     → Statistics: direction, change%, volatility
│   │       │   - get_msp(commodity) → case-insensitive MSP lookup
│   │       │   - get_sell_recommendation_data() → comprehensive sell data
│   │       │   - calculate_net_realization() → price minus transport
│   │       │   - haversine_distance() → GPS distance in km
│   │       │
│   │       └── constants.py           # Static configuration
│   │           - MANDI_COORDINATES: 35 major mandis with GPS
│   │           - MSP_RATES: 20 commodities for 2025-26
│   │           - PERISHABILITY_INDEX: 1-10 scale per commodity
│   │           - STORAGE_COST_PER_DAY: ₹/qtl/day
│   │           - TRANSPORT_COST_PER_QTL_PER_KM: ₹0.8
│   │
│   ├── agent_configs/
│   │   ├── orchestrator_prompt.txt    # Bedrock Agent system prompt
│   │   │   - Intent classification (6 intents)
│   │   │   - Language rules (Hindi/English auto-detect)
│   │   │   - Location handling (GPS injection)
│   │   │   - Response format templates
│   │   │   - Guardrails
│   │   │
│   │   └── price_intel_openapi.json   # OpenAPI spec (not used — Bedrock rejected it)
│   │
│   └── scripts/
│       ├── fetch_data_local.py        # Initial data fetcher
│       ├── fetch_more_data.py         # Targeted commodity/state data fetcher
│       └── load_dynamodb.py           # Batch load items into DynamoDB
│
├── data/
│   └── dynamodb_items.json            # Fetched price data (379 records)
│
├── deploy_packages/                   # Lambda zip files + test outputs
│
├── ARCHITECTURE.md                    # This file
├── WORKLOG.md                         # Detailed work log with all decisions
├── PLAN.md                            # 5-day execution plan
├── TEAM_HANDOFF.md                    # Team status document
└── README.md                          # Project overview
```

## DynamoDB Schema

**Table: MandiMitraPrices**

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String (Partition Key) | `{COMMODITY}#{STATE}` e.g., `WHEAT#MADHYA_PRADESH` |
| SK | String (Sort Key) | `{YYYY-MM-DD}#{MANDI_NAME}` e.g., `2026-02-26#ARON APMC` |
| commodity | String | Original commodity name (e.g., "Wheat") |
| state | String | Original state name (e.g., "Madhya Pradesh") |
| district | String | District name |
| mandi_name | String | APMC mandi name (uppercase) |
| arrival_date | String | ISO date (YYYY-MM-DD) |
| variety | String | Crop variety |
| min_price | Number | Minimum price ₹/quintal |
| max_price | Number | Maximum price ₹/quintal |
| modal_price | Number | Modal (most common) price ₹/quintal |
| date_commodity | String | `{date}#{COMMODITY}` — used by MANDI-INDEX GSI |

**GSI-1 (MANDI-INDEX):** PK=`mandi_name`, SK=`date_commodity`
- Enables: "Show all commodities at mandi X"

**GSI-2 (DATE-INDEX):** PK=`arrival_date`, SK=`PK`
- Enables: "Show all prices on date X"

## AWS Resources

| Resource | ID/Name | Purpose |
|----------|---------|---------|
| DynamoDB | MandiMitraPrices | Price time-series data |
| S3 (frontend) | mandimitra-frontend-471112620976 | Static website hosting |
| S3 (deploy) | mandimitra-deployment-471112620976 | Lambda deployment packages |
| Lambda | mandimitra-chat | Chat endpoint (invokes Bedrock Agent) |
| Lambda | mandimitra-price-query | Price queries + Bedrock Action Group |
| Lambda | mandimitra-data-ingestion | Data fetcher from data.gov.in |
| API Gateway | skwsw8qk22 | REST API with CORS |
| Bedrock Agent | GDSWGCDJIX | Multi-agent orchestrator (Nova Pro) |
| Agent Alias | TSTALIASID | Points to DRAFT version |
| IAM | MandiMitraLambdaRole | Lambda execution role |
| IAM | MandiMitraBedrockAgentRole | Bedrock Agent role |

## Agent Action Groups

**PriceIntelligenceTools** (5 functions):
1. `query_mandi_prices(commodity, state, mandi?, days?)` — Price lookup
2. `get_nearby_mandis(latitude, longitude, radius_km, commodity?)` — GPS-based mandi finder
3. `get_price_trend(commodity, state, mandi?, days?)` — Trend analysis
4. `get_msp(commodity)` — MSP lookup
5. `get_sell_recommendation(commodity, state, latitude, longitude, quantity_qtl)` — Sell/hold data

**MandiTools** (1 function):
1. `get_all_prices_at_mandi(mandi, days?)` — All commodity prices at a mandi

## Key Design Decisions

1. **Nova Pro over Claude**: Claude requires EULA form on Bedrock; Nova Pro is AWS-native and works immediately. Better fit for AWS hackathon.

2. **functionSchema over OpenAPI**: Bedrock Agent rejected OpenAPI spec validation. `functionSchema` with inline function definitions is simpler and works.

3. **Static export (SSG)**: `output: "export"` in Next.js for S3 hosting — no server needed, zero compute cost.

4. **Trace fallback chain**: Bedrock Agent sometimes sends empty chunk bytes but includes the answer in traces. Three-level fallback: chunk → trace answer tag → retry without traces.

5. **TSTALIASID (DRAFT)**: Agent alias `BM6JROSWME` pointed to version 1 (outdated). TSTALIASID always uses DRAFT with latest prompt. AWS CLI v1 doesn't support `create-agent-version`.

6. **GPS injection**: User's GPS coordinates are injected into the agent's input message as context, not as a separate API parameter. This lets the agent use them for any tool that needs location.

7. **DynamoDB single-table design**: One table with composite keys enables all query patterns via PK/SK + GSIs. PAY_PER_REQUEST billing for cost efficiency.
