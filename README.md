# MandiMitra — AI Mandi Price Intelligence for Indian Farmers

> AI-powered multi-agent copilot that gives Indian farmers real-time mandi price intelligence, sell/hold recommendations, and negotiation support — all in Hindi.

**Track:** AI for Retail, Commerce & Market Intelligence
**Hackathon:** AI for Bharat (AWS x Hack2skill)
**Team:** Robots | Lead: Ujjwal Godara
**Live URL:** [https://d2mtfau3fvs243.cloudfront.net](https://d2mtfau3fvs243.cloudfront.net)

---

## The Problem

India has 7,000+ APMC mandis generating massive commodity price data, yet **86% of small farmers** sell at whatever price the local intermediary offers — losing **15-30% of potential crop value** due to information asymmetry. Current government portals are English-only raw dashboards that lack actionable intelligence.

## The Solution

MandiMitra uses **Amazon Bedrock Multi-Agent Collaboration** with a Supervisor Agent routing to 4 specialist sub-agents + a Knowledge Base (RAG), providing comprehensive market intelligence through a conversational Hindi interface.

| Capability | Agent | What It Does |
|-----------|-------|-------------|
| Price Intelligence | PriceIntelligenceAgent | Real-time mandi prices, nearby mandis (GPS-based, 50km radius), trend analysis |
| Sell Advisory | SellAdvisoryAgent | AI-powered SELL / HOLD / SPLIT with shelf life, storage tips, weather risk |
| Negotiation Prep | NegotiationAgent | Generates shareable price briefs for mandi negotiation |
| Weather Advisory | WeatherAgent | 5-day agricultural weather forecast and sell-timing guidance |
| Knowledge Base (RAG) | Bedrock KB | MSP rates, crop calendars, storage guides, mandi procedures |

**20+ commodities** tracked across **24 states** with **16,500+ DynamoDB records** and **60+ mandi GPS coordinates**.

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
   [Bedrock SUPERVISOR Agent]
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
| Amazon Bedrock Knowledge Base | RAG over agricultural policy documents (Titan Embeddings v2) |
| Amazon OpenSearch Serverless | Vector store for Knowledge Base embeddings |
| Amazon DynamoDB | Price time-series storage (16,500+ records) |
| AWS Lambda | 3 serverless functions (chat, price query, data ingestion) |
| Amazon API Gateway | REST API (chat + prices) |
| Amazon S3 | Static website hosting + KB document storage |
| Amazon CloudFront | HTTPS CDN (enables Voice + GPS APIs) |
| Amazon EventBridge | Daily automated data ingestion (9:30 PM IST) |
| Bedrock Guardrails | Content filtering and safety rails |
| Amazon CloudWatch | Lambda monitoring + 7 CloudWatch Alarms |
| LangFuse | LLM tracing and observability |

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
- AWS account with Bedrock access (Claude Sonnet 4 enabled)
- data.gov.in API key (free at https://data.gov.in)

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Load Data
```bash
pip install boto3 requests
python backend/scripts/fetch_30days.py   # Fetch 30 days of price data
```

### Test the API
```bash
curl -X POST https://d2mtfau3fvs243.cloudfront.net/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "wheat ka bhav MP mein", "session_id": "test1", "language": "hi"}'
```

### Knowledge Base Setup
```bash
pip install opensearch-py requests-aws4auth
python backend/knowledge_base/setup_knowledge_base.py
```

### Run Tests
```bash
npx playwright test tests/frontend_flows.spec.js --project=chromium
```

---

## Project Structure

```
hackathon/
+-- frontend/                     # Next.js 14 + Tailwind CSS PWA
|   +-- app/
|       +-- components/           # Chat UI, Price Chart, Location Picker
|       +-- lib/                  # API client, voice input
|       +-- page.tsx              # Main chat application
+-- backend/
|   +-- lambdas/
|   |   +-- chat_handler/         # Bedrock Agent invocation + LangFuse
|   |   +-- price_query/          # Action group tool implementations
|   |   +-- data_ingestion/       # Agmarknet --> DynamoDB pipeline
|   |   +-- shared/               # Constants, DB utils, weather utils
|   +-- agent_configs/
|   |   +-- sub_agents/           # Multi-agent prompts (5 agents)
|   +-- knowledge_base/           # RAG documents + setup scripts
|   |   +-- msp_rates_comprehensive.md
|   |   +-- crop_calendar_india.md
|   |   +-- storage_and_post_harvest.md
|   |   +-- mandi_guide_india.md
|   |   +-- setup_knowledge_base.py
|   +-- scripts/                  # Data fetching & agent setup scripts
+-- docs/                         # Architecture, flows, audit docs
+-- tests/                        # Playwright E2E tests
+-- infra/                        # Infrastructure setup guides
+-- ARCHITECTURE.md               # Detailed system architecture
+-- README.md                     # This file
```

---

## Knowledge Base (RAG)

MandiMitra includes a Bedrock Knowledge Base with curated agricultural documents:

| Document | Content |
|----------|---------|
| MSP Rates | Official MSP for Kharif 2024-26 and Rabi 2025-27, sourced from PIB/CCEA |
| Crop Calendar | 20+ crops with sowing/harvest months, best sell windows, state-wise data |
| Storage Guide | Crop-wise storage methods, shelf life, temperature/humidity requirements |
| Mandi Guide | APMC procedures, state-wise fee structures, e-NAM registration, government schemes |

**Stack:** S3 --> Titan Embeddings v2 (1024-dim) --> OpenSearch Serverless (FAISS HNSW) --> Bedrock KB

---

## Impact

- **150M+** small farming households in India
- **15-30%** better price realization through market intelligence
- **100% serverless** — scales to millions with no infrastructure management
- Directly supports PM's **Doubling Farmers' Income** mission

---

## Data Source

Real-time commodity prices from **Agmarknet** via [data.gov.in](https://data.gov.in) government API. Covers 2,000+ mandis, 300+ commodities, updated daily. Automated ingestion via EventBridge at 9:30 PM IST.

---

*Built with Amazon Bedrock Multi-Agent Collaboration, Claude Sonnet 4, and a lot of chai.*
