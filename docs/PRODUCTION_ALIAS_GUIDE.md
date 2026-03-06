# Production Agent Alias Guide

## Why Production Aliases Matter

Currently MandiMitra uses `TSTALIASID` (test alias) which always points to the **working draft**. This means:
- Any change you make to an agent is immediately live (no staging)
- No version pinning — you can't rollback to a known-good version
- No blue-green deployment capability

A **named alias** (e.g., `v1`) points to a specific **numbered version**, giving you version control, rollback, and safe deployments.

---

## Step 1: Create Sub-Agent Aliases First

Sub-agents must have named aliases BEFORE the orchestrator can reference them.

### Via AWS CLI

```bash
# PriceIntelligence
aws bedrock-agent create-agent-alias \
  --agent-id CAEJ90IYS6 \
  --agent-alias-name v1 \
  --description "Production alias for PriceIntel agent"

# SellAdvisory
aws bedrock-agent create-agent-alias \
  --agent-id CCYSN80MGN \
  --agent-alias-name v1 \
  --description "Production alias for SellAdvisory agent"

# Negotiation
aws bedrock-agent create-agent-alias \
  --agent-id UZRXDX75NR \
  --agent-alias-name v1 \
  --description "Production alias for Negotiation agent"

# Weather
aws bedrock-agent create-agent-alias \
  --agent-id XE43VNHO3T \
  --agent-alias-name v1 \
  --description "Production alias for Weather agent"
```

### Via Console
1. Go to **Bedrock > Agents > [Agent Name]**
2. Click **Aliases** tab > **Create alias**
3. Name: `v1`, select the latest prepared version
4. Note down the **Alias ID** (format: `XXXXXXXXXX`)

---

## Step 2: Update Orchestrator's Collaborator References

The orchestrator's sub-agent collaborators must reference the **named aliases** (not TSTALIASID).

### Via Console
1. Go to **Bedrock > Agents > MandiMitra (Orchestrator)**
2. Click **Multi-agent collaboration** section
3. For each collaborator, change the alias from `TSTALIASID` to the `v1` alias ID
4. Click **Save** > **Prepare**

### Via CLI
```bash
# Get current collaborator config
aws bedrock-agent list-agent-collaborators \
  --agent-id GDSWGCDJIX \
  --agent-version DRAFT

# Update each collaborator with named alias
aws bedrock-agent associate-agent-collaborator \
  --agent-id GDSWGCDJIX \
  --agent-version DRAFT \
  --agent-descriptor '{"aliasArn":"arn:aws:bedrock:us-east-1:471112620976:agent-alias/CAEJ90IYS6/<v1-alias-id>"}' \
  --collaboration-instruction "Price intelligence agent for mandi commodity prices" \
  --collaborator-name "MandiMitra-PriceIntelligence"
```

---

## Step 3: Create Orchestrator Alias

After sub-agents have named aliases and orchestrator references them:

```bash
aws bedrock-agent create-agent-alias \
  --agent-id GDSWGCDJIX \
  --agent-alias-name v1 \
  --description "Production alias for MandiMitra orchestrator"
```

Note the **Orchestrator Alias ID** — this replaces `TSTALIASID` in your Lambda.

---

## Step 4: Update Lambda Environment Variables

### Via CLI
```bash
aws lambda update-function-configuration \
  --function-name mandimitra-chat \
  --environment "Variables={
    BEDROCK_AGENT_ID=GDSWGCDJIX,
    BEDROCK_AGENT_ALIAS_ID=<v1-alias-id>,
    LANGFUSE_HOST=https://cloud.langfuse.com,
    LANGFUSE_PUBLIC_KEY=<your-key>,
    LANGFUSE_SECRET_KEY=<your-key>
  }"
```

### Via SAM Template
Update `infra/template.yaml`:
```yaml
Environment:
  Variables:
    BEDROCK_AGENT_ID: GDSWGCDJIX
    BEDROCK_AGENT_ALIAS_ID: <v1-alias-id>  # Replace TSTALIASID
```

Then deploy: `sam build && sam deploy`

### Update `.env`
```
BEDROCK_AGENT_ALIAS_ID=<v1-alias-id>
```

---

## Step 5: Versioning Strategy

### Workflow: v1 → v2 Rollout

1. **Make changes** to agent instructions/config (working draft)
2. **Prepare** the agent (creates a new numbered version, e.g., version 3)
3. **Test** using `TSTALIASID` (still points to draft)
4. **Create new alias** `v2` pointing to the tested version
5. **Update Lambda** env var to point to `v2`
6. **Keep `v1` active** for rollback

```bash
# Prepare creates a new version
aws bedrock-agent prepare-agent --agent-id GDSWGCDJIX

# Create v2 alias pointing to latest version
aws bedrock-agent create-agent-alias \
  --agent-id GDSWGCDJIX \
  --agent-alias-name v2 \
  --routing-configuration '[{"agentVersion":"3"}]'

# Point Lambda to v2
aws lambda update-function-configuration \
  --function-name mandimitra-chat \
  --environment "Variables={BEDROCK_AGENT_ALIAS_ID=<v2-alias-id>,...}"
```

### Alternative: Update existing alias to new version
```bash
aws bedrock-agent update-agent-alias \
  --agent-id GDSWGCDJIX \
  --agent-alias-id <v1-alias-id> \
  --agent-alias-name v1 \
  --routing-configuration '[{"agentVersion":"3"}]'
```

---

## Step 6: Rollback Procedure

If something breaks after deploying v2:

```bash
# Option A: Point Lambda back to v1 alias
aws lambda update-function-configuration \
  --function-name mandimitra-chat \
  --environment "Variables={BEDROCK_AGENT_ALIAS_ID=<v1-alias-id>,...}"

# Option B: Repoint v2 alias to old version
aws bedrock-agent update-agent-alias \
  --agent-id GDSWGCDJIX \
  --agent-alias-id <v2-alias-id> \
  --agent-alias-name v2 \
  --routing-configuration '[{"agentVersion":"2"}]'  # Previous version
```

Rollback is instant — no re-preparation needed.

---

## Step 7: CI/CD Considerations

For future automation:

```yaml
# GitHub Actions workflow (example)
deploy-agent:
  steps:
    - name: Update agent instructions
      run: |
        INST=$(cat backend/agent_configs/orchestrator_prompt.txt)
        aws bedrock-agent update-agent \
          --agent-id $AGENT_ID \
          --instruction "$INST" ...

    - name: Prepare agent
      run: |
        aws bedrock-agent prepare-agent --agent-id $AGENT_ID
        # Wait for PREPARED status
        aws bedrock-agent wait agent-prepared --agent-id $AGENT_ID

    - name: Update alias to latest version
      run: |
        VERSION=$(aws bedrock-agent get-agent --agent-id $AGENT_ID \
          --query 'agent.agentVersion' --output text)
        aws bedrock-agent update-agent-alias \
          --agent-id $AGENT_ID \
          --agent-alias-id $ALIAS_ID \
          --routing-configuration "[{\"agentVersion\":\"$VERSION\"}]"
```

### Key CI/CD Principles
- **Never auto-deploy to production** without testing on `TSTALIASID` first
- **Tag versions** with git commit SHA for traceability
- **Keep at least 2 previous versions** for rollback
- **Test sub-agents independently** before updating orchestrator
- **Order matters**: prepare sub-agents → update orchestrator collaborators → prepare orchestrator → update alias
