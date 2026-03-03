# MandiMitra — Flow Test Report
**Date:** 2026-03-02
**URL:** https://d2mtfau3fvs243.cloudfront.net
**Test Runner:** Playwright v1.58.2 (Headless Chromium)
**GPS Used:** Delhi (28.6139°N, 77.2090°E) — user live location
**DynamoDB Items at Time of Test:** 8,153
**Total Duration:** 2.1 minutes (7 tests, 1 worker)

---

## Summary

| # | Flow | Query | Result | Functional? |
|---|------|-------|--------|-------------|
| UI | Homepage Load | — | ✅ PASS (10.9s) | ✅ Yes |
| 1 | Price Check (Hindi) | MP में गेहूं का भाव | ✅ PASS (19.2s) | ⚠️ Degraded |
| 2 | Best Mandi (GPS) | इंदौर पास सोयाबीन मंडी | ✅ PASS (16.8s) | ⚠️ Degraded |
| 3 | Sell Advisory | सोयाबीन बेचूं या रुकूं? | ✅ PASS (16.2s) | ⚠️ Degraded |
| 4 | Negotiation Brief | गेहूं price brief | ✅ PASS (24.4s) | ⚠️ Degraded |
| 5 | Weather Advisory | 5 दिन मौसम + फसल | ✅ PASS (17.5s) | ✅ **Fully Working** |
| 6 | English Query | Wheat price Punjab | ✅ PASS (14.1s) | ❌ Broken |

**7/7 tests passed** (Playwright assertions) but only **2/7 flows are fully functional** today.

---

## Detailed Flow Results

---

### ✅ UI: Homepage Loads Correctly
**Status:** FULLY WORKING
**Duration:** 10.9s

**What worked:**
- Page title: `MandiMitra — किसान का साथी | Mandi Price Intelligence`
- MandiMitra branding and Hindi tagline rendered correctly
- Chat textarea visible and enabled
- All 4 quick-action chips visible: लाइव भाव, सबसे अच्छी मंडी, मंडी जानकारी, बेचें या रुकें
- LocationPicker modal dismissed successfully via `button:has-text("बाद में")`

---

### ⚠️ Flow 1: Price Check — MP Wheat (Hindi)
**Status:** DEGRADED — responds but no price data
**Query:** `मध्य प्रदेश में गेहूं का भाव क्या है?`
**Duration:** 19.2s
**Agent Steps:** 15 reasoning steps executed

**Actual Response:**
> किसान भाई, मध्य प्रदेश में गेहूं का डेटा अभी उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।

**What worked:**
- Agent received the Hindi query correctly
- Routed to PriceIntelligenceAgent (15 reasoning steps = data lookup attempted)
- "How MandiMitra Reasoned" trace panel populated
- Response in Hindi, correct tone ("किसान भाई")

**What failed:**
- No actual wheat prices returned — returned "data not available"
- No 3-digit price numbers in response

**Root cause:**
- Data ingestion (`fetch_30days.py`) is still in progress — at ~560/17,640 API calls (~3.2%) at time of test
- Madhya Pradesh wheat data not yet fetched in this run
- DynamoDB has 8,153 items but coverage is partial (today started from MP/Wheat = index 0)

**Expected once data ingestion completes:**
> किसान भाई, मध्य प्रदेश में गेहूं का भाव — इंदौर: ₹2,150/क्विंटल, भोपाल: ₹2,180/क्विंटल, उज्जैन: ₹2,090/क्विंटल | स्रोत: Agmarknet | 01/03/2026

---

### ⚠️ Flow 2: Best Mandi — Soyabean near Indore
**Status:** DEGRADED — no price data + internal name leak
**Query:** `मेरे पास 20 क्विंटल सोयाबीन है, इंदौर के पास कौन सी मंडी सबसे अच्छी रहेगी?`
**Duration:** 16.8s
**Agent Steps:** 13 reasoning steps

**Actual Response:**
> किसान भाई, मुझे खेद है कि इंदौर और देवास में सोयाबीन के लिए कोई डेटा उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें। आप मूल्य तुलना के लिए PriceIntelligenceAgent का उपयोग कर सकते हैं।

**What worked:**
- Correctly identified Indore + Dewas as nearby mandis
- GPS-based proximity lookup logic executed

**What failed:**
- No soyabean price data available for Indore/Dewas in DynamoDB yet
- **BUG:** Internal agent name `PriceIntelligenceAgent` leaked into user-facing response — should never be shown to farmers

**Root cause:**
- Same data gap as Flow 1 (soyabean for MP not yet ingested)
- Internal name leak: sub-agent prompt leaks through `clean_agent_response()` — the cleanup regex doesn't catch plain-text agent names

---

### ⚠️ Flow 3: Sell Advisory — Soyabean Hold/Sell
**Status:** DEGRADED — agent asked for location instead of using GPS
**Query:** `क्या अभी सोयाबीन बेचना चाहिए या रुकूं? 50 क्विंटल है।`
**Duration:** 16.2s
**Agent Steps:** 10 steps

**Actual Response:**
> कृपया राज्य, अक्षांश और देशांतर की जानकारी दें।

**What worked:**
- Query routed to SellAdvisoryAgent correctly (10 steps)
- Response in Hindi

**What failed:**
- Agent asked user for lat/lon instead of using the GPS already available
- No actual sell/hold recommendation given

**Root cause:**
- The browser Playwright geolocation permission (Delhi: 28.61°N, 77.21°E) is set, but **the frontend only sends GPS to the backend AFTER the user explicitly grants location in the LocationPicker**
- Since the test dismisses the LocationPicker with "बाद में" (skip), no `latitude`/`longitude` is sent in the API request body
- The backend `handler.py` only augments the message with GPS if `user_lat` and `user_lon` are present in the request
- **Fix needed:** Either auto-pass GPS when browser has it, or provide a default location in the test query (e.g., add "दिल्ली में" to the query)

**Expected with location granted:**
> किसान भाई, सोयाबीन अभी HOLD करें। दिल्ली पास मंडियों में भाव ₹4,200–4,450/क्विंटल। 30-दिन ट्रेंड: +3.2%। मौसम अगले 5 दिन साफ। भंडारण लागत ₹15/क्विंटल/दिन।

---

### ⚠️ Flow 4: Negotiation Brief — Wheat
**Status:** DEGRADED — agent needs state clarification
**Query:** `गेहूं का price brief दो जो मैं मंडी में दिखा सकूं negotiation के लिए`
**Duration:** 24.4s
**Agent Steps:** 15 steps

**Actual Response:**
> कृपया मुझे वह राज्य बताएं जहां आप गेहूं बेचने की योजना बना रहे हैं।

**What worked:**
- Routed to NegotiationAgent correctly (15 steps — extensive reasoning)
- Agent understood negotiation intent
- Response is reasonable (clarification request)

**What failed:**
- No negotiation brief card generated
- Needs follow-up turn (state name) before it can proceed
- This is a multi-turn flow — the test only does 1 turn

**Is this a bug?** Partially. Without state context this is reasonable behavior. However, if GPS was passed, the agent should infer state from coordinates automatically.

**Expected with location (Delhi, 2-turn flow):**
Turn 1: "दिल्ली/Haryana?" → Turn 2 (user: "Haryana") →
> 🌾 **गेहूं — Negotiation Brief | Haryana**
> MSP: ₹2,275 | मंडी औसत: ₹2,180 | पिछले 7 दिन: ₹2,150–2,210
> 💡 Target: ₹2,200+ मांगें
> WhatsApp पर शेयर करें ▶

---

### ✅ Flow 5: Weather Advisory (FULLY WORKING)
**Status:** FULLY WORKING — real data returned
**Query:** `अगले 5 दिन मौसम कैसा रहेगा? क्या फसल बेचने का सही समय है?`
**Duration:** 17.5s
**Agent Steps:** (not counted — direct weather API call)

**Actual Response:**
> किसान भाई, अगले 5 दिन मौसम अनुकूल रहने की उम्मीद है। बारिश की संभावना नहीं है और तापमान **16.6°C से 34.2°C** के बीच रहेगा। यह परिवहन के लिए अच्छा समय है।
>
> हालांकि, गेहूं की कीमतें गिर रही हैं। पिछले 30 दिनों में कीमतों में **7.3% की गिरावट** आई है और आने वाले दिनों में और गिरावट की उम्मीद है। इसलिए, अभी बेचने की सलाह नहीं दी जाती है।
>
> अगले कदम के रूप में, आप मौसम और कीमतों पर नजर रखें और जब कीमतें स्थिर हों या बढ़ें, तब बेचने पर विचार करें।

**What worked:**
- Real temperature data: 16.6°C–34.2°C (Delhi forecast)
- Real 30-day price trend: -7.3% (calculated from DynamoDB data)
- Combined weather + price advisory in one response
- Response in Hindi, clear actionable advice
- Correct sell recommendation: "HOLD"

**Notes:**
- Weather agent used Delhi GPS (28.61°N, 77.21°E) correctly via the browser
- Price trend from DynamoDB historical data is working

---

### ❌ Flow 6: English Query — Wheat in Punjab
**Status:** BROKEN — garbled response
**Query:** `What is the current wheat price in Punjab mandis?`
**Duration:** 14.1s
**Agent Steps:** 7 steps

**Actual Response:**
> Bot: Thought:

**What worked:**
- Query was received and processed (7 reasoning steps)
- Not blocked by guardrails (previous version blocked this)

**What failed:**
- Response is completely garbled — literally just `"Bot: Thought:"`
- No price data, no meaningful output whatsoever
- `clean_agent_response()` did not catch this artifact

**Root cause:**
- The response leaked a partial reasoning trace: `"Bot: Thought:"` is a fragment of the model's internal chain-of-thought
- This specific pattern is not caught by the current XML cleanup regex (it's plain text, not XML)
- Also no data for Punjab wheat in DynamoDB yet (same data gap)

**Fix needed:**
```python
# In clean_agent_response(), add after XML stripping:
if text.startswith("Bot: Thought:") or text.strip() in ("Bot: Thought:", "Thought:"):
    return ""  # Return empty so fallback triggers
```

---

## Issues Found — Priority Order

### 🔴 Critical (blocks core functionality)

**Issue 1: Data not yet available (temporary)**
- Affects: Flow 1, 2, 3, 4, 6
- All price queries return "data unavailable"
- Root cause: `fetch_30days.py` is at ~560/17,640 (3.2%) — running overnight
- **ETA to fix:** Automatically resolves once fetch completes (~8–10 hours)
- **Status:** ⏳ Self-resolving

**Issue 2: GPS not passed when LocationPicker is dismissed**
- Affects: Flow 3 (Sell Advisory), Flow 4 (Negotiation Brief)
- Agent asks "कृपया राज्य, अक्षांश और देशांतर की जानकारी दें" instead of using location
- Root cause: Browser has GPS but frontend only sends it after user accepts LocationPicker
- **Fix:** Pass browser GPS automatically when user grants browser permission (regardless of LocationPicker interaction)

### 🟡 Medium (bad UX, not blocking)

**Issue 3: Internal agent name leaked to user**
- Affects: Flow 2 response
- Response mentions `PriceIntelligenceAgent` — internal implementation detail
- Root cause: Sub-agent prompt instructs it to suggest using `PriceIntelligenceAgent` by name
- **Fix:** Update SellAdvisoryAgent / PriceIntelligenceAgent prompts to use user-friendly names only

**Issue 4: "Bot: Thought:" artifact in Flow 6 English query**
- Affects: Flow 6
- Response is `"Bot: Thought:"` — completely useless
- Root cause: Chain-of-thought fragment leaked, not caught by `clean_agent_response()`
- **Fix:** Add plain-text artifact patterns to cleanup function

### 🟢 Low (works, could be better)

**Issue 5: Flow 4 always needs 2 turns**
- Negotiation brief asks for state in first turn even with location data
- For multi-turn this is acceptable behavior
- **Enhancement:** Auto-infer state from GPS coordinates

---

## What Works Well Today

| Feature | Status | Notes |
|---------|--------|-------|
| App loads, branding | ✅ Working | Fast ~10s load |
| Hindi NLP routing | ✅ Working | All Hindi queries routed correctly |
| Weather forecast | ✅ Working | Real Delhi forecast data |
| 30-day price trend | ✅ Working | -7.3% for wheat from DynamoDB |
| LocationPicker modal | ✅ Working | Dismisses cleanly |
| Agent reasoning trace | ✅ Working | "How MandiMitra Reasoned" panel |
| Copy/Share buttons | ✅ Working | Visible on responses |
| Guardrails | ✅ Working | v3 — not blocking any agricultural queries |
| Response latency | ✅ Good | 14–24s per query (Bedrock multi-agent) |

---

## Expected State After Data Ingestion Completes

Once `fetch_30days.py` finishes (~17,640 API calls → ~50,000–80,000 DynamoDB items):

| Flow | Expected Result |
|------|----------------|
| Flow 1: Price Check | Real prices for 100+ mandis in MP |
| Flow 2: Best Mandi | Top 3 mandis ranked by price near Indore |
| Flow 3: Sell Advisory | SELL/HOLD with price trend, weather, storage cost |
| Flow 4: Negotiation Brief | WhatsApp-ready price card with MSP comparison |
| Flow 5: Weather | Already working |
| Flow 6: English | Will work once "Bot: Thought:" fix deployed |

---

## DynamoDB Query Diagnostics

**Current item count:** 8,153 items
**Table:** `MandiMitraPrices`
**Key structure:** `PK = STATE#COMMODITY`, `SK = DATE#MANDI`

**Quick check commands:**
```bash
# Total items
py -c "import boto3; c=boto3.client('dynamodb',region_name='us-east-1'); pages=c.get_paginator('scan').paginate(TableName='MandiMitraPrices',Select='COUNT'); print(sum(p['Count'] for p in pages))"

# Check if MP wheat data exists
py -c "
import boto3
d = boto3.resource('dynamodb', region_name='us-east-1')
t = d.Table('MandiMitraPrices')
r = t.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={':pk': 'MADHYA PRADESH#Wheat', ':sk': '2026-03-01'},
    Limit=3
)
print(f'MP Wheat records: {r[\"Count\"]}')
for item in r.get('Items', []):
    print(item)
"
```

---

## Test Infrastructure

- **Framework:** Playwright v1.58.2
- **Browser:** Headless Chromium (Desktop Chrome profile)
- **Parallelism:** Sequential (1 worker) — Bedrock has session limits
- **Retries:** 1 on failure
- **GPS:** Delhi 28.6139°N, 77.2090°E (user live location)
- **Config:** [playwright.config.js](../playwright.config.js)
- **Spec:** [tests/frontend_flows.spec.js](../tests/frontend_flows.spec.js)
- **Screenshots:** `tests/screenshots/` (12 files captured)
- **Run command:** `npx playwright test`

---

*Report generated: 2026-03-02 22:52 IST*
*Next full re-run recommended after: data ingestion completes + "Bot: Thought:" fix deployed*
