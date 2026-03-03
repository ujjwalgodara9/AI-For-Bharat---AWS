# MandiMitra — AI Mandi Price Intelligence for Indian Farmers

> *AI-powered multi-agent copilot that gives Indian farmers real-time mandi price intelligence, sell/hold recommendations, and negotiation support — all in Hindi.*

**Track:** AI for Retail, Commerce & Market Intelligence
**Hackathon:** AI for Bharat (AWS x Hack2skill)
**Team:** Robots | Lead: Ujjwal Godara
**Live URL:** https://d2mtfau3fvs243.cloudfront.net

---

## The Problem

India has 7,000+ APMC mandis generating massive commodity price data, yet **86% of small farmers** sell at whatever price the local intermediary offers — losing **15–30% of potential crop value** due to information asymmetry. Current government portals are English-only raw dashboards that lack actionable intelligence.

## The Solution

MandiMitra uses **Amazon Bedrock Multi-Agent Collaboration** — a Supervisor Agent routing to 4 specialist sub-agents — providing comprehensive market intelligence through a conversational Hindi interface:

| Capability | Agent | What It Does |
|-----------|-------|-------------|
| **Price Intelligence** | PriceIntelligenceAgent | Real-time mandi prices, nearby mandis (GPS-based, 50km radius), trend analysis, transport cost |
| **Sell Advisory** | SellAdvisoryAgent | AI-powered SELL / HOLD / SPLIT with shelf life, storage tips, weather risk, price prediction |
| **Negotiation Prep** | NegotiationAgent | Generates shareable price briefs for mandi negotiation |
| **Weather Advisory** | WeatherAgent | 5-day agricultural weather forecast and sell-timing guidance |
| **Browse & Mandi Tools** | Supervisor (direct) | Dynamic commodity lists, mandi profiles, state-wise data browsing |

**20 commodities** tracked across **14 states** with **5,177+ DynamoDB records** and **60+ mandi GPS coordinates**.

---

## Architecture (v2 — Multi-Agent)

```
User (Hindi/English/Voice) → CloudFront HTTPS CDN
        │
   [S3 Static PWA — Next.js 14]
        │ POST /api/chat
   [API Gateway HTTP]
        │
   [mandimitra-chat Lambda]
        │
   [Bedrock SUPERVISOR Agent — GDSWGCDJIX]
   ┌────┬────────┬───────────┬──────────┐
   │    │        │           │          │
[Price] [Sell] [Negot.] [Weather] [Direct Tools]
[Intel] [Adv.]          [Agent]   BrowseTools
[Agent]                           MandiTools
   │       │        │       │
   └───────┴────────┴───────┘
              │ (all use)
   [mandimitra-price-query Lambda]
   ┌──────────┬────────────────────┐
   │          │                    │
[DynamoDB] [Open-Meteo API]  [data.gov.in Agmarknet]
5,177 items  Weather forecast   Price ingestion
```

## Architecture Change: v1 → v2

| Aspect | v1 (Single Agent) | v2 (Multi-Agent) |
|--------|-------------------|-----------------|
| Bedrock Agent count | 1 | 5 (1 supervisor + 4 sub-agents) |
| Collaboration mode | DISABLED | SUPERVISOR |
| Routing | Agent calls tools directly | Supervisor delegates to specialist sub-agents |
| Action groups | 4 on single agent | 1 per sub-agent (focused) |
| Sell advisory | Tool call on main agent | Dedicated SellAdvisoryAgent |
| Negotiation | Manual multi-tool chain | Dedicated NegotiationAgent |
| Weather | WeatherTools action group | Dedicated WeatherAgent |
| Context passing | Single session | `relayConversationHistory=TO_COLLABORATOR` |
| Latency | ~4–7s | ~15–20s (multi-agent overhead) |

---

## AWS Services Used

| Service | Purpose | Status |
|---------|---------|--------|
| Amazon Bedrock Agents | Multi-agent supervisor + 4 specialist agents | ✅ Active |
| Amazon Nova Pro | Foundation model for all 5 agents | ✅ Active |
| Amazon DynamoDB | Price time-series storage (5,177+ records) | ✅ Active |
| AWS Lambda | 3 serverless functions | ✅ Active |
| Amazon API Gateway | REST API (chat + prices) | ✅ Active |
| Amazon S3 | Static website + Lambda packages | ✅ Active |
| Amazon CloudFront | HTTPS CDN (enables Voice + GPS APIs) | ✅ Active |
| Amazon CloudWatch | Lambda logs + monitoring | ✅ Active |
| AWS IAM | Role-based access control | ✅ Active |
| LangFuse | LLM tracing + observability | ✅ Active |
| Amazon EventBridge | Daily ingestion schedule | ❌ **NOT YET CONFIGURED** |
| Bedrock Guardrails | Content filtering | ❌ **NOT YET CONFIGURED** |

---

## Bedrock Agent IDs (Quick Reference)

| Agent | ID | Alias ID | Role |
|-------|-----|----------|------|
| MandiMitra (Supervisor) | GDSWGCDJIX | TSTALIASID | Routes all queries |
| PriceIntelligenceAgent | CAEJ90IYS6 | 7YU2OMSRBQ | Price queries |
| SellAdvisoryAgent | CCYSN80MGN | HPMZYLQZU3 | Sell/hold advisory |
| NegotiationAgent | UZRXDX75NR | TFQ24DRCOW | Price briefs |
| WeatherAgent | XE43VNHO3T | YUSEVJPMWJ | Weather forecast |

Lambda uses: `BEDROCK_AGENT_ID=GDSWGCDJIX`, `BEDROCK_AGENT_ALIAS_ID=TSTALIASID`

---

## Quick Start

### Prerequisites
- Node.js 18+, Python 3.12+, AWS CLI v2, boto3
- AWS account with Bedrock access (Nova Pro enabled)
- data.gov.in API key (free at https://data.gov.in)

### 1. Frontend (runs in demo mode without backend)
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
# OR build for production:
npm run build && cp -r out/* <s3-bucket>/
```

### 2. Load Data
```bash
# Fetch last 7 days of historical data
pip install boto3 requests
python backend/scripts/fetch_7days.py

# Or trigger Lambda manually:
aws lambda invoke --function-name mandimitra-data-ingestion \
  --payload '{"days_back": 7}' output.json
```

### 3. Test the API
```bash
# Via CloudFront:
curl -X POST https://d2mtfau3fvs243.cloudfront.net/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "wheat ka bhav MP mein", "session_id": "test1", "language": "hi"}'
```

### 4. Recreate Multi-Agent Setup (if starting fresh)
```bash
python backend/scripts/setup_multi_agent_resume.py
```

---

## Project Structure

```
hackathon/
├── frontend/                 # Next.js 14 + Tailwind CSS PWA
│   └── app/
│       ├── components/       # Chat UI, Price Chart, Location Picker
│       ├── lib/              # API client, voice input
│       └── page.tsx          # Main chat application
├── backend/
│   ├── lambdas/
│   │   ├── chat_handler/     # Bedrock Agent invocation + LangFuse
│   │   ├── price_query/      # All action group tool implementations
│   │   ├── data_ingestion/   # Agmarknet → DynamoDB pipeline
│   │   └── shared/           # Constants, DB utils, weather utils
│   ├── agent_configs/
│   │   ├── orchestrator_prompt.txt      # Legacy single-agent prompt
│   │   └── sub_agents/                  # v2 multi-agent prompts
│   │       ├── supervisor_orchestrator_prompt.txt
│   │       ├── price_intelligence_agent_prompt.txt
│   │       ├── sell_advisory_agent_prompt.txt
│   │       ├── negotiation_agent_prompt.txt
│   │       └── weather_agent_prompt.txt
│   └── scripts/
│       ├── fetch_7days.py               # 7-day historical data fetcher
│       └── setup_multi_agent_resume.py  # Multi-agent setup script
├── docs/
│   ├── AWS_AUDIT.md          # Full AWS resource audit
│   ├── old_docs/             # v1 documentation (pre-multi-agent)
│   └── new_docs/             # v2 documentation (current)
├── multi_agent_ids.json      # Agent and alias IDs
├── ARCHITECTURE.md           # System architecture (updated)
├── FLOWS.md                  # User flow walkthroughs (updated)
├── WORKLOG.md                # Chronological dev log
└── README.md                 # This file
```

---

## Demo Flows

1. **Price Check (Hindi):** *"मध्य प्रदेश में गेहूं का भाव क्या है?"*
   → PriceIntelligenceAgent queries DynamoDB, returns 10 mandis with today's prices

2. **Best Mandi (GPS):** *"मेरे पास 20 क्विंटल सोयाबीन है, कहाँ बेचूं?"*
   → PriceIntelligenceAgent finds mandis within 50km, ranks by net realization (price minus transport)

3. **Smart Sell Advisory:** *"क्या अभी सोयाबीन बेचना चाहिए या रुकूं? 50 क्विंटल है इंदौर के पास।"*
   → SellAdvisoryAgent: shelf life + 30-day trend + weather risk → SELL/HOLD/SPLIT recommendation

4. **Negotiation Brief:** *"Price brief दो गेहूं का"*
   → NegotiationAgent: MSP + local price + best nearby mandi + trend → formatted shareable brief

5. **Weather:** *"अगले 5 दिन मौसम कैसा रहेगा?"*
   → WeatherAgent: Open-Meteo 5-day forecast + agricultural sell-timing advisory

---

## Impact

- **150M+** small farming households in India
- **₹50,000+** potential extra income per farmer per year (15–30% better price negotiation)
- **₹8.6/farmer/month** operating cost (100% serverless)
- Directly supports PM's **Doubling Farmers' Income** mission

---

## Data Source

Real-time commodity prices from **Agmarknet** via data.gov.in government API (Resource: `9ef84268-d588-465a-a308-a864a43d0070`). Covers 2000+ mandis, 300+ commodities, updated daily by 5:00 PM IST.

---

*Built with Amazon Bedrock Multi-Agent Collaboration, Amazon Nova Pro, and a lot of chai.*
