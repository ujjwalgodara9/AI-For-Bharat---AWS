# 🌾 MandiMitra — AI Mandi Price Intelligence for Indian Farmers

> *AI-powered multi-agent copilot that gives Indian farmers real-time mandi price intelligence, sell/hold recommendations, and negotiation support — all in Hindi.*

**Track:** AI for Retail, Commerce & Market Intelligence
**Hackathon:** AI for Bharat (AWS x Hack2skill)
**Team:** Robots | Lead: Ujjwal Godara

---

## The Problem

India has 7,000+ APMC mandis generating massive commodity price data, yet **86% of small farmers** sell at whatever price the local intermediary offers — losing **15–30% of potential crop value** due to information asymmetry. Current government portals are English-only raw dashboards that lack actionable intelligence.

## The Solution

MandiMitra uses **Amazon Bedrock Agents** to orchestrate three specialist AI agents that work collaboratively:

| Agent | Role |
|-------|------|
| **Price Intelligence** | Real-time mandi prices, comparisons, trend analysis |
| **Sell Advisory** | AI-powered SELL / HOLD / SPLIT recommendations |
| **Negotiation Prep** | Generates price briefs for mandi negotiation |

All agents operate through a **conversational Hindi interface** where farmers ask questions naturally and receive data-driven, actionable answers.

## Architecture

```
User (Hindi/English/Voice)
        │
   [API Gateway]
        │
  [Orchestrator Agent] ── Amazon Bedrock (Claude)
   ┌────┼────┐
   ▼    ▼    ▼
[Price][Sell][Negotiation]
[Intel][Advry][Prep Agent]
   │    │    │
   └────┼────┘
        │
  [Tool Layer]
  ├── DynamoDB (live prices)
  ├── Agmarknet API (data.gov.in)
  ├── Distance Calculator
  └── MSP Lookup
        │
  [LangFuse Tracing]
```

## AWS Services Used (10+)

| Service | Purpose |
|---------|---------|
| Amazon Bedrock Agents | Multi-agent orchestration |
| Bedrock Guardrails | Prevent price hallucination |
| Amazon DynamoDB | Price time-series storage |
| AWS Lambda | Serverless compute |
| Amazon API Gateway | REST API |
| Amazon S3 | Data storage |
| Amazon EventBridge | Scheduled data pipeline |
| AWS Amplify | Frontend hosting |
| Amazon CloudWatch | Monitoring |
| AWS IAM | Security |

## Quick Start

### Prerequisites
- Node.js 18+, Python 3.11+, AWS CLI
- AWS account with Bedrock access
- data.gov.in API key (free)

### 1. Clone & Setup
```bash
git clone <repo-url>
cd hackathon
cp .env.example .env
# Fill in your credentials in .env
```

### 2. Frontend (runs with demo mode by default)
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### 3. AWS Infrastructure
```bash
# Option A: SAM (recommended)
cd infra
sam build && sam deploy --guided

# Option B: Manual
bash infra/setup_aws.sh
```

### 4. Bedrock Agents
Follow `infra/BEDROCK_SETUP_GUIDE.md` for step-by-step agent creation.

### 5. Load Data
```bash
# Trigger data ingestion manually (or wait for daily 6 AM schedule)
aws lambda invoke --function-name mandimitra-data-ingestion output.json
```

## Project Structure

```
hackathon/
├── frontend/                 # Next.js 14 + Tailwind CSS
│   ├── app/
│   │   ├── components/       # Chat UI components
│   │   ├── lib/              # API client, voice input
│   │   └── page.tsx          # Main chat application
│   └── package.json
├── backend/
│   ├── lambdas/
│   │   ├── data_ingestion/   # Agmarknet → DynamoDB pipeline
│   │   ├── chat_handler/     # Bedrock Agent invocation + LangFuse
│   │   ├── price_query/      # Price lookup + Agent action groups
│   │   └── shared/           # Constants, DB utils, calculations
│   └── agent_configs/        # Bedrock Agent prompts + OpenAPI specs
├── infra/
│   ├── template.yaml         # AWS SAM template
│   ├── setup_aws.sh          # Manual AWS setup script
│   └── BEDROCK_SETUP_GUIDE.md
├── design.md                 # System architecture document
├── requirements.md           # Functional requirements
├── PLAN.md                   # Execution plan
└── .env.example              # Environment variables template
```

## Demo Flows

1. **Price Check:** *"इंदौर में सोयाबीन का भाव क्या है?"*
2. **Best Mandi:** *"मेरे पास 20 क्विंटल गेहूं है, कहाँ बेचूं?"*
3. **Sell Advisory:** *"क्या अभी बेचना चाहिए या रुकूं?"*
4. **Negotiation Brief:** *"Price brief दो गेहूं का"*

## Impact

- **150M+** small farming households in India
- **₹50,000+** potential extra income per farmer per year
- **₹8.6/farmer/month** operating cost (100% serverless)
- Directly supports PM's **Doubling Farmers' Income** mission

## Data Source

Real-time commodity prices from **Agmarknet** via data.gov.in government API.
Covers 2000+ mandis, 300+ commodities, updated daily.

---

*Built with Amazon Bedrock Agents, Amazon Nova Pro, and a lot of chai. ☕*
