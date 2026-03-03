# MandiMitra -- User Flows Documentation

MandiMitra is an AI-powered agricultural market intelligence copilot for Indian farmers. It uses an Amazon Bedrock Agent (Nova Pro) with **4 action groups** and **13 functions** to provide real-time mandi price intelligence, sell/hold advisory, weather guidance, and negotiation support.

This document describes every user flow in the application at the step-by-step level: what the user does, how the frontend handles it, what API calls are made, how the Bedrock Agent processes it, which tool functions are invoked, and how the response renders back in the UI.

---

## Table of Contents

1. [Price Check Flow](#1-price-check-flow)
2. [Best Mandi / Where to Sell Flow](#2-best-mandi--where-to-sell-flow)
3. [Sell or Hold Advisory Flow](#3-sell-or-hold-advisory-flow)
4. [Weather Advisory Flow](#4-weather-advisory-flow)
5. [Mandi Information / Market Profile Flow](#5-mandi-information--market-profile-flow)
6. [All Prices at Mandi Flow](#6-all-prices-at-mandi-flow)
7. [Browse Data Flow](#7-browse-data-flow)
8. [Negotiation Brief Flow](#8-negotiation-brief-flow)
9. [Voice Input Flow](#9-voice-input-flow)
10. [Location Selection Flow](#10-location-selection-flow)
11. [Data Freshness Flow](#11-data-freshness-flow)
12. [Fallback Strategy](#12-fallback-strategy)
13. [Error Handling](#13-error-handling)

---

## 1. Price Check Flow

**Purpose:** User asks for the current mandi price of a specific commodity.

### Trigger

User types or speaks a query such as:
- "wheat ka bhav Karnal mein"
- "soyabean price in Indore"
- Taps the **"Check Price" / "bhav dekho"** quick action button

### Step-by-Step Flow

**Step 1 -- Frontend Action** (`frontend/app/page.tsx`)
- `sendMessage(content)` is called with the user's text.
- A user `ChatMessage` object is created and appended to the `messages` state array.
- `isLoading` is set to `true`, which shows the `TypingIndicator` component.
- The frontend builds a POST payload:
  ```json
  {
    "message": "wheat ka bhav Karnal mein",
    "language": "hi",
    "session_id": "session_1709..._abc123",
    "latitude": 29.69,
    "longitude": 76.99
  }
  ```
- A `fetch()` call is made to `POST {API_BASE}/chat`.

**Step 2 -- API Gateway**
- API Gateway (`skwsw8qk22 / prod`) receives the POST at `/api/chat`.
- Routes to the `mandimitra-chat` Lambda function.

**Step 3 -- Chat Handler Lambda** (`backend/lambdas/chat_handler/handler.py`)
- `handler()` parses the JSON body: extracts `message`, `language`, `session_id`, `latitude`, `longitude`.
- Builds an augmented message:
  ```
  [Respond in Hindi] [User GPS location: latitude=29.69, longitude=76.99. Use this for nearby mandi lookups and transport cost calculations.] wheat ka bhav Karnal mein
  ```
- Calls `invoke_agent()` which invokes `bedrock_agent_runtime.invoke_agent()` with:
  - `agentId`: GDSWGCDJIX
  - `agentAliasId`: TSTALIASID
  - `sessionId`: the user's session ID
  - `inputText`: the augmented message
  - `enableTrace`: True
- Starts a LangFuse trace (if configured) for observability.

**Step 4 -- Bedrock Agent Processing** (Nova Pro model)
- **Pre-processing**: Classifies intent as `PRICE_CHECK`.
- **Reasoning**: "Need wheat prices in Haryana near Karnal. Will call query_mandi_prices."
- **Tool Selection**: Selects `PriceIntelligenceTools` action group, function `query_mandi_prices`.

**Step 5 -- Action Group Lambda** (`backend/lambdas/price_query/handler.py`)
- `handle_agent_action()` is invoked with:
  ```json
  {
    "actionGroup": "PriceIntelligenceTools",
    "function": "query_mandi_prices",
    "parameters": [
      {"name": "commodity", "value": "Wheat"},
      {"name": "state", "value": "Haryana"},
      {"name": "mandi", "value": "Karnal"},
      {"name": "days", "value": "7"}
    ]
  }
  ```
- Calls `query_prices("Wheat", "Haryana", "Karnal", 7)` in `dynamodb_utils.py`:
  - Constructs PK = `WHEAT#HARYANA`, queries DynamoDB with SK range `{start_date}#KARNAL` to `{end_date}#KARNAL~`.
  - If no results, tries APMC suffix fallback (see [Fallback Strategy](#12-fallback-strategy)).
  - If still nothing, does a district scan for mandis in Karnal district.
- Calls `get_price_trend("Wheat", "Haryana", "Karnal", 7)`:
  - Computes direction (rising/falling/stable), change_pct, avg_price, volatility, min/max in period.
- Calls `get_msp("Wheat")`:
  - Returns `{"commodity": "Wheat", "msp": 2275, "year": "2025-26", "has_msp": true}`.
- Determines **data freshness**: compares latest `arrival_date` against today and yesterday.
- Separates `today_prices` and `previous_day_prices` for comparison.
- Returns the Bedrock Agent response envelope:
  ```json
  {
    "messageVersion": "1.0",
    "response": {
      "actionGroup": "PriceIntelligenceTools",
      "function": "query_mandi_prices",
      "functionResponse": {
        "responseBody": {
          "TEXT": {
            "body": "{\"prices\": [...], \"today_prices\": [...], \"previous_day_prices\": [...], \"data_freshness\": \"today\", \"trend\": {...}, \"msp\": {...}, \"record_count\": 5}"
          }
        }
      }
    }
  }
  ```

**Step 6 -- Bedrock Agent Response Generation**
- The agent processes the tool output.
- Generates a Hindi response containing: current price (modal, min, max), previous day comparison, MSP comparison, 7-day trend, data source and date.
- Returns the response in `<answer>` tags within the model output.

**Step 7 -- Chat Handler Collects Response**
- Collects response bytes from the streaming `completion` event.
- Fallback chain if bytes are empty: extract from trace `<answer>` tag, then retry without traces.
- Returns to API Gateway:
  ```json
  {
    "response": "Hindi formatted price text...",
    "session_id": "session_...",
    "language": "hi",
    "agent_trace": [{...}, {...}, ...],
    "latency_seconds": 2.1
  }
  ```

**Step 8 -- UI Rendering** (`frontend/app/components/ChatBubble.tsx`)
- The bot `ChatMessage` is appended to the messages array.
- `ChatBubble` renders the response with:
  - Message text split by `\n` into line breaks.
  - `PriceChart` component: `extractPriceData()` regex-parses the response text for `mandi: Rs.X,XXX` patterns and renders an SVG mini-chart comparing mandi prices.
  - WhatsApp share button (opens `wa.me/?text=...`).
  - Copy button (uses `navigator.clipboard.writeText()`).
  - Expandable "How MandiMitra Reasoned" trace panel showing each agent step (preprocessing, reasoning, tool_call, observation).

---

## 2. Best Mandi / Where to Sell Flow

**Purpose:** User wants to know which nearby mandi offers the best price for their commodity, factoring in transport costs.

### Trigger

User types or speaks:
- "mere paas 20 quintal wheat hai, kahan bechun?"
- "best mandi near me for soyabean"
- Taps the **"Best Mandi" / "kahan bechun?"** quick action button

### Step-by-Step Flow

**Step 1 -- Frontend Action**
- Same as Price Check: `sendMessage()` posts to `/api/chat` with the message, language, session_id, and GPS coordinates.

**Step 2 -- API Gateway to Chat Handler**
- Identical routing as Price Check.

**Step 3 -- Chat Handler**
- Augments message with `[User GPS location: latitude=X, longitude=Y]`.
- Invokes Bedrock Agent.

**Step 4 -- Bedrock Agent Processing**
- **Intent**: `MANDI_COMPARE`.
- **Reasoning**: "User wants best selling location. Need nearby mandis with prices and transport cost. Will use get_nearby_mandis with GPS."
- **Tool Selection**: `PriceIntelligenceTools` / `get_nearby_mandis`.

**Step 5 -- Tool Function: `get_nearby_mandis`**
- Parameters:
  ```json
  {"latitude": 22.72, "longitude": 75.86, "radius_km": 100, "commodity": "Soyabean"}
  ```
- `get_nearby_mandis()` in `dynamodb_utils.py`:
  - Iterates over all 55+ entries in `MANDI_COORDINATES`.
  - Calculates haversine distance from user GPS to each mandi.
  - Filters mandis within `radius_km`.
  - For each nearby mandi, fetches the latest 3-day price via `query_prices()`.
  - Calculates `net_realization` for each mandi:
    ```
    net_realization = modal_price - (distance_km * 0.8)
    ```
    Where 0.8 is `TRANSPORT_COST_PER_QTL_PER_KM` (Rs. per quintal per km).
  - Sorts by distance ascending.
- Returns up to 10 nearby mandis with prices and net realization.

**Step 6 -- Agent Response**
- Agent generates a response ranking mandis by net realization (highest first).
- Includes: mandi name, distance, modal price, transport cost per quintal, net realization.
- Recommends the best option with clear reasoning.

**Step 7 -- UI Rendering**
- Chat bubble with mandi comparison.
- `PriceChart` auto-extracts mandi price points from the response text and renders an SVG bar comparison.
- WhatsApp share and copy buttons available.

---

## 3. Sell or Hold Advisory Flow

**Purpose:** User asks whether to sell their commodity now or hold for a better price.

### Trigger

User types:
- "kya abhi soyabean bechna chahiye ya kuch din ruku?"
- "should I sell my wheat now or wait?"
- Taps the **"Sell or Hold?" / "bechun ya rukun?"** quick action button, then selects a commodity from the picker.

### Step-by-Step Flow

**Step 1 -- Frontend: Commodity Picker**
- When user taps "Sell or Hold?", `QuickActions` component shows a commodity picker (`COMMODITY_OPTIONS`: Wheat, Soyabean, Onion, Tomato, Potato, Chana, Mustard, Cotton, Maize, Rice).
- On selection, constructs a detailed query:
  - Hindi: "kya abhi {commodity} bechna chahiye ya kuch din rukna chahiye? Shelf life aur kitne din ruk sakte hain yeh bhi batao."
  - English: "Should I sell my {commodity} now or wait? Also tell me the shelf life and recommended hold time."

**Step 2 -- API Call**
- Same POST to `/api/chat` with message, language, session_id, GPS.

**Step 3 -- Bedrock Agent Processing**
- **Intent**: `SELL_ADVISORY`.
- **Tool Selection**: `PriceIntelligenceTools` / `get_sell_recommendation`.

**Step 4 -- Tool Function: `get_sell_recommendation`**
- Parameters:
  ```json
  {
    "commodity": "Soyabean",
    "state": "Madhya Pradesh",
    "latitude": 22.72,
    "longitude": 75.86,
    "quantity_qtl": 10,
    "storage_available": "true"
  }
  ```
- `get_sell_recommendation_data()` in `dynamodb_utils.py`:
  1. Calls `get_nearby_mandis(lat, lon, 150, commodity)` -- finds mandis within 150 km with prices.
  2. Calls `get_price_trend(commodity, state, best_mandi, 30)` -- 30-day trend analysis.
  3. Calls `get_msp(commodity)` -- MSP lookup.
  4. Looks up `PERISHABILITY_INDEX` (1-10 scale; e.g., Wheat=1, Tomato=9, Soyabean=2).
  5. Looks up `STORAGE_COST_PER_DAY` (e.g., Wheat=Rs.1.5, Tomato=Rs.15, default=Rs.2).
  6. Calculates `net_realization` for each mandi (price minus transport cost).
  7. Sorts mandis by net realization descending.
  8. Calculates **shelf life** from perishability index:
     - Perishability 1 = 180 days, 2 = 90 days, 3 = 60 days, ... 9 = 3 days, 10 = 1 day.
  9. Calculates **recommended hold days**:
     - If trend is "rising" and storage available: hold up to 30% of shelf life, max 15 days.
     - If trend is "stable" and perishability <= 3 and storage available: hold up to 20% of shelf life, max 10 days.
     - Otherwise: 0 (sell now).
  10. Calculates `total_storage_cost_if_held = storage_cost_per_day * hold_days * quantity`.
- Returns comprehensive JSON with all data points.

**Step 5 -- Agent Response**
- Agent generates a clear recommendation: SELL / HOLD / SPLIT.
- Includes: shelf life, recommended hold time, storage cost per day, total storage cost if held, confidence level, reasoning, best mandi with net realization.

**Step 6 -- UI Rendering**
- Formatted sell advisory in chat bubble.
- Price chart if multiple mandi prices are mentioned.
- Agent trace showing reasoning chain.

---

## 4. Weather Advisory Flow

**Purpose:** User asks about weather conditions to plan mandi visits or crop handling.

### Trigger

User types:
- "mausam kaisa hai agle 5 din?"
- "weather forecast for Indore"
- "baarish aayegi kya?"
- Taps the **"Weather" / "mausam"** quick action button.

### Step-by-Step Flow

**Step 1 -- Frontend Action**
- Quick action constructs: "Indore mein agle 5 din mausam kaisa rahega? Mandi jaane mein koi dikkat?"
- POST to `/api/chat`.

**Step 2 -- Bedrock Agent Processing**
- **Intent**: `WEATHER`.
- **Tool Selection**: `WeatherTools` / `get_weather_advisory`.

**Step 3 -- Tool Function: `get_weather_advisory`**
- Parameters:
  ```json
  {"location": "Indore", "latitude": "22.72", "longitude": "75.86"}
  ```
- `get_weather_advisory()` in `weather_utils.py`:
  1. **Resolves coordinates**: If lat/lon provided, use directly. Otherwise, looks up location in `MANDI_COORDINATES` (exact match, title case, then fuzzy match).
  2. **Calls Open-Meteo API** (free, no key needed):
     ```
     https://api.open-meteo.com/v1/forecast?latitude=22.72&longitude=75.86
       &daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max
       &current_weather=true&timezone=Asia/Kolkata&forecast_days=5
     ```
  3. **Parses response**: Extracts 5-day forecast with max/min temp, precipitation, WMO weather code (mapped to descriptions like "Clear sky", "Moderate rain", "Thunderstorm"), wind speed.
  4. **Generates agricultural advisory** via `generate_agri_advisory()`:
     - **Rain alerts**: >50mm = "Heavy rainfall, sell perishables now"; >20mm = "Moderate rainfall, plan mandi visits on dry days"; <2mm = "Dry weather, good for transport."
     - **Temperature alerts**: >42C = "Extreme heat, transport early morning"; >38C = "High temperature, irrigate in evening"; <5C = "Cold weather, protect from frost."
     - **Storm alerts**: Thunderstorm detected = "Avoid open field work, harvest ready crops."
     - **Sell impact**: Sets `sell_impact` to "sell_perishable_now", "urgent_harvest", or "neutral".
  5. Returns: current conditions, 5-day forecast array, advisory (alerts, recommendations, sell_impact, total_rain_5d, temp_range).

**Step 4 -- Agent Response**
- Current weather conditions.
- 5-day forecast summary.
- Agricultural alerts and recommendations.
- Impact on selling decisions.

**Step 5 -- UI Rendering**
- Weather advisory in chat bubble with alerts and recommendations.
- Agent trace showing weather tool invocation.

---

## 5. Mandi Information / Market Profile Flow

**Purpose:** User asks for comprehensive information about a specific mandi.

### Trigger

User types:
- "Indore mandi ki puri jankari do"
- "mandi information for Karnal"
- "Agmarknet details for Nagpur mandi"
- Taps the **"Mandi Info" / "mandi jankari"** quick action button.

### Step-by-Step Flow

**Step 1 -- Frontend Action**
- Quick action constructs: "{city} mandi ki puri jankari do -- kaun si faslen bik rahi hain, bhav, aur Agmarknet vivaran"
- POST to `/api/chat`.

**Step 2 -- Bedrock Agent Processing**
- **Intent**: `MANDI_PROFILE`.
- **Tool Selection**: `MandiTools` / `get_mandi_profile`.

**Step 3 -- Tool Function: `get_mandi_profile`**
- Parameters:
  ```json
  {"mandi": "Indore", "days": 7}
  ```
- `get_mandi_profile()` in `dynamodb_utils.py`:
  1. Queries `MANDI-INDEX` GSI with `mandi_name = "INDORE"`.
  2. If no results, tries APMC suffixes: "INDORE APMC", "INDORE(GRAIN)", "INDORE(F&V)".
  3. If still no results, falls back to full table scan matching `district` or partial `mandi_name`.
  4. Groups items by commodity, keeping the latest price for each.
  5. Sorts commodities by modal_price descending.
  6. Extracts mandi metadata: mandi_name, district, state, coordinates.
  7. Attaches Agmarknet source information:
     ```json
     {
       "portal": "https://agmarknet.gov.in",
       "data_api": "https://data.gov.in",
       "update_schedule": "Daily by 5:00 PM IST (per DMI guidelines)",
       "coverage": "2000+ APMC mandis across India",
       "fields": "commodity, variety, min_price, max_price, modal_price, arrival_date"
     }
     ```
  8. Returns: mandi name, district, state, coordinates, total commodities traded, top 20 commodities with prices, Agmarknet info, total records found.

**Step 4 -- Agent Response**
- Mandi name, district, state.
- Total commodities traded.
- Top commodities with prices sorted by modal price.
- Agmarknet data source details and update schedule.
- Suggests: "Is mandi ki kisi bhi fasal ka bhav puch sakte hain."

**Step 5 -- UI Rendering**
- Comprehensive mandi profile in chat bubble.
- Price chart if multiple commodity prices are extracted.

---

## 6. All Prices at Mandi Flow

**Purpose:** User asks what commodities are available and their prices at a specific mandi.

### Trigger

User types:
- "Indore mandi mein kya kya mil raha hai?"
- "all prices at Karnal"
- "is mandi mein kya bhav hai?"

### Step-by-Step Flow

**Step 1 -- Frontend Action**
- POST to `/api/chat` with the user's message.

**Step 2 -- Bedrock Agent Processing**
- **Intent**: `MANDI_ALL_PRICES`.
- **Tool Selection**: `MandiTools` / `get_all_prices_at_mandi`.

**Step 3 -- Tool Function: `get_all_prices_at_mandi`**
- Parameters:
  ```json
  {"mandi": "Indore", "days": 7}
  ```
- In `price_query/handler.py`:
  1. Calls `query_mandi_prices("Indore", 7)` from `dynamodb_utils.py`.
  2. `query_mandi_prices()` queries the `MANDI-INDEX` GSI for all records at that mandi within the date range.
  3. Applies the full fallback chain (exact match, APMC suffix, district scan, partial match -- see [Fallback Strategy](#12-fallback-strategy)).
  4. Groups results by commodity, keeping the record with the highest modal_price for each commodity.
  5. Returns:
     ```json
     {
       "mandi": "INDORE",
       "commodities_count": 12,
       "prices": [
         {"commodity": "Soyabean", "modal_price": 4850, "min_price": 4200, "max_price": 5100, "arrival_date": "2026-02-28", "variety": "Yellow"},
         ...
       ],
       "total_records": 45
     }
     ```

**Step 4 -- Agent Response**
- Lists ALL commodities available at the mandi with prices.
- Sorted by price (highest first).
- Includes MSP comparison where applicable.

**Step 5 -- UI Rendering**
- Grouped commodity listing in chat bubble.
- Price chart for visual comparison of commodity prices.

---

## 7. Browse Data Flow

**Purpose:** User wants to know what commodities, mandis, or states are available in the system.

### Trigger

User types:
- "kaun si faslen hain?"
- "which mandis are available?"
- "kaun se rajya?"
- "list commodities in Rajasthan"

### Step-by-Step Flow

**Step 1 -- Bedrock Agent Processing**
- **Intent**: `BROWSE_DATA`.
- **Tool Selection**: `BrowseTools` action group, one of three functions.

**Step 2 -- Tool Functions**

**Function A: `list_available_commodities`**
- Parameters: `{"state": "Rajasthan"}` (optional state filter)
- `list_available_commodities()` in `dynamodb_utils.py`:
  - Full table scan with projection on `commodity` and `state`.
  - Optionally filters by state.
  - Paginates through all results.
  - Returns sorted list of unique commodity names.
- Response: `{"commodities": ["Bajra", "Chana", "Cotton", ...], "count": 15, "state_filter": "Rajasthan"}`

**Function B: `list_available_mandis`**
- Parameters: `{"state": ""}` (optional state filter)
- `list_available_mandis()`:
  - Full table scan with projection on `mandi_name`, `state`, `district`.
  - Deduplicates by mandi name.
  - Returns sorted list of mandi objects.
- Response: `{"mandis": [{"mandi": "INDORE", "state": "Madhya Pradesh", "district": "Indore"}, ...], "count": 120, "state_filter": "all states"}`

**Function C: `list_available_states`**
- Parameters: none.
- `list_available_states()`:
  - Full table scan with projection on `state`.
  - Returns sorted list of unique state names.
- Response: `{"states": ["Andhra Pradesh", "Bihar", "Gujarat", ...], "count": 14}`

**Step 3 -- Agent Response**
- Clean formatted list.
- Mandis grouped by state.
- Total count mentioned.
- Suggests next action: "in mein se kisi bhi fasal ka bhav puch sakte hain."

**Step 4 -- UI Rendering**
- Formatted list in chat bubble.
- No chart rendering for browse queries.

---

## 8. Negotiation Brief Flow

**Purpose:** User wants a formatted price intelligence document to show traders at the mandi for better negotiation.

### Trigger

User types:
- "price brief do"
- "negotiation card banao"
- "mandi jaane se pehle brief chahiye"

### Step-by-Step Flow

**Step 1 -- Bedrock Agent Processing**
- **Intent**: `NEGOTIATION`.
- The agent orchestrates multiple tool calls to gather comprehensive price intelligence.

**Step 2 -- Tool Invocations** (agent may chain multiple calls)
1. `query_mandi_prices` -- gets current price at user's local mandi.
2. `get_nearby_mandis` -- gets prices at comparable mandis within radius.
3. `get_msp` -- gets MSP reference price.
4. `get_price_trend` -- gets 7-day and 30-day trends.

**Step 3 -- Agent Response**
- Generates a structured, shareable **Price Brief** formatted as:
  ```
  ===================================
    MandiMitra Price Brief
    Wheat -- 28 Feb 2026
  ===================================
    MSP Reference:       Rs.2,275/quintal
    Your Mandi (Indore): Rs.2,350/quintal
    Best Nearby (Dewas): Rs.2,420 (38km)
    7-Day Trend:         +1.8%
    Fair Price Range:    Rs.2,350 -- Rs.2,450
  -----------------------------------
    Nearby Mandis:
    - Dewas: Rs.2,420 (38km)
    - Ujjain: Rs.2,310 (55km)
    - Bhopal: Rs.2,380 (190km)
  -----------------------------------
    Source: Agmarknet | 28-Feb-2026
    MandiMitra -- Farmer's Companion
  ===================================
  ```
- Includes a suggestion to share on WhatsApp and show to the trader.

**Step 4 -- UI Rendering**
- Formatted brief in chat bubble (monospace-style layout preserved via line breaks).
- **WhatsApp share button** is prominent — opens `wa.me/?text=<encoded_brief>`. Farmer taps to forward the Price Brief to any WhatsApp contact or group (trader, cooperative, family member).
- Copy button for clipboard.
- Price chart comparing nearby mandis.

> **Sharing design note:** All MandiMitra responses include a WhatsApp share button (opens `wa.me/?text=...`). There is **no PDF download** functionality — sharing is exclusively via WhatsApp text forwarding or clipboard copy. This is intentional: WhatsApp is the primary communication channel for Indian farmers, and text-based sharing works even on 2G/low-bandwidth connections.

---

## 9. Voice Input Flow

**Purpose:** User speaks their query in Hindi or English instead of typing. Critical for farmers with limited literacy.

### Trigger

User taps the microphone button in the `ChatInput` component, or taps the "Hindi mein bolkar puchen" hint.

### Step-by-Step Flow

**Step 1 -- Voice Support Check** (`frontend/app/lib/voice.ts`)
- On component mount, `isVoiceSupported()` checks for `window.SpeechRecognition` or `window.webkitSpeechRecognition`.
- If unsupported, the mic button is hidden entirely.

**Step 2 -- Start Listening**
- User taps mic button -> `handleVoice()` in `ChatInput`.
- `startListening(language, onResult, onError)` is called.
- Creates a new `SpeechRecognition` instance.
- Configures:
  - `lang`: `"hi-IN"` for Hindi, `"en-IN"` for English.
  - `continuous`: false (single utterance).
  - `interimResults`: false (only final transcript).
  - `maxAlternatives`: 1.
- Calls `recognition.start()`.
- UI: mic button turns red with pulsing animation (`voice-pulse` CSS class), hint text changes to "Listening... (tap to stop)".

**Step 3 -- Speech Recognition**
- Browser's Web Speech API processes audio from the device microphone.
- For Hindi (`hi-IN`), the API handles Devanagari script transcription.
- For English (`en-IN`), uses Indian English model.

**Step 4 -- Result Handling**
- `recognition.onresult` fires with the transcript.
- `onResult(transcript)` callback:
  - Appends the transcript to the current input text (allows multi-utterance building).
  - Sets `isListening` to false.
  - Mic button returns to normal state.
- The transcript now appears in the text input field.
- User can edit the text if needed, then tap Send.

**Step 5 -- Sending**
- User taps the Send button (or presses Enter).
- From here, the flow is identical to any text input flow -- the transcript is sent as the message to `/api/chat`.

### Voice Error Handling

- **"not-allowed" / "service-not-allowed"**: "Microphone permission denied. Please allow microphone access in your browser settings."
- **"no-speech"**: "No speech detected. Please try again and speak clearly."
- **Recognition ends without result**: "No speech detected. Please tap the mic and speak clearly."
- **`recognition.start()` throws**: "Could not start voice input. Please try again."
- All errors display as a red pill-shaped banner above the input, auto-clearing after 4 seconds.

---

## 10. Location Selection Flow

**Purpose:** Establish the user's location so GPS coordinates can be injected into every query for nearby mandi lookups and transport cost calculations.

### Trigger

- **Auto-trigger**: `LocationPicker` modal opens automatically 800ms after first page load if no location is set.
- **Manual trigger**: User taps the location label in the `ChatHeader` to change location.

### Step-by-Step Flow

**Step 1 -- Location Picker Modal Opens** (`frontend/app/components/LocationPicker.tsx`)
- Modal appears with two options:
  1. **Live GPS** button at the top.
  2. **State/City selection** list below.

**Step 2a -- GPS Path**
- User taps "Live Location (GPS)".
- `navigator.geolocation.getCurrentPosition()` is called with `enableHighAccuracy: true`, `timeout: 15000`.
- On success: `onSelectLocation({latitude, longitude, label: "Live GPS", state: ""})`.
- On permission denied (error code 1): Shows yellow warning message in Hindi/English suggesting the user select state/city manually instead.
- On other errors: Shows generic GPS error with fallback suggestion.

**Step 2b -- Manual Selection Path**
- User taps a state (e.g., "Madhya Pradesh") from the list of 11 agricultural states.
- Drills into city list (e.g., Indore, Bhopal, Ujjain, Gwalior, etc.).
- User taps a city, or taps "Entire state" to use state-level coordinates.
- `onSelectLocation({latitude: 22.72, longitude: 75.86, label: "Indore, Madhya Pradesh", state: "Madhya Pradesh", city: "Indore"})`.

**Step 3 -- State Stored in Frontend**
- `page.tsx` receives the location:
  - `userLocation` = `{latitude, longitude}` -- injected into every `/api/chat` POST payload.
  - `locationLabel` = display string for the header (e.g., "Indore, Madhya Pradesh").
  - `locationState` = state name -- used by `QuickActions` to construct location-aware queries.
  - `locationCity` = city name -- used by `QuickActions` and `WelcomeScreen`.
  - `locationStatus` = `"granted"`.

**Step 4 -- Location Injection into Queries**
- Every subsequent `sendMessage()` call includes `latitude` and `longitude` in the POST body.
- The Chat Handler Lambda injects these into the augmented message:
  ```
  [User GPS location: latitude=22.72, longitude=75.86. Use this for nearby mandi lookups and transport cost calculations.]
  ```
- `QuickActions` constructs location-aware quick action queries (e.g., "soyabean ka bhav batao Indore mein" instead of generic queries).

### Available Locations

13 states with 2-8 cities each, covering major agricultural regions:
Madhya Pradesh, Rajasthan, Maharashtra, Uttar Pradesh, Gujarat, Punjab, Haryana, Karnataka, Tamil Nadu, Andhra Pradesh, West Bengal, Bihar, Chhattisgarh.

---

## 11. Data Freshness Flow

**Purpose:** Ensure users always know whether they are seeing today's live data or historical data, since Agmarknet mandis finalize auction data at 5:00 PM IST.

### How Data Gets Into the System

1. **Source**: data.gov.in Agmarknet API (resource ID: `9ef84268-d588-465a-a308-a864a43d0070`).
2. **Ingestion**: `mandimitra-data-ingestion` Lambda, triggered by EventBridge schedule.
3. **Schedule**: Daily at 9:30 PM IST (4:00 PM UTC) -- ensuring all Agmarknet data is fully propagated and available.
4. **Process**: For each of 15 commodities x 9 states:
   - Fetches from data.gov.in API with state and commodity filters.
   - Transforms records: parses dates (dd/mm/yyyy to ISO), validates prices (modal between min/max with 5% tolerance, positive, realistic range Rs.1 to Rs.5,00,000, not future-dated).
   - Batch writes to DynamoDB `MandiMitraPrices` table.
   - Stores audit log in S3.

### How Data Freshness Is Determined

In `price_query/handler.py`, the `query_mandi_prices` function:

1. Fetches prices for the requested commodity/state/mandi.
2. Gets `latest_date` from the most recent record's `arrival_date`.
3. Compares against `today` (UTC) and `yesterday`:
   ```python
   data_freshness = "today" if latest_date == today else (
       "yesterday" if latest_date == yesterday else f"last_available:{latest_date}"
   )
   ```
4. Separates `today_prices` and `previous_day_prices` into distinct arrays.
5. Adds a `note` field if today's prices are not yet available:
   ```
   "Data sourced from Agmarknet. Mandi prices are finalized daily by 5:00 PM IST."
   ```

### How the Agent Communicates Freshness

The orchestrator prompt instructs the agent:
- If `data_freshness` is NOT "today", ALWAYS state clearly:
  - Hindi: "yeh kal (pichle karobari din) ka bhav hai"
  - English: "This is yesterday's (last trading day) price"
- If `today_prices` is empty but `previous_day_prices` exists: "Aaj ka data abhi uplabdh nahi hai, pichle din ka bhav dikha rahe hain."
- When both today and previous day prices exist, show BOTH and highlight the change.

### Timeline for a Typical Day

| Time (IST) | Event |
|-------------|-------|
| Morning | Mandi auctions begin |
| By 5:00 PM | Agmarknet finalizes daily data (per DMI guidelines) |
| 9:30 PM | MandiMitra ingestion Lambda runs |
| 9:30 PM+ | Today's data becomes available in queries |
| Before 9:30 PM | Queries return yesterday's data with freshness note |

---

## 12. Fallback Strategy

**Purpose:** Ensure users get useful results even when their query does not exactly match the data in DynamoDB, because users often name cities or districts rather than official APMC market names.

### Fallback Chain for `query_prices()` (commodity + state + mandi)

**Level 1 -- Exact Mandi Match**
- DynamoDB query with PK = `{COMMODITY}#{STATE}` and SK range `{start_date}#{MANDI_UPPER}` to `{end_date}#{MANDI_UPPER}~`.
- Example: User says "Karnal" -> queries for SK containing `KARNAL`.

**Level 2 -- APMC Suffix Match**
- If Level 1 returns no items, tries suffixes:
  - `{MANDI} APMC` (e.g., "KARNAL APMC")
  - `{MANDI}(GRAIN)` (e.g., "KARNAL(GRAIN)")
  - `{MANDI}(F&V)` (e.g., "KARNAL(F&V)")
- Stops at first suffix that returns results.

**Level 3 -- All Historical (No Date Filter)**
- If Levels 1-2 fail, queries the full PK without date range (ScanIndexForward=False, Limit=20).
- Filters results by mandi name containing the search term.

**Level 4 -- District Match**
- If mandi name filter returns nothing, tries matching the `district` field.
- Example: "Karnal" is a district -> finds "INDRI APMC" which is in Karnal district.

**Level 5 -- All Available Data**
- If nothing matches, returns whatever records exist for this commodity+state.
- Agent clearly communicates that exact mandi was not found and shows available data.

### Fallback Chain for `query_mandi_prices()` (all commodities at a mandi)

**Level 1 -- Exact Match via MANDI-INDEX GSI**
- Queries GSI with `mandi_name = {MANDI_UPPER}` and `date_commodity` range.

**Level 2 -- APMC Suffix via GSI**
- Tries suffixes on the GSI: `{MANDI} APMC`, `{MANDI}(GRAIN)`, `{MANDI}(F&V)`.
- No date filter, Limit=50, ScanIndexForward=False.

**Level 3 -- District Scan**
- Full table scan with `FilterExpression: Attr("district").eq(mandi)`.
- Paginates through all results.

**Level 4 -- Partial Name Scan**
- Full table scan with `FilterExpression: Attr("mandi_name").contains(MANDI_UPPER)`.
- Paginates through all results.

### Fallback Chain for `get_mandi_profile()`

Follows the same 4-level chain as `query_mandi_prices()`, with the addition of matching `Attr("district").eq(mandi.strip())` in the scan fallback.

### Weather Location Resolution

1. Exact match in `MANDI_COORDINATES` (uppercase).
2. Title case match in `MANDI_COORDINATES`.
3. Fuzzy match: checks if the location string is contained in any coordinate key or vice versa.
4. If all fail: returns error "Location not found. Try a major city name."

---

## 13. Error Handling

### Voice Input Errors

| Error Condition | User-Facing Message | Behavior |
|-----------------|---------------------|----------|
| Browser does not support Web Speech API | Mic button is hidden entirely | `isVoiceSupported()` returns false |
| Microphone permission denied (`not-allowed`) | "Microphone permission denied. Please allow microphone access in your browser settings." | Red banner, auto-clears in 4s |
| No speech detected (`no-speech`) | "No speech detected. Please try again and speak clearly." | Red banner, auto-clears in 4s |
| Recognition ends without any result | "No speech detected. Please tap the mic and speak clearly." | Red banner, auto-clears in 4s |
| `recognition.start()` throws exception | "Could not start voice input. Please try again." | Red banner, auto-clears in 4s |
| Other speech errors | "Voice error: {error}" | Red banner, auto-clears in 4s |

### API / Network Errors

| Error Condition | Handling |
|-----------------|----------|
| `fetch()` to `/api/chat` fails (network error, non-200 status) | Catches in `sendMessage()` try/catch. Shows localized error message: Hindi: "Maaf karen, kuch gadbad ho gayi. Kripya dobara puchen." English: "Sorry, something went wrong. Please try again." Error logged to console. |
| Chat Handler Lambda receives invalid JSON body | Returns 400: `{"error": "Invalid JSON body"}` |
| Chat Handler receives empty message | Returns 400: `{"error": "Message is required"}` |
| Bedrock Agent invocation fails | Catches exception, logs to LangFuse with ERROR level. Returns 500: `{"error": "Failed to process your query. Please try again.", "detail": "..."}` |
| Bedrock Agent returns empty response chunks | **Fallback 1**: Extracts answer from trace `<answer>` tags (parsed from `modelInvocationOutput.rawResponse.content`). **Fallback 2**: Retries the entire agent invocation with `enableTrace=False` and a new session ID suffix `-retry`. |

### Action Group / Tool Errors

| Error Condition | Handling |
|-----------------|----------|
| Unknown function name | Returns `{"error": "Unknown function: {name}"}` in the action group response. Agent interprets and communicates to user. |
| DynamoDB query returns no data | Returns empty arrays. Agent follows orchestrator prompt: explains data is from Agmarknet live API, suggests checking other commodities or nearby mandis. |
| Exception in any tool function | Caught by try/except in `handle_agent_action()`. Returns `{"error": "{exception message}"}` in the action group response envelope. Logged with full traceback. |
| Weather API (Open-Meteo) fails or times out | Returns `{"error": "Weather API error: {message}"}`. Agent communicates the failure and suggests retrying. |
| Weather location not found | Returns `{"error": "Location '{name}' not found. Try a major city name."}` |
| Mandi coordinates not found (for transport cost) | Returns `{"error": "Mandi '{name}' coordinates not found"}` |

### Data Quality Errors (Ingestion Time)

The data ingestion Lambda validates each record before writing to DynamoDB:

| Validation Rule | Action on Failure |
|-----------------|-------------------|
| Modal price outside min-max range (5% tolerance) | Record skipped with warning log |
| Price < Rs.1 or > Rs.5,00,000 | Record skipped as unrealistic |
| Date is in the future | Record skipped |
| Missing market name or arrival date | Record skipped |
| Modal price is null/missing | Record skipped |

### Demo Mode Fallback

When `NEXT_PUBLIC_API_URL` environment variable is not set (frontend deployed without backend):
- `sendMessage()` detects empty `API_BASE`.
- Calls `simulateResponse()` instead of making a real API call.
- Returns pre-built demo responses for price check, sell advisory, negotiation brief, and a default greeting.
- Demo responses include realistic agent trace data for the UI to render.
- Latency is simulated with a 1.5-2.5 second delay.

---

## Appendix: Action Group and Function Reference

### Action Group 1: PriceIntelligenceTools (5 functions)

| Function | Parameters | Purpose |
|----------|-----------|---------|
| `query_mandi_prices` | commodity, state, mandi?, days? | Price lookup with trend + MSP + data freshness |
| `get_nearby_mandis` | latitude, longitude, radius_km, commodity? | GPS-based mandi finder with net realization |
| `get_price_trend` | commodity, state, mandi?, days? | Trend direction, change%, volatility, data points |
| `get_msp` | commodity | MSP lookup for 20 commodities (2025-26 rates) |
| `get_sell_recommendation` | commodity, state, latitude, longitude, quantity_qtl, storage_available? | Comprehensive sell/hold advisory data |

### Action Group 2: MandiTools (2 functions)

| Function | Parameters | Purpose |
|----------|-----------|---------|
| `get_all_prices_at_mandi` | mandi, days? | All commodity prices at a mandi, grouped |
| `get_mandi_profile` | mandi, days? | Comprehensive mandi profile with Agmarknet details |

### Action Group 3: BrowseTools (3 functions)

| Function | Parameters | Purpose |
|----------|-----------|---------|
| `list_available_commodities` | state? | List all commodities in database |
| `list_available_mandis` | state? | List all mandis with district info |
| `list_available_states` | (none) | List all states with data |

### Action Group 4: WeatherTools (1 function)

| Function | Parameters | Purpose |
|----------|-----------|---------|
| `get_weather_advisory` | location, latitude?, longitude? | 5-day forecast + agricultural advisory |

**Additional function** (called via PriceIntelligenceTools but defined separately):

| Function | Parameters | Purpose |
|----------|-----------|---------|
| `calculate_transport_cost` | origin_lat, origin_lon, dest_mandi, quantity_qtl | Transport cost calculation using haversine distance |

**Total: 13 functions across 4 action groups.**

---

## v2 Roadmap (Post-Hackathon)

The following features are **intentionally deferred to v2** to maintain focus on the core use case for the hackathon deadline:

| Feature | Why Deferred | Notes |
|---------|-------------|-------|
| **Multi-language support** (regional languages beyond Hindi/English) | Requires curated translations for 15+ languages, testing with native speakers | v1 supports Hindi + English only |
| **WhatsApp Business API integration** | Requires WhatsApp Business API access ($), monthly subscription costs | v1 uses `wa.me/?text=...` deep link which is free |
| **Bedrock Knowledge Base (RAG)** | Requires additional AWS setup (OpenSearch Serverless), adds latency; current tool-based approach is faster and more accurate for structured price data | Would add MSP circulars, government scheme docs |
| **SMS/USSD fallback** | Needs telecom partnership, significant infra investment | Important for feature-phone users |
| **Marketplace integration** | Direct connection to APMC e-trading platforms | Requires APMC agreements |
| **Farmer credit/loan advisory** | Needs RBI/fintech partner integration | Out of scope for market intelligence tool |
| **Crop yield prediction** | Needs satellite/IoT data feeds | Agricultural ML model |
| **Group/cooperative features** | Multi-user sessions, shared price alerts | Requires user accounts and persistent sessions |
