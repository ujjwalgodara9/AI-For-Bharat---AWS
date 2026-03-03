# MandiMitra — Architecture & Code Flow (v2 — Multi-Agent)

> **What changed from v1:** Architecture upgraded from a single Bedrock Agent with 4 action groups to a **5-agent supervisor system** using Amazon Bedrock Multi-Agent Collaboration. See the v1→v2 diff table below.

---

## v1 → v2 Architecture Diff

| Dimension | v1 (Before — Single Agent) | v2 (After — Multi-Agent) |
|-----------|---------------------------|--------------------------|
| Bedrock Agent count | 1 (MandiMitra) | **5** (1 supervisor + 4 sub-agents) |
| `agentCollaboration` | DISABLED | **SUPERVISOR** |
| Intent routing | Agent calls its own action groups | Supervisor delegates to specialist sub-agents |
| Price queries | PriceIntelligenceTools (on main agent) | → PriceIntelligenceAgent (CAEJ90IYS6) |
| Sell advisory | PriceIntelligenceTools.get_sell_recommendation | → **SellAdvisoryAgent** (CCYSN80MGN) |
| Negotiation brief | Multi-tool call chain on main agent | → **NegotiationAgent** (UZRXDX75NR) |
| Weather advisory | WeatherTools (on main agent) | → **WeatherAgent** (XE43VNHO3T) |
| Browse / Mandi | BrowseTools + MandiTools on main agent | **Direct on Supervisor** (still there) |
| Context to sub-agents | N/A | `relayConversationHistory=TO_COLLABORATOR` |
| Latency | 4–7 seconds | 15–20 seconds (multi-agent routing overhead) |
| DynamoDB items | 4,467 (initial) | **5,177+** (7-day historical added) |
| LangFuse tracing | Not active | **Active** (langfuse v2.60.10) |
| CloudFront | HTTP→HTTPS redirect | ✅ Same |
| EventBridge schedule | MISSING (was never created) | **Still missing — needs fix** |

---

## Full System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │           USER (Farmer's Phone)             │
                    │    PWA / Chat UI (installable)              │
                    │    Voice Input (Hindi hi-IN / English en-IN)│
                    │    GPS location auto-detect                  │
                    └──────────────────┬──────────────────────────┘
                                       │ HTTPS
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │      CloudFront (HTTPS CDN)                 │
                    │      E1FOPZ17Q7P6CF                        │
                    │      d2mtfau3fvs243.cloudfront.net          │
                    │      HTTP→HTTPS redirect                     │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │         S3 Static Website                   │
                    │     mandimitra-frontend-471112620976        │
                    │     Next.js 14 SSG (output: "export")       │
                    └──────────────────┬──────────────────────────┘
                                       │ POST /api/chat
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │        API Gateway HTTP (skwsw8qk22)        │
                    │  POST /api/chat → mandimitra-chat            │
                    │  GET /api/prices/{commodity} → price-query  │
                    └──────────┬────────────────────┬────────────┘
                               │                    │
                               ▼                    ▼
              ┌────────────────────────┐  ┌─────────────────────┐
              │  mandimitra-chat       │  │ mandimitra-price-    │
              │  Lambda (29s, 512MB)   │  │ query Lambda        │
              │  ─────────────────     │  │ (30s, 256MB)        │
              │  1. Parse message       │  │ Direct price API     │
              │  2. Inject GPS context  │  └─────────────────────┘
              │  3. Invoke Bedrock      │
              │     Agent (TSTALIASID) │
              │  4. Collect stream      │
              │  5. LangFuse trace      │
              └────────────┬───────────┘
                           │ invoke_agent
                           ▼
╔══════════════════════════════════════════════════════════════╗
║  BEDROCK SUPERVISOR AGENT: MandiMitra (GDSWGCDJIX)          ║
║  Model: amazon.nova-pro-v1:0                                ║
║  Mode: SUPERVISOR | Alias: TSTALIASID → DRAFT               ║
║                                                              ║
║  OWN ACTION GROUPS (used for BROWSE/MANDI queries):         ║
║  • BrowseTools   → list_available_commodities/mandis/states ║
║  • MandiTools    → get_all_prices_at_mandi, get_mandi_profile║
║  • PriceIntelligenceTools → (direct fallback)               ║
║  • WeatherTools  → (direct fallback)                        ║
║                                                              ║
║  DELEGATES to sub-agents via collaboration:                 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ┌──────────────────────────────────────────────────┐       ║
║  │ PriceIntelligenceAgent (CAEJ90IYS6/7YU2OMSRBQ)  │       ║
║  │ Triggered for: PRICE_CHECK, NEARBY_MANDI, TREND  │       ║
║  │ Action group: PriceIntelligenceTools             │       ║
║  │  • query_mandi_prices(commodity, state, mandi?)  │       ║
║  │  • get_nearby_mandis(lat, lon, radius?, commodity?)│      ║
║  │  • get_price_trend(commodity, state, mandi?)     │       ║
║  │  • get_msp(commodity)                            │       ║
║  │  • calculate_transport_cost(lat, lon, mandi, qtl)│       ║
║  └──────────────────────────────────────────────────┘       ║
║                                                              ║
║  ┌──────────────────────────────────────────────────┐       ║
║  │ SellAdvisoryAgent (CCYSN80MGN/HPMZYLQZU3)        │       ║
║  │ Triggered for: SELL_ADVISORY intent              │       ║
║  │ Action group: SellAdvisoryTools                  │       ║
║  │  • get_sell_recommendation(commodity, state,     │       ║
║  │      latitude, longitude, quantity_qtl)          │       ║
║  │    → nearby mandis + trend + MSP + weather       │       ║
║  │    → shelf life + storage cost + season          │       ║
║  │    → SELL/HOLD/SPLIT recommendation              │       ║
║  └──────────────────────────────────────────────────┘       ║
║                                                              ║
║  ┌──────────────────────────────────────────────────┐       ║
║  │ NegotiationAgent (UZRXDX75NR/TFQ24DRCOW)         │       ║
║  │ Triggered for: NEGOTIATION intent                │       ║
║  │ Action group: NegotiationTools                   │       ║
║  │  • query_mandi_prices, get_msp                   │       ║
║  │  • get_nearby_mandis, get_price_trend            │       ║
║  │  → Outputs formatted shareable Price Brief       │       ║
║  └──────────────────────────────────────────────────┘       ║
║                                                              ║
║  ┌──────────────────────────────────────────────────┐       ║
║  │ WeatherAgent (XE43VNHO3T/YUSEVJPMWJ)             │       ║
║  │ Triggered for: WEATHER intent                    │       ║
║  │ Action group: WeatherTools                       │       ║
║  │  • get_weather_advisory(location, lat?, lon?)    │       ║
║  │    → Open-Meteo 5-day forecast                   │       ║
║  │    → Rain/heat/storm alerts                      │       ║
║  │    → Sell-timing advisory                        │       ║
║  └──────────────────────────────────────────────────┘       ║
╚══════════════════════════════════════════════════════════════╝
                           │
       All sub-agent tool calls go to:
                           ▼
              ┌────────────────────────────┐
              │  mandimitra-price-query    │
              │  Lambda (Action Executor)  │
              │  handler.py               │
              │  shared/dynamodb_utils.py  │
              │  shared/weather_utils.py   │
              │  shared/constants.py       │
              └───────┬────────────┬───────┘
                      │            │
              ┌───────▼───┐  ┌─────▼──────────┐
              │ DynamoDB  │  │ Open-Meteo API  │
              │ Mandi     │  │ Free weather    │
              │ MitraPrices│  │ 5-day forecast │
              │ ~5,177 items│  └────────────────┘
              └───────────┘

Data Pipeline (manual trigger — EventBridge NOT configured):
              ┌────────────────────────────┐
              │  data.gov.in Agmarknet API │
              │  Resource: 9ef84268...     │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │ mandimitra-data-ingestion  │
              │ Lambda (900s timeout)      │
              │ 20 commodities x 14 states │
              └─────────────┬──────────────┘
                            │
                    ┌───────▼───────┐
                    │   DynamoDB    │
                    │ + S3 audit    │
                    └───────────────┘
```

---

## DynamoDB Schema

**Table: MandiMitraPrices**

| Key/Attribute | Type | Example |
|--------------|------|---------|
| PK (Partition Key) | String | `WHEAT#MADHYA_PRADESH` |
| SK (Sort Key) | String | `2026-03-01#INDORE APMC` |
| commodity | String | "Wheat" |
| state | String | "Madhya Pradesh" |
| district | String | "Indore" |
| mandi_name | String | "INDORE APMC" (uppercase) |
| arrival_date | String | "2026-03-01" (ISO) |
| variety | String | "Mill Quality" |
| min_price | Decimal | 2200 |
| max_price | Decimal | 2420 |
| modal_price | Decimal | 2250 |
| date_commodity | String | `2026-03-01#WHEAT` (for GSI) |
| ingested_at | String | ISO timestamp |
| arrivals_tonnes | Decimal (optional) | 145.5 |

**Global Secondary Indexes:**

| Index | PK | SK | Enables |
|-------|----|----|---------|
| DATE-INDEX | arrival_date | PK | "All prices on date X" |
| MANDI-INDEX | mandi_name | date_commodity | "All commodities at mandi X" |

---

## File Structure (Backend)

```
backend/
├── lambdas/
│   ├── chat_handler/
│   │   └── handler.py          # Chat Lambda
│   │       invoke_agent()       # Bedrock streaming invocation
│   │       extract_trace()      # Parse agent trace steps
│   │       Fallback: chunk → trace answer → retry
│   │
│   ├── price_query/
│   │   └── handler.py          # Action Group Lambda
│   │       handle_api_request() # GET /api/prices/{commodity}
│   │       handle_agent_action()# Bedrock action group dispatcher
│   │       → routes to 13+ functions
│   │
│   ├── data_ingestion/
│   │   └── handler.py          # Data pipeline Lambda
│   │       fetch_from_agmarknet()  # data.gov.in API fetch
│   │       write_to_dynamodb()     # Batch write with validation
│   │       transform_record()      # Parse + validate each record
│   │
│   └── shared/                 # Bundled with each Lambda zip
│       ├── __init__.py
│       ├── constants.py        # MANDI_COORDINATES (60+), MSP_RATES (20 crops)
│       │                         PERISHABILITY_INDEX, STORAGE_COST_PER_DAY
│       │                         CROP_SEASONS, WEATHER_STORAGE_IMPACT
│       ├── dynamodb_utils.py   # All DB + calculation logic
│       │   query_prices()          # PK query + 4-level fallback
│       │   query_mandi_prices()    # MANDI-INDEX GSI query
│       │   get_nearby_mandis()     # Haversine from 60+ coordinates
│       │   get_price_trend()       # Direction, change%, volatility
│       │   get_msp()               # Case-insensitive MSP lookup
│       │   get_sell_recommendation_data()  # Full sell advisory
│       │   _get_season_context()   # Harvest/sowing season detection
│       │   _assess_weather_storage_risk()  # Weather impact on crops
│       │   list_available_commodities/mandis/states()
│       │   calculate_net_realization()
│       │   haversine_distance()
│       └── weather_utils.py    # Open-Meteo weather advisory
│           get_weather_advisory()
│           generate_agri_advisory()
│
├── agent_configs/
│   ├── orchestrator_prompt.txt        # Legacy v1 prompt (kept for reference)
│   └── sub_agents/                    # v2 multi-agent prompts
│       ├── supervisor_orchestrator_prompt.txt
│       ├── price_intelligence_agent_prompt.txt
│       ├── sell_advisory_agent_prompt.txt
│       ├── negotiation_agent_prompt.txt
│       └── weather_agent_prompt.txt
│
└── scripts/
    ├── fetch_7days.py               # Explicit date-filtered historical fetch
    │   fetch_for_date()              # Per-date API call with dedup
    │   write_batch()                 # Deduplicate + individual put_item
    ├── setup_multi_agent_resume.py  # Multi-agent Bedrock setup
    ├── create_multi_agent.py        # Original setup attempt (reference)
    └── (legacy fetch scripts)
```

---

## Sell Advisory Logic

```python
# In shared/dynamodb_utils.py: get_sell_recommendation_data()

1. get_nearby_mandis(lat, lon, 150km, commodity)
   → Finds mandis within 150km with current prices
   → Calculates net_realization = modal_price - (distance × ₹0.8/qtl/km)

2. get_price_trend(commodity, state, best_mandi, 30 days)
   → trend: "rising" | "falling" | "stable"
   → change_pct, avg_price, volatility, data_points

3. get_msp(commodity) → MSP reference price

4. PERISHABILITY_INDEX[commodity]  # 1 (wheat=180 days) to 10 (tomato=1 day)
   shelf_life = {1:180, 2:90, 3:60, 4:45, 5:30, 6:21, 7:14, 8:7, 9:3, 10:1}[p]

5. _get_season_context(commodity)
   → is_harvest, is_sowing, note (supply/demand pressure)

6. Decision matrix:
   IF trend=="rising" AND storage AND perishability<=5:
       hold_days = min(shelf_life * 0.3, 15)
       recommendation = "HOLD"
   ELIF trend=="stable" AND perishability<=3 AND storage:
       hold_days = min(shelf_life * 0.2, 10)
       recommendation = "HOLD"
   ELSE:
       hold_days = 0
       recommendation = "SELL"

7. total_storage_cost = storage_cost_per_day × hold_days × quantity_qtl
```

---

## Key Design Decisions

1. **Multi-agent over single-agent**: Specialist sub-agents produce more focused, accurate responses for their domain. The sell advisor doesn't need to know browse commands.

2. **Nova Pro over Claude**: Claude requires EULA in AWS Console; Nova Pro is AWS-native with immediate access — better fit for AWS hackathon context.

3. **functionSchema over OpenAPI**: Bedrock rejected OpenAPI spec during initial setup. `functionSchema` with inline definitions works reliably.

4. **TSTALIASID → DRAFT**: Lambda always uses DRAFT alias so all prompt changes take effect immediately without a separate publish step. Intentional for rapid hackathon iteration.

5. **Max 5 params per function**: Bedrock Agents enforces this at the account/service quota level. `get_sell_recommendation` dropped `storage_available` to comply.

6. **`create_agent_version` missing from boto3**: Not in botocore 1.42.58 service model. Workaround: omit `routingConfiguration` when creating alias — server auto-creates a version snapshot.

7. **Lambda zip structure for shared/**: Handler imports `from shared.dynamodb_utils import ...`. Zip must contain `handler.py` at root AND `shared/` as a subdirectory — NOT flat files.

8. **DynamoDB single-table design**: Composite PK+SK + 2 GSIs enables all 4 query patterns (by commodity+state, by mandi, by date, nearby via constants). PAY_PER_REQUEST billing.

9. **Haversine + GPS coordinate table**: `constants.py` has 60+ major APMC mandis with lat/lon. Real-time GPS distance calculation instead of static zone mapping.

10. **4-level query fallback**: User says "Karnal" but data says "INDRI APMC" (in Karnal district). Fallback chain: exact match → APMC suffix → historical data → district scan → partial match.

11. **Data freshness**: `data_freshness: "today" | "yesterday" | "last_available:{date}"`. Agent explicitly tells farmer if they're seeing yesterday's data.

12. **Open-Meteo for weather**: Free API, no key, global coverage, WMO weather codes. Returns temperature, precipitation, wind for 5 days.

13. **relayConversationHistory=TO_COLLABORATOR**: Sub-agents receive the full conversation history so they understand context (e.g., location, commodity already mentioned earlier in conversation).

14. **LangFuse tracing**: Every Bedrock Agent invocation traced with all reasoning/tool/observation steps. Enables debugging, latency analysis, and conversation analytics.

---

## AWS Resource Summary (Audit Date: March 1, 2026)

See [docs/AWS_AUDIT.md](../AWS_AUDIT.md) for the complete audit.

| Resource | ID/Name | Status |
|----------|---------|--------|
| Supervisor Agent | GDSWGCDJIX (MandiMitra) | PREPARED, SUPERVISOR mode |
| PriceIntelligenceAgent | CAEJ90IYS6 | PREPARED |
| SellAdvisoryAgent | CCYSN80MGN | PREPARED |
| NegotiationAgent | UZRXDX75NR | PREPARED |
| WeatherAgent | XE43VNHO3T | PREPARED |
| DynamoDB | MandiMitraPrices | ACTIVE, 5,177+ items |
| CloudFront | d2mtfau3fvs243.cloudfront.net | Deployed |
| API Gateway | skwsw8qk22 | Live |
| Lambda (chat) | mandimitra-chat | Active, 29s, 512MB |
| Lambda (prices) | mandimitra-price-query | Active, 30s, 256MB |
| Lambda (ingest) | mandimitra-data-ingestion | Active, 900s, 512MB |
| LangFuse | cloud.langfuse.com | Active ✅ |
| EventBridge | — | ❌ NOT CONFIGURED |
| Guardrails | — | ❌ EMPTY |
