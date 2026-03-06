# MandiMitra — System Architecture & Technical Documentation

> **Version:** 2.0 (Multi-Agent) | **Last Updated:** 6 March 2026
> **Live URL:** https://d2mtfau3fvs243.cloudfront.net
> **Model:** Claude Sonnet 4 (`us.anthropic.claude-sonnet-4-20250514-v1:0`)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Multi-Agent Architecture](#3-multi-agent-architecture)
4. [AWS Services Map](#4-aws-services-map)
5. [Frontend Architecture](#5-frontend-architecture)
6. [Backend Architecture](#6-backend-architecture)
7. [Data Pipeline](#7-data-pipeline)
8. [Database Design](#8-database-design)
9. [API Design](#9-api-design)
10. [Agent Prompts & Intelligence](#10-agent-prompts--intelligence)
11. [Observability & Monitoring](#11-observability--monitoring)
12. [Security & Guardrails](#12-security--guardrails)
13. [Deployment Architecture](#13-deployment-architecture)
14. [User Flows](#14-user-flows)
15. [File Structure](#15-file-structure)
16. [Resource IDs & Configuration](#16-resource-ids--configuration)

---

## 1. System Overview

MandiMitra is an AI-powered agricultural market intelligence platform that helps Indian farmers make better selling decisions. It provides real-time mandi (market) prices, sell/hold recommendations, negotiation briefs, and weather advisories — all through a conversational Hindi/English interface.

### Key Numbers

| Metric | Value |
|--------|-------|
| Commodities tracked | 20 (covers 80%+ farmer queries) |
| States covered | 14 major agricultural states |
| DynamoDB records | 8,874+ price entries |
| Mandi GPS coordinates | 60+ major mandis |
| Foundation model | Claude Sonnet 4 (Anthropic) |
| Bedrock Agents | 5 (1 Supervisor + 4 Sub-agents) |
| Lambda functions | 3 (Chat, Price Query, Data Ingestion) |
| Average response time | ~15-21 seconds |
| Languages supported | Hindi, Hinglish, English |
| Target users | 150M+ small farming households |

---

## 2. High-Level Architecture

```
                            ┌─────────────────────────────────┐
                            │         Indian Farmer           │
                            │   (Hindi / English / Voice)     │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌───────────────────────────────┐
                            │   Amazon CloudFront (HTTPS)   │
                            │   d2mtfau3fvs243.cloudfront   │
                            │   .net                        │
                            │   Distribution: E1FOPZ17Q7P6CF│
                            └───────────────┬───────────────┘
                                            │
                         ┌──────────────────┼──────────────────┐
                         │                  │                  │
                         ▼                  ▼                  │
              ┌──────────────────┐  ┌──────────────────┐       │
              │   Amazon S3      │  │  API Gateway     │       │
              │   Static Website │  │  (MandiMitraAPI)  │       │
              │   Next.js 14 PWA │  │  skwsw8qk22      │       │
              │   mandimitra-    │  └────────┬─────────┘       │
              │   frontend-      │           │                 │
              │   471112620976   │     ┌─────┴──────┐          │
              └──────────────────┘     │            │          │
                                       ▼            ▼          │
                              ┌────────────┐ ┌────────────┐    │
                              │ mandimitra │ │ mandimitra │    │
                              │ -chat      │ │ -price-    │    │
                              │ Lambda     │ │ query      │    │
                              │            │ │ Lambda     │    │
                              └─────┬──────┘ └─────┬──────┘    │
                                    │              │           │
                                    ▼              │           │
                      ┌──────────────────────┐     │           │
                      │  Amazon Bedrock      │     │           │
                      │  Multi-Agent System  │     │           │
                      │  (SUPERVISOR Mode)   │─────┘           │
                      │                      │                 │
                      │  Claude Sonnet 4     │                 │
                      └──────────┬───────────┘                 │
                                 │                             │
                    ┌────────────┼─────────────┐               │
                    ▼            ▼             ▼               │
            ┌────────────┐ ┌──────────┐ ┌──────────┐          │
            │  DynamoDB  │ │Open-Meteo│ │Nominatim │          │
            │  Mandi     │ │Weather   │ │Geocoding │          │
            │  Prices    │ │API (Free)│ │API (Free)│          │
            └────────────┘ └──────────┘ └──────────┘          │
                                                               │
                              ┌─────────────────┐             │
                              │ EventBridge      │             │
                              │ (Daily 9:30PM)   │             │
                              └────────┬────────┘             │
                                       ▼                       │
                              ┌─────────────────┐             │
                              │ mandimitra-data- │             │
                              │ ingestion Lambda │             │
                              └────────┬────────┘             │
                                       ▼                       │
                              ┌─────────────────┐             │
                              │ data.gov.in     │             │
                              │ Agmarknet API   │             │
                              └─────────────────┘
```

### Request Flow (End-to-End)

```
1. User types "गेहूं का भाव बताओ इंदौर" in the chat UI
2. Frontend (Next.js) → POST /api/chat with {message, session_id, language, lat, lon, state, city}
3. API Gateway → mandimitra-chat Lambda
4. Chat Lambda:
   a. Detects language style (Hindi/Hinglish/English)
   b. Augments message with location context + language instruction
   c. Invokes Bedrock Supervisor Agent (GDSWGCDJIX)
5. Supervisor Agent:
   a. Classifies intent → PRICE_CHECK
   b. Routes to PriceIntelligenceAgent (CAEJ90IYS6)
6. PriceIntelligenceAgent:
   a. Calls query_mandi_prices(commodity="Wheat", state="MADHYA_PRADESH", mandi="INDORE")
   b. Bedrock invokes mandimitra-price-query Lambda
7. Price Query Lambda:
   a. Queries DynamoDB (PK="WHEAT#MADHYA_PRADESH", SK begins_with "2026-03")
   b. Returns price data with trend, MSP, nearby mandis
8. Response flows back: Lambda → Agent → Supervisor → Chat Lambda → API Gateway → Frontend
9. Frontend renders Hindi response with prices, expandable agent trace, TTS button
```

---

## 3. Multi-Agent Architecture

MandiMitra uses Amazon Bedrock's **SUPERVISOR_ROUTER** collaboration mode with 5 agents:

```
                    ┌─────────────────────────────────────────┐
                    │     MandiMitra Supervisor Agent          │
                    │     ID: GDSWGCDJIX                      │
                    │     Model: Claude Sonnet 4              │
                    │     Mode: SUPERVISOR_ROUTER             │
                    │     Guardrail: snlfs5xjb61l             │
                    │                                         │
                    │  Direct Action Groups:                  │
                    │  ├── BrowseTools (list commodities,     │
                    │  │    mandis, states)                   │
                    │  ├── MandiTools (mandi profile,         │
                    │  │    all prices at mandi)              │
                    │  ├── PriceIntelligenceTools (prices,    │
                    │  │    nearby, sell rec, transport)      │
                    │  └── WeatherTools (weather advisory)    │
                    └──────────┬──────────────────────────────┘
                               │
              ┌────────────────┼────────────────┬───────────────┐
              │                │                │               │
              ▼                ▼                ▼               ▼
   ┌──────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │ PriceIntelligence│ │ SellAdvisory │ │ Negotiation  │ │   Weather    │
   │ Agent            │ │ Agent        │ │ Agent        │ │   Agent      │
   │ ID: CAEJ90IYS6   │ │ ID: CCYSN80MGN│ │ ID: UZRXDX75NR│ │ ID: XE43VNHO3T│
   │                  │ │              │ │              │ │              │
   │ Tools:           │ │ Tools:       │ │ Tools:       │ │ Tools:       │
   │ - query_mandi_   │ │ - get_sell_  │ │ - query_mandi│ │ - get_weather│
   │   prices         │ │   recommend  │ │   _prices    │ │   _advisory  │
   │ - get_nearby_    │ │   ation      │ │ - get_msp    │ │              │
   │   mandis         │ │ - get_price_ │ │ - get_price_ │ │              │
   │ - get_price_     │ │   trend      │ │   trend      │ │              │
   │   trend          │ │ - get_weather│ │ - get_nearby │ │              │
   │ - get_msp        │ │   _advisory  │ │   _mandis    │ │              │
   │ - calculate_     │ │              │ │              │ │              │
   │   transport_cost │ │              │ │              │ │              │
   └──────────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │                    │                │               │
         └────────────────────┴────────────────┴───────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  mandimitra-price-query│
                        │  Lambda (shared)       │
                        │  13 tool functions     │
                        └───────────────────────┘
```

### Intent Classification & Routing

| User Intent | Example Query | Routed To | Tools Used |
|-------------|--------------|-----------|------------|
| PRICE_CHECK | "गेहूं का भाव MP में?" | PriceIntelligence | query_mandi_prices, get_msp |
| MANDI_COMPARE | "कहाँ बेचूं? 20 qtl सोयाबीन" | PriceIntelligence | get_nearby_mandis, calculate_transport_cost |
| SELL_ADVISORY | "अभी बेचूं या रुकूं?" | SellAdvisory | get_sell_recommendation, get_price_trend, get_weather_advisory |
| NEGOTIATION | "Price brief दो गेहूं का" | Negotiation | query_mandi_prices, get_msp, get_price_trend, get_nearby_mandis |
| WEATHER | "मौसम कैसा रहेगा?" | Weather | get_weather_advisory |
| BROWSE_DATA | "कौन-कौन सी फसलें हैं?" | Supervisor (direct) | list_available_commodities, list_available_mandis |
| MANDI_PROFILE | "इंदौर मंडी की जानकारी" | Supervisor (direct) | get_mandi_profile, get_all_prices_at_mandi |

### Agent Collaboration Flow

```
User: "50 क्विंटल सोयाबीन बेचना चाहिए या रुकूं? इंदौर"

Supervisor Agent
  │
  ├─── Intent: SELL_ADVISORY
  │
  ├─── Routes to SellAdvisoryAgent
  │     │
  │     ├── Calls: get_sell_recommendation(commodity="Soyabean", state="MADHYA_PRADESH",
  │     │          mandi="INDORE", quantity=50, lat=22.72, lon=75.86)
  │     │
  │     │   └── Lambda internally:
  │     │       ├── query_prices() → Current prices at Indore
  │     │       ├── get_price_trend() → 30-day trend (↑ RISING)
  │     │       ├── get_msp() → ₹4,892/qtl
  │     │       ├── get_nearby_mandis() → 5 mandis within 50km
  │     │       ├── get_weather_advisory() → Clear weather next 5 days
  │     │       ├── Check perishability → Index 2 (low)
  │     │       ├── Check crop season → Post-harvest season
  │     │       └── Calculate net realization per mandi
  │     │
  │     ├── SellAdvisoryAgent reasons:
  │     │   "Price above MSP, trend rising, weather clear,
  │     │    low perishability → HOLD recommendation (70% confidence)"
  │     │
  │     └── Returns structured recommendation
  │
  └─── Supervisor formats final Hindi response with:
        - HOLD recommendation with reasoning
        - Current price vs MSP comparison
        - 30-day price trend
        - Weather outlook
        - Storage tips in Hindi
```

---

## 4. AWS Services Map

### Services in Production

| Service | Resource | Purpose | Config |
|---------|----------|---------|--------|
| **Bedrock Agents** | 5 agents (SUPERVISOR mode) | Multi-agent AI orchestration | Claude Sonnet 4 |
| **Bedrock Guardrails** | `snlfs5xjb61l` | Content safety filtering | VIOLENCE/HATE/SEXUAL: HIGH |
| **Lambda** | `mandimitra-chat` | Chat endpoint, Bedrock invocation | Python 3.12, 512MB, 29s |
| **Lambda** | `mandimitra-price-query` | Price queries + Action Groups | Python 3.12, 256MB, 30s |
| **Lambda** | `mandimitra-data-ingestion` | Daily Agmarknet data fetch | Python 3.12, 512MB, 900s |
| **DynamoDB** | `MandiMitraPrices` | Price time-series storage | PAY_PER_REQUEST, 2 GSIs |
| **API Gateway** | `skwsw8qk22` (MandiMitraAPI) | REST API | REGIONAL, TLS 1.0 |
| **CloudFront** | `E1FOPZ17Q7P6CF` | CDN + HTTPS | d2mtfau3fvs243.cloudfront.net |
| **S3** | `mandimitra-frontend-471112620976` | Frontend static hosting | Website-enabled |
| **S3** | `mandimitra-data` | Audit logs from ingestion | Private |
| **EventBridge** | `mandimitra-daily-ingestion` | Daily price ingestion trigger | cron(0 16 * * ? *) = 9:30PM IST |
| **CloudWatch** | 7 alarms | Lambda errors, throttles, DynamoDB | All OK |
| **IAM** | `MandiMitraBedrockAgentRole` | Bedrock agent execution role | AmazonBedrockFullAccess |

### External APIs (No AWS Cost)

| API | Purpose | Auth | Rate Limit |
|-----|---------|------|-----------|
| data.gov.in Agmarknet | Commodity price data | API Key | ~100 req/min |
| Open-Meteo | Weather forecasts | None (free) | 10,000 req/day |
| Nominatim (OpenStreetMap) | Reverse geocoding (GPS → city) | None (free) | 1 req/sec |

---

## 5. Frontend Architecture

### Technology Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 14 | React framework with static export |
| React | 18 | UI library |
| TypeScript | 5 | Type safety |
| Tailwind CSS | 3 | Utility-first styling |
| Web Speech API | Browser | Voice input (STT) + Text-to-Speech (TTS) |

### Build & Deployment

```
Next.js Config (next.config.mjs):
  output: "export"          → Static HTML/CSS/JS (no server)
  trailingSlash: true       → S3 compatible URLs
  images.unoptimized: true  → No Image Optimization API needed

Build:  NEXT_PUBLIC_API_URL=https://...execute-api.../prod/api npm run build
Deploy: aws s3 sync out/ s3://mandimitra-frontend-471112620976 --delete
Cache:  aws cloudfront create-invalidation --distribution-id E1FOPZ17Q7P6CF --paths "/*"
```

### Component Architecture

```
layout.tsx (Root — metadata, PWA manifest, service worker)
  │
  └── page.tsx (Main Chat Application)
        │
        ├── State Management:
        │   ├── messages[]           — Chat history
        │   ├── isLoading            — API call in progress
        │   ├── language (hi/en)     — UI language toggle
        │   ├── sessionId (UUID)     — Bedrock session
        │   ├── locationState/City   — User's selected location
        │   └── lat/lon              — GPS coordinates
        │
        ├── ChatHeader.tsx
        │   ├── MandiMitra logo + title
        │   ├── Language toggle (Hindi <> English)
        │   └── Live status indicator
        │
        ├── WelcomeScreen.tsx (shown when no messages)
        │   ├── 4 Feature cards (Live Prices, Best Mandi, Sell/Hold, Mandi Info)
        │   ├── Crop picker popup (dynamic from API)
        │   ├── Quick action chips
        │   ├── Location display with GPS status
        │   └── "Powered by Amazon Bedrock Agents + Claude Sonnet 4"
        │
        ├── ChatBubble.tsx (per message)
        │   ├── User bubble (right-aligned, saffron)
        │   ├── Bot bubble (left-aligned, white)
        │   ├── TTS button (read aloud)
        │   ├── Copy to clipboard
        │   ├── WhatsApp share button
        │   ├── PriceChart.tsx (SVG mini chart if price data detected)
        │   └── Expandable Agent Trace panel
        │       ├── preprocessing steps
        │       ├── reasoning steps
        │       ├── tool_call invocations
        │       ├── observation results
        │       └── model_output final
        │
        ├── ChatInput.tsx
        │   ├── Auto-resizing textarea
        │   ├── Voice input button (Web Speech API)
        │   └── Send button
        │
        ├── LocationPicker.tsx (modal)
        │   ├── State dropdown (14 states)
        │   ├── City dropdown (filtered by state)
        │   ├── GPS auto-detect button
        │   │   └── Nominatim reverse geocode (lat/lon → state/city)
        │   └── Manual coordinate input
        │
        └── TypingIndicator.tsx (animated dots during loading)
```

### Voice & Speech

```
lib/voice.ts:
  ├── startListening(language)
  │   ├── Hindi: recognition.lang = "hi-IN"
  │   └── English: recognition.lang = "en-IN"
  │
  └── speak(text, language)
      ├── Hindi voices: "Lekha" (preferred), any "hi" voice
      └── English voices: "Rishi", "Veena", any "en-IN" voice
```

### Demo Mode

When `NEXT_PUBLIC_API_URL` is empty/unset, the frontend runs in **demo mode** using `simulateResponse()` in `page.tsx`. This returns realistic mock data for all flows without any backend.

---

## 6. Backend Architecture

### Lambda: mandimitra-chat (Chat Handler)

```
Entry: handler(event, context)
  │
  ├── Parse request body (message, session_id, language, lat, lon, state, city)
  │
  ├── Language Detection:
  │   ├── Check for Devanagari characters → Hindi
  │   ├── Check for Hindi transliteration patterns → Hinglish
  │   └── Default → English
  │
  ├── Message Augmentation:
  │   ├── Prepend: "[RESPOND IN {language}. Use {style}.]"
  │   ├── Append: "[User's selected location: state={state}, city={city}, GPS=({lat},{lon})]"
  │   └── Priority: state/city from frontend > GPS > nothing
  │
  ├── invoke_agent(message, session_id, ...)
  │   ├── bedrock_agent_runtime.invoke_agent(
  │   │     agentId="GDSWGCDJIX",
  │   │     agentAliasId="TSTALIASID",
  │   │     sessionId=session_id,
  │   │     inputText=augmented_message,
  │   │     enableTrace=True
  │   │   )
  │   ├── Stream response chunks
  │   ├── Extract agent traces (preprocessing, reasoning, tool_call, observation, model_output)
  │   └── Fallback: extract <answer> tags from trace if response empty
  │
  ├── clean_agent_response(response)
  │   ├── Strip "Bot:" prefix
  │   ├── Remove leaked XML tags (<response>, <answer>, etc.)
  │   └── Clean sub-agent artifacts
  │
  ├── LangFuse Tracing (optional):
  │   ├── trace.generation(model="claude-sonnet-4", input=message, output=response)
  │   └── Graceful degradation if langfuse not available
  │
  └── Return JSON:
      {
        "response": "गेहूं का भाव इंदौर मंडी में...",
        "agent_trace": [...trace steps...],
        "latency_ms": 21400,
        "language": "hi"
      }
```

### Lambda: mandimitra-price-query (Price Query + Action Groups)

Dual-purpose Lambda handling both direct API calls and Bedrock Agent Action Group invocations.

```
Entry: handler(event, context)
  │
  ├── Route Detection:
  │   ├── event.has("actionGroup") → Bedrock Agent Action Group call
  │   └── event.has("httpMethod") → API Gateway direct call
  │
  ├── 13 Tool Functions:
  │
  │   ┌── Price Queries ──────────────────────────────────────────┐
  │   │ query_mandi_prices(commodity, state, mandi?, days?)       │
  │   │   → DynamoDB PK query + fallback strategies               │
  │   │                                                           │
  │   │ get_all_prices_at_mandi(mandi, days?)                     │
  │   │   → MANDI-INDEX GSI query                                 │
  │   │                                                           │
  │   │ get_nearby_mandis(lat, lon, radius_km, commodity?)        │
  │   │   → Haversine distance from MANDI_COORDINATES dict        │
  │   │   → Fetches prices for each nearby mandi                  │
  │   └───────────────────────────────────────────────────────────┘
  │
  │   ┌── Analysis ───────────────────────────────────────────────┐
  │   │ get_price_trend(commodity, state, mandi, days?)            │
  │   │   → 7/30-day moving average, volatility, direction        │
  │   │                                                           │
  │   │ get_msp(commodity)                                         │
  │   │   → MSP_RATES dict lookup (2025-26 season)                │
  │   │                                                           │
  │   │ calculate_transport_cost(origin_lat, origin_lon,           │
  │   │                          dest_lat, dest_lon, quantity)     │
  │   │   → Haversine x Rs.0.80/qtl/km                            │
  │   │                                                           │
  │   │ get_sell_recommendation(commodity, state, mandi, quantity, │
  │   │                         lat, lon)                          │
  │   │   → 14-step comprehensive analysis                        │
  │   └───────────────────────────────────────────────────────────┘
  │
  │   ┌── Weather ────────────────────────────────────────────────┐
  │   │ get_weather_advisory(lat, lon, location_name?)             │
  │   │   → Open-Meteo 5-day forecast + agricultural advisory     │
  │   └───────────────────────────────────────────────────────────┘
  │
  │   ┌── Browse / Discovery ─────────────────────────────────────┐
  │   │ list_available_commodities(state?)                         │
  │   │ list_available_mandis(state?)                              │
  │   │ list_available_states()                                    │
  │   │ get_mandi_profile(mandi, days?)                            │
  │   └───────────────────────────────────────────────────────────┘
  │
  └── Response Format:
      Bedrock: {"actionGroup": "...", "function": "...", "functionResponse": {...}}
      API GW:  {"statusCode": 200, "body": JSON}
```

### Lambda: mandimitra-data-ingestion (Data Pipeline)

```
Entry: handler(event, context)
  │
  ├── Trigger: EventBridge schedule (daily 9:30 PM IST)
  │           OR manual invoke with {"days_back": N}
  │
  ├── For each commodity (20) x state (14):
  │   ├── GET https://api.data.gov.in/resource/{RESOURCE_ID}
  │   │     ?api-key={key}&format=json
  │   │     &filters[commodity]={commodity}
  │   │     &filters[state]={state}
  │   │     &limit=100
  │   │
  │   ├── Data Validation:
  │   │   ├── modal_price in [min_price, max_price] (5% tolerance)
  │   │   ├── Price range: Rs.1 - Rs.5,00,000
  │   │   ├── No future dates
  │   │   └── Required fields present
  │   │
  │   ├── Transform to DynamoDB format:
  │   │   ├── PK: "{COMMODITY}#{STATE}" (e.g., "WHEAT#MADHYA_PRADESH")
  │   │   ├── SK: "{date}#{mandi}#{variety}"
  │   │   └── Attributes: min_price, max_price, modal_price, etc.
  │   │
  │   ├── Deduplication: Track PK+SK in seen_keys set
  │   │
  │   └── Rate limiting: 0.5s delay + exponential backoff on 429
  │
  ├── Batch write to DynamoDB (25 items per batch)
  │
  ├── Audit log to S3 (mandimitra-data bucket)
  │
  └── Return statistics: {records_fetched, records_written, errors}
```

### Shared Modules

```
backend/lambdas/shared/
  │
  ├── constants.py
  │   ├── TRACKED_COMMODITIES (20): Wheat, Soyabean, Onion, Tomato, Potato, ...
  │   ├── TRACKED_STATES (14): MP, Rajasthan, Maharashtra, UP, Gujarat, ...
  │   ├── MSP_RATES (2025-26): {Wheat: 2275, Soyabean: 4892, Rice: 2300, ...}
  │   ├── PERISHABILITY_INDEX: {Tomato: 9, Onion: 7, Wheat: 2, ...} (1-10 scale)
  │   ├── CROP_SEASONS: {Wheat: {harvest: [3,4], type: "Rabi"}, ...}
  │   ├── MANDI_COORDINATES: {INDORE: (22.72, 75.86), DELHI: (28.65, 77.23), ...}
  │   ├── COMMODITY_TRANSLATIONS: {Wheat: "गेहूं", Soyabean: "सोयाबीन", ...}
  │   ├── STORAGE_TIPS: {Wheat: {en: "...", hi: "..."}, ...}
  │   └── WEATHER_STORAGE_IMPACT: Multiplicative shelf-life factors
  │
  ├── dynamodb_utils.py
  │   ├── query_prices() — PK query with date range + fallback strategies
  │   ├── query_mandi_prices() — MANDI-INDEX GSI
  │   ├── get_price_trend() — Linear regression, MA, volatility
  │   ├── get_nearby_mandis() — Haversine distance sorting
  │   ├── get_sell_recommendation_data() — 14-step comprehensive analysis
  │   ├── get_mandi_profile() — Mandi overview with all commodities
  │   ├── list_available_*() — Discovery queries
  │   └── haversine_distance() — GPS distance calculation
  │
  ├── weather_utils.py
  │   ├── get_weather_advisory() — Open-Meteo 5-day forecast
  │   ├── WMO weather code mapping (0-99 → human readable)
  │   └── generate_agri_advisory() — Rain/temp/storm → farmer advice
  │
  └── geocoding.py
      ├── geocode_location() — Nominatim API (name → lat/lon)
      ├── get_coordinates() — Hardcoded dict first, then API fallback
      └── @lru_cache(maxsize=256) — In-memory caching
```

---

## 7. Data Pipeline

### Daily Ingestion Flow

```
                 ┌────────────────────┐
                 │   EventBridge      │
                 │   cron(0 16 * * ?) │ ← 9:30 PM IST / 4:00 PM UTC
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │   mandimitra-data  │
                 │   -ingestion       │
                 │   Lambda           │
                 │   (15 min timeout) │
                 └─────────┬──────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
    ┌──────────────┐ ┌──────────┐ ┌──────────┐
    │  data.gov.in │ │ DynamoDB │ │    S3    │
    │  Agmarknet   │ │ Batch    │ │  Audit   │
    │  API         │ │ Write    │ │  Logs    │
    │  (280 calls) │ │          │ │          │
    └──────────────┘ └──────────┘ └──────────┘
     20 commodities     8,874+     Raw JSON
     x 14 states        records    responses
```

### Data Coverage

| Dimension | Count | Examples |
|-----------|-------|---------|
| Commodities (tracked) | 20 | Wheat, Soyabean, Onion, Tomato, Potato, Cotton, Rice |
| Commodities (in DB) | 205 | Agmarknet returns all commodities at queried mandis |
| States (tracked) | 14 | MP, Rajasthan, Maharashtra, UP, Gujarat, Karnataka, Punjab, Haryana |
| States (in DB) | 24 | From historical fetch scripts |
| Mandis (GPS mapped) | 60+ | Indore, Dewas, Ujjain, Shajapur, Karnal, Delhi, Ahmedabad |
| Date range | 2006-2026 | Historical + daily updates |
| Total records | 8,874+ | Growing daily |

---

## 8. Database Design

### DynamoDB Table: MandiMitraPrices

```
┌─────────────────────────────────────────────────────────────────┐
│                      MandiMitraPrices                            │
│                      Billing: PAY_PER_REQUEST                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Primary Key:                                                    │
│  ├── PK (Partition): "WHEAT#MADHYA_PRADESH"                     │
│  └── SK (Sort):      "2026-03-05#INDORE#BOLD"                   │
│                       {date}#{mandi}#{variety}                   │
│                                                                  │
│  Attributes:                                                     │
│  ├── commodity        "Wheat"                                    │
│  ├── state            "Madhya Pradesh"                           │
│  ├── district         "Indore"                                   │
│  ├── mandi_name       "INDORE"                                   │
│  ├── arrival_date     "2026-03-05"                               │
│  ├── variety          "BOLD"                                     │
│  ├── min_price        2200 (Rs/quintal)                          │
│  ├── max_price        2400                                       │
│  ├── modal_price      2300                                       │
│  ├── date_commodity   "2026-03-05#WHEAT"                         │
│  ├── ingested_at      "2026-03-05T16:30:00Z"                    │
│  └── arrivals_tonnes  450 (optional)                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GSI: MANDI-INDEX                                                │
│  ├── PK: mandi_name     "INDORE"                                │
│  ├── SK: date_commodity  "2026-03-05#WHEAT"                     │
│  └── Projection: ALL                                             │
│  Use: "Show all commodities at Indore mandi"                    │
│                                                                  │
│  GSI: DATE-INDEX                                                 │
│  ├── PK: arrival_date   "2026-03-05"                            │
│  ├── SK: PK             "WHEAT#MADHYA_PRADESH"                  │
│  └── Projection: ALL                                             │
│  Use: "Show all prices for today"                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Access Patterns

| Pattern | Query | Index | Used By |
|---------|-------|-------|---------|
| Prices by commodity + state | PK = "WHEAT#MP", SK begins_with "2026-03" | Main table | query_mandi_prices |
| Prices at specific mandi | mandi_name = "INDORE" | MANDI-INDEX | get_all_prices_at_mandi |
| All prices on a date | arrival_date = "2026-03-05" | DATE-INDEX | Data analysis |
| Nearby mandis | In-memory Haversine from MANDI_COORDINATES | None | get_nearby_mandis |
| Price trend | PK query last 30 days | Main table | get_price_trend |
| Available commodities | Full scan with projection | None | list_available_commodities |

---

## 9. API Design

### API Gateway: MandiMitraAPI

**Base URL:** `https://skwsw8qk22.execute-api.us-east-1.amazonaws.com/prod/api`

#### POST /api/chat

Send a message to the AI agent.

```json
// Request
{
  "message": "गेहूं का भाव इंदौर में बताओ",
  "session_id": "uuid-v4-string",
  "language": "hi",
  "latitude": 22.72,
  "longitude": 75.86,
  "state": "Madhya Pradesh",
  "city": "Indore"
}

// Response
{
  "response": "इंदौर मंडी में गेहूं का आज का भाव:\n- न्यूनतम: ₹2,200/क्विंटल\n- अधिकतम: ₹2,400/क्विंटल\n- मॉडल: ₹2,300/क्विंटल\n\nMSP: ₹2,275/क्विंटल\n📈 7-दिन का रुझान: बढ़ रहा है (+2.3%)",
  "agent_trace": [
    {"type": "preprocessing", "content": "Detected Hindi, commodity: Wheat, location: Indore"},
    {"type": "tool_call", "content": "query_mandi_prices(Wheat, MADHYA_PRADESH, INDORE)"},
    {"type": "observation", "content": "{prices: [...]}"},
    {"type": "model_output", "content": "Final formatted response"}
  ],
  "latency_ms": 21400,
  "language": "hi"
}
```

#### GET /api/prices/{commodity}

Direct price lookup (bypasses AI agent).

```
GET /api/prices/Wheat?state=MADHYA_PRADESH&mandi=INDORE&days=7
GET /api/prices/_list?state=MADHYA_PRADESH  → Available commodities with Hindi translations
```

### CORS Configuration

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## 10. Agent Prompts & Intelligence

### Language Detection Strategy

```
User message analysis (in chat_handler):

1. Devanagari script detected → Hindi
   → "[RESPOND IN HINDI. Use शुद्ध हिंदी.]"

2. Hindi transliteration (gehun, bhav, mein) → Hinglish
   → "[RESPOND IN HINGLISH. Mix Hindi and English naturally.]"

3. Default → English
   → "[RESPOND IN ENGLISH.]"
```

### Supervisor Prompt Key Rules

1. **ALWAYS call tools first** — Never say "data not available" without querying
2. **Location resolution priority**: Message mention > GPS > context > ask user
3. **City != Mandi**: Indore (city) may have multiple mandis (INDORE APMC, INDORE FRUIT MARKET)
4. **Spelling correction**: Common misspellings auto-corrected (gehun -> Wheat, pyaj -> Onion)
5. **Response format**: Standard template with prices, MSP comparison, trend, and actionable advice
6. **Data freshness**: Agmarknet finalizes by 5 PM IST; morning queries may show yesterday's data

### Sell Recommendation Decision Matrix

```
                     Price vs MSP
                  Above    |    Below
               ┌───────────┼───────────┐
    Rising     │   HOLD    │   HOLD    │
  Trend        │  (wait    │  (wait    │
               │  for      │  for MSP) │
               │  peak)    │           │
               ├───────────┼───────────┤
    Falling    │   SELL    │   SELL    │
               │  (capture │  (cut     │
               │  current) │  losses)  │
               ├───────────┼───────────┤
    Stable     │   SPLIT   │   HOLD    │
               │  (sell    │  (await   │
               │  50%)     │  uptick)  │
               └───────────┴───────────┘

  Overrides:
  - Perishability > 7 → SELL regardless (Tomato=9, Onion=7)
  - Weather risk (rain > 20mm) → SELL perishables
  - Price > 120% MSP → SELL (exceptional price)
```

---

## 11. Observability & Monitoring

### LangFuse Tracing

```
Chat Handler → LangFuse Cloud (https://cloud.langfuse.com)
  │
  ├── Trace per conversation turn:
  │   ├── Input: user message (original)
  │   ├── Output: agent response (cleaned)
  │   ├── Model: claude-sonnet-4
  │   ├── Latency: response time in ms
  │   ├── Session ID: conversation grouping
  │   └── Metadata: language, location, trace steps
  │
  └── Graceful degradation: if langfuse import fails, tracing is silently disabled
```

### CloudWatch Alarms (7 Active)

| Alarm | Metric | Threshold |
|-------|--------|-----------|
| MandiMitra-ChatHandler-Errors | Lambda Errors | > 0 in 5 min |
| MandiMitra-ChatHandler-HighDuration | Duration | > 25000ms |
| MandiMitra-ChatHandler-Throttles | Throttles | > 0 in 5 min |
| MandiMitra-DataIngestion-Errors | Lambda Errors | > 0 in 5 min |
| MandiMitra-PriceQuery-Errors | Lambda Errors | > 0 in 5 min |
| MandiMitra-DynamoDB-SystemErrors | SystemErrors | > 0 in 5 min |
| MandiMitra-DynamoDB-ReadThrottles | ReadThrottleEvents | > 0 in 5 min |

### Agent Trace Transparency

Every bot response includes an expandable "How MandiMitra Reasoned" section showing:
- Preprocessing steps (language detection, intent classification)
- Reasoning steps (which agent, which tools)
- Tool calls (exact function + parameters)
- Observations (raw tool results)
- Model output (final reasoning)

---

## 12. Security & Guardrails

### Bedrock Guardrail: MandiMitraGuardrail (snlfs5xjb61l)

| Policy | Level | Direction |
|--------|-------|-----------|
| Violence | HIGH | Input + Output |
| Hate speech | HIGH | Input + Output |
| Sexual content | HIGH | Input + Output |
| Misconduct | MEDIUM | Input + Output |
| Insults | LOW | Input + Output |
| Prompt attacks | MEDIUM | Input only |

### Topic Deny Policy

| Topic | Description |
|-------|-------------|
| FinancialInvestment | Blocks stock market, futures trading, investment advice |

### Word Filters

- "guaranteed profit" → Blocked
- Profanity list → Blocked

### Infrastructure Security

- S3 bucket: Private (website endpoint only)
- CloudFront: HTTPS enforced (enables browser Voice + GPS APIs)
- API Gateway: CORS configured
- Lambda: IAM role with least-privilege DynamoDB/Bedrock/S3 access
- DynamoDB: Encryption at rest (AWS managed)
- No secrets in code: `.env` in `.gitignore`, credentials via Lambda env vars

---

## 13. Deployment Architecture

### Current Deployment Model

```
Developer Machine
  │
  ├── Frontend Deploy:
  │   └── npm run build → aws s3 sync → CloudFront invalidation
  │
  ├── Lambda Deploy:
  │   ├── Chat Handler: zip handler.py + langfuse/* → update-function-code
  │   ├── Price Query:  zip handler.py + shared/* → update-function-code
  │   └── Data Ingestion: zip handler.py → update-function-code
  │
  └── Agent Config:
      └── aws bedrock-agent update-agent → prepare-agent
          (sub-agents first, then supervisor)
```

### SAM Template (infra/template.yaml)

Infrastructure-as-Code for one-command deployment:

```yaml
Resources:
  PriceTable:       DynamoDB (PAY_PER_REQUEST, 2 GSIs)
  DataBucket:       S3 (audit logs)
  DataIngestion:    Lambda (Python 3.12, 512MB, 900s) + EventBridge schedule
  ChatHandler:      Lambda (Python 3.12, 512MB, 29s)
  PriceQuery:       Lambda (Python 3.12, 256MB, 30s)
  APIGateway:       HTTP API (/api/chat POST, /api/prices GET)
```

### Agent Preparation Order

When updating agents, sub-agents must be prepared **before** the supervisor:

```
1. Prepare PriceIntelligence (CAEJ90IYS6)  → Wait for PREPARED
2. Prepare SellAdvisory (CCYSN80MGN)       → Wait for PREPARED
3. Prepare Negotiation (UZRXDX75NR)        → Wait for PREPARED
4. Prepare Weather (XE43VNHO3T)            → Wait for PREPARED
5. Prepare Supervisor (GDSWGCDJIX)         → Wait for PREPARED
```

---

## 14. User Flows

### Flow 1: Price Check

```
User: "इंदौर में गेहूं का भाव क्या है?"
  │
  ├── Supervisor → PriceIntelligenceAgent
  ├── Tool: query_mandi_prices("Wheat", "MADHYA_PRADESH", "INDORE")
  ├── Tool: get_msp("Wheat")
  │
  └── Response:
      इंदौर मंडी में गेहूं का भाव:
      - न्यूनतम: ₹2,200/क्विंटल
      - अधिकतम: ₹2,400/क्विंटल
      - मॉडल: ₹2,300/क्विंटल

      MSP: ₹2,275/क्विंटल (मॉडल भाव MSP से ऊपर)
      7-दिन रुझान: +2.3% बढ़ रहा है
```

### Flow 2: Best Mandi (GPS-based)

```
User: "20 क्विंटल सोयाबीन कहाँ बेचूं?"
  │
  ├── Supervisor → PriceIntelligenceAgent
  ├── Tool: get_nearby_mandis(22.72, 75.86, 50, "Soyabean")
  ├── Tool: calculate_transport_cost(...)
  │
  └── Response:
      आपके 50km के अंदर मंडियाँ:
      1. इंदौर - ₹4,950/qtl (ट्रांसपोर्ट: ₹160) → शुद्ध: ₹4,790
      2. देवास - ₹4,900/qtl (ट्रांसपोर्ट: ₹480) → शुद्ध: ₹4,420
      3. उज्जैन - ₹4,850/qtl (ट्रांसपोर्ट: ₹640) → शुद्ध: ₹4,210

      सुझाव: इंदौर मंडी में बेचें (सबसे ज्यादा शुद्ध मुनाफा)
```

### Flow 3: Sell/Hold Advisory

```
User: "50 क्विंटल सोयाबीन बेचूं या रुकूं?"
  │
  ├── Supervisor → SellAdvisoryAgent
  ├── Tool: get_sell_recommendation("Soyabean", "MP", "INDORE", 50, 22.72, 75.86)
  │         (internally calls: prices + trend + MSP + weather + season + nearby)
  │
  └── Response:
      सुझाव: HOLD (70% confidence)

      कारण:
      1. भाव MSP (₹4,892) से ऊपर
      2. 30-दिन का रुझान: बढ़ रहा है (+3.2%)
      3. मौसम: अगले 5 दिन साफ
      4. सोयाबीन कम जल्दी खराब होती है (Index: 2/10)
      5. फसल सीज़न: कटाई के बाद — भंडारण संभव

      भंडारण सुझाव: सूखी जगह पर रखें, नमी 12% से कम रखें
```

### Flow 4: Negotiation Brief

```
User: "गेहूं का price brief दो"
  │
  ├── Supervisor → NegotiationAgent
  ├── Tools: query_mandi_prices + get_msp + get_price_trend + get_nearby_mandis
  │
  └── Response:
      गेहूं — मूल्य संक्षेप (6 मार्च 2026)

      आज का भाव (इंदौर): ₹2,300/qtl
      MSP 2025-26: ₹2,275/qtl
      उचित भाव: ₹2,280 - ₹2,350/qtl

      बाज़ार रुझान: 7 दिनों में +2.3%

      आस-पास की मंडियाँ:
      - देवास: ₹2,250  |  उज्जैन: ₹2,280

      ₹2,300 से कम पर न बेचें — भाव MSP से ऊपर और बढ़ रहा है

      [WhatsApp पर शेयर करें]
```

### Flow 5: Weather Advisory

```
User: "अगले 5 दिन मौसम कैसा रहेगा?"
  │
  ├── Supervisor → WeatherAgent
  ├── Tool: get_weather_advisory(22.72, 75.86)
  │
  └── Response:
      5-दिन मौसम पूर्वानुमान (इंदौर):

      आज:    32°C / 18°C  साफ
      कल:    33°C / 19°C  साफ
      परसों:  30°C / 20°C  हल्की बारिश (5mm)
      दिन 4:  28°C / 18°C  बादल
      दिन 5:  31°C / 17°C  साफ

      कृषि सलाह:
      - परसों हल्की बारिश — सब्ज़ियाँ ढककर रखें
      - कटाई के लिए अगले 2 दिन अच्छे हैं
      - भंडारण: नमी बढ़ सकती है, अनाज सूखा रखें
```

---

## 15. File Structure

```
MandiMitra/
│
├── frontend/                          # Next.js 14 + Tailwind CSS PWA
│   ├── app/
│   │   ├── page.tsx                   # Main chat application + demo simulator
│   │   ├── layout.tsx                 # Root layout, metadata, PWA
│   │   ├── globals.css                # Custom styles, animations, Devanagari font
│   │   ├── components/
│   │   │   ├── ChatHeader.tsx         # Header: logo, language toggle, status
│   │   │   ├── ChatBubble.tsx         # Messages: TTS, copy, WhatsApp, trace
│   │   │   ├── ChatInput.tsx          # Input: textarea, voice mic, send
│   │   │   ├── WelcomeScreen.tsx      # Landing: feature cards, crop picker
│   │   │   ├── LocationPicker.tsx     # Location: GPS, state/city dropdown
│   │   │   ├── QuickActions.tsx       # Quick action buttons
│   │   │   ├── PriceChart.tsx         # SVG mini price chart
│   │   │   └── TypingIndicator.tsx    # Animated loading dots
│   │   └── lib/
│   │       ├── api.ts                 # TypeScript types + API client
│   │       └── voice.ts              # Web Speech API (STT + TTS)
│   ├── public/
│   │   ├── manifest.json             # PWA manifest
│   │   ├── sw.js                     # Service worker
│   │   └── icon-*.png                # App icons
│   ├── next.config.mjs               # Static export config
│   ├── tailwind.config.ts            # Custom color palette
│   └── package.json                  # Dependencies
│
├── backend/
│   ├── lambdas/
│   │   ├── chat_handler/
│   │   │   ├── handler.py            # Chat Lambda (Bedrock + LangFuse)
│   │   │   └── requirements.txt      # boto3, langfuse
│   │   ├── price_query/
│   │   │   ├── handler.py            # Price query + Action Groups (13 tools)
│   │   │   └── requirements.txt      # boto3
│   │   ├── data_ingestion/
│   │   │   ├── handler.py            # Agmarknet → DynamoDB pipeline
│   │   │   └── requirements.txt      # boto3
│   │   └── shared/
│   │       ├── __init__.py
│   │       ├── constants.py           # Commodities, states, MSP, coordinates
│   │       ├── dynamodb_utils.py      # DB queries, trend, sell recommendation
│   │       ├── weather_utils.py       # Open-Meteo API + agri advisory
│   │       └── geocoding.py           # Nominatim reverse geocoding
│   │
│   ├── agent_configs/
│   │   ├── orchestrator_prompt.txt    # Supervisor system prompt
│   │   ├── price_intel_prompt.txt     # PriceIntelligence prompt
│   │   ├── sell_advisory_prompt.txt   # SellAdvisory prompt
│   │   ├── negotiation_prep_prompt.txt # Negotiation prompt
│   │   ├── price_intel_openapi.json   # OpenAPI spec for Action Groups
│   │   └── sub_agents/
│   │       └── weather_agent_prompt.txt # Weather prompt
│   │
│   └── scripts/
│       ├── create_multi_agent.py      # Multi-agent setup
│       ├── setup_multi_agent_resume.py # Resume agent setup
│       ├── fetch_30days.py            # Historical data fetch
│       └── fetch_7days.py             # Weekly data fetch
│
├── infra/
│   ├── template.yaml                  # AWS SAM CloudFormation template
│   ├── setup_aws.sh                   # Manual AWS setup script
│   └── BEDROCK_SETUP_GUIDE.md         # Step-by-step agent creation guide
│
├── tests/
│   ├── edge_cases.spec.js             # Playwright: edge cases
│   ├── frontend_flows.spec.js         # Playwright: main flows
│   └── debug_potato.spec.js           # Playwright: debug test
│
├── data/                              # Sample data files (dev/test)
├── docs/                              # Additional documentation
│
├── multi_agent_ids.json               # Agent + alias IDs
├── playwright.config.js               # E2E test configuration
├── ARCHITECTURE.md                    # THIS FILE
├── PROJECT_AUDIT.md                   # AWS resource audit
├── TEAM_HANDOFF.md                    # Status + task assignment
├── README.md                          # Project overview
└── .env.example                       # Environment variable template
```

---

## 16. Resource IDs & Configuration

### Bedrock Agents

| Agent | Agent ID | Alias ID | Model | Status |
|-------|----------|----------|-------|--------|
| MandiMitra (Supervisor) | GDSWGCDJIX | TSTALIASID (DRAFT) | us.anthropic.claude-sonnet-4-20250514-v1:0 | PREPARED |
| PriceIntelligence | CAEJ90IYS6 | 7YU2OMSRBQ (live) | us.anthropic.claude-sonnet-4-20250514-v1:0 | PREPARED |
| SellAdvisory | CCYSN80MGN | HPMZYLQZU3 (live) | us.anthropic.claude-sonnet-4-20250514-v1:0 | PREPARED |
| Negotiation | UZRXDX75NR | TFQ24DRCOW (live) | us.anthropic.claude-sonnet-4-20250514-v1:0 | PREPARED |
| Weather | XE43VNHO3T | YUSEVJPMWJ (live) | us.anthropic.claude-sonnet-4-20250514-v1:0 | PREPARED |

### Lambda Functions

| Function | Runtime | Memory | Timeout | Last Deployed |
|----------|---------|--------|---------|---------------|
| mandimitra-chat | Python 3.12 | 512 MB | 29s | 2026-03-06 (with langfuse bundled) |
| mandimitra-price-query | Python 3.12 | 256 MB | 30s | 2026-03-06 (with geocoding.py) |
| mandimitra-data-ingestion | Python 3.12 | 512 MB | 900s | 2026-03-05 |

### AWS Resources

| Resource | ID/ARN | Region |
|----------|--------|--------|
| API Gateway | skwsw8qk22 (MandiMitraAPI) | us-east-1 |
| CloudFront | E1FOPZ17Q7P6CF | Global |
| S3 (Frontend) | mandimitra-frontend-471112620976 | us-east-1 |
| S3 (Data) | mandimitra-data | us-east-1 |
| DynamoDB | MandiMitraPrices | us-east-1 |
| EventBridge | mandimitra-daily-ingestion | us-east-1 |
| Guardrail | snlfs5xjb61l | us-east-1 |

### Environment Variables

```bash
# Backend (.env)
AWS_DEFAULT_REGION=us-east-1
BEDROCK_AGENT_ID=GDSWGCDJIX
BEDROCK_AGENT_ALIAS_ID=TSTALIASID
DATA_GOV_API_KEY=<from data.gov.in>
LANGFUSE_PUBLIC_KEY=<from langfuse.com>
LANGFUSE_SECRET_KEY=<from langfuse.com>
LANGFUSE_HOST=https://cloud.langfuse.com

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://skwsw8qk22.execute-api.us-east-1.amazonaws.com/prod/api
```

---

*Built with Amazon Bedrock Multi-Agent Collaboration, Claude Sonnet 4, and a lot of chai.*
