# MandiMitra - Complete Project Audit (March 6, 2026)

## Table of Contents
1. [AWS Services Used](#1-aws-services-used)
2. [Bedrock Agents (Deployed)](#2-bedrock-agents-deployed)
3. [Agent Prompts](#3-agent-prompts)
4. [Lambda Functions](#4-lambda-functions)
5. [Deployment Status (Local vs Deployed)](#5-deployment-status-local-vs-deployed)
6. [DynamoDB: Schema, Data & Access Patterns](#6-dynamodb-schema-data--access-patterns)
7. [API Gateway & CloudFront](#7-api-gateway--cloudfront)
8. [EventBridge & CloudWatch](#8-eventbridge--cloudwatch)
9. [Guardrails](#9-guardrails)
10. [Frontend](#10-frontend)
11. [Data Ingestion Pipeline](#11-data-ingestion-pipeline)
12. [Model Comparison: Nova Pro vs Claude 3.7 Sonnet](#12-model-comparison-nova-pro-vs-claude-37-sonnet)
13. [DynamoDB Tools & Data Access Patterns](#13-dynamodb-tools--data-access-patterns)
14. [PPT Promises vs Implementation Status](#14-ppt-promises-vs-implementation-status)
15. [Gaps & Recommendations](#15-gaps--recommendations)

---

## 1. AWS Services Used

| Service | Purpose | Resource ID/Name |
|---------|---------|-----------------|
| Amazon Bedrock Agents | Multi-agent AI orchestration (SUPERVISOR mode) | 5 agents (see below) |
| Amazon Bedrock (Nova Pro v1) | Foundation model for all agents | `amazon.nova-pro-v1:0` |
| Amazon Bedrock Guardrails | Content filtering & safety | `snlfs5xjb61l` |
| AWS Lambda | 3 serverless functions (chat, price-query, data-ingestion) | See below |
| Amazon DynamoDB | Price time-series storage | `MandiMitraPrices` |
| Amazon API Gateway | REST API (chat + prices) | `skwsw8qk22` (MandiMitraAPI) |
| Amazon CloudFront | CDN for frontend | `d2mtfau3fvs243.cloudfront.net` (E1FOPZ17Q7P6CF) |
| Amazon S3 | Frontend hosting + data audit logs | `mandimitra-frontend-471112620976`, `mandimitra-data` |
| Amazon EventBridge | Daily ingestion scheduler | `mandimitra-daily-ingestion` |
| Amazon CloudWatch | 7 alarms for monitoring | See below |

**NOT Used (promised in PPT but not implemented):**
- Amazon Bedrock Knowledge Bases (RAG)
- Amazon OpenSearch Serverless (vector store)
- Amazon Titan Embeddings
- AWS Amplify Hosting (using S3+CloudFront instead)
- Kiro IDE

---

## 2. Bedrock Agents (Deployed)

All agents are PREPARED and use **amazon.nova-pro-v1:0** model.

| Agent | ID | Role | Alias (Prod) | Alias Points To |
|-------|----|----|-------------|-----------------|
| MandiMitra (Supervisor) | GDSWGCDJIX | SUPERVISOR - routes queries to sub-agents | `prod` (BM6JROSWME) → v3, `TSTALIASID` → DRAFT | v3 |
| PriceIntelligence | CAEJ90IYS6 | Price lookups, nearby mandis, trends, MSP | `live` (7YU2OMSRBQ) → v3 | v3 |
| SellAdvisory | CCYSN80MGN | Sell/hold/split recommendations | `live` (HPMZYLQZU3) → v3 | v3 |
| Negotiation | UZRXDX75NR | Price briefs for mandi negotiation | `live` (TFQ24DRCOW) → v3 | v3 |
| Weather | XE43VNHO3T | 5-day forecast + agricultural advisory | `live` (YUSEVJPMWJ) → v2 | v2 |

### Chat Handler Configuration
- `BEDROCK_AGENT_ID` = `GDSWGCDJIX`
- `BEDROCK_AGENT_ALIAS_ID` = `TSTALIASID` (points to DRAFT, NOT prod alias)

### Action Groups on Supervisor (GDSWGCDJIX)
| Action Group | Name | Description |
|-------------|------|-------------|
| KYYMTPXMWY | BrowseTools | List mandis, commodities, states |
| ASGXYH4STL | MandiTools | Mandi profile and all-prices |
| REC9WFZCNW | PriceIntelligenceTools | Price queries, nearby mandis, sell recommendation |
| MIYZDHRQ9H | WeatherTools | Weather advisory |

### Action Groups on PriceIntelligence (CAEJ90IYS6)
| Action Group | Name |
|-------------|------|
| CEJXKNQW30 | PriceIntelligenceTools |

---

## 3. Agent Prompts

All 5 agent prompts are **deployed and match local files** (1-byte trailing newline diff only).

| Agent | Local File | Deployed Length | Status |
|-------|-----------|----------------|--------|
| Supervisor | `backend/agent_configs/orchestrator_prompt.txt` | 9759 chars | DEPLOYED |
| PriceIntelligence | `backend/agent_configs/price_intel_prompt.txt` | 4671 chars | DEPLOYED |
| SellAdvisory | `backend/agent_configs/sell_advisory_prompt.txt` | 4732 chars | DEPLOYED |
| Negotiation | `backend/agent_configs/negotiation_prep_prompt.txt` | 5388 chars | DEPLOYED |
| Weather | `backend/agent_configs/sub_agents/weather_agent_prompt.txt` | 2288 chars | DEPLOYED |

Key prompt features:
- Language detection (Hindi, Hinglish, English)
- Query refinement with spelling correction
- Location resolution priority (chat > GPS > context > ask)
- City vs Mandi vs State disambiguation
- Standard response format templates
- Data freshness rules (Agmarknet finalizes by 5 PM IST)

---

## 4. Lambda Functions

| Function | Runtime | Timeout | Memory | Last Deployed |
|----------|---------|---------|--------|--------------|
| mandimitra-chat | Python 3.12 | 29s | 512 MB | 2026-03-06 02:26 UTC |
| mandimitra-price-query | Python 3.12 | 30s | 256 MB | 2026-03-04 15:52 UTC |
| mandimitra-data-ingestion | Python 3.12 | 900s (15min) | 512 MB | 2026-03-05 13:02 UTC |

### Chat Handler (`mandimitra-chat`)
- Invokes Bedrock Agent (Supervisor)
- Auto-detects language style (Hindi/Hinglish/English) from message content
- Augments message with language instruction + GPS context
- Extracts `<answer>` tags from model traces as fallback
- `clean_agent_response()` strips leaked XML tags from sub-agents
- Retry without traces if response is empty
- LangFuse tracing (optional, degrades gracefully)

### Price Query (`mandimitra-price-query`)
- Dual-purpose: API Gateway direct calls + Bedrock Agent action group handler
- 13 functions: query_mandi_prices, get_nearby_mandis, get_price_trend, get_msp, calculate_transport_cost, get_all_prices_at_mandi, list_available_commodities, list_available_mandis, list_available_states, get_weather_advisory, get_sell_recommendation, get_mandi_profile
- Special `_list` endpoint for frontend commodity fetching
- Uses geocoding.py for coordinate resolution
- Parameter validation with `agent_error_response()` helper

### Data Ingestion (`mandimitra-data-ingestion`)
- Fetches from data.gov.in Agmarknet API
- 20 commodities x 14 states
- Rate limit handling with exponential backoff (429 retry)
- Deduplication by PK+SK in batch_writer
- Data validation: modal in min-max range, realistic prices (1-500000), no future dates
- SK includes variety: `{date}#{market}#{variety}`
- Audit logs to S3

---

## 5. Deployment Status (Local vs Deployed)

### Lambda Code Match

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| **chat handler** | handler.py | MATCH | Latest code deployed |
| **price-query** handler.py | handler.py | **MISMATCH** | Local has geocoding import, validation improvements |
| **price-query** shared/dynamodb_utils.py | shared/dynamodb_utils.py | **MISMATCH** | Local has updated import (COMMODITY_TRANSLATIONS) |
| **price-query** shared/weather_utils.py | shared/weather_utils.py | **MISMATCH** | Local has geocoding import |
| **price-query** shared/geocoding.py | NOT IN ZIP | **MISSING** | New file not deployed! |
| **price-query** shared/constants.py | shared/constants.py | MATCH | |
| **data-ingestion** handler.py | handler.py | MATCH | Latest code deployed |

### Frontend Deployment

| Component | Status | Last Deployed | Notes |
|-----------|--------|--------------|-------|
| S3 Frontend | **OUTDATED** | 2026-03-01 | Latest git pull has ChatBubble TTS, voice.ts, language field changes from March 6 |

### Agent Prompts

| Agent | Status |
|-------|--------|
| All 5 prompts | DEPLOYED (match local) |

### CRITICAL ISSUES:
1. **`mandimitra-price-query` Lambda is NOT deployed** - Missing `geocoding.py`, handler/utils/weather mismatches. Functions using `get_coordinates()` will FAIL.
2. **Frontend not deployed** - Voice TTS, language detection in bubbles, ChatBubble improvements are NOT live.
3. **Chat handler uses TSTALIASID (DRAFT)** not the prod alias (BM6JROSWME). This is OK for development but means changes to DRAFT agent take effect immediately without version control.

---

## 6. DynamoDB: Schema, Data & Access Patterns

### Table: MandiMitraPrices
- **Billing**: PAY_PER_REQUEST (on-demand)
- **Total Items**: 8,874
- **Size**: ~2.2 MB
- **Status**: ACTIVE

### Key Schema
| Attribute | Type | Example |
|-----------|------|---------|
| PK (Partition Key) | String | `WHEAT#MADHYA_PRADESH` |
| SK (Sort Key) | String | `2026-03-05#INDORE#BOLD` (date#mandi#variety) |

### Global Secondary Indexes (GSIs)
| Index | Partition Key | Sort Key | Projection | Use Case |
|-------|--------------|----------|-----------|----------|
| DATE-INDEX | arrival_date | PK | ALL | Query prices by date across commodities |
| MANDI-INDEX | mandi_name | date_commodity | ALL | Query all commodities at a specific mandi |

### Item Attributes
```
PK, SK, commodity, state, district, mandi_name, arrival_date, variety,
min_price, max_price, modal_price, date_commodity, ingested_at, arrivals_tonnes (optional)
```

### Data Distribution
- **205 unique commodities** in DB (Agmarknet returns ALL commodities at queried mandis, not just our 20)
- **24 states** covered (more than the 14 configured — data from historical fetch scripts)
- **Date range**: 2006-08-06 to 2026-03-05 (261 unique dates, from 30-day fetch)
- **Top commodities by record count**: Potato (718), Tomato (710), Onion (669), Wheat (482), Red Chilli (375)
- **Top states by record count**: Tamil Nadu (1086), Gujarat (1035), Madhya Pradesh (966)

---

## 7. API Gateway & CloudFront

### API Gateway (MandiMitraAPI - skwsw8qk22)
- Type: REGIONAL REST API
- Security: TLS 1.0

| Route | Method | Lambda Target |
|-------|--------|--------------|
| `/api/chat` | POST | mandimitra-chat |
| `/api/prices/{commodity}` | GET | mandimitra-price-query |

Special routes:
- `GET /api/prices/_list?state=X` — Returns available commodities with Hindi translations

### CloudFront (d2mtfau3fvs243.cloudfront.net)
- Distribution ID: E1FOPZ17Q7P6CF
- Status: Deployed
- Origin: `mandimitra-frontend-471112620976.s3-website-us-east-1.amazonaws.com`
- No additional cache behaviors (API calls go directly to API Gateway, not through CloudFront)

---

## 8. EventBridge & CloudWatch

### EventBridge Rule
- **Name**: mandimitra-daily-ingestion
- **Schedule**: `cron(0 16 * * ? *)` = 9:30 PM IST daily
- **State**: ENABLED
- **Target**: mandimitra-data-ingestion Lambda

### CloudWatch Alarms (7 total, all OK)
| Alarm | Metric | Namespace |
|-------|--------|-----------|
| MandiMitra-ChatHandler-Errors | Errors | AWS/Lambda |
| MandiMitra-ChatHandler-HighDuration | Duration | AWS/Lambda |
| MandiMitra-ChatHandler-Throttles | Throttles | AWS/Lambda |
| MandiMitra-DataIngestion-Errors | Errors | AWS/Lambda |
| MandiMitra-PriceQuery-Errors | Errors | AWS/Lambda |
| MandiMitra-DynamoDB-SystemErrors | SystemErrors | AWS/DynamoDB |
| MandiMitra-DynamoDB-ReadThrottles | ReadThrottleEvents | AWS/DynamoDB |

---

## 9. Guardrails

### MandiMitraGuardrail (snlfs5xjb61l)
- **Status**: READY (DRAFT version)
- **Associated with**: Supervisor Agent (GDSWGCDJIX)

| Policy | Configuration |
|--------|--------------|
| Content Filter | VIOLENCE (HIGH), HATE (HIGH), SEXUAL (HIGH), MISCONDUCT (MEDIUM), INSULTS (LOW), PROMPT_ATTACK (MEDIUM input only) |
| Topic Deny | "FinancialInvestment" - blocks stock/futures/investment queries |
| Word Policy | Blocks "guaranteed profit" + profanity |
| Off-Topic Filter | REMOVED (was blocking valid agricultural queries) |

---

## 10. Frontend

### Tech Stack
- Next.js 14 (React 18, SSR/SSG)
- Tailwind CSS (mobile-first)
- Hosted on S3 + CloudFront (NOT Amplify)

### Key Components
| Component | File | Purpose |
|-----------|------|---------|
| Home/Chat Page | `frontend/app/page.tsx` | Main chat interface, session management, API calls |
| ChatHeader | `components/ChatHeader.tsx` | Language toggle, location button |
| ChatBubble | `components/ChatBubble.tsx` | Message display, WhatsApp share, TTS (new), copy, agent trace |
| ChatInput | `components/ChatInput.tsx` | Text input + voice input |
| QuickActions | `components/QuickActions.tsx` | Quick crop query buttons (dynamic from API) |
| WelcomeScreen | `components/WelcomeScreen.tsx` | Onboarding screen with crop suggestions |
| LocationPicker | `components/LocationPicker.tsx` | GPS + manual location selection |
| PriceChart | `components/PriceChart.tsx` | Mini price comparison chart |
| Voice (lib) | `lib/voice.ts` | Web Speech API for STT + TTS |
| API client (lib) | `lib/api.ts` | Type definitions + API helpers |

### New Features (in code but NOT deployed):
- **Text-to-Speech (TTS)**: Read bot responses aloud (Hindi/English voices)
- **Language field per message**: Each message carries its detected language
- **ChatBubble TTS button**: Speaker icon next to bot messages

### Dynamic Crop Lists
- When user selects location, frontend calls `GET /api/prices/_list?state=X`
- Returns commodities available in DynamoDB for that state with Hindi translations
- Falls back to hardcoded list if API fails

---

## 11. Data Ingestion Pipeline

### Configuration
- **20 commodities**: Wheat, Soyabean, Onion, Tomato, Potato, Mustard, Chana, Maize, Cotton, Rice, Garlic, Moong, Urad, Bajra, Jowar, Groundnut, Turmeric, Red Chilli, Coriander, Cumin
- **14 states**: MP, Rajasthan, Maharashtra, UP, Gujarat, Karnataka, Punjab, Haryana, AP, Telangana, TN, Bihar, WB, Chhattisgarh
- **API**: data.gov.in Agmarknet (resource: 9ef84268-d588-465a-a308-a864a43d0070)
- **Rate limiting**: 0.5s delay between requests + exponential backoff on 429 (3s * 2^attempt, up to 5 retries)
- **Data validation**: modal in min-max range (5% tolerance), price 1-500000, no future dates
- **Deduplication**: PK+SK pair tracked in seen_keys set

### Known Behavior
- Agmarknet returns ALL commodities at queried mandis, not just our 20. That's why DB has 205 commodities.
- Historical data from `fetch_30days.py` covers more states (21) and commodities (28) than daily ingestion.

---

## 12. Model Comparison: Nova Pro vs Claude 3.7 Sonnet

Currently all agents use **amazon.nova-pro-v1:0**. You mentioned having Claude 3.7 Sonnet authorized. Here's the comparison:

| Feature | Amazon Nova Pro | Claude 3.7 Sonnet |
|---------|----------------|-------------------|
| **Provider** | Amazon (first-party) | Anthropic (third-party on Bedrock) |
| **Speed** | Fast (optimized for Bedrock) | Moderate (slightly slower) |
| **Cost** | Lower (Amazon tier pricing) | Higher (~2-3x Nova Pro) |
| **Reasoning Quality** | Good for structured tasks | Excellent - significantly better at complex reasoning |
| **Hindi/Hinglish** | Decent but can miss nuances | Better multilingual understanding |
| **Tool Use** | Good (native Bedrock integration) | Excellent tool use, better parameter extraction |
| **Following Instructions** | Sometimes ignores complex prompt rules | Much better at following structured prompts |
| **Context Window** | 300K tokens | 200K tokens |
| **Known Issues** | Can return "Hi" or minimal responses for complex queries, sometimes ignores response format | More consistent output formatting |
| **Best For** | Simple price lookups, weather queries | Sell advisory, negotiation briefs, complex multi-step reasoning |

### Recommendation
**Switch SellAdvisory and Negotiation agents to Claude 3.7 Sonnet** (`anthropic.claude-3-5-sonnet-20241022-v2:0` or the latest Sonnet model ID on Bedrock). These are the two agents where the "Hi" bug and poor reasoning are most impactful. Keep Weather and simple PriceIntelligence on Nova Pro for cost efficiency.

You could also consider a **hybrid approach**:
- **Supervisor**: Claude 3.7 Sonnet (better routing/reasoning)
- **PriceIntelligence**: Nova Pro (simple tool calls, cost-efficient)
- **SellAdvisory**: Claude 3.7 Sonnet (complex reasoning needed)
- **Negotiation**: Claude 3.7 Sonnet (structured output quality matters)
- **Weather**: Nova Pro (simple tool call + format)

---

## 13. DynamoDB Tools & Data Access Patterns

### All DynamoDB Access Functions (in `dynamodb_utils.py`)

| Function | Access Pattern | Index Used | Fallbacks |
|----------|---------------|-----------|-----------|
| `query_prices(commodity, state, mandi?, days?)` | PK query + SK range | Main table | APMC suffix variants, no-date scan, all-data fallback |
| `query_mandi_prices(mandi, days?)` | Mandi name + date range | MANDI-INDEX | APMC suffix, district scan, partial name scan |
| `get_nearby_mandis(lat, lon, radius, commodity?)` | In-memory coordinate scan | None (MANDI_COORDINATES dict) | Fetches prices per mandi via query_mandi_prices |
| `get_price_trend(commodity, state, mandi, days?)` | Uses query_prices internally | Main table | Linear regression, volatility calc |
| `get_msp(commodity)` | In-memory lookup | None (MSP_RATES dict) | Case-insensitive match |
| `get_sell_recommendation_data(...)` | Combines nearby + prices + trend + MSP + season + weather | Multiple | Comprehensive 14-step analysis |
| `list_available_commodities(state?)` | Full table scan with projection | None | Paginated scan |
| `list_available_mandis(state?)` | Full table scan with projection | None | Paginated scan |
| `list_available_states()` | Full table scan with projection | None | Paginated scan |
| `list_commodities_with_translations(state?)` | Uses list_available_commodities | None | Filters through COMMODITY_TRANSLATIONS |
| `get_mandi_profile(mandi, days?)` | Mandi name query | MANDI-INDEX | APMC suffix, district/partial scan |
| `calculate_net_realization(price, distance, qty?)` | Pure computation | None | - |
| `haversine_distance(lat1, lon1, lat2, lon2)` | Pure computation | None | - |

### How Data Can Be Queried

1. **By Commodity + State** (most common): `PK = "WHEAT#MADHYA_PRADESH"` with SK date range
2. **By Mandi** (MANDI-INDEX GSI): `mandi_name = "INDORE"` with date_commodity range
3. **By Date** (DATE-INDEX GSI): `arrival_date = "2026-03-05"` with PK range
4. **By GPS** (in-memory): Haversine distance from MANDI_COORDINATES dict (60+ mandis)
5. **Full scan**: For listing all commodities/mandis/states (paginated)

### Data Freshness
- Daily ingestion at 9:30 PM IST (EventBridge)
- Agmarknet data finalized by 5 PM IST
- `data_freshness` field computed: "today" / "yesterday" / "last_available:{date}"

---

## 14. PPT Promises vs Implementation Status

Based on the presentation PDF (11 pages):

| PPT Promise | Status | Notes |
|-------------|--------|-------|
| Multi-agent AI orchestration on Bedrock | DONE | 5 agents (Supervisor + 4 sub-agents) |
| Real-time mandi price intelligence | DONE | 8,874 items, 205 commodities, 24 states |
| Sell/hold recommendations | DONE | 14-step analysis with weather, season, storage |
| Negotiation price briefs | DONE | Fair price formula, WhatsApp-shareable |
| Hindi conversational interface | DONE | Hindi/Hinglish/English auto-detection |
| Voice input for low-literacy users | DONE (code) | Web Speech API STT, NOT deployed to frontend yet |
| Text-to-Speech | DONE (code) | TTS in ChatBubble, NOT deployed to frontend yet |
| Weather-market correlation | DONE | Open-Meteo API, weather-adjusted shelf life |
| Transport-cost-adjusted comparison | DONE | Haversine distance + Rs.0.80/qtl/km |
| MSP reference in all price responses | DONE | 2025-26 MSP rates for 14 commodities |
| WhatsApp share | DONE | Share button on every bot message |
| Agent trace/reasoning transparency | DONE | Expandable "How MandiMitra Reasoned" section |
| "100+ commodities across 500+ mandis" | PARTIALLY | 205 commodities in DB (from Agmarknet), but only 20 tracked. Mandi count TBD |
| Anomaly detection | NOT DONE | Mentioned in PPT but no anomaly detection code exists |
| Amazon Bedrock Knowledge Bases (RAG) | NOT DONE | PPT promises RAG over agricultural policy docs |
| Amazon OpenSearch Serverless | NOT DONE | PPT lists as vector store |
| Amazon Titan Embeddings | NOT DONE | PPT lists for vector search |
| Bedrock Guardrails "factual grounding" | PARTIAL | Guardrails exist but no factual grounding policy |
| AWS Amplify Hosting (CI/CD) | NOT DONE | Using S3 + CloudFront (manual deploy) |
| Kiro IDE | NOT DONE | Not used |
| Claude Sonnet/Haiku for reasoning | NOT DONE | Using Nova Pro instead |
| "Daily data refresh" | DONE | EventBridge cron at 9:30 PM IST |
| WhatsApp integration | NOT DONE | PPT roadmap item |
| Crop photo quality grading | NOT DONE | PPT roadmap item |
| eNAM direct trading | NOT DONE | PPT roadmap item |
| Multi-language (Tamil, Telugu, etc.) | NOT DONE | PPT roadmap item |
| Satellite data (NDVI) | NOT DONE | PPT roadmap item |
| Downloadable one-page brief | PARTIAL | Text brief exists, no PDF download |
| Price chart visualization | DONE | PriceChart component extracts prices from text |
| Dynamic crop lists per location | DONE (code) | API endpoint exists, NOT deployed (price-query mismatch) |
| Geocoding (resolve any city) | DONE (code) | Nominatim API in geocoding.py, NOT deployed (missing from Lambda zip) |

---

## 15. Gaps & Recommendations

### CRITICAL (Must Fix Now)

1. **Deploy price-query Lambda** - 3 files mismatch + geocoding.py missing. Any function using `get_coordinates()` or the updated handler logic will fail.
   ```
   Affected: calculate_transport_cost, weather_utils location resolution
   Fix: Rebuild and deploy the zip with all shared/ files including geocoding.py
   ```

2. **Deploy frontend** - Voice TTS, language per message, and ChatBubble improvements are NOT live.
   ```
   Fix: npm run build && deploy to S3 + CloudFront invalidation
   ```

3. **SellAdvisory "Hi" bug** - Nova Pro sometimes returns minimal "Hi" responses for complex sell/hold queries. This is a model quality issue.
   ```
   Fix: Switch SellAdvisory agent to Claude 3.7 Sonnet (better reasoning)
   Alternative: Add retry logic in sell advisory prompt, or add a "minimum response length" check
   ```

### IMPORTANT (Should Fix)

4. **Chat uses DRAFT alias** - `BEDROCK_AGENT_ALIAS_ID=TSTALIASID` means DRAFT agent. Changes to the agent take effect immediately without version control. Consider using the prod alias (BM6JROSWME).

5. **Guardrail version** - Using DRAFT version, not a numbered version. Should create a versioned guardrail for production stability.

6. **No Knowledge Base (RAG)** - PPT promises RAG over agricultural policy documents. This is a significant gap if judges check.

7. **No Anomaly Detection** - PPT mentions anomaly detection but no code exists. Could add a simple z-score check on prices.

8. **"Claude Sonnet/Haiku" in PPT** - PPT explicitly says "Amazon Bedrock (Claude Sonnet/Haiku for reasoning)" but actual deployment uses Nova Pro. This is a factual inconsistency that judges may catch.

### NICE TO HAVE

9. **list_available_commodities uses full table scan** - Expensive as data grows. Consider a metadata/summary table or caching.

10. **Nearby mandis uses in-memory dict** - Only 60+ mandis in MANDI_COORDINATES. Works now but doesn't scale. Geocoding.py helps but isn't deployed.

11. **Frontend S3 has no CloudFront invalidation automation** - Manual invalidation needed after each deploy.

12. **No CI/CD pipeline** - Manual zip builds and Lambda deploys. PPT mentions Amplify CI/CD.

13. **Data has 205 commodities but only 20 tracked** - Agmarknet returns all commodities at queried mandis. The extra commodities have data but no MSP/season/storage info in constants.

---

## Appendix: File Structure

```
hackathon/
  backend/
    agent_configs/
      orchestrator_prompt.txt          # Supervisor prompt (deployed)
      price_intel_prompt.txt           # PriceIntelligence prompt (deployed)
      sell_advisory_prompt.txt         # SellAdvisory prompt (deployed)
      negotiation_prep_prompt.txt      # Negotiation prompt (deployed)
      price_intel_openapi.json         # OpenAPI spec for action groups
      sub_agents/
        supervisor_orchestrator_prompt.txt  # Earlier version (not deployed)
        price_intelligence_agent_prompt.txt # Earlier version (not deployed)
        sell_advisory_agent_prompt.txt      # Earlier version (not deployed)
        negotiation_agent_prompt.txt        # Earlier version (not deployed)
        weather_agent_prompt.txt           # Weather prompt (deployed)
    lambdas/
      chat_handler/handler.py          # Chat Lambda (DEPLOYED, matches)
      price_query/handler.py           # Price query Lambda (NOT DEPLOYED)
      data_ingestion/handler.py        # Ingestion Lambda (DEPLOYED, matches)
      shared/
        __init__.py
        constants.py                   # Constants (deployed, matches)
        dynamodb_utils.py              # DynamoDB utils (NOT DEPLOYED)
        weather_utils.py               # Weather utils (NOT DEPLOYED)
        geocoding.py                   # Geocoding (NEW, NOT DEPLOYED)
    scripts/
      fetch_30days.py                  # 30-day historical fetch
      fetch_7days.py                   # 7-day fetch
      fetch_all_india.py               # All-India fetch (rate limits fast)
      test_api_rate_limit.py           # API rate limit tester
  frontend/
    app/
      page.tsx                         # Main chat page
      components/                      # React components
      lib/
        api.ts                         # API types & client
        voice.ts                       # Speech recognition & TTS
  tests/
    frontend_flows.spec.js             # Playwright tests (7 tests)
    edge_cases.spec.js                 # Edge case tests (new)
  docs/
    PRODUCTION_ALIAS_GUIDE.md          # Guide for prod aliases
  multi_agent_ids.json                 # Agent/alias IDs
  1771148131737-MandiMitraPresentation.pdf  # Submission PPT
```
