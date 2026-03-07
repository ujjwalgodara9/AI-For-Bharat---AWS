# Requirements - MandiMitra: Agentic Market Intelligence Copilot for Agri-Commerce

## Project Overview

**MandiMitra** is an AI-powered multi-agent market intelligence system that empowers Indian farmers, FPOs (Farmer Producer Organizations), and small traders with real-time mandi price intelligence, demand forecasting, and actionable sell-side recommendations — delivered conversationally in Hindi and regional languages.

### Problem Statement (Track 1: AI for Retail, Commerce & Market Intelligence)

India has 7,000+ APMC mandis generating massive commodity price data, yet small farmers and local traders cannot access or interpret this data. They sell at whatever price the local intermediary (arthiya) offers, losing 15-30% of potential value due to **information asymmetry**. Current tools are either English-only dashboards, raw government portals, or simple SMS alerts that lack contextual intelligence.

**Key Pain Points:**
- Farmers have no way to compare prices across nearby mandis before transporting produce
- No forecasting — farmers cannot time their sales optimally
- Language barrier — most tools are English-only; 70%+ of farmers prefer Hindi/regional languages
- No negotiation support — farmers enter mandis without price benchmarks
- FPOs lack data-driven procurement and selling strategies

### Target Users

1. **Small & Marginal Farmers** (< 2 hectares) — 86% of Indian farming households
2. **FPO Managers** — managing collective procurement and sales for 500-1000+ farmers
3. **Local Traders / Commission Agents** — seeking price arbitrage across mandis
4. **Agricultural Extension Workers** — advising farmers on market conditions

---

## Functional Requirements

### FR-1: Real-Time Mandi Price Ingestion & Storage

**Description:** The system shall ingest real-time and historical commodity price data from government data sources (Agmarknet/data.gov.in) and store it in a structured, queryable format.

**Acceptance Criteria:**
- System pulls daily price data for 100+ commodities across 500+ mandis
- Data includes: commodity name, variety, min price, max price, modal price, mandi name, state, date
- Historical data for at least 12 months is available for trend analysis
- Data refresh frequency: at least once daily (scheduled via AWS Lambda + EventBridge)
- Data stored in Amazon DynamoDB with time-series optimized schema (partition key: commodity#state, sort key: date#mandi)

### FR-2: Multi-Lingual Conversational Interface

**Description:** Users shall interact with MandiMitra through a chat-based conversational interface that supports Hindi, English, and Hindi-English code-mixing.

**Acceptance Criteria:**
- System understands queries in Hindi (Devanagari), English, and code-mixed input (e.g., "meri soyabean ka rate kya hai Indore mandi mein?")
- Responses are generated in the user's preferred language
- Voice input support (text-to-speech / speech-to-text) for low-literacy users
- Interface works on mobile web browsers (responsive design)
- Conversation history maintained within a session

### FR-3: Price Intelligence Agent

**Description:** An AI agent that analyzes current and historical mandi prices to provide intelligent market insights.

**Acceptance Criteria:**
- Given a commodity and location, returns: current price, 7/30/90-day trend, price comparison across nearest 5-10 mandis within configurable radius (default 100km)
- Detects price anomalies (e.g., "Tomato prices in Nashik are 40% below 30-day average — likely oversupply")
- Provides short-term price forecasts (3-7 day horizon) using historical patterns, seasonal trends, and weather correlation
- Calculates transportation-cost-adjusted net realization across mandis
- Generates MSP (Minimum Support Price) comparison when applicable

### FR-4: Sell Advisory Agent

**Description:** An AI agent that provides personalized sell/hold recommendations based on price intelligence, storage conditions, and market trends.

**Acceptance Criteria:**
- Given commodity, quantity, location, and storage availability — recommends: sell now, hold for X days, or transport to alternate mandi
- Factors in: current price trends, seasonal patterns, perishability of commodity, estimated storage cost/loss, transportation costs
- Provides confidence level with each recommendation
- Supports follow-up questions ("what if I hold for 2 more weeks?")

### FR-5: Negotiation Prep Agent

**Description:** Generates a "price brief" document that farmers can reference during mandi negotiations.

**Acceptance Criteria:**
- Generates a concise one-page brief containing: commodity current price range across mandis, MSP reference, quality-grade adjusted fair price, 7-day price trend chart description, comparable recent transactions
- Available as downloadable PDF or shareable WhatsApp-friendly text
- Includes timestamp and data source attribution for credibility
- Available in Hindi and English

### FR-6: Weather-Market Correlation Engine

**Description:** Integrates weather data to enhance price forecasting and advisory intelligence.

**Acceptance Criteria:**
- Ingests weather forecast data from IMD (India Meteorological Department) public APIs
- Correlates weather events (heavy rain, drought, heatwave) with historical price impacts for specific commodities
- Proactively alerts users: "Heavy rain forecast in Vidarbha next week — soyabean prices may spike by 5-8% based on historical patterns"
- Weather data refreshed daily

### FR-7: Agent Orchestration & Tool Use

**Description:** Multiple AI agents are orchestrated through a central coordinator using Amazon Bedrock Agents with tool-use capabilities.

**Acceptance Criteria:**
- Central orchestrator agent receives user query, determines intent, and routes to appropriate specialist agent(s)
- Agents can invoke tools: Agmarknet API, Weather API, DynamoDB queries, price calculation functions
- Multi-step reasoning: complex queries trigger sequential agent calls (e.g., "Where should I sell my wheat?" → Price Agent → Weather Agent → Sell Advisory Agent)
- Agent execution traces are logged for debugging and transparency
- Guardrails prevent hallucinated price data — agents must cite data source and timestamp

---

## Non-Functional Requirements

### NFR-1: Performance
- Query response time: < 5 seconds for simple price lookups, < 15 seconds for complex multi-agent advisory
- System supports 1,000 concurrent users
- Data ingestion pipeline completes daily refresh within 30 minutes

### NFR-2: Scalability
- Architecture supports horizontal scaling via AWS Lambda and DynamoDB auto-scaling
- Can be extended to cover all 7,000+ mandis and 300+ commodities
- New regional languages can be added without architectural changes

### NFR-3: Reliability & Availability
- 99.5% uptime target
- Graceful degradation: if weather API is unavailable, price intelligence still functions
- Data staleness indicator: system warns users if price data is > 24 hours old

### NFR-4: Security & Privacy
- No personally identifiable farmer data stored
- API endpoints secured with AWS IAM and API Gateway
- All data in transit encrypted via TLS 1.2+

### NFR-5: Cost Efficiency
- Estimated monthly AWS cost < ₹15,000 for MVP (1,000 DAU)
- Uses Bedrock's pay-per-token pricing to minimize LLM costs
- DynamoDB on-demand capacity mode for cost optimization during low-traffic periods

### NFR-6: Accessibility
- Mobile-first responsive design
- Works on 3G/4G connections (< 500KB initial page load)
- High-contrast UI for outdoor readability
- Large touch targets for users unfamiliar with smartphone interfaces

---

## Data Sources

| Source | Data | Access | Refresh |
|--------|------|--------|---------|
| Agmarknet (data.gov.in) | Mandi prices, arrivals | Public API / CSV | Daily |
| IMD | Weather forecasts | Public API | Daily |
| Ministry of Agriculture | MSP rates | Public / Static | Seasonal |
| Google Maps API | Distance/transport cost | API (free tier) | On-demand |

---

## User Stories

### US-1: Farmer Price Check
**As a** small wheat farmer in Madhya Pradesh,
**I want to** ask "गेहूं का भाव क्या चल रहा है?" in Hindi,
**So that** I know the current wheat price in my nearest mandis before deciding where to sell.

### US-2: Best Mandi Selection
**As a** soybean farmer with 20 quintals ready to sell,
**I want to** know which mandi within 80km gives me the best net price (after transport costs),
**So that** I maximize my earnings.

### US-3: Sell Timing Decision
**As a** potato farmer with cold storage access,
**I want to** understand if I should sell now or hold for 2-3 weeks,
**So that** I can time the market and avoid selling during a price dip.

### US-4: FPO Bulk Planning
**As an** FPO manager aggregating onions from 200 farmers,
**I want to** see demand-supply trends across mandis and forecasted prices,
**So that** I can plan bulk transportation and negotiate better rates.

### US-5: Negotiation at Mandi
**As a** farmer entering Kota mandi to sell mustard,
**I want** a price brief showing comparable prices in nearby mandis and MSP reference,
**So that** I have leverage to negotiate a fair price with the trader.

---

## AWS Services Mapping

| Component | AWS Service | Purpose |
|-----------|-------------|---------|
| LLM / Reasoning | Amazon Bedrock (Nova Pro) | Agent reasoning, NLU, response generation |
| Agent Orchestration | Amazon Bedrock Agents | Multi-agent coordination, tool use |
| Knowledge Base | Amazon Bedrock Knowledge Bases | RAG over agricultural documents, policies |
| Data Storage | Amazon DynamoDB | Price time-series, user sessions |
| File Storage | Amazon S3 | Raw data files, generated PDFs |
| Compute | AWS Lambda | Data ingestion, API handlers |
| Scheduling | Amazon EventBridge | Daily data refresh triggers |
| API Layer | Amazon API Gateway | REST API for frontend |
| CDN / HTTPS | Amazon CloudFront | HTTPS delivery for S3 frontend (enables Voice + GPS) |
| Monitoring | Amazon CloudWatch | Logs, metrics, alarms |
| IDE / Dev | Kiro | Requirements & design generation |

---

## Milestones

| Phase | Deliverable | Timeline |
|-------|-------------|----------|
| Phase 1 | Data pipeline (Agmarknet → DynamoDB) + basic price lookup agent | Week 1 |
| Phase 2 | Multi-agent orchestration (Price + Advisory + Negotiation agents) | Week 2 |
| Phase 3 | Hindi language support + conversational UI | Week 3 |
| Phase 4 | Weather integration + forecasting + testing | Week 4 |
| Phase 5 | Demo video + documentation + submission | Week 5 |
