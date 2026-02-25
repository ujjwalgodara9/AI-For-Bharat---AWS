# MandiMitra — Team Handoff & Status

**Last Updated:** 25 Feb 2026
**Deadline:** 1 Mar 2026 (internal) / 4 Mar 2026 (hackathon)

---

## WHAT'S DONE (Day 1 Progress)

### Frontend (100% scaffold done, demo mode working)
**Location:** `frontend/`

| File | What It Does | Status |
|------|-------------|--------|
| `app/page.tsx` | Main chat application — all state management, message handling, demo response simulator | DONE |
| `app/components/ChatHeader.tsx` | Top bar with MandiMitra logo, Hindi/English toggle, live indicator | DONE |
| `app/components/ChatBubble.tsx` | Message bubbles (user + bot) with expandable Agent Trace panel | DONE |
| `app/components/ChatInput.tsx` | Text input + voice mic button + send button | DONE |
| `app/components/QuickActions.tsx` | Quick action buttons (भाव देखो, कहाँ बेचूं, etc.) in Hindi & English | DONE |
| `app/components/TypingIndicator.tsx` | Animated "thinking" dots while AI processes | DONE |
| `app/components/WelcomeScreen.tsx` | Landing screen with 4 feature cards + data source badge | DONE |
| `app/lib/api.ts` | API client — types, chat API call, session management | DONE |
| `app/lib/voice.ts` | Web Speech API wrapper for Hindi/English voice input | DONE |
| `app/globals.css` | Custom styles — animations, scrollbar, Devanagari font | DONE |
| `app/layout.tsx` | Root layout with Hindi metadata, SEO tags | DONE |
| `tailwind.config.ts` | Custom MandiMitra color palette (green/saffron/mandi theme) | DONE |

**How to run:**
```bash
cd frontend
npm install    # already done
npm run dev    # opens at http://localhost:3000
```

**Demo mode:** The frontend works STANDALONE without any backend. It has a built-in `simulateResponse()` function in `page.tsx` that returns realistic mock data for all 4 flows (price check, best mandi, sell advisory, negotiation brief). This is triggered automatically when `NEXT_PUBLIC_API_URL` is not set.

---

### Backend Lambdas (100% code done, needs AWS deployment)
**Location:** `backend/`

| File | What It Does | Status |
|------|-------------|--------|
| `lambdas/data_ingestion/handler.py` | Fetches commodity prices from data.gov.in Agmarknet API → transforms → batch writes to DynamoDB. Covers 15 commodities × 9 states. | CODE DONE, needs deployment |
| `lambdas/chat_handler/handler.py` | Receives user message → invokes Bedrock Orchestrator Agent → streams response + trace → logs to LangFuse → returns JSON | CODE DONE, needs deployment |
| `lambdas/price_query/handler.py` | Dual-purpose: handles API Gateway direct price queries AND Bedrock Agent Action Group tool calls. Supports 6 functions: `query_mandi_prices`, `get_nearby_mandis`, `get_price_trend`, `get_msp`, `calculate_transport_cost`, `get_sell_recommendation` | CODE DONE, needs deployment |
| `lambdas/shared/constants.py` | All shared constants: tracked commodities (20), tracked states (14), MSP rates for 2025-26, perishability index, storage costs, transport cost rate, GPS coordinates for 30+ major mandis | DONE |
| `lambdas/shared/dynamodb_utils.py` | Database utility functions: price queries with GSI support, Haversine distance calculator, trend analysis (7/30-day MA, volatility, direction), net realization calculator, sell recommendation data aggregator | DONE |

---

### Bedrock Agent Configs (100% done, needs AWS Console setup)
**Location:** `backend/agent_configs/`

| File | What It Does |
|------|-------------|
| `orchestrator_prompt.txt` | System prompt for the Orchestrator Agent — intent classification (PRICE_CHECK, MANDI_COMPARE, SELL_ADVISORY, NEGOTIATION, GENERAL), language detection, response formatting rules, guardrail instructions |
| `price_intel_prompt.txt` | System prompt for Price Intelligence Agent — tool usage rules, data citation requirements, output format spec |
| `sell_advisory_prompt.txt` | System prompt for Sell Advisory Agent — full decision matrix (trend × perishability × storage → SELL/HOLD/SPLIT), output format with confidence % |
| `negotiation_prep_prompt.txt` | System prompt for Negotiation Prep Agent — price brief template format, fair price calculation formula |
| `price_intel_openapi.json` | OpenAPI 3.0 spec defining all 6 tool functions the agents can call — this gets uploaded to Bedrock Agent Action Groups |

---

### Infrastructure (100% done, needs AWS credentials to deploy)
**Location:** `infra/`

| File | What It Does |
|------|-------------|
| `template.yaml` | AWS SAM template — creates DynamoDB table (with 2 GSIs), S3 bucket, 3 Lambda functions, API Gateway with CORS, EventBridge daily schedule, IAM policies. Single `sam deploy` deploys everything. |
| `setup_aws.sh` | Manual alternative to SAM — bash script that creates resources one by one using AWS CLI |
| `BEDROCK_SETUP_GUIDE.md` | Step-by-step guide (with screenshots-worth of detail) to create all 4 Bedrock Agents, add action groups, configure guardrails, test in console |

---

### Project Docs
| File | What It Does |
|------|-------------|
| `README.md` | GitHub-ready README with architecture, quick start, demo flows, impact numbers |
| `PLAN.md` | Full 5-day execution plan with day-by-day tasks, demo video script, submission checklist |
| `design.md` | Original system architecture document (from Round 1) |
| `requirements.md` | Original functional requirements (from Round 1) |
| `.env.example` | Template for all environment variables needed |
| `.gitignore` | Properly configured for Next.js + Python + AWS |

---

## WHAT'S NOT DONE (Pick Up Here)

### Priority 1: AWS Setup (BLOCKING — needed before anything else)
**Owner:** Team Lead (Ujjwal)
**Time:** 30 minutes

1. Get AWS credentials configured (`aws configure`)
2. Register at https://data.gov.in → get API key
3. Register at https://langfuse.com → get public/secret keys
4. Enable Bedrock model access (Claude Sonnet + Haiku) in `us-east-1`
5. Copy `.env.example` → `.env` and fill in all values

### Priority 2: Deploy Infrastructure
**Owner:** Backend person
**Time:** 15 minutes

```bash
# Option A: SAM (recommended)
cd infra
sam build
sam deploy --guided

# Option B: Manual
bash infra/setup_aws.sh
```

### Priority 3: Load Real Data
**Owner:** Backend person
**Time:** 10 minutes

```bash
# Invoke data ingestion Lambda manually
aws lambda invoke --function-name mandimitra-data-ingestion --payload '{"days_back": 30}' output.json
cat output.json  # verify records loaded
```

### Priority 4: Create Bedrock Agents
**Owner:** Backend person
**Time:** 45 minutes

Follow `infra/BEDROCK_SETUP_GUIDE.md` exactly. It has:
- Step-by-step for all 4 agents (Orchestrator, PriceIntel, SellAdvisory, NegotiationPrep)
- How to add action groups with the OpenAPI spec
- How to set up guardrails
- Test queries to verify

After creating agents, update `.env` with:
```
BEDROCK_AGENT_ID=<orchestrator-agent-id>
BEDROCK_AGENT_ALIAS_ID=<orchestrator-alias-id>
```

### Priority 5: Connect Frontend to Real Backend
**Owner:** Frontend person
**Time:** 5 minutes

Set in `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod/api
```
Restart dev server. The frontend automatically switches from demo mode to real API calls.

### Priority 6: Deploy Frontend
**Owner:** Frontend person
**Time:** 15 minutes

Option A — AWS Amplify:
1. Push code to GitHub
2. AWS Console → Amplify → New App → Connect GitHub repo
3. Set `frontend/` as the app root
4. Add environment variable: `NEXT_PUBLIC_API_URL`
5. Deploy

Option B — Vercel (faster for testing):
```bash
cd frontend
npx vercel
```

### Priority 7: Polish & Demo Video (Mar 1)
- End-to-end test all 5 flows in Hindi + English
- Tune agent prompts for natural Hindi responses
- Record 4-5 minute demo video (script in PLAN.md)
- Write project summary for submission

---

## FILE MAP (Quick Reference)

```
hackathon/
│
├── 📋 PLAN.md                    ← Full execution plan, day-by-day
├── 📋 TEAM_HANDOFF.md            ← THIS FILE — what's done, what to do
├── 📋 README.md                  ← GitHub README
├── 📋 .env.example               ← Environment variables template
├── 📋 .gitignore                 ← Git ignore rules
│
├── 🎨 frontend/                  ← NEXT.JS APP (run: npm run dev)
│   ├── app/
│   │   ├── page.tsx              ← ⭐ MAIN APP — chat logic + demo simulator
│   │   ├── layout.tsx            ← Root layout, SEO meta
│   │   ├── globals.css           ← Styles, animations, fonts
│   │   ├── components/
│   │   │   ├── ChatHeader.tsx    ← Header bar (logo, lang toggle)
│   │   │   ├── ChatBubble.tsx    ← Message bubbles + agent trace
│   │   │   ├── ChatInput.tsx     ← Text input + voice + send
│   │   │   ├── QuickActions.tsx  ← Quick action buttons
│   │   │   ├── TypingIndicator.tsx ← "Thinking..." animation
│   │   │   └── WelcomeScreen.tsx ← Landing page with feature cards
│   │   └── lib/
│   │       ├── api.ts            ← API client, types, session mgmt
│   │       └── voice.ts          ← Web Speech API for voice input
│   └── tailwind.config.ts       ← Custom color theme
│
├── ⚙️ backend/                   ← PYTHON LAMBDAS
│   ├── lambdas/
│   │   ├── data_ingestion/
│   │   │   └── handler.py       ← ⭐ Agmarknet API → DynamoDB pipeline
│   │   ├── chat_handler/
│   │   │   └── handler.py       ← ⭐ Bedrock Agent invocation + LangFuse
│   │   ├── price_query/
│   │   │   └── handler.py       ← ⭐ Price queries + Agent action groups
│   │   └── shared/
│   │       ├── constants.py     ← MSP rates, commodities, mandi coords
│   │       └── dynamodb_utils.py ← DB queries, Haversine, trend calc
│   └── agent_configs/
│       ├── orchestrator_prompt.txt    ← Orchestrator system prompt
│       ├── price_intel_prompt.txt     ← Price agent system prompt
│       ├── sell_advisory_prompt.txt   ← Sell agent system prompt
│       ├── negotiation_prep_prompt.txt ← Negotiation agent prompt
│       └── price_intel_openapi.json   ← ⭐ Tool definitions (OpenAPI spec)
│
├── 🏗️ infra/                    ← AWS INFRASTRUCTURE
│   ├── template.yaml            ← ⭐ SAM template (deploy everything)
│   ├── setup_aws.sh             ← Manual AWS setup script
│   └── BEDROCK_SETUP_GUIDE.md   ← ⭐ Step-by-step agent creation
│
├── 📄 design.md                 ← System architecture (Round 1)
└── 📄 requirements.md           ← Functional requirements (Round 1)
```

---

## TASK SPLIT FOR TEAM

### Person 1: Backend / AWS (Ujjwal)
- [ ] AWS account setup + credentials
- [ ] data.gov.in API key
- [ ] `sam deploy` infrastructure
- [ ] Create Bedrock Agents (follow guide)
- [ ] Load data with ingestion Lambda
- [ ] Test end-to-end API calls
- [ ] LangFuse setup + verify traces

### Person 2: Frontend
- [ ] Review UI, test all demo flows
- [ ] Add any missing UI polish (colors, spacing, mobile test)
- [ ] Connect to real API once backend is live
- [ ] Deploy to AWS Amplify
- [ ] Test on Android phone
- [ ] Add "Share on WhatsApp" button to price brief responses

### Person 3: Content / Demo
- [ ] Test all 5 user flows in Hindi + English
- [ ] Tune agent prompts if Hindi responses sound unnatural
- [ ] Write 1-page Project Summary for submission
- [ ] Write Problem Statement (200 words)
- [ ] Script the demo video (structure in PLAN.md)
- [ ] Record demo video (4-5 min, OBS/Loom)
- [ ] Upload to YouTube/Drive
- [ ] Final submission on Hack2skill dashboard

---

## KEY DECISIONS ALREADY MADE

| Decision | Choice | Why |
|----------|--------|-----|
| Frontend framework | Next.js 14 + Tailwind | Fast, SSR, mobile-optimized |
| Backend | Python Lambdas (serverless) | AWS-native, cheap, auto-scaling |
| AI orchestration | Amazon Bedrock Agents (multi-agent) | AWS hackathon, shows agentic architecture |
| LLM models | Claude Sonnet (reasoning) + Haiku (fast lookups) | Best on Bedrock, cost-efficient |
| Database | DynamoDB with 2 GSIs | Serverless, fast queries, pay-per-use |
| Data source | data.gov.in Agmarknet API | Real government data, free, daily updated |
| LLM tracing | LangFuse (cloud, free tier) | Beautiful dashboard, works with Bedrock, quick setup |
| Deployment | SAM + Amplify | Single-command deploy, CI/CD |
| Demo mode | Built into frontend | Can demo without backend running |

---

## CREDENTIALS NEEDED (Ujjwal to arrange)

| What | Where to get | Who needs it |
|------|-------------|-------------|
| AWS Access Key + Secret | AWS IAM Console | Everyone |
| data.gov.in API Key | https://data.gov.in/user/register | Backend |
| LangFuse Public + Secret Key | https://langfuse.com | Backend |
| AWS Credits ($100 promo) | Hack2skill email (incoming) | Team Lead |

---

*Questions? Check PLAN.md for the full strategy, or the specific file for code details.*
