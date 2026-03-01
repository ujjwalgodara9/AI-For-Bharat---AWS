# MandiMitra — Architecture & Code Flow

## System Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │           USER (Farmer's Phone)             │
                    │    PWA / WhatsApp-style Chat UI              │
                    │    Voice Input (Hindi/English)               │
                    └──────────────────┬──────────────────────────┘
                                       │ HTTPS + GPS coords
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │      CloudFront (HTTPS CDN)                 │
                    │      d2mtfau3fvs243.cloudfront.net          │
                    │      SSL/TLS → enables Voice + GPS APIs     │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │         S3 Static Website Hosting           │
                    │     Next.js 14 + Tailwind CSS (SSG)         │
                    │   mandimitra-frontend-471112620976           │
                    │   PWA (installable) + Service Worker         │
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
                    │    │ 2. Select action group       │           │
                    │    │ 3. Call tool function(s)      │           │
                    │    │ 4. Process tool output        │           │
                    │    │ 5. Generate Hindi response    │           │
                    │    └─────────────┬──────────────┘           │
                    │                  │                          │
                    │    ┌─────────────┼──────────────┐           │
                    │    │             ▼              │           │
                    │    │  mandimitra-price-query    │           │
                    │    │  (Action Group Lambda)     │           │
                    │    │  4 Action Groups:          │           │
                    │    │  • PriceIntelligenceTools  │           │
                    │    │  • MandiTools              │           │
                    │    │  • BrowseTools             │           │
                    │    │  • WeatherTools            │           │
                    │    │  13 functions total         │           │
                    │    └─────────────┬──────────────┘           │
                    │                  │                          │
                    │         ┌────────┴────────┐                │
                    │         ▼                 ▼                │
                    │    DynamoDB          Open-Meteo API        │
                    │    MandiMitraPrices  (Weather forecast)    │
                    │    4,467 records     5-day agri advisory   │
                    └─────────────────────────────────────────────┘
```

## Data Flow — Chat Message

```
User types: "wheat ka bhav Karnal mein"
     │
     ▼
Frontend (page.tsx)
  ├── Gets location from LocationPicker: {city: "Karnal", state: "Haryana"}
  ├── POST /api/chat {message, language: "hi", latitude, longitude, session_id}
     │
     ▼
API Gateway → mandimitra-chat Lambda (handler.py)
  ├── Parses body: message, language, lat, lon
  ├── Builds augmented message:
  │   "[Respond in Hindi] [User GPS: lat=29.68, lon=76.99] wheat ka bhav Karnal mein"
  ├── Calls bedrock_agent_runtime.invoke_agent()
     │
     ▼
Bedrock Agent (Nova Pro model)
  ├── Pre-processing: classifies intent → PRICE_CHECK
  ├── Reasoning: "Need wheat prices in Haryana near Karnal"
  ├── Tool call: PriceIntelligenceTools/query_mandi_prices
  │   params: {commodity: "wheat", state: "Haryana", mandi: "Karnal"}
     │
     ▼
mandimitra-price-query Lambda (handle_agent_action)
  ├── Calls query_prices("wheat", "Haryana", "Karnal")
  │   → Tries exact match on mandi_name "KARNAL"
  │   → Tries "KARNAL APMC" suffix
  │   → Falls back to district scan (finds "Indri APMC" in Karnal district)
  ├── Calls get_price_trend("wheat", "Haryana")
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
  ├── Message text with line breaks
  ├── Price trend mini-chart (SVG) if price data detected
  ├── WhatsApp share + Copy buttons
  └── Agent trace expandable in UI
```

## File Structure & Purpose

```
hackathon/
├── frontend/                          # Next.js 14 + Tailwind CSS
│   ├── app/
│   │   ├── page.tsx                   # Main chat page
│   │   │   - State: messages, language, sessionId, userLocation
│   │   │   - LocationPicker modal for state/city selection
│   │   │   - sendMessage() → POST /api/chat with location
│   │   │   - Fallback demo mode when API_BASE not set
│   │   │
│   │   ├── components/
│   │   │   ├── ChatHeader.tsx         # App header with language toggle + location label
│   │   │   ├── ChatBubble.tsx         # Message bubbles + price chart + WhatsApp share + agent trace
│   │   │   ├── ChatInput.tsx          # Text input + voice mic (Web Speech API) + Hindi prompt
│   │   │   ├── PriceChart.tsx         # SVG price comparison chart (auto-extracted from responses)
│   │   │   ├── QuickActions.tsx       # Quick action buttons (price, mandi, sell, weather)
│   │   │   ├── LocationPicker.tsx     # State/city picker + GPS detection modal
│   │   │   ├── TypingIndicator.tsx    # Animated thinking dots
│   │   │   └── WelcomeScreen.tsx      # Welcome screen with feature cards + browse chips
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client, interfaces (ChatMessage, PriceData, TrendData)
│   │   │   └── voice.ts              # Web Speech API wrapper for Hindi/English
│   │   │
│   │   ├── layout.tsx                 # Root layout (PWA manifest, service worker registration)
│   │   └── globals.css                # Tailwind + custom animations
│   │
│   ├── public/
│   │   ├── manifest.json              # PWA manifest (installable app)
│   │   ├── sw.js                      # Service worker (offline caching)
│   │   ├── icon-192.png               # PWA icon 192x192
│   │   └── icon-512.png               # PWA icon 512x512
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
│   │   │       - 13 functions across 4 action groups
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
│   │       │   - query_prices(): PK query + APMC suffix fallback + district scan
│   │       │   - query_mandi_prices(): GSI-1 query + district fallback + partial match
│   │       │   - get_nearby_mandis(): Haversine distance from 55+ mandi coordinates
│   │       │   - get_price_trend(): direction, change%, volatility, data_points
│   │       │   - get_msp(): case-insensitive MSP lookup (20 commodities)
│   │       │   - get_sell_recommendation_data(): comprehensive sell advisory data
│   │       │   - list_available_commodities/mandis/states(): browse data
│   │       │   - calculate_net_realization(): price minus transport cost
│   │       │   - haversine_distance(): GPS distance in km
│   │       │
│   │       ├── weather_utils.py       # Weather advisory (Open-Meteo API)
│   │       │   - get_weather_advisory(): 5-day forecast + agri recommendations
│   │       │   - generate_agri_advisory(): rain/heat/storm alerts, sell impact
│   │       │
│   │       └── constants.py           # Static configuration
│   │           - MANDI_COORDINATES: 55+ major mandis with GPS
│   │           - MSP_RATES: 20 commodities for 2025-26
│   │           - PERISHABILITY_INDEX: 1-10 scale per commodity
│   │           - STORAGE_COST_PER_DAY: ₹/qtl/day
│   │           - TRANSPORT_COST_PER_QTL_PER_KM: ₹0.8
│   │
│   ├── agent_configs/
│   │   └── orchestrator_prompt.txt    # Bedrock Agent system prompt
│   │       - Intent classification (8 intents including WEATHER)
│   │       - Language rules (Hindi/English auto-detect)
│   │       - Location handling (GPS injection + district search)
│   │       - Response format templates (price, sell, weather, browse)
│   │       - Guardrails
│   │
│   └── scripts/
│       ├── fetch_all_data.py          # Aggressive state-by-state data fetcher
│       ├── fetch_more_data.py         # Targeted commodity/state data fetcher
│       ├── fetch_data_local.py        # Initial data fetcher
│       ├── load_all_data.py           # Batch load items into DynamoDB
│       └── load_dynamodb.py           # Original batch loader
│
├── data/                              # Fetched price data (not committed)
│   ├── dynamodb_items_all.json        # 2,026 records (first batch)
│   ├── dynamodb_items_new.json        # 3,572 records (second batch)
│   └── raw_all_states.json            # 4,110 raw API records
│
├── ARCHITECTURE.md                    # This file
├── DATA_INVENTORY.md                  # Data coverage details
├── FLOWS.md                           # 13 detailed user flow walkthroughs
├── PLAN.md                            # 5-day execution plan
├── design.md                          # Detailed design document
├── requirements.md                    # Requirements specification
└── README.md                          # Project overview
```

## DynamoDB Schema

**Table: MandiMitraPrices** (4,467 items)

| Attribute | Type | Description |
|-----------|------|-------------|
| PK | String (Partition Key) | `{COMMODITY}#{STATE}` e.g., `WHEAT#HARYANA` |
| SK | String (Sort Key) | `{YYYY-MM-DD}#{MANDI_NAME}` e.g., `2026-02-28#INDRI APMC` |
| commodity | String | Original commodity name (e.g., "Wheat") |
| state | String | Original state name (e.g., "Haryana") |
| district | String | District name (e.g., "Karnal") |
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

## Search & Fallback Strategy

When a user queries a location (e.g., "Karnal"):
1. **Exact mandi name** → `KARNAL` in MANDI-INDEX
2. **APMC suffix** → `KARNAL APMC`, `KARNAL(GRAIN)`, `KARNAL(F&V)`
3. **District scan** → Full table scan with `Attr("district").eq("Karnal")` — finds mandis IN that district (e.g., "Indri APMC" in Karnal district)
4. **Partial match** → `Attr("mandi_name").contains("KARNAL")`

## AWS Resources

| Resource | ID/Name | Purpose |
|----------|---------|---------|
| DynamoDB | MandiMitraPrices (4,467 items) | Price time-series data |
| CloudFront | E1FOPZ17Q7P6CF (d2mtfau3fvs243.cloudfront.net) | HTTPS CDN — enables Voice + GPS |
| S3 (frontend) | mandimitra-frontend-471112620976 | Static website + PWA |
| S3 (deploy) | mandimitra-deployment-471112620976 | Lambda deployment packages |
| Lambda | mandimitra-chat | Chat endpoint (invokes Bedrock Agent) |
| Lambda | mandimitra-price-query | Price queries + Action Groups + Weather |
| Lambda | mandimitra-data-ingestion | Data fetcher from data.gov.in |
| API Gateway | skwsw8qk22 | REST API with CORS |
| Bedrock Agent | GDSWGCDJIX | Multi-agent orchestrator (Nova Pro) |
| Agent Alias | TSTALIASID | Points to DRAFT version |
| IAM | MandiMitraLambdaRole | Lambda execution role |
| IAM | MandiMitraBedrockAgentRole | Bedrock Agent role |

## Agent Action Groups

**PriceIntelligenceTools** (ID: REC9WFZCNW, 5 functions):
1. `query_mandi_prices(commodity, state, mandi?, days?)` — Price lookup with fuzzy matching
2. `get_nearby_mandis(latitude, longitude, radius_km, commodity?)` — GPS-based mandi finder
3. `get_price_trend(commodity, state, mandi?, days?)` — Trend analysis
4. `get_msp(commodity)` — MSP lookup
5. `get_sell_recommendation(commodity, state, latitude, longitude, quantity_qtl)` — Sell/hold data

**MandiTools** (2 functions):
1. `get_all_prices_at_mandi(mandi, days?)` — All commodity prices at a mandi
2. `get_mandi_profile(mandi, days?)` — Comprehensive mandi profile with Agmarknet details

**BrowseTools** (ID: KYYMTPXMWY, 3 functions):
1. `list_available_commodities(state?)` — List commodities in database
2. `list_available_mandis(state?)` — List mandis with district info
3. `list_available_states()` — List all states with data

**WeatherTools** (ID: MIYZDHRQ9H, 1 function):
1. `get_weather_advisory(location, latitude?, longitude?)` — 5-day weather + agri advisory

## Frontend Features

| Feature | Implementation |
|---------|---------------|
| Chat UI | WhatsApp-style bubbles with agent trace panel |
| Voice Input | Web Speech API (`hi-IN`, `en-IN`) with error handling + user feedback |
| Location Picker | Manual state/city (13 states, 65+ cities) + GPS auto-detect + permission handling |
| Commodity Picker | Crop selection popup on Quick Actions + Welcome Screen (no hardcoded crops) |
| Quick Actions | Always-visible action bar with 5 buttons (Price, Best Mandi, Sell/Hold, Weather, Mandi Info) |
| Price Chart | Auto-extracted SVG mini-chart from bot responses |
| WhatsApp Share | `wa.me/?text=` with message content + branding |
| Copy Button | `navigator.clipboard.writeText()` |
| PWA | manifest.json + service worker for offline + installable |
| Language Toggle | Hindi/English switch in header |
| Demo Mode | Simulated responses when `API_BASE` not set |

## Key Design Decisions

1. **Nova Pro over Claude**: Claude requires EULA on Bedrock; Nova Pro is AWS-native. Better fit for AWS hackathon.

2. **functionSchema over OpenAPI**: Bedrock Agent rejected OpenAPI spec. `functionSchema` with inline function definitions works.

3. **Static export (SSG)**: `output: "export"` in Next.js for S3 hosting — no server, zero compute cost.

4. **Trace fallback chain**: Bedrock Agent sometimes sends empty chunks but includes answer in traces. Three-level fallback: chunk → trace answer → retry.

5. **TSTALIASID (DRAFT)**: Always uses latest prompt. No need to create versions.

6. **GPS injection**: User's GPS injected into agent message as context, not a separate parameter.

7. **DynamoDB single-table design**: Composite keys + GSIs enable all query patterns. PAY_PER_REQUEST billing.

8. **District-level fallback search**: Users often name cities/districts, not APMC market names. Full-table scan fallback finds mandis by district.

9. **Open-Meteo for weather**: Free API, no key needed, global coverage. Provides WMO weather codes, daily temperature, precipitation, wind.

10. **PWA for rural deployment**: Installable app without Play Store. Service worker caches for offline use on low-connectivity rural networks.

11. **No hardcoded crops**: All crop-specific buttons use a picker popup — user always selects their commodity.

12. **Shelf life in sell advisory**: Sell/hold recommendations include commodity shelf life, recommended hold days, and storage cost estimates.

13. **Data freshness awareness**: System tracks whether data is from today, yesterday, or older. Agent explicitly mentions date context in responses. Agmarknet mandis finalize data by 5:00 PM IST per DMI guidelines. Ingestion runs at 9:30 PM IST.

14. **Data validation at ingestion**: Records with unrealistic prices (<₹1 or >₹5L), modal outside min-max range, or future dates are rejected.

15. **GPS permission graceful degradation**: If browser GPS is denied, the picker auto-hides the GPS option and prompts manual state/city selection.

16. **CloudFront for HTTPS**: S3 static hosting is HTTP-only. CloudFront distribution provides HTTPS (free tier: 1TB/month), which is required for Web Speech API (voice input) and Geolocation API (GPS). HTTP→HTTPS redirect enabled.
