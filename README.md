# MandiMitra — AI Mandi Price Intelligence for Indian Farmers

> AI-powered multi-agent copilot that gives Indian farmers real-time mandi price intelligence, sell/hold recommendations, and negotiation support — all in Hindi.

**Track:** AI for Retail, Commerce & Market Intelligence
**Hackathon:** AI for Bharat (AWS x Hack2skill)
**Team:** Robots | Lead: Ujjwal Godara
**Live URL:** [https://d2mtfau3fvs243.cloudfront.net](https://d2mtfau3fvs243.cloudfront.net)
**GitHub:** [github.com/ujjwalgodara9/AI-For-Bharat--AWS](https://github.com/ujjwalgodara9/AI-For-Bharat--AWS)

---

## The Problem

India has 7,000+ APMC mandis generating massive commodity price data, yet **86% of small farmers** sell at whatever price the local intermediary offers — losing **15-30% of potential crop value** due to information asymmetry. Current government portals are English-only raw dashboards that lack actionable intelligence.

## The Solution

MandiMitra uses **Amazon Bedrock Multi-Agent Collaboration** (SUPERVISOR mode) to orchestrate **5 specialist AI agents** + a Knowledge Base (RAG) via **13 tool functions**, providing comprehensive market intelligence through a conversational Hindi interface.

| Capability | Agent | What It Does |
|-----------|-------|-------------|
| Price Intelligence | PriceIntelligenceAgent | Real-time mandi prices, nearby mandis (GPS-based, 50-100km radius), trend analysis, MSP comparison |
| Sell Advisory | SellAdvisoryAgent | AI-powered SELL / HOLD / SPLIT analyzing 14 factors (price trend, perishability, MSP, weather, season, storage) |
| Negotiation Prep | NegotiationAgent | Generates shareable price briefs with MSP reference, local/best price, trend direction |
| Weather Advisory | WeatherAgent | 5-day agricultural weather forecast with sell-timing guidance via Open-Meteo |
| Knowledge Base (RAG) | Bedrock KB | MSP rates (2024-27), crop calendars, storage guides, mandi procedures via 4 curated docs |

**222 commodities** across **24 states** with **16,500+ DynamoDB records**, **1,451 mandis**, and **60+ GPS coordinates**.

---

## Architecture

```
User (Hindi/English/Voice) --> CloudFront HTTPS CDN
        |
   [S3 Static PWA - Next.js 14]
        | POST /api/chat
   [API Gateway REST]
        |
   [mandimitra-chat Lambda]
        |
   [Bedrock SUPERVISOR Agent (Claude Sonnet)]
   +----+--------+-----------+----------+------------------+
   |    |        |           |          |                  |
[Price] [Sell] [Negot.] [Weather] [Knowledge Base]
[Intel] [Adv.] [Agent]  [Agent]   [RAG - OpenSearch]
[Agent]                            MSP, Crops, Storage
   |       |        |       |
   +-------+--------+-------+
              | (all use)
   [mandimitra-price-query Lambda]
   +----------+-----------------------+
   |          |                       |
[DynamoDB] [Open-Meteo API]   [data.gov.in Agmarknet]
16,500+    Weather forecast    Daily price ingestion
records
```

---

## AWS Services Used

| Service | Purpose |
|---------|---------|
| Amazon Bedrock Agents | Multi-agent supervisor + 4 specialist sub-agents (Claude Sonnet 4) |
| Amazon Bedrock Knowledge Base | RAG over 4 curated agricultural documents (Titan Embeddings v2) |
| Amazon OpenSearch Serverless | FAISS HNSW vector store for Knowledge Base embeddings |
| Amazon DynamoDB | Price time-series storage (16,500+ records, 3 GSIs, 222 commodities) |
| AWS Lambda | 3 functions — Chat Handler (60s), Price Query (30s, 13 tools), Data Ingestion (900s) |
| Amazon API Gateway | REST API with CORS + rate limiting |
| Amazon S3 | Static frontend hosting + KB docs + audit logs |
| Amazon CloudFront | HTTPS CDN (enables Voice + GPS browser APIs on mobile) |
| Amazon EventBridge | Daily automated data ingestion cron (9:30 PM IST) |
| Bedrock Guardrails v3 | Content filtering, safety rules, PII protection, factual grounding |
| Amazon CloudWatch | 7 alarms (errors, throttles, duration) + Lambda monitoring + logs |
| LangFuse | LLM tracing and observability on every invocation |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14, React 18, TypeScript 5, Tailwind CSS 3.4 | Mobile-first PWA with Hindi UI |
| Backend | Python 3.12, AWS Lambda | Serverless API + data pipeline |
| AI/ML | Amazon Bedrock (Claude Sonnet 4 + Haiku), Titan Embeddings v2 | Multi-agent orchestration + RAG |
| Database | DynamoDB (PAY_PER_REQUEST, 3 GSIs) | Time-series price data |
| Vector Store | OpenSearch Serverless | Knowledge Base embeddings |
| IaC | AWS SAM (template.yaml) | Infrastructure as Code |
| Testing | Playwright | E2E browser tests |
| Observability | LangFuse, CloudWatch | LLM traces + monitoring |

---

## Demo Flows

1. **Price Check (Hindi):** *"Madhya Pradesh mein gehun ka bhav kya hai?"*
   --> PriceIntelligenceAgent queries DynamoDB, returns 10 mandis with today's prices

2. **Best Mandi (GPS):** *"Mere paas 20 quintal soyabean hai, kahan bechun?"*
   --> Finds mandis within 50km, ranks by net realization (price minus transport)

3. **Smart Sell Advisory:** *"Kya abhi soyabean bechna chahiye ya rukun?"*
   --> Shelf life + 30-day trend + weather risk --> SELL/HOLD/SPLIT recommendation

4. **Negotiation Brief:** *"Price brief do gehun ka"*
   --> MSP + local price + best nearby mandi + trend --> formatted shareable brief

5. **Weather:** *"Agle 5 din mausam kaisa rahega?"*
   --> 5-day forecast + agricultural sell-timing advisory

6. **Knowledge Base:** *"Wheat ka MSP kya hai?" / "Soyabean kab boya jata hai?"*
   --> RAG retrieval from curated agricultural documents

---

## Quick Start

### Prerequisites
- Node.js 18+, Python 3.12+, AWS CLI v2
- AWS account with Bedrock access (Claude Sonnet & Haiku enabled)
- data.gov.in API key (free at https://data.gov.in)

### 1. Clone & Configure

```bash
git clone https://github.com/ujjwalgodara9/AI-For-Bharat--AWS.git
cd AI-For-Bharat---AWS
cp .env.example .env
# Fill in AWS credentials, data.gov.in API key, Bedrock agent IDs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000 (demo mode when NEXT_PUBLIC_API_URL is empty)
npm run build     # Production build
```

> **Demo mode:** When `NEXT_PUBLIC_API_URL` is empty, the frontend uses `simulateResponse()` with realistic mock data for all 5 flows — no backend needed.

### 3. Deploy Infrastructure (AWS SAM)

```bash
cd infra
sam build
sam deploy --guided   # Prompts for API keys, Bedrock agent IDs, etc.
```

### 4. Load Price Data

```bash
pip install boto3 requests
python backend/scripts/fetch_30days.py   # Fetch 30 days of Agmarknet price data into DynamoDB
```

### 5. Set Up Bedrock Agents

Follow the step-by-step guide: [`infra/BEDROCK_SETUP_GUIDE.md`](infra/BEDROCK_SETUP_GUIDE.md)

### 6. Knowledge Base Setup (Optional)

```bash
pip install opensearch-py requests-aws4auth
python backend/knowledge_base/setup_knowledge_base.py
```

### 7. Run Tests

```bash
npx playwright test tests/frontend_flows.spec.js --project=chromium
```

### 8. Test the API

```bash
curl -X POST https://<your-cloudfront-url>/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "wheat ka bhav MP mein", "session_id": "test1", "language": "hi"}'
```

---

## Project Structure

```
AI-For-Bharat---AWS/
├── frontend/                          # Next.js 14 + Tailwind CSS PWA
│   ├── app/
│   │   ├── page.tsx                   # Main chat app (demo mode + live API)
│   │   ├── layout.tsx                 # Root layout, metadata, service worker
│   │   ├── globals.css                # Custom styles, Devanagari fonts
│   │   ├── components/
│   │   │   ├── ChatHeader.tsx         # Header with language toggle, GPS status
│   │   │   ├── ChatBubble.tsx         # Messages + expandable Agent Trace panel
│   │   │   ├── ChatInput.tsx          # Text input, voice button, send
│   │   │   ├── QuickActions.tsx       # Quick action buttons (Hindi)
│   │   │   ├── TypingIndicator.tsx    # Loading animation
│   │   │   ├── WelcomeScreen.tsx      # Landing screen with feature cards
│   │   │   ├── PriceChart.tsx         # Price data visualization
│   │   │   └── LocationPicker.tsx     # GPS / manual location selection
│   │   └── lib/
│   │       ├── api.ts                 # API client, TypeScript types
│   │       └── voice.ts              # Web Speech API wrapper
│   └── public/                        # PWA icons, manifest.json
│
├── backend/
│   ├── lambdas/
│   │   ├── chat_handler/handler.py    # Bedrock Agent invocation + LangFuse tracing
│   │   ├── price_query/handler.py     # Action group tools (6 functions)
│   │   ├── data_ingestion/handler.py  # Agmarknet → DynamoDB daily pipeline
│   │   └── shared/
│   │       ├── constants.py           # MSP rates, commodities, mandi GPS coords
│   │       ├── dynamodb_utils.py      # Price queries, Haversine, trends, sell rec
│   │       ├── weather_utils.py       # Open-Meteo API weather advisory
│   │       └── geocoding.py           # State/city → lat/lon lookup
│   ├── agent_configs/
│   │   ├── orchestrator_prompt.txt    # Supervisor agent system prompt
│   │   ├── price_intel_prompt.txt     # PriceIntel agent prompt
│   │   ├── sell_advisory_prompt.txt   # SellAdvisory agent prompt
│   │   ├── negotiation_prep_prompt.txt# Negotiation agent prompt
│   │   ├── price_intel_openapi.json   # OpenAPI spec for agent action groups
│   │   └── sub_agents/               # Alternative agent configs
│   ├── knowledge_base/
│   │   ├── msp_rates_comprehensive.md # Kharif 2024-26 & Rabi 2025-27 MSP rates
│   │   ├── crop_calendar_india.md     # 20+ crops sowing/harvest/sell windows
│   │   ├── storage_and_post_harvest.md# Storage methods, shelf life, temp/humidity
│   │   ├── mandi_guide_india.md       # APMC procedures, e-NAM, state fees
│   │   ├── setup_knowledge_base.py    # RAG setup script
│   │   └── upload_to_s3.py           # Upload KB docs to S3
│   └── scripts/
│       ├── fetch_30days.py            # Fetch 30 days price data
│       ├── fetch_all_india.py         # Bulk all-India data fetch
│       ├── create_multi_agent.py      # Bedrock agent creation script
│       └── test_rate_limit.py         # API rate limit testing
│
├── infra/
│   ├── template.yaml                  # AWS SAM template (full stack deploy)
│   ├── setup_aws.sh                   # Manual AWS CLI setup script
│   └── BEDROCK_SETUP_GUIDE.md         # Step-by-step agent creation guide
│
├── tests/
│   ├── frontend_flows.spec.js         # E2E tests: all 5 primary flows (Hindi)
│   └── edge_cases.spec.js             # Language detection, spelling edge cases
│
├── docs/
│   ├── TEAM_HANDOFF.md                # Project status, what's done, next steps
│   ├── KNOWLEDGE_BASE_GUIDE.md        # RAG setup & document strategy
│   ├── FLOWS.md                       # Detailed user flow diagrams
│   ├── PROJECT_AUDIT.md               # Code review findings
│   ├── PRODUCTION_ALIAS_GUIDE.md      # Bedrock production alias setup
│   ├── PLAN.md                        # Execution plan & submission checklist
│   ├── WORKLOG.md                     # Daily progress log
│   ├── design.md                      # Original system design
│   └── requirements.md               # Functional requirements spec
│
├── ARCHITECTURE.md                    # Detailed technical architecture doc
├── README.md                          # This file
└── .env.example                       # Environment variables template
```

---

## Multi-Agent Architecture (Bedrock)

### Orchestrator Agent (Supervisor)
- **Model:** Claude Sonnet 4
- **Mode:** SUPERVISOR (Agent Collaboration)
- **Role:** Intent classification, parameter resolution, routing to 5 specialist agents

### Sub-Agents

| Agent | Model | Tools / Functions |
|-------|-------|-------------------|
| **PriceIntel** | Claude Haiku | `query_mandi_prices`, `get_nearby_mandis`, `get_price_trend`, `get_msp`, `calc_transport_cost` (5 tools) |
| **SellAdvisory** | Claude Sonnet 4 | `get_sell_recommendation`, 14-factor analysis + `get_weather_advisory` |
| **NegotiationPrep** | Claude Haiku | `query_mandi_prices`, `get_msp`, `get_nearby_mandis`, `get_price_trend` (4 tools) |
| **WeatherAdvisory** | Claude Haiku | `get_weather_advisory` via Open-Meteo → 5-day agri forecast |
| **Knowledge Base (RAG)** | Bedrock KB | 4 curated docs: MSP rates 2024-27, crop calendar, storage guide, mandi guide |

### Price Query Lambda — 13 Tool Functions

| Tool | Description |
|------|-------------|
| `query_mandi_prices` | Commodity prices by state/mandi with date range |
| `get_nearby_mandis` | GPS-based mandi finder (50-100km radius, Haversine distance) |
| `get_price_trend` | 7/30-day trend, volatility, moving averages |
| `get_msp` | Official Minimum Support Price lookup |
| `calculate_transport_cost` | Transport cost per quintal per km |
| `calculate_net_realization` | Price minus transport cost per quintal |
| `get_sell_recommendation` | SELL/HOLD/SPLIT with confidence score and reasons |
| `get_weather_advisory` | 5-day agricultural weather forecast via Open-Meteo |

---

## Knowledge Base (RAG)

MandiMitra includes a Bedrock Knowledge Base with curated agricultural documents:

| Document | Content |
|----------|---------|
| MSP Rates | Official MSP for Kharif 2024-26 and Rabi 2025-27, sourced from PIB/CCEA |
| Crop Calendar | 20+ crops with sowing/harvest months, best sell windows, state-wise data |
| Storage Guide | Crop-wise storage methods, shelf life, temperature/humidity requirements |
| Mandi Guide | APMC procedures, state-wise fee structures, e-NAM registration, government schemes |

**Stack:** S3 → Titan Embeddings v2 (1024-dim) → OpenSearch Serverless (FAISS HNSW) → Bedrock KB

---

## DynamoDB Schema

**Table:** `MandiMitraPrices` (PAY_PER_REQUEST billing)

| Key | Format | Example |
|-----|--------|---------|
| **PK** (Partition) | `{COMMODITY}#{STATE}` | `WHEAT#MADHYA_PRADESH` |
| **SK** (Sort) | `{DATE}#{MANDI}` | `2026-03-09#INDORE` |

**GSIs (3):**
- `MANDI-INDEX` — Fast mandi-level lookups
- `DATE-INDEX` — Daily price aggregation
- `COMMODITY-INDEX` — Cross-state commodity queries

**Attributes:** `arrival_date`, `mandi_name`, `district`, `state`, `commodity`, `modal_price`, `min_price`, `max_price`, `quantity_in_qtl`, `msp`

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat` | Send message to Bedrock Agent. Body: `{message, language, session_id}` |
| GET | `/api/prices/{commodity}` | Direct price lookup. Query: `?state=...&mandi=...&days=7` |
| GET | `/api/prices/_list` | List available commodities for a state |
| GET | `/api/prices/_locations` | List districts/mandis for a state |

---

## Data Coverage

| Dimension | Coverage |
|-----------|----------|
| **Commodities** | 222 (20 actively tracked: Wheat, Soyabean, Onion, Tomato, Potato, Mustard, Chana, Maize, Cotton, Rice, Garlic, Moong, Urad, Bajra, Jowar, Groundnut, Turmeric, Red Chilli, Coriander, Cumin) |
| **States** | 24 |
| **Mandis** | 1,451 unique APMC markets |
| **Districts** | 421 |
| **Records** | 16,500+ DynamoDB records (growing daily) |
| **Source** | Agmarknet via [data.gov.in](https://data.gov.in) government API (2,000+ mandis) |
| **Update Frequency** | Daily at 9:30 PM IST via EventBridge |

---

## Language Support

- **Hindi (Devanagari)** — Full native support with Noto Sans Devanagari font
- **Hinglish** — Hindi words in Roman script (auto-detected)
- **English** — Complete English interface
- **Voice Input** — Web Speech API (browser mic button)
- **Auto-detection** — Language detected from Devanagari percentage + transliteration matching

---

## Environment Variables

See [`.env.example`](.env.example) for the full template. Key variables:

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region (default: `us-east-1`) |
| `DATA_GOV_API_KEY` | Free API key from data.gov.in |
| `BEDROCK_AGENT_ID` | Orchestrator agent ID from Bedrock Console |
| `BEDROCK_AGENT_ALIAS_ID` | Agent alias ID (use named alias for production) |
| `LANGFUSE_HOST` | LangFuse endpoint (optional, for LLM tracing) |
| `NEXT_PUBLIC_API_URL` | API Gateway URL (empty = demo mode) |

---

## Performance

| Metric | Value |
|--------|-------|
| End-to-end response time | 15-21 seconds (multi-agent reasoning + DynamoDB + tools) |
| Price Query Lambda | ~2-3 seconds |
| Chat Handler timeout | 60 seconds |
| CloudWatch Alarms | 7 (errors, throttles, duration) — all OK |
| Guardrails | Bedrock Guardrails v3 (content filtering, PII protection) |
| Observability | LangFuse LLM tracing on every invocation |

---

## Estimated Monthly Cost (1,000 DAU MVP)

| Service | Cost (INR) |
|---------|-----------|
| Amazon Bedrock (50K queries) | ~Rs.8,000 |
| DynamoDB (16GB, 500K reads) | ~Rs.800 |
| Knowledge Base (OpenSearch 2 OCU) | ~Rs.3,000 |
| Lambda (100K invocations) | ~Rs.200 |
| S3 + CloudFront | ~Rs.200 |
| API Gateway + EventBridge | ~Rs.300 |
| CloudWatch (7 alarms + logs) | ~Rs.300 |
| **Total** | **~Rs.12,800/month (~$150)** |

Scales to ~Rs.50,000/month at 10,000 DAU. 100% serverless — zero idle cost, pay-per-use.

---

## Impact

- **150M+** small farming households in India
- **15-30%** better price realization through market intelligence
- **Rs.50,000-1,00,000** potential annual recovery per farmer
- **100% serverless** — auto-scales from 0 to millions with zero infrastructure management
- Complements **eNAM**, **PM-KISAN**, **PMFBY**, and **Doubling Farmers' Income** mission
- **Free for individual farmers** — premium tier for FPOs, aggregators, and commodity traders

---

## Roadmap

- WhatsApp Bot integration
- Multi-language support (Marathi, Telugu, Tamil, Gujarati, Punjabi)
- ML-based 7-day price prediction
- Push notifications for price alerts
- Direct buyer-seller marketplace
- Crop photo quality grading
- Satellite data (NDVI) for yield-adjusted forecasting

---

## Documentation

| Document | Description |
|----------|-------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Detailed technical architecture |
| [`infra/BEDROCK_SETUP_GUIDE.md`](infra/BEDROCK_SETUP_GUIDE.md) | Step-by-step Bedrock agent creation |
| [`docs/TEAM_HANDOFF.md`](docs/TEAM_HANDOFF.md) | Project status & handoff notes |
| [`docs/KNOWLEDGE_BASE_GUIDE.md`](docs/KNOWLEDGE_BASE_GUIDE.md) | RAG setup & document strategy |
| [`docs/FLOWS.md`](docs/FLOWS.md) | User flow diagrams |
| [`docs/PROJECT_AUDIT.md`](docs/PROJECT_AUDIT.md) | Code review findings |
| [`docs/PRODUCTION_ALIAS_GUIDE.md`](docs/PRODUCTION_ALIAS_GUIDE.md) | Production alias setup |

---

*Built with Amazon Bedrock Multi-Agent Collaboration, Claude Sonnet 4, and a lot of chai. 12 AWS services in production.*
