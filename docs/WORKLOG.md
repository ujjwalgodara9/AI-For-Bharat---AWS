# MandiMitra — Work Log

Track of everything done, in chronological order.

---

## Feb 25, 2026

### Done
1. **PLAN.md created** — Full 5-day execution plan with day-by-day tasks, demo video script, submission checklist
2. **TEAM_HANDOFF.md created** — Status document for teammates
3. **Frontend scaffolded** — Next.js 14 + Tailwind CSS project
4. **Frontend components built:**
   - ChatHeader (logo, lang toggle, live indicator)
   - ChatBubble (message bubbles + expandable agent trace panel)
   - ChatInput (text + voice mic + send button)
   - QuickActions (4 quick action buttons in Hindi/English)
   - TypingIndicator (animated thinking dots)
   - WelcomeScreen (4 feature cards, data source badge)
   - Voice input (Web Speech API — Hindi + English)
   - API client with types
   - Demo mode simulator (works without backend)
5. **Frontend verified** — Builds clean, runs on localhost:3000
6. **Backend Lambdas written:**
   - data_ingestion/handler.py — Agmarknet API → DynamoDB pipeline
   - chat_handler/handler.py — Bedrock Agent invocation + LangFuse tracing
   - price_query/handler.py — Price queries + Bedrock Agent action groups
   - shared/constants.py — MSP rates, commodities, mandi GPS coords
   - shared/dynamodb_utils.py — DB queries, Haversine, trend analysis
7. **Agent configs written:**
   - orchestrator_prompt.txt, price_intel_prompt.txt, sell_advisory_prompt.txt, negotiation_prep_prompt.txt
   - price_intel_openapi.json (OpenAPI spec for action groups)
8. **Infrastructure:**
   - SAM template (template.yaml) — DynamoDB + Lambda + API Gateway + S3 + EventBridge
   - setup_aws.sh — manual AWS setup script
   - BEDROCK_SETUP_GUIDE.md — step-by-step agent creation guide
9. **Project docs:** README.md, .env.example, .gitignore

---

## Feb 27, 2026

### Done
10. **AWS Credits received** — $100 from hackathon
11. **Data sources identified:**
    - data.gov.in — Variety-wise daily market prices + Current daily prices
    - enam.gov.in — Trade data dashboard
    - ncdex.com — Commodity heatmap
    - agmarknet.gov.in — Mandi profiles + Daily price/arrival reports
    - Weather APIs — multiple available
12. **Starting AWS deployment and data pipeline integration**

13. **Data fetch script created** — `backend/scripts/fetch_data_local.py`
    - Fetches from both data.gov.in APIs (current daily + historical variety-wise)
    - Handles rate limiting with exponential backoff retry
    - Transforms to DynamoDB item format
    - Tested: 239 records fetched (100 current + 140 historical)
    - Confirmed real Feb 2026 data: Tomato Rs.1900 Punjab, Soyabean, Wheat, Onion, etc.
14. **Data APIs validated:**
    - Current prices: resource ID `9ef84268-d588-465a-a308-a864a43d0070` — 16,588 records available
    - Historical prices: resource ID `35985678-0d79-46b4-9ed6-6f13308a1d24` — 77M+ records
    - Both return: state, district, market, commodity, variety, grade, arrival_date, min/max/modal price
    - Demo API key works but rate-limited (10 records/call). Own API key needed for full data.
15. **eNAM trade data reviewed** — Has internal Ajax APIs (`Ajax_ctrl/trade_data_list`) but no public API. Can scrape if needed.

### Waiting On (from Ujjwal) — ALL RESOLVED
- [x] AWS CLI Access Keys — received & configured (account 471112620976)
- [ ] data.gov.in personal API key — using demo key (rate-limited but works)
- [x] Bedrock model access — Claude models need agreement form (NOT_AVAILABLE), switched to Amazon Nova Pro/Lite (immediately available, better fit for AWS hackathon)

---

## Feb 27–28, 2026 (Night Session — AWS Deployment)

### Done

16. **AWS CLI installed & configured**
    - `pip install awscli`, configured with Access Key `AKIAW3MEADOYBLMMIDHL`
    - Account: 471112620976, Region: us-east-1
    - Verified IAM identity works

17. **Bedrock model access investigation**
    - Claude models (Sonnet, Haiku): `agreementAvailability: NOT_AVAILABLE` — need EULA form in AWS Console
    - Tried creating agreement via CLI → `AccessDeniedException: You have not filled out the request form`
    - **Solution: Switched to Amazon Nova Pro/Lite** — fully AVAILABLE without forms
    - Tested Nova Lite: successfully returned Hindi response ("नमस्ते")
    - This is actually BETTER for an AWS hackathon (AWS's own model)

18. **DynamoDB table created** — `MandiMitraPrices`
    - PK: `COMMODITY#STATE`, SK: `DATE#MANDI`
    - GSI-1 `MANDI-INDEX`: mandi_name + date_commodity
    - GSI-2 `DATE-INDEX`: arrival_date + PK
    - Billing: PAY_PER_REQUEST (serverless, cost-efficient)
    - ARN: `arn:aws:dynamodb:us-east-1:471112620976:table/MandiMitraPrices`

19. **Data loaded into DynamoDB** — 239 records
    - Created `backend/scripts/load_dynamodb.py` — batch_write with retry
    - All 239 items loaded, 0 failures
    - Verified: `SOYABEAN#MADHYA_PRADESH` query returns 3+ items
    - Data includes: Soyabean, Wheat, Onion, Tomato, Potato, Mustard, Cotton, Maize, Paddy, Groundnut across 8 states

20. **S3 bucket created** — `mandimitra-deployment-471112620976`
    - Used for Lambda deployment packages and agent configs

21. **IAM roles created:**
    - `MandiMitraLambdaRole` — for Lambda functions (DynamoDB, Bedrock, S3, CloudWatch access)
    - `MandiMitraBedrockAgentRole` — for Bedrock Agent (Bedrock + Lambda invoke)

22. **Lambda functions deployed (3 functions):**
    - `mandimitra-price-query` (Python 3.12, 256MB, 30s timeout) — price lookups + agent action groups
    - `mandimitra-data-ingestion` (Python 3.12, 512MB, 300s timeout) — data.gov.in → DynamoDB
    - `mandimitra-chat` (Python 3.12, 256MB, 60s timeout) — Bedrock Agent invocation
    - All packaged as zips, uploaded to S3, deployed via AWS CLI

23. **Lambda code fixes during deployment:**
    - `dynamodb_utils.py` PK format mismatch: query used `MADHYA PRADESH` but data had `MADHYA_PRADESH` → fixed `.upper().replace(" ", "_")`
    - Added fallback query: if no recent data found (days=7), auto-queries ALL historical data
    - MSP lookup made case-insensitive (agent sends lowercase, constants have title case)
    - Repackaged and updated Lambda 3 times to fix these issues

24. **Price query Lambda tested successfully:**
    - Direct invoke: `query_prices("Soyabean", "Madhya Pradesh")` → 10 records returned
    - Returns real prices: Shamshabad Rs.1345, Kurwai Rs.1854, etc.
    - MSP lookup works: Wheat → Rs.2275, Soyabean → Rs.4892

25. **API Gateway created** — `MandiMitraAPI` (ID: `skwsw8qk22`)
    - `POST /api/chat` → mandimitra-chat Lambda
    - `GET /api/prices/{commodity}` → mandimitra-price-query Lambda
    - CORS configured (OPTIONS methods with headers)
    - Lambda invoke permissions added
    - Deployed to `prod` stage
    - **Live URL: `https://skwsw8qk22.execute-api.us-east-1.amazonaws.com/prod`**

26. **API Gateway tested:**
    - `GET /api/prices/Soyabean?state=Madhya%20Pradesh&days=0` → returns real price data ✅

27. **Bedrock Agent created** — `MandiMitra` (ID: `GDSWGCDJIX`)
    - Foundation model: `amazon.nova-lite-v1:0`
    - Orchestrator prompt loaded from `orchestrator_prompt.txt`
    - Action group: `PriceIntelligenceTools` with 5 functions:
      - `query_mandi_prices`, `get_nearby_mandis`, `get_price_trend`, `get_msp`, `get_sell_recommendation`
    - Note: Bedrock limits 5 params per function — reduced `get_sell_recommendation` from 6 to 5 params
    - Note: OpenAPI spec format failed validation — switched to `functionSchema` format (simpler)
    - Agent prepared and alias created: `BM6JROSWME`
    - Lambda permission added for Bedrock to invoke price_query

28. **Bedrock Agent tested end-to-end:**
    - Query: "soyabean ka bhav batao madhya pradesh mein"
    - Agent reasoning: identified PRICE_CHECK intent, called `query_mandi_prices` tool
    - Tool returned real data from DynamoDB
    - Response: "किसान भाई, सोयाबीन का भाव मध्य प्रदेश में ₹1345.0 प्रति क्विंटल है" ✅
    - 9 trace steps captured (preprocessing, reasoning, tool call, observation, final response)

29. **Chat API (POST /api/chat) — debugging & fix:**
    - **Problem:** API returned `"response": ""` even though Lambda captured 118-char response
    - **Investigation:** CloudWatch logs showed `Raw bytes type: bytes, len: 248` — bytes received
    - Lambda logged `Response parts count: 1, sizes: [118]`, `Full response length: 118` — text captured
    - But API Gateway returned empty string
    - **Root cause:** `json.dumps(body, ensure_ascii=False)` with Hindi text caused serialization issue through API Gateway proxy
    - **Fix:** Changed to `ensure_ascii=True` + explicit `Content-Type: application/json; charset=utf-8` + direct return dict
    - After fix: `wheat MSP?` → 1458 chars response ✅

30. **Nova Lite quality issue identified:**
    - Simple queries (MSP lookup) work great
    - Complex queries with large tool output (soyabean prices with 10 records) → garbled response (lots of "0 0 0 0")
    - **Next step: Switch to Nova Pro** for better quality Hindi responses

31. **Switched to Nova Pro — fixed garbled responses**
    - Updated agent foundation model: `amazon.nova-lite-v1:0` → `amazon.nova-pro-v1:0`
    - Re-prepared agent, same alias works
    - Tested complex soyabean query: clean Hindi response with structured price data ✅
    - Response: "मध्य प्रदेश में सोयाबीन का भाव: मोडल मूल्य: ₹1854.00/क्विंटल..."
    - Latency: ~3.9s (acceptable for chat)

32. **Frontend connected to live API**
    - Created `frontend/.env.local` with `NEXT_PUBLIC_API_URL=https://skwsw8qk22.execute-api.us-east-1.amazonaws.com/prod/api`
    - Frontend auto-switches from demo mode to real API calls
    - Updated "Powered by" text to "Amazon Bedrock Agents + Amazon Nova AI"

33. **Frontend deployed to S3 static hosting**
    - Added `output: "export"` to `next.config.mjs` for static site generation
    - Build successful: 94.5 kB first load JS
    - Created S3 bucket: `mandimitra-frontend-471112620976` with static website hosting
    - Set public read access policy
    - Uploaded all static files
    - **LIVE URL: `http://mandimitra-frontend-471112620976.s3-website-us-east-1.amazonaws.com`**
    - Verified: HTTP 200 ✅

34. **Loaded 220 more records into DynamoDB:**
    - Ran `fetch_more_data.py` — fetched 220 records from historical API (11 commodities, 9 states, 30 mandis)
    - Loaded into DynamoDB — total now **379 records** (deduped by PK/SK)
    - Commodities: Wheat, Soyabean, Onion, Tomato, Potato, Mustard, Cotton, Maize, Rice, Gram, Garlic, Groundnut, Bajra

35. **Fixed empty response bug (intermittent):**
    - **Problem:** Some queries returned `response: ""` through API Gateway even though Bedrock Agent produces correct answer
    - **Investigation:** CloudWatch showed `Chunk keys: ['bytes']` but `Raw bytes type: bytes, len: 0` — Bedrock sends empty chunk
    - However, the answer IS in the trace: `modelInvocationOutput.rawResponse.content` contains nested JSON with `<answer>` tag
    - **Root cause:** Bedrock Agent runtime sometimes sends empty bytes in the completion chunk but includes the full answer in the trace's raw model output
    - **Fix:** Added trace fallback — parse `rawResponse.content` JSON → extract `text` field → find `<answer>` tag → use as response
    - After fix: Price check returns 467-804 char responses with detailed mandi prices ✅

36. **Tested all 4 chat flows through API Gateway:**
    - ✅ **Price Check:** "wheat ka bhav MP mein" → 4 mandis with prices, trend, MSP (804 chars, 4.3s)
    - ⚠️ **Best Mandi:** Agent asks for lat/lon instead of using state data directly — needs prompt fix
    - ✅ **Sell Advisory:** "cotton stock hai, bechun ya ruk jaaun? Gujarat" → clear sell/hold recommendation (248 chars, 7.1s)
    - ✅ **Negotiation:** "rice bechne Punjab mein, negotiate kaise?" → price card with trend, MSP, negotiation tips (522 chars, 9.1s)
    - Increased Lambda memory to 512MB for faster cold starts, timeout set to 29s (API Gateway limit)

37. **Fixed agent alias version mismatch — root cause of empty responses:**
    - **Problem:** Price check returned empty response intermittently through API Gateway
    - **Investigation:** Direct Bedrock call worked fine; Lambda call returned empty chunks
    - **Root cause:** Agent alias `BM6JROSWME` was pointing to version 1 (old prompt), while DRAFT had updated prompt with new rules
    - AWS CLI v1 doesn't support `create-agent-version`, so couldn't create version 2
    - **Fix:** Switched Lambda to use `TSTALIASID` (test alias, points to DRAFT)
    - After fix: Price check returns consistently (3/3 tests passed, 545 chars each) ✅
    - All 4 flows now pass consistently

38. **Updated agent prompt for better user experience:**
    - Added rules: never ask for lat/lon, use state data directly
    - For best mandi queries, compare all mandis in the state by price
    - Updated Bedrock Agent instruction and prepared agent

39. **Frontend redeployed to S3:**
    - Rebuilt with latest config
    - Uploaded 20 files to S3 static hosting
    - Live at same URL

### Current Status (Feb 28, 2026)
- **ALL 4 FLOWS WORKING END-TO-END:**
  - Frontend (S3 static) → API Gateway → Chat Lambda → Bedrock Agent (Nova Pro) → Tool Lambda → DynamoDB → Hindi response ✅
- **Live URLs:**
  - Frontend: `http://mandimitra-frontend-471112620976.s3-website-us-east-1.amazonaws.com`
  - API: `https://skwsw8qk22.execute-api.us-east-1.amazonaws.com/prod/api`
- **All 4 flows tested and passing**, with traces enabled for UI
- **379 records** in DynamoDB across 11+ commodities, 9 states, 30+ mandis

### AWS Resources Created (Cost Tracking)
| Resource | Name/ID | Cost Model |
|----------|---------|------------|
| DynamoDB | MandiMitraPrices (379 items) | PAY_PER_REQUEST (~$0) |
| S3 (deploy) | mandimitra-deployment-471112620976 | ~$0 |
| S3 (frontend) | mandimitra-frontend-471112620976 | ~$0 |
| Lambda x3 | mandimitra-{price-query,data-ingestion,chat} (512MB) | Pay per invoke (~$0) |
| API Gateway | skwsw8qk22 | Pay per request (~$0) |
| Bedrock Agent | GDSWGCDJIX / alias BM6JROSWME (Nova Pro) | ~$0.002/call |
| IAM Roles x2 | MandiMitraLambdaRole, MandiMitraBedrockAgentRole | Free |
| **Estimated spend so far:** | **< $2.00** | Testing invocations |

### Remaining Tasks
- [x] Fix Best Mandi flow — agent uses state data now
- [x] Fix empty response bug — alias version mismatch
- [x] Rebuild and redeploy frontend
- [ ] Record demo video (4-5 min)
- [ ] Write project summary for submission
- [ ] Submit on Hack2skill dashboard by March 4

---

## Mar 1, 2026

### Done

40. **Dynamic crop lists from DB** (commit 613726b)
    - `list_commodities_with_translations()` now filters to only tracked crops with known Hindi translations
    - Added deduplication (`seen` set) to prevent duplicate entries in crop picker
    - Crops fetched from live DynamoDB, not hardcoded

41. **Near-me radius fixed to 50km**
    - `get_nearby_mandis()` radius capped at 50km — more practical for farmers
    - Previously was returning mandis too far away to be actionable

42. **Commodity name sync**
    - Agent-sent commodity names (lowercase/varied casing) synced with DynamoDB PK format
    - `COMMODITY_TRANSLATIONS` used as canonical source for both UI labels and DB lookups

43. **Smart sell advisory improvements**
    - Enhanced sell/hold advisory to include price prediction trend
    - Added weather risk factor to sell timing recommendation
    - Storage tips and shelf life context in advisory output

44. **README.md updated** (unstaged) — reflects actual architecture:
    - Changed "3 specialist agents" to "1 orchestrator with 4 action groups, 13 functions"
    - Updated architecture diagram with CloudFront + S3 + Nova Pro
    - Replaced AWS Amplify with CloudFront in AWS services table
    - Removed LangFuse (not implemented) from architecture diagram

45. **LangFuse tracing activated** (Mar 1, 2026)
    - Installed `langfuse==2.60.10` (v2 API, pinned `<3.0.0` to avoid breaking API changes in v3)
    - Rebuilt `mandimitra-chat` Lambda zip with langfuse bundled (~6.8 MB)
    - Set Lambda env vars: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
    - Fixed API error: LangFuse v3 broke `.trace()` method; downgraded to v2.x
    - Verified: Lambda now sends trace → LangFuse cloud; all agent steps (reasoning, tool_call, observation, model_output) logged as spans
    - **LangFuse dashboard:** https://cloud.langfuse.com

46. **AWS resource verification** (Mar 1, 2026)
    - Confirmed agent aliases: `TSTALIASID` (DRAFT, active), `BM6JROSWME` ("prod", points to v1)
    - Lambda using `TSTALIASID` — correct for rapid iteration
    - CloudFront `d2mtfau3fvs243.cloudfront.net` — confirmed live and loading MandiMitra UI
    - API Gateway `skwsw8qk22` — confirmed responding to POST /api/chat with live Soyabean Indore price
    - DynamoDB: 4,730 items (count from describe-table; up from 4,467)

47. **Data ingestion triggered for 7-day historical data** (Mar 1, 2026)
    - Invoked `mandimitra-data-ingestion` Lambda async with `{"days_back": 7}`
    - Lambda will fetch 20 commodities × 14 states = 280 API calls to data.gov.in
    - Results should appear in DynamoDB within 15 minutes
    - Scheduled EventBridge will continue daily at 9:30 PM IST

48. **Documentation updates** (Mar 1, 2026)
    - FLOWS.md: Added WhatsApp sharing design note (no PDF, text-forward only)
    - FLOWS.md: Added v2 Roadmap section (multi-language, WhatsApp Business API, Knowledge Base, SMS/USSD, etc.)
    - ARCHITECTURE.md: Added LangFuse to AWS resources table, clarified agent alias strategy, added design decisions #14 (LangFuse) and #15 (WhatsApp sharing)
    - `backend/lambdas/chat_handler/requirements.txt`: Pinned langfuse to `>=2.0.0,<3.0.0`

### Current Status (Mar 1, 2026 PM — Post Claude Session)
- **DynamoDB:** 4,730+ records (ingestion running for more), 20 commodities, 14 states, 60+ mandis
- **CloudFront:** `d2mtfau3fvs243.cloudfront.net` — HTTPS, fully live ✅
- **LangFuse:** Active and tracing all Bedrock Agent interactions ✅
- **API:** Responding correctly — Soyabean Indore price returned live ✅
- **All flows working:** Price Check, Best Mandi, Sell Advisory, Weather, Browse, Negotiation Brief
- **Deadline:** March 4, 2026

### Remaining Tasks (Submission Sprint)
- [ ] Record demo video (4-5 min) — show all major flows in Hindi + English, use CloudFront URL
- [ ] Write project summary (200-word problem statement + 1-page overview)
- [ ] Commit all staged changes (README.md, WORKLOG.md, ARCHITECTURE.md, FLOWS.md, requirements.txt)
- [ ] Submit on Hack2skill dashboard by March 4
- [ ] Upload video to YouTube/Drive, add link to submission

---

## Mar 1, 2026 (Evening — Multi-Agent Architecture + Full Audit)

### Done

49. **Full AWS resource audit** (Mar 1, 2026 Evening)
    - Audited all services: Bedrock (5 agents), Lambda (3), DynamoDB (1 table), API Gateway, CloudFront, S3, IAM, EventBridge, Guardrails
    - **Critical finding:** EventBridge schedule for daily ingestion was NEVER created (README claimed it was running)
    - **Critical finding:** Bedrock Guardrails are EMPTY (README claimed they were active)
    - Full audit saved to `docs/AWS_AUDIT.md`

50. **Multi-Bedrock Agent architecture implemented** (Mar 1, 2026 Evening)
    - Upgraded from single-agent (GDSWGCDJIX) to 5-agent supervisor system
    - Created 4 specialist sub-agents:
      - MandiMitra-PriceIntelligence (CAEJ90IYS6) — price queries, nearby mandis, trends
      - MandiMitra-SellAdvisory (CCYSN80MGN) — sell/hold/split decisions
      - MandiMitra-Negotiation (UZRXDX75NR) — shareable price briefs
      - MandiMitra-Weather (XE43VNHO3T) — 5-day forecast + agri advisory
    - Wrote all 5 agent prompts in `backend/agent_configs/sub_agents/`
    - Set Supervisor to `agentCollaboration=SUPERVISOR` mode
    - Associated all 4 sub-agents as collaborators (`relayConversationHistory=TO_COLLABORATOR`)
    - **Tested:** Multi-agent routing verified — wheat query → PriceIntelligenceAgent, soyabean sell → SellAdvisoryAgent ✅

51. **Bug fixes during multi-agent setup**
    - Fixed `note_hi` KeyError in `_get_season_context()` — early return for unknown commodities was missing Hindi note key
    - Fixed Lambda zip structure — `shared/` must be subdirectory (not flat files) for `from shared.dynamodb_utils import` to work
    - Discovered Bedrock SDK quota: max 5 parameters per function in action groups
    - Discovered `create_agent_version` not in boto3 1.40.16 — workaround: omit `routingConfiguration` in alias creation (server auto-creates version snapshot)

52. **7-day historical data ingestion** (Mar 1, 2026)
    - Created `backend/scripts/fetch_7days.py` with explicit date filters (`filters[arrival_date]`)
    - Fixed DynamoDB BatchWriter duplicate key error — switched to individual `put_item` with dedup
    - DynamoDB: **5,191 items** (up from 4,467 initial)
    - Data range: Feb 23 – Mar 1, 2026

53. **Documentation restructured** (Mar 1, 2026 Evening)
    - Created `docs/` directory with `old_docs/` and `new_docs/`
    - Old docs preserved in `docs/old_docs/` (README_v1, ARCHITECTURE_v1, etc.)
    - New docs in `docs/new_docs/` (updated for multi-agent architecture)
    - Added `docs/new_docs/KNOWLEDGE_BASE_GUIDE.md` — full guide for Bedrock Knowledge Base setup
    - Updated root-level README.md and ARCHITECTURE.md

### Current Status (Mar 1, 2026 Evening)
- **DynamoDB:** 5,191 items, 7-day history, 20 commodities, 14 states ✅
- **Multi-agent:** Supervisor + 4 sub-agents, all PREPARED, routing verified ✅
- **LangFuse:** Active tracing ✅
- **CloudFront:** Live HTTPS ✅
- **EventBridge:** Still needs creation for daily auto-ingestion ❌
- **Deadline:** March 4, 2026

---

## Mar 2, 2026 (Infrastructure Hardening + Frontend Tests)

### Done

54. **EventBridge schedule CREATED** (Mar 2, 2026)
    - Rule: `mandimitra-daily-ingestion`, schedule `cron(0 16 * * ? *)` = 9:30 PM IST daily
    - Target: `mandimitra-data-ingestion` Lambda with `{"days_back": 1}` input
    - Lambda permission granted to EventBridge source ARN
    - This was the critical missing piece — daily ingestion now actually runs automatically

55. **Bedrock Guardrail CREATED** (Mar 2, 2026)
    - Created `MandiMitraGuardrail` (ID: `snlfs5xjb61l`)
    - v3 (final config): Only blocks financial investment advice + harmful content + profanity
    - Topic filters: `FinancialInvestment` (MCX/stocks/guaranteed profit) — only 1 topic (not OffTopic, too aggressive)
    - Content filters: SEXUAL/VIOLENCE/HATE HIGH, INSULTS/MISCONDUCT MEDIUM
    - PII protection: CREDIT_DEBIT_CARD_NUMBER blocked
    - Associated with supervisor agent GDSWGCDJIX
    - NOTE: v1 and v2 were too aggressive — blocked valid English crop price queries. v3 is the correct config.

56. **CloudWatch Alarms CREATED** (Mar 2, 2026) — 7 alarms:
    - `MandiMitra-ChatHandler-Errors` — ≥3 errors in 5 min
    - `MandiMitra-PriceQuery-Errors` — ≥3 errors in 5 min
    - `MandiMitra-DataIngestion-Errors` — ≥1 error in 5 min
    - `MandiMitra-ChatHandler-HighDuration` — p95 > 25s in 10 min
    - `MandiMitra-ChatHandler-Throttles` — ≥1 throttle in 5 min
    - `MandiMitra-DynamoDB-SystemErrors` — ≥1 system error
    - `MandiMitra-DynamoDB-ReadThrottles` — ≥5 throttles in 5 min

57. **Playwright frontend tests CREATED AND ALL PASSING** (Mar 2, 2026)
    - 7 tests: UI, Flow 1 (Price Check Hindi), Flow 2 (Best Mandi GPS), Flow 3 (Sell Advisory), Flow 4 (Negotiation Brief), Flow 5 (Weather), Flow 6 (English Query)
    - All 7 pass in 1.7 minutes against live CloudFront URL
    - Key fixes in test design:
      - Dismiss LocationPicker modal with `button:has-text("बाद में")` before interacting
      - Use `textarea:not([disabled])` selector (not just `textarea`)
      - Wait for `!body.includes('सोच रहा हूँ')` to detect response completion
    - **Notable results from tests:** Flow 5 (Weather) returned REAL weather data: "तापमान 15.9°C से 33.7°C" and price prediction ₹2590 (+8.4%)
    - Screenshots saved in `tests/screenshots/`

58. **Lambda fix: XML cleanup for sub-agent responses** (Mar 2, 2026)
    - Sub-agents were leaking `<AgentCommunication__sendMessage recipient="User" content="..." />` XML tags into responses
    - Added `clean_agent_response()` function in `backend/lambdas/chat_handler/handler.py`
    - Strips AgentCommunication XML tags and extracts content attribute
    - Deployed to Lambda

59. **Expanded data ingestion** (Mar 2, 2026)
    - Created `backend/scripts/fetch_all_india.py` (state+date strategy — 21 states)
    - Created `backend/scripts/fetch_30days.py` (28 commodities × 21 states × up to 30 days) ← **Primary script**
    - Running in background: 17,640 API calls for 30-day history
    - Data flowing: multiple records per commodity-state-date combination (e.g., 10 records for Wheat/MP/today)
    - Rate limit handling: automatic 30s backoff on 429 errors

### Current Status (Mar 2, 2026)
- **DynamoDB:** 5,200+ items and growing (background fetch active for 30 days × 28 crops × 21 states)
- **EventBridge:** LIVE — daily 9:30 PM IST auto-ingestion ✅
- **Guardrails:** LIVE — v3, light config, all agricultural queries allowed ✅
- **CloudWatch:** 7 alarms monitoring Lambda errors, duration, throttles, DynamoDB ✅
- **Playwright Tests:** 7/7 passing against live CloudFront URL ✅
- **Multi-agent:** All 5 agents PREPARED, Guardrail associated ✅
- **Deadline:** March 4, 2026 — **2 days remaining**

### Remaining Tasks
- [ ] Create EventBridge schedule for daily 9:30 PM IST ingestion
- [ ] Record demo video (4-5 min) — multi-agent flows
- [ ] Write project summary (200-word problem statement)
- [ ] Submit on Hack2skill by March 4
- [ ] Optional: Create Bedrock Knowledge Base (see docs/new_docs/KNOWLEDGE_BASE_GUIDE.md)

---
