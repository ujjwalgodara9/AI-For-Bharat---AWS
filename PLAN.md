# MandiMitra — Prototype Phase Execution Plan

## Team: Robots | Lead: Ujjwal Godara | Hackathon: AI for Bharat (AWS × Hack2skill)

**Track:** AI for Retail, Commerce & Market Intelligence
**Phase:** Prototype Development (Round 2)
**Timeline:** Feb 25 – Mar 1, 2026 (submit by Mar 4 deadline, done early for buffer)

---

## 1. WHAT WE ARE BUILDING

**MandiMitra** is an AI-powered multi-agent copilot that gives Indian farmers real-time mandi price intelligence, sell/hold recommendations, and negotiation support — all in Hindi, through a conversational interface.

### The Core Problem

| Fact | Impact |
|------|--------|
| India has 7,000+ APMC mandis generating massive price data daily | Data exists but farmers can't access it |
| 86% of farmers are small/marginal (< 2 hectares) | No bargaining power, sell at whatever price offered |
| Farmers lose **15–30% of crop value** due to information asymmetry | ₹50,000–₹1,00,000 lost per farmer per year |
| Existing tools (Agmarknet, eNAM, Kisan Suvidha) are English-only raw dashboards | 70%+ farmers prefer Hindi, can't interpret data |
| No tool tells farmers WHERE to sell, WHEN to sell, or at WHAT PRICE to negotiate | Gap between data availability and actionable intelligence |

### Our Solution — Three AI Agents Working Together

```
 FARMER → "मेरे पास 50 क्विंटल सोयाबीन है, कहाँ बेचूं?"
           (I have 50 quintals of soyabean, where should I sell?)
                              │
                              ▼
                 ┌─────────────────────┐
                 │  ORCHESTRATOR AGENT │ ← Understands Hindi, classifies intent
                 │    (The Manager)    │    decides which specialist(s) to call
                 └─────────┬───────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
   ┌────────────┐  ┌─────────────┐  ┌────────────┐
   │   PRICE    │  │    SELL     │  │ NEGOTIATION│
   │   INTEL    │  │  ADVISORY   │  │    PREP    │
   │   AGENT    │  │   AGENT     │  │   AGENT    │
   └─────┬──────┘  └──────┬──────┘  └─────┬──────┘
         │                │               │
   Queries DynamoDB   Uses price data  Generates price
   for live prices    + weather +      brief farmer can
   across mandis,     perishability    show at mandi
   calculates         to recommend     for negotiation
   transport costs    SELL/HOLD/SPLIT
         │                │               │
         └────────────────┼───────────────┘
                          ▼
   RESPONSE → "देवास मंडी में बेचें (₹5,020/क्विंटल) — इंदौर से ₹320 ज़्यादा
               मिलेगा transport cost काटने के बाद भी। इस हफ्ते भाव 2% बढ़ रहे
               हैं। अगर 5 दिन रुक सकते हैं तो ₹4,920–₹5,050 तक जा सकता है।"
```

---

## 2. WHY THIS WINS

### Track Alignment (AI for Retail, Commerce & Market Intelligence)

The hackathon asks: *"Build an AI-powered solution that enhances decision-making, efficiency, or user experience across retail, commerce, and marketplace ecosystems."*

| Requirement | How MandiMitra Delivers |
|-------------|------------------------|
| **Enhances decision-making** | AI agents analyze 500+ mandis to recommend exactly WHERE and WHEN to sell |
| **Improves efficiency** | Replaces days of phone calls / travel with a 5-second AI query |
| **Better user experience** | Hindi conversational AI vs raw English data portals |
| **Retail/commerce context** | APMC mandis = India's largest agricultural retail marketplace |
| **Market intelligence** | Real-time price comparison, trend analysis, anomaly detection, forecasting |

### Cross-Track Bonus (Also fits Track 3: Rural Innovation)

MandiMitra also perfectly fits *"AI for Rural Innovation & Sustainable Systems"*:
- Targets 86% small farmers = the rural backbone of India
- Reduces food waste (sell at right time → less rot)
- Resource-efficient serverless architecture

### Competitive Edge — What Makes Us Different

| Factor | Our Advantage |
|--------|---------------|
| **Real Data** | Live government Agmarknet data, NOT mock/synthetic |
| **Multi-Agent AI** | True agentic orchestration (not a single-prompt chatbot) |
| **Hindi-First** | Built for Bharat, not just metro India |
| **AWS-Deep** | 10+ AWS services used meaningfully (not just EC2 + S3) |
| **LLM Observability** | LangFuse tracing dashboard showing agent reasoning chains |
| **Guardrails** | Bedrock Guardrails prevent price hallucination (responsible AI) |
| **Quantified Impact** | ₹16,000 extra income per farmer per transaction, provably |
| **Viable Cost** | ₹8.6 per farmer per month — deployable TODAY |
| **Agent Transparency** | UI shows "How MandiMitra Reasoned" step-by-step trace |

---

## 3. TECHNICAL ARCHITECTURE

### Full System Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                                │
│               Next.js 14 + Tailwind CSS (Mobile-First)               │
│          WhatsApp-style Chat │ Price Cards │ Voice Input              │
│                    Deployed on: AWS Amplify                           │
└────────────────────────────┬──────────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (REST)                             │
│         POST /chat  │  GET /prices  │  GET /mandis  │  POST /brief   │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     LAMBDA HANDLERS (Python)                          │
│                                                                       │
│  chat_handler.py ──→ Invokes Bedrock Agent Runtime                   │
│  prices_handler.py ──→ Direct DynamoDB queries                       │
│  mandis_handler.py ──→ DynamoDB + Haversine distance calc            │
│  brief_handler.py ──→ Invokes Negotiation Prep Agent                 │
│                                                                       │
│  + LangFuse tracing on every call                                    │
└────────────────────────────┬──────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│  BEDROCK AGENTS  │ │  DynamoDB    │ │  S3                  │
│                  │ │              │ │                      │
│  Orchestrator    │ │ MandiPrices  │ │ Raw CSVs (audit)     │
│  ├─ Price Intel  │ │ table with   │ │ Knowledge base docs  │
│  ├─ Sell Advisory│ │ GSI-1, GSI-2 │ │ Generated briefs     │
│  └─ Negotiation  │ │              │ │                      │
│                  │ │              │ │                      │
│  + Guardrails    │ │              │ │                      │
│  + Knowledge Base│ │              │ │                      │
└──────────────────┘ └──────────────┘ └──────────────────────┘
        │
        ▼
┌──────────────────┐
│  LangFuse Cloud  │
│  (Observability) │
│                  │
│ Traces, tokens,  │
│ latency, cost    │
│ per query        │
└──────────────────┘

DATA PIPELINE (runs daily at 6 AM IST):
┌──────────┐    ┌────────────┐    ┌──────────────┐    ┌──────────┐
│EventBridge│───→│ Lambda:    │───→│ Transform +  │───→│ DynamoDB │
│ Schedule  │    │ fetch from │    │ compute MA,  │    │ batch    │
│           │    │ data.gov.in│    │ anomalies    │    │ write    │
└──────────┘    └────────────┘    └──────────────┘    └──────────┘
```

### AWS Services Used (10+)

| # | Service | Purpose | Why |
|---|---------|---------|-----|
| 1 | **Amazon Bedrock (Nova Pro)** | LLM reasoning for orchestrator agent | Core AI engine |
| 2 | **Bedrock Agents** | Single orchestrator with 4 action groups, 12 functions | Agentic architecture |
| 3 | **Bedrock Guardrails** | Prompt-level guardrails (no price hallucination) | Responsible AI |
| 4 | **DynamoDB** | Price time-series (4,467 items, 2 GSIs, PAY_PER_REQUEST) | Fast queries, auto-scale |
| 5 | **Lambda** | 3 functions: chat, price-query, data-ingestion | Serverless, pay-per-use |
| 6 | **API Gateway** | REST API (skwsw8qk22) with CORS | Frontend-backend bridge |
| 7 | **S3** | Frontend hosting (static website) + deployment packages | Durable storage |
| 8 | **CloudWatch** | Lambda logs, metrics | Monitoring |
| 9 | **IAM** | MandiMitraLambdaRole + MandiMitraBedrockAgentRole | Security |
| 10 | **Open-Meteo API** | 5-day weather forecast + agricultural advisory | Weather intelligence (external) |

### Data Source: Government Agmarknet API

```
Endpoint: https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070
Access:   Free API key from data.gov.in
Fields:   state, district, market, commodity, variety, arrival_date,
          min_price, max_price, modal_price
Coverage: 2000+ mandis, 300+ commodities
Freshness: Daily updates
Rate Limit: 500 req/day (free tier — enough for daily batch)
```

### LLM Observability: LangFuse

Every LLM call is traced with:
- Input/output tokens and cost
- Latency breakdown (agent routing → tool calls → response)
- Agent reasoning chain visualization
- Session-level tracking (full conversation trace)
- Dashboard: success rate, avg latency, daily cost, token usage

---

## 4. HOW THE AGENTS WORK (Detailed)

### Agent 1: Price Intelligence Agent

**Role:** Fetch and analyze real-time mandi prices

**Tools it can call:**
| Tool | What It Does | Implementation |
|------|-------------|----------------|
| `query_mandi_prices` | Get prices for a commodity in a state/mandi | Lambda → DynamoDB query |
| `get_nearby_mandis` | Find mandis within X km radius | Lambda → DynamoDB + Haversine formula |
| `calculate_transport_cost` | Estimate ₹/quintal transport cost | Lambda → distance × ₹8/km/quintal |
| `get_msp` | Look up government MSP for commodity | Lambda → static S3 data |
| `get_price_trend` | 7/30-day moving average + trend direction | Lambda → DynamoDB analytics |

**Example flow:**
```
User: "इंदौर में सोयाबीन का भाव क्या है?"

Agent thinks: Need current soyabean price in Indore
Agent calls: query_mandi_prices(commodity="Soyabean", state="Madhya Pradesh", mandi="Indore")
Agent gets:  { modal_price: 4850, min: 4200, max: 5100, date: "2026-02-25" }
Agent calls: get_msp(commodity="Soyabean", year=2025)
Agent gets:  { msp: 4892 }
Agent calls: get_price_trend(commodity="Soyabean", mandi="Indore", days=7)
Agent gets:  { trend: "rising", change_pct: 2.3, ma_7d: 4780 }

Agent responds: "इंदौर मंडी में सोयाबीन का आज का भाव ₹4,850/क्विंटल है।
MSP ₹4,892 है — अभी MSP से थोड़ा कम चल रहा है।
पिछले 7 दिन में भाव 2.3% बढ़ा है। (स्रोत: Agmarknet, 25-Feb-2026)"
```

### Agent 2: Sell Advisory Agent

**Role:** Recommend SELL / HOLD / SPLIT based on multiple factors

**Decision Matrix:**
```
INPUTS:
  - current_price (from Price Intel Agent)
  - trend_direction: rising / falling / stable
  - perishability_index: 1-10 (preconfigured per commodity)
  - storage_available: yes / no
  - weather_forecast: adverse / normal
  - quantity: quintals

LOGIC:
  IF trend == rising AND perishability < 5 AND storage_available:
      → HOLD for {optimal_days} days. Expected: +{x}%

  ELIF trend == falling OR perishability >= 7:
      → SELL NOW at {best_mandi}. Prices declining.

  ELIF volatility == high:
      → SPLIT: Sell 50% now, hold 50%.

  ELSE:
      → SELL at {best_net_price_mandi}. Market stable.

OUTPUT always includes:
  - Recommendation with confidence %
  - Reasoning explanation
  - Alternative options
  - Risk factors
```

### Agent 3: Negotiation Prep Agent

**Role:** Generate a price brief farmers carry to the mandi

**Output format:**
```
╔══════════════════════════════════════════════════╗
║          MandiMitra Price Brief                  ║
║          सोयाबीन — 25 Feb 2026                   ║
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
║ Data Source: Agmarknet | Generated: 25-Feb-2026  ║
╚══════════════════════════════════════════════════╝
```

### Orchestrator: How Multi-Agent Routing Works

```
User Query → Orchestrator (Claude Sonnet)
  │
  ├─ Simple price query → Price Intel Agent ONLY
  │   "गेहूं का भाव?" → direct price lookup
  │
  ├─ Sell decision → Price Intel → Sell Advisory (sequential)
  │   "कहाँ बेचूं?" → first get prices, then advise
  │
  ├─ Negotiation → Price Intel → Negotiation Prep (sequential)
  │   "Price brief दो" → first get data, then format brief
  │
  └─ Complex query → Price Intel → Sell Advisory → Negotiation (all three)
      "50 क्विंटल सोयाबीन कहाँ बेचूं, brief भी चाहिए"
```

---

## 5. BUSINESS CASE & IMPACT

### Market Size

| Metric | Number |
|--------|--------|
| Small & marginal farming households in India | 150 million+ |
| Average annual income loss due to information asymmetry | ₹50,000 – ₹1,00,000 |
| Total addressable market (TAM) for price intelligence | ₹7.5 – 15 lakh crore |
| Farmers with smartphones | 50%+ and growing rapidly |
| Farmers comfortable with WhatsApp-style interfaces | 80%+ of smartphone owners |

### Unit Economics

```
Cost to serve 1 farmer for 1 month:
  Bedrock (Claude Haiku, ~50 queries): ₹4.00
  DynamoDB reads:                       ₹0.80
  Lambda compute:                       ₹0.20
  Other (S3, API GW, CloudWatch):       ₹3.60
  TOTAL:                                ₹8.60/farmer/month

Value created per farmer:
  Average extra income from better selling decisions: ₹50,000+/year
  ROI: ₹103/year cost → ₹50,000+ value = 485x return
```

### Revenue Model (Post-Hackathon Vision)

| Tier | Users | Price | Features |
|------|-------|-------|----------|
| Free | Individual farmers | ₹0 | Basic price check, 5 queries/day |
| Pro | Power farmers / traders | ₹99/month | Unlimited queries, sell advisory, alerts |
| FPO | Farmer Producer Orgs | ₹2,999/month | Dashboard, bulk analytics, API access |
| Enterprise | Commodity traders | ₹9,999/month | Full API, historical data, forecasting |

### Government Alignment

MandiMitra directly supports:
- **Doubling Farmers' Income** mission (PM's stated goal)
- **eNAM** (National Agriculture Market) — we complement, not compete
- **PM-KISAN** ecosystem — additional farmer empowerment tool
- **Digital India** — bringing data to rural India in local language

---

## 6. DAY-BY-DAY EXECUTION PLAN

### Day 1 — Feb 25 (Tuesday): Foundation + Data Pipeline

| Time | Owner | Task | Details |
|------|-------|------|---------|
| 9–10 AM | Lead | **AWS Account Setup** | Create IAM user with admin access, enable Bedrock models (Claude Sonnet 3.5, Haiku) in us-east-1, set billing alert at $80 |
| 10–11 AM | Lead | **data.gov.in Registration** | Register at data.gov.in, get API key, test Agmarknet endpoint with curl/Postman |
| 11–1 PM | Backend Dev | **Data Ingestion Lambda** | Python Lambda: fetch from data.gov.in API → parse JSON → transform to DynamoDB schema → batch write. Cover 15 commodities × 5 states |
| 11–1 PM | Frontend Dev | **Next.js Project Setup** | `npx create-next-app@14 mandimitra --typescript --tailwind` + folder structure + configure AWS Amplify for deployment |
| 2–3 PM | Backend Dev | **DynamoDB Table Creation** | Create `MandiPrices` table with PK/SK + GSI-1 (MANDI-INDEX) + GSI-2 (DATE-INDEX) |
| 2–3 PM | Frontend Dev | **UI Component Scaffold** | Create chat layout, message components, header, quick action buttons (empty shells) |
| 3–5 PM | Backend Dev | **Run Initial Data Load** | Execute Lambda manually, verify 5000+ records in DynamoDB, debug any parsing issues |
| 3–5 PM | Frontend Dev | **Chat Interface UI** | WhatsApp-style chat bubbles, input bar, send button, language toggle — no backend yet, use mock responses |
| 5–6 PM | Lead | **EventBridge Setup** | Create schedule rule: daily 6 AM IST → trigger data ingestion Lambda |
| 6–7 PM | Lead | **LangFuse Account** | Sign up at langfuse.com, get API keys, install SDK in backend |

**Day 1 Exit Criteria:**
- [x] DynamoDB has real Agmarknet price data (4,467 records loaded)
- [x] Next.js app runs locally with chat UI (mock data)
- [ ] Daily data pipeline scheduled (EventBridge not yet configured)
- [ ] LangFuse account ready (deferred — using Bedrock Agent traces instead)

---

### Day 2 — Feb 26 (Wednesday): Bedrock Agents + Backend APIs

| Time | Owner | Task | Details |
|------|-------|------|---------|
| 9–11 AM | Backend Dev | **Bedrock Agent: Price Intel** | Create agent in Bedrock console, write system prompt, add action group with OpenAPI spec for `query_mandi_prices`, `get_nearby_mandis` |
| 9–11 AM | Frontend Dev | **Price Comparison View** | Build mandi price cards: commodity name, price, mandi, distance, trend indicator, "Best" badge |
| 11–1 PM | Backend Dev | **Action Group Lambdas** | Write 4 Lambda functions: `query_mandi_prices`, `get_nearby_mandis`, `calculate_transport_cost`, `get_msp` — each queries DynamoDB |
| 11–1 PM | Frontend Dev | **Negotiation Brief Card** | Styled text card with MSP reference, fair price, trend, comparable prices, share button |
| 2–4 PM | Backend Dev | **Bedrock Agent: Sell Advisory** | Create agent, write decision-logic prompt, add action groups for trend analysis and recommendation |
| 2–4 PM | Frontend Dev | **Mobile Responsive Polish** | Test all views on 360px, fix spacing, large touch targets, high contrast |
| 4–5 PM | Backend Dev | **Bedrock Agent: Orchestrator** | Create supervisor agent that routes to sub-agents based on intent |
| 5–7 PM | Backend Dev | **API Gateway + Chat Lambda** | Create REST API: `POST /api/chat` → Lambda → invoke Bedrock Agent → return response + agent trace |
| 5–7 PM | Frontend Dev | **Connect Frontend to API** | Replace mock data with real API calls, handle loading states, errors |
| 7–8 PM | Both | **End-to-End Smoke Test** | Type a Hindi query in UI → see real response from Bedrock agents with real DynamoDB data |

**Day 2 Exit Criteria:**
- [x] Bedrock Agent (single orchestrator with 4 action groups, 12 functions) created and responding
- [x] API Gateway serving chat endpoint (skwsw8qk22 / prod)
- [x] Frontend connected to real backend (S3 static hosting)
- [x] Full Hindi query flow working end-to-end

---

### Day 3 — Feb 27 (Thursday): Integration + Observability + Voice

| Time | Owner | Task | Details |
|------|-------|------|---------|
| 9–11 AM | Backend Dev | **LangFuse Integration** | Add LangFuse tracing to chat Lambda — log every agent invocation, tool call, token count, latency |
| 9–11 AM | Frontend Dev | **Voice Input** | Add Web Speech API microphone button — speak in Hindi → transcribe → send as text query |
| 11–1 PM | Backend Dev | **Bedrock Guardrails** | Configure: factual grounding filter, block hallucinated prices, PII filter. Attach to all agents |
| 11–1 PM | Frontend Dev | **Agent Trace Panel** | Expandable "🔍 How MandiMitra Reasoned" section showing step-by-step agent logic from trace response |
| 2–4 PM | Backend Dev | **Bedrock Knowledge Base** | Upload MSP documents + APMC guidelines to S3 → create Knowledge Base → attach to agents for RAG |
| 2–4 PM | Frontend Dev | **Landing Page** | Hero section with MandiMitra logo, tagline, sample queries, "Start Chatting" CTA |
| 4–6 PM | Both | **Test All 5 User Flows** | Price check, best mandi, sell advisory, negotiation brief, weather query — in Hindi AND English |
| 6–7 PM | Both | **Bug Fixes + Prompt Tuning** | Fix Hindi response quality, handle edge cases, improve agent prompts |

**Day 3 Exit Criteria:**
- [ ] LangFuse dashboard showing real traces (deferred — using Bedrock Agent traces in UI)
- [x] Voice input working (Web Speech API: hi-IN, en-IN)
- [ ] Guardrails preventing hallucination (deferred — prompt-level guardrails in place)
- [x] All 5 user flows work in Hindi + English (price, mandi compare, sell, weather, browse)
- [x] Agent reasoning visible in UI (expandable trace panel in ChatBubble)

---

### Day 4 — Feb 28 (Friday): Deploy + Polish + Test

| Time | Owner | Task | Details |
|------|-------|------|---------|
| 9–10 AM | Lead | **AWS Amplify Deployment** | Connect GitHub → Amplify, configure env vars (API URL, keys), deploy frontend |
| 10–12 PM | Both | **Production Testing** | Test deployed URL on mobile phones (Android Chrome), fix any CORS/deployment issues |
| 12–1 PM | Frontend Dev | **UI Polish** | Add MandiMitra branding, color scheme (green/saffron for agriculture), smooth animations |
| 2–3 PM | Backend Dev | **Performance Optimization** | Optimize DynamoDB queries, add caching for frequent lookups, ensure < 5s response time |
| 3–4 PM | Frontend Dev | **Offline Cache** | localStorage cache for last-viewed prices with "Last updated X hours ago" badge |
| 4–5 PM | Frontend Dev | **Share on WhatsApp** | "Share" button on price brief that opens WhatsApp with pre-formatted text |
| 5–6 PM | Backend Dev | **Observability Dashboard Page** | Simple `/monitoring` page showing key LangFuse metrics (embed or screenshots) |
| 6–7 PM | Both | **Full Regression Test** | Every feature, every flow, on mobile + desktop, Hindi + English |

**Day 4 Exit Criteria:**
- [x] Live URL working on S3 static hosting (mandimitra-frontend-471112620976)
- [x] Mobile experience is smooth (PWA installable, service worker caching)
- [x] Response times acceptable (~5-15s for agent queries via Bedrock)
- [x] All features work on production (price, mandi compare, sell, weather, browse, voice)

---

### Day 5 — Mar 1 (Saturday): Demo Video + Documentation + Submit

| Time | Owner | Task | Details |
|------|-------|------|---------|
| 9–10 AM | Lead | **Script Demo Video** | Write exact script (see structure below) |
| 10–12 PM | Lead | **Record Demo Video** | Use OBS Studio or Loom. Record 2-3 takes, pick best one |
| 12–1 PM | Lead | **Upload Video** | YouTube (unlisted) or Google Drive (viewer access) |
| 2–3 PM | All | **Project Summary** | 1-page write-up: What we built, how it works, AWS services used, impact |
| 3–4 PM | All | **Problem Statement** | Crisp 200-word problem context |
| 4–5 PM | Lead | **Clean GitHub Repo** | Professional README with architecture diagram, screenshots, setup instructions, `.env.example`, remove secrets |
| 5–6 PM | Lead | **Submit on Dashboard** | Submit all 5 deliverables, test working link one final time |
| 6–7 PM | All | **Celebrate** | Buffer complete. Submission done 3 days early |

### Demo Video Structure (4–5 minutes)

```
[0:00–0:30]  THE PROBLEM
  "150 million small farmers in India lose 15-30% of their crop value
   because they don't know where prices are best. Current tools are
   English-only dashboards. No one tells them WHERE to sell, WHEN to
   sell, or HOW to negotiate."

[0:30–1:00]  THE SOLUTION
  "MandiMitra — an AI copilot with 3 specialist agents that work
   together to give farmers real-time market intelligence in Hindi."
  Show architecture diagram briefly.

[1:00–3:30]  LIVE DEMO (on phone screen)
  Flow 1: Voice query in Hindi → price response with source citation
  Flow 2: "कहाँ बेचूं?" → mandi comparison with transport costs
  Flow 3: Sell advisory → HOLD recommendation with reasoning
  Flow 4: Price brief → shareable negotiation card
  Show: Agent reasoning trace (the "How MandiMitra Reasoned" panel)
  Show: LangFuse dashboard (tracing, tokens, cost)

[3:30–4:00]  AWS ARCHITECTURE
  Show architecture diagram, highlight 10+ AWS services

[4:00–4:30]  IMPACT & SCALE
  "₹16,000 extra income per farmer per transaction"
  "₹8.6 per farmer per month to operate"
  "100% serverless — scales to millions"
  "Fits government's Doubling Farmers' Income mission"
```

---

## 7. WHAT WE NEED (Prerequisites & Credentials)

### Must Have Before Starting

| # | Item | Who Gets It | Time Needed |
|---|------|-------------|-------------|
| 1 | **AWS Account** with admin access | Lead | Have it / 10 min |
| 2 | **AWS Credits** ($100 from hackathon) | Lead (email from Hack2skill) | Wait for email |
| 3 | **data.gov.in API Key** | Anyone | 5 min — register at data.gov.in |
| 4 | **Bedrock Model Access** | Lead | Enable Claude Sonnet + Haiku in us-east-1 via AWS Console → Bedrock → Model Access |
| 5 | **LangFuse Account** | Backend dev | 2 min — sign up at langfuse.com (free tier) |
| 6 | **Node.js 18+** installed | Frontend dev | Already have / 5 min |
| 7 | **Python 3.11+** installed | Backend dev | Already have / 5 min |
| 8 | **AWS CLI** configured | All | 10 min |
| 9 | **GitHub repo** access for all team members | Lead | 5 min |

### Nice to Have

| # | Item | Purpose |
|---|------|---------|
| 1 | Mandi GPS coordinates dataset | For distance calculation (can use district-level approximations) |
| 2 | MSP rates PDF/data | For knowledge base RAG (can hard-code top 20 crops) |
| 3 | OBS Studio installed | For recording demo video |
| 4 | Android phone for testing | Mobile UX testing |

---

## 8. RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| data.gov.in API is down/slow | Pre-fetch and cache data; have CSV fallback with last 30 days of data |
| Bedrock Agents have cold start latency | Use provisioned concurrency on Lambda; show "thinking..." animation |
| Hindi responses are poor quality | Extensive prompt engineering; test with real Hindi queries; fallback to English |
| $100 AWS credits run out | Monitor daily with billing alert at $80; use Haiku (cheaper) for simple lookups |
| Working link goes down during evaluation | Use Amplify (auto-healing); set up CloudWatch alarm for 5xx errors |
| Team member unavailable | Each person's work is independent; code is on shared GitHub repo |
| Agent hallucination | Bedrock Guardrails + always cite data source + timestamps |

---

## 9. SUBMISSION CHECKLIST

| # | Deliverable | Format | Status |
|---|------------|--------|--------|
| 1 | **Project Summary** | 1-page write-up on dashboard | ⬜ |
| 2 | **Demo Video** | YouTube/Drive link (4-5 min) | ⬜ |
| 3 | **GitHub Repository** | Public/private repo link | ✅ (main branch, 2 commits) |
| 4 | **Working Link** | S3 Static Website URL | ✅ (mandimitra-frontend-471112620976) |
| 5 | **Problem Statement** | Clear context on dashboard | ⬜ |

---

## 10. POST-HACKATHON ROADMAP (Mention in Demo)

Show judges we've thought beyond the prototype:

1. **WhatsApp Bot** — Zero-download reach via Meta Business API
2. **Crop Photo Grading** — Upload photo → AI quality grade → price adjustment
3. **FPO Dashboard** — Bulk analytics for farmer collectives
4. **eNAM Integration** — Direct online mandi trading
5. **Multi-Language** — Tamil, Telugu, Marathi, Punjabi, Gujarati
6. **Satellite Data** — NDVI crop health → yield-adjusted forecasting
7. **Credit Linkage** — Kisan Credit Card integration

---

*This document is the single source of truth for MandiMitra prototype development. Update it as we progress.*

*Let's build something that actually helps Indian farmers. 🌾*
