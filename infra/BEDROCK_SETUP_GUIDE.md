# Bedrock Agent Setup Guide

Step-by-step guide to create MandiMitra's multi-agent system in AWS Console.

> **Last Updated:** 3 Mar 2026
> **Status:** All Lambdas deployed. Bug fixes applied (weather coords, mandi price lookup, date ingestion).

## Prerequisites

- Bedrock model access enabled for **Claude 3.5 Sonnet** and **Claude 3 Haiku** in `us-east-1`
- SAM stack deployed (DynamoDB table + Lambda functions exist)
- Price Query Lambda ARN from SAM outputs

> **Note on Alias IDs:** After creating an agent alias (Step X → "Create Alias `v1`"), copy the **Alias ID** (not the Agent ID).
> The default test alias `TSTALIASID` points to the working draft — fine for testing but unstable for demos.
> Always use a named alias (e.g., `v1`) for consistent behaviour.

---

## Step 1: Enable Model Access

1. Go to **AWS Console → Amazon Bedrock → Model Access**
2. Click **Manage model access**
3. Enable:
   - `anthropic.claude-3-5-sonnet-20241022-v2:0` (for orchestrator + sell advisory)
   - `anthropic.claude-3-haiku-20240307-v1:0` (for price intel + negotiation prep)
4. Click **Save changes** (takes ~1 minute)

---

## Step 2: Create Price Intelligence Agent

1. Go to **Bedrock → Agents → Create Agent**

2. **Agent details:**
   - Name: `MandiMitra-PriceIntel`
   - Description: `Price intelligence agent for mandi commodity prices`
   - Model: `Claude 3 Haiku`
   - Instructions: Copy contents of `backend/agent_configs/price_intel_prompt.txt`

3. **Add Action Group:**
   - Name: `PriceTools`
   - Action group type: `Define with API schemas`
   - Action group invocation: Select your **Price Query Lambda ARN**
   - API schema: Upload `backend/agent_configs/price_intel_openapi.json`

4. Click **Create Agent**

5. Click **Prepare** to prepare the agent

6. Click **Create Alias** → name it `v1`

7. **Note down:** Agent ID and Alias ID

---

## Step 3: Create Sell Advisory Agent

1. Go to **Bedrock → Agents → Create Agent**

2. **Agent details:**
   - Name: `MandiMitra-SellAdvisory`
   - Description: `Sell/hold/split recommendation agent`
   - Model: `Claude 3.5 Sonnet` (needs deeper reasoning)
   - Instructions: Copy contents of `backend/agent_configs/sell_advisory_prompt.txt`

3. **Add Action Group:**
   - Name: `SellTools`
   - Action group type: `Define with API schemas`
   - Action group invocation: Select your **Price Query Lambda ARN** (same Lambda, different functions)
   - API schema: Use the same `price_intel_openapi.json` (it includes `get_sell_recommendation`)

4. Click **Create Agent** → **Prepare** → **Create Alias** `v1`

5. **Note down:** Agent ID and Alias ID

---

## Step 4: Create Negotiation Prep Agent

1. Go to **Bedrock → Agents → Create Agent**

2. **Agent details:**
   - Name: `MandiMitra-NegotiationPrep`
   - Description: `Generates price briefs for mandi negotiation`
   - Model: `Claude 3 Haiku`
   - Instructions: Copy contents of `backend/agent_configs/negotiation_prep_prompt.txt`

3. **Add Action Group:**
   - Same as above — `PriceTools` with Price Query Lambda

4. Click **Create Agent** → **Prepare** → **Create Alias** `v1`

---

## Step 5: Create Orchestrator Agent (Supervisor)

1. Go to **Bedrock → Agents → Create Agent**

2. **Agent details:**
   - Name: `MandiMitra-Orchestrator`
   - Description: `Central orchestrator that routes to specialist agents`
   - Model: `Claude 3.5 Sonnet`
   - Instructions: Copy contents of `backend/agent_configs/orchestrator_prompt.txt`

3. **Agent collaboration (Multi-Agent):**
   - Enable **Agent collaboration**
   - Add sub-agents:
     - `MandiMitra-PriceIntel` — alias `v1`
     - `MandiMitra-SellAdvisory` — alias `v1`
     - `MandiMitra-NegotiationPrep` — alias `v1`
   - Collaboration mode: **SUPERVISOR_ROUTER**

4. Click **Create Agent** → **Prepare** → **Create Alias** `v1`

5. **Note down the Orchestrator's Agent ID and Alias ID** — these go into your `.env`

---

## Step 6: Add Guardrails

1. Go to **Bedrock → Guardrails → Create guardrail**

2. **Name:** `MandiMitraGuardrails`

3. **Content filters:**
   - Hate: Block HIGH
   - Insults: Block HIGH
   - Sexual: Block HIGH
   - Violence: Block HIGH

4. **Denied topics:**
   - Topic: `non-agricultural-products`
   - Definition: `Questions about gold, silver, stocks, crypto, or non-agricultural commodity prices`
   - Sample phrases: `"gold ka rate kya hai"`, `"stock market price"`, `"bitcoin price"`

5. **Word filters:**
   - Add managed word list for profanity

6. **Contextual grounding:**
   - Enable grounding check
   - Grounding threshold: 0.7
   - Relevance threshold: 0.7

7. Click **Create guardrail**

8. **Attach to Orchestrator Agent:**
   - Go to Orchestrator Agent → Edit → Guardrails → Select `MandiMitraGuardrails`
   - Re-prepare the agent

---

## Step 7: Update Environment Variables

Add these to your `.env`:

```
BEDROCK_AGENT_ID=<orchestrator-agent-id>
BEDROCK_AGENT_ALIAS_ID=<orchestrator-alias-id>   # Use the v1 alias ID, NOT TSTALIASID

# LangFuse — MUST use LANGFUSE_HOST (not LANGFUSE_BASE_URL)
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=<your-key>
LANGFUSE_SECRET_KEY=<your-key>
```

Update the Chat Handler Lambda environment variables in AWS Console or re-deploy with SAM.

> **Common mistake:** Using `LANGFUSE_BASE_URL` instead of `LANGFUSE_HOST` — the chat handler
> reads `os.environ.get("LANGFUSE_HOST")` so the URL must be set under that exact key.

---

## Step 8: Test in Console

1. Go to the **Orchestrator Agent** in Bedrock Console
2. Click **Test** in the right panel
3. Try these queries:

```
Test 1: "सोयाबीन का भाव बताओ इंदौर में"
Expected: Routes to PriceIntel → returns real price data

Test 2: "मेरे पास 50 क्विंटल गेहूं है, कहाँ बेचूं?"
Expected: Routes to PriceIntel → SellAdvisory → returns recommendation

Test 3: "Price brief दो गेहूं का इंदौर मंडी के लिए"
Expected: Routes to NegotiationPrep → returns formatted brief

Test 4: "Gold ka price kya hai?"
Expected: Guardrail blocks → polite refusal
```

4. Check the **Trace** panel to see agent routing and tool calls

---

## Optional: Knowledge Base (RAG)

1. Go to **Bedrock → Knowledge Bases → Create**
2. Name: `MandiMitraKB`
3. Data source: S3 bucket → create a `/knowledge-base/` prefix
4. Upload documents:
   - MSP rate cards (PDF)
   - APMC Act guidelines
   - Crop storage best practices
5. Embedding model: **Amazon Titan Embeddings v2**
6. Vector store: **Quick create (OpenSearch Serverless)**
7. Attach to Orchestrator Agent as a Knowledge Base
